from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TournamentGroup(Base):
    """Grupo de un torneo (A..L del Mundial 2026).

    NO se llama `group`: GROUP es palabra reservada en SQL (GROUP BY).
    """

    __tablename__ = "tournament_group"
    __table_args__ = (
        UniqueConstraint("competition_id", "season_year", "name", name="uq_group_comp_season_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competition.id"))
    season_year: Mapped[int] = mapped_column()
    name: Mapped[str] = mapped_column(String(2))  # "A".."L"

    competition: Mapped["Competition"] = relationship(back_populates="groups")  # noqa: F821
    members: Mapped[list["GroupTeam"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    matches: Mapped[list["Match"]] = relationship(back_populates="group")  # noqa: F821


class GroupTeam(Base):
    """Pertenencia de un equipo a un grupo del torneo."""

    __tablename__ = "group_team"
    __table_args__ = (UniqueConstraint("group_id", "team_id", name="uq_group_team"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("tournament_group.id", ondelete="CASCADE"))
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"))

    group: Mapped["TournamentGroup"] = relationship(back_populates="members")
