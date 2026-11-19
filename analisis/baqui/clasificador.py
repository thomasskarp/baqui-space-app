"""Semáforo de Baqui (versión 2).

Base: docs/algoritmo.md (5 variables, eslabón más débil, umbral de lluvia
por HAND). Se le suman las reglas de seguridad de docs/clasificacion-semaforo.md
(calidad del dato, prudencia cerca de los cortes, contradicciones, asfalto).
Orden: sin dato -> rojo -> gris -> amarillo -> verde. La primera que se cumple decide.
Un dato vacío o roto (None, NaN, inf, texto) da "sin dato" aunque otra variable dé rojo: nunca verde.
"""
import math
import numbers
from dataclasses import dataclass, field, replace

SIN_DATO, ROJO, GRIS, AMARILLO, VERDE = "sin dato", "intransitable", "dato viejo", "con barro", "transitable"


@dataclass
class Umbrales:
    """Valores de arranque. Se calibran con un evento y se prueban con otro."""
    min_pixeles: int = 20
    max_dias: int = 12                # más que una vuelta completa de NISAR: no se usa
    dias_frescos: int = 4
    agua_seguida_rojo: float = 50.0   # m seguidos de agua sobre el camino
    agua_seguida_amarillo: float = 20.0
    agua_pct_amarillo: float = 3.0    # % de la franja con agua nueva
    lluvia_gris: float = 20.0         # mm desde la pasada, con dato no fresco
    suelo_mojado_pct: float = 30.0    # % de la franja con el eco 1 a 3 dB más alto
    dm_contradice: float = 0.02       # la zona (CYGNSS/SMAP) casi no se mojó
    agua_siempre: float = 30.0        # % de laguna en la franja: revisar el mapa
    margen: float = 0.10              # a menos del 10 % de un corte, el color más grave
    factor_ripio: float = 1.5
    lluvia_sin_hand: float = 25.0     # mm, si todavía no hay HAND
    lluvia_referencia: float = 2.0    # mm entre el día anterior y el día de la referencia: con esto o más, la referencia no es seca (valor de arranque)

    def aguanta(self, hand_m):
        """Lluvia que aguanta el tramo según qué tan alto está (la esponja)."""
        if not _es_numero(hand_m):    # None, NaN o inf: sin dato de altura
            return self.lluvia_sin_hand
        if hand_m < 2:
            return 15.0
        if hand_m <= 5:
            return 30.0
        return 50.0


@dataclass
class Tramo:
    N: int                         # píxeles válidos en la franja
    E: float                       # días desde la pasada del radar
    agua_seguida_m: float = 0.0    # var. 1: tramo seguido más largo con agua nueva
    monte_seguido_m: float = 0.0   # var. 2: tramo seguido más largo con agua bajo el monte
    agua_pct: float = 0.0          # % de la franja con agua nueva
    suelo_mojado_pct: float = 0.0  # var. 3
    lluvia_mm: float = 0.0         # var. 4: lluvia desde la pasada
    hand_m: float | None = None    # var. 5
    dM: float | None = None        # humedad de zona (CYGNSS/SMAP) desde la fecha seca
    Wp: float = 0.0                # % agua de siempre
    T: str = "tierra"              # tierra, ripio o asfalto
    # Banderas de calidad: solo True deja seguir. False, None (no se sabe), NaN o un texto: sin dato.
    misma_orbita: bool = True
    misma_version: bool = True
    referencia_seca: bool = True
    otra_pasada_coincide: bool | None = None
    fecha_pasada: str = ""
    # mm de lluvia IMERG entre el día anterior a la referencia y el día de la referencia.
    # None = quien llama no lo comprobó; NaN = lo intentó y no hay dato. En un JSON el NaN se guarda
    # como null y vuelve como None: quien mide tiene que dejar también referencia_seca en False o None.
    lluvia_referencia_mm: float | None = None


@dataclass
class Resultado:
    color: str
    regla: str
    motivo: str
    confianza: str = ""
    avisos: list = field(default_factory=list)


# Datos que no pueden faltar, con el nombre que se le muestra a la gente
OBLIGATORIOS = {
    "N": "píxeles válidos", "E": "días desde la pasada", "agua_seguida_m": "agua sobre el camino",
    "monte_seguido_m": "agua bajo el monte", "agua_pct": "agua en la franja", "suelo_mojado_pct": "suelo mojado",
    "lluvia_mm": "lluvia desde la pasada", "Wp": "agua de siempre",
}


def _suelto(x):
    """Un valor de numpy envuelto en un arreglo de 0 dimensiones (lo que dan np.asarray o xarray) se saca: es un solo valor."""
    if getattr(x, "ndim", None) != 0:
        return x
    if bool(getattr(x, "mask", False)):   # valor enmascarado de numpy (np.ma.masked): no hay dato
        return None
    return x.item()


def _es_numero(x):
    """Número finito de verdad (también los de numpy, sueltos o envueltos). None, NaN, inf, texto o una lista: no."""
    x = _suelto(x)
    return isinstance(x, numbers.Real) and math.isfinite(x)


def _es_si(x):
    """Un sí de verdad: True (también el de numpy). None, NaN, un número o un texto como "True": no."""
    return _suelto(x) is True


def _supera(valor, corte, u):
    """Prudencia: cuenta como superado si queda a menos del margen del corte."""
    return valor is not None and valor >= corte * (1 - u.margen)


def clasificar(t: Tramo, u: Umbrales = Umbrales()) -> Resultado:
    avisos = []
    # Sin dato: con un número vacío o roto toda comparación da "no" y el tramo saldría verde.
    # Por eso va antes de cualquier comparación.
    rotos = [nombre for campo, nombre in OBLIGATORIOS.items() if not _es_numero(getattr(t, campo))]
    if t.lluvia_referencia_mm is not None and not _es_numero(t.lluvia_referencia_mm):
        rotos.append("lluvia de la fecha de referencia")
    if rotos:
        return Resultado(SIN_DATO, "S", "falta el dato de: " + ", ".join(rotos), "—", avisos)
    # hand_m y dM son opcionales: rotos valen lo mismo que "no hay", pero se avisa.
    # Se copia: el Tramo que entra no se toca.
    if t.hand_m is not None and not _es_numero(t.hand_m):
        t = replace(t, hand_m=None)
        avisos.append("dato de altura (HAND) roto: se sigue sin él")
    if t.dM is not None and not _es_numero(t.dM):
        t = replace(t, dM=None)
        avisos.append("dato de humedad de la zona roto: se sigue sin él")

    if t.Wp >= u.agua_siempre:
        avisos.append("posible error del mapa de caminos: el tramo cruza agua de siempre")
    pasada = f" del {t.fecha_pasada}" if t.fecha_pasada else ""

    # Sin dato: la calidad no alcanza para decir nada.
    # Las banderas valen solo si son True: con NaN o un texto ("False" de un CSV), "not" las daba por buenas.
    faltan = []
    if not _es_si(t.misma_orbita):
        faltan.append("órbita distinta")
    if not _es_si(t.misma_version):
        faltan.append("versión distinta")
    llovio_antes = t.lluvia_referencia_mm is not None and t.lluvia_referencia_mm >= u.lluvia_referencia
    if not _es_si(t.referencia_seca) or llovio_antes:   # corte de calidad: comparación directa, sin margen
        faltan.append("la fecha de referencia no es seca"
                      + (f" ({t.lluvia_referencia_mm:g} mm de lluvia)" if llovio_antes else ""))
    if t.N < u.min_pixeles:
        faltan.append(f"pocos píxeles ({t.N})")
    if t.E > u.max_dias:
        faltan.append(f"radar de hace {t.E:g} días")
    if faltan:
        return Resultado(SIN_DATO, "S", "; ".join(faltan), "—", avisos)

    def res(color, regla, motivo, contradiccion=False):
        return Resultado(color, regla, motivo, _confianza(t, u, contradiccion), avisos)

    # Rojo: el eslabón más débil
    if _supera(t.agua_seguida_m, u.agua_seguida_rojo, u):
        return res(ROJO, "R1", f"{t.agua_seguida_m:g} m seguidos con agua (radar{pasada})")
    if _supera(t.monte_seguido_m, u.agua_seguida_rojo, u):
        return res(ROJO, "R2", f"{t.monte_seguido_m:g} m seguidos con agua bajo el monte (radar{pasada})")

    # Gris: el radar ya no vale
    if t.E > u.dias_frescos and _supera(t.lluvia_mm, u.lluvia_gris, u):
        return res(GRIS, "G", f"llovieron {t.lluvia_mm:g} mm después del radar{pasada}: preguntá antes de salir")

    k = u.factor_ripio if t.T == "ripio" else 1.0
    # Amarillo
    if (_supera(t.agua_seguida_m, u.agua_seguida_amarillo, u)
            or _supera(t.monte_seguido_m, u.agua_seguida_amarillo, u)
            or _supera(t.agua_pct, u.agua_pct_amarillo, u)):
        return res(AMARILLO, "A1", "agua cerca del camino")
    if t.T != "asfalto":
        if _supera(t.suelo_mojado_pct, u.suelo_mojado_pct * k, u):
            if t.dM is not None and t.dM < u.dm_contradice and t.lluvia_mm < 5:
                return res(AMARILLO, "A2b", f"el radar ve {t.suelo_mojado_pct:g} % de suelo mojado pero la zona"
                           " no se mojó: puede ser un campo arado. Verificar", True)
            return res(AMARILLO, "A2", f"{t.suelo_mojado_pct:g} % del tramo con suelo mojado: barro probable")
        tope = u.aguanta(t.hand_m) * k
        if _supera(t.lluvia_mm, tope, u):
            alto = f"a {t.hand_m:g} m del bajo" if t.hand_m is not None else "sin dato de altura"
            return res(AMARILLO, "A3", f"llovieron {t.lluvia_mm:g} mm desde la pasada{pasada};"
                       f" este tramo ({alto}) aguanta {tope:g} mm")
    return res(VERDE, "V", f"sin agua ni barro detectados (radar{pasada})")


def _confianza(t, u, contradiccion):
    otra = _suelto(t.otra_pasada_coincide)   # solo True o False dicen algo: NaN o un texto valen como None
    if contradiccion or t.E > u.dias_frescos or otra is False:
        return "baja"
    if otra is True or (t.dM is not None and t.dM >= u.dm_contradice):
        return "alta"
    return "media"
