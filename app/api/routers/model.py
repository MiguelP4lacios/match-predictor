"""Router de modelo — solo lectura.

GET /api/v1/model — ModelVersion activo (mayor id) con backtest y calibración.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import ModelInfo
from app.core.database import get_session
from app.models.model import ModelVersion

router = APIRouter(tags=["model"])


@router.get("/model", response_model=ModelInfo)
def get_active_model(
    session: Session = Depends(get_session),  # noqa: B008
) -> ModelInfo:
    """Versión activa del modelo (mayor id).

    Sirve valores directamente desde params_json — sin recompute.
    Zero llamadas externas.
    """
    stmt = select(ModelVersion).order_by(ModelVersion.id.desc()).limit(1)
    mv = session.scalars(stmt).first()

    if mv is None:
        return ModelInfo(name="none", params_summary=None, backtest=None, calibration=None)

    params = mv.params_json or {}

    return ModelInfo(
        name=mv.name,
        params_summary=params.get("thresholds") or params.get("params_summary"),
        backtest=params.get("backtest"),
        calibration=params.get("calibration"),
    )
