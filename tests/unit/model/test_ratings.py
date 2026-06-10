"""Tests unitarios TDD para app/model/ratings.py.

Spec: lookup_rating(session, team_id, before_date)
  - Devuelve (rating, False) para el último rating_date < before_date
  - Devuelve (DEFAULT_RATING=1500.0, True) si no hay fila previa
  - DEFAULT_RATING = 1500.0
  - HOME_ADVANTAGE = 100.0

Escenario numérico (signal id=10 datos reales):
  - Mexico (team_id=57): rating=1980.33 antes del 2026-06-11
  - South Africa (team_id=21): rating=1662.98 antes del 2026-06-11
"""

import datetime
import decimal

import pytest
from sqlalchemy.orm import Session

# RED: estas importaciones fallan porque app/model/ratings.py no existe todavía
from app.model.ratings import DEFAULT_RATING, HOME_ADVANTAGE, lookup_rating
from app.models import EloRating, Team
from app.models.competition import Competition
from app.models.enums import CompetitionKind


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------


def _make_team(session: Session, name: str) -> Team:
    t = Team(name=name)
    session.add(t)
    session.flush()
    return t


def _make_elo(
    session: Session,
    team: Team,
    rating: float,
    rating_date: datetime.date,
) -> EloRating:
    elo = EloRating(team_id=team.id, rating=decimal.Decimal(str(rating)), rating_date=rating_date)
    session.add(elo)
    session.flush()
    return elo


# ---------------------------------------------------------------------------
# DEFAULT_RATING y HOME_ADVANTAGE: constantes correctas
# ---------------------------------------------------------------------------


def test_default_rating_is_1500():
    """DEFAULT_RATING debe ser exactamente 1500.0."""
    assert DEFAULT_RATING == 1500.0


def test_home_advantage_is_100():
    """HOME_ADVANTAGE debe ser exactamente 100.0."""
    assert HOME_ADVANTAGE == 100.0


# ---------------------------------------------------------------------------
# lookup_rating: sin registro previo → DEFAULT + low_confidence=True
# ---------------------------------------------------------------------------


def test_lookup_rating_fallback_when_no_prior_rating(db_session):
    """Sin rating previo, retorna (DEFAULT_RATING, True)."""
    team = _make_team(db_session, "LR_Test_NoRating")

    rating, low_confidence = lookup_rating(db_session, team.id, datetime.date(2026, 6, 11))

    assert rating == DEFAULT_RATING
    assert low_confidence is True


def test_lookup_rating_ignores_rating_on_same_date(db_session):
    """Rating con rating_date == before_date es excluido (sin look-ahead).

    La query usa < (estrictamente menor), no <=.
    """
    team = _make_team(db_session, "LR_Test_SameDate")
    _make_elo(db_session, team, 1800.0, datetime.date(2026, 6, 11))

    rating, low_confidence = lookup_rating(db_session, team.id, datetime.date(2026, 6, 11))

    assert rating == DEFAULT_RATING
    assert low_confidence is True


# ---------------------------------------------------------------------------
# lookup_rating: con registro previo → valor correcto + low_confidence=False
# ---------------------------------------------------------------------------


def test_lookup_rating_returns_latest_before_date(db_session):
    """Retorna el rating_date más reciente estrictamente antes de before_date."""
    team = _make_team(db_session, "LR_Test_TwoRatings")
    _make_elo(db_session, team, 1700.0, datetime.date(2026, 6, 1))
    _make_elo(db_session, team, 1750.0, datetime.date(2026, 6, 8))  # más reciente → ganador

    rating, low_confidence = lookup_rating(db_session, team.id, datetime.date(2026, 6, 11))

    assert abs(rating - 1750.0) < 1e-6
    assert low_confidence is False


def test_lookup_rating_returns_earlier_when_closest_excluded(db_session):
    """Cuando el rating más reciente coincide exactamente con before_date, usa el anterior."""
    team = _make_team(db_session, "LR_Test_EdgeDate")
    _make_elo(db_session, team, 1600.0, datetime.date(2026, 6, 5))
    _make_elo(db_session, team, 1650.0, datetime.date(2026, 6, 11))  # excluido (same date)

    rating, low_confidence = lookup_rating(db_session, team.id, datetime.date(2026, 6, 11))

    assert abs(rating - 1600.0) < 1e-6
    assert low_confidence is False


# ---------------------------------------------------------------------------
# Escenario numérico signal id=10 (datos reales de BD)
# ---------------------------------------------------------------------------


def test_lookup_rating_mexico_before_2026_06_11(db_session):
    """Mexico (team_id=57) → 1980.33 antes del 2026-06-11 (datos reales).

    Triangulación con datos reales de la BD: confirma que el lookup
    point-in-time funciona con la data sembrada.
    """
    rating, low_confidence = lookup_rating(db_session, 57, datetime.date(2026, 6, 11))

    # Spec: Mexico 1980.33 (rating_date=2026-06-04)
    assert abs(rating - 1980.3295316848994) < 1e-3
    assert low_confidence is False


def test_lookup_rating_south_africa_before_2026_06_11(db_session):
    """South Africa (team_id=21) → 1662.98 antes del 2026-06-11 (datos reales)."""
    rating, low_confidence = lookup_rating(db_session, 21, datetime.date(2026, 6, 11))

    # Spec: South Africa 1662.98 (rating_date=2026-06-06)
    assert abs(rating - 1662.9772439294302) < 1e-3
    assert low_confidence is False
