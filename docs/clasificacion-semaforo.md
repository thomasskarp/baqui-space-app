# Baqui: clasificación, auditoría y procesamiento

14/11/2026. Este documento junta tres cosas:
- El algoritmo del equipo, [algoritmo.md](algoritmo.md), que es la base.
- Las reglas de seguridad para que no mienta.
- La auditoría que permite **garantizar** un porcentaje de acierto.

Código:
- `analisis/baqui/clasificador.py`: decide el color.
- `analisis/baqui/auditoria.py`: mide el acierto.
- `analisis/baqui/sensibilidad.py`: mide qué tan frágil es cada umbral.
- Tests: `analisis/tests/`. Pasan 181 de 181.

## 1. Qué se puede garantizar (y qué no)

**"Acierta el 100 %" no lo puede decir nadie.** Lo que sí se puede decir, con números, es **"acierta al menos X %"**, con un 95 % de seguridad estadística. Ese X depende de **cuántos casos reales** se comprobaron.

| Para garantizar al menos… | Casos necesarios con 0 errores | Con 1 error | Con 2 errores | Con 5 errores |
|---|---|---|---|---|
| 80 % | 14 | 22 | 30 | 50 |
| 90 % | 29 | 46 | 61 | 103 |
| **95 %** | **59** | 93 | 124 | 208 |
| 99 % | 299 | 473 | 628 | 1.049 |

(Cálculo exacto de Clopper-Pearson, de una cola. Se reproduce con `casos_necesarios()` en `analisis/baqui/auditoria.py`.)

**Cómo se sube el porcentaje garantizado:** se suben **dos cosas a la vez**:
1. **El acierto real.** Se logra con mejores datos y reglas (secciones 3 y 5).
2. **La cantidad de casos comprobados.** Se logra juntando reportes (sección 4). Es lo que más rápido sube la garantía: con 1 solo caso no se puede garantizar nada, aunque esté bien.

**Lo que se garantiza primero es lo grave:** que un camino cortado **no salga verde**. Se mide aparte y se publica como "si Baqui dice verde, la chance de que no se pueda pasar es como mucho X %".

## 2. Las reglas (algoritmo del equipo + seguridad)

**Se lee de arriba hacia abajo y la primera que se cumple decide.**

| Regla | Si… | Color | Origen |
|---|---|---|---|
| **S** | **Falta algún valor** del radar o de la lluvia, órbita o versión distinta, referencia que no es seca, menos de 20 píxeles válidos, o radar de **más de 12 días** | ⚪ **Sin dato** | Seguridad |
| **R1** | **50 m seguidos o más** con agua nueva (el eslabón más débil) | 🔴 Intransitable | Equipo, var. 1 |
| **R2** | **50 m seguidos o más** con agua bajo el monte (doble rebote) | 🔴 Intransitable | Equipo, var. 2 |
| **G** | Radar de **más de 4 días** y **más de 20 mm** de lluvia después | ⚪ **Dato viejo**: "preguntá antes de salir" | Equipo, var. 4 |
| **A1** | 20 m seguidos con agua, o 3 % de la franja con agua nueva | 🟡 Con barro: "agua cerca" | Seguridad |
| **A2** | **30 % o más** de la franja con suelo mojado (el eco 1 a 3 dB más alto) | 🟡 Con barro | Equipo, var. 3 |
| **A2b** | Lo mismo que A2, pero la zona no se mojó (CYGNSS/SMAP) y no llovió | 🟡 Con barro, **confianza baja**: "puede ser un campo arado, verificar" | Seguridad |
| **A3** | La lluvia desde la pasada supera **lo que aguanta el tramo** según su altura (HAND): bajo 15 mm, medio 30 mm, alto 50 mm; sin HAND 25 mm | 🟡 Con barro | Equipo, var. 5 |
| **V** | Nada de lo anterior | 🟢 Transitable | — |

**Reglas que cruzan toda la tabla:**
- **Un dato vacío nunca da verde:** si falta algún valor del radar o de la lluvia (vacío o roto), el tramo sale **sin dato** y el motivo dice cuál. Por ejemplo: *"falta el dato de: suelo mojado, lluvia desde la pasada"*. Se revisa antes que todo lo demás, incluso antes del rojo: si el radar ve agua pero falta otro valor, el tramo sale sin dato (nunca verde, pero tampoco rojo). La altura (HAND) y la humedad de la zona son opcionales: si faltan, se sigue sin ellas. La lluvia de la fecha de referencia es un caso aparte: está en el punto siguiente.
- **Referencia seca:** quiere decir **menos de 2 mm** de lluvia (IMERG) entre el día anterior y el día de la referencia, sumados, en la celda del tramo. Con 2 mm o más, el tramo sale sin dato: *"la fecha de referencia no es seca (4 mm de lluvia)"*. Es un valor de arranque (`lluvia_referencia`), a calibrar. Es un corte directo: acá no corre el margen de prudencia. **Ojo:** este control corre solo si quien llama al clasificador le pasa esa lluvia (`lluvia_referencia_mm`). `medir.py` la pasa siempre, y si la celda viene sin dato (NaN) el tramo sale sin dato. Si no se pasa (`None`, el valor por defecto), el control se saltea. `medir.py` guarda en cada tramo si la referencia era seca (sí, no o sin medir), así que al reclasificar desde su GeoJSON sale el mismo color. Límite: solo mira esos dos días; una lluvia fuerte de días anteriores no se ve, y la fecha de referencia se sigue eligiendo seca a mano.
- **La lluvia que falta no es un día seco:** si la celda de IMERG de un día viene vacía, el tramo sale sin dato; si falta el archivo de un día, la corrida se corta con error. En la estimación día a día (`estado.py`), el tramo sigue sin dato hasta la próxima pasada del radar.
- **Prudencia:** si un valor queda **a menos del 10 % de un corte**, se toma el color más grave. Por ejemplo, 46 m de agua seguida ya cuentan como 50.
- **Un rojo viejo sigue rojo:** si el radar vio agua hace 8 días, se muestra rojo con confianza baja, no gris: la edad del dato no esconde una señal de peligro.
- **Asfalto:** solo se pinta por agua (R1, R2 y A1), nunca por barro.
- **Ripio:** aguanta 50 % más de suelo mojado y de lluvia.
- **Agua de siempre:** si el tramo tiene 30 % o más de laguna en la fecha seca, sale un aviso: "posible error del mapa de caminos".
- **Cada color dice por qué, con números.** Por ejemplo: *"llovieron 35 mm desde la pasada del 11/10; este tramo (a 1,4 m del bajo) aguanta 15 mm"*.

**Confianza:**
- **Alta:** dato de 4 días o menos, y otra pasada de radar o la zona (CYGNSS/SMAP) confirman.
- **Media:** dato de 4 días o menos, sin confirmación.
- **Baja:** dato de más de 4 días, o una contradicción (regla A2b).

## 3. Auditoría exigente: el protocolo

La auditoría sigue **8 pasos, en este orden**. Si uno se saltea, el número no vale.

1. **Congelar las reglas antes de mirar la prueba.** Los umbrales se ajustan con el evento de **calibración** (lluvia del 9/10/2026) y se guardan en un commit de git **con fecha**. Después de eso no se tocan.
2. **Probar con otro evento.** El evento de **prueba** es otra lluvia con pasada NISAR (por ejemplo, 19/8 o 19/9/2026). El acierto que se publica sale **solo de la prueba**. `auditar(..., excluir_evento="calibración")` lo hace solo.
3. **Verdad a ciegas.** Quien anota lo que pasó en el camino ("pasé", "con dificultad", "no pasé") **no ve antes el color de Baqui**.
4. **Casos de las tres clases.** No vale probar solo con días secos, donde acertar "verde" es fácil. Tiene que haber caminos cortados, con barro y sanos.
5. **Tabla de cruce completa**, con los errores a la vista. La genera `python -m baqui.auditoria casos.csv`:
   - acierto medido y **acierto garantizado** (al menos X %);
   - **escapados** (verde y no pasó), con su máximo garantizado;
   - **detección** de cortados entre los que tienen color; el informe dice aparte cuántos cortados reales quedaron sin dato o con dato viejo;
   - **cobertura**: qué parte de los tramos tiene color y no gris. "Dato viejo" se cuenta igual que "sin dato": no entra en el acierto y baja la cobertura.
6. **Revisar cada error, uno por uno:** por qué falló (dato viejo, campo arado, viento sobre el agua, mapa de caminos mal) y qué regla lo hubiera evitado. **Los cambios entran en la versión siguiente**, que se vuelve a probar con un evento nuevo.
7. **Prueba de fragilidad.** `sensibilidad()` mueve cada umbral ±20 % y cuenta cuántos tramos cambian de color. No mueve los cortes de calidad del dato (píxeles, edad máxima del radar de 12 días, lluvia de la fecha de referencia) ni el margen de prudencia. El corte de dato fresco (4 días) sí se mueve, porque decide entre un color y "dato viejo". Si un umbral cambia mucho, está mal elegido o le falta dato.
8. **Rastro completo y repetible.** Cada tramo guarda:
   - el ID del archivo del satélite;
   - la fecha de la pasada;
   - los valores de cada variable;
   - la regla que decidió el color.
   
   Con los mismos archivos, el mismo código da el mismo color. **Un revisor que no escribió el código** corre todo de nuevo y compara.

## 4. De dónde salen los casos (para que la garantía suba)

| Fuente | Qué valida | Cuántos casos |
|---|---|---|
| **Reportes de productores y peones** del equipo y de conocidos: tramo, fecha, "pasé / con dificultad / no pasé" | Todo: agua, barro y verde | Pocos, pero los mejores |
| **Noticias y redes de municipios del Chaco** con caminos cortados y fecha (por ejemplo, "camino X intransitable") | Rojos | Decenas por temporada de lluvias |
| **OPERA DSWx-S1** (radar Sentinel-1, otro equipo y otro método) | Solo la parte de **agua** (R1, R2 y A1) | **Miles**, automáticos |
| **Casos armados a mano** (tests) | Que el código haga lo que dicen las reglas | 181 hoy |

**La parte de agua se puede auditar en serio en la hackatón:** comparar el agua que ve Baqui en cada tramo contra el mapa de agua de OPERA en la misma fecha da miles de casos, y con eso se puede garantizar un porcentaje alto. **La parte de barro necesita reportes de gente**: se arranca con los del equipo y se suma uno por cada uso real.

## 5. Mejorar el procesamiento: más rápido y más confiable

### Más confiable

1. **Referencia con varias fechas secas, no una.** Para cada píxel se usan todas las pasadas secas de la misma órbita y se calcula su eco normal **y cuánto varía**. Después se mide el cambio **en "veces lo normal"** (lo que en estadística se llama puntaje z), no en dB sueltos. Un campo que siempre varía mucho deja de dar falsas alarmas. **Es la mejora que más acierto suma.**
2. **Una referencia por órbita.** Cada órbita de NISAR (060, 111, 161) tiene su propia referencia. Así **todas las pasadas sirven** y hay dato nuevo cada 3–5 días en lugar de cada 12.
3. **Umbral de agua automático (Otsu)** en cada imagen, como dice el algoritmo del equipo, controlado contra OPERA.
4. **Filtrar el ruido del radar antes de medir "50 m seguidos".** Con píxeles de 10–20 m, 50 m son entre 3 y 5 píxeles, y una pintita de ruido podría dar un rojo falso. Hay que pasar un filtro de mediana de 3 × 3 píxeles y pedir que el agua siga en la pasada siguiente o en otra órbita para darle confianza alta.
5. **Usar la máscara de calidad de NISAR** (`mask`) para sacar sombra y layover. Ya está en el archivo GCOV.

### Más rápido

1. **No bajar la imagen entera.** Un GCOV ocupa varios GB. Con `earthaccess.open()` y `h5py` se lee **solo la ventana del camino**. Hay que probarlo en el H0, porque depende de cómo esté armado el archivo.
2. **Calcular una vez por pasada, guardar poco.** Por cada pasada se guarda solo la tabla de tramos (unos KB), no la imagen. La web lee esa tabla.
3. **Buscar pasadas nuevas solas.** Un proceso diario gratuito (GitHub Actions) pregunta a la NASA (CMR) si hay archivos nuevos sobre el Chaco y procesa solo esos. Así Baqui se actualiza **apenas la NASA publica**, sin que nadie lo corra a mano.
4. **La referencia se calcula una sola vez** por órbita y se guarda. Cada pasada nueva es solo una resta.

## 6. Lo que hace falta del equipo

1. **Reportes de los dos eventos** (9/10 y otro), con tramo, fecha y resultado, anotados sin mirar a Baqui.
2. **Links o capturas de noticias de caminos cortados en el Chaco**, con fecha.
3. **Guardar el login de Earthdata**, para bajar NISAR y calibrar.
4. **Privacidad:** nombres, teléfonos y ubicaciones exactas de campos no van a los agentes gratis ni a la entrega.
