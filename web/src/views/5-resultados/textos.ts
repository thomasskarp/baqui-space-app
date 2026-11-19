// Todos los textos visibles de la sección 5 (cómo lo sabe BAQUI y cierre).
// Los números llegan ya formateados desde Seccion5.tsx (salen de src/data/resultados.json).
// BAQUI es una consulta de hoy, no un histórico: sin fechas a la vista.

export const textos = {
  tituloSeccion: "Cómo lo sabe BAQUI",
  // "Zona" y no "camino": el campo de alrededor subió casi lo mismo (+1,57 dB contra +1,63 dB en el eje), el radar no
  // separa el camino de su entorno (docs/hipotesis-fisica.md, sección 3). Elegido por Facundo, 15/11.
  titulo: "El radar ve la zona mojada.",
  bajada: "Medición real del radar NISAR (NASA-ISRO) en el corredor de General San Martín, Chaco. Verificable gratis.",

  // Hipótesis física, arriba del número: primero la causa, después la prueba (pedido de Facundo, 15/11).
  // Sale de docs/hipotesis-fisica.md, sección 1.
  hipotesis: {
    etiqueta: "Hipótesis física",
    titulo: "Por qué pasa",
    pasos: [
      { clave: "seco", nombre: "Seco", eco: "Eco normal", texto: "La tierra seca devuelve el eco de siempre." },
      { clave: "mojado", nombre: "Mojado", eco: "El eco sube", texto: "Sin agua encima: la tierra mojada devuelve más señal." },
      { clave: "agua", nombre: "Bajo agua", eco: "El eco cae", texto: "El agua cubre el suelo y hace de espejo: la señal casi no vuelve." },
    ],
    // Texto de Facundo; "y su entorno" suma lo que mostró la medición (zona mojada).
    // En dos partes: en el celular la causa no se muestra porque los 3 pasos ya la dicen.
    fraseCausa:
      "Con El Niño llueve más y los caminos de tierra se cortan. El radar NISAR ve a través de las nubes, y el agua cambia el eco que vuelve: la tierra mojada devuelve más; si el agua ya cubre el suelo, casi nada.",
    fraseComo:
      "Para probarlo comparamos una pasada después de la lluvia con otra de referencia de la misma órbita. Si el eco sube, el suelo está mojado; si cae, el agua lo tapa. BAQUI lo traduce en transitable o intransitable.",
  },

  // Número principal: el eco extra del radar sobre los caminos de tierra (pedido de Facundo, 15/11).
  // Los "23 km intransitables" se sacaron: salían de una sospecha (eco que sube bajo el monte), no de un corte confirmado.
  estado: "Zona mojada",
  ecoValor: (db: string) => `+${db}`,
  unidadDb: "dB",
  // Sin "contra la tierra seca": la pasada de referencia no estaba del todo seca (ver _fuente en resultados.json).
  ecoRotulo: "de eco extra",
  principal: "El eco subió sobre los caminos rurales y su entorno: el suelo se mojó, sin agua encima.",
  // "Sin pavimento" y no "de tierra": en dos tercios de esos km OSM no dice la superficie (ver _fuente en resultados.json).
  detallePrincipal: (km: string) =>
    `Valor del medio sobre el centro de ${km} km de caminos rurales sin pavimento, según OpenStreetMap.`,
  lectorPrincipal: (db: string, km: string) =>
    `Sobre ${km} km de caminos rurales sin pavimento y su entorno, el radar recibe ${db} decibeles de eco extra: la zona se mojó.`,

  // Datos de apoyo
  subenValor: (n: string) => `${n} de 10`,
  // Se compara sin monte, lo mismo con lo mismo: el campo abierto subió casi igual que el camino, por eso "zona mojada".
  // (Antes comparaba con el campo lejos, que tiene el doble de monte: no era una comparación justa.)
  subenTexto: (campo: string, eje: string) =>
    `puntos del camino con más de 1 dB extra. Sin monte, el campo subió casi igual: +${campo} contra +${eje} dB.`,
  aguaValor: (pct: string) => `${pct} %`,
  aguaTexto: (px: string, total: string) =>
    `con agua abierta: ${px} de ${total} puntos. Mojado pero no bajo agua (bajo el monte no se puede confirmar).`,

  // Fuente (sin nombres de archivo a la vista: llevan la fecha de cada pasada)
  tituloFuente: "De dónde sale",
  lineaFuente: (r: { satelite: string; banda: string; orbita: string; frame: string }) =>
    `Radar ${r.satelite} · banda ${r.banda} · órbita ${r.orbita} · frame ${r.frame}`,
  medicion: "Medición: caminos rurales sin pavimento de OpenStreetMap, mediana del eje",
  copiarId: "Copiar ID del archivo",
  copiado: "Copiado",
  copiarLector: "Copiar ID del archivo: el identificador oficial de NISAR, para buscarlo en ASF Vertex",
  copiadoLector: "Identificador copiado.",
  verificar: "Verificalo gratis en ASF Vertex",
  nuevaPestana: "(se abre en otra pestaña)",

  // Cierre
  cierre: "¿Llegás hoy? Consultá tu camino.",
  marca: "BAQUI",
  marcaBajada: "Caminos rurales leídos desde el espacio",

  // Pie
  real: "Real:",
  realTexto: "radar NISAR, caminos de OpenStreetMap y los resultados de esta sección.",
  simulado: "Simulado:",
  simuladoTexto: "el agua de la demo (sección 4) y la consola de la sección 2 (escena ilustrativa).",
  hecho: "Hecho para NASA Space Apps Challenge 2026 · General San Martín, Chaco",
  separador: "·",
  ia: "Se usó IA para programar y redactar; está declarado en la entrega.",
} as const;
