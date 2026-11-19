"""Cómo evoluciona el barro de un tramo día a día.

Idea: un índice de barro (0 a 100) con memoria.
- Cuando pasa el radar, el índice se pone en lo que midió (el radar manda).
- Entre pasadas:
    * cada día sin lluvia, el barro se seca: baja a la mitad cada `media_vida` días;
    * cada día con lluvia, sube según cuánto aguanta el tramo (su altura, HAND).
- Si sigue lloviendo, empeora; si sale el sol y no llueve, mejora.
- El color sale del índice. Mañana se estima suponiendo que no llueve.
- Si falta la lluvia de un día (None, NaN), no se inventa un día seco: el tramo queda
  sin dato hasta la próxima pasada del radar.

Todos los números son de arranque: `media_vida` se calibra con las pasadas de NISAR
posteriores a la lluvia del 9/10/2026 (ver docs/clasificacion-semaforo.md).
"""
import math
import numbers
from dataclasses import dataclass, field

ROJO, AMARILLO, VERDE, SIN_DATO = "intransitable", "con barro", "transitable", "sin dato"


@dataclass
class Parametros:
    media_vida: float = 5.7        # días que tarda el barro en bajar a la mitad, sin lluvia.
                                   # Medido con NISAR (baqui/secado.py): 3 caminos, lluvia del 9/10/2026.
    factor_bajo: float = 1.5       # en un bajo (HAND < 2 m) se seca más lento
    factor_alto: float = 0.7       # en una loma (HAND > 5 m) se seca más rápido
    dhh_lleno: float = 3.0         # dB de subida del eco que equivalen a barro 100
    lluvia_minima: float = 2.0     # mm: menos que esto no cuenta como día de lluvia
    corte_rojo: float = 60.0
    corte_amarillo: float = 35.0
    margen: float = 0.10           # prudencia: a menos del 10 % de un corte, el color más grave
    max_dias_radar: int = 12       # sin radar en 12 días: sin dato

    def aguanta(self, hand_m):
        """mm de lluvia que llevan el tramo de seco a barro 100."""
        if not _es_numero(hand_m):     # None, NaN o inf: sin dato de altura
            return 25.0
        if hand_m < 2:
            return 15.0
        if hand_m <= 5:
            return 30.0
        return 50.0

    def secado_diario(self, hand_m):
        """Fracción del barro que queda después de un día seco."""
        mv = self.media_vida
        if not _es_numero(hand_m):     # None, NaN o inf: sin dato de altura
            return 0.5 ** (1 / mv)
        if hand_m < 2:
            mv *= self.factor_bajo
        elif hand_m > 5:
            mv *= self.factor_alto
        return 0.5 ** (1 / mv)


def desde_radar(dhh_db, agua_seguida_m=0.0, p: Parametros = Parametros()):
    """Índice de barro medido por el radar en el día de la pasada. Si falta un dato, NaN (sin dato)."""
    if not _es_numero(agua_seguida_m):
        return float("nan")
    if agua_seguida_m >= 50:
        return 100.0
    if not _es_numero(dhh_db):
        return float("nan")
    return max(0.0, min(100.0, 100 * dhh_db / p.dhh_lleno))


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


def color(indice, p: Parametros = Parametros()):
    # Un índice vacío o roto (None, NaN, inf) nunca puede dar "transitable".
    if not _es_numero(indice):
        return SIN_DATO
    if indice >= p.corte_rojo * (1 - p.margen):
        return ROJO
    if indice >= p.corte_amarillo * (1 - p.margen):
        return AMARILLO
    return VERDE


@dataclass
class Dia:
    fecha: str
    indice: float
    color: str
    dias_desde_radar: int
    motivo: str


@dataclass
class Serie:
    dias: list = field(default_factory=list)

    @property
    def hoy(self):
        return self.dias[-1]


def evolucionar(fechas, lluvia_mm, pasadas, hand_m=None, p: Parametros = Parametros()):
    """Recorre los días y devuelve el estado de cada uno.

    fechas: lista de fechas (texto), una por día, en orden.
    lluvia_mm: lluvia de cada día, misma longitud. Un día sin dato (None, NaN) deja el tramo
        sin dato hasta la próxima pasada: no cuenta como día seco.
    pasadas: {fecha: índice medido por el radar} (usar desde_radar()).
    """
    s = Serie()
    indice, desde = None, None
    for f, mm in zip(fechas, lluvia_mm):
        mm = _suelto(mm)
        if f in pasadas:
            indice, desde = _suelto(pasadas[f]), 0
            motivo = f"radar del {f}"
        elif indice is None:
            s.dias.append(Dia(f, float("nan"), SIN_DATO, -1, "todavía no pasó el radar"))
            continue
        else:
            desde += 1
            if not _es_numero(indice):
                pass   # ya está sin dato: sigue así, con su motivo, hasta la próxima pasada del radar
            elif not _es_numero(mm):
                # sin la lluvia del día no se sabe si el barro bajó o subió
                indice, motivo = float("nan"), "falta el dato de lluvia"
            elif mm >= p.lluvia_minima:
                indice = min(100.0, indice + 100 * mm / p.aguanta(hand_m))
                motivo = f"llovieron {mm:g} mm"
            else:
                indice = indice * p.secado_diario(hand_m)
                motivo = "día seco: se seca"
        c = SIN_DATO if desde > p.max_dias_radar else color(indice, p)
        s.dias.append(Dia(f, round(indice, 1) if _es_numero(indice) else float("nan"), c, desde, motivo))
    return s


def dias_hasta_pasar(dia: Dia, hand_m=None, p: Parametros = Parametros(), tope=15):
    """Si no llueve, ¿en cuántos días el tramo vuelve a verde? (None: sin dato o más que el tope)."""
    if dia.color == SIN_DATO:
        return None
    indice, n = dia.indice, 0
    while color(indice, p) != VERDE:
        if n >= tope:
            return None
        indice *= p.secado_diario(hand_m)
        n += 1
    return n


def manana_sin_lluvia(dia: Dia, hand_m=None, p: Parametros = Parametros()):
    """Color de mañana si no llueve."""
    if dia.color == SIN_DATO:
        return SIN_DATO
    return color(dia.indice * p.secado_diario(hand_m), p)
