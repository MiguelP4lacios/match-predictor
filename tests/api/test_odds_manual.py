"""TDD — Task 4.4: POST /api/v1/odds/manual.

Escenarios de spec odds-capture:
  OM1 — POST válido GROUP_ADVANCE → HTTP 201, Odds insertada con outcome_team_id
  OM2 — POST válido REACH_SEMI_FINAL → HTTP 201 insertada
  OM3 — POST válido REACH_FINAL → HTTP 201 insertada
  OM4 — POST con MATCH_1X2 → HTTP 422 (mercado no permitido)
  OM5 — POST con OVER_UNDER → HTTP 422
  OM6 — POST con OUTRIGHT_WINNER → HTTP 422 (solo para futuros avance, no campeón aquí)
  OM7 — team_id inexistente → HTTP 422
"""

import pytest
from sqlalchemy import select

from app.models import Competition, Odds, Team
from app.models.enums import CompetitionKind, MarketType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _team(session, name: str = "TEST_ManualTeam") -> Team:
    t = Team(name=name)
    session.add(t)
    session.flush()
    return t


def _wc(session) -> Competition:
    comp = session.scalar(select(Competition).where(Competition.name == "FIFA World Cup"))
    if comp is None:
        comp = Competition(name="FIFA World Cup", kind=CompetitionKind.WORLD_CUP)
        session.add(comp)
        session.flush()
    return comp


# ---------------------------------------------------------------------------
# OM1 — GROUP_ADVANCE persisted
# ---------------------------------------------------------------------------


def test_manual_odds_group_advance_inserted(client, db_session):
    """POST GROUP_ADVANCE → 201 + Odds insertada."""
    team = _team(db_session)

    payload = {
        "market_type": "GROUP_ADVANCE",
        "outcome_team_id": team.id,
        "decimal_odds": 1.30,
        "bookmaker": "betplay",
    }
    resp = client.post("/api/v1/odds/manual", json=payload)

    assert resp.status_code == 201, resp.text

    row = db_session.scalar(
        select(Odds).where(
            Odds.market_type == MarketType.GROUP_ADVANCE,
            Odds.outcome_team_id == team.id,
        )
    )
    assert row is not None
    assert float(row.decimal_odds) == pytest.approx(1.30, abs=0.001)
    assert row.bookmaker == "betplay"
    assert row.match_id is None


# ---------------------------------------------------------------------------
# OM2 — REACH_SEMI_FINAL persisted
# ---------------------------------------------------------------------------


def test_manual_odds_reach_semi_final_inserted(client, db_session):
    """POST REACH_SEMI_FINAL → 201."""
    team = _team(db_session, "TEST_ManualSF")

    payload = {
        "market_type": "REACH_SEMI_FINAL",
        "outcome_team_id": team.id,
        "decimal_odds": 2.50,
        "bookmaker": "betplay",
    }
    resp = client.post("/api/v1/odds/manual", json=payload)

    assert resp.status_code == 201, resp.text

    row = db_session.scalar(
        select(Odds).where(
            Odds.market_type == MarketType.REACH_SEMI_FINAL,
            Odds.outcome_team_id == team.id,
        )
    )
    assert row is not None


# ---------------------------------------------------------------------------
# OM3 — REACH_FINAL persisted
# ---------------------------------------------------------------------------


def test_manual_odds_reach_final_inserted(client, db_session):
    """POST REACH_FINAL → 201."""
    team = _team(db_session, "TEST_ManualFinal")

    payload = {
        "market_type": "REACH_FINAL",
        "outcome_team_id": team.id,
        "decimal_odds": 4.00,
        "bookmaker": "betplay",
    }
    resp = client.post("/api/v1/odds/manual", json=payload)

    assert resp.status_code == 201, resp.text


# ---------------------------------------------------------------------------
# OM4 — MATCH_1X2 rejected (422)
# ---------------------------------------------------------------------------


def test_manual_odds_rejects_match_1x2(client, db_session):
    """POST MATCH_1X2 → 422."""
    team = _team(db_session, "TEST_ManualReject1")

    payload = {
        "market_type": "MATCH_1X2",
        "outcome_team_id": team.id,
        "decimal_odds": 2.0,
        "bookmaker": "betplay",
    }
    resp = client.post("/api/v1/odds/manual", json=payload)

    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# OM5 — OVER_UNDER rejected (422)
# ---------------------------------------------------------------------------


def test_manual_odds_rejects_over_under(client, db_session):
    """POST OVER_UNDER → 422."""
    team = _team(db_session, "TEST_ManualReject2")

    payload = {
        "market_type": "OVER_UNDER",
        "outcome_team_id": team.id,
        "decimal_odds": 1.90,
        "bookmaker": "betplay",
    }
    resp = client.post("/api/v1/odds/manual", json=payload)

    assert resp.status_code == 422, resp.text
