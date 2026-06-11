"""Router de odds manuales.

POST /api/v1/odds/manual — entrada manual de cuotas de futuros (GROUP_ADVANCE,
    REACH_SEMI_FINAL, REACH_FINAL) no disponibles vía The Odds API free tier.
    Permite ingresar cuotas de BetPlay u otras casas para mercados de avance.

Restricción: MATCH_1X2 y OVER_UNDER solo se capturan por el pipeline automático.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models.enums import MarketType
from app.models.odds import Odds

router = APIRouter(tags=["odds"])

# Mercados permitidos vía entrada manual (avance/futuros no cubiertos por la API free)
_ALLOWED_MANUAL_MARKETS: frozenset[MarketType] = frozenset(
    {MarketType.GROUP_ADVANCE, MarketType.REACH_SEMI_FINAL, MarketType.REACH_FINAL}
)


class ManualOddsRequest(BaseModel):
    """Body para entrada manual de cuotas de futuros."""

    market_type: MarketType
    outcome_team_id: int = Field(..., gt=0, description="ID del equipo en nuestra BD")
    decimal_odds: float = Field(..., gt=1.0, description="Cuota decimal (>1.0)")
    bookmaker: str = Field(..., min_length=1, max_length=60)
    captured_at: datetime | None = Field(
        None,
        description="Momento de captura; usa UTC now si omitido",
    )

    @model_validator(mode="after")
    def validate_market_type(self) -> "ManualOddsRequest":
        if self.market_type not in _ALLOWED_MANUAL_MARKETS:
            allowed = ", ".join(sorted(m.value for m in _ALLOWED_MANUAL_MARKETS))
            raise ValueError(
                f"market_type='{self.market_type}' no está permitido en /odds/manual. "
                f"Solo se aceptan mercados de futuros de avance: {allowed}. "
                "MATCH_1X2 y OVER_UNDER se capturan por el pipeline automático."
            )
        return self


class ManualOddsResponse(BaseModel):
    id: int
    market_type: MarketType
    outcome_team_id: int
    decimal_odds: float
    bookmaker: str
    captured_at: datetime


@router.post("/odds/manual", response_model=ManualOddsResponse, status_code=status.HTTP_201_CREATED)
def create_manual_odds(
    body: ManualOddsRequest,
    session: Session = Depends(get_session),  # noqa: B008
) -> ManualOddsResponse:
    """Persiste una cuota de futuros ingresada manualmente.

    Permite ingresar odds de avance de grupo, semifinal o final que no están
    disponibles en el tier gratuito de The Odds API.
    Restringe a GROUP_ADVANCE / REACH_SEMI_FINAL / REACH_FINAL.
    """
    captured_at = body.captured_at or datetime.now(UTC).replace(tzinfo=None)

    row = Odds(
        market_type=body.market_type,
        outcome_team_id=body.outcome_team_id,
        decimal_odds=body.decimal_odds,
        bookmaker=body.bookmaker,
        captured_at=captured_at,
        match_id=None,
        is_closing=False,
    )
    session.add(row)
    session.flush()

    return ManualOddsResponse(
        id=row.id,
        market_type=row.market_type,
        outcome_team_id=row.outcome_team_id,
        decimal_odds=float(row.decimal_odds),
        bookmaker=row.bookmaker,
        captured_at=row.captured_at,
    )
