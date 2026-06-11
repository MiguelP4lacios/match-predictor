"""TDD — Router de apuestas REAL: POST/GET/DELETE /api/v1/bets + /paper per-mode.

Escenarios (verbatim de spec real-bets + api-readonly R6):
  POST:
    - 201 match SCHEDULED, stake=12000, odds=1.40, outcome=HOME
    - 404 match_id=9999
    - 422 odds=0.90
    - 422 stake=0
    - 422 match FINISHED
  GET:
    - ?mode=REAL → 3 ítems
    - ?mode=REAL&status=pending → 2 ítems
  DELETE:
    - REAL PENDING → 204
    - WON → 409
    - PAPER → 400
    - 9999 → 404
  GET /api/v1/paper per-mode:
    - REAL staked=24000 returns=28800 → roi=0.20
    - REAL sin settled → roi=null
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

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


def _make_match_for_bets(session, status=MatchStatus.SCHEDULED) -> Match:
    comp = Competition(name="Bets Test Comp", kind=CompetitionKind.WORLD_CUP)
    session.add(comp)
    session.flush()

    home = Team(name=f"Bets Home {id(session)}{status}")
    away = Team(name=f"Bets Away {id(session)}{status}")
    session.add_all([home, away])
    session.flush()

    m = Match(
        competition_id=comp.id,
        match_date=date(2026, 7, 10),
        home_team_id=home.id,
        away_team_id=away.id,
        status=status,
        home_score=1 if status == MatchStatus.FINISHED else None,
        away_score=0 if status == MatchStatus.FINISHED else None,
    )
    session.add(m)
    session.flush()
    return m


def _make_paper_signal(session) -> ValueSignal:
    """Crea infraestructura mínima para una apuesta PAPER."""
    comp = Competition(name="Paper Bets Comp", kind=CompetitionKind.FRIENDLY)
    session.add(comp)
    session.flush()

    home = Team(name=f"PB Home {id(session)}")
    away = Team(name=f"PB Away {id(session)}")
    session.add_all([home, away])
    session.flush()

    match = Match(
        competition_id=comp.id,
        match_date=date(2026, 6, 15),
        home_team_id=home.id,
        away_team_id=away.id,
        status=MatchStatus.FINISHED,
        home_score=1,
        away_score=0,
    )
    session.add(match)
    session.flush()

    mv = ModelVersion(name=f"pb-mv-{id(session)}", params_json={})
    session.add(mv)
    session.flush()

    pred = Prediction(
        match_id=match.id,
        model_version_id=mv.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code="HOME",
        probability=0.55,
        low_confidence=False,
    )
    session.add(pred)
    session.flush()

    odds = Odds(
        match_id=match.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code="HOME",
        bookmaker="Pinnacle",
        decimal_odds=2.00,
        captured_at=datetime(2026, 6, 14, 10, 0, tzinfo=UTC),
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
# POST /api/v1/bets — 201 success
# ---------------------------------------------------------------------------


def test_post_bet_real_201(client, db_session):
    """POST con match SCHEDULED, stake=12000, odds=1.40, HOME → 201."""
    match = _make_match_for_bets(db_session, MatchStatus.SCHEDULED)

    resp = client.post(
        "/api/v1/bets",
        json={
            "match_id": match.id,
            "outcome_code": "HOME",
            "odds_taken": 1.40,
            "stake": 12000,
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] > 0
    assert body["mode"] == "real"
    assert body["status"] == "pending"
    assert body["match_id"] == match.id
    assert body["outcome_code"] == "HOME"
    assert float(body["odds_taken"]) == pytest.approx(1.40)
    assert float(body["stake"]) == pytest.approx(12000.0)
    assert body["pnl"] is None
    assert body["placed_at"] is not None


# ---------------------------------------------------------------------------
# POST — 404 match not found
# ---------------------------------------------------------------------------


def test_post_bet_404_match_not_found(client, db_session):
    """match_id que no existe → 404."""
    resp = client.post(
        "/api/v1/bets",
        json={
            "match_id": 999_999_999,
            "outcome_code": "HOME",
            "odds_taken": 1.40,
            "stake": 12000,
        },
    )
    assert resp.status_code == 404
    assert "Match not found" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST — 422 odds inválidas
# ---------------------------------------------------------------------------


def test_post_bet_422_invalid_odds(client, db_session):
    """odds_taken=0.90 → 422."""
    match = _make_match_for_bets(db_session)
    resp = client.post(
        "/api/v1/bets",
        json={
            "match_id": match.id,
            "outcome_code": "HOME",
            "odds_taken": 0.90,
            "stake": 12000,
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST — 422 stake cero
# ---------------------------------------------------------------------------


def test_post_bet_422_zero_stake(client, db_session):
    """stake=0 → 422."""
    match = _make_match_for_bets(db_session)
    resp = client.post(
        "/api/v1/bets",
        json={
            "match_id": match.id,
            "outcome_code": "HOME",
            "odds_taken": 1.40,
            "stake": 0,
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST — 422 match FINISHED
# ---------------------------------------------------------------------------


def test_post_bet_422_match_finished(client, db_session):
    """match con status=FINISHED → 422 (no se puede apostar)."""
    match = _make_match_for_bets(db_session, MatchStatus.FINISHED)
    resp = client.post(
        "/api/v1/bets",
        json={
            "match_id": match.id,
            "outcome_code": "HOME",
            "odds_taken": 1.40,
            "stake": 12000,
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/bets?mode=REAL → 3 ítems
# ---------------------------------------------------------------------------


def test_get_bets_filter_mode_real(client, db_session):
    """GET ?mode=REAL retorna exactamente las apuestas REAL."""
    from sqlalchemy import text

    db_session.execute(text("DELETE FROM bet_log"))
    db_session.flush()

    match = _make_match_for_bets(db_session)

    # 3 REAL bets
    for _ in range(3):
        bet = BetLog(
            value_signal_id=None,
            match_id=match.id,
            outcome_code="HOME",
            mode=BetMode.REAL,
            stake=Decimal("1000.00"),
            odds_taken=1.50,
            status=BetStatus.PENDING,
        )
        db_session.add(bet)

    # 2 PAPER bets
    sig = _make_paper_signal(db_session)
    for _ in range(2):
        bet = BetLog(
            value_signal_id=sig.id,
            mode=BetMode.PAPER,
            stake=Decimal("100.00"),
            odds_taken=2.00,
            status=BetStatus.PENDING,
        )
        db_session.add(bet)

    db_session.flush()

    resp = client.get("/api/v1/bets?mode=REAL")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3
    for item in items:
        assert item["mode"] == "real"


# ---------------------------------------------------------------------------
# GET /api/v1/bets?mode=REAL&status=pending → 2 ítems
# ---------------------------------------------------------------------------


def test_get_bets_filter_mode_and_status(client, db_session):
    """GET ?mode=REAL&status=pending retorna exactamente los REAL PENDING."""
    from sqlalchemy import text

    db_session.execute(text("DELETE FROM bet_log"))
    db_session.flush()

    match = _make_match_for_bets(db_session)

    # 2 REAL PENDING
    for _ in range(2):
        db_session.add(
            BetLog(
                value_signal_id=None,
                match_id=match.id,
                outcome_code="HOME",
                mode=BetMode.REAL,
                stake=Decimal("1000.00"),
                odds_taken=1.50,
                status=BetStatus.PENDING,
            )
        )

    # 1 REAL WON
    db_session.add(
        BetLog(
            value_signal_id=None,
            match_id=match.id,
            outcome_code="HOME",
            mode=BetMode.REAL,
            stake=Decimal("1000.00"),
            odds_taken=1.50,
            status=BetStatus.WON,
            pnl=Decimal("500.00"),
        )
    )
    db_session.flush()

    resp = client.get("/api/v1/bets?mode=REAL&status=pending")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    for item in items:
        assert item["status"] == "pending"


# ---------------------------------------------------------------------------
# DELETE REAL PENDING → 204
# ---------------------------------------------------------------------------


def test_delete_real_pending_204(client, db_session):
    """DELETE REAL PENDING → 204, fila eliminada."""
    match = _make_match_for_bets(db_session)
    bet = BetLog(
        value_signal_id=None,
        match_id=match.id,
        outcome_code="HOME",
        mode=BetMode.REAL,
        stake=Decimal("1000.00"),
        odds_taken=1.50,
        status=BetStatus.PENDING,
    )
    db_session.add(bet)
    db_session.flush()

    resp = client.delete(f"/api/v1/bets/{bet.id}")
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# DELETE WON → 409
# ---------------------------------------------------------------------------


def test_delete_won_409(client, db_session):
    """DELETE apuesta WON → 409 (ya liquidada)."""
    match = _make_match_for_bets(db_session)
    bet = BetLog(
        value_signal_id=None,
        match_id=match.id,
        outcome_code="HOME",
        mode=BetMode.REAL,
        stake=Decimal("1000.00"),
        odds_taken=1.50,
        status=BetStatus.WON,
        pnl=Decimal("500.00"),
    )
    db_session.add(bet)
    db_session.flush()

    resp = client.delete(f"/api/v1/bets/{bet.id}")
    assert resp.status_code == 409
    assert "settled" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# DELETE PAPER → 400
# ---------------------------------------------------------------------------


def test_delete_paper_400(client, db_session):
    """DELETE apuesta PAPER → 400 (no se borra manualmente)."""
    sig = _make_paper_signal(db_session)
    bet = BetLog(
        value_signal_id=sig.id,
        mode=BetMode.PAPER,
        stake=Decimal("10.00"),
        odds_taken=2.00,
        status=BetStatus.PENDING,
    )
    db_session.add(bet)
    db_session.flush()

    resp = client.delete(f"/api/v1/bets/{bet.id}")
    assert resp.status_code == 400
    assert "PAPER" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# DELETE 9999 → 404
# ---------------------------------------------------------------------------


def test_delete_nonexistent_404(client, db_session):
    """DELETE id que no existe → 404."""
    resp = client.delete("/api/v1/bets/999999999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/paper — REAL staked=24000 returns=28800 → roi=0.20
# ---------------------------------------------------------------------------


def test_paper_real_roi_positive(client, db_session):
    """GET /paper: REAL staked=24000 returns=28800 → roi=0.20."""
    from sqlalchemy import text

    db_session.execute(text("DELETE FROM bet_log"))
    db_session.flush()

    match = _make_match_for_bets(db_session)

    # REAL WON: stake=12000, pnl=+4800 → returns=16800
    db_session.add(
        BetLog(
            value_signal_id=None,
            match_id=match.id,
            outcome_code="HOME",
            mode=BetMode.REAL,
            stake=Decimal("12000.00"),
            odds_taken=1.40,
            status=BetStatus.WON,
            pnl=Decimal("4800.00"),
        )
    )
    # REAL LOST: stake=12000, pnl=-12000 → returns=0
    db_session.add(
        BetLog(
            value_signal_id=None,
            match_id=match.id,
            outcome_code="HOME",
            mode=BetMode.REAL,
            stake=Decimal("12000.00"),
            odds_taken=1.40,
            status=BetStatus.LOST,
            pnl=Decimal("-12000.00"),
        )
    )
    db_session.flush()

    resp = client.get("/api/v1/paper")
    assert resp.status_code == 200
    body = resp.json()

    assert "real" in body
    assert float(body["real"]["staked"]) == pytest.approx(24000.0)
    assert float(body["real"]["returns"]) == pytest.approx(16800.0)
    # roi = (4800 - 12000) / 24000 = -7200/24000 = -0.30
    assert body["real"]["roi"] == pytest.approx(-0.30, abs=1e-4)


# ---------------------------------------------------------------------------
# GET /api/v1/paper — REAL roi=0.20 (net positive)
# ---------------------------------------------------------------------------


def test_paper_real_roi_0_20(client, db_session):
    """GET /paper: 2 REAL bets staked=24000 returns=28800 → roi=0.20."""
    from sqlalchemy import text

    db_session.execute(text("DELETE FROM bet_log"))
    db_session.flush()

    match = _make_match_for_bets(db_session)

    # 1 WON stake=24000 pnl=4800 → returns=28800 → roi=4800/24000=0.20
    db_session.add(
        BetLog(
            value_signal_id=None,
            match_id=match.id,
            outcome_code="HOME",
            mode=BetMode.REAL,
            stake=Decimal("24000.00"),
            odds_taken=1.20,
            status=BetStatus.WON,
            pnl=Decimal("4800.00"),
        )
    )
    db_session.flush()

    resp = client.get("/api/v1/paper")
    assert resp.status_code == 200
    body = resp.json()
    assert "real" in body
    assert float(body["real"]["staked"]) == pytest.approx(24000.0)
    assert float(body["real"]["returns"]) == pytest.approx(28800.0)
    assert body["real"]["roi"] == pytest.approx(0.20, abs=1e-4)


# ---------------------------------------------------------------------------
# GET /api/v1/paper — REAL sin settled → roi null
# ---------------------------------------------------------------------------


def test_paper_real_roi_null_no_settled(client, db_session):
    """GET /paper: todas las REAL son PENDING → real.roi=null."""
    from sqlalchemy import text

    db_session.execute(text("DELETE FROM bet_log"))
    db_session.flush()

    match = _make_match_for_bets(db_session)
    db_session.add(
        BetLog(
            value_signal_id=None,
            match_id=match.id,
            outcome_code="HOME",
            mode=BetMode.REAL,
            stake=Decimal("5000.00"),
            odds_taken=1.50,
            status=BetStatus.PENDING,
        )
    )
    db_session.flush()

    resp = client.get("/api/v1/paper")
    assert resp.status_code == 200
    body = resp.json()
    assert "real" in body
    assert body["real"]["settled"] == 0
    assert body["real"]["roi"] is None
