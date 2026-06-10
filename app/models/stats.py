from datetime import date

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class EloRating(Base):
    """Serie temporal de Elo por selección. El predictor central del modelo."""

    __tablename__ = "elo_rating"
    __table_args__ = (UniqueConstraint("team_id", "rating_date", name="uq_elo_team_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"), index=True)
    rating_date: Mapped[date] = mapped_column(index=True)
    rating: Mapped[float] = mapped_column()


class MatchTeamStats(Base, TimestampMixin):
    """Stats por equipo por partido, donde existan (StatsBomb). TODO nullable:
    la mayoría de partidos de selecciones NO tienen xG gratis."""

    __tablename__ = "match_team_stats"
    __table_args__ = (UniqueConstraint("match_id", "team_id", name="uq_stats_match_team"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("match.id", ondelete="CASCADE"))
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"))

    xg: Mapped[float | None] = mapped_column()
    shots: Mapped[int | None] = mapped_column()
    shots_on_target: Mapped[int | None] = mapped_column()
    possession: Mapped[float | None] = mapped_column()

    match: Mapped["Match"] = relationship(back_populates="team_stats")  # noqa: F821
