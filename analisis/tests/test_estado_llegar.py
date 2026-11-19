import math

import networkx as nx
import numpy as np
from baqui.estado import Dia, Parametros, color, dias_hasta_pasar, evolucionar, desde_radar, manana_sin_lluvia, ROJO, AMARILLO, VERDE, SIN_DATO
from baqui.llegar import mejor_recorrido

F = [f"{d}/10" for d in range(11, 21)]


def test_radar_manda_el_dia_de_la_pasada():
    s = evolucionar(F[:1], [0], {"11/10": desde_radar(3.4)})
    assert s.hoy.color == ROJO and s.hoy.indice == 100


def test_si_sale_el_sol_se_seca():
    s = evolucionar(F, [0] * 10, {"11/10": desde_radar(2.4)})  # índice 80
    colores = [d.color for d in s.dias]
    assert colores[0] == ROJO and colores[-1] == VERDE
    assert all(a.indice >= b.indice for a, b in zip(s.dias, s.dias[1:]))   # nunca sube sin lluvia


def test_si_sigue_lloviendo_empeora():
    s = evolucionar(F[:4], [0, 10, 10, 10], {"11/10": desde_radar(1.2)})   # arranca en 40
    assert s.dias[0].color == AMARILLO and s.hoy.color == ROJO


def test_bajo_se_seca_mas_lento_que_loma():
    lluvia = [0] * 10
    bajo = evolucionar(F, lluvia, {"11/10": 80.0}, hand_m=1)
    loma = evolucionar(F, lluvia, {"11/10": 80.0}, hand_m=8)
    assert bajo.dias[4].indice > loma.dias[4].indice


def test_manana_si_no_llueve():
    s = evolucionar(F[:3], [0, 0, 0], {"11/10": 72.0})
    assert manana_sin_lluvia(s.hoy) in (AMARILLO, VERDE)


def test_sin_radar_mucho_tiempo_es_sin_dato():
    fechas = [str(i) for i in range(15)]
    s = evolucionar(fechas, [0] * 15, {"0": 50.0})
    assert s.hoy.color == SIN_DATO


def test_antes_del_primer_radar_es_sin_dato():
    s = evolucionar(F[:2], [0, 0], {"12/10": 10.0})
    assert s.dias[0].color == SIN_DATO and s.dias[1].color == VERDE


def test_agua_es_barro_100():
    assert desde_radar(0.5, agua_seguida_m=80) == 100


def red(colores):
    """Ruta 'R' (asfalto) -> A -> destino 'D' por dos caminos: corto (A-D) y largo (A-B-D)."""
    G = nx.Graph()
    G.add_edge("R", "A", color="transitable", largo_m=5000)
    G.add_edge("A", "D", color=colores[0], largo_m=2000)
    G.add_edge("A", "B", color=colores[1], largo_m=4000)
    G.add_edge("B", "D", color=colores[2], largo_m=4000)
    return G


def test_llegas_por_el_corto_si_todo_verde():
    r = mejor_recorrido(red(["transitable"] * 3), "R", "D")
    assert r["respuesta"] == "llegás" and r["largo_m"] == 7000


def test_si_el_corto_esta_cortado_va_por_el_largo():
    r = mejor_recorrido(red(["intransitable", "transitable", "transitable"]), "R", "D")
    assert r["respuesta"] == "llegás" and r["nodos"] == ["R", "A", "B", "D"]


def test_prefiere_largo_verde_a_corto_con_barro():
    r = mejor_recorrido(red(["con barro", "transitable", "transitable"]), "R", "D")
    assert r["respuesta"] == "llegás" and r["largo_m"] == 13000


def test_llegas_con_barro():
    r = mejor_recorrido(red(["con barro", "intransitable", "transitable"]), "R", "D")
    assert r["respuesta"] == "llegás con barro" and r["tramo_peor"] == ("A", "D")


def test_no_llegas_si_todos_cortados():
    r = mejor_recorrido(red(["intransitable", "intransitable", "transitable"]), "R", "D")
    assert r["respuesta"] == "no llegás"


def test_cuando_voy_a_poder_pasar():
    from baqui.estado import dias_hasta_pasar
    s = evolucionar(F[:1], [0], {"11/10": 90.0})
    bajo = dias_hasta_pasar(s.hoy, hand_m=1)
    loma = dias_hasta_pasar(s.hoy, hand_m=8)
    assert bajo > loma > 0
    assert dias_hasta_pasar(evolucionar(F[:1], [0], {"11/10": 10.0}).hoy) == 0


def test_un_solo_camino_vale_su_peor_tramo():
    G = nx.path_graph(["ruta", "t1", "t2", "campo"])
    for (u, v), c in zip(G.edges, ["transitable", "con barro", "transitable"]):
        G[u][v].update(color=c, largo_m=1000)
    r = mejor_recorrido(G, "ruta", "campo")
    assert r["respuesta"] == "llegás con barro" and r["tramo_peor"] == ("t1", "t2")


def test_indice_roto_nunca_es_transitable():
    for roto in (float("nan"), float("inf"), None):
        assert color(roto) == SIN_DATO
    s = evolucionar(F[:3], [0, 0, 0], {"11/10": desde_radar(float("nan"))})
    assert all(d.color == SIN_DATO for d in s.dias)
    assert manana_sin_lluvia(s.hoy) == SIN_DATO and dias_hasta_pasar(s.hoy) is None


def test_dato_viejo_cuenta_como_sin_dato():
    r = mejor_recorrido(red(["dato viejo", "intransitable", "transitable"]), "R", "D")
    assert r["respuesta"] == "sin dato" and r["color_peor"] == "dato viejo"


def test_prefiere_verde_a_dato_viejo_y_color_desconocido_no_rompe():
    r = mejor_recorrido(red(["dato viejo", "transitable", "transitable"]), "R", "D")
    assert r["respuesta"] == "llegás" and r["nodos"] == ["R", "A", "B", "D"]
    assert mejor_recorrido(red(["???", "intransitable", "transitable"]), "R", "D")["respuesta"] == "sin dato"


# --- Un dato vacío o roto nunca puede dar verde ---

NAN, INF = float("nan"), float("inf")


def test_lluvia_sin_dato_no_cuenta_como_dia_seco():
    for roto in (None, NAN, INF, -INF, "5"):
        s = evolucionar(F[:5], [0, 0, roto, 0, 30], {"11/10": 20.0})
        assert [d.color for d in s.dias] == [VERDE, VERDE, SIN_DATO, SIN_DATO, SIN_DATO], roto
        # ni el día seco ni la lluvia de después lo "arreglan": sigue sin dato y con su motivo
        assert all(math.isnan(d.indice) and d.motivo == "falta el dato de lluvia" for d in s.dias[2:])
        assert manana_sin_lluvia(s.hoy) == SIN_DATO and dias_hasta_pasar(s.hoy) is None


def test_la_pasada_siguiente_vuelve_a_fijar_el_indice():
    s = evolucionar(F[:4], [0, None, 0, 0], {"11/10": 20.0, "13/10": 40.0})
    assert [d.color for d in s.dias] == [VERDE, SIN_DATO, AMARILLO, AMARILLO]
    assert s.dias[2].indice == 40 and s.dias[2].motivo == "radar del 13/10" and s.dias[2].dias_desde_radar == 0
    assert s.hoy.motivo == "día seco: se seca"


def test_lluvia_sin_dato_el_dia_de_la_pasada_no_importa():
    s = evolucionar(F[:2], [NAN, 0], {"11/10": 20.0})    # ese día manda el radar
    assert [d.color for d in s.dias] == [VERDE, VERDE]


def test_radar_sin_dato_y_despues_llueve_sigue_sin_dato():
    # antes, min(100, NaN + lluvia) daba 100: un rojo inventado que después "se secaba" hasta verde
    s = evolucionar([str(i) for i in range(13)], [0, 10] + [0] * 11, {"0": desde_radar(NAN)})
    assert all(d.color == SIN_DATO and math.isnan(d.indice) for d in s.dias)


def test_lluvia_con_numeros_de_numpy_no_se_pierde():
    # IMERG viene en float32: un número de numpy no es un dato roto
    con_numpy = evolucionar(F[:4], np.array([0, 0, 10, 0], dtype="float32"), {"11/10": 20.0})
    comun = evolucionar(F[:4], [0, 0, 10, 0], {"11/10": 20.0})
    assert [d.color for d in con_numpy.dias] == [d.color for d in comun.dias] == [VERDE, VERDE, ROJO, AMARILLO]
    assert color(np.float32(80)) == ROJO and color(np.float32("nan")) == SIN_DATO


def test_numero_envuelto_en_un_arreglo_de_numpy_es_un_numero():
    # np.asarray y .values de xarray devuelven un arreglo de 0 dimensiones: es un dato, no un roto
    lluvia = [0, 10, 0, 0, 0]
    bajo = evolucionar(F[:5], lluvia, {"11/10": 10.0}, hand_m=1.0)
    assert bajo.dias[1].color == ROJO and bajo.dias[1].indice == 76.7
    assert evolucionar(F[:5], lluvia, {"11/10": 10.0}, hand_m=np.array(1.0)) == bajo     # antes: con barro (50), como sin HAND
    assert evolucionar(F[:5], [np.array(mm) for mm in lluvia], {"11/10": np.array(10.0)}, hand_m=1.0) == bajo
    assert Parametros().aguanta(np.array(1.0)) == 15 and Parametros().secado_diario(np.array(8.0)) == Parametros().secado_diario(8)
    assert color(np.array(80.0)) == ROJO and desde_radar(np.array(1.2), np.array(0.0)) == 40
    # envuelto, pero vacío o roto: sigue siendo sin dato
    for roto in (np.array(NAN), np.array(INF), np.array("80"), np.array([80.0])):
        assert color(roto) == SIN_DATO and Parametros().aguanta(roto) == 25, roto
    assert evolucionar(F[:3], [0, np.array(NAN), 0], {"11/10": 20.0}).hoy.color == SIN_DATO


def test_hand_roto_es_como_no_tener_hand():
    p, lluvia = Parametros(), [0, 10] + [0] * 8
    sin_hand = evolucionar(F, lluvia, {"11/10": 50.0})
    for roto in (NAN, INF, -INF, "1"):
        assert p.aguanta(roto) == p.aguanta(None) == 25              # antes NaN aguantaba 50 mm
        assert p.secado_diario(roto) == p.secado_diario(None)        # antes inf secaba como una loma
        assert evolucionar(F, lluvia, {"11/10": 50.0}, hand_m=roto) == sin_hand
        assert dias_hasta_pasar(sin_hand.dias[1], hand_m=roto) == dias_hasta_pasar(sin_hand.dias[1])
        assert manana_sin_lluvia(sin_hand.dias[1], hand_m=roto) == manana_sin_lluvia(sin_hand.dias[1])


def test_agua_sin_dato_es_indice_sin_dato():
    for roto in (None, NAN, INF, -INF, "80"):
        assert math.isnan(desde_radar(2.4, agua_seguida_m=roto))
        assert color(desde_radar(0.0, agua_seguida_m=roto)) == SIN_DATO   # antes: 0, o sea verde
    assert desde_radar(NAN, agua_seguida_m=80) == 100                    # el agua medida sigue mandando
    assert desde_radar(1.2, agua_seguida_m=0) == 40


def test_indice_roto_no_da_pronostico():
    s = evolucionar(F[:3], [0, NAN, 0], {"11/10": 20.0})
    assert s.hoy.color == SIN_DATO
    assert dias_hasta_pasar(s.hoy) is None and manana_sin_lluvia(s.hoy) == SIN_DATO
    # aunque el día venga armado a mano con un color que no corresponde
    for roto in (NAN, INF):
        mal = Dia("11/10", roto, VERDE, 0, "armado a mano")
        assert dias_hasta_pasar(mal) is None and manana_sin_lluvia(mal) == SIN_DATO


def test_valor_enmascarado_de_numpy_no_es_un_numero():
    import numpy as np
    assert color(np.ma.masked) == SIN_DATO
    s = evolucionar(F[:3], [0, np.ma.masked, 0], {"11/10": desde_radar(0.5)})
    assert s.hoy.color == SIN_DATO
