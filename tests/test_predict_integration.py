"""Tests de integración para predict_1x2 (usa db_session con SAVEPOINT).

Spec: model-1x2 — Req: Point-in-Time Rating Lookup + Prediction Persistence
TDD RED: fallan hasta que predict_1x2.py exista.
"""

import datetime

from sqlalchemy import func, select

from app.model.predict_1x2 import predict_match
from app.models import EloRating, Match, ModelVersion, Prediction, Team
from app.models.enums import CompetitionKind, MatchStatus

# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------


def _make_team(session, name: str) -> Team:
    """Inserta un equipo y devuelve la instancia."""
    t = Team(name=name)
    session.add(t)
    session.flush()
    return t


def _make_competition(session):
    from app.models import Competition

    c = Competition(name="Test WC", kind=CompetitionKind.WORLD_CUP)
    session.add(c)
    session.flush()
    return c


def _make_match(session, comp, home: Team, away: Team, date: datetime.date) -> Match:
    m = Match(
        competition_id=comp.id,
        match_date=date,
        home_team_id=home.id,
        away_team_id=away.id,
        neutral_site=False,
        status=MatchStatus.SCHEDULED,
        went_to_extra_time=False,
        went_to_penalties=False,
    )
    session.add(m)
    session.flush()
    return m


def _make_model_version(session, name: str = "1x2-olm-test-sc05") -> ModelVersion:
    mv = ModelVersion(
        name=name,
        params_json={
            "model": "A-olm",
            "cutpoints": {"a1": -0.50, "delta": 1.0},
            "beta_diff": 0.004,
            "beta_neutral": -0.30,
        },
    )
    session.add(mv)
    session.flush()
    return mv


def _add_elo(session, team_id: int, date: datetime.date, rating: float) -> None:
    er = EloRating(team_id=team_id, rating_date=date, rating=rating)
    session.add(er)
    session.flush()


# ---------------------------------------------------------------------------
# SC-OLM-05: Anti-look-ahead — rating 2017-12-31 (1650) vs 2018-01-15 (1670)
# Partido en 2018-01-15 → debe usarse 1650, NOT 1670
# ---------------------------------------------------------------------------


def test_predict_uses_rating_strictly_before_match_date(db_session):
    """SC-OLM-05: rating_date < match_date; NO se usa el rating del mismo día."""
    comp = _make_competition(db_session)
    home = _make_team(db_session, "TeamAlpha")
    away = _make_team(db_session, "TeamBeta")
    match = _make_match(db_session, comp, home, away, datetime.date(2018, 1, 15))
    mv = _make_model_version(db_session)

    # Rating del día del partido (NO debe usarse)
    _add_elo(db_session, home.id, datetime.date(2018, 1, 15), 1670.0)
    # Rating antes del partido (debe usarse)
    _add_elo(db_session, home.id, datetime.date(2017, 12, 31), 1650.0)

    # Rating para el visitante
    _add_elo(db_session, away.id, datetime.date(2017, 12, 31), 1500.0)

    predict_match(db_session, match_id=match.id, model_version_id=mv.id)

    # Verificar que se generaron las 3 predicciones
    count = db_session.scalar(
        select(func.count(Prediction.id)).where(Prediction.match_id == match.id)
    )
    assert count == 3

    preds = db_session.scalars(select(Prediction).where(Prediction.match_id == match.id)).all()
    assert all(not p.low_confidence for p in preds)

    # La probabilidad persistida debe salir del rating 1650 (rating_date < match_date),
    # NUNCA del 1670 del mismo día. Cancha no neutral → diff incluye +100 de localía.
    from app.model.probabilities import predict_proba

    expected = predict_proba(mv.params_json, elo_diff=(1650.0 + 100.0) - 1500.0, neutral=False)
    leaked = predict_proba(mv.params_json, elo_diff=(1670.0 + 100.0) - 1500.0, neutral=False)
    p_home = next(float(p.probability) for p in preds if p.outcome_code == "HOME")
    assert abs(p_home - expected["home"]) < 1e-5
    assert abs(p_home - leaked["home"]) > 1e-6  # con 1670 daría otro número


# ---------------------------------------------------------------------------
# SC-OLM-06: Equipo sin rating previo → effective=1500, low_confidence=True
# ---------------------------------------------------------------------------


def test_predict_defaults_to_1500_when_no_prior_rating(db_session):
    """SC-OLM-06: sin rating previo → low_confidence=True en las 3 predicciones."""
    comp = _make_competition(db_session)
    home = _make_team(db_session, "TeamGamma")
    away = _make_team(db_session, "TeamDelta")
    match = _make_match(db_session, comp, home, away, datetime.date(2020, 6, 1))
    mv = _make_model_version(db_session, name="1x2-olm-test-sc06")

    # Sin ningún elo_rating → ambos equipos sin historial

    predict_match(db_session, match_id=match.id, model_version_id=mv.id)

    preds = db_session.scalars(select(Prediction).where(Prediction.match_id == match.id)).all()
    assert len(preds) == 3
    # Ambos equipos sin rating → low_confidence debe ser True
    assert all(p.low_confidence for p in preds)


# ---------------------------------------------------------------------------
# SC-OLM-08: Idempotencia — 2 runs → exactamente 3 filas
# ---------------------------------------------------------------------------


def test_predict_idempotent_two_runs(db_session):
    """SC-OLM-08: ejecutar predict_match dos veces → exactamente 3 filas (upsert)."""
    comp = _make_competition(db_session)
    home = _make_team(db_session, "TeamEpsilon")
    away = _make_team(db_session, "TeamZeta")
    match = _make_match(db_session, comp, home, away, datetime.date(2020, 7, 1))
    mv = _make_model_version(db_session, name="1x2-olm-test-sc08")

    _add_elo(db_session, home.id, datetime.date(2020, 6, 1), 1600.0)
    _add_elo(db_session, away.id, datetime.date(2020, 6, 1), 1550.0)

    predict_match(db_session, match_id=match.id, model_version_id=mv.id)
    predict_match(db_session, match_id=match.id, model_version_id=mv.id)

    count = db_session.scalar(
        select(func.count(Prediction.id)).where(Prediction.match_id == match.id)
    )
    assert count == 3

    # Verificar que P(H)+P(D)+P(A)=1 dentro de 1e-5
    preds = db_session.scalars(select(Prediction).where(Prediction.match_id == match.id)).all()
    total = sum(float(p.probability) for p in preds)
    assert abs(total - 1.0) < 1e-5
