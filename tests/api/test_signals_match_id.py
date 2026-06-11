"""Tests para SignalItem.match_id en GET /api/v1/signals.

Escenario: los ítems de señal contienen el campo match_id (int).
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.betting import ValueSignal
from app.models.competition import Competition
from app.models.enums import CompetitionKind, MarketType, MatchStatus
from app.models.match import Match
from app.models.model import ModelVersion, Prediction
from app.models.odds import Odds
from app.models.team import Team


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _seed_signal(session) -> tuple[int, int]:
    """Crea una señal mínima. Retorna (signal_id, match_id)."""
    comp = Competition(name="Signal Match Test", kind=CompetitionKind.FRIENDLY)
    session.add(comp)
    session.flush()

    home = Team(name="SMT Home")
    away = Team(name="SMT Away")
    session.add_all([home, away])
    session.flush()

    match = Match(
        competition_id=comp.id,
        match_date=date(2026, 8, 1),
        home_team_id=home.id,
        away_team_id=away.id,
        status=MatchStatus.SCHEDULED,
    )
    session.add(match)
    session.flush()

    mv = ModelVersion(name="smt-mv", params_json={})
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
        decimal_odds=2.10,
        captured_at=datetime(2026, 7, 31, 10, 0, tzinfo=UTC),
    )
    session.add(odds)
    session.flush()

    sig = ValueSignal(
        prediction_id=pred.id,
        odds_id=odds.id,
        edge=0.09,
        ev=0.07,
        kelly_fraction=0.05,
        recommended_stake=Decimal("15.00"),
    )
    session.add(sig)
    session.flush()

    return sig.id, match.id


# ---------------------------------------------------------------------------
# Test: SignalItem contains match_id
# ---------------------------------------------------------------------------


def test_signals_items_contain_match_id(client, db_session):
    """GET /api/v1/signals → cada ítem tiene match_id con el id del partido."""
    _sig_id, match_id = _seed_signal(db_session)

    resp = client.get("/api/v1/signals?limit=200")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1

    # Todos los ítems deben tener el campo match_id
    for item in body["items"]:
        assert "match_id" in item, f"match_id ausente en item {item['id']}"

    # Al menos el ítem que acabamos de crear tiene el match_id correcto
    our_items = [i for i in body["items"] if i["id"] == _sig_id]
    assert len(our_items) == 1
    assert our_items[0]["match_id"] == match_id
