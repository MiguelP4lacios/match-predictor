"""Tests para GET /api/v1/paper.

Escenarios de spec api-readonly:
  R6-S1: ROI numérico exacto con WON + LOST + PENDING
  R6-S2: solo apuestas PENDING → roi=null sin error
"""

from datetime import UTC
from decimal import Decimal

from sqlalchemy import text

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


def _make_signal_for_bet(session) -> ValueSignal:
    """Crea los registros mínimos requeridos para un BetLog."""
    comp = Competition(name="Paper Test League", kind=CompetitionKind.FRIENDLY)
    session.add(comp)
    session.flush()

    h = Team(name="Paper Home")
    a = Team(name="Paper Away")
    session.add_all([h, a])
    session.flush()

    match = Match(
        competition_id=comp.id,
        match_date=__import__("datetime").date(2026, 6, 25),
        home_team_id=h.id,
        away_team_id=a.id,
        status=MatchStatus.FINISHED,
        home_score=2,
        away_score=1,
    )
    session.add(match)
    session.flush()

    mv = ModelVersion(name="paper-mv", params_json={})
    session.add(mv)
    session.flush()

    pred = Prediction(
        match_id=match.id,
        model_version_id=mv.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code="HOME",
        probability=0.60,
        low_confidence=False,
    )
    session.add(pred)
    session.flush()

    from datetime import datetime

    odds = Odds(
        match_id=match.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code="HOME",
        bookmaker="Pinnacle",
        decimal_odds=1.90,
        captured_at=datetime(2026, 6, 24, 10, 0, tzinfo=UTC),
    )
    session.add(odds)
    session.flush()

    sig = ValueSignal(
        prediction_id=pred.id,
        odds_id=odds.id,
        edge=0.07,
        ev=0.05,
        kelly_fraction=0.04,
        recommended_stake=Decimal("10.00"),
    )
    session.add(sig)
    session.flush()
    return sig


# ---------------------------------------------------------------------------
# R6-S1: ROI numérico
# ---------------------------------------------------------------------------


def test_paper_roi_numeric(client, db_session):
    """R6-S1: ROI = (40-30)/(50+30) = 0.125 con WON + LOST + PENDING."""
    # Limpiar bet_logs existentes dentro del SAVEPOINT para tener conteos exactos
    db_session.execute(text("DELETE FROM bet_log"))
    db_session.flush()

    sig = _make_signal_for_bet(db_session)

    bet_won = BetLog(
        value_signal_id=sig.id,
        mode=BetMode.PAPER,
        stake=Decimal("50.00"),
        odds_taken=1.80,
        status=BetStatus.WON,
        pnl=Decimal("40.00"),
    )
    bet_lost = BetLog(
        value_signal_id=sig.id,
        mode=BetMode.PAPER,
        stake=Decimal("30.00"),
        odds_taken=1.80,
        status=BetStatus.LOST,
        pnl=Decimal("-30.00"),
    )
    bet_pending = BetLog(
        value_signal_id=sig.id,
        mode=BetMode.PAPER,
        stake=Decimal("20.00"),
        odds_taken=1.80,
        status=BetStatus.PENDING,
    )
    db_session.add_all([bet_won, bet_lost, bet_pending])
    db_session.flush()

    resp = client.get("/api/v1/paper")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert body["open"] == 1
    assert body["settled"] == 2
    assert body["roi"] is not None
    assert abs(body["roi"] - 0.125) < 1e-4


# ---------------------------------------------------------------------------
# R6-S2: solo PENDING → roi null
# ---------------------------------------------------------------------------


def test_paper_roi_null_when_no_settled(client, db_session):
    """R6-S2: sin apuestas WON/LOST → roi=null sin error."""
    sig = _make_signal_for_bet(db_session)
    bet = BetLog(
        value_signal_id=sig.id,
        mode=BetMode.PAPER,
        stake=Decimal("20.00"),
        odds_taken=1.80,
        status=BetStatus.PENDING,
    )
    db_session.add(bet)
    db_session.flush()

    resp = client.get("/api/v1/paper")

    assert resp.status_code == 200
    body = resp.json()
    assert body["roi"] is None
    assert body["open"] >= 1
    assert body["settled"] == 0
