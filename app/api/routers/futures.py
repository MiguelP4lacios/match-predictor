"""Router de futuros Monte Carlo — solo lectura.

GET /api/v1/futures/probabilities — probabilidades de futuros WC2026 (champion,
    advance group, reach semi, reach final) para los 48 equipos, rankeadas por
    p_champion DESC. Sirve exclusivamente desde Postgres; cero llamadas externas.

GET /api/v1/futures/signals — señales +EV pre-computadas sobre OUTRIGHT_WINNER
    (generadas por futures_signals.py). Retorna lista vacía si no hay señales.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import (
    FuturesProbItem,
    FuturesProbResponse,
    FuturesSignalItem,
    FuturesSignalResponse,
)
from app.core.database import get_session
from app.models.betting import ValueSignal
from app.models.enums import MarketType
from app.models.model import ModelVersion, Prediction
from app.models.odds import Odds
from app.models.team import Team

router = APIRouter(tags=["futures"])

_MC_MODEL_NAME = "montecarlo-v1"


# ---------------------------------------------------------------------------
# GET /futures/probabilities
# ---------------------------------------------------------------------------


@router.get("/futures/probabilities", response_model=FuturesProbResponse)
def futures_probabilities(
    session: Session = Depends(get_session),  # noqa: B008
) -> FuturesProbResponse:
    """Probabilidades de futuros WC2026 desde Monte Carlo (montecarlo-v1).

    Retorna todos los equipos con predicciones, rankeados por p_champion DESC.
    Cero llamadas externas — lectura exclusiva desde Postgres.
    """
    mv = session.scalar(select(ModelVersion).where(ModelVersion.name == _MC_MODEL_NAME))
    if mv is None:
        return FuturesProbResponse(champions=[])

    # Un SELECT recupera todos los mercados de futuros en una pasada
    rows = session.execute(
        select(
            Prediction.outcome_team_id,
            Prediction.market_type,
            Prediction.probability,
            Team.name,
        )
        .join(Team, Prediction.outcome_team_id == Team.id)
        .where(
            Prediction.model_version_id == mv.id,
            Prediction.outcome_team_id.is_not(None),
        )
    ).all()

    if not rows:
        return FuturesProbResponse(champions=[])

    # Agregar por equipo
    teams: dict[int, dict] = {}
    for row in rows:
        tid = row.outcome_team_id
        if tid not in teams:
            teams[tid] = {
                "team_id": tid,
                "team": row.name,
                "group": None,
                "p_champion": 0.0,
                "p_advance_group": 0.0,
                "p_reach_sf": 0.0,
                "p_reach_final": 0.0,
            }
        mt = str(row.market_type)
        prob = float(row.probability)
        if mt == MarketType.OUTRIGHT_WINNER:
            teams[tid]["p_champion"] = prob
        elif mt == MarketType.GROUP_ADVANCE:
            teams[tid]["p_advance_group"] = prob
        elif mt == MarketType.REACH_SEMI_FINAL:
            teams[tid]["p_reach_sf"] = prob
        elif mt == MarketType.REACH_FINAL:
            teams[tid]["p_reach_final"] = prob

    # Rankear por p_champion DESC
    sorted_teams = sorted(teams.values(), key=lambda x: x["p_champion"], reverse=True)

    return FuturesProbResponse(champions=[FuturesProbItem(**t) for t in sorted_teams])


# ---------------------------------------------------------------------------
# GET /futures/signals
# ---------------------------------------------------------------------------


@router.get("/futures/signals", response_model=FuturesSignalResponse)
def futures_signals(
    session: Session = Depends(get_session),  # noqa: B008
) -> FuturesSignalResponse:
    """Señales +EV de futuros pre-computadas (OUTRIGHT_WINNER, model=montecarlo-v1).

    Requiere que futures_signals.py haya generado ValueSignal rows.
    Retorna lista vacía si no hay señales — nunca falla por ausencia de datos.
    Cero re-cómputo en el request path; cero llamadas externas.
    """
    mv = session.scalar(select(ModelVersion).where(ModelVersion.name == _MC_MODEL_NAME))
    if mv is None:
        return FuturesSignalResponse(items=[])

    rows = session.execute(
        select(
            ValueSignal.id.label("signal_id"),
            Team.id.label("team_id"),
            Team.name.label("team"),
            Prediction.probability.label("p_champion"),
            ValueSignal.edge,
            Odds.decimal_odds.label("best_odds"),
            Odds.bookmaker,
        )
        .join(Prediction, ValueSignal.prediction_id == Prediction.id)
        .join(Team, Prediction.outcome_team_id == Team.id)
        .join(Odds, ValueSignal.odds_id == Odds.id)
        .where(
            Prediction.model_version_id == mv.id,
            Prediction.market_type == MarketType.OUTRIGHT_WINNER,
            Prediction.outcome_team_id.is_not(None),
        )
        .order_by(ValueSignal.edge.desc())
    ).all()

    items = [
        FuturesSignalItem(
            signal_id=r.signal_id,
            team_id=r.team_id,
            team=r.team,
            p_champion=float(r.p_champion),
            edge=float(r.edge),
            best_odds=float(r.best_odds),
            bookmaker=r.bookmaker,
        )
        for r in rows
    ]

    return FuturesSignalResponse(items=items)
