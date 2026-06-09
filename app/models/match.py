from datetime import date

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import MatchStage, MatchStatus
from app.models.types import match_stage_type, match_status_type


class Match(Base, TimestampMixin):
    """Partido de selecciones: histórico y Mundial 2026 con el mismo modelo."""

    __tablename__ = "match"

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competition.id"))
    match_date: Mapped[date] = mapped_column(index=True)

    home_team_id: Mapped[int] = mapped_column(ForeignKey("team.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("team.id"))

    # En mundiales casi todo es campo neutral -> afecta la ventaja de localía.
    neutral_site: Mapped[bool] = mapped_column(default=False)
    stage: Mapped[MatchStage | None] = mapped_column(match_stage_type)
    status: Mapped[MatchStatus] = mapped_column(
        match_status_type, default=MatchStatus.SCHEDULED
    )

    home_score: Mapped[int | None] = mapped_column()
    away_score: Mapped[int | None] = mapped_column()
    went_to_extra_time: Mapped[bool] = mapped_column(default=False)
    went_to_penalties: Mapped[bool] = mapped_column(default=False)

    city: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str | None] = mapped_column(String(120))

    # Solo partidos de fase de grupos del torneo.
    group_id: Mapped[int | None] = mapped_column(ForeignKey("tournament_group.id"))

    competition: Mapped["Competition"] = relationship(back_populates="matches")  # noqa: F821
    home_team: Mapped["Team"] = relationship(foreign_keys=[home_team_id])  # noqa: F821
    away_team: Mapped["Team"] = relationship(foreign_keys=[away_team_id])  # noqa: F821
    group: Mapped["TournamentGroup | None"] = relationship(back_populates="matches")  # noqa: F821

    goals: Mapped[list["GoalEvent"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )
    shootout: Mapped["Shootout | None"] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )
    team_stats: Mapped[list["MatchTeamStats"]] = relationship(  # noqa: F821
        back_populates="match", cascade="all, delete-orphan"
    )


class GoalEvent(Base):
    """Gol individual (martj42 goalscorers.csv)."""

    __tablename__ = "goal_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("match.id", ondelete="CASCADE"))
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"))
    scorer_name: Mapped[str | None] = mapped_column(String(120))
    minute: Mapped[int | None] = mapped_column()
    own_goal: Mapped[bool] = mapped_column(default=False)
    penalty: Mapped[bool] = mapped_column(default=False)

    match: Mapped["Match"] = relationship(back_populates="goals")


class Shootout(Base):
    """Definición por penales (martj42 shootouts.csv). Una por partido."""

    __tablename__ = "shootout"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("match.id", ondelete="CASCADE"), unique=True
    )
    winner_team_id: Mapped[int] = mapped_column(ForeignKey("team.id"))

    match: Mapped["Match"] = relationship(back_populates="shootout")
