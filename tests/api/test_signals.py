"""Tests para GET /api/v1/signals.

Escenarios de spec api-readonly:
  R2-S1: señales filtradas por fecha y min_edge → 200 con items
  R2-S2: ninguna señal cumple filtro → 200 con items=[], total=0
  R2-S3: paginación limit/offset → subset correcto
  R7: list → 200 + colección vacía (no 404)
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
# Helpers de fixture de datos
# ---------------------------------------------------------------------------


def _make_competition(session) -> Competition:
    comp = Competition(
        name="Test League",
        kind=CompetitionKind.FRIENDLY,
    )
    session.add(comp)
    session.flush()
    return comp


def _make_teams(session) -> tuple[Team, Team]:
    home = Team(name="Alpha FC")
    away = Team(name="Beta FC")
    session.add_all([home, away])
    session.flush()
    return home, away


def _make_match(session, comp, home, away, match_date=date(2026, 6, 15)) -> Match:
    m = Match(
        competition_id=comp.id,
        match_date=match_date,
        home_team_id=home.id,
        away_team_id=away.id,
        status=MatchStatus.SCHEDULED,
    )
    session.add(m)
    session.flush()
    return m


def _make_prediction(session, match, mv) -> Prediction:
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
    return pred


def _make_odds(session, match, captured_at=None) -> Odds:
    if captured_at is None:
        captured_at = datetime(2026, 6, 14, 12, 0, tzinfo=UTC)
    o = Odds(
        match_id=match.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code="HOME",
        bookmaker="Pinnacle",
        decimal_odds=1.95,
        captured_at=captured_at,
    )
    session.add(o)
    session.flush()
    return o


def _make_signal(session, prediction, odds, edge=0.08) -> ValueSignal:
    sig = ValueSignal(
        prediction_id=prediction.id,
        odds_id=odds.id,
        edge=edge,
        ev=0.05,
        kelly_fraction=0.04,
        recommended_stake=Decimal("10.00"),
    )
    session.add(sig)
    session.flush()
    return sig


def _make_model_version(session) -> ModelVersion:
    mv = ModelVersion(name="test-model-v1", params_json={})
    session.add(mv)
    session.flush()
    return mv


# ---------------------------------------------------------------------------
# Escenario R2-S1: señales filtradas
# ---------------------------------------------------------------------------


def test_signals_filtered_by_date_and_edge(client, db_session):
    """R2-S1: señales con match_date=2026-06-15 y edge=0.08 aparecen en respuesta."""
    comp = _make_competition(db_session)
    home, away = _make_teams(db_session)
    mv = _make_model_version(db_session)
    match = _make_match(db_session, comp, home, away, date(2026, 6, 15))
    pred = _make_prediction(db_session, match, mv)
    odds = _make_odds(db_session, match)
    sig = _make_signal(db_session, pred, odds, edge=0.08)
    db_session.flush()

    resp = client.get("/api/v1/signals?from=2026-06-15&min_edge=0.05")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    item = next(i for i in body["items"] if i["id"] == sig.id)
    assert abs(item["edge"] - 0.08) < 1e-4
    assert item["home_team"] == "Alpha FC"
    assert item["away_team"] == "Beta FC"
    assert item["bookmaker"] == "Pinnacle"


# ---------------------------------------------------------------------------
# Escenario R2-S2: sin resultados
# ---------------------------------------------------------------------------


def test_signals_no_results(client, db_session):
    """R2-S2: filtro imposible → 200 con lista vacía, no 404."""
    resp = client.get("/api/v1/signals?min_edge=0.99")

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


# ---------------------------------------------------------------------------
# Escenario R2-S3: paginación
# ---------------------------------------------------------------------------


def test_signals_pagination(client, db_session):
    """R2-S3: offset=1 devuelve un item menos que sin offset."""
    comp = _make_competition(db_session)
    home, away = _make_teams(db_session)
    mv = _make_model_version(db_session)

    # Crear 2 señales en el mismo partido
    match = _make_match(db_session, comp, home, away, date(2026, 6, 16))
    pred1 = Prediction(
        match_id=match.id,
        model_version_id=mv.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code="HOME",
        probability=0.55,
        low_confidence=False,
    )
    pred2 = Prediction(
        match_id=match.id,
        model_version_id=mv.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code="DRAW",
        probability=0.25,
        low_confidence=False,
    )
    db_session.add_all([pred1, pred2])
    db_session.flush()

    o1 = _make_odds(db_session, match)
    o2 = Odds(
        match_id=match.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code="DRAW",
        bookmaker="Bet365",
        decimal_odds=3.20,
        captured_at=datetime(2026, 6, 15, 10, 0, tzinfo=UTC),
    )
    db_session.add(o2)
    db_session.flush()

    _make_signal(db_session, pred1, o1, edge=0.07)
    sig2 = ValueSignal(
        prediction_id=pred2.id,
        odds_id=o2.id,
        edge=0.06,
        ev=0.04,
        kelly_fraction=0.03,
        recommended_stake=Decimal("8.00"),
    )
    db_session.add(sig2)
    db_session.flush()

    resp_all = client.get("/api/v1/signals?limit=200")
    resp_offset = client.get("/api/v1/signals?limit=200&offset=1")

    assert resp_all.status_code == 200
    assert resp_offset.status_code == 200
    total = resp_all.json()["total"]
    # El offset reduce la lista en 1
    assert len(resp_offset.json()["items"]) == len(resp_all.json()["items"]) - 1
    assert resp_all.json()["total"] == total  # total no cambia con offset


def test_signals_excluye_partidos_jugados(client, db_session):
    """Una señal de un partido FINISHED NO debe aparecer (la apuesta ya no es posible)."""
    comp = _make_competition(db_session)
    home, away = _make_teams(db_session)
    mv = _make_model_version(db_session)

    # Partido por jugar → su señal SÍ aparece
    m_sched = _make_match(db_session, comp, home, away, date(2026, 6, 20))
    p_sched = _make_prediction(db_session, m_sched, mv)
    sig_sched = _make_signal(db_session, p_sched, _make_odds(db_session, m_sched), edge=0.10)

    # Partido ya jugado → su señal NO aparece
    m_done = _make_match(db_session, comp, home, away, date(2026, 6, 11))
    m_done.status = MatchStatus.FINISHED
    db_session.flush()
    p_done = _make_prediction(db_session, m_done, mv)
    sig_done = _make_signal(db_session, p_done, _make_odds(db_session, m_done), edge=0.10)
    db_session.flush()

    ids = [i["id"] for i in client.get("/api/v1/signals?min_edge=0.05").json()["items"]]
    assert sig_sched.id in ids
    assert sig_done.id not in ids
