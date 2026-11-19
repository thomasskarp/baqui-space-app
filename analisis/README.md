# BAQUI · Análisis de datos de NASA

Acá está la ciencia detrás de la web: los scripts de Python que bajan los datos del radar NISAR de NASA, miden el eco sobre los caminos de tierra del corredor de General San Martín (Chaco) y clasifican cada tramo.

> **English:** Python code that downloads NASA NISAR radar data, measures backscatter change over dirt roads near General San Martín (Chaco, Argentina) and classifies each road segment. Start with [`docs/hipotesis-fisica.md`](../docs/hipotesis-fisica.md) (physical hypothesis) and [`docs/algoritmo.md`](../docs/algoritmo.md) (algorithm).

## Qué leer primero

| Documento | Qué tiene |
|---|---|
| [`docs/hipotesis-fisica.md`](../docs/hipotesis-fisica.md) | Qué le pasa al camino con la lluvia, cómo lo ve el radar, lo que medimos y lo que todavía no se puede afirmar |
| [`docs/algoritmo.md`](../docs/algoritmo.md) | Del radar a la respuesta, paso a paso |
| [`docs/clasificacion-semaforo.md`](../docs/clasificacion-semaforo.md) | Las reglas que deciden el estado de cada tramo |
| [`docs/mvp-caminos.md`](../docs/mvp-caminos.md) | Alcance del prototipo |
| [`docs/recursos-radar.md`](../docs/recursos-radar.md), [`docs/repos-nasa-radar.md`](../docs/repos-nasa-radar.md) | Fuentes y herramientas de radar que revisamos |

## Datos que usa (todos públicos y gratis)

- **NISAR GCOV** (radar de banda L, polarizaciones HH y HV): se bajan desde ASF / NASA Earthdata.
- **SMAP** (humedad del suelo), **IMERG** (lluvia), **OPERA** (agua en superficie) y el modelo de elevación.
- **OpenStreetMap**: los caminos.

Los datos **no están en el repo** (son varios GB): se bajan con los scripts y quedan en `analisis/datos/`, que git ignora.

## Cómo correrlo

```bash
cd analisis
python -m venv .venv          # hace falta Python 3.12 o más nuevo
source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m pytest -q tests   # 178 tests, no necesitan los datos
```

Para bajar datos hace falta una cuenta gratis de [NASA Earthdata](https://urs.earthdata.nasa.gov/):

```bash
python -m baqui.descarga.login_earthdata   # pide usuario y contraseña una vez; los guarda en tu compu, no en el repo
python -m baqui.descarga.bajar_nisar       # baja solo la ventana del corredor
python -m baqui.descarga.bajar_capas       # OPERA, IMERG, elevación y SMAP (o una sola: opera, imerg, dem, smap)
python -m baqui.lluvia 2026-09-25 2026-11-15   # grilla diaria de lluvia IMERG entre esas fechas
# Mide cada tramo comparando una pasada con la de referencia de la misma órbita:
python -m baqui.medir 20261011_161A164 20260929_161A164 --zona corredor
```

## Carpetas

- `baqui/`: medición, clasificación, lluvia, secado y rutas.
- `baqui/descarga/`: bajada de datos de la NASA.
- `baqui/graficos/`: imágenes de antes y después.
- `baqui/chequeos/`: controles de solo lectura que generan los números citados en la hipótesis física y en la web.
- `tests/`: pruebas de la lógica de clasificación, medición y llegada.

Los números que muestra la web salen de acá. Cada uno tiene anotado su archivo de origen en [`../web/src/data/resultados.json`](../web/src/data/resultados.json) (campos `_fuente`).
