"""TDD RED → GREEN — Router de parlays: POST preview, POST persist, GET.

Escenarios verbatim de spec/design:
  S1 — preview 3 legs: stake=5000 → retorno=35420, combined_odds≈7.084
  S2 — odds ≤ 1 → 422
  S3 — 1 leg → 422 (Pydantic min_length)
  S4 — partido FINISHED → 422
  S5 — POST persist → 201, BetLog bet_kind=parlay + N bet_leg rows
  S6 — GET /parlays → lista; ?mode=real filtra
"""

from datetime import date
from decimal import Decimal

import pytest

from app.models.betting import BetLeg, BetLog
from app.models.competition import Competition
from app.models.enums import BetKind, CompetitionKind, MarketType, MatchStatus
from app.models.match import Match
from app.models.model import Prediction
from app.models.team import Team

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_match(session, status=MatchStatus.SCHEDULED, idx: str = "") -> Match:
    comp = Competition(name=f"Parlay Comp {idx}", kind=CompetitionKind.WORLD_CUP)
    session.add(comp)
    session.flush()

    home = Team(name=f"PAH {idx} {id(session)}")
    away = Team(name=f"PAA {idx} {id(session)}")
    session.add_all([home, away])
    session.flush()

    match = Match(
        competition_id=comp.id,
        match_date=date(2026, 7, 10),
        home_team_id=home.id,
        away_team_id=away.id,
        status=status,
    )
    session.add(match)
    session.flush()
    return match


def _make_prediction(session, match_id, mv_id, outcome_code, probability):
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
# S1 — preview 3-leg: stake=5000 → retorno=35420
# ---------------------------------------------------------------------------


def test_preview_3legs_retorno(client, db_session):
    """stake=5000, combined=7.084 → retorno=35420.00."""
    m1 = _make_match(db_session, idx="p1")
    m2 = _make_match(db_session, idx="p2")
    m3 = _make_match(db_session, idx="p3")

    body = {
        "legs": [
            {"match_id": m1.id, "outcome_code": "HOME", "odds": "1.40"},
            {"match_id": m2.id, "outcome_code": "AWAY", "odds": "2.75"},
            {"match_id": m3.id, "outcome_code": "HOME", "odds": "1.84"},
        ],
        "stake": "5000",
    }
    resp = client.post("/api/v1/parlays/preview", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert float(data["combined_odds"]) == pytest.approx(7.084, abs=0.002)
    assert float(data["retorno"]) == pytest.approx(35420, abs=1)
    assert data["stake"] == "5000"


# ---------------------------------------------------------------------------
# S2 — odds ≤ 1 → 422
# ---------------------------------------------------------------------------


def test_preview_odds_le_one_returns_422(client, db_session):
    """Leg con odds=0.90 (≤1) → 422."""
    m1 = _make_match(db_session, idx="q1")
    m2 = _make_match(db_session, idx="q2")

    body = {
        "legs": [
            {"match_id": m1.id, "outcome_code": "HOME", "odds": "0.90"},
            {"match_id": m2.id, "outcome_code": "AWAY", "odds": "2.00"},
        ],
        "stake": "100",
    }
    resp = client.post("/api/v1/parlays/preview", json=body)

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# S3 — 1 leg → 422 (Pydantic min_length=2)
# ---------------------------------------------------------------------------


def test_preview_single_leg_returns_422(client, db_session):
    """Solo 1 leg → 422."""
    m1 = _make_match(db_session, idx="r1")

    body = {
        "legs": [{"match_id": m1.id, "outcome_code": "HOME", "odds": "1.90"}],
        "stake": "100",
    }
    resp = client.post("/api/v1/parlays/preview", json=body)

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# S4 — partido FINISHED en preview → 422
# ---------------------------------------------------------------------------


def test_preview_finished_match_returns_422(client, db_session):
    """Leg apuntando a partido FINISHED → 422."""
    m_finished = _make_match(db_session, status=MatchStatus.FINISHED, idx="f1")
    m_scheduled = _make_match(db_session, idx="f2")

    body = {
        "legs": [
            {"match_id": m_finished.id, "outcome_code": "HOME", "odds": "1.50"},
            {"match_id": m_scheduled.id, "outcome_code": "AWAY", "odds": "2.00"},
        ],
        "stake": "100",
    }
    resp = client.post("/api/v1/parlays/preview", json=body)

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# S5 — POST /parlays persist → 201, BetLog parlay + bet_leg rows
# ---------------------------------------------------------------------------


def test_create_parlay_persists_betlog_and_legs(client, db_session):
    """POST /parlays → 201; BetLog bet_kind=parlay + 2 BetLeg en BD."""
    m1 = _make_match(db_session, idx="c1")
    m2 = _make_match(db_session, idx="c2")

    body = {
        "legs": [
            {"match_id": m1.id, "outcome_code": "HOME", "odds": "1.40"},
            {"match_id": m2.id, "outcome_code": "AWAY", "odds": "2.50"},
        ],
        "stake": "5000",
        "note": "test parlay",
    }
    resp = client.post("/api/v1/parlays", json=body)

    assert resp.status_code == 201
    data = resp.json()
    bet_id = data["id"]
    assert data["bet_kind"] == "parlay"

    # Verify BetLog in DB
    from sqlalchemy import select

    bet = db_session.get(BetLog, bet_id)
    assert bet is not None
    assert bet.bet_kind == BetKind.PARLAY
    assert bet.stake == Decimal("5000")

    # Verify BetLeg rows
    legs = db_session.execute(select(BetLeg).where(BetLeg.bet_log_id == bet_id)).scalars().all()
    assert len(legs) == 2
    outcome_codes = {leg.outcome_code for leg in legs}
    assert "HOME" in outcome_codes
    assert "AWAY" in outcome_codes


# ---------------------------------------------------------------------------
# S6 — GET /parlays filters by mode
# ---------------------------------------------------------------------------


def test_get_parlays_list(client, db_session):
    """GET /parlays → lista de parlays; ?mode=real filtra por modo."""
    m1 = _make_match(db_session, idx="g1")
    m2 = _make_match(db_session, idx="g2")

    # Create one real parlay
    resp = client.post(
        "/api/v1/parlays",
        json={
            "legs": [
                {"match_id": m1.id, "outcome_code": "HOME", "odds": "1.80"},
                {"match_id": m2.id, "outcome_code": "AWAY", "odds": "2.20"},
            ],
            "stake": "1000",
        },
    )
    assert resp.status_code == 201

    # GET all
    resp_list = client.get("/api/v1/parlays")
    assert resp_list.status_code == 200
    items = resp_list.json()
    assert len(items) >= 1
    assert all(item["bet_kind"] == "parlay" for item in items)

    # GET filtered by mode=real
    resp_real = client.get("/api/v1/parlays?mode=real")
    assert resp_real.status_code == 200
    for item in resp_real.json():
        assert item["mode"] == "real"
