# MVP: un campo, un camino, una lluvia

14/11/2026. Decisión del equipo: **el MVP muestra un solo caso real** (un campo, un camino) y valida la idea con **una fórmula de parámetros y una tabla**. Desafío: Dancing with the SARs.

## El caso

**Una lluvia real, cuatro fechas de NISAR por la misma pasada.** **[verificado]** en ASF y en NASA POWER, para el punto de General San Martín (-26,54; -59,34):

| Fecha | Qué pasó | NISAR (órbita 161, ascendente, frame 164) | Lo que esperamos ver |
|---|---|---|---|
| **29/9/2026** | Antes: sin lluvias grandes desde el 19/9 | ✅ GCOV | 🟢 Referencia seca |
| **9/10/2026** | **Lluvia de ~59 mm** (la más fuerte de jun–nov; ~71 mm en 3 días) | — | — |
| **11/10/2026** | **2 días después** de la lluvia | ✅ GCOV | 🔴 / 🔵 Barro o agua |
| **23/10/2026** | 14 días después: recuperación | ✅ GCOV | 🟡 / 🟢 |
| **4/11/2026** | Casi un mes después | ✅ GCOV | 🟢 |

Pasadas extra para confirmar: órbita 060 (4/10 antes y 16/10 después) y órbita 111 descendente (7/10 antes y 19/10 después).

**Ojo con la calidad de los datos:** 29/9 y 11/10 son **PROVISIONAL** (versión P05023). 23/10 y 4/11 son de la versión nueva (P05036). **El par principal (29/9 contra 11/10) es de la misma versión**: comparable. Al usar las otras fechas hay que aclararlo.

La lluvia sale de NASA POWER (celda de ~50 km). Se confirma con IMERG en la celda exacta del camino.

## Lo que tiene que traer el equipo (lo más importante)

1. **Un camino rural real** cerca de San Martín, que alguno conozca, y el campo al que lleva.
2. **Qué pasó en ese camino entre el 9 y el 20 de octubre de 2026:** ¿se cortó?, ¿hubo barro?, ¿alguien se quedó? Lo mejor son **mensajes o fotos de WhatsApp con fecha** (el problema mismo deja la prueba). Si no hay octubre, cualquier otra fecha con pasada NISAR de la tabla.
3. **Permiso** del productor para usar el caso (sin nombre ni teléfono en la entrega; la ubicación exacta del campo se puede correr o redondear).

> Privacidad: nada de esto va a los agentes gratis. Solo a Claude y al equipo.

## La fórmula (versión 1: valores iniciales, se ajustan con el caso)

Para cada **tramo** de ~500 m del camino se mira una **franja de 50 m a cada lado**.

### Las señales

| Código | Señal | Fuente | Cómo se calcula |
|---|---|---|---|
| **W** | % de la franja con agua | NISAR GCOV (HH) | píxeles con HH < **-18 dB** (umbral inicial) |
| **ΔHH** | Cuánto subió el eco respecto de la fecha seca | NISAR GCOV (HH) | mediana de HH (dB) en la franja, sin el agua, menos la de la referencia seca |
| **P3** | Lluvia de los últimos 3 días | IMERG (POWER de testigo) | suma en mm |
| **P7** | Lluvia de los últimos 7 días | IMERG | suma en mm |
| **S** | Días secos desde la última lluvia > 5 mm | IMERG | conteo |
| **B** | ¿El tramo está en un bajo? | NASADEM | 1 si está más de 1 m por debajo del promedio del entorno de 1 km; si no, 0 |
| **C** | % de arcilla del suelo | SoilGrids | valor del punto |

### La regla

```
1) Si W ≥ 10 %                          → 🔵 INUNDADO
   (confianza alta si OPERA DSWx-S1 también ve agua)

2) Si no, riesgo R de 0 a 100:
   R = 35·n(ΔHH; 0 a 3 dB)
     + 30·n(P3; 0 a 50 mm)
     + 10·n(P7; 0 a 80 mm)
     + 15·B
     + 10·n(C; 20 a 50 %)
     − 20·n(S; 0 a 5 días)
   (n = llevar el valor a una escala de 0 a 1 entre esos dos límites)

3) R ≥ 60 → 🔴 INTRANSITABLE
   35 ≤ R < 60 → 🟡 CON BARRO
   R < 35 → 🟢 TRANSITABLE

4) Si R cae a menos de 5 puntos de un corte → el color más prudente.
5) Sin pasada de radar en los últimos 6 días → mismo cálculo sin ΔHH, marcado "ESTIMADO".
```

**Los pesos (35, 30, 10, 15, 10, 20), los límites y los cortes (35 y 60) son un punto de partida razonable, no una verdad.** Se muestran en pantalla y se pueden mover.

## La tabla de validación (lo que se muestra al jurado)

| Fecha | W | ΔHH | P3 | S | R | Color del sistema | Qué pasó de verdad | ¿Acertó? |
|---|---|---|---|---|---|---|---|---|
| 29/9 | | | | | | | (lo trae el equipo) | |
| 11/10 | | | | | | | | |
| 23/10 | | | | | | | | |
| 4/11 | | | | | | | | |

Se completa con los datos reales y con lo que diga el productor o el peón. **Si un color no coincide, se ajusta un parámetro y se explica por qué.** Mostrar ese ajuste también suma: es el método funcionando.

## Testigos (para no tirar información falsa)

- **Agua:** OPERA DSWx-S1 en fechas cercanas (otro radar) y Sentinel-2 si hubo un día despejado.
- **Humedad:** SMAP (9 km) y NISAR SME2 (200 m). SME2 es PROVISIONAL y puede venir marcada como poco confiable después de lluvia: se lee la marca.
- **Lluvia:** IMERG contra NASA POWER.

## Lo que ve el productor (la demo de 30 segundos)

1. El globo gira y baja al campo.
2. El camino pintado el **29/9: verde**.
3. Botón **"lluvia del 9/10"** → el **11/10 en rojo o azul**.
4. Avanza: **23/10 amarillo**, **4/11 verde**.
5. En cada tramo: "Fuente: NISAR, 11/10/2026 · confianza alta".
6. Cierre: "Sin mandar un mensaje, el productor sabía que no tenía que salir".

## Pasos de trabajo, en orden

1. **H0, lo más difícil primero:** con la cuenta Earthdata, bajar el GCOV del 29/9 y del 11/10 (órbita 161) y abrirlos. Ver que se lea `HHHH` sobre el camino.
2. Elegir el camino real y sacar su línea de OpenStreetMap (o dibujarla).
3. Calcular W y ΔHH en la franja, para las 4 fechas.
4. Bajar IMERG, NASADEM y SoilGrids del punto y calcular R.
5. Completar la tabla de validación con lo que pasó de verdad.
6. Web con el globo y el camino pintado por fecha.
7. Video de 30 segundos, página en inglés y entrega.

## Primer resultado real con radar (Sentinel-1, 14/11)

Comparamos el radar Sentinel-1 del **1/10** (antes) contra el del **13/10** (4 días después de la lluvia del 9/10). Las dos fechas son de la misma órbita (141, descendente) y cubren un cuadrado de ~50 × 50 km alrededor de San Martín.

- **Agua:** 0,22 % del área antes y 0,19 % después. **Al 13/10 no quedaba inundación visible.**
- **Eco del radar:** subió **+1,07 dB** en promedio. **El suelo seguía mojado.** Encaja con "barro sí, agua no".
- **Caminos de tierra de más de 800 m (OpenStreetMap): 256.** Los tramos donde más subió el eco son:

| Camino OSM (id) | Largo | Subida del eco | Centro (lat, lon) |
|---|---|---|---|
| 746343006 | 980 m | +4,5 dB | -26,3338; -59,2365 |
| 118260612 | 1.710 m | +3,2 dB | -26,5898; -59,3005 |
| 1084701978 | 954 m | +2,9 dB | -26,4326; -59,3315 |

**Son candidatos, no confirmados:** la subida puede ser barro, pero también un campo arado o un cultivo al costado. Hay que confirmarlos con alguien que conozca el camino y con NISAR (29/9 contra 11/10). El script de este cruce no está en el repo.

## Primer resultado con NISAR (14/11, datos reales)

Se leyó por internet solo la ventana de ~50 × 50 km de los dos GCOV de NISAR: órbita 161 A, frame 164, P05023, del 29/9 y del 11/10. Están en `datos/nisar/*.npz` y el script es `baqui/graficos/vista_nisar_mvp.py`. La imagen está en `datos/nisar/antes_despues_sanmartin.png`.

- **Eco HH de toda la zona:** pasó de -7,9 a -7,2 dB (**+0,9 dB** de mediana). El 46 % del área subió más de 1 dB.
- **Agua:** 1,3 % antes y 1,0 % después. **Agua nueva: 0,1 %.** No hubo inundación al 11/10: **barro sí, agua no.**
- **Los 3 caminos candidatos que marcó Sentinel-1 también resaltan en NISAR:**

| Camino | Sentinel-1 (1/10 → 13/10) | NISAR (29/9 → 11/10) | Agua nueva |
|---|---|---|---|
| 1 (OSM 746343006) | +4,5 dB | **+3,4 dB** | 0 % |
| 2 (OSM 118260612) | +3,2 dB | **+1,9 dB** | 0 % |
| 3 (OSM 1084701978) | +2,9 dB | **+3,0 dB** | 0 % |

**Dos radares distintos** (Sentinel-1 en banda C y NISAR en banda L, con órbitas y fechas distintas) **marcan los mismos caminos.** En la zona, la subida media fue de +0,9 dB. Sigue faltando confirmarlo en el terreno: puede ser barro o un campo arado al costado.

**La misma pasada de NISAR cubre de la latitud -28,4 a la -25,8 y de la longitud -61,7 a la -58,7: entran Resistencia y General San Martín.** La lectura del corredor completo quedó en marcha.

## Cómo se secaron los caminos (NISAR, 4 pasadas después de la lluvia)

Cada pasada se compara contra una referencia seca **de su misma órbita**. Script: `baqui/secado.py`. Gráfico: `datos/nisar/secado_caminos.png`.

| Días después | Pasada | Zona | Camino 1 | Camino 2 | Camino 3 |
|---|---|---|---|---|---|
| 2 | 11/10, órbita 161 | +1,1 dB | **+3,4** | **+1,9** | **+3,0** |
| 7 | 16/10, órbita 060 | +0,8 | +1,1 | +0,5 | +1,4 |
| 10 | 19/10, órbita 111 | +0,6 | +1,0 | +1,3 | +1,1 |
| 14 | 23/10, órbita 161 (*) | -0,7 | 0,0 | -0,1 | 0,0 |

(*) Versión distinta del producto (P05036 contra P05023) y 7 mm de lluvia el 21-23/10. La caída de la zona (-0,7 dB) puede ser en parte el cambio de versión.

- **El barro baja a la mitad en unos 5,7 días** (ajuste con las 3 primeras pasadas). Es la `media_vida` que ahora usa `baqui/estado.py`.
- **La primera semana se seca más rápido** (media vida de ~3 a 4,5 días entre el día 2 y el 7). Después va más lento.
- **Con la fórmula actual:** rojo el 11/10, amarillo el 16 y el 19/10, y verde el 23/10.
- **Límites:** es una sola lluvia y 3 caminos. Se comparan órbitas distintas, que miran con ángulos distintos. Falta la confirmación en el terreno. **Es una primera medición, no una verdad:** se ajusta con cada lluvia nueva.

## Corredor Resistencia – General San Martín (NISAR 161A, 29/9 contra 11/10)

Ventana de ~95 × 150 km, leída con `baqui/descarga/bajar_nisar.py`. Imagen: `datos/nisar/antes_despues_corredor.png` (`baqui/graficos/vista_corredor.py`).

- **Las dos ciudades entran en la misma pasada.** Resistencia queda cerca del borde este de la franja. El 19 % de la ventana cae fuera de la franja.
- **La mitad norte, alrededor de General San Martín, se mojó** (azul). **Hacia Resistencia casi no cambió** o bajó un poco (rojo claro). La lluvia del 9/10 cargó más al norte.
- **Para la demo:** se puede llegar bien hasta cerca de San Martín, y **el problema está en los últimos kilómetros de tierra** de la zona norte. Es justo el caso de "avanzás el 70 % y te quedás en el 30 %".
- El porcentaje de agua de esta ventana no se informa: el borde negro de la franja (sin dato) se confunde con agua y hay que enmascararlo antes de contar.

## Semáforo por tramo con NISAR real (`baqui/medir.py`, 15/11)

El paso entre el radar y la tabla. Corrida: `python -m baqui.medir 20261011_161A164 20260929_161A164`. Salida: `datos/nisar/tramos_20261011_161A164.geojson`, con 1387 tramos de ~1 km sobre los caminos de OpenStreetMap del corredor.

- **Píxeles:** se usa la máscara de NISAR (solo valen 1 a 254; el 0 es "parcialmente enfocado"). Además se aplica una mediana de 3 × 3 y una franja de 30 m a cada lado del eje.
- **Otsu no sirve solo para el agua:** con tan poca agua en la imagen, el corte cae en -8,5 dB, que separa dos tipos de tierra. Se usa como máximo -18 dB. Con Otsu, el HV separa monte de campo abierto en -15,8 dB.
- **En toda la ventana:**
  - agua nueva: 0,05 %;
  - doble rebote bajo el monte: 0,17 %;
  - suelo mojado: 11 %;
  - cambio mediano del eco: +0,23 dB.

  **Coincide con lo anterior: barro sí, agua no.**
- **Resultado (lluvia y HAND todavía no se suman):**
  - 760 con barro (651 por suelo mojado y 109 por agua cerca);
  - 393 transitables;
  - 23 intransitables, todos por doble rebote bajo el monte;
  - 211 sin dato: 128 caen fuera de la franja del radar y 83 son caminos de OSM de menos de 100 m.
- **Los 3 caminos candidatos:**
  - el 1 y el 2 salen con barro;
  - el 3 sale transitable, con 26,7 % de suelo mojado. Queda justo debajo del corte (30 % menos el margen del 10 %).
- **Limpieza:** sin la mayoría de 3 × 3, el doble rebote daba 167 rojos con píxeles sueltos. Con la limpieza quedan 23.
- **Ojo:**
  - El 68 % de la ventana queda como "monte" (HV alto). Eso incluye cultivos y pastizales, así que los 23 rojos por doble rebote son lo menos firme. Hay que mirarlos uno por uno contra la imagen o preguntar.
  - La referencia del 29/9 tuvo 4 mm de lluvia ese mismo día (IMERG), de media en todo el corredor: llovió sobre todo al sur. En las celdas de los tramos medidos fueron entre 0,1 y 1,2 mm, menos que los 2 mm del control de referencia seca. Ese control no deja ningún tramo sin dato y las cifras de arriba no cambian (corrida repetida el 18/11).

### Con la lluvia sumada (`baqui/lluvia.py`, 15/11)

- **Grilla IMERG de cada día** (0,1°, unos 10 km) en `datos/imerg/grilla/`: 50 días, del 25/9 al 13/11. Cada tramo suma la lluvia de su celda desde el día siguiente a la pasada hasta el día de la consulta. Si falta un día, no se inventa: corta con error.
- **Corrida:** `python -m baqui.medir 20261011_161A164 20260929_161A164 --hoy 2026-10-23`.

| Consulta | Lluvia por tramo desde el 11/10 (mín / mediana / máx) | Cambio |
|---|---|---|
| 13/10 | 0,2 / 0,8 / 2,9 mm | ninguno |
| 21/10 | 0,3 / 0,9 / 3,5 mm | ninguno |
| 23/10 | 0,4 / 3,0 / 18,8 mm | 13 tramos pasan a **dato viejo** ("llovieron 18 mm después del radar: preguntá antes de salir") |

- **El 22/10 llovió al sur, no al norte.** Al sur de -26,95° la media fue 25,5 mm, con un máximo de 59 mm cerca de Resistencia. Al norte, donde están los caminos de OSM que bajamos, fue 3,8 mm. Eso explica la diferencia con NASA POWER que figuraba como pendiente: es probable que POWER se haya leído en un punto del norte.
- **Lo que falta:**
  - el semáforo todavía no "seca" el barro con el tiempo. El 21/10, sin lluvia nueva, sigue igual que el 11/10 (`estado.py` tiene la media vida de 5,7 días y falta conectarla);
  - los caminos de OSM cubren solo la mitad norte del corredor;
  - el HAND.
