from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import MarketType
from app.models.types import market_type_type


class Odds(Base):
    """Snapshot de cuota — POLIMÓRFICO: cubre 1X2, Over/Under y Futures.

    - match_id     : para mercados de partido (1X2, O/U). NULL en futures.
    - competition_id: para futures de torneo (campeón, avance). NULL en partido.
    - outcome_code : HOME/DRAW/AWAY, OVER/UNDER.
    - outcome_team_id: equipo del outcome en futures (campeón = ese equipo).
    - line         : 2.5, 3.5 para Over/Under.
    - is_closing   : el snapshot final pre-evento = benchmark para medir edge.
    """

    __tablename__ = "odds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    match_id: Mapped[int | None] = mapped_column(
        ForeignKey("match.id", ondelete="CASCADE"), index=True
    )
    competition_id: Mapped[int | None] = mapped_column(ForeignKey("competition.id"))

    market_type: Mapped[MarketType] = mapped_column(market_type_type)
    outcome_code: Mapped[str | None] = mapped_column(String(20))
    outcome_team_id: Mapped[int | None] = mapped_column(ForeignKey("team.id"))
    line: Mapped[float | None] = mapped_column(Numeric(5, 2))

    bookmaker: Mapped[str] = mapped_column(String(60))
    decimal_odds: Mapped[float] = mapped_column(Numeric(8, 3))
    captured_at: Mapped[datetime] = mapped_column(index=True)
    is_closing: Mapped[bool] = mapped_column(default=False)
