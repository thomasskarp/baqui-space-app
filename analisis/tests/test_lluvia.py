import math
from datetime import date

import numpy as np
import pytest

from baqui.lluvia import Lluvia


def grilla(carpeta, dia, norte, sur):
    """Dos celdas: la del norte (-26,5) y la del sur (-27,5)."""
    np.savez(carpeta / f"{dia}.npz", lon=np.array([-59.3]), lat=np.array([-27.5, -26.5]),
             p=np.array([[sur], [norte]], dtype="float32"))


def test_suma_desde_el_dia_siguiente_y_por_celda(tmp_path):
    grilla(tmp_path, "2026-10-11", 99, 99)   # día de la pasada: no cuenta
    grilla(tmp_path, "2026-10-12", 10, 1)
    grilla(tmp_path, "2026-10-13", 5, np.nan)
    ll = Lluvia(tmp_path)
    assert ll.desde_pasada(-59.3, -26.55, date(2026, 10, 11), date(2026, 10, 13)) == 15
    assert ll.desde_pasada(-59.3, -27.4, date(2026, 10, 11), date(2026, 10, 12)) == 1
    assert ll.desde_pasada(-59.3, -26.5, date(2026, 10, 11), date(2026, 10, 11)) == 0
    # el sur no tiene dato el 13: la suma es NaN (antes ese día contaba como 0 y daba 1 mm)
    assert math.isnan(ll.desde_pasada(-59.3, -27.4, date(2026, 10, 11), date(2026, 10, 13)))


def test_si_falta_un_dia_no_inventa(tmp_path):
    grilla(tmp_path, "2026-10-12", 10, 1)
    ll = Lluvia(tmp_path)
    assert ll.faltan(date(2026, 10, 11), date(2026, 10, 13)) == ["2026-10-13"]
    with pytest.raises(LookupError):
        ll.desde_pasada(-59.3, -26.5, date(2026, 10, 11), date(2026, 10, 13))


def test_suma_una_lista_de_dias(tmp_path):
    grilla(tmp_path, "2026-09-28", 1.24, 0)
    grilla(tmp_path, "2026-09-29", 0.33, np.nan)
    grilla(tmp_path, "2026-10-05", 40, 40)           # no está en la lista: no cuenta
    ll = Lluvia(tmp_path)
    dias = [date(2026, 9, 28), date(2026, 9, 29)]
    assert ll.suma(-59.3, -26.5, dias) == 1.6        # 1,24 + 0,33 = 1,57: un decimal
    assert ll.suma(-59.3, -27.5, dias[:1]) == 0.0    # 0 medido sí es un día seco
    assert math.isnan(ll.suma(-59.3, -27.5, dias))   # celda vacía el 29: NaN, no 0
    assert ll.suma(-59.3, -26.5, []) == 0.0
    assert ll.suma(-59.3, -26.5, iter(dias)) == 1.6  # también con un generador


def test_suma_con_celda_infinita_es_nan(tmp_path):
    grilla(tmp_path, "2026-09-29", np.inf, 3)
    ll = Lluvia(tmp_path)
    assert math.isnan(ll.suma(-59.3, -26.5, [date(2026, 9, 29)]))
    assert ll.suma(-59.3, -27.5, [date(2026, 9, 29)]) == 3


def test_punto_fuera_de_la_grilla_es_nan(tmp_path):
    # 3 × 3 celdas de 0,1°, en float32 como IMERG: lon de -59,45 a -59,25 y lat de -26,75 a -26,55
    np.savez(tmp_path / "2026-09-29.npz", lon=np.array([-59.45, -59.35, -59.25], dtype="float32"),
             lat=np.array([-26.75, -26.65, -26.55], dtype="float32"),
             p=np.array([[1, 2, 3], [4, 0, 6], [7, 8, 9]], dtype="float32"))
    ll, dia = Lluvia(tmp_path), [date(2026, 9, 29)]
    assert ll.suma(-59.35, -26.65, dia) == 0             # adentro: 0 medido
    assert ll.suma(-59.21, -26.51, dia) == 9             # a menos de media celda del borde: es la celda de la esquina
    assert ll.suma(-59.20, -26.50, dia) == 9             # justo en el borde de la celda
    assert math.isnan(ll.suma(-70, -10, dia))            # antes: 7, la lluvia de la esquina más cercana
    assert math.isnan(ll.suma(-59.19, -26.55, dia))      # a más de media celda, aunque sea en un solo eje
    assert math.isnan(ll.suma(-59.35, -26.81, dia))
    assert math.isnan(ll.desde_pasada(-70, -10, date(2026, 9, 28), date(2026, 9, 29)))


def test_punto_sin_coordenadas_es_nan(tmp_path):
    grilla(tmp_path, "2026-09-29", 0, 0)
    ll, dia = Lluvia(tmp_path), [date(2026, 9, 29)]
    assert ll.suma(-59.3, -26.5, dia) == 0
    for roto in (float("nan"), float("inf"), -float("inf"), None, "-59.3"):
        # antes, NaN o inf caían en la primera celda: un día seco inventado
        assert math.isnan(ll.suma(roto, -26.5, dia)), roto
        assert math.isnan(ll.suma(-59.3, roto, dia)), roto


def test_grilla_de_una_sola_celda_usa_la_celda_de_imerg(tmp_path):
    grilla(tmp_path, "2026-09-29", 4, 4)                 # una sola columna, en lon -59,3
    ll, dia = Lluvia(tmp_path), [date(2026, 9, 29)]
    assert ll.suma(-59.34, -26.5, dia) == 4              # a 0,04°: adentro de la celda de 0,1°
    assert math.isnan(ll.suma(-59.4, -26.5, dia))        # a 0,1°: es la celda de al lado, que no está


def test_suma_si_falta_la_grilla_de_un_dia_es_error(tmp_path):
    grilla(tmp_path, "2026-09-29", 0, 0)
    with pytest.raises(LookupError, match="falta la grilla IMERG de 2026-09-28: correr python -m baqui.lluvia"):
        Lluvia(tmp_path).suma(-59.3, -26.5, [date(2026, 9, 28), date(2026, 9, 29)])
