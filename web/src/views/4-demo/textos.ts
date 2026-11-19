// Todos los textos visibles de la sección 4 (la demo).
// Para traducir al inglés, alcanza con cambiar este archivo.

const km = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const entero = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 });

/** Cómo se muestra el tag place de OpenStreetMap de cada destino. */
const TIPOS: Record<string, string> = {
  hamlet: "paraje",
  locality: "paraje",
  village: "localidad",
  town: "pueblo",
  isolated_dwelling: "lugar rural (una casa)",
  farm: "lugar rural (un campo)",
};

export const T4 = {
  tituloSeccion: "La demo: ¿llegás hoy?",
  titulo: "¿Llegás hoy?",
  bajada: "Elegí a dónde vas. BAQUI mira cómo está el camino hoy y te dice si podés salir.",
  bajadaNota: "En BAQUI el agua la ve el radar NISAR. En esta demo el agua es simulada.",

  buscador: {
    etiqueta: "Recorrido",
    desde: "Desde",
    origen: "Gral. San Martín",
    placeholder: "¿Hacia dónde?",
    abrir: "Elegir destino",
    lista: "Destinos de la demo",
    elegido: "elegido",
    tipo: (placeOsm: string) => TIPOS[placeOsm] ?? "lugar",
    opcionDetalle: (tipo: string, kmCamino1: number) => `${tipo} · ${km.format(kmCamino1)} km`,
  },

  consultar: {
    boton: "Consultar",
    accesible: (destino: string) => `Consultar cómo está hoy el camino a ${destino}`,
  },

  respuesta: {
    titulo: (destino: string) => `Hoy, a ${destino}`,
    transitable: "TRANSITABLE",
    intransitable: "INTRANSITABLE",
    conDesvio: (n: number, valor: number) => `Por el camino ${n} · ${km.format(valor)} km`,
  },

  frases: {
    llegas: "Llegás. Podés salir.",
    alternativo: "Andá por el camino 2: es más largo, pero llegás.",
    "no-llegas": "No hay otro camino. Hoy no llegás: no salgas.",
  },

  /** Solo cuando no hay otro camino (respuesta "no salgas"). */
  unSoloCamino: "En el campo, casi siempre hay un solo camino.",

  regla: "Regla: 50 m seguidos de agua nueva sobre el camino y no se pasa. Las lagunas de siempre no cuentan.",

  mapa: {
    region: "Mapa satelital del recorrido",
    cargando: "Cargando mapa…",
    error: "No se pudo cargar el mapa. Revisá tu conexión y recargá la página.",
    datosPrueba: "Datos de prueba",
    datosPruebaDetalle: "Agua simulada",
    leyendaCamino: "Camino (OpenStreetMap)",
    leyendaAgua: "Agua nueva",
    leyendaLaguna: "Laguna de siempre",
    laguna: "Laguna de siempre: no cuenta",
    aguaSobreCamino: "Agua sobre el camino",
    charco: (m: number) => `Charco de ${entero.format(m)} m: no alcanza`,
    cartel: (n: number) => `Camino ${n}`,
    cartelKm: (valor: number) => ` · ${km.format(valor)} km`,
    origen: "Gral. San Martín",
    elegirMarcador: (nombre: string) => `Ir a ${nombre}`,
    resumen: (destino: string, partes: string[]) =>
      `Recorrido de Gral. San Martín a ${destino}. ${partes.join(" ")}`,
    resumenCamino: (n: number, valor: number, tapado: boolean) =>
      `Camino ${n}, ${km.format(valor)} km: ${tapado ? "tapado por el agua" : "libre"}.`,
    resumenSinOtro: "No hay otro camino.",
  },

  /** Atribución del mapa (va abajo del mapa, a 12 px). */
  pie: {
    caminos: "Caminos y lugares ©",
    caminosFuente: "OpenStreetMap",
    caminosLicencia: "(ODbL)",
    caminosUrl: "https://www.openstreetmap.org/copyright",
    satelite: "Satélite:",
    sateliteFuente: "Sentinel-2 cloudless 2023",
    sateliteDetalle: "de EOX IT Services GmbH (datos modificados de Copernicus Sentinel 2023)",
    sateliteUrl: "https://s2maps.eu",
    nisar: "Radar NISAR",
    nisarUrl: "https://science.nasa.gov/mission/nisar/",
    nuevaPestana: "(abre en otra pestaña)",
  },
};
