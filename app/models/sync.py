from datetime import datetime

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import DataSource
from app.models.types import data_source_type


class SyncLog(Base, TimestampMixin):
    """Control de ingesta adaptativa: evita pedir lo ya fresco y respeta cuotas
    (API-Football 100 req/día, The Odds API 500 créditos/mes)."""

    __tablename__ = "sync_log"
    __table_args__ = (UniqueConstraint("resource", "source", name="uq_sync_resource_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    resource: Mapped[str] = mapped_column(String(120))
    source: Mapped[DataSource] = mapped_column(data_source_type)
    last_fetched_at: Mapped[datetime | None] = mapped_column()
    status: Mapped[str | None] = mapped_column(String(40))
