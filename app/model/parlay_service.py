"""Servicio de parlay: resuelve p_model por leg desde la BD y llama al núcleo puro.

Capa: api → model (dirección correcta). Los routers llaman este módulo; nunca al revés.
Sin lógica matemática aquí — toda la aritmética vive en parlay.py (puro, testeable
sin HTTP ni BD).

Selector de model_version activa: `ORDER BY id DESC LIMIT 1`
Mismo selector que usa GET /api/v1/model. Fuente única de verdad.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.parlay import Leg, ParlayDiagnosis, combine_parlay
from app.models.enums import MarketType
from app.models.model import ModelVersion, Prediction


def _active_model_version_id(session: Session) -> int | None:
    """Devuelve el ID del ModelVersion activo (mayor id). None si no existe."""
    stmt = select(ModelVersion.id).order_by(ModelVersion.id.desc()).limit(1)
    return session.scalar(stmt)


def resolve_legs(
    session: Session,
    raw_legs: list[dict],
) -> ParlayDiagnosis:
    """Resuelve cada leg, obtiene p_model desde Prediction activa y llama combine_parlay.

    Args:
        session: sesión SQLAlchemy.
        raw_legs: lista de dicts con keys match_id, outcome_code, odds (Decimal), label.

    Returns:
        ParlayDiagnosis del parlay completo.

    Raises:
        ValueError: si raw_legs tiene menos de 2 elementos (propagado desde combine_parlay).
    """
    mv_id = _active_model_version_id(session)

    legs: list[Leg] = []
    for raw in raw_legs:
        match_id: int = raw["match_id"]
        outcome_code: str = raw["outcome_code"]
        odds: Decimal = raw["odds"]
        label: str = raw.get("label", f"{match_id}:{outcome_code}")

        p_model: float | None = None

        if mv_id is not None:
            # Query: Prediction del modelo activo para este match/outcome/MATCH_1X2
            stmt = (
                select(Prediction.probability)
                .where(
                    Prediction.match_id == match_id,
                    Prediction.outcome_code == outcome_code,
                    Prediction.market_type == MarketType.MATCH_1X2,
                    Prediction.model_version_id == mv_id,
                )
                .limit(1)
            )
            prob = session.scalar(stmt)
            if prob is not None:
                p_model = float(prob)

        legs.append(
            Leg(
                match_id=match_id,
                outcome_code=outcome_code,
                odds=odds,
                p_model=p_model,
                label=label,
            )
        )

    return combine_parlay(legs)
