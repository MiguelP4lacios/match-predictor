"""Lookup de ratings Elo point-in-time — compartido por predict y explain.

La query anti-look-ahead garantiza que nunca se usa información futura:
  SELECT rating WHERE team_id=:t AND rating_date < :d ORDER BY rating_date DESC LIMIT 1
  Si no hay fila previa → DEFAULT_RATING, low_confidence=True.
"""

import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EloRating

DEFAULT_RATING: float = 1500.0
HOME_ADVANTAGE: float = 100.0


def lookup_rating(
    session: Session,
    team_id: int,
    before_date: datetime.date,
) -> tuple[float, bool]:
    """Devuelve (rating, low_confidence) para el equipo antes de before_date.

    Usa la condición estrictamente < before_date para evitar look-ahead.
    Si no hay fila previa: retorna (DEFAULT_RATING, True).

    Args:
        session:     sesión SQLAlchemy activa.
        team_id:     ID del equipo.
        before_date: fecha del partido (excluida del rango de búsqueda).

    Returns:
        Tupla (rating: float, low_confidence: bool).
    """
    stmt = (
        select(EloRating.rating)
        .where(
            EloRating.team_id == team_id,
            EloRating.rating_date < before_date,
        )
        .order_by(EloRating.rating_date.desc())
        .limit(1)
    )
    result = session.scalar(stmt)
    if result is None:
        return DEFAULT_RATING, True
    return float(result), False
