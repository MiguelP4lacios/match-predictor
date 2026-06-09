from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import Confederation, DataSource
from app.models.types import confederation_type, data_source_type


class Team(Base, TimestampMixin):
    """Selección nacional. Fuente única de verdad (canónica)."""

    __tablename__ = "team"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    fifa_code: Mapped[str | None] = mapped_column(String(3), unique=True)
    confederation: Mapped[Confederation | None] = mapped_column(confederation_type)

    aliases: Mapped[list["TeamAlias"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )


class TeamAlias(Base):
    """Traductor cross-source: (fuente, id/nombre externo) -> team canónico.

    El corazón de la capa DataSource provider-agnostic.
    """

    __tablename__ = "team_alias"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_team_alias_source_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id", ondelete="CASCADE"))
    source: Mapped[DataSource] = mapped_column(data_source_type)
    external_id: Mapped[str] = mapped_column(String(120))

    team: Mapped["Team"] = relationship(back_populates="aliases")
