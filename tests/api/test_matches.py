"""Tests para GET /api/v1/matches/upcoming y GET /api/v1/matches/{id}.

Escenarios de spec api-readonly:
  R3-S1: partido SCHEDULED con predicciones 1X2 → probs correctas
  R3-S2: partido SCHEDULED sin predicciones → p_home=null, etc.
  R4-S1: detalle partido existente → 200 con predictions y last_odds
  R4-S2: partido inexistente → 404 con detail="Match not found"
  R7: /matches/upcoming → 200 + lista vacía (no 404)
"""

from datetime import UTC, date, datetime

from app.models.competition import Competition
from app.models.enums import CompetitionKind, MarketType, MatchStatus
from app.models.match import Match
from app.models.model import ModelVersion, Prediction
from app.models.odds import Odds
from app.models.team import Team

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _comp(session) -> Competition:
    c = Competition(name="WC Test", kind=CompetitionKind.WORLD_CUP)
    session.add(c)
    session.flush()
    return c


def _teams(session) -> tuple[Team, Team]:
    h = Team(name="Home Side")
    a = Team(name="Away Side")
    session.add_all([h, a])
    session.flush()
    return h, a


def _match(session, comp, home, away, status=MatchStatus.SCHEDULED, d=date(2026, 6, 20)) -> Match:
    m = Match(
        competition_id=comp.id,
        match_date=d,
        home_team_id=home.id,
        away_team_id=away.id,
        status=status,
    )
    session.add(m)
    session.flush()
    return m


def _mv(session) -> ModelVersion:
    mv = ModelVersion(name="mv-matches-test", params_json={})
    session.add(mv)
    session.flush()
    return mv


def _add_1x2_predictions(session, match_id, mv_id, p_home=0.55, p_draw=0.25, p_away=0.20):
    preds = [
        Prediction(
            match_id=match_id,
            model_version_id=mv_id,
            market_type=MarketType.MATCH_1X2,
            outcome_code="HOME",
            probability=p_home,
            low_confidence=False,
        ),
        Prediction(
            match_id=match_id,
            model_version_id=mv_id,
            market_type=MarketType.MATCH_1X2,
            outcome_code="DRAW",
            probability=p_draw,
            low_confidence=False,
        ),
        Prediction(
            match_id=match_id,
            model_version_id=mv_id,
            market_type=MarketType.MATCH_1X2,
            outcome_code="AWAY",
            probability=p_away,
            low_confidence=False,
        ),
    ]
    session.add_all(preds)
    session.flush()
    return preds


# ---------------------------------------------------------------------------
# R3-S1: upcoming con predicciones
# ---------------------------------------------------------------------------


def test_upcoming_with_predictions(client, db_session):
    """R3-S1: partido SCHEDULED con 1X2 → probabilidades exactas y low_confidence."""
    comp = _comp(db_session)
    home, away = _teams(db_session)
    mv = _mv(db_session)
    m = _match(db_session, comp, home, away)
    _add_1x2_predictions(db_session, m.id, mv.id, 0.55, 0.25, 0.20)

    resp = client.get("/api/v1/matches/upcoming")

    assert resp.status_code == 200
    items = resp.json()
    item = next(i for i in items if i["id"] == m.id)
    assert abs(item["p_home"] - 0.55) < 1e-4
    assert abs(item["p_draw"] - 0.25) < 1e-4
    assert abs(item["p_away"] - 0.20) < 1e-4
    assert item["low_confidence"] is False


# ---------------------------------------------------------------------------
# R3-S2: upcoming sin predicciones
# ---------------------------------------------------------------------------


def test_upcoming_without_predictions(client, db_session):
    """R3-S2: partido SCHEDULED sin predicciones → p_home/draw/away son null."""
    comp = _comp(db_session)
    home, away = _teams(db_session)
    m = _match(db_session, comp, home, away, d=date(2026, 6, 21))

    resp = client.get("/api/v1/matches/upcoming")

    assert resp.status_code == 200
    items = resp.json()
    item = next(i for i in items if i["id"] == m.id)
    assert item["p_home"] is None
    assert item["p_draw"] is None
    assert item["p_away"] is None


# ---------------------------------------------------------------------------
# R7: upcoming devuelve 200 + lista vacía si no hay SCHEDULED
# ---------------------------------------------------------------------------


def test_upcoming_empty_returns_200(client, db_session):
    """R7: ningún partido SCHEDULED → 200 con lista, no 404."""
    resp = client.get("/api/v1/matches/upcoming")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# R4-S1: detalle partido existente
# ---------------------------------------------------------------------------


def test_match_detail_found(client, db_session):
    """R4-S1: partido id=X con predictions y odds → 200 con datos completos."""
    comp = _comp(db_session)
    home, away = _teams(db_session)
    mv = _mv(db_session)
    m = _match(db_session, comp, home, away)
    _add_1x2_predictions(db_session, m.id, mv.id)

    o = Odds(
        match_id=m.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code="HOME",
        bookmaker="Pinnacle",
        decimal_odds=1.85,
        captured_at=datetime(2026, 6, 19, 10, 0, tzinfo=UTC),
    )
    db_session.add(o)
    db_session.flush()

    resp = client.get(f"/api/v1/matches/{m.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == m.id
    assert body["home_team"] == "Home Side"
    assert len(body["predictions"]) == 3
    assert len(body["last_odds"]) >= 1


# ---------------------------------------------------------------------------
# R4-S2: partido no encontrado → 404
# ---------------------------------------------------------------------------


def test_match_detail_not_found(client, db_session):
    """R4-S2: match id=9999 no existe → 404 con detail='Match not found'."""
    resp = client.get("/api/v1/matches/9999999")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Match not found"
