"""Router de observabilidad operacional.

GET /api/v1/health/full — retorna HealthFull con veredictos ok/warn/stale.

Invariante: CERO llamadas HTTP externas; todo serve-from-DB.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.model.health_status import HealthFull, get_health

router = APIRouter(tags=["health"])


@router.get("/health/full", response_model=HealthFull)
def health_full(session: Session = Depends(get_session)) -> HealthFull:  # noqa: B008
    """Observabilidad operacional: métricas con veredictos desde la BD.

    Lee sync_log, odds, model_version y match — cero llamadas externas.
    Responde < 500ms en carga normal (solo queries DB).
    """
    return get_health(session)
