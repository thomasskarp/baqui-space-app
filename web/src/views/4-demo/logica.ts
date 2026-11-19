// Lógica pura de la demo: ¿el agua tapa el camino?
// Sin React ni Leaflet, para poder probarla con node (logica.test.ts).
//
// Regla de BAQUI: si hay un solo tramo de 50 m seguidos tapado por agua NUEVA,
// el camino está intransitable. Las lagunas de siempre no cuentan.

/** Metros seguidos de agua nueva sobre el camino a partir de los cuales no se pasa. */
export const AGUA_SEGUIDA_MAX_M = 50;

/** Cada cuántos metros se mira el recorrido. */
export const PASO_MUESTREO_M = 5;

/** [lat, lon] en grados. */
export type LatLon = [number, number];
/** Anillo de un polígono (sin repetir el primer punto al final). */
export type Poligono = LatLon[];

const RADIO_TIERRA_M = 6371008.8;
const rad = (g: number) => (g * Math.PI) / 180;

/** Distancia entre dos puntos en metros (haversine). */
export function distanciaM(a: LatLon, b: LatLon): number {
  const dLat = rad(b[0] - a[0]);
  const dLon = rad(b[1] - a[1]);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a[0])) * Math.cos(rad(b[0])) * Math.sin(dLon / 2) ** 2;
  return 2 * RADIO_TIERRA_M * Math.asin(Math.sqrt(h));
}

/** Largo de una línea en metros. */
export function largoM(linea: LatLon[]): number {
  let total = 0;
  for (let i = 1; i < linea.length; i++) total += distanciaM(linea[i - 1], linea[i]);
  return total;
}

/** Punto dentro del polígono (rayo horizontal). A escala de un camino rural alcanza con lat/lon planos. */
export function puntoEnPoligono(p: LatLon, poligono: Poligono): boolean {
  const [y, x] = p;
  let dentro = false;
  for (let i = 0, j = poligono.length - 1; i < poligono.length; j = i++) {
    const [yi, xi] = poligono[i];
    const [yj, xj] = poligono[j];
    const cruza = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (cruza) dentro = !dentro;
  }
  return dentro;
}

/** Puntos sobre la línea, uno cada `paso` metros (incluye el primero y el último). */
export function muestrear(linea: LatLon[], paso = PASO_MUESTREO_M): LatLon[] {
  if (linea.length === 0) return [];
  const puntos: LatLon[] = [linea[0]];
  let falta = paso; // metros hasta la próxima muestra
  for (let i = 1; i < linea.length; i++) {
    const a = linea[i - 1];
    const b = linea[i];
    const d = distanciaM(a, b);
    let recorrido = 0;
    while (d - recorrido >= falta) {
      recorrido += falta;
      const t = recorrido / d;
      puntos.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
      falta = paso;
    }
    falta -= d - recorrido;
  }
  const ultimo = linea[linea.length - 1];
  const final = puntos[puntos.length - 1];
  if (final[0] !== ultimo[0] || final[1] !== ultimo[1]) puntos.push(ultimo);
  return puntos;
}

/**
 * El tramo tapado más largo de un camino: cuántos metros, dónde empieza y termina (metros desde el origen) y su punto medio.
 * `metros` cuenta muestras (N muestras = N × paso). `desdeM` y `hastaM` son la posición de la primera y de la última
 * muestra tapada: por eso hastaM − desdeM da un paso menos que `metros`.
 */
export type TramoTapado = { metros: number; desdeM: number; hastaM: number; centro: LatLon | null };

/**
 * Tramo más largo tapado por agua nueva. Un punto dentro de una laguna de siempre no cuenta como tapado.
 * Cada muestra tapada vale `paso` metros (N muestras = N × paso). Eso redondea para el lado prudente: un charco real
 * de 50 m o más siempre da intransitable. Con (N − 1) × paso se escaparían charcos reales de 50 a 55 m.
 */
export function tramoTapadoMasLargo(
  linea: LatLon[],
  aguaNueva: Poligono[],
  lagunasDeSiempre: Poligono[] = [],
  paso = PASO_MUESTREO_M,
): TramoTapado {
  let mejor: TramoTapado = { metros: 0, desdeM: 0, hastaM: 0, centro: null };
  if (aguaNueva.length === 0) return mejor;
  const puntos = muestrear(linea, paso);
  let actual = 0;
  let inicio = 0;
  puntos.forEach((p, i) => {
    const tapado =
      aguaNueva.some((pol) => puntoEnPoligono(p, pol)) && !lagunasDeSiempre.some((pol) => puntoEnPoligono(p, pol));
    if (!tapado) {
      actual = 0;
      return;
    }
    if (actual === 0) inicio = i;
    actual += paso;
    if (actual > mejor.metros) {
      mejor = { metros: actual, desdeM: inicio * paso, hastaM: i * paso, centro: puntos[Math.floor((inicio + i) / 2)] };
    }
  });
  return mejor;
}

/** Metros del tramo más largo tapado por agua nueva (las lagunas de siempre no cuentan). */
export function tramoTapadoMaxM(
  linea: LatLon[],
  aguaNueva: Poligono[],
  lagunasDeSiempre: Poligono[] = [],
  paso = PASO_MUESTREO_M,
): number {
  return tramoTapadoMasLargo(linea, aguaNueva, lagunasDeSiempre, paso).metros;
}

/** true si el camino no da paso: algún tramo de agua nueva llega a AGUA_SEGUIDA_MAX_M. */
export function caminoTapado(
  linea: LatLon[],
  aguaNueva: Poligono[],
  lagunasDeSiempre: Poligono[] = [],
  paso = PASO_MUESTREO_M,
): boolean {
  return tramoTapadoMaxM(linea, aguaNueva, lagunasDeSiempre, paso) >= AGUA_SEGUIDA_MAX_M;
}

/**
 * llegas: el camino 1 da paso · alternativo: el camino 1 está tapado pero el camino 2 da paso ·
 * no-llegas: no hay camino que dé paso (lo más común en el campo: hay un solo camino y está tapado).
 */
export type Veredicto = "llegas" | "alternativo" | "no-llegas";

/**
 * Veredicto del viaje a partir de qué caminos están tapados (en orden: camino 1, camino 2).
 * Sin camino alternativo la lista tiene un solo elemento: [true] → no-llegas.
 */
export function veredicto(tapados: boolean[]): Veredicto {
  if (tapados.length === 0 || !tapados[0]) return "llegas";
  if (tapados.slice(1).some((t) => !t)) return "alternativo";
  return "no-llegas";
}
