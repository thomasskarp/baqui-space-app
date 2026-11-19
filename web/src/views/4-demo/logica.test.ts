// Pruebas de logica.ts. Correr con:  node src/views/4-demo/logica.test.ts
// (Node 24 corre TypeScript directo.)
import { readFileSync } from "node:fs";
import type * as LogicaTipos from "./logica";
import type { Datos } from "./datos";

// Import con extensión .ts para node; tsc no revisa la ruta porque es dinámica.
const L = (await import("./logica" + ".ts")) as typeof LogicaTipos;
const { AGUA_SEGUIDA_MAX_M, caminoTapado, tramoTapadoMaxM, tramoTapadoMasLargo, veredicto, muestrear, largoM } = L;

let fallas = 0;
function prueba(nombre: string, ok: boolean, detalle = "") {
  if (!ok) fallas++;
  console.log(`${ok ? "ok   " : "FALLA"} ${nombre}${detalle ? ` (${detalle})` : ""}`);
}

// Camino recto de 1 km hacia el este, en la latitud de Gral. San Martín.
const LAT = -26.537;
const LON0 = -59.342;
const M_POR_GRADO_LON = (Math.PI / 180) * 6371008.8 * Math.cos((LAT * Math.PI) / 180);
const lon = (m: number) => LON0 + m / M_POR_GRADO_LON;
const lat = (m: number) => LAT + m / ((Math.PI / 180) * 6371008.8);
const camino: LogicaTipos.LatLon[] = [
  [LAT, lon(0)],
  [LAT, lon(1000)],
];
/** Rectángulo de agua que cruza el camino entre los metros desde y hasta. */
const agua = (desde: number, hasta: number): LogicaTipos.Poligono => [
  [lat(-40), lon(desde)],
  [lat(-40), lon(hasta)],
  [lat(40), lon(hasta)],
  [lat(40), lon(desde)],
];

prueba("umbral es 50 m", AGUA_SEGUIDA_MAX_M === 50);
const muestras = muestrear(camino);
prueba("muestreo cada 5 m", muestras.length === 201, `${muestras.length} muestras en ${largoM(camino).toFixed(1)} m`);

// 1. Sin agua: transitable.
prueba("sin agua → transitable", !caminoTapado(camino, []));

// 2. 30 m de agua: sigue verde.
const m30 = tramoTapadoMaxM(camino, [agua(400, 430)]);
prueba("30 m de agua → sigue transitable", !caminoTapado(camino, [agua(400, 430)]), `${m30} m tapados`);

// 3. 60 m de agua: rojo.
const m60 = tramoTapadoMaxM(camino, [agua(400, 460)]);
prueba("60 m de agua → intransitable", caminoTapado(camino, [agua(400, 460)]), `${m60} m tapados`);

// 4. Dos charcos de 30 m separados no se suman.
prueba("dos charcos de 30 m separados → transitable", !caminoTapado(camino, [agua(100, 130), agua(600, 630)]));

// 5. Laguna de siempre de 200 m: no cuenta.
const laguna = agua(200, 400);
prueba("laguna de siempre de 200 m → no cuenta", !caminoTapado(camino, [laguna], [laguna]));
prueba("la misma agua, si fuera nueva → intransitable", caminoTapado(camino, [laguna]));

// 5b. Bordes del conteo. Cada muestra tapada vale 5 m (N muestras = N × 5 m): redondea para el lado prudente.
// Un charco de 50 m o más siempre da intransitable y uno de 40 m o menos nunca, caigan donde caigan las muestras.
// Entre 45 y 50 m depende de dónde caen. (Con (N − 1) × 5 m se escaparían charcos reales de 50 a 55 m.)
const CORRIMIENTOS = [0, 0.5, 1, 2.5, 4, 4.9]; // metros entre el borde del charco y la muestra anterior
/** Un charco de `largo` m en cada corrimiento: en el medio del camino y contra el final (camino que no termina justo en una muestra). */
function charcosDe(largo: number): { linea: LogicaTipos.LatLon[]; charco: LogicaTipos.Poligono }[] {
  return CORRIMIENTOS.flatMap((c) => {
    const fin = 1000 + c;
    const hastaElFin: LogicaTipos.LatLon[] = [
      [LAT, lon(0)],
      [LAT, lon(fin)],
    ];
    return [
      { linea: camino, charco: agua(400 + c, 400 + c + largo) },
      { linea: hastaElFin, charco: agua(fin - largo, fin + 100) },
    ];
  });
}
/** "de 50 a 55 m tapados": lo menos y lo más que cuenta la lógica entre todos los corrimientos. */
const cuenta = (casos: ReturnType<typeof charcosDe>) => {
  const m = casos.map((k) => tramoTapadoMaxM(k.linea, [k.charco]));
  return `de ${Math.min(...m)} a ${Math.max(...m)} m tapados en ${m.length} posiciones`;
};
for (const largo of [50, 51, 52.5, 54.9, 60]) {
  const casos = charcosDe(largo);
  prueba(`charco de ${largo} m → siempre intransitable`, casos.every((k) => caminoTapado(k.linea, [k.charco])), cuenta(casos));
}
for (const largo of [40, 39, 30, 5]) {
  const casos = charcosDe(largo);
  prueba(`charco de ${largo} m → nunca intransitable`, !casos.some((k) => caminoTapado(k.linea, [k.charco])), cuenta(casos));
}

// 6. Veredicto del viaje.
prueba("veredicto: camino 1 libre → llegás", veredicto([false, true]) === "llegas");
prueba("veredicto: solo camino 2 libre → alternativo", veredicto([true, false]) === "alternativo");
prueba("veredicto: los dos tapados → no llegás", veredicto([true, true]) === "no-llegas");
// Sin camino alternativo (lo más común en el campo): un solo camino, tapado → no llegás.
prueba("veredicto: sin camino alternativo y tapado → no llegás", veredicto([true]) === "no-llegas");
prueba("veredicto: sin camino alternativo y libre → llegás", veredicto([false]) === "llegas");

// 7. Escenarios reales de la demo (rutas.json): caminos de OSM + agua simulada (una sola capa "de hoy").
const datos = JSON.parse(readFileSync(new URL("./rutas.json", import.meta.url), "utf8")) as Datos;
const esperado: Record<string, LogicaTipos.Veredicto> = {
  "villa-jardin": "llegas",
  "siete-arboles": "alternativo",
  "laguna-el-lobo": "no-llegas",
};
const ids = datos.destinos.map((d) => d.id);
prueba("están todos los destinos esperados", ids.length === Object.keys(esperado).length && ids.every((id) => id in esperado), ids.join(", "));
prueba("la demo abre con el destino TRANSITABLE", esperado[datos.destino_inicial] === "llegas", datos.destino_inicial);
prueba("el que abre es el primero de la lista", datos.destinos[0].id === datos.destino_inicial);
const nueva = datos.agua.filter((a) => a.tipo !== "laguna_siempre").map((a) => a.coords);
const siempre = datos.agua.filter((a) => a.tipo === "laguna_siempre").map((a) => a.coords);
const charcos = datos.agua.filter((a) => a.tipo === "charco").map((a) => a.coords);
const resultado: Record<string, LogicaTipos.Veredicto> = {};
for (const d of datos.destinos) {
  const tapados = d.caminos.map((c) => caminoTapado(c.coords, nueva, siempre));
  const metros = d.caminos.map((c) => tramoTapadoMaxM(c.coords, nueva, siempre));
  resultado[d.id] = veredicto(tapados);
  prueba(`${d.nombre}: hoy → ${esperado[d.id]}`, resultado[d.id] === esperado[d.id], `tapado seguido: ${metros.join(" m / ")} m`);
  // El camino alternativo solo existe si no es más del doble de largo.
  if (d.caminos[1]) prueba(`${d.nombre}: el camino 2 no es más del doble`, d.caminos[1].km <= 2 * d.caminos[0].km, `${d.caminos[1].km} km contra ${d.caminos[0].km} km`);
  prueba(`${d.nombre}: los datos dicen lo mismo que la lógica`, d.alternativa.existe === (d.caminos.length > 1));
  if (esperado[d.id] === "llegas") {
    prueba(`${d.nombre}: sin agua sobre el camino`, tramoTapadoMaxM(d.caminos[0].coords, [...nueva, ...siempre]) === 0);
  }
  if (esperado[d.id] === "no-llegas") {
    prueba(`${d.nombre}: sin camino alternativo`, d.caminos.length === 1 && !d.alternativa.existe && d.alternativa.motivo === "sin_otro_camino", d.alternativa.motivo);
    prueba(`${d.nombre}: se llega por un solo camino (tramo único de 500 m o más)`, d.un_solo_camino);
    // El agua cae dentro del tramo único (puentes del grafo de OSM): ahí no hay otra forma de llegar.
    const [desde, hasta] = d.tramo_unico_km;
    const t = tramoTapadoMasLargo(d.caminos[0].coords, nueva, siempre);
    const dKm = t.desdeM / 1000;
    const hKm = t.hastaM / 1000;
    prueba(`${d.nombre}: el agua cae en el tramo único`, t.metros >= AGUA_SEGUIDA_MAX_M && dKm >= desde - 0.05 && hKm <= hasta + 0.05,
      `agua del km ${dKm.toFixed(2)} al ${hKm.toFixed(2)}, tramo único del km ${desde} al ${hasta}`);
  }
  // Una laguna de siempre que toca el camino no cuenta; si contara, lo taparía.
  const siContara = d.caminos.map((c) => tramoTapadoMaxM(c.coords, siempre));
  if (siContara.some((m) => m > 0)) {
    prueba(`${d.nombre}: la laguna de siempre toca el camino pero no cuenta`, siContara.some((m) => m >= AGUA_SEGUIDA_MAX_M) && !caminoTapado(d.caminos[0].coords, siempre, siempre), `taparía ${siContara.join(" m / ")} m`);
  }
}
// En el campo casi siempre hay un solo camino: la mayoría de los destinos no tiene camino alternativo según OSM
// (tramo único de 500 m o más: si se corta ahí, no hay otra forma de llegar). Esto es de la red de caminos, no del
// agua de hoy: Colonia Villa Jardín tampoco tiene otro camino, pero hoy no lo necesita.
const unSolo = datos.destinos.filter((d) => d.un_solo_camino);
prueba("la mayoría de los destinos no tiene camino alternativo (al menos 2)", unSolo.length >= 2 && unSolo.length * 2 > datos.destinos.length,
  `${unSolo.length} de ${datos.destinos.length}: ${unSolo.map((d) => d.nombre).join(", ")}`);
// Con el agua de hoy, ¿cuántos quedan INTRANSITABLE sin otro camino? Hoy es uno solo, y es una limitación de los datos:
// entre los lugares de OSM, Laguna El Lobo es el único con camino de tierra (surface) dentro de su tramo único, y el
// agua solo se pone sobre tierra (ver generar_rutas.py). Esta prueba pide al menos uno y que todos los que digan
// "no llegás" sean de un solo camino; si el equipo acepta otra regla de tierra, subir el mínimo a 2.
const sinSalida = datos.destinos.filter((d) => resultado[d.id] === "no-llegas");
prueba("hay al menos un destino INTRANSITABLE sin otro camino, y todos son de un solo camino",
  sinSalida.length >= 1 && sinSalida.every((d) => d.un_solo_camino && !d.alternativa.existe),
  `${sinSalida.length} de ${datos.destinos.length}: ${sinSalida.map((d) => d.nombre).join(", ")}`);
// El cartel de un destino con un solo camino va antes del tramo único (no tapa el tramo que muestra que no hay otro camino).
for (const d of unSolo) {
  const c = d.caminos[0];
  const puntos = muestrear(c.coords);
  let mejor = 0;
  puntos.forEach((p, i) => {
    if (L.distanciaM(p, c.ancla) < L.distanciaM(puntos[mejor], c.ancla)) mejor = i;
  });
  const kmAncla = (mejor * L.PASO_MUESTREO_M) / 1000;
  prueba(`${d.nombre}: el cartel va antes del tramo único`, kmAncla < d.tramo_unico_km[0] && !!c.cartel_lado,
    `cartel en el km ${kmAncla.toFixed(1)} (${c.cartel_lado}), tramo único desde el km ${d.tramo_unico_km[0]}`);
}
// Orden de la lista: el que abre (llegás), el del camino 2 y después los que no tienen otro camino.
const orden = datos.destinos.map((d) => resultado[d.id]);
const rango: Record<LogicaTipos.Veredicto, number> = { llegas: 0, alternativo: 1, "no-llegas": 2 };
prueba("orden: llegás, camino 2, sin otro camino", orden.every((v, i) => i === 0 || rango[orden[i - 1]] <= rango[v]) && orden[0] === "llegas", orden.join(" → "));
// El agua solo toca caminos de tierra según OSM.
const tierra = new Set(datos.superficies_tierra);
for (const a of datos.agua) {
  const malos = a.caminos_osm_tocados.filter((c) => c.surface === null || !tierra.has(c.surface));
  prueba(`${a.id}: es simulada y toca solo caminos de tierra`, a.simulado && a.caminos_osm_tocados.length > 0 && malos.length === 0,
    a.caminos_osm_tocados.map((c) => `way ${c.way} ${c.surface}`).join(", "));
}
// El charco chico cruza el camino 2 de Siete Árboles menos de 50 m: se pasa igual.
const sa = datos.destinos.find((d) => d.id === "siete-arboles")!;
const mCharco = tramoTapadoMaxM(sa.caminos[1].coords, charcos);
prueba("charco chico: toca el camino 2 pero no llega a 50 m", mCharco > 0 && mCharco < AGUA_SEGUIDA_MAX_M, `${mCharco} m`);

console.log(fallas === 0 ? "\nTodo bien." : `\n${fallas} prueba(s) fallaron.`);
if (fallas) process.exit(1);
