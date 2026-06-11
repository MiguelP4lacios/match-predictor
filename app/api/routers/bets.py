"""Router de apuestas REAL — escritura.

POST /api/v1/bets          — registrar apuesta REAL
GET  /api/v1/bets          — listar (filtro opcional por mode/status)
DELETE /api/v1/bets/{id}   — borrar REAL PENDING únicamente
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import BetCreate, BetItem
from app.core.database import get_session
from app.models.betting import BetLog
from app.models.enums import BetMode, BetStatus, MatchStatus
from app.models.match import Match

router = APIRouter(tags=["bets"])


# ---------------------------------------------------------------------------
# POST /bets
# ---------------------------------------------------------------------------


@router.post("/bets", response_model=BetItem, status_code=201)
def create_bet(
    body: BetCreate,
    session: Session = Depends(get_session),  # noqa: B008
) -> BetItem:
    """Registrar apuesta REAL.

    Validaciones:
    - match_id debe existir → 404
    - match.status debe ser SCHEDULED → 422
    - odds_taken > 1 y stake > 0 son validados por Pydantic en BetCreate
    """
    match = session.get(Match, body.match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    if match.status != MatchStatus.SCHEDULED:
        raise HTTPException(
            status_code=422,
            detail=f"Match is not SCHEDULED (current status: {match.status.value})",
        )

    bet = BetLog(
        match_id=body.match_id,
        outcome_code=body.outcome_code,
        odds_taken=float(body.odds_taken),
        stake=body.stake,
        mode=BetMode.REAL,
        status=BetStatus.PENDING,
        placed_at=datetime.now(tz=UTC),
        value_signal_id=body.value_signal_id,
        note=body.note,
    )
    session.add(bet)
    session.commit()
    session.refresh(bet)

    return BetItem(
        id=bet.id,
        mode=str(bet.mode),
        status=str(bet.status),
        match_id=bet.match_id,
        outcome_code=bet.outcome_code,
        odds_taken=float(bet.odds_taken),
        stake=bet.stake,
        pnl=bet.pnl,
        settled_result=bet.settled_result,
        settled_at=bet.settled_at,
        placed_at=bet.placed_at,
        note=bet.note,
        value_signal_id=bet.value_signal_id,
    )


# ---------------------------------------------------------------------------
# GET /bets
# ---------------------------------------------------------------------------


@router.get("/bets", response_model=list[BetItem])
def list_bets(
    mode: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    session: Session = Depends(get_session),  # noqa: B008
) -> list[BetItem]:
    """Listar apuestas con filtros opcionales por mode y status."""
    stmt = select(BetLog)

    if mode is not None:
        try:
            mode_enum = BetMode(mode.lower())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid mode: {mode}") from None
        stmt = stmt.where(BetLog.mode == mode_enum)

    if status is not None:
        try:
            status_enum = BetStatus(status.lower())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status: {status}") from None
        stmt = stmt.where(BetLog.status == status_enum)

    stmt = stmt.order_by(BetLog.placed_at.desc().nullslast(), BetLog.id.desc())
    rows = session.execute(stmt).scalars().all()

    return [
        BetItem(
            id=row.id,
            mode=str(row.mode),
            status=str(row.status),
            match_id=row.match_id,
            outcome_code=row.outcome_code,
            odds_taken=float(row.odds_taken),
            stake=row.stake,
            pnl=row.pnl,
            settled_result=row.settled_result,
            settled_at=row.settled_at,
            placed_at=row.placed_at,
            note=row.note,
            value_signal_id=row.value_signal_id,
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# DELETE /bets/{id}
# ---------------------------------------------------------------------------


@router.delete("/bets/{bet_id}", status_code=204)
def delete_bet(
    bet_id: int,
    session: Session = Depends(get_session),  # noqa: B008
) -> None:
    """Borrar apuesta REAL PENDING.

    - 204: borrado OK
    - 404: no existe
    - 400: apuesta PAPER (no se borra manualmente)
    - 409: apuesta liquidada (WON/LOST/VOID)
    """
    bet = session.get(BetLog, bet_id)
    if bet is None:
        raise HTTPException(status_code=404, detail="Bet not found")

    if bet.mode == BetMode.PAPER:
        raise HTTPException(status_code=400, detail="PAPER bets cannot be deleted manually")

    if bet.status != BetStatus.PENDING:
        raise HTTPException(status_code=409, detail="Bet already settled")

    session.delete(bet)
    session.commit()
