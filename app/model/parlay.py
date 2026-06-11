"""Núcleo puro de parlay +EV.

Funciones PURAS: sin BD, sin estado global, sin LLM. Testeables directamente.

Independencia de legs: se asume independencia estadística entre resultados de
distintos partidos. Esta suposición se documenta explícitamente porque es la
diferencia entre un modelo correcto y uno que sobreestima (correlación positiva
entre favoritos en competiciones copas daría model_prob ligeramente alto).

Tipos: Decimal para odds/combined (reproducibilidad de la UI), float para probs
y EV (consistente con probabilities.py y los campos Numeric(8,5) de Prediction).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import reduce

from app.model.probabilities import compute_ev

# ---------------------------------------------------------------------------
# Dataclasses de dominio
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Leg:
    """Input para una pierna del parlay."""

    match_id: int
    outcome_code: str
    odds: Decimal
    p_model: float | None
    label: str


@dataclass(frozen=True)
class LegDiagnosis:
    """Diagnóstico de una leg individual."""

    leg: Leg
    ev: float | None  # None cuando p_model es None
    is_negative_ev: bool  # False cuando ev es None (no hay base para decir negativo)


@dataclass(frozen=True)
class ParlayDiagnosis:
    """Diagnóstico del parlay completo."""

    combined_odds: Decimal
    model_prob: float | None  # None si algún leg no tiene p_model
    ev: float | None  # None si model_prob es None
    legs: list[LegDiagnosis]
    suggested_without_negatives: list[Leg]  # Legs EV+ que quedan si se remueven las EV-


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------


def combine_parlay(legs: list[Leg]) -> ParlayDiagnosis:
    """Combina N legs en un diagnóstico de parlay.

    Args:
        legs: Lista de piernas del parlay. Debe tener al menos 2 legs.

    Returns:
        ParlayDiagnosis con cuota combinada, prob. conjunta bajo independencia,
        EV del parlay y diagnóstico por leg.

    Raises:
        ValueError: si legs tiene menos de 2 elementos.

    Nota independencia: model_prob = Π p_i asume que los resultados de distintos
    partidos son estadísticamente independientes. En grupos iniciales del Mundial
    esta suposición es razonable; en cruces directos relacionados puede sesgar al alza.
    """
    if len(legs) < 2:
        raise ValueError(f"Un parlay requiere al menos 2 legs; recibido: {len(legs)}")

    # --- combined_odds: producto de odds (Decimal para precisión) ---
    combined_odds: Decimal = reduce(lambda acc, leg: acc * leg.odds, legs, Decimal("1"))
    # Normalizar a 3 decimales para UI
    combined_odds = combined_odds.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    # --- Diagnóstico por leg ---
    leg_diags: list[LegDiagnosis] = []
    for leg in legs:
        if leg.p_model is None:
            leg_diags.append(LegDiagnosis(leg=leg, ev=None, is_negative_ev=False))
        else:
            leg_ev = compute_ev(leg.p_model, float(leg.odds))
            leg_diags.append(LegDiagnosis(leg=leg, ev=leg_ev, is_negative_ev=leg_ev < 0))

    # --- model_prob: producto de probabilidades (bajo independencia) ---
    # Si algún leg no tiene p_model, no podemos calcular la prob. conjunta.
    if any(ld.leg.p_model is None for ld in leg_diags):
        model_prob = None
        parlay_ev = None
    else:
        model_prob = reduce(
            lambda acc, leg: acc * leg.p_model,  # type: ignore[operator]
            legs,
            1.0,
        )
        parlay_ev = compute_ev(model_prob, float(combined_odds))

    # --- suggested_without_negatives: legs EV+ cuando hay al menos uno EV- ---
    negative_legs = {ld.leg for ld in leg_diags if ld.is_negative_ev}
    if negative_legs:
        suggested = [leg for leg in legs if leg not in negative_legs]
    else:
        suggested = []

    return ParlayDiagnosis(
        combined_odds=combined_odds,
        model_prob=model_prob,
        ev=parlay_ev,
        legs=leg_diags,
        suggested_without_negatives=suggested,
    )
