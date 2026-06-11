from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import MarketType
from app.models.types import market_type_type


class ModelVersion(Base, TimestampMixin):
    """Versión del modelo. Sin trazabilidad de versión, el backtest miente."""

    __tablename__ = "model_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    params_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    predictions: Mapped[list["Prediction"]] = relationship(back_populates="model_version")


class Prediction(Base):
    """Probabilidad estimada por el modelo, point-in-time (sin look-ahead)."""

    __tablename__ = "prediction"
    __table_args__ = (
        UniqueConstraint(
            "model_version_id",
            "match_id",
            "competition_id",
            "market_type",
            "outcome_code",
            "outcome_team_id",
            name="uq_prediction_identity",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    match_id: Mapped[int | None] = mapped_column(
        ForeignKey("match.id", ondelete="CASCADE"), index=True
    )
    competition_id: Mapped[int | None] = mapped_column(ForeignKey("competition.id"))
    model_version_id: Mapped[int] = mapped_column(ForeignKey("model_version.id"))
    # FK al equipo para predicciones de futuros (CHAMPION, ADVANCE_GROUP, REACH_*).
    # NULL en predicciones 1X2 / Over-Under basadas en partido.
    outcome_team_id: Mapped[int | None] = mapped_column(ForeignKey("team.id"), nullable=True)

    market_type: Mapped[MarketType] = mapped_column(market_type_type)
    outcome_code: Mapped[str | None] = mapped_column(String(20))
    probability: Mapped[float] = mapped_column(Numeric(8, 5))
    # Línea Over/Under asociada a la predicción (ej. 2.5, 3.5). NULL en 1X2.
    line: Mapped[float | None] = mapped_column(Numeric(5, 2))
    # True cuando no existe rating histórico previo y se usó 1500 por defecto.
    low_confidence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    generated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    model_version: Mapped["ModelVersion"] = relationship(back_populates="predictions")
