"""Lee una ventana chica de varias pasadas NISAR para seguir cómo se seca el suelo.

Uso: python -m baqui.descarga.serie_nisar
Guarda datos/nisar/<fecha>_<orbita>_caminos.npz
"""
import os, time
from pathlib import Path
import numpy as np, h5py, earthaccess
from baqui.descarga.bajar_nisar import BASE, SALIDA
from pyproj import Transformer

BBOX = (-59.40, -26.65, -59.18, -26.28)   # alrededor de los 3 caminos candidatos
PASADAS = [  # (colección, texto que identifica el archivo)
    ("NISAR_L2_GCOV_PROVISIONAL_V1", "_060_A_164_2005_DHDH_A_20261004"),
    ("NISAR_L2_GCOV_PROVISIONAL_V1", "_060_A_164_2005_DHDH_A_20261016"),
    ("NISAR_L2_GCOV_PROVISIONAL_V1", "_111_D_102_2005_DHDH_A_20261007"),
    ("NISAR_L2_GCOV_PROVISIONAL_V1", "_111_D_102_2005_DHDH_A_20261019"),
    ("NISAR_L2_GCOV_V1", "_161_A_164_2005_DHDH_A_20261023"),
    ("NISAR_L2_GCOV_PROVISIONAL_V1", "_161_A_164_2005_DHDH_A_20260929"),
    ("NISAR_L2_GCOV_PROVISIONAL_V1", "_161_A_164_2005_DHDH_A_20261011"),
]


def main():
    earthaccess.login(strategy="netrc")
    Path(SALIDA).mkdir(parents=True, exist_ok=True)   # en un clon nuevo la carpeta no existe
    for col, clave in PASADAS:
        p = clave.split("_")
        fecha, orbita = p[-1], p[1] + p[2] + p[3]
        destino = f"{SALIDA}/{fecha}_{orbita}_caminos.npz"
        if os.path.exists(destino):
            continue
        r = [g for g in earthaccess.search_data(short_name=col, point=(-59.34, -26.54),
                                                temporal=(f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:]}",) * 2)
             if clave in g["meta"]["native-id"]]
        if not r:
            print("no está:", clave, flush=True); continue
        t0 = time.time()
        with h5py.File(earthaccess.open(r[:1])[0], "r") as f:
            g = f[BASE]
            x, y = g["xCoordinates"][:], g["yCoordinates"][:]
            epsg = int(g["projection"][()])
            t = Transformer.from_crs(4326, epsg, always_xy=True)
            xs, ys = t.transform([BBOX[0], BBOX[2]] * 2, [BBOX[1]] * 2 + [BBOX[3]] * 2)
            c = np.where((x >= min(xs)) & (x <= max(xs)))[0]
            fl = np.where((y >= min(ys)) & (y <= max(ys)))[0]
            sl = (slice(fl.min(), fl.max() + 1), slice(c.min(), c.max() + 1))
            d = {k: g[k][sl] for k in ("HHHH", "HVHV", "mask") if k in g}
            np.savez_compressed(destino, x=x[sl[1]], y=y[sl[0]], epsg=epsg,
                                archivo=r[0]["meta"]["native-id"], **d)
        print(f"{fecha} {orbita}: {d['HHHH'].shape} en {time.time()-t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
