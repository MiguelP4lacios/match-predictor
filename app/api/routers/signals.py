"""Router de señales +EV — solo lectura.

GET /api/v1/signals             — lista paginada con filtros por fecha y edge mínimo.
GET /api/v1/signals/{id}/explain — explicación trazable de una señal concreta.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.api.schemas import SignalExplanation, SignalItem, SignalList
from app.core.database import get_session
from app.model.explain import ExplainSection as ModelExplainSection
from app.model.explain import ExplainStep as ModelExplainStep
from app.model.explain import build_explanation
from app.models.betting import ValueSignal
from app.models.match import Match
from app.models.model import Prediction
from app.models.odds import Odds
from app.models.team import Team

router = APIRouter(tags=["signals"])


@router.get("/signals", response_model=SignalList)
def list_signals(
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: Annotated[date | None, Query()] = None,
    min_edge: Annotated[float, Query(ge=0.0)] = 0.0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: Session = Depends(get_session),  # noqa: B008
) -> SignalList:
    """Lista paginada de señales +EV.

    Filtros opcionales: from/to (match_date), min_edge.
    Paginación: limit (default 50, máx 200) y offset.
    Zero llamadas externas — solo lectura desde Postgres.
    """
    home_team_alias = aliased(Team, name="home_team_alias")
    away_team_alias = aliased(Team, name="away_team_alias")

    base = (
        select(
            ValueSignal.id,
            Match.match_date,
            Match.kickoff_at,
            home_team_alias.name.label("home_team"),
            away_team_alias.name.label("away_team"),
            Prediction.market_type,
            Prediction.outcome_code,
            Prediction.probability.label("p_model"),
            Odds.decimal_odds.label("best_odds"),
            Odds.bookmaker,
            ValueSignal.edge,
            ValueSignal.ev,
            ValueSignal.kelly_fraction,
            ValueSignal.recommended_stake,
            Odds.captured_at,
        )
        .join(Prediction, ValueSignal.prediction_id == Prediction.id)
        .join(Match, Prediction.match_id == Match.id)
        .join(home_team_alias, Match.home_team_id == home_team_alias.id)
        .join(away_team_alias, Match.away_team_id == away_team_alias.id)
        .join(Odds, ValueSignal.odds_id == Odds.id)
        .where(ValueSignal.edge >= min_edge)
    )

    if from_:
        base = base.where(Match.match_date >= from_)
    if to:
        base = base.where(Match.match_date <= to)

    # Total sin paginación
    count_stmt = select(func.count()).select_from(base.subquery())
    total: int = session.scalar(count_stmt) or 0

    paginated = base.order_by(Match.match_date, ValueSignal.id).limit(limit).offset(offset)
    rows = session.execute(paginated).all()

    items = [
        SignalItem(
            id=r.id,
            match_date=r.match_date,
            kickoff_at=r.kickoff_at,
            home_team=r.home_team,
            away_team=r.away_team,
            market_type=str(r.market_type),
            outcome_code=r.outcome_code,
            p_model=float(r.p_model),
            best_odds=float(r.best_odds),
            bookmaker=r.bookmaker,
            edge=float(r.edge),
            ev=float(r.ev),
            kelly_fraction=float(r.kelly_fraction),
            recommended_stake=r.recommended_stake,
            captured_at=r.captured_at,
        )
        for r in rows
    ]

    return SignalList(items=items, total=total)


# ---------------------------------------------------------------------------
# GET /signals/{id}/explain
# ---------------------------------------------------------------------------


def _map_step(step: ModelExplainStep) -> dict:
    """Convierte un ExplainStep del modelo a dict para Pydantic."""
    return {
        "key": step.key,
        "label_es": step.label_es,
        "raw": step.raw,
        "formatted": step.formatted,
        "glossary_term": step.glossary_term,
    }


def _map_section(section: ModelExplainSection) -> dict:
    """Convierte un ExplainSection del modelo a dict para Pydantic."""
    return {
        "key": section.key,
        "titulo": section.titulo,
        "steps": [_map_step(s) for s in section.steps],
        "note": section.note,
    }


@router.get("/signals/{signal_id}/explain", response_model=SignalExplanation)
def explain_signal(
    signal_id: int,
    session: Session = Depends(get_session),  # noqa: B008
) -> SignalExplanation:
    """Explicación trazable de una señal +EV.

    Desglosa 5 secciones: edge, origen_p_model, stake, calidad_modelo y metadata.
    Todos los valores canónicos vienen verbatim de la BD; cero llamadas externas.

    Raises:
        HTTPException(404): si signal_id no existe.
    """
    explanation = build_explanation(session, signal_id)
    if explanation is None:
        raise HTTPException(status_code=404, detail="Signal not found")

    return SignalExplanation(
        sections=[_map_section(s) for s in explanation.sections],
    )
