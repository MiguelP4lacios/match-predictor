"""Router de apuestas — estadísticas por modo.

GET /api/v1/paper — conteos y ROI de BetLog por modo (PAPER y REAL separados).
"""

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import BetsPageStats, ModeStats
from app.core.database import get_session
from app.models.betting import BetLog
from app.models.enums import BetMode, BetStatus

router = APIRouter(tags=["paper"])


def _mode_stats(session: Session, mode: BetMode) -> ModeStats:
    """Calcula estadísticas para un modo (PAPER o REAL)."""
    # Conteos por estado
    count_stmt = (
        select(BetLog.status, func.count().label("cnt"))
        .where(BetLog.mode == mode)
        .group_by(BetLog.status)
    )
    counts: dict[str, int] = {}
    for row in session.execute(count_stmt).all():
        counts[str(row.status)] = row.cnt

    total = sum(counts.values())
    pending_count = counts.get(str(BetStatus.PENDING), 0)
    won_count = counts.get(str(BetStatus.WON), 0)
    lost_count = counts.get(str(BetStatus.LOST), 0)
    settled_count = won_count + lost_count

    # ROI, staked, returns — solo sobre WON + LOST
    staked: Decimal | None = None
    returns: Decimal | None = None
    roi: float | None = None

    if settled_count > 0:
        roi_stmt = select(
            func.sum(BetLog.pnl).label("total_pnl"),
            func.sum(BetLog.stake).label("total_stake"),
        ).where(
            BetLog.mode == mode,
            BetLog.status.in_([BetStatus.WON, BetStatus.LOST]),
        )
        row = session.execute(roi_stmt).one()
        if row.total_stake and float(row.total_stake) != 0:
            staked = row.total_stake
            pnl_sum = row.total_pnl or Decimal("0")
            returns = staked + pnl_sum
            roi = float(pnl_sum) / float(staked)

    return ModeStats(
        total=total,
        pending=pending_count,
        settled=settled_count,
        won=won_count,
        lost=lost_count,
        staked=staked,
        returns=returns,
        roi=roi,
    )


@router.get("/paper", response_model=BetsPageStats)
def paper_stats(
    session: Session = Depends(get_session),  # noqa: B008
) -> BetsPageStats:
    """Estadísticas de apuestas por modo (PAPER y REAL).

    ROI = sum(pnl) / sum(stake) sobre WON + LOST por modo.
    Si settled = 0 para un modo → roi = null (sin división por cero).
    Los modos NUNCA se mezclan.
    Zero llamadas externas.
    """
    return BetsPageStats(
        paper=_mode_stats(session, BetMode.PAPER),
        real=_mode_stats(session, BetMode.REAL),
    )
