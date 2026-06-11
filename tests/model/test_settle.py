"""TDD — Motor de liquidación settle_bets.

Escenarios (verbatim de spec/design):
  - WON: stake=12000 odds=1.40 HOME 2-0 → pnl=+4800.00
  - LOST: stake=12000 odds=1.40 HOME 1-1 → pnl=-12000.00 settled_result=DRAW
  - Idempotencia: re-run → 0 filas modificadas
  - SCHEDULED intacto: apuesta PENDING, partido no terminado → queda PENDING
  - Penales knockout: 1-1 FINISHED → DRAW para 1X2, apuesta HOME → LOST
  - PAPER vía signal→prediction: apuesta PAPER con value_signal_id
  - commit-spy: session.commit llamado exactamente 1 vez por ejecución
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.model.settle import settle_bets
from app.models.betting import BetLog, ValueSignal
from app.models.competition import Competition
from app.models.enums import BetMode, BetStatus, CompetitionKind, MarketType, MatchStatus
from app.models.match import Match
from app.models.model import ModelVersion, Prediction
from app.models.odds import Odds
from app.models.team import Team


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_competition(session) -> Competition:
    comp = Competition(name="Settle Test", kind=CompetitionKind.WORLD_CUP)
    session.add(comp)
    session.flush()
    return comp


def _make_teams(session) -> tuple[Team, Team]:
    home = Team(name=f"Settle Home {id(session)}")
    away = Team(name=f"Settle Away {id(session)}")
    session.add_all([home, away])
    session.flush()
    return home, away


def _make_match(session, comp, home, away, status=MatchStatus.FINISHED, home_score=2, away_score=0) -> Match:
    m = Match(
        competition_id=comp.id,
        match_date=date(2026, 6, 25),
        home_team_id=home.id,
        away_team_id=away.id,
        status=status,
        home_score=home_score,
        away_score=away_score,
    )
    session.add(m)
    session.flush()
    return m


def _make_real_bet(session, match, outcome_code="HOME", stake=Decimal("12000.00"), odds=1.40) -> BetLog:
    bet = BetLog(
        value_signal_id=None,
        match_id=match.id,
        outcome_code=outcome_code,
        mode=BetMode.REAL,
        stake=stake,
        odds_taken=odds,
        status=BetStatus.PENDING,
    )
    session.add(bet)
    session.flush()
    return bet


def _make_paper_signal_bet(session, comp, home, away, match_status=MatchStatus.FINISHED, home_score=0, away_score=1) -> BetLog:
    """Apuesta PAPER via value_signal_id → prediction → match."""
    match = _make_match(session, comp, home, away, status=match_status, home_score=home_score, away_score=away_score)

    mv = ModelVersion(name=f"settle-mv-{match.id}", params_json={})
    session.add(mv)
    session.flush()

    pred = Prediction(
        match_id=match.id,
        model_version_id=mv.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code="AWAY",
        probability=0.60,
        low_confidence=False,
    )
    session.add(pred)
    session.flush()

    odds_obj = Odds(
        match_id=match.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code="AWAY",
        bookmaker="Pinnacle",
        decimal_odds=2.00,
        captured_at=datetime(2026, 6, 24, 10, 0, tzinfo=UTC),
    )
    session.add(odds_obj)
    session.flush()

    sig = ValueSignal(
        prediction_id=pred.id,
        odds_id=odds_obj.id,
        edge=0.07,
        ev=0.05,
        kelly_fraction=0.04,
        recommended_stake=Decimal("10.00"),
    )
    session.add(sig)
    session.flush()

    bet = BetLog(
        value_signal_id=sig.id,
        match_id=None,
        outcome_code=None,
        mode=BetMode.PAPER,
        stake=Decimal("10.00"),
        odds_taken=2.00,
        status=BetStatus.PENDING,
    )
    session.add(bet)
    session.flush()
    return bet


# ---------------------------------------------------------------------------
# Scenario: WON — verificación numérica
# ---------------------------------------------------------------------------


def test_settle_won_numeric(db_session):
    """stake=12000 odds=1.40 HOME 2-0 → WON pnl=+4800.00."""
    comp = _make_competition(db_session)
    home, away = _make_teams(db_session)
    match = _make_match(db_session, comp, home, away, home_score=2, away_score=0)
    bet = _make_real_bet(db_session, match)

    result = settle_bets(db_session)

    db_session.refresh(bet)
    assert result["settled"] == 1
    assert result["won"] == 1
    assert result["lost"] == 0
    assert bet.status == BetStatus.WON
    assert bet.pnl == Decimal("4800.00")
    assert bet.settled_result == "HOME"
    assert bet.settled_at is not None


# ---------------------------------------------------------------------------
# Scenario: LOST — verificación numérica
# ---------------------------------------------------------------------------


def test_settle_lost_numeric(db_session):
    """stake=12000 odds=1.40 HOME 1-1 → LOST pnl=-12000.00 settled_result=DRAW."""
    comp = _make_competition(db_session)
    home, away = _make_teams(db_session)
    match = _make_match(db_session, comp, home, away, home_score=1, away_score=1)
    bet = _make_real_bet(db_session, match)

    result = settle_bets(db_session)

    db_session.refresh(bet)
    assert result["settled"] == 1
    assert result["lost"] == 1
    assert bet.status == BetStatus.LOST
    assert bet.pnl == Decimal("-12000.00")
    assert bet.settled_result == "DRAW"


# ---------------------------------------------------------------------------
# Scenario: Idempotencia — re-run 0 cambios
# ---------------------------------------------------------------------------


def test_settle_idempotent(db_session):
    """Re-run sobre apuesta ya WON → 0 filas modificadas."""
    comp = _make_competition(db_session)
    home, away = _make_teams(db_session)
    match = _make_match(db_session, comp, home, away, home_score=2, away_score=0)
    bet = _make_real_bet(db_session, match)

    settle_bets(db_session)
    db_session.refresh(bet)
    pnl_after_first = bet.pnl
    settled_at_after_first = bet.settled_at

    # Segunda ejecución
    result2 = settle_bets(db_session)

    db_session.refresh(bet)
    assert result2["settled"] == 0
    assert bet.pnl == pnl_after_first
    assert bet.settled_at == settled_at_after_first


# ---------------------------------------------------------------------------
# Scenario: Partido no terminado — apuesta intacta
# ---------------------------------------------------------------------------


def test_settle_scheduled_match_untouched(db_session):
    """Apuesta PENDING con partido SCHEDULED → queda PENDING tras settle."""
    comp = _make_competition(db_session)
    home, away = _make_teams(db_session)
    match = _make_match(db_session, comp, home, away, status=MatchStatus.SCHEDULED, home_score=None, away_score=None)
    bet = _make_real_bet(db_session, match)

    result = settle_bets(db_session)

    db_session.refresh(bet)
    assert result["settled"] == 0
    assert bet.status == BetStatus.PENDING
    assert bet.pnl is None
    assert bet.settled_at is None


# ---------------------------------------------------------------------------
# Scenario: Penales knockout — DRAW para 1X2
# ---------------------------------------------------------------------------


def test_settle_penalties_is_draw_for_1x2(db_session):
    """Partido 1-1 FINISHED (penales decidieron) → 1X2 = DRAW; apuesta HOME → LOST."""
    comp = _make_competition(db_session)
    home, away = _make_teams(db_session)
    match = _make_match(db_session, comp, home, away, home_score=1, away_score=1)
    bet = _make_real_bet(db_session, match, outcome_code="HOME")

    settle_bets(db_session)

    db_session.refresh(bet)
    assert bet.status == BetStatus.LOST
    assert bet.settled_result == "DRAW"


# ---------------------------------------------------------------------------
# Scenario: Apuesta PAPER se liquida por signal → prediction
# ---------------------------------------------------------------------------


def test_settle_paper_via_signal_prediction(db_session):
    """Apuesta PAPER con value_signal_id → liquida via prediction.match_id y outcome_code."""
    comp = _make_competition(db_session)
    home, away = _make_teams(db_session)

    # away_score > home_score → AWAY wins; apuesta outcome=AWAY → WON
    bet = _make_paper_signal_bet(db_session, comp, home, away, home_score=0, away_score=1)

    settle_bets(db_session)

    db_session.refresh(bet)
    assert bet.status == BetStatus.WON
    assert bet.settled_result == "AWAY"


# ---------------------------------------------------------------------------
# Scenario: commit-spy — settle_bets commitea exactamente 1 vez
# ---------------------------------------------------------------------------


def test_settle_commits_exactly_once(db_session):
    """settle_bets llama session.commit exactamente 1 vez (regresión commit-boundary bug)."""
    comp = _make_competition(db_session)
    home, away = _make_teams(db_session)
    match = _make_match(db_session, comp, home, away, home_score=3, away_score=0)
    _make_real_bet(db_session, match)

    with patch.object(db_session, "commit", wraps=db_session.commit) as mock_commit:
        settle_bets(db_session)

    mock_commit.assert_called_once()
