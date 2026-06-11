from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import BetMode, BetStatus
from app.models.types import bet_mode_type, bet_status_type


class ValueSignal(Base, TimestampMixin):
    """Señal +EV: cuando la prob. del modelo supera la implícita en la cuota."""

    __tablename__ = "value_signal"
    __table_args__ = (UniqueConstraint("prediction_id", "odds_id", name="uq_signal_identity"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("prediction.id", ondelete="CASCADE"))
    odds_id: Mapped[int] = mapped_column(ForeignKey("odds.id", ondelete="CASCADE"))

    edge: Mapped[float] = mapped_column(Numeric(8, 5))
    ev: Mapped[float] = mapped_column(Numeric(8, 5))
    kelly_fraction: Mapped[float] = mapped_column(Numeric(8, 5))
    recommended_stake: Mapped[Decimal] = mapped_column(Numeric(14, 2))

    bets: Mapped[list["BetLog"]] = relationship(back_populates="signal")


class BetLog(Base, TimestampMixin):
    """Registro de apuesta. PAPER (señal automática) o REAL (manual, COP)."""

    __tablename__ = "bet_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # Ruta PAPER: FK a la señal +EV que originó la apuesta (nullable desde m6).
    value_signal_id: Mapped[int | None] = mapped_column(ForeignKey("value_signal.id"), nullable=True)

    # Ruta REAL: FK directa al partido + outcome apostado.
    match_id: Mapped[int | None] = mapped_column(
        ForeignKey("match.id"), nullable=True, index=True
    )
    outcome_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    mode: Mapped[BetMode] = mapped_column(bet_mode_type, default=BetMode.PAPER)
    stake: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    odds_taken: Mapped[float] = mapped_column(Numeric(8, 3))
    status: Mapped[BetStatus] = mapped_column(bet_status_type, default=BetStatus.PENDING)
    settled_result: Mapped[str | None] = mapped_column(String(20))
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    placed_at: Mapped[datetime | None] = mapped_column()

    # Liquidación
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    signal: Mapped["ValueSignal | None"] = relationship(back_populates="bets")
    match: Mapped["Match | None"] = relationship()  # noqa: F821
