"""Helpers de consulta de cuotas — extraído de signals.py.

Dirección de dependencia: api → model (este módulo NUNCA importa de app.api).
Usado tanto por signals.py como por los routers de la API.

Queries SQLAlchemy 2.0 sin N+1:
  - best_odds_per_outcome: mejor cuota (máx decimal_odds) por outcome_code.
  - latest_per_bookmaker: snapshot más reciente por bookmaker para un outcome.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Odds
from app.models.enums import MarketType


def best_odds_per_outcome(
    match_id: int,
    session: Session,
    market_type: MarketType = MarketType.MATCH_1X2,
) -> dict[str, Odds]:
    """Retorna el registro Odds con la cuota máxima por outcome_code.

    Usa una subquery de agregación para evitar N+1: una sola ida a la BD
    independientemente del número de bookmakers.

    Args:
        match_id:    ID del partido.
        session:     sesión SQLAlchemy activa.
        market_type: tipo de mercado (default MATCH_1X2).

    Returns:
        Diccionario ``{outcome_code: Odds}`` con la cuota más alta por outcome.
        Vacío si no hay odds para el partido.
    """
    # Subquery: max(decimal_odds) por outcome_code
    subq = (
        select(
            Odds.outcome_code,
            func.max(Odds.decimal_odds).label("max_odds"),
        )
        .where(
            Odds.match_id == match_id,
            Odds.market_type == market_type,
            Odds.outcome_code.isnot(None),
        )
        .group_by(Odds.outcome_code)
        .subquery()
    )

    # Join con la tabla original para obtener el objeto Odds completo
    stmt = (
        select(Odds)
        .join(
            subq,
            (Odds.outcome_code == subq.c.outcome_code) & (Odds.decimal_odds == subq.c.max_odds),
        )
        .where(
            Odds.match_id == match_id,
            Odds.market_type == market_type,
        )
    )

    rows = session.scalars(stmt).all()

    # En caso de múltiples odds con la misma cuota máxima, usar cualquiera.
    # Usar el de id más alto (más reciente ingresado) para determinismo.
    best: dict[str, Odds] = {}
    for o in rows:
        oc = o.outcome_code
        if oc is None:
            continue
        if oc not in best or o.id > best[oc].id:
            best[oc] = o

    return best


def latest_per_bookmaker(
    match_id: int,
    outcome_code: str,
    session: Session,
    market_type: MarketType = MarketType.MATCH_1X2,
) -> list[Odds]:
    """Retorna el snapshot más reciente de cada bookmaker para un outcome.

    Usa una subquery de agregación para evitar N+1.

    Args:
        match_id:      ID del partido.
        outcome_code:  Código de resultado (HOME, DRAW, AWAY, OVER, UNDER...).
        session:       sesión SQLAlchemy activa.
        market_type:   tipo de mercado (default MATCH_1X2).

    Returns:
        Lista de Odds — un registro por bookmaker (el más reciente).
        Vacía si no hay datos.
    """
    # Subquery: max(captured_at) por bookmaker
    subq = (
        select(
            Odds.bookmaker,
            func.max(Odds.captured_at).label("latest_at"),
        )
        .where(
            Odds.match_id == match_id,
            Odds.market_type == market_type,
            Odds.outcome_code == outcome_code,
        )
        .group_by(Odds.bookmaker)
        .subquery()
    )

    stmt = (
        select(Odds)
        .join(
            subq,
            (Odds.bookmaker == subq.c.bookmaker) & (Odds.captured_at == subq.c.latest_at),
        )
        .where(
            Odds.match_id == match_id,
            Odds.market_type == market_type,
            Odds.outcome_code == outcome_code,
        )
    )

    return list(session.scalars(stmt).all())
