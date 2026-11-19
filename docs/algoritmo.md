# BAQUI: el algoritmo del semáforo

**Idea:** con **5 variables por tramo**, todas medidas con ondas de radio o microondas, sale el color de cada camino. Son reglas simples, sin inteligencia artificial: se pueden explicar en una pizarra y el jurado puede auditarlas.

---

## Las 5 variables

### 1. Cambio del eco (ΔHH): ¿apareció agua?
- **Fuente:** NISAR GCOV, canal HH, comparando la imagen de antes con la de después. Se mide en dB.
- **Cómo funciona:** el agua quieta funciona como un espejo y el eco cae mucho. Si en un punto el eco **bajó fuerte** (más de 3 dB) y **ahora está muy bajo** (debajo de un umbral), eso es **agua nueva**.
- **Agua de siempre:** si el punto ya estaba oscuro **antes**, es una laguna o un río. No se pinta.

### 2. Rebote doble (HH sube, HV estable): ¿hay agua escondida bajo el monte? ⭐ *lo innovador*
- **Fuente:** NISAR GCOV, canales HH y HV.
- **Cómo funciona:** NISAR usa **banda L**, una onda larga que **atraviesa las hojas**. Cuando hay agua bajo los árboles, la onda rebota en el agua, pega en el tronco y vuelve con **más fuerza**. Es el "doble rebote".
- **Por qué importa:** en el Chaco muchos caminos pasan entre monte y bañados. Una cámara nunca ve esa agua; NISAR sí.
- **Regla:** HH sube más de 3 dB en una zona con vegetación (HV alto) = **agua bajo el monte**.

### 3. Suelo mojado (HH sube poco en suelo abierto): ¿hay barro?
- **Fuente:** NISAR GCOV, canal HH.
- **Cómo funciona:** la tierra mojada devuelve **más eco** que la seca, porque el agua cambia cómo refleja el suelo. Si no hay agua a la vista pero el eco **subió un poco** (de 1 a 3 dB) en suelo abierto, la tierra está empapada: **barro probable**.
- **Por qué importa:** el agua se ve fácil, pero el barro es lo que de verdad te encaja. Esto lo mide directamente.

### 4. Lluvia desde la última pasada: ¿el dato sigue valiendo?
- **Fuente:** NASA IMERG (medida con microondas, se actualiza cada 30 min).
- **Cómo funciona:** se suma la lluvia caída **desde que pasó el radar** hasta ahora. Si llovió mucho después, lo que vio el radar ya no vale. Si falta la lluvia de un día, no se toma como día seco: el tramo queda sin dato.

### 5. Qué tan bajo está el tramo (HAND): ¿junta agua?
- **Fuente:** modelo de altura **Copernicus DEM**, que se hizo con radar (TanDEM-X). De ahí sale el **HAND** (*Height Above Nearest Drainage*): cuántos metros está el camino por encima del cauce o bajo más cercano. ⚠️ ASF publica un HAND global de 30 m; confirmar la descarga.
- **Cómo funciona:** un tramo a 1 m del bajo se corta con poca lluvia; uno a 8 m aguanta mucho más. Es el **umbral propio de cada tramo** (la "esponja").
- **Es fijo:** se calcula una sola vez.

---

## Las reglas del semáforo

Por cada tramo se mira una **franja de 30 m** a cada lado del camino (el radar ve de a ~20 m y un camino mide ~10 m).

**Primero se pregunta por el rojo, después por el gris, después por el amarillo y, si no es nada de eso, es verde.**

Antes de todo eso va un control de seguridad: si falta algún valor del radar o de la lluvia, el tramo sale **sin dato**. Un dato vacío nunca da verde. El detalle está en [clasificacion-semaforo.md](clasificacion-semaforo.md).

| Color | Regla | En criollo |
|---|---|---|
| 🔴 **Rojo** | Agua nueva (var. 1) **o** agua bajo el monte (var. 2) en **un tramo seguido de 50 m o más** | Hay agua sobre el camino |
| ⚪ **Gris** | Pasaron **más de 4 días** desde el radar **y** cayeron **más de 20 mm** después | Lo que vio el radar ya no vale |
| 🟡 **Amarillo** | Suelo mojado (var. 3) en buena parte del tramo **o** lluvia desde la pasada (var. 4) por encima del umbral del tramo (var. 5) | Barro probable |
| 🟢 **Verde** | Nada de lo anterior | Se pasa |

**Umbral de lluvia por tramo (var. 5):**
| HAND del tramo | Aguanta hasta |
|---|---|
| Menos de 2 m (bajo) | 15 mm |
| De 2 a 5 m | 30 mm |
| Más de 5 m (alto) | 50 mm |

(Son valores de arranque. Se ajustan con el evento del 09/10 y con lo que cuente alguien que conozca los caminos.)

---

## Tres ideas que lo hacen distinto

1. **El eslabón más débil.** No se promedia el tramo: si **50 m seguidos** tienen agua, el tramo entero es rojo. Un camino con un solo pozo de 50 m está cortado aunque el resto esté seco. Un promedio diría "90 % seco, pasá", y te encajás.
2. **El umbral se calcula solo.** El límite de "oscuro = agua" no se elige a mano: se saca de la propia imagen con el **método de Otsu**, que encuentra el corte entre los dos grupos del histograma (agua y tierra). Sirve para cualquier fecha sin recalibrar.
3. **Cada color dice por qué.** El tramo no solo es amarillo: dice *"amarillo: llovieron 35 mm desde el radar del 11/10 y este tramo aguanta 15 mm"*. Así es auditable.

---

## Lo que sale por tramo (el GeoJSON)
```json
{
  "color": "amarillo",
  "motivo": "llovieron 35 mm desde la pasada del 11/10; el tramo aguanta 15 mm",
  "agua_nueva_m": 0,
  "suelo_mojado_pct": 40,
  "lluvia_desde_pasada_mm": 35,
  "hand_m": 1.4,
  "ultima_pasada": "2026-10-11",
  "fuente": "NISAR GCOV 161A + IMERG + Copernicus DEM"
}
```

## Qué entra en las 48 h
| Prioridad | Variable |
|---|---|
| **Sí o sí** | 1 (agua nueva) y 4 (lluvia): con eso ya hay rojo, gris, amarillo y verde |
| **Mucho valor, poco costo** | 3 (suelo mojado): son los mismos datos del 1, cambia solo la regla |
| **Lo que nos diferencia** | 2 (agua bajo el monte): mismos datos, se suma el canal HV |
| **Si hay tiempo** | 5 (HAND): requiere bajar un dato más. Mientras tanto se usa un umbral fijo de 25 mm |

## Límites (los decimos)
- El viento hace olas sobre el agua y la "ensucia" en el radar: puede dar algún rojo de menos.
- El asfalto y la arena seca también se ven oscuros. Por eso se mira el **cambio**, no la foto sola.
- Los umbrales de dB son de arranque y se ajustan mirando el histograma real del 11/10.
