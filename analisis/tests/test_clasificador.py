from dataclasses import replace

import numpy as np
import pytest

from baqui.clasificador import OBLIGATORIOS, Tramo, Umbrales, clasificar, ROJO, AMARILLO, VERDE, SIN_DATO, GRIS

NAN, INF = float("nan"), float("inf")
ROTOS = (None, NAN, INF, -INF, "12")


def c(**kw):
    base = dict(N=100, E=2)
    base.update(kw)
    return clasificar(Tramo(**base))


def test_seco_es_verde():
    assert c().regla == "V"


def test_pozo_de_50_m_corta_el_camino():
    # eslabón más débil: 60 m de agua en un tramo de 500 m es rojo, aunque sea el 4 %
    r = c(agua_seguida_m=60, agua_pct=4)
    assert (r.color, r.regla) == (ROJO, "R1")


def test_agua_bajo_el_monte_es_rojo():
    assert c(monte_seguido_m=80).regla == "R2"


def test_charco_corto_es_amarillo():
    assert c(agua_seguida_m=25).color == AMARILLO


def test_prudencia_cerca_del_corte():
    assert c(agua_seguida_m=46).color == ROJO  # 46 m está a menos del 10 % de 50 m


def test_rojo_viejo_sigue_rojo():
    assert c(E=8, agua_seguida_m=100, lluvia_mm=30).color == ROJO


def test_llovio_mucho_despues_es_gris():
    r = c(E=6, lluvia_mm=30)
    assert (r.color, r.regla) == (GRIS, "G")


def test_dato_fresco_con_lluvia_usa_hand():
    assert c(E=2, lluvia_mm=20, hand_m=1.4).regla == "A3"  # bajo: aguanta 15 mm
    assert c(E=2, lluvia_mm=20, hand_m=8).color == VERDE   # alto: aguanta 50 mm


def test_sin_hand_usa_25_mm():
    assert c(E=2, lluvia_mm=24).color == AMARILLO  # 24 está a menos del 10 % de 25
    assert c(E=2, lluvia_mm=10).color == VERDE


def test_suelo_mojado_es_amarillo():
    assert c(suelo_mojado_pct=40, dM=0.08).regla == "A2"


def test_suelo_mojado_sin_lluvia_ni_zona_mojada_es_sospechoso():
    r = c(suelo_mojado_pct=40, dM=0.0, lluvia_mm=0)
    assert (r.regla, r.confianza) == ("A2b", "baja")


def test_asfalto_no_se_pinta_por_barro():
    assert c(T="asfalto", suelo_mojado_pct=80, lluvia_mm=40).color == VERDE


def test_asfalto_con_agua_es_rojo():
    assert c(T="asfalto", agua_seguida_m=70).color == ROJO


def test_ripio_aguanta_mas():
    assert c(T="ripio", E=2, lluvia_mm=20, hand_m=1.4).color == VERDE  # 15 x 1,5 = 22,5 mm


def test_sin_dato_por_calidad():
    assert c(N=5, agua_seguida_m=100).color == SIN_DATO
    assert c(misma_orbita=False).color == SIN_DATO
    assert c(E=15).color == SIN_DATO


def test_laguna_de_siempre_avisa():
    assert c(Wp=40).avisos


def test_motivo_explica_numeros():
    r = c(E=2, lluvia_mm=35, hand_m=1.4, fecha_pasada="11/10")
    assert "35 mm" in r.motivo and "15 mm" in r.motivo and "11/10" in r.motivo


def test_confianza():
    assert c(agua_seguida_m=60, otra_pasada_coincide=True).confianza == "alta"
    assert c(agua_seguida_m=60).confianza == "media"
    assert c(E=6, agua_seguida_m=60).confianza == "baja"


def test_nunca_verde_con_agua_seguida_o_lluvia_alta_en_bajo():
    for agua in (0, 20, 50, 200):
        for lluvia in (0, 14, 40):
            for E in (1, 3, 6, 10):
                r = c(agua_seguida_m=agua, lluvia_mm=lluvia, E=E, hand_m=1)
                if agua >= 50:
                    assert r.color == ROJO
                if r.color == VERDE:
                    assert agua < 18 and lluvia < 13.5, (agua, lluvia, E, r)


# --- Un dato vacío o roto nunca puede dar verde ---

@pytest.mark.parametrize("campo", list(OBLIGATORIOS))
@pytest.mark.parametrize("roto", ROTOS)
def test_dato_roto_es_sin_dato_aunque_otra_variable_de_rojo(campo, roto):
    for otras in ({}, {"agua_seguida_m": 100.0}, {"suelo_mojado_pct": 80.0, "lluvia_mm": 60.0}):
        r = c(**{**otras, campo: roto})
        assert (r.color, r.regla, r.confianza) == (SIN_DATO, "S", "—"), (campo, roto, r)
        assert r.motivo.startswith("falta el dato de: ") and OBLIGATORIOS[campo] in r.motivo


def test_los_dos_casos_que_daban_verde():
    r = clasificar(Tramo(N=100, E=1, agua_seguida_m=NAN, suelo_mojado_pct=NAN))
    assert r.color == SIN_DATO and r.motivo == "falta el dato de: agua sobre el camino, suelo mojado"
    r = clasificar(Tramo(N=NAN, E=NAN))
    assert r.color == SIN_DATO and r.motivo == "falta el dato de: píxeles válidos, días desde la pasada"


def test_nunca_verde_con_dos_datos_rotos_a_la_vez():
    for a in OBLIGATORIOS:
        for b in OBLIGATORIOS:
            for roto in ROTOS:
                assert c(**{a: roto, b: NAN}).color == SIN_DATO, (a, b, roto)


def test_agua_de_siempre_rota_no_avisa_ni_rompe():
    r = c(Wp=NAN, agua_seguida_m=200)
    assert r.color == SIN_DATO and r.avisos == []


def test_numeros_de_numpy_son_numeros():
    r = clasificar(Tramo(N=np.int64(100), E=np.float32(2), agua_seguida_m=np.float32(60), hand_m=np.float64(1)))
    assert (r.color, r.regla) == (ROJO, "R1")


@pytest.mark.parametrize("roto", (NAN, INF, -INF, "1.4"))
def test_hand_roto_es_como_no_tener_hand(roto):
    assert Umbrales().aguanta(roto) == Umbrales().aguanta(None) == 25   # antes NaN daba 50 mm, lo más permisivo
    t = Tramo(N=100, E=2, lluvia_mm=24, hand_m=roto)
    r = clasificar(t)
    assert replace(r, avisos=[]) == c(lluvia_mm=24) and r.regla == "A3" and "sin dato de altura" in r.motivo
    assert r.avisos == ["dato de altura (HAND) roto: se sigue sin él"]   # se descarta, pero no en silencio
    assert t.hand_m is roto                                              # el Tramo que entra no se toca


@pytest.mark.parametrize("roto", (NAN, INF, -INF, "0.08"))
def test_dm_roto_es_como_no_tener_dm(roto):
    t = Tramo(N=100, E=2, suelo_mojado_pct=40, dM=roto)
    r = clasificar(t)
    assert replace(r, avisos=[]) == c(suelo_mojado_pct=40) and (r.regla, r.confianza) == ("A2", "media")
    assert r.avisos == ["dato de humedad de la zona roto: se sigue sin él"]
    assert t.dM is roto


def test_sin_hand_ni_dm_no_hay_aviso():
    assert c(lluvia_mm=24).avisos == [] and c(suelo_mojado_pct=40, hand_m=1.4, dM=0.08).avisos == []


def test_numero_envuelto_en_un_arreglo_de_numpy_es_un_numero():
    # np.asarray y .values de xarray devuelven un arreglo de 0 dimensiones: es un dato, no un roto
    r = clasificar(Tramo(N=100, E=2, lluvia_mm=14, hand_m=np.array(1.0)))
    assert (r.regla, r.avisos) == ("A3", []) and "a 1 m del bajo" in r.motivo     # antes: verde, como sin HAND
    r = clasificar(Tramo(N=100, E=2, suelo_mojado_pct=40, dM=np.array(0.0)))
    assert (r.regla, r.confianza, r.avisos) == ("A2b", "baja", [])                # antes: A2, confianza media
    r = clasificar(Tramo(N=np.array(100), E=np.array(2.0), agua_seguida_m=np.array(60.0), lluvia_mm=np.array(0.0)))
    assert (r.color, r.regla, r.motivo) == (ROJO, "R1", "60 m seguidos con agua (radar)")   # antes: sin dato
    assert c(N=np.array(5)).motivo == "pocos píxeles (5)"
    # envuelto, pero vacío o roto: sigue siendo sin dato
    for roto in (np.array(NAN), np.array(INF), np.array("100"), np.array(None), np.array([100.0])):
        assert c(agua_seguida_m=roto).color == SIN_DATO, roto
    assert c(lluvia_mm=24, hand_m=np.array([1.4])).avisos                         # una lista no es una altura


# --- Las banderas de calidad valen solo si son True ---

@pytest.mark.parametrize("bandera", ("misma_orbita", "misma_version", "referencia_seca"))
@pytest.mark.parametrize("roto", (False, None, NAN, INF, "True", "False", "no", np.False_, np.array(NAN)))
def test_bandera_que_no_es_true_es_sin_dato(bandera, roto):
    # antes, NaN y los textos (lo que devuelve un CSV) pasaban por "sí" y el tramo salía verde
    for otras in ({}, {"agua_seguida_m": 100.0}):
        r = c(**{**otras, bandera: roto})
        assert (r.color, r.regla, r.confianza) == (SIN_DATO, "S", "—"), (bandera, roto, r)


def test_bandera_true_de_numpy_vale():
    assert c(misma_orbita=np.True_, misma_version=np.array(True), referencia_seca=np.bool_(True)) == c()


def test_otra_pasada_solo_cuenta_si_es_true_o_false():
    for roto in (NAN, INF, "False", "no", "True"):
        assert c(otra_pasada_coincide=roto).confianza == "media", roto            # antes: "alta"
    assert c(otra_pasada_coincide=NAN, dM=0.08).confianza == "alta"               # la zona sí confirma
    assert c(otra_pasada_coincide=np.True_).confianza == "alta"
    assert c(otra_pasada_coincide=np.False_).confianza == "baja"                  # antes: "media"
    assert c(otra_pasada_coincide=False, dM=0.08).confianza == "baja"


# --- La referencia tiene que ser seca ---

def test_referencia_con_lluvia_es_sin_dato():
    r = c(lluvia_referencia_mm=2.0)                                      # justo en el corte
    assert (r.color, r.regla) == (SIN_DATO, "S")
    assert r.motivo == "la fecha de referencia no es seca (2 mm de lluvia)"
    assert c(agua_seguida_m=100, lluvia_referencia_mm=7.5).color == SIN_DATO   # gana aunque haya rojo
    assert c(N=5, lluvia_referencia_mm=7.5).motivo == "la fecha de referencia no es seca (7.5 mm de lluvia); pocos píxeles (5)"


def test_referencia_marcada_como_no_seca_es_sin_dato():
    assert c(referencia_seca=False).motivo == "la fecha de referencia no es seca"
    assert c(referencia_seca=False, lluvia_referencia_mm=0.0).color == SIN_DATO


def test_referencia_seca_o_sin_comprobar_no_cambia_nada():
    assert c(lluvia_referencia_mm=None) == c() == c(lluvia_referencia_mm=0.0)
    assert c(lluvia_referencia_mm=1.9).color == VERDE                    # corte directo, sin el margen del 10 %
    assert c(agua_seguida_m=60, lluvia_referencia_mm=1.9).regla == "R1"
    assert clasificar(Tramo(N=100, E=2, lluvia_referencia_mm=3.0), Umbrales(lluvia_referencia=5.0)).color == VERDE


@pytest.mark.parametrize("roto", (NAN, INF, -INF, "2"))
def test_lluvia_de_la_referencia_sin_dato_es_sin_dato(roto):
    r = c(lluvia_referencia_mm=roto)
    assert (r.color, r.regla) == (SIN_DATO, "S")
    assert r.motivo == "falta el dato de: lluvia de la fecha de referencia"


def test_valor_enmascarado_de_numpy_es_sin_dato():
    import numpy as np
    for campo in ("N", "agua_seguida_m", "lluvia_mm"):
        assert c(**{campo: np.ma.masked}).color == SIN_DATO


def test_dato_faltante_no_tapa_la_causa_de_fondo():
    r = c(N=0, lluvia_referencia_mm=NAN)
    assert r.color == SIN_DATO
    assert r.motivo == "falta el dato de: lluvia de la fecha de referencia; pocos píxeles (0)"
