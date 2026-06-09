from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import CompetitionKind
from app.models.types import competition_kind_type


class Competition(Base, TimestampMixin):
    """Competición recurrente (World Cup, qualifiers, friendly, nations league...)."""

    __tablename__ = "competition"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    kind: Mapped[CompetitionKind] = mapped_column(competition_kind_type)

    matches: Mapped[list["Match"]] = relationship(back_populates="competition")  # noqa: F821
    groups: Mapped[list["TournamentGroup"]] = relationship(  # noqa: F821
        back_populates="competition"
    )
