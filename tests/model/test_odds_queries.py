"""Tests de integración TDD para odds_queries.py.

Spec: helpers best_odds_per_outcome y latest_per_bookmaker.
  - best_odds_per_outcome(match_id, session): retorna la cuota máxima por outcome_code.
  - latest_per_bookmaker(match_id, outcome_code, session): retorna un registro
    por bookmaker (el más reciente).
"""

import datetime

import pytest
from sqlalchemy.orm import Session

from app.model.odds_queries import best_odds_per_outcome, latest_per_bookmaker
from app.models import Competition, Match, Odds, Team
from app.models.enums import CompetitionKind, MarketType, MatchStatus

# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------


def _setup_match(session: Session) -> Match:
    """Crea competición, equipos y partido mínimos."""
    comp = Competition(name="OQ Test WC", kind=CompetitionKind.WORLD_CUP)
    session.add(comp)
    session.flush()

    home = Team(name="OQ_Home")
    away = Team(name="OQ_Away")
    session.add_all([home, away])
    session.flush()

    match = Match(
        competition_id=comp.id,
        match_date=datetime.date(2026, 6, 20),
        home_team_id=home.id,
        away_team_id=away.id,
        neutral_site=False,
        status=MatchStatus.SCHEDULED,
        went_to_extra_time=False,
        went_to_penalties=False,
    )
    session.add(match)
    session.flush()
    return match


def _odds(
    session: Session,
    match: Match,
    bookmaker: str,
    outcome_code: str,
    decimal_odds: float,
    captured_at: datetime.datetime,
) -> Odds:
    o = Odds(
        match_id=match.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code=outcome_code,
        bookmaker=bookmaker,
        decimal_odds=decimal_odds,
        captured_at=captured_at,
        is_closing=False,
    )
    session.add(o)
    session.flush()
    return o


# ---------------------------------------------------------------------------
# best_odds_per_outcome: retorna la cuota máxima por outcome_code
# ---------------------------------------------------------------------------


def test_best_odds_per_outcome_returns_max(db_session):
    """best_odds_per_outcome: para HOME, retorna la cuota más alta entre bookmakers."""
    match = _setup_match(db_session)
    t = datetime.datetime(2026, 6, 19, 12, 0)

    # Dos bookmakers con distintas cuotas HOME: 2.10 y 2.30 (la mayor gana)
    _odds(db_session, match, "BookA", "HOME", 2.10, t)
    best = _odds(db_session, match, "BookB", "HOME", 2.30, t)

    result = best_odds_per_outcome(match.id, db_session)

    assert "HOME" in result
    assert result["HOME"].id == best.id
    assert float(result["HOME"].decimal_odds) == 2.30


def test_best_odds_per_outcome_covers_all_outcomes(db_session):
    """best_odds_per_outcome: retorna entradas para HOME, DRAW y AWAY cuando existen."""
    match = _setup_match(db_session)
    t = datetime.datetime(2026, 6, 19, 12, 0)

    # Un bookmaker con triple completo
    h = _odds(db_session, match, "BookC", "HOME", 2.20, t)
    d = _odds(db_session, match, "BookC", "DRAW", 3.10, t)
    a = _odds(db_session, match, "BookC", "AWAY", 3.50, t)

    result = best_odds_per_outcome(match.id, db_session)

    assert set(result.keys()) >= {"HOME", "DRAW", "AWAY"}
    assert result["HOME"].id == h.id
    assert result["DRAW"].id == d.id
    assert result["AWAY"].id == a.id


def test_best_odds_per_outcome_empty_when_no_odds(db_session):
    """best_odds_per_outcome: retorna dict vacío si no hay odds para el partido."""
    match = _setup_match(db_session)

    result = best_odds_per_outcome(match.id, db_session)

    assert result == {}


# ---------------------------------------------------------------------------
# latest_per_bookmaker: retorna un registro por bookmaker (el más reciente)
# ---------------------------------------------------------------------------


def test_latest_per_bookmaker_returns_one_per_bookmaker(db_session):
    """latest_per_bookmaker: retorna exactamente un Odds por bookmaker (el más reciente)."""
    match = _setup_match(db_session)
    t1 = datetime.datetime(2026, 6, 19, 10, 0)
    t2 = datetime.datetime(2026, 6, 19, 12, 0)  # más reciente

    _odds(db_session, match, "BookX", "HOME", 2.10, t1)
    latest = _odds(db_session, match, "BookX", "HOME", 2.25, t2)
    _odds(db_session, match, "BookY", "HOME", 2.15, t1)

    result = latest_per_bookmaker(match.id, "HOME", db_session)

    bookmakers = {o.bookmaker for o in result}
    assert bookmakers == {"BookX", "BookY"}

    # BookX debe tener el snapshot más reciente
    bookx_row = next(o for o in result if o.bookmaker == "BookX")
    assert bookx_row.id == latest.id
    assert float(bookx_row.decimal_odds) == 2.25


def test_latest_per_bookmaker_empty_when_no_odds(db_session):
    """latest_per_bookmaker: retorna lista vacía si no hay odds para el partido/outcome."""
    match = _setup_match(db_session)

    result = latest_per_bookmaker(match.id, "HOME", db_session)

    assert result == []
