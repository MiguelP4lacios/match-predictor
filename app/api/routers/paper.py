"""Router de apuestas en papel — solo lectura.

GET /api/v1/paper — conteos y ROI de BetLog mode=PAPER.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import PaperStats
from app.core.database import get_session
from app.models.betting import BetLog
from app.models.enums import BetMode, BetStatus

router = APIRouter(tags=["paper"])


@router.get("/paper", response_model=PaperStats)
def paper_stats(
    session: Session = Depends(get_session),  # noqa: B008
) -> PaperStats:
    """Estadísticas de apuestas en modo PAPER.

    ROI = sum(pnl) / sum(stake) sobre WON + LOST.
    Si settled = 0 → roi = null (sin división por cero).
    Zero llamadas externas.
    """
    # Conteos por estado
    count_stmt = (
        select(BetLog.status, func.count().label("cnt"))
        .where(BetLog.mode == BetMode.PAPER)
        .group_by(BetLog.status)
    )
    counts: dict[str, int] = {}
    for row in session.execute(count_stmt).all():
        counts[str(row.status)] = row.cnt

    total = sum(counts.values())
    open_count = counts.get(str(BetStatus.PENDING), 0)
    settled_count = counts.get(str(BetStatus.WON), 0) + counts.get(str(BetStatus.LOST), 0)

    # ROI sobre WON + LOST únicamente
    roi: float | None = None
    if settled_count > 0:
        roi_stmt = select(
            func.sum(BetLog.pnl).label("total_pnl"),
            func.sum(BetLog.stake).label("total_stake"),
        ).where(
            BetLog.mode == BetMode.PAPER,
            BetLog.status.in_([BetStatus.WON, BetStatus.LOST]),
        )
        row = session.execute(roi_stmt).one()
        if row.total_stake and float(row.total_stake) != 0:
            roi = float(row.total_pnl or 0) / float(row.total_stake)

    return PaperStats(
        total=total,
        open=open_count,
        settled=settled_count,
        roi=roi,
    )
