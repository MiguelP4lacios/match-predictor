"""TDD RED → GREEN — Motor puro de parlay (combine_parlay).

Escenarios verbatim de spec/design:
  S1 — 3-leg happy path:
       odds 1.40×2.75×1.84=7.084, prob 0.834×0.491×0.780=0.3194, EV +1.2627
       per-leg EV: +16.8% / +35.0% / +43.5%
  S2 — 2-leg con leg −EV + suggested_without_negatives:
       odds 1.40×0.90 → leg 2 odds<1 devuelve error de validación en combine_parlay
       Ajuste: usar un leg con p < implied para tener EV negativo real.
       odds 1.40 p=0.60 (EV+) / odds 2.00 p=0.30 (EV-) → suggested_without_negatives=[leg1]
  S3 — empty legs → ValueError
  S4 — 1-leg → ValueError
"""

from decimal import Decimal

import pytest

from app.model.parlay import Leg, ParlayDiagnosis, combine_parlay


# ---------------------------------------------------------------------------
# S1 — 3-leg happy path: números verbatim
# ---------------------------------------------------------------------------


def test_combine_parlay_3legs_numeric():
    """odds 1.40×2.75×1.84=7.084; prob 0.834×0.491×0.780≈0.3194; EV≈+1.2627."""
    legs = [
        Leg(match_id=1, outcome_code="HOME", odds=Decimal("1.40"), p_model=0.834, label="A HOME"),
        Leg(match_id=2, outcome_code="AWAY", odds=Decimal("2.75"), p_model=0.491, label="B AWAY"),
        Leg(match_id=3, outcome_code="HOME", odds=Decimal("1.84"), p_model=0.780, label="C HOME"),
    ]
    result = combine_parlay(legs)

    assert isinstance(result, ParlayDiagnosis)
    assert result.combined_odds == pytest.approx(Decimal("7.084"), abs=Decimal("0.001"))
    assert result.model_prob == pytest.approx(0.3194, abs=0.0002)
    assert result.ev == pytest.approx(1.2627, abs=0.002)
    # All three legs have positive EV; no suggestions
    assert len(result.suggested_without_negatives) == 0


# ---------------------------------------------------------------------------
# S1b — per-leg EV (+16.8% / +35.0% / +43.5%)
# ---------------------------------------------------------------------------


def test_combine_parlay_per_leg_ev():
    """Per-leg EV values match spec: +16.8% / +35.0% / +43.5%."""
    legs = [
        Leg(match_id=1, outcome_code="HOME", odds=Decimal("1.40"), p_model=0.834, label="A HOME"),
        Leg(match_id=2, outcome_code="AWAY", odds=Decimal("2.75"), p_model=0.491, label="B AWAY"),
        Leg(match_id=3, outcome_code="HOME", odds=Decimal("1.84"), p_model=0.780, label="C HOME"),
    ]
    result = combine_parlay(legs)

    assert len(result.legs) == 3
    assert result.legs[0].ev == pytest.approx(0.168, abs=0.002)   # +16.8%
    assert result.legs[1].ev == pytest.approx(0.350, abs=0.002)   # +35.0%
    assert result.legs[2].ev == pytest.approx(0.435, abs=0.002)   # +43.5%
    # All positive
    assert all(not ld.is_negative_ev for ld in result.legs)


# ---------------------------------------------------------------------------
# S2 — 2-leg con leg −EV → suggested_without_negatives contiene solo los EV+
# ---------------------------------------------------------------------------


def test_combine_parlay_negative_ev_leg_filtered():
    """Un leg con EV negativo → is_negative_ev=True + suggested_without_negatives excluye ese leg."""
    # Leg 1: p=0.60, odds=1.40 → EV = 0.60*0.40 - 0.40 = 0.24-0.40 = -0.16 → EV NEGATIVO
    # Leg 2: p=0.834, odds=1.84 → EV = 0.834*0.84 - 0.166 = +0.535 → EV POSITIVO
    leg_neg = Leg(match_id=10, outcome_code="HOME", odds=Decimal("1.40"), p_model=0.60, label="NEG")
    leg_pos = Leg(match_id=11, outcome_code="AWAY", odds=Decimal("1.84"), p_model=0.834, label="POS")

    result = combine_parlay([leg_neg, leg_pos])

    assert result.legs[0].is_negative_ev is True
    assert result.legs[1].is_negative_ev is False
    # suggested_without_negatives only has the positive-EV leg
    assert len(result.suggested_without_negatives) == 1
    assert result.suggested_without_negatives[0].match_id == 11


# ---------------------------------------------------------------------------
# S3 — empty legs → ValueError
# ---------------------------------------------------------------------------


def test_combine_parlay_empty_raises():
    """combine_parlay([]) debe lanzar ValueError."""
    with pytest.raises(ValueError, match="al menos 2"):
        combine_parlay([])


# ---------------------------------------------------------------------------
# S4 — 1-leg → ValueError
# ---------------------------------------------------------------------------


def test_combine_parlay_single_leg_raises():
    """combine_parlay con 1 leg debe lanzar ValueError."""
    with pytest.raises(ValueError, match="al menos 2"):
        combine_parlay([
            Leg(match_id=1, outcome_code="HOME", odds=Decimal("1.90"), p_model=0.60, label="X")
        ])


# ---------------------------------------------------------------------------
# S5 — leg sin p_model (None) → model_prob=None, EV del leg=None
# ---------------------------------------------------------------------------


def test_combine_parlay_leg_without_p_model():
    """Leg con p_model=None → leg.ev=None, ParlayDiagnosis.model_prob=None."""
    legs = [
        Leg(match_id=1, outcome_code="HOME", odds=Decimal("1.90"), p_model=0.60, label="A"),
        Leg(match_id=2, outcome_code="AWAY", odds=Decimal("2.00"), p_model=None, label="B"),
    ]
    result = combine_parlay(legs)

    assert result.model_prob is None
    assert result.ev is None
    # Leg with None p_model has None ev and is not flagged negative
    assert result.legs[1].ev is None
    assert result.legs[1].is_negative_ev is False
