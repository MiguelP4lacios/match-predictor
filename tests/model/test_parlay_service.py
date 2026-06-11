"""TDD RED → GREEN — parlay_service: resolución de p_model desde Prediction activa.

Escenarios:
  S1 — Leg con predicción existente → p_model resuelto desde Prediction
  S2 — Leg sin predicción para ese outcome → p_model=None (no rompe, leg presente)
  S3 — Preview completo: resolve_legs → ParlayDiagnosis (odds correctas)
"""

from decimal import Decimal

import pytest

from app.model.parlay_service import resolve_legs
from app.models.competition import Competition
from app.models.enums import CompetitionKind, MarketType, MatchStatus
from app.models.match import Match
from app.models.model import ModelVersion, Prediction
from app.models.team import Team


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_match(session, home_name: str, away_name: str) -> Match:
    comp = Competition(name=f"PS Test {home_name}", kind=CompetitionKind.WORLD_CUP)
    session.add(comp)
    session.flush()

    home = Team(name=f"H {home_name}")
    away = Team(name=f"A {away_name}")
    session.add_all([home, away])
    session.flush()

    match = Match(
        competition_id=comp.id,
        match_date=__import__("datetime").date(2026, 7, 1),
        home_team_id=home.id,
        away_team_id=away.id,
        status=MatchStatus.SCHEDULED,
    )
    session.add(match)
    session.flush()
    return match


def _make_prediction(
    session,
    match_id: int,
    mv_id: int,
    outcome_code: str,
    probability: float,
) -> Prediction:
    pred = Prediction(
        match_id=match_id,
        model_version_id=mv_id,
        market_type=MarketType.MATCH_1X2,
        outcome_code=outcome_code,
        probability=probability,
        low_confidence=False,
    )
    session.add(pred)
    session.flush()
    return pred


# ---------------------------------------------------------------------------
# S1 — Leg con predicción → p_model resuelto
# ---------------------------------------------------------------------------


def test_resolve_legs_p_model_from_prediction(db_session):
    """Leg con Prediction activa → p_model viene del campo probability."""
    m1 = _make_match(db_session, "BRA", "ARG")
    m2 = _make_match(db_session, "MEX", "USA")

    mv = ModelVersion(name="ps-mv-active", params_json={})
    db_session.add(mv)
    db_session.flush()

    _make_prediction(db_session, m1.id, mv.id, "HOME", probability=0.65)
    _make_prediction(db_session, m2.id, mv.id, "AWAY", probability=0.50)

    raw_legs = [
        {"match_id": m1.id, "outcome_code": "HOME", "odds": Decimal("1.80"), "label": "BRA HOME"},
        {"match_id": m2.id, "outcome_code": "AWAY", "odds": Decimal("2.10"), "label": "USA AWAY"},
    ]
    result = resolve_legs(db_session, raw_legs)

    assert len(result.legs) == 2
    # First leg: p_model resolved from prediction
    leg_diag = result.legs[0]
    assert leg_diag.leg.p_model == pytest.approx(0.65, abs=1e-4)
    assert leg_diag.leg.odds == Decimal("1.80")


# ---------------------------------------------------------------------------
# S2 — Leg sin predicción → p_model=None
# ---------------------------------------------------------------------------


def test_resolve_legs_no_prediction_gives_none(db_session):
    """Leg sin Prediction en BD activa → p_model=None; no lanza excepción."""
    match = _make_match(db_session, "GER", "FRA")

    # No hay ModelVersion ni Prediction — la BD está vacía para este test

    raw_legs = [
        {"match_id": match.id, "outcome_code": "AWAY", "odds": Decimal("2.50"), "label": "FRA AWAY"},
        {"match_id": match.id, "outcome_code": "HOME", "odds": Decimal("2.00"), "label": "GER HOME"},
    ]
    result = resolve_legs(db_session, raw_legs)

    assert len(result.legs) == 2
    for ld in result.legs:
        assert ld.leg.p_model is None
    # EV not computable when p_model unknown
    assert result.model_prob is None
    assert result.ev is None


# ---------------------------------------------------------------------------
# S3 — Combined odds correctas cuando hay dos legs
# ---------------------------------------------------------------------------


def test_resolve_legs_combined_odds(db_session):
    """Dos legs: odds 1.40 × 2.50 → combined_odds ≈ 3.500."""
    m1 = _make_match(db_session, "ESP", "ENG")
    m2 = _make_match(db_session, "NED", "POR")

    mv = ModelVersion(name="ps-mv-combined", params_json={})
    db_session.add(mv)
    db_session.flush()

    _make_prediction(db_session, m1.id, mv.id, "HOME", 0.70)
    _make_prediction(db_session, m2.id, mv.id, "AWAY", 0.45)

    raw_legs = [
        {"match_id": m1.id, "outcome_code": "HOME", "odds": Decimal("1.40"), "label": "ESP HOME"},
        {"match_id": m2.id, "outcome_code": "AWAY", "odds": Decimal("2.50"), "label": "POR AWAY"},
    ]
    result = resolve_legs(db_session, raw_legs)

    assert result.combined_odds == pytest.approx(Decimal("3.500"), abs=Decimal("0.001"))
    # Both p_model present → ev computed
    assert result.model_prob is not None
    assert result.ev is not None
