"""Mide qué se ve y qué no en los caminos (corredor, NISAR 161A164 29/09 vs 11/10). Solo lectura."""
from pathlib import Path
import json, glob, os
import numpy as np
from scipy.ndimage import median_filter, uniform_filter
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling
from rasterio.merge import merge
from pyproj import Transformer
from shapely.geometry import LineString

# Carpeta datos/ al lado de baqui/ (se llena con los scripts de descarga; no va a git).
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "datos")
OUT = {}


def a_db(lin, valido, filtrar=True):
    v = np.where(valido & (lin > 0), lin, np.nan).astype("float32")
    v = 10 * np.log10(v)
    if not filtrar:
        return v
    ok = np.isfinite(v)
    f = median_filter(np.where(ok, v, np.nanmedian(v)), 3)
    f[~ok] = np.nan
    return f


def tipo(tags):
    sup = (tags or {}).get("surface", "")
    if sup in ("asphalt", "concrete", "paved", "paving_stones"):
        return "asfalto"
    if sup in ("gravel", "fine_gravel", "compacted", "pebblestone"):
        return "ripio"
    return "tierra"


z0 = np.load(f"{R}/nisar/20260929_161A164_corredor.npz")
z1 = np.load(f"{R}/nisar/20261011_161A164_corredor.npz")
x, y, epsg = z0["x"], z0["y"], int(z0["epsg"])
assert np.allclose(x, z1["x"]) and np.allclose(y, z1["y"])
val = ((z0["mask"] > 0) & (z0["mask"] < 255)) & ((z1["mask"] > 0) & (z1["mask"] < 255))
hh0, hh1 = a_db(z0["HHHH"], val), a_db(z1["HHHH"], val)
hv0, hv1 = a_db(z0["HVHV"], val), a_db(z1["HVHV"], val)
hh0r, hh1r = a_db(z0["HHHH"], val, False), a_db(z1["HHHH"], val, False)
hv0r, hv1r = a_db(z0["HVHV"], val, False), a_db(z1["HVHV"], val, False)
lin = {"HH0": z0["HHHH"], "HH1": z1["HHHH"], "HV0": z0["HVHV"], "HV1": z1["HVHV"]}
del z0, z1
ok = np.isfinite(hh0) & np.isfinite(hh1) & np.isfinite(hv0) & np.isfinite(hv1)
dHH, dHV = hh1 - hh0, hv1 - hv0
dHHr, dHVr = hh1r - hh0r, hv1r - hv0r
T = from_origin(x[0] - 10, y[0] + 10, 20, 20)
shape = hh0.shape
print("grilla", shape, "validos", ok.sum())

# --- caminos rasterizados por distancia al eje
rd = json.loads(Path(f"{R}/osm/roads.json").read_text(encoding="utf-8"))
ways = [e for e in rd["elements"] if e.get("type") == "way" and len(e.get("geometry", [])) > 1]
tr = Transformer.from_crs(4326, epsg, always_xy=True).transform
lineas = {"tierra": [], "ripio": [], "asfalto": []}
largo = {"tierra": 0, "ripio": 0, "asfalto": 0}
for w in ways:
    ln = LineString([tr(p["lon"], p["lat"]) for p in w["geometry"]])
    t = tipo(w.get("tags"))
    lineas[t].append(ln)
    largo[t] += ln.length
OUT["km_osm_por_tipo"] = {k: round(v / 1000, 1) for k, v in largo.items()}


def ras(lns, dist):
    if not lns:
        return np.zeros(shape, bool)
    return rasterize([(l.buffer(dist), 1) for l in lns], out_shape=shape, transform=T, dtype="uint8").astype(bool)


todos = sum(lineas.values(), [])
eje = {t: ras(lineas[t], 10) & ok for t in lineas}           # centro del píxel a <=10 m del eje: el camino
franja = {t: ras(lineas[t], 30) & ok for t in lineas}        # franja de medir.py
cualquier_camino = ras(todos, 30)
vecino = ras(todos, 100) & ~cualquier_camino & ok             # de 30 a 100 m del eje: al costado
lejos = ~ras(todos, 300) & ok                                 # campo a más de 300 m de un camino

# --- cortes: números de medir.py, pero el de agua es -18 dB fijo (allá: mínimo entre Otsu y -18) y sin la limpieza de 3 × 3
from_corte_agua = -18.0
# Otsu del HV de referencia
def otsu(v, bins=256):
    v = v[np.isfinite(v)]
    h, b = np.histogram(v, bins); c = (b[:-1] + b[1:]) / 2
    w = np.cumsum(h); mu = np.cumsum(h * c); tot = w[-1]
    e = (mu[-1] * w - mu * tot) ** 2 / (w * (tot - w) + 1e-12)
    return float(c[np.argmax(e[:-1])])
paso = max(1, int(ok.sum()) // 2_000_000)
corte_hv = float(np.clip(otsu(hv0[ok][::paso]), -18, -12))
monte = ok & (hv0 >= corte_hv)
siempre = ok & (hh0 < from_corte_agua)
OUT["corte_monte_hv_db"] = round(corte_hv, 2)

# --- DEM a la grilla del radar; altura relativa (no es HAND: DEM menos su media en ~1 km)
tiles = sorted(glob.glob(f"{R}/dem/*.tif"))
srcs = [rasterio.open(t) for t in tiles]
mos, mt = merge(srcs)
dem = np.full(shape, np.nan, "float32")
reproject(mos[0].astype("float32"), dem, src_transform=mt, src_crs="EPSG:4326", dst_transform=T,
          dst_crs=f"EPSG:{epsg}", resampling=Resampling.bilinear, dst_nodata=np.nan)
dfill = np.where(np.isfinite(dem), dem, np.nanmedian(dem))
rel = dem - uniform_filter(dfill, 51)  # 51 px x 20 m ~ 1 km
OUT["dem_rango_m"] = [round(float(np.nanpercentile(dem, 1)), 1), round(float(np.nanpercentile(dem, 99)), 1)]

# --- OPERA agua del 01/10 (antes) y del 13/10 (después) a la grilla
def opera(fecha):
    acc = np.zeros(shape, "uint8") + 255
    for f in sorted(glob.glob(f"{R}/opera/*_{fecha}T*_WTR.tif")):
        with rasterio.open(f) as s:
            a = np.full(shape, 255, "uint8")
            reproject(s.read(1), a, src_transform=s.transform, src_crs=s.crs, dst_transform=T,
                      dst_crs=f"EPSG:{epsg}", resampling=Resampling.nearest, src_nodata=255, dst_nodata=255)
            m = (acc == 255) & (a != 255)
            acc[m] = a[m]
    return acc
op0, op1 = opera("20261001"), opera("20261013")
OUT["opera_valores_0110"] = {int(k): int(v) for k, v in zip(*np.unique(op0[ok], return_counts=True))}
OUT["opera_valores_1310"] = {int(k): int(v) for k, v in zip(*np.unique(op1[ok], return_counts=True))}


def resumen(m, nombre):
    if m.sum() == 0:
        OUT[nombre] = {"n": 0}; return
    l0, l1 = lin["HH0"][m].astype("float64"), lin["HH1"][m].astype("float64")
    v0, v1 = lin["HV0"][m].astype("float64"), lin["HV1"][m].astype("float64")
    OUT[nombre] = {
        "n_px": int(m.sum()), "km2": round(m.sum() * 400 / 1e6, 2),
        "dHH_mediana_db": round(float(np.nanmedian(dHH[m])), 2),
        "dHV_mediana_db": round(float(np.nanmedian(dHV[m])), 2),
        "dHH_media_potencia_db": round(float(10 * np.log10(np.nanmean(l1) / np.nanmean(l0))), 2),
        "dHV_media_potencia_db": round(float(10 * np.log10(np.nanmean(v1) / np.nanmean(v0))), 2),
        "HH_seco_mediana_db": round(float(np.nanmedian(hh0[m])), 2),
        "HH_lluvia_mediana_db": round(float(np.nanmedian(hh1[m])), 2),
        "HV_seco_mediana_db": round(float(np.nanmedian(hv0[m])), 2),
        "HV_lluvia_mediana_db": round(float(np.nanmedian(hv1[m])), 2),
        "pct_dHH_sube_1_a_3": round(100 * float(((dHH[m] >= 1) & (dHH[m] <= 3)).mean()), 1),
        "pct_dHH_sube_mas_3": round(100 * float((dHH[m] > 3).mean()), 1),
        "pct_dHH_baja_3": round(100 * float((dHH[m] <= -3).mean()), 1),
        "pct_monte": round(100 * float(monte[m].mean()), 1),
    }

# 1. cambio por tipo de camino
for t in eje:
    resumen(eje[t], f"1_eje_{t}")
    resumen(franja[t], f"1_franja30m_{t}")
resumen(vecino, "1_costado_30a100m")
resumen(lejos, "1_campo_lejos_300m")
resumen(ok, "1_toda_la_escena")
# tierra sin monte vs con monte
resumen(eje["tierra"] & ~monte, "1_eje_tierra_abierto")
resumen(eje["tierra"] & monte, "1_eje_tierra_con_monte_hv")
# bajos vs lomas (solo eje tierra, abierto, para que el monte del DSM no confunda)
tie = eje["tierra"] & ~monte & np.isfinite(rel)
q1, q2 = np.nanpercentile(rel[tie], [33.3, 66.7])
OUT["rel_terciles_m"] = [round(float(q1), 2), round(float(q2), 2)]
resumen(tie & (rel <= q1), "1_eje_tierra_bajo_tercil")
resumen(tie & (rel >= q2), "1_eje_tierra_loma_tercil")
resumen(tie & (rel <= -0.5), "1_eje_tierra_bajo_rel<-0.5m")
resumen(tie & (rel >= 0.5), "1_eje_tierra_loma_rel>+0.5m")
# lagunas que ya estaban
resumen(siempre, "1_agua_siempre_hh0<-18")
lag = siempre & (op0 == 1)
resumen(lag, "1_laguna_hh0<-18_y_opera0110")
resumen(ok & (op0 == 1), "1_opera_agua_0110")
resumen(siempre & franja["tierra"], "1_agua_siempre_en_franja_tierra")

# 2. barro vs agua abierta vs agua bajo monte (sobre el eje de tierra y franja)
def clases_m(m, nombre):
    n = m.sum()
    nueva = m & ~siempre & (dHH <= -3) & (hh1 < -18)
    barro = m & ~monte & ~siempre & (dHH >= 1) & (dHH <= 3)
    sube_mas3 = m & ~siempre & (dHH > 3)
    bm = m & monte & ~siempre & (dHH >= 3)
    bm_pol = bm & (dHH - dHV >= 3)
    OUT[nombre] = {"n_px": int(n),
                   "pct_del_total_abierto_y_sube_1a3": round(100 * barro.sum() / n, 2),
                   "pct_sube_mas_3": round(100 * sube_mas3.sum() / n, 2),
                   "pct_agua_abierta_nueva": round(100 * nueva.sum() / n, 3),
                   "px_agua_abierta_nueva": int(nueva.sum()),
                   "pct_bajo_monte_dHH>=3": round(100 * bm.sum() / n, 3),
                   "pct_bajo_monte_y_dHH-dHV>=3": round(100 * bm_pol.sum() / n, 3),
                   "px_bajo_monte_y_dHH-dHV>=3": int(bm_pol.sum()),
                   "pct_opera_agua_nueva_1310": round(100 * float(((op1 == 1) & (op0 == 0))[m].sum()) / n, 3),
                   "pct_opera_sin_dato_1310": round(100 * float((op1 > 1)[m].sum()) / n, 2)}
clases_m(eje["tierra"], "2_eje_tierra")
clases_m(franja["tierra"], "2_franja30m_tierra")
clases_m(vecino, "2_costado_30a100m")
clases_m(lejos, "2_campo_lejos_300m")
# HH vs HV en monte al costado del camino
mc = vecino & monte & ~siempre
OUT["2_monte_costado"] = {"n_px": int(mc.sum()),
                          "dHH_mediana": round(float(np.nanmedian(dHH[mc])), 2),
                          "dHV_mediana": round(float(np.nanmedian(dHV[mc])), 2),
                          "dHH_menos_dHV_mediana": round(float(np.nanmedian((dHH - dHV)[mc])), 2),
                          "p95_dHH_menos_dHV": round(float(np.nanpercentile((dHH - dHV)[mc], 95)), 2),
                          "pct_dHH-dHV>=3": round(100 * float(((dHH - dHV)[mc] >= 3).mean()), 2)}
ab = eje["tierra"] & ~monte
OUT["2_eje_tierra_abierto_HHvsHV"] = {"dHH_menos_dHV_mediana": round(float(np.nanmedian((dHH - dHV)[ab])), 2)}

# 4. ruido: píxel suelto vs filtrado; error de la mediana en un tramo de 1 km
OUT["4_ruido"] = {
    "std_dHH_pixel_crudo_campo_lejos": round(float(np.nanstd(dHHr[lejos])), 2),
    "std_dHH_filtro3x3_campo_lejos": round(float(np.nanstd(dHH[lejos])), 2),
    "std_dHV_pixel_crudo_campo_lejos": round(float(np.nanstd(dHVr[lejos])), 2),
    "std_dHH_pixel_crudo_eje_tierra": round(float(np.nanstd(dHHr[eje["tierra"]])), 2),
    "std_dHH_filtro_eje_tierra": round(float(np.nanstd(dHH[eje["tierra"]])), 2),
}
# contraste del camino contra su costado en el día seco (¿se distingue el camino?)
OUT["4_contraste_seco"] = {
    "HH_eje_tierra_abierto": round(float(np.nanmedian(hh0[eje["tierra"] & ~monte])), 2),
    "HH_costado_abierto": round(float(np.nanmedian(hh0[vecino & ~monte])), 2),
    "HV_eje_tierra_abierto": round(float(np.nanmedian(hv0[eje["tierra"] & ~monte])), 2),
    "HV_costado_abierto": round(float(np.nanmedian(hv0[vecino & ~monte])), 2),
    "HH_eje_asfalto": round(float(np.nanmedian(hh0[eje["asfalto"]])), 2),
}
OUT["4_monte_tapa"] = {"pct_eje_tierra_con_monte": round(100 * float(monte[eje["tierra"]].mean()), 1),
                       "pct_franja_tierra_con_monte": round(100 * float(monte[franja["tierra"]].mean()), 1)}
OUT["4_agua_cerca_ruido_hh_seco_lagunas_p50_p05"] = [round(float(np.nanmedian(hh0[siempre])), 2),
                                                     round(float(np.nanpercentile(hh0[siempre], 5)), 2)]
Path(f"{R}/chequeos/salida_corredor.json").write_text(json.dumps(OUT, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps(OUT, indent=1, ensure_ascii=False))
