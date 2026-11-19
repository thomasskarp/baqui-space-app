"""¿Qué tan frágil es el color? Mueve cada umbral ±20 % y cuenta cuántos tramos cambian."""
from dataclasses import fields, replace
from baqui.clasificador import Umbrales, clasificar

# No se mueven los cortes de calidad del dato (píxeles, edad máxima del radar, lluvia de la fecha de referencia)
# ni el margen de prudencia: dicen si el dato sirve, no cómo está el camino.
# "dias_frescos" sí se mueve: decide entre un color y "dato viejo" (regla G).
NO_SE_MUEVEN = {"min_pixeles", "max_dias", "lluvia_referencia", "margen"}


def sensibilidad(tramos, u=Umbrales(), cambio=0.20):
    base = [clasificar(t, u).color for t in tramos]
    salida = {}
    for f in fields(Umbrales):
        if f.name in NO_SE_MUEVEN:
            continue
        v = getattr(u, f.name)
        cambian = 0
        for factor in (1 - cambio, 1 + cambio):
            u2 = replace(u, **{f.name: v * factor})
            cambian = max(cambian, sum(clasificar(t, u2).color != b for t, b in zip(tramos, base)))
        salida[f.name] = cambian / len(tramos) if tramos else 0.0
    return dict(sorted(salida.items(), key=lambda kv: -kv[1]))
