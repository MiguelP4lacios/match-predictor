from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import BetMode, BetStatus
from app.models.types import bet_mode_type, bet_status_type


class ValueSignal(Base, TimestampMixin):
    """Señal +EV: cuando la prob. del modelo supera la implícita en la cuota."""

    __tablename__ = "value_signal"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("prediction.id", ondelete="CASCADE")
    )
    odds_id: Mapped[int] = mapped_column(ForeignKey("odds.id", ondelete="CASCADE"))

    edge: Mapped[float] = mapped_column(Numeric(8, 5))
    ev: Mapped[float] = mapped_column(Numeric(8, 5))
    kelly_fraction: Mapped[float] = mapped_column(Numeric(8, 5))
    recommended_stake: Mapped[Decimal] = mapped_column(Numeric(14, 2))

    bets: Mapped[list["BetLog"]] = relationship(back_populates="signal")


class BetLog(Base, TimestampMixin):
    """Registro de apuesta. Arranca en modo PAPER hasta validar el edge."""

    __tablename__ = "bet_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    value_signal_id: Mapped[int] = mapped_column(ForeignKey("value_signal.id"))

    mode: Mapped[BetMode] = mapped_column(bet_mode_type, default=BetMode.PAPER)
    stake: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    odds_taken: Mapped[float] = mapped_column(Numeric(8, 3))
    status: Mapped[BetStatus] = mapped_column(bet_status_type, default=BetStatus.PENDING)
    settled_result: Mapped[str | None] = mapped_column(String(20))
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    placed_at: Mapped[datetime | None] = mapped_column()

    signal: Mapped["ValueSignal"] = relationship(back_populates="bets")
