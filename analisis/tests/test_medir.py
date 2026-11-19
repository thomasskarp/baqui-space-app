import json
from dataclasses import fields

import numpy as np
import pytest
from pyproj import Transformer
from shapely.geometry import LineString

from baqui import medir
from baqui.clasificador import Tramo, clasificar, ROJO, AMARILLO, VERDE, SIN_DATO
from baqui.lluvia import Lluvia
from baqui.medir import Cortes, clases, cortar, medir_tramo, otsu, sin_nan, tipo

# Grilla de 20 m como la de NISAR: x crece al este, y baja al sur
X = np.arange(0, 2000, 20.0)
Y = np.arange(1000, 0, -20.0)
CAMINO = LineString([(100, 500), (1900, 500)])


def mapas_vacios():
    forma = (len(Y), len(X))
    m = {k: np.zeros(forma, bool) for k in ("siempre", "nueva", "bajo_monte", "mojado")}
    m["ok"] = np.ones(forma, bool)
    return m


def zona(m, clave, x0, x1, y0=440, y1=560):
    cx = (X >= x0) & (X <= x1)
    fy = (Y >= y0) & (Y <= y1)
    m[clave][np.ix_(fy, cx)] = True


def test_otsu_separa_dos_grupos():
    rng = np.random.default_rng(1)
    v = np.r_[rng.normal(-22, 1, 3000), rng.normal(-8, 1, 7000)]
    assert -20 < otsu(v) < -10


def test_charco_de_100_m_da_rojo():
    m = mapas_vacios()
    zona(m, "nueva", 800, 900)
    med = medir_tramo(CAMINO, m, X, Y)
    assert 100 <= med["agua_seguida_m"] <= 120
    assert med["N"] > 0 and med["agua_pct"] > 0
    assert clasificar(Tramo(E=0, **med)).color == ROJO


def test_agua_lejos_del_camino_no_cuenta():
    m = mapas_vacios()
    zona(m, "nueva", 800, 1200, y0=700, y1=900)   # a 200 m del eje
    med = medir_tramo(CAMINO, m, X, Y)
    assert med["agua_seguida_m"] == 0 and med["agua_pct"] == 0
    assert clasificar(Tramo(E=0, **med)).color == VERDE


def test_pintitas_sueltas_no_suman_metros_seguidos():
    m = mapas_vacios()
    for x0 in range(200, 1800, 200):              # un píxel cada 200 m
        zona(m, "nueva", x0, x0, 500, 500)
    assert medir_tramo(CAMINO, m, X, Y)["agua_seguida_m"] == 20


def test_barro_en_media_franja_da_amarillo():
    m = mapas_vacios()
    zona(m, "mojado", 100, 1000)
    med = medir_tramo(CAMINO, m, X, Y)
    assert med["suelo_mojado_pct"] >= 30
    assert clasificar(Tramo(E=0, **med)).color == AMARILLO


def test_pixeles_invalidos_no_cuentan():
    m = mapas_vacios()
    m["ok"][:] = False
    assert medir_tramo(CAMINO, m, X, Y)["N"] == 0


def test_tramo_fuera_de_la_imagen():
    lejos = LineString([(5000, 5000), (6000, 5000)])
    assert medir_tramo(lejos, mapas_vacios(), X, Y)["N"] == 0


def test_clases_de_pixeles():
    forma = (4, 4)
    tierra = np.full(forma, -8.0)
    antes = {"hh": tierra.copy(), "hv": np.full(forma, -20.0)}
    antes["hh"][0, 0] = -24                         # laguna de siempre
    antes["hv"][3, :] = -10                         # fila de monte
    despues = {"hh": tierra.copy()}
    despues["hh"][0, 0] = -24
    despues["hh"][1, 1] = -24                       # agua nueva
    despues["hh"][2, 2] = -6                        # +2 dB en suelo abierto: mojado
    despues["hh"][3, 3] = -4                        # +6 dB en monte: doble rebote
    m, info = clases(antes, despues, Cortes(limpiar=False))
    assert m["siempre"][0, 0] and not m["nueva"][0, 0]
    assert m["nueva"][1, 1] and m["mojado"][2, 2] and m["bajo_monte"][3, 3]
    assert m["nueva"].sum() == 1 and m["mojado"].sum() == 1 and m["bajo_monte"].sum() == 1
    assert info["corte_agua_despues"] <= Cortes().tope_agua


def test_cortar_y_tipo():
    piezas = cortar(LineString([(0, 0), (2500, 0)]), 1000)
    assert [round(p.length) for p in piezas] == [1000, 1000, 500]
    assert [round(p.length) for p in cortar(LineString([(0, 0), (2300, 0)]), 1000)] == [1000, 1300]
    assert tipo({"surface": "asphalt"}) == "asfalto"
    assert tipo({"surface": "gravel"}) == "ripio"
    assert tipo({}) == "tierra"


def test_limpieza_borra_pixel_suelto_y_deja_charco():
    forma = (12, 12)
    antes = {"hh": np.full(forma, -8.0), "hv": np.full(forma, -20.0)}
    antes["hv"][:, :2] = -10                        # algo de monte para que Otsu de HV tenga dos grupos
    despues = {"hh": np.full(forma, -8.0)}
    despues["hh"][1, 9] = -24                       # píxel suelto
    despues["hh"][5:9, 5:9] = -24                   # charco de 4 × 4
    m, _ = clases(antes, despues)
    assert not m["nueva"][1, 9]
    assert m["nueva"][6, 6] and m["nueva"].sum() >= 4


def test_sin_nan_deja_json_valido():
    sucio = {"a": float("nan"), "b": [1.5, float("inf"), {"c": -float("inf")}], "d": (np.float64("nan"), 2),
             "e": "NaN", "f": None, "g": 0.0}
    limpio = sin_nan(sucio)
    assert limpio == {"a": None, "b": [1.5, None, {"c": None}], "d": [None, 2], "e": "NaN", "f": None, "g": 0.0}
    assert json.loads(json.dumps(limpio, allow_nan=False)) == limpio
    with pytest.raises(ValueError):
        json.dumps(sucio, allow_nan=False)


# --- main() de punta a punta, con una escena chiquita inventada ---

EPSG = 32721                                             # UTM 21 sur, la zona del corredor
DESPUES, REFERENCIA = "20261011_161A164", "20260929_161A164"
ARCHIVO = "NISAR_L2_PR_GCOV_001_161_A_164_4005_DHDH_A_{0}T093000_{0}T093030_X05009_N_F_J_001.h5"


def _json_estricto(texto):
    """Como lo lee un navegador: NaN o Infinity sueltos no son JSON."""
    def no_es_json(palabra):
        raise ValueError(f"{palabra} no es JSON")
    return json.loads(texto, parse_constant=no_es_json)


@pytest.fixture
def escena(tmp_path, monkeypatch):
    """Dos pasadas, un camino de 2 km (dos tramos) y una celda de lluvia por tramo.

    El tramo 0 tiene un charco de 120 m cruzado sobre el camino; el tramo 1 está seco.
    Devuelve correr(lluvias, *opciones): `lluvias` es {día: (mm del tramo 0, mm del tramo 1)}.
    """
    a_utm = Transformer.from_crs(4326, EPSG, always_xy=True).transform
    a_geo = Transformer.from_crs(EPSG, 4326, always_xy=True).transform
    x0, y0 = a_utm(-59.30, -26.80)
    x, y = x0 + np.arange(-200, 2220, 20.0), y0 + np.arange(400, -420, -20.0)
    hh = np.full((len(y), len(x)), -8.0)                 # tierra
    hh[-4:, :10] = -24.0                                 # laguna de siempre, lejos del camino
    hv = np.full(hh.shape, -20.0)
    hv[:4, :] = -10.0                                    # franja de monte, lejos del camino
    hh1 = hh.copy()
    hh1[np.ix_(np.abs(y - y0) <= 40, (x >= x0 + 400) & (x <= x0 + 500))] = -24.0
    for nombre, fecha, eco in ((REFERENCIA, "20260929", hh), (DESPUES, "20261011", hh1)):
        np.savez(tmp_path / f"{nombre}_corredor.npz", mask=np.ones(hh.shape, "uint8"), HHHH=10 ** (eco / 10),
                 HVHV=10 ** (hv / 10), x=x, y=y, epsg=EPSG, archivo=ARCHIVO.format(fecha))
    puntas = [a_geo(x0, y0), a_geo(x0 + 2000, y0)]
    osm = tmp_path / "roads.json"
    osm.write_text(json.dumps({"elements": [{"type": "way", "id": 7, "tags": {"name": "Camino de prueba"},
                                             "geometry": [{"lon": lo, "lat": la} for lo, la in puntas]}]}),
                   encoding="utf-8")
    grillas = tmp_path / "imerg"
    grillas.mkdir()
    lon = np.array([a_geo(x0 + 500, y0)[0], a_geo(x0 + 1500, y0)[0]])   # una celda sobre cada tramo
    monkeypatch.setattr(medir, "D", str(tmp_path))
    monkeypatch.setattr(medir, "Lluvia", lambda: Lluvia(grillas))

    def correr(lluvias, *opciones):
        for dia, mm in lluvias.items():
            np.savez(grillas / f"{dia}.npz", lon=lon, lat=np.array([-26.8]), p=np.array([mm], dtype="float32"))
        medir.main([DESPUES, REFERENCIA, "--osm", str(osm), *opciones])
        (salida,) = tmp_path.glob("tramos_*.geojson")
        texto = salida.read_text(encoding="utf-8")
        assert "NaN" not in texto and "Infinity" not in texto
        g = _json_estricto(texto)
        return salida.name, g["baqui"], [f["properties"] for f in g["features"]]

    return correr


def test_main_con_referencia_seca(escena):
    nombre, meta, (charco, seco) = escena({"2026-09-28": (0, 0), "2026-09-29": (0, 1.5)})
    assert nombre == f"tramos_{DESPUES}.geojson"
    assert (charco["color"], charco["regla"]) == (ROJO, "R1") and charco["agua_seguida_m"] >= 100
    assert (seco["color"], seco["regla"]) == (VERDE, "V")
    assert (charco["lluvia_referencia_mm"], seco["lluvia_referencia_mm"]) == (0, 1.5)
    assert charco["referencia_seca"] is True and seco["referencia_seca"] is True
    assert charco["lluvia_mm"] == seco["lluvia_mm"] == 0 and charco["nombre"] == "Camino de prueba"
    assert meta["referencia_seca"] == ("IMERG Late diario del 28/09 y el 29/09: con 2 mm o más la referencia no es seca."
                                       " Tramos en celdas con 2 mm o más (sin dato): 0; sin lluvia medida en esos días: 0")
    assert meta["lluvia"] == "sin lluvia: hoy = día de la pasada"


def test_main_referencia_con_lluvia_da_sin_dato_solo_en_ese_tramo(escena):
    # llovió el día anterior a la referencia, y solo sobre el tramo 1
    _, meta, (charco, seco) = escena({"2026-09-28": (0, 3), "2026-09-29": (0, 0.5)})
    assert charco["color"] == ROJO
    assert (seco["color"], seco["regla"]) == (SIN_DATO, "S")
    assert seco["motivo"] == "la fecha de referencia no es seca (3.5 mm de lluvia)"
    # la propiedad dice lo mismo que el motivo (antes quedaba en true)
    assert seco["referencia_seca"] is False and charco["referencia_seca"] is True
    assert meta["referencia_seca"].endswith("Tramos en celdas con 2 mm o más (sin dato): 1; sin lluvia medida en esos días: 0")


def test_main_sin_lluvia_medida_escribe_json_valido(escena):
    lluvias = {"2026-09-28": (np.nan, 0), "2026-09-29": (0, 0), "2026-10-12": (4, np.nan), "2026-10-13": (0, 0)}
    nombre, meta, (charco, seco) = escena(lluvias, "--hoy", "2026-10-13")
    assert nombre == f"tramos_{DESPUES}_20261013.geojson"
    # tramo 0: no se sabe si la referencia era seca; gana "sin dato" aunque el radar vea el charco
    assert charco["lluvia_referencia_mm"] is None and charco["lluvia_mm"] == 4
    assert (charco["color"], charco["motivo"]) == (SIN_DATO, "falta el dato de: lluvia de la fecha de referencia")
    assert charco["referencia_seca"] is None and seco["referencia_seca"] is True   # null: no se sabe si era seca
    # tramo 1: no se sabe cuánto llovió desde la pasada; antes ese día contaba como seco y daba verde
    assert seco["lluvia_mm"] is None and seco["lluvia_referencia_mm"] == 0
    assert (seco["color"], seco["motivo"]) == (SIN_DATO, "falta el dato de: lluvia desde la pasada")
    assert meta["referencia_seca"].endswith("Tramos en celdas con 2 mm o más (sin dato): 0; sin lluvia medida en esos días: 1")
    assert meta["lluvia"] == "IMERG Late diario, del 12/10 al 13/10"


def test_main_con_la_grilla_lejos_del_camino_no_presta_la_celda_del_borde(escena, tmp_path):
    # grilla IMERG a 3 grados del camino, con 0 mm: antes se usaba la celda del borde y el tramo seco salía verde
    for dia in ("2026-09-28", "2026-09-29"):
        np.savez(tmp_path / "imerg" / f"{dia}.npz", lon=np.array([-56.35, -56.25]), lat=np.array([-26.85, -26.75]),
                 p=np.zeros((2, 2), "float32"))
    _, meta, tramos = escena({})
    for p in tramos:
        assert (p["color"], p["motivo"]) == (SIN_DATO, "falta el dato de: lluvia de la fecha de referencia")
        assert p["lluvia_referencia_mm"] is None and p["referencia_seca"] is None
    assert meta["referencia_seca"].endswith("Tramos en celdas con 2 mm o más (sin dato): 0; sin lluvia medida en esos días: 2")


@pytest.mark.parametrize("lluvias, opciones, colores", [
    ({"2026-09-28": (0, 0), "2026-09-29": (0, 1.5)}, (), (ROJO, VERDE)),
    ({"2026-09-28": (0, 3), "2026-09-29": (0, 0.5)}, (), (ROJO, SIN_DATO)),             # llovió en la referencia
    # sin lluvia medida: en la referencia (tramo 0) y desde la pasada (tramo 1). En el JSON las dos quedan en null
    ({"2026-09-28": (np.nan, 0), "2026-09-29": (0, 0), "2026-10-12": (4, np.nan)}, ("--hoy", "2026-10-12"),
     (SIN_DATO, SIN_DATO)),
])
def test_con_lo_guardado_en_el_geojson_sale_el_mismo_color(escena, lluvias, opciones, colores):
    _, _, tramos = escena(lluvias, *opciones)
    assert tuple(p["color"] for p in tramos) == colores
    for p in tramos:
        # antes, el null de la lluvia de referencia volvía como "nadie lo comprobó" y el charco salía rojo
        r = clasificar(Tramo(**{c.name: p[c.name] for c in fields(Tramo)}))
        assert (r.color, r.regla, r.confianza, r.avisos) == (p["color"], p["regla"], p["confianza"], p["avisos"]), p


def test_main_sin_la_grilla_de_la_referencia_no_arranca(escena, tmp_path):
    with pytest.raises(SystemExit, match="falta IMERG de 2026-09-28: correr python -m baqui.lluvia"):
        escena({"2026-09-29": (0, 0)})
    with pytest.raises(SystemExit, match="falta IMERG de 2026-09-28, 2026-10-12: correr python -m baqui.lluvia"):
        escena({}, "--hoy", "2026-10-12")
    assert not list(tmp_path.glob("tramos_*.geojson"))
