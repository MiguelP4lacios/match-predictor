from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: la app responde."""
    return {"status": "ok"}


@router.get("/health/db")
def health_db(session: Session = Depends(get_session)) -> dict[str, str]:
    """Readiness: la BD responde. Útil para detectar Postgres caído."""
    session.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}
