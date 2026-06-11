"""TDD RED → GREEN — settle_parlays: liquidación de parlays.

Escenarios verbatim de spec/design:
  S1 — Todos los legs WON → WON pnl = stake × (combined_odds - 1)
       stake=5000, combined_odds=7.084 → pnl=+30420 (= 5000 × 6.084)
  S2 — Un leg LOST → parlay LOST pnl = -stake = -5000
  S3 — Un leg con partido aún SCHEDULED → parlay sigue PENDING
  S4 — No-regresión simples: settle_bets INTACTO (settle_parlays no lo toca)
  S5 — Idempotencia: re-run sobre parlay ya WON → 0 cambios
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.model.settle import settle_bets, settle_parlays
from app.models.betting import BetLeg, BetLog
from app.models.competition import Competition
from app.models.enums import BetKind, BetMode, BetStatus, CompetitionKind, MarketType, MatchStatus
from app.models.match import Match
from app.models.model import ModelVersion, Prediction
from app.models.odds import Odds
from app.models.team import Team


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_competition(session) -> Competition:
    comp = Competition(name=f"SP Test {id(session)}", kind=CompetitionKind.WORLD_CUP)
    session.add(comp)
    session.flush()
    return comp


def _make_teams(session, prefix="") -> tuple:
    home = Team(name=f"SPH {prefix} {id(session)}")
    away = Team(name=f"SPA {prefix} {id(session)}")
    session.add_all([home, away])
    session.flush()
    return home, away


def _make_match(session, comp, home, away, status=MatchStatus.FINISHED, home_score=2, away_score=0) -> Match:
    m = Match(
        competition_id=comp.id,
        match_date=date(2026, 7, 15),
        home_team_id=home.id,
        away_team_id=away.id,
        status=status,
        home_score=home_score if status == MatchStatus.FINISHED else None,
        away_score=away_score if status == MatchStatus.FINISHED else None,
    )
    session.add(m)
    session.flush()
    return m


def _make_parlay(
    session,
    legs_config: list[dict],
    stake: Decimal = Decimal("5000"),
) -> BetLog:
    """Crea BetLog parlay + BetLeg rows.

    legs_config: lista de dicts con keys: match (Match obj), outcome_code, odds, win_result
    """
    # combined_odds = producto de odds (para odds_taken en BetLog)
    combined = Decimal("1")
    for lc in legs_config:
        combined *= Decimal(str(lc["odds"]))

    bet = BetLog(
        match_id=None,
        outcome_code=None,
        value_signal_id=None,
        bet_kind=BetKind.PARLAY,
        mode=BetMode.REAL,
        stake=stake,
        odds_taken=float(combined),
        status=BetStatus.PENDING,
    )
    session.add(bet)
    session.flush()

    for lc in legs_config:
        leg = BetLeg(
            bet_log_id=bet.id,
            match_id=lc["match"].id,
            outcome_code=lc["outcome_code"],
            odds_taken=Decimal(str(lc["odds"])),
        )
        session.add(leg)
    session.flush()
    return bet


# ---------------------------------------------------------------------------
# S1 — Todos los legs WON → WON pnl=+30420
# ---------------------------------------------------------------------------


def test_settle_parlays_all_legs_won(db_session):
    """3 legs todos WON → parlay WON; pnl = 5000 × (7.084 - 1) ≈ 30420."""
    comp = _make_competition(db_session)
    h1, a1 = _make_teams(db_session, "s1a")
    h2, a2 = _make_teams(db_session, "s1b")
    h3, a3 = _make_teams(db_session, "s1c")

    m1 = _make_match(db_session, comp, h1, a1, home_score=2, away_score=0)  # HOME wins
    m2 = _make_match(db_session, comp, h2, a2, home_score=0, away_score=1)  # AWAY wins
    m3 = _make_match(db_session, comp, h3, a3, home_score=3, away_score=0)  # HOME wins

    bet = _make_parlay(db_session, [
        {"match": m1, "outcome_code": "HOME", "odds": "1.40"},
        {"match": m2, "outcome_code": "AWAY", "odds": "2.75"},
        {"match": m3, "outcome_code": "HOME", "odds": "1.84"},
    ], stake=Decimal("5000"))

    result = settle_parlays(db_session)

    db_session.refresh(bet)
    assert result["settled"] == 1
    assert result["won"] == 1
    assert result["lost"] == 0
    assert bet.status == BetStatus.WON
    # pnl = 5000 × (7.084 - 1) = 5000 × 6.084 = 30420
    assert bet.pnl == pytest.approx(Decimal("30420"), abs=Decimal("1"))


# ---------------------------------------------------------------------------
# S2 — Un leg LOST → parlay LOST pnl=-5000
# ---------------------------------------------------------------------------


def test_settle_parlays_one_leg_lost(db_session):
    """Un leg LOST → parlay LOST pnl=-stake=-5000."""
    comp = _make_competition(db_session)
    h1, a1 = _make_teams(db_session, "s2a")
    h2, a2 = _make_teams(db_session, "s2b")

    m1 = _make_match(db_session, comp, h1, a1, home_score=2, away_score=0)  # HOME wins
    m2 = _make_match(db_session, comp, h2, a2, home_score=1, away_score=1)  # DRAW

    # Second leg bets on HOME (but result is DRAW) → LOST
    bet = _make_parlay(db_session, [
        {"match": m1, "outcome_code": "HOME", "odds": "1.40"},
        {"match": m2, "outcome_code": "HOME", "odds": "2.00"},
    ], stake=Decimal("5000"))

    result = settle_parlays(db_session)

    db_session.refresh(bet)
    assert result["settled"] == 1
    assert result["lost"] == 1
    assert bet.status == BetStatus.LOST
    assert bet.pnl == Decimal("-5000.00")


# ---------------------------------------------------------------------------
# S3 — Un leg PENDING (partido no terminado) → parlay PENDING
# ---------------------------------------------------------------------------


def test_settle_parlays_pending_leg_stays_pending(db_session):
    """Un leg con partido SCHEDULED → parlay queda PENDING."""
    comp = _make_competition(db_session)
    h1, a1 = _make_teams(db_session, "s3a")
    h2, a2 = _make_teams(db_session, "s3b")

    m1 = _make_match(db_session, comp, h1, a1, home_score=2, away_score=0)  # FINISHED
    m2 = _make_match(db_session, comp, h2, a2, status=MatchStatus.SCHEDULED)  # still pending

    bet = _make_parlay(db_session, [
        {"match": m1, "outcome_code": "HOME", "odds": "1.40"},
        {"match": m2, "outcome_code": "AWAY", "odds": "2.00"},
    ], stake=Decimal("5000"))

    result = settle_parlays(db_session)

    db_session.refresh(bet)
    assert result["settled"] == 0
    assert bet.status == BetStatus.PENDING
    assert bet.pnl is None


# ---------------------------------------------------------------------------
# S4 — No-regresión: settle_bets no toca parlays
# ---------------------------------------------------------------------------


def test_settle_bets_does_not_touch_parlays(db_session):
    """settle_bets solo procesa apuestas SINGLE; parlays quedan PENDING."""
    comp = _make_competition(db_session)
    h1, a1 = _make_teams(db_session, "nr1")
    h2, a2 = _make_teams(db_session, "nr2")

    # SINGLE bet — will be settled by settle_bets
    m_single = _make_match(db_session, comp, h1, a1, home_score=2, away_score=0)
    single_bet = BetLog(
        match_id=m_single.id,
        outcome_code="HOME",
        value_signal_id=None,
        mode=BetMode.REAL,
        stake=Decimal("1000"),
        odds_taken=1.80,
        status=BetStatus.PENDING,
    )
    db_session.add(single_bet)
    db_session.flush()

    # PARLAY bet — should NOT be touched by settle_bets
    m2 = _make_match(db_session, comp, h2, a2, home_score=1, away_score=0)
    m3_scheduled = _make_match(db_session, comp, h1, a2, status=MatchStatus.SCHEDULED)
    parlay_bet = _make_parlay(db_session, [
        {"match": m2, "outcome_code": "HOME", "odds": "1.50"},
        {"match": m3_scheduled, "outcome_code": "AWAY", "odds": "2.00"},
    ])

    # settle_bets settles the single, leaves parlay alone
    result_bets = settle_bets(db_session)
    db_session.refresh(single_bet)
    db_session.refresh(parlay_bet)

    assert result_bets["settled"] == 1
    assert single_bet.status == BetStatus.WON
    assert parlay_bet.status == BetStatus.PENDING  # untouched


# ---------------------------------------------------------------------------
# S5 — Idempotencia: re-run sobre parlay ya WON → 0 cambios
# ---------------------------------------------------------------------------


def test_settle_parlays_idempotent(db_session):
    """Re-run sobre parlay ya WON → 0 cambios adicionales."""
    comp = _make_competition(db_session)
    h1, a1 = _make_teams(db_session, "id1")
    h2, a2 = _make_teams(db_session, "id2")

    m1 = _make_match(db_session, comp, h1, a1, home_score=1, away_score=0)  # HOME
    m2 = _make_match(db_session, comp, h2, a2, home_score=0, away_score=2)  # AWAY

    bet = _make_parlay(db_session, [
        {"match": m1, "outcome_code": "HOME", "odds": "1.50"},
        {"match": m2, "outcome_code": "AWAY", "odds": "2.00"},
    ], stake=Decimal("1000"))

    settle_parlays(db_session)
    db_session.refresh(bet)
    first_pnl = bet.pnl
    first_settled_at = bet.settled_at

    # Second run
    result2 = settle_parlays(db_session)
    db_session.refresh(bet)
    assert result2["settled"] == 0
    assert bet.pnl == first_pnl
    assert bet.settled_at == first_settled_at
