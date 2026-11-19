"""Del radar a la tabla: mide las variables de cada tramo de camino con dos pasadas NISAR.

Compara una pasada "después" con una "referencia" seca de la MISMA órbita y versión,
y por cada tramo de OpenStreetMap saca lo que pide baqui.clasificador.Tramo:
N, agua_seguida_m, monte_seguido_m, agua_pct, suelo_mojado_pct y Wp.

Uso:
  python -m baqui.medir 20261011_161A164 20260929_161A164 [--zona corredor] [--tramo 1000] [--hoy 2026-10-11]
Salida: datos/nisar/tramos_<después>[_<hoy>].geojson (un tramo por feature, con medidas y color).
Con --hoy posterior a la pasada se suma la lluvia IMERG del tramo (baqui/lluvia.py) y cuenta la edad del radar.
Control de la referencia: con 2 mm o más de lluvia IMERG entre el día anterior y el de la referencia, el tramo
queda sin dato (hacen falta las grillas de esos dos días). Límite: solo mira esos dos días. Una lluvia fuerte de
días anteriores no se ve, aunque el camino siga mojado (en baqui/estado.py el barro baja a la mitad cada 5,7 días):
la fecha de referencia se sigue eligiendo seca a mano.
Cada tramo guarda `referencia_seca`: true (seca), false (llovió) o null (no hay lluvia medida). Así, con lo
guardado en el GeoJSON, el clasificador vuelve a dar el mismo color.

Pasos por píxel (docs/algoritmo.md y docs/clasificacion-semaforo.md):
  1. Máscara de NISAR: vale solo 1..254. El 0 es "parcialmente enfocado" y el 255 queda fuera de la toma
     (lo dice el atributo `description` de `mask` en el GCOV).
  2. HH y HV en dB, con filtro de mediana de 3 × 3 para sacar el moteado.
     Después se limpia con mayoría de 3 × 3 el agua nueva y el doble rebote (clasificacion-semaforo.md, punto 4).
  3. Corte de agua con Otsu sobre HH. Con poca agua en la imagen, Otsu parte la tierra en dos
     (en el corredor da cerca de -8 dB), así que se usa como máximo `tope_agua`.
  4. Corte de monte con Otsu sobre el HV de la referencia, dentro de [`monte_min`, `monte_max`].
  5. Clases: agua de siempre, agua nueva, agua bajo el monte (doble rebote) y suelo mojado.
Por tramo se mira una franja de `franja_m` a cada lado del eje. Los metros seguidos se cuentan en casillas
de `paso_m` a lo largo del camino: una casilla cuenta si tiene al menos un píxel de la clase.
El HAND queda para el paso siguiente: mientras tanto el clasificador usa el umbral fijo de 25 mm.
"""
from pathlib import Path
import argparse, json, math
from dataclasses import dataclass, asdict
from datetime import date, timedelta

import numpy as np
import shapely
from pyproj import Transformer
from scipy.ndimage import median_filter
from shapely.geometry import LineString, mapping
from shapely.ops import substring

from baqui.clasificador import Tramo, Umbrales, clasificar
from baqui.lluvia import Lluvia

D = "datos/nisar"


@dataclass
class Cortes:
    """Valores de arranque en dB. Se calibran con el evento del 9/10 y después no se tocan."""
    baja_agua: float = -3.0     # el eco bajó al menos esto: agua nueva
    sube_monte: float = 3.0     # el eco subió al menos esto bajo vegetación: doble rebote
    mojado_min: float = 1.0     # suelo abierto: subió entre mojado_min y mojado_max
    mojado_max: float = 3.0
    tope_agua: float = -18.0    # el corte de agua nunca queda más alto que esto
    monte_min: float = -18.0    # límites del corte de monte (HV)
    monte_max: float = -12.0
    franja_m: float = 30.0
    paso_m: float = 20.0
    limpiar: bool = True        # mayoría de 3 × 3 sobre agua nueva y doble rebote: borra pintitas sueltas


def otsu(valores, bins=256):
    """Corte que mejor separa dos grupos del histograma (método de Otsu)."""
    v = np.asarray(valores, dtype="float64")
    v = v[np.isfinite(v)]
    h, bordes = np.histogram(v, bins)
    centro = (bordes[:-1] + bordes[1:]) / 2
    w = np.cumsum(h)
    mu = np.cumsum(h * centro)
    total = w[-1]
    entre = (mu[-1] * w - mu * total) ** 2 / (w * (total - w) + 1e-12)
    return float(centro[np.argmax(entre[:-1])])


def a_db(lineal, valido):
    """Potencia lineal a dB con mediana 3 × 3. Lo inválido se rellena con la mediana para filtrar y vuelve a NaN."""
    v = np.where(valido & (lineal > 0), lineal, np.nan).astype("float64")
    v = 10 * np.log10(v)
    ok = np.isfinite(v)
    relleno = np.where(ok, v, np.nanmedian(v))
    f = median_filter(relleno, 3)
    f[~ok] = np.nan
    return f


def cargar(nombre, zona):
    z = np.load(f"{D}/{nombre}_{zona}.npz")
    valido = (z["mask"] > 0) & (z["mask"] < 255)
    return {"hh": a_db(z["HHHH"], valido), "hv": a_db(z["HVHV"], valido), "valido": valido,
            "x": z["x"], "y": z["y"], "epsg": int(z["epsg"]), "archivo": str(z["archivo"])}


def clases(antes, despues, c: Cortes = Cortes()):
    """Mapas de verdadero/falso por píxel. Los cortes usados vuelven en `info`."""
    hh0, hh1, hv0 = antes["hh"], despues["hh"], antes["hv"]
    ok = np.isfinite(hh0) & np.isfinite(hh1) & np.isfinite(hv0)
    paso = max(1, int(ok.sum()) // 2_000_000)          # Otsu con ~2 millones de píxeles alcanza
    otsu0, otsu1, otsu_hv = otsu(hh0[ok][::paso]), otsu(hh1[ok][::paso]), otsu(hv0[ok][::paso])
    corte0, corte1 = min(otsu0, c.tope_agua), min(otsu1, c.tope_agua)
    corte_hv = float(np.clip(otsu_hv, c.monte_min, c.monte_max))
    d = hh1 - hh0
    siempre = ok & (hh0 < corte0)
    nueva = ok & ~siempre & (d <= c.baja_agua) & (hh1 < corte1)
    monte = ok & (hv0 >= corte_hv)
    bajo_monte = monte & ~siempre & (d >= c.sube_monte)
    mojado = ok & ~monte & ~siempre & ~nueva & (d >= c.mojado_min) & (d <= c.mojado_max)
    if c.limpiar:   # sin esto, un píxel de ruido ya suma 20 m "seguidos"
        nueva, bajo_monte = (median_filter(v.astype(np.uint8), 3).astype(bool) & ok for v in (nueva, bajo_monte))
    info = {"otsu_hh_antes": otsu0, "otsu_hh_despues": otsu1, "corte_agua_antes": corte0,
            "corte_agua_despues": corte1, "otsu_hv": otsu_hv, "corte_monte": corte_hv,
            "cambio_mediano_db": float(np.nanmedian(d[ok])),
            "monte_pct": float(100 * monte[ok].mean()), "agua_nueva_pct": float(100 * nueva[ok].mean()),
            "bajo_monte_pct": float(100 * bajo_monte[ok].mean()), "mojado_pct": float(100 * mojado[ok].mean())}
    return {"ok": ok, "siempre": siempre, "nueva": nueva, "bajo_monte": bajo_monte, "mojado": mojado}, info


def _seguido(s, marca, paso):
    """Metros seguidos más largos con la marca, en casillas de `paso` a lo largo del camino."""
    if not marca.any():
        return 0.0
    casillas = np.unique((s[marca] // paso).astype(int))
    corridas = np.split(casillas, np.where(np.diff(casillas) != 1)[0] + 1)
    return float(max(len(r) for r in corridas) * paso)


def medir_tramo(linea: LineString, mapas, x, y, c: Cortes = Cortes()):
    """Medidas de un tramo (en las coordenadas del radar). x crece hacia el este; y baja hacia el sur."""
    xmin, ymin, xmax, ymax = linea.buffer(c.franja_m).bounds
    c0, c1 = np.searchsorted(x, xmin), np.searchsorted(x, xmax, side="right")
    f0, f1 = np.searchsorted(-y, -ymax), np.searchsorted(-y, -ymin, side="right")
    vacio = {"N": 0, "agua_seguida_m": 0.0, "monte_seguido_m": 0.0, "agua_pct": 0.0,
             "suelo_mojado_pct": 0.0, "Wp": 0.0}
    if c0 >= c1 or f0 >= f1:
        return vacio
    xx, yy = np.meshgrid(x[c0:c1], y[f0:f1])
    puntos = shapely.points(xx.ravel(), yy.ravel())
    franja = shapely.distance(linea, puntos) <= c.franja_m
    win = (slice(f0, f1), slice(c0, c1))
    ok = mapas["ok"][win].ravel() & franja
    n = int(ok.sum())
    if n == 0:
        return vacio
    s = shapely.line_locate_point(linea, puntos[ok])
    m = {k: mapas[k][win].ravel()[ok] for k in ("siempre", "nueva", "bajo_monte", "mojado")}
    return {"N": n,
            "agua_seguida_m": _seguido(s, m["nueva"], c.paso_m),
            "monte_seguido_m": _seguido(s, m["bajo_monte"], c.paso_m),
            "agua_pct": round(100 * m["nueva"].mean(), 2),
            "suelo_mojado_pct": round(100 * m["mojado"].mean(), 2),
            "Wp": round(100 * m["siempre"].mean(), 2)}


def cortar(linea: LineString, largo):
    """Parte un camino en tramos de `largo` metros. Un resto de menos de medio tramo se suma al anterior."""
    if linea.length <= largo:
        return [linea]
    bordes = list(np.arange(0, linea.length, largo)) + [linea.length]
    if bordes[-1] - bordes[-2] < largo / 2:
        del bordes[-2]
    return [substring(linea, a, b) for a, b in zip(bordes[:-1], bordes[1:]) if b - a > 1]


def tipo(tags):
    sup = (tags or {}).get("surface", "")
    if sup in ("asphalt", "concrete", "paved", "paving_stones"):
        return "asfalto"
    if sup in ("gravel", "fine_gravel", "compacted", "pebblestone"):
        return "ripio"
    return "tierra"


def _partes(archivo):
    p = archivo.split("_")
    return "_".join(p[5:8]), p[13], p[11][:8]   # órbita-frame, versión de proceso, fecha


def caminos_osm(ruta="datos/osm/roads.json"):
    rd = json.loads(Path(ruta).read_text(encoding="utf-8"))
    return [e for e in rd["elements"] if e.get("type") == "way" and len(e.get("geometry", [])) > 1]


def sin_nan(o):
    """NaN e inf no existen en JSON: pasan a None (null), también dentro de listas y diccionarios."""
    if isinstance(o, dict):
        return {k: sin_nan(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [sin_nan(v) for v in o]
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("despues")
    a.add_argument("referencia")
    a.add_argument("--zona", default="corredor")
    a.add_argument("--tramo", type=float, default=1000.0, help="largo de cada tramo en metros")
    a.add_argument("--hoy", default=None, help="fecha de la consulta (AAAA-MM-DD); por defecto, la de la pasada")
    a.add_argument("--osm", default="datos/osm/roads.json")
    args = a.parse_args(argv)

    antes, despues = cargar(args.referencia, args.zona), cargar(args.despues, args.zona)
    assert antes["epsg"] == despues["epsg"] and np.allclose(antes["x"], despues["x"]) \
        and np.allclose(antes["y"], despues["y"]), "las dos pasadas no tienen la misma grilla"
    orb0, ver0, f0 = _partes(antes["archivo"])
    orb1, ver1, f1 = _partes(despues["archivo"])
    pasada = date(int(f1[:4]), int(f1[4:6]), int(f1[6:]))
    referencia = date(int(f0[:4]), int(f0[4:6]), int(f0[6:]))
    hoy = date.fromisoformat(args.hoy) if args.hoy else pasada
    dias_ref = [referencia - timedelta(days=1), referencia]   # para saber si la referencia es seca
    lluvia = Lluvia()
    falta = [d.isoformat() for d in dias_ref if d.isoformat() not in lluvia.dias] + lluvia.faltan(pasada, hoy)
    if falta:
        raise SystemExit(f"falta IMERG de {', '.join(sorted(set(falta)))}: correr python -m baqui.lluvia")
    mapas, info = clases(antes, despues)
    x, y = despues["x"], despues["y"]
    u = Umbrales()

    ida = Transformer.from_crs(4326, despues["epsg"], always_xy=True).transform
    vuelta = Transformer.from_crs(despues["epsg"], 4326, always_xy=True).transform
    feats, colores, ref_no_seca, ref_sin_lluvia = [], {}, 0, 0
    for way in caminos_osm(args.osm):
        linea = LineString([ida(p["lon"], p["lat"]) for p in way["geometry"]])
        for i, pieza in enumerate(cortar(linea, args.tramo)):
            med = medir_tramo(pieza, mapas, x, y)
            lon, lat = vuelta(*pieza.interpolate(0.5, normalized=True).coords[0])
            mm = lluvia.desde_pasada(lon, lat, pasada, hoy) if hoy > pasada else 0.0
            mm_ref = lluvia.suma(lon, lat, dias_ref)
            # Lo que se midió: True (seca), False (llovió) o None (sin lluvia medida). Hace falta en el GeoJSON:
            # ahí el NaN de mm_ref se guarda como null y, al releerlo, la referencia pasaría por seca.
            seca = mm_ref < u.lluvia_referencia if math.isfinite(mm_ref) else None
            t = Tramo(E=(hoy - pasada).days, T=tipo(way.get("tags")), misma_orbita=orb0 == orb1, lluvia_mm=mm,
                      misma_version=ver0 == ver1, fecha_pasada=pasada.strftime("%d/%m"),
                      referencia_seca=seca, lluvia_referencia_mm=mm_ref, **med)
            r = clasificar(t, u)
            colores[r.color] = colores.get(r.color, 0) + 1
            ref_no_seca += seca is False
            ref_sin_lluvia += seca is None
            props = {"way": way["id"], "nombre": (way.get("tags") or {}).get("name", ""), "tramo": i,
                     "largo_m": round(pieza.length), **asdict(t), "color": r.color, "regla": r.regla,
                     "motivo": r.motivo, "confianza": r.confianza, "avisos": r.avisos}
            feats.append({"type": "Feature", "geometry": mapping(shapely.transform(pieza, lambda xy: np.column_stack(vuelta(xy[:, 0], xy[:, 1])))), "properties": sin_nan(props)})

    salida = f"{D}/tramos_{args.despues}" + (f"_{hoy:%Y%m%d}" if hoy > pasada else "") + ".geojson"
    meta = sin_nan({
        "despues": despues["archivo"], "referencia": antes["archivo"], "hoy": hoy.isoformat(),
        "tramo_m": args.tramo, "cortes": asdict(Cortes()), **{k: round(v, 2) for k, v in info.items()},
        "lluvia": f"IMERG Late diario, del {pasada + timedelta(days=1):%d/%m} al {hoy:%d/%m}" if hoy > pasada
                  else "sin lluvia: hoy = día de la pasada",
        "referencia_seca": f"IMERG Late diario del {dias_ref[0]:%d/%m} y el {dias_ref[1]:%d/%m}: con"
                           f" {u.lluvia_referencia:g} mm o más la referencia no es seca. Tramos en celdas con"
                           f" {u.lluvia_referencia:g} mm o más (sin dato): {ref_no_seca}; sin lluvia medida en esos días: {ref_sin_lluvia}",
        "pendiente": "HAND todavía no se suma (umbral fijo de 25 mm)"})
    # NaN no es JSON: en propiedades y meta ya pasó a null; si queda alguno (una coordenada), que falle acá
    Path(salida).write_text(json.dumps({"type": "FeatureCollection", "baqui": meta, "features": feats},
                                       ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(json.dumps({k: meta[k] for k in meta if k not in ("cortes",)}, ensure_ascii=False, indent=1))
    print(f"{len(feats)} tramos -> {salida}")
    for k, v in sorted(colores.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
