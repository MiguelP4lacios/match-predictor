"""Router de partidos — solo lectura.

GET /api/v1/matches/upcoming  — próximos SCHEDULED con predicciones 1X2.
GET /api/v1/matches/{id}      — detalle: predicciones + últimas cuotas + señales.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.api.schemas import MatchDetail, OddsItem, PredictionItem, SignalItem, UpcomingMatch
from app.core.database import get_session
from app.models.betting import ValueSignal
from app.models.enums import MarketType, MatchStatus
from app.models.match import Match
from app.models.model import Prediction
from app.models.odds import Odds
from app.models.team import Team

router = APIRouter(tags=["matches"])


@router.get("/matches/upcoming", response_model=list[UpcomingMatch])
def upcoming_matches(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: Session = Depends(get_session),  # noqa: B008
) -> list[UpcomingMatch]:
    """Partidos próximos (SCHEDULED) con predicciones 1X2 opcionales.

    Anti-N+1: 2 queries — matches paginados + predictions IN (...).
    """
    home_alias = aliased(Team, name="home_alias")
    away_alias = aliased(Team, name="away_alias")

    matches_stmt = (
        select(
            Match.id,
            Match.match_date,
            Match.kickoff_at,
            home_alias.name.label("home_team"),
            away_alias.name.label("away_team"),
            Match.neutral_site,
            Match.stage,
        )
        .join(home_alias, Match.home_team_id == home_alias.id)
        .join(away_alias, Match.away_team_id == away_alias.id)
        .where(Match.status == MatchStatus.SCHEDULED)
        .order_by(Match.match_date, Match.kickoff_at, Match.id)
        .limit(limit)
        .offset(offset)
    )
    match_rows = session.execute(matches_stmt).all()

    if not match_rows:
        return []

    match_ids = [r.id for r in match_rows]

    # Una sola query para todas las predicciones 1X2 del batch
    preds_stmt = select(Prediction).where(
        Prediction.match_id.in_(match_ids),
        Prediction.market_type == MarketType.MATCH_1X2,
    )
    all_preds = session.scalars(preds_stmt).all()

    # Índice: match_id → {outcome_code: prediction}
    pred_index: dict[int, dict[str, Prediction]] = {}
    for p in all_preds:
        pred_index.setdefault(p.match_id, {})[p.outcome_code or ""] = p

    results = []
    for r in match_rows:
        preds = pred_index.get(r.id, {})
        p_home_pred = preds.get("HOME")
        p_draw_pred = preds.get("DRAW")
        p_away_pred = preds.get("AWAY")

        # low_confidence: True si cualquier predicción 1X2 la tiene
        lc = None
        if p_home_pred or p_draw_pred or p_away_pred:
            lc = any(
                getattr(p, "low_confidence", False)
                for p in [p_home_pred, p_draw_pred, p_away_pred]
                if p is not None
            )

        results.append(
            UpcomingMatch(
                id=r.id,
                match_date=r.match_date,
                kickoff_at=r.kickoff_at,
                home_team=r.home_team,
                away_team=r.away_team,
                neutral_site=r.neutral_site,
                stage=str(r.stage) if r.stage else None,
                p_home=float(p_home_pred.probability) if p_home_pred else None,
                p_draw=float(p_draw_pred.probability) if p_draw_pred else None,
                p_away=float(p_away_pred.probability) if p_away_pred else None,
                low_confidence=lc,
            )
        )

    return results


@router.get("/matches/{match_id}", response_model=MatchDetail)
def match_detail(
    match_id: int,
    session: Session = Depends(get_session),  # noqa: B008
) -> MatchDetail:
    """Detalle de un partido: predicciones + últimas cuotas + señales.

    Devuelve 404 si el partido no existe.
    """
    home_detail = aliased(Team, name="home_detail_alias")
    away_detail = aliased(Team, name="away_detail_alias")

    match_stmt = (
        select(
            Match.id,
            Match.match_date,
            Match.kickoff_at,
            home_detail.name.label("home_team"),
            away_detail.name.label("away_team"),
            Match.neutral_site,
            Match.stage,
            Match.status,
            Match.home_score,
            Match.away_score,
        )
        .join(home_detail, Match.home_team_id == home_detail.id)
        .join(away_detail, Match.away_team_id == away_detail.id)
        .where(Match.id == match_id)
    )
    m = session.execute(match_stmt).one_or_none()
    if m is None:
        raise HTTPException(status_code=404, detail="Match not found")

    # Predicciones (todos los mercados)
    preds_stmt = select(Prediction).where(Prediction.match_id == match_id)
    all_preds = session.scalars(preds_stmt).all()
    predictions = [
        PredictionItem(
            id=p.id,
            market_type=str(p.market_type),
            outcome_code=p.outcome_code,
            probability=float(p.probability),
            low_confidence=p.low_confidence,
        )
        for p in all_preds
    ]

    # Últimas cuotas por (bookmaker, outcome_code) — max(captured_at) por grupo
    latest_subq = (
        select(
            Odds.bookmaker,
            Odds.outcome_code,
            func.max(Odds.captured_at).label("latest_at"),
        )
        .where(Odds.match_id == match_id)
        .group_by(Odds.bookmaker, Odds.outcome_code)
        .subquery()
    )
    odds_stmt = (
        select(Odds)
        .join(
            latest_subq,
            (Odds.bookmaker == latest_subq.c.bookmaker)
            & (Odds.outcome_code == latest_subq.c.outcome_code)
            & (Odds.captured_at == latest_subq.c.latest_at),
        )
        .where(Odds.match_id == match_id)
    )
    last_odds = [
        OddsItem(
            bookmaker=o.bookmaker,
            outcome_code=o.outcome_code,
            decimal_odds=float(o.decimal_odds),
            captured_at=o.captured_at,
        )
        for o in session.scalars(odds_stmt).all()
    ]

    # Señales asociadas al partido
    pred_ids = [p.id for p in all_preds]
    signals: list[SignalItem] = []
    if pred_ids:
        home_sig = aliased(Team, name="home_sig_alias")
        away_sig = aliased(Team, name="away_sig_alias")
        sigs_stmt = (
            select(
                ValueSignal.id,
                Match.match_date,
                Match.kickoff_at,
                home_sig.name.label("home_team"),
                away_sig.name.label("away_team"),
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
            .join(home_sig, Match.home_team_id == home_sig.id)
            .join(away_sig, Match.away_team_id == away_sig.id)
            .join(Odds, ValueSignal.odds_id == Odds.id)
            .where(ValueSignal.prediction_id.in_(pred_ids))
        )
        for r in session.execute(sigs_stmt).all():
            signals.append(
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
            )

    return MatchDetail(
        id=m.id,
        match_date=m.match_date,
        kickoff_at=m.kickoff_at,
        home_team=m.home_team,
        away_team=m.away_team,
        neutral_site=m.neutral_site,
        stage=str(m.stage) if m.stage else None,
        status=str(m.status),
        home_score=m.home_score,
        away_score=m.away_score,
        predictions=predictions,
        last_odds=last_odds,
        signals=signals,
    )
