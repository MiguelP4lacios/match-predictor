from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description="Sistema de predicción +EV para apuestas de selecciones (Mundial 2026)",
    version="0.1.0",
)

app.include_router(health_router)
