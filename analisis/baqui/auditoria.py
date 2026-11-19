"""Auditoría de Baqui: cruza lo que dijo el semáforo con lo que pasó de verdad.

Entrada: un CSV con columnas
    tramo, fecha, evento, baqui, real, confianza
  baqui: transitable | con barro | intransitable | sin dato | dato viejo
  real:  pasé | con dificultad | no pasé
"sin dato" y "dato viejo" no cuentan para el acierto y bajan la cobertura:
ahí Baqui no afirmó nada (en "dato viejo" dijo "preguntá antes de salir").
El informe dice cuántos de esos eran caminos cortados: no entran en la detección.
Uso:  python -m baqui.auditoria casos.csv [--evento-calibracion 2026-10-09]
"""
import csv, sys
from collections import Counter
from scipy.stats import beta

COLORES = ["transitable", "con barro", "intransitable"]
SIN_COLOR = {"sin dato", "dato viejo"}  # Baqui no afirmó nada
REALES = ["pasé", "con dificultad", "no pasé"]
ACIERTO = {("transitable", "pasé"), ("con barro", "con dificultad"), ("intransitable", "no pasé")}
NIVEL = 0.95  # garantía con 95 % de confianza estadística


def piso(aciertos, n, nivel=NIVEL):
    """Lo mínimo que se puede garantizar (Clopper-Pearson, una cola)."""
    if n == 0:
        return 0.0
    if aciertos == 0:
        return 0.0
    return float(beta.ppf(1 - nivel, aciertos, n - aciertos + 1))


def techo(eventos, n, nivel=NIVEL):
    """Lo máximo que puede valer una tasa de error (Clopper-Pearson, una cola)."""
    if n == 0:
        return 1.0
    if eventos == n:
        return 1.0
    return float(beta.ppf(nivel, eventos + 1, n - eventos))


def casos_necesarios(meta, errores=0, nivel=NIVEL):
    n = errores + 1
    while piso(n - errores, n, nivel) < meta:
        n += 1
    return n


def leer(ruta):
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def auditar(casos, excluir_evento=None):
    """Devuelve las medidas. Los casos del evento de calibración no cuentan."""
    usados = [c for c in casos if c.get("evento") != excluir_evento]
    sin_dato = [c for c in usados if c["baqui"] in SIN_COLOR]
    con_color = [c for c in usados if c["baqui"] not in SIN_COLOR]
    for c in con_color:
        if c["baqui"] not in COLORES or c["real"] not in REALES:
            raise ValueError(f"valor raro en el caso {c}")
    for c in sin_dato:   # sin color, "real" puede venir vacío, pero un texto mal escrito no se cuenta en silencio
        if c["real"] not in REALES and c["real"] != "":
            raise ValueError(f"valor raro en el caso {c}")
    m = Counter((c["baqui"], c["real"]) for c in con_color)
    n = len(con_color)
    ok = sum(v for k, v in m.items() if k in ACIERTO)
    no_pase = [c for c in con_color if c["real"] == "no pasé"]
    escapados = [c for c in no_pase if c["baqui"] == "transitable"]
    detectados = [c for c in no_pase if c["baqui"] == "intransitable"]
    verdes = [c for c in con_color if c["baqui"] == "transitable"]
    return {
        "n": n,
        "sin_dato": len(sin_dato),
        "sin_dato_no_pase": sum(c["real"] == "no pasé" for c in sin_dato),  # cortes reales que quedaron sin color
        "cobertura": n / len(usados) if usados else 0.0,
        "matriz": m,
        "acierto": ok / n if n else 0.0,
        "acierto_garantizado": piso(ok, n),
        "no_pase": len(no_pase),
        "escapados": len(escapados),
        "escapados_max": techo(len(escapados), len(no_pase)),
        "deteccion": len(detectados) / len(no_pase) if no_pase else 0.0,
        "deteccion_garantizada": piso(len(detectados), len(no_pase)),
        "verdes": len(verdes),
        "verde_falla_max": techo(sum(c["real"] == "no pasé" for c in verdes), len(verdes)),
        "errores": [c for c in con_color if (c["baqui"], c["real"]) not in ACIERTO],
    }


def informe(r):
    p = lambda x: f"{100 * x:.0f} %"
    l = [f"Casos con color: {r['n']}   sin dato o dato viejo: {r['sin_dato']} (no pasó: {r['sin_dato_no_pase']})"
         f"   cobertura: {p(r['cobertura'])}", "",
         "Baqui / real      " + "".join(f"{x:>16}" for x in REALES)]
    for c in COLORES:
        l.append(f"{c:<18}" + "".join(f"{r['matriz'][(c, x)]:>16}" for x in REALES))
    l += ["",
          f"Acierto medido: {p(r['acierto'])}   garantizado (95 %): al menos {p(r['acierto_garantizado'])}",
          f"Caminos cortados con color: {r['no_pase']}   detectados en rojo: {p(r['deteccion'])}"
          f"   garantizado: al menos {p(r['deteccion_garantizada'])}",
          f"ESCAPADOS (verde y no pasó): {r['escapados']}"
          f"   como mucho {p(r['escapados_max'])} de los caminos cortados",
          f"Si Baqui dice verde, la chance de que no se pueda pasar es como mucho {p(r['verde_falla_max'])}"
          f" ({r['verdes']} verdes)", "",
          f"Errores para revisar uno por uno: {len(r['errores'])}"]
    for c in r["errores"]:
        l.append(f"  - tramo {c['tramo']} {c['fecha']}: Baqui dijo {c['baqui']}, pasó {c['real']}")
    return "\n".join(l)


if __name__ == "__main__":
    args = sys.argv[1:]
    excluir = None
    if "--evento-calibracion" in args:
        i = args.index("--evento-calibracion")
        excluir = args[i + 1]
        del args[i:i + 2]
    print(informe(auditar(leer(args[0]), excluir)))
