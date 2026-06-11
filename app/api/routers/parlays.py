"""Router de parlays — escritura + preview.

POST /api/v1/parlays/preview   — preview sin persistencia
POST /api/v1/parlays           — registrar parlay (BetLog parlay + bet_leg rows)
GET  /api/v1/parlays           — listar parlays (filtro por mode)
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import (
    ParlayCreate,
    ParlayItem,
    ParlayLegDiag,
    ParlayPreviewRequest,
    ParlayPreviewResponse,
)
from app.core.database import get_session
from app.model.parlay import LegDiagnosis
from app.model.parlay_service import resolve_legs
from app.models.betting import BetLeg, BetLog
from app.models.enums import BetKind, BetMode, BetStatus, MatchStatus
from app.models.match import Match

router = APIRouter(tags=["parlays"])


def _leg_diag_to_schema(ld: LegDiagnosis) -> ParlayLegDiag:
    return ParlayLegDiag(
        match_id=ld.leg.match_id,
        outcome_code=ld.leg.outcome_code,
        odds=ld.leg.odds,
        p_model=ld.leg.p_model,
        ev=ld.ev,
        is_negative_ev=ld.is_negative_ev,
    )


def _validate_legs_scheduled(session: Session, raw_legs: list[dict]) -> None:
    """Valida que todos los matches de los legs existan y estén SCHEDULED."""
    for raw in raw_legs:
        match = session.get(Match, raw["match_id"])
        if match is None:
            raise HTTPException(
                status_code=404,
                detail=f"Match {raw['match_id']} not found",
            )
        if match.status != MatchStatus.SCHEDULED:
            raise HTTPException(
                status_code=422,
                detail=f"Match {raw['match_id']} is not SCHEDULED (current: {match.status.value})",
            )


# ---------------------------------------------------------------------------
# POST /parlays/preview
# ---------------------------------------------------------------------------


@router.post("/parlays/preview", response_model=ParlayPreviewResponse)
def preview_parlay(
    body: ParlayPreviewRequest,
    session: Session = Depends(get_session),  # noqa: B008
) -> ParlayPreviewResponse:
    """Preview de parlay: computa diagnóstico sin persistir nada.

    Validaciones:
    - ≥ 2 legs (Pydantic, ya validado)
    - odds > 1 por leg (Pydantic, ya validado)
    - todos los matches deben estar SCHEDULED → 422 si no
    - stake ≥ 0 (0 significa "solo ver la cuota")
    """
    raw_legs = [
        {
            "match_id": leg.match_id,
            "outcome_code": leg.outcome_code,
            "odds": leg.odds,
            "label": leg.label or f"{leg.match_id}:{leg.outcome_code}",
        }
        for leg in body.legs
    ]

    _validate_legs_scheduled(session, raw_legs)

    diagnosis = resolve_legs(session, raw_legs)

    stake = body.stake or Decimal("0")
    retorno = (stake * diagnosis.combined_odds).quantize(Decimal("0.01"))

    return ParlayPreviewResponse(
        combined_odds=diagnosis.combined_odds,
        model_prob=diagnosis.model_prob,
        ev=diagnosis.ev,
        stake=stake,
        retorno=retorno,
        legs=[_leg_diag_to_schema(ld) for ld in diagnosis.legs],
        suggested_without_negatives=[
            ParlayLegDiag(
                match_id=leg.match_id,
                outcome_code=leg.outcome_code,
                odds=leg.odds,
                p_model=leg.p_model,
                ev=None,
                is_negative_ev=False,
            )
            for leg in diagnosis.suggested_without_negatives
        ],
    )


# ---------------------------------------------------------------------------
# POST /parlays
# ---------------------------------------------------------------------------


@router.post("/parlays", response_model=ParlayItem, status_code=201)
def create_parlay(
    body: ParlayCreate,
    session: Session = Depends(get_session),  # noqa: B008
) -> ParlayItem:
    """Registrar parlay REAL: persiste BetLog(bet_kind=parlay) + N BetLeg.

    Validaciones:
    - ≥ 2 legs (Pydantic)
    - odds > 1 por leg (Pydantic)
    - stake > 0 (Pydantic)
    - todos los matches SCHEDULED → 422

    Frontera de transacción: commit explícito al final (no auto-commit).
    """
    raw_legs = [
        {
            "match_id": leg.match_id,
            "outcome_code": leg.outcome_code,
            "odds": leg.odds,
            "label": leg.label or f"{leg.match_id}:{leg.outcome_code}",
        }
        for leg in body.legs
    ]

    _validate_legs_scheduled(session, raw_legs)

    # Compute combined odds for odds_taken field on BetLog
    diagnosis = resolve_legs(session, raw_legs)

    now = datetime.now(tz=UTC)

    bet = BetLog(
        match_id=None,
        outcome_code=None,
        value_signal_id=None,
        bet_kind=BetKind.PARLAY,
        mode=BetMode.REAL,
        stake=body.stake,
        odds_taken=float(diagnosis.combined_odds),
        status=BetStatus.PENDING,
        placed_at=now,
        note=body.note,
    )
    session.add(bet)
    session.flush()  # get bet.id

    for raw in raw_legs:
        leg_row = BetLeg(
            bet_log_id=bet.id,
            match_id=raw["match_id"],
            outcome_code=raw["outcome_code"],
            odds_taken=raw["odds"],
        )
        session.add(leg_row)

    session.commit()
    session.refresh(bet)

    return ParlayItem(
        id=bet.id,
        mode=str(bet.mode),
        status=str(bet.status),
        bet_kind=str(bet.bet_kind),
        stake=bet.stake,
        odds_taken=float(bet.odds_taken),
        pnl=bet.pnl,
        settled_at=bet.settled_at,
        placed_at=bet.placed_at,
        note=bet.note,
    )


# ---------------------------------------------------------------------------
# GET /parlays
# ---------------------------------------------------------------------------


@router.get("/parlays", response_model=list[ParlayItem])
def list_parlays(
    mode: Annotated[str | None, Query()] = None,
    session: Session = Depends(get_session),  # noqa: B008
) -> list[ParlayItem]:
    """Listar parlays (bet_kind=parlay) con filtro opcional por mode."""
    stmt = select(BetLog).where(BetLog.bet_kind == BetKind.PARLAY)

    if mode is not None:
        try:
            mode_enum = BetMode(mode.lower())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid mode: {mode}") from None
        stmt = stmt.where(BetLog.mode == mode_enum)

    stmt = stmt.order_by(BetLog.placed_at.desc().nullslast(), BetLog.id.desc())
    rows = session.execute(stmt).scalars().all()

    return [
        ParlayItem(
            id=row.id,
            mode=str(row.mode),
            status=str(row.status),
            bet_kind=str(row.bet_kind),
            stake=row.stake,
            odds_taken=float(row.odds_taken),
            pnl=row.pnl,
            settled_at=row.settled_at,
            placed_at=row.placed_at,
            note=row.note,
        )
        for row in rows
    ]
