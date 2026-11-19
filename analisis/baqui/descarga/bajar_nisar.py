"""Lee por internet solo la ventana de San Martín de los GCOV de NISAR y la guarda chica.

Uso: python -m baqui.descarga.bajar_nisar
Salida: datos/nisar/<fecha>_<orbita>.npz con HHHH, HVHV, mask, x, y y el EPSG.
"""
import sys, time
from pathlib import Path
import numpy as np, h5py, earthaccess
from pyproj import Transformer

import os
# oeste, sur, este, norte. Por defecto: el corredor de Resistencia a General San Martín.
# El cuadrado chico del MVP (el mismo de Sentinel-1) es -59.60,-26.80,-59.10,-26.30.
BBOX = tuple(float(v) for v in os.environ.get("BAQUI_BBOX", "-59.70,-27.55,-58.80,-26.20").split(","))
BASE = "science/LSAR/GCOV/grids/frequencyA/"
SALIDA = "datos/nisar"


def ventana(f):
    g = f[BASE]
    x, y = g["xCoordinates"][:], g["yCoordinates"][:]
    epsg = int(g["projection"][()])
    t = Transformer.from_crs(4326, epsg, always_xy=True)
    xs, ys = t.transform([BBOX[0], BBOX[2], BBOX[0], BBOX[2]], [BBOX[1], BBOX[1], BBOX[3], BBOX[3]])
    cols = np.where((x >= min(xs)) & (x <= max(xs)))[0]
    filas = np.where((y >= min(ys)) & (y <= max(ys)))[0]
    return x, y, epsg, filas, cols


def main():
    earthaccess.login(strategy="netrc")
    r = earthaccess.search_data(short_name="NISAR_L2_GCOV_PROVISIONAL_V1", point=(-59.34, -26.54),
                                temporal=("2026-09-28", "2026-10-12"))
    r = [g for g in r if "_161_A_164_" in g["meta"]["native-id"]]
    Path(SALIDA).mkdir(parents=True, exist_ok=True)   # en un clon nuevo la carpeta no existe
    for g, fh in zip(r, earthaccess.open(r)):
        nombre = g["meta"]["native-id"]
        fecha = nombre.split("_")[11][:8]
        t0 = time.time()
        with h5py.File(fh, "r") as f:
            x, y, epsg, filas, cols = ventana(f)
            if len(filas) == 0 or len(cols) == 0:
                print(nombre, "no cubre la ventana"); continue
            sl = (slice(filas.min(), filas.max() + 1), slice(cols.min(), cols.max() + 1))
            datos = {k: f[BASE + k][sl] for k in ("HHHH", "HVHV", "mask") if k in f[BASE]}
            zona = os.environ.get("BAQUI_ZONA", "corredor")
            np.savez_compressed(f"{SALIDA}/{fecha}_161A164_{zona}.npz", x=x[sl[1]], y=y[sl[0]], epsg=epsg,
                                archivo=nombre, **datos)
        hh = datos["HHHH"]
        ok = np.isfinite(hh) & (hh > 0)
        print(f"{fecha}: {hh.shape} píxeles, paso {abs(x[1]-x[0]):.0f} m, EPSG {epsg}, "
              f"HH mediana {10*np.log10(np.median(hh[ok])):.1f} dB, válidos {100*ok.mean():.0f} %, "
              f"{time.time()-t0:.0f} s", flush=True)


if __name__ == "__main__":
    sys.exit(main())
