from dataclasses import fields
import pytest
from baqui.auditoria import auditar, piso, casos_necesarios, informe
from baqui.sensibilidad import sensibilidad, NO_SE_MUEVEN
from baqui.clasificador import Tramo, Umbrales

def casos(filas):
    return [dict(zip(["tramo", "fecha", "evento", "baqui", "real", "confianza"], f)) for f in filas]

def test_piso_20_de_20():
    assert round(piso(20, 20), 2) == 0.86

def test_casos_necesarios():
    assert casos_necesarios(0.95) == 59
    assert casos_necesarios(0.90) == 29

def test_escapado_se_cuenta_aparte():
    r = auditar(casos([
        ("1", "11/10", "A", "transitable", "no pasé", "media"),
        ("2", "11/10", "A", "intransitable", "no pasé", "alta"),
        ("3", "11/10", "A", "transitable", "pasé", "alta"),
    ]))
    assert r["escapados"] == 1 and r["no_pase"] == 2 and len(r["errores"]) == 1

def test_evento_de_calibracion_no_cuenta():
    r = auditar(casos([
        ("1", "11/10", "cal", "transitable", "pasé", "alta"),
        ("2", "19/10", "prueba", "con barro", "con dificultad", "alta"),
    ]), excluir_evento="cal")
    assert r["n"] == 1

def test_sin_dato_baja_la_cobertura_no_el_acierto():
    r = auditar(casos([
        ("1", "11/10", "A", "sin dato", "no pasé", "—"),
        ("2", "11/10", "A", "transitable", "pasé", "alta"),
    ]))
    assert r["acierto"] == 1 and r["cobertura"] == 0.5

def test_dato_viejo_cuenta_como_sin_dato():
    r = auditar(casos([
        ("1", "23/10", "A", "dato viejo", "no pasé", "baja"),
        ("2", "23/10", "A", "transitable", "pasé", "alta"),
    ]))
    assert r["n"] == 1 and r["sin_dato"] == 1 and r["cobertura"] == 0.5
    assert r["acierto"] == 1 and r["no_pase"] == 0 and not r["errores"]
    assert "sin dato o dato viejo: 1" in informe(r)

def test_informe_dice_los_cortes_sin_color():
    # 9 cortes reales, pero 8 cayeron en "dato viejo": el informe no los puede callar
    r = auditar(casos([
        ("1", "23/10", "A", "intransitable", "no pasé", "alta"),
        ("2", "23/10", "A", "transitable", "pasé", "alta"),
        ("3", "23/10", "A", "sin dato", "pasé", "—"),
    ] + [(str(i), "23/10", "A", "dato viejo", "no pasé", "baja") for i in range(4, 12)]))
    assert r["no_pase"] == 1 and r["sin_dato"] == 9 and r["sin_dato_no_pase"] == 8
    texto = informe(r)
    assert "sin dato o dato viejo: 9 (no pasó: 8)" in texto and "Caminos cortados con color: 1" in texto

def test_valor_desconocido_tira_error():
    for baqui, real in [("violeta", "pasé"), ("transitable", "más o menos")]:
        with pytest.raises(ValueError, match="valor raro"):
            auditar(casos([("1", "11/10", "A", baqui, real, "alta")]))

def test_informe_dice_garantia():
    r = auditar(casos([(str(i), "11/10", "A", "transitable", "pasé", "alta") for i in range(20)]))
    assert "al menos 86 %" in informe(r)

def test_sensibilidad_detecta_umbral_fragil():
    tramos = [Tramo(N=100, E=2, suelo_mojado_pct=30)] * 5 + [Tramo(N=100, E=2)] * 5
    s = sensibilidad(tramos)
    assert s["suelo_mojado_pct"] > 0 and s["agua_siempre"] == 0

def test_no_se_mueven_existen_en_umbrales():
    # un nombre mal escrito no saca nada de la lista y nadie se entera
    assert NO_SE_MUEVEN <= {f.name for f in fields(Umbrales)}

def test_sensibilidad_mueve_dias_frescos():
    # dias_frescos decide entre un color y "dato viejo" (regla G): con 3,2 días los dos tramos de E=4 pasan a gris
    tramos = [Tramo(N=100, E=4, lluvia_mm=19), Tramo(N=100, E=4, lluvia_mm=30), Tramo(N=100, E=5, lluvia_mm=19),
              Tramo(N=100, E=2, agua_seguida_m=46), Tramo(N=100, E=2, suelo_mojado_pct=28)]
    s = sensibilidad(tramos)
    assert s["dias_frescos"] == 0.4 and max(s.values()) == 0.4
    # los cortes de calidad del dato y el margen quedan afuera
    assert not {"min_pixeles", "max_dias", "lluvia_referencia", "margen"} & set(s)
    from dataclasses import fields
    from baqui.clasificador import Umbrales
    from baqui.sensibilidad import NO_SE_MUEVEN
    assert set(s) == {f.name for f in fields(Umbrales)} - NO_SE_MUEVEN


def test_real_mal_escrito_en_un_caso_sin_color_tira_error():
    import pytest
    with pytest.raises(ValueError):
        auditar(casos([("1", "11/10", "A", "dato viejo", "No pasé", "—")]))
    assert auditar(casos([("1", "11/10", "A", "sin dato", "", "—")]))["sin_dato"] == 1
