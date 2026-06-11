from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.routers.bets import router as bets_router
from app.api.routers.groups import router as groups_router
from app.api.routers.matches import router as matches_router
from app.api.routers.model import router as model_router
from app.api.routers.paper import router as paper_router
from app.api.routers.parlays import router as parlays_router
from app.api.routers.signals import router as signals_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description="Sistema de predicción +EV para apuestas de selecciones (Mundial 2026)",
    version="0.1.0",
)

# CORS debe registrarse ANTES de los routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(signals_router, prefix="/api/v1")
app.include_router(matches_router, prefix="/api/v1")
app.include_router(model_router, prefix="/api/v1")
app.include_router(paper_router, prefix="/api/v1")
app.include_router(bets_router, prefix="/api/v1")
app.include_router(parlays_router, prefix="/api/v1")
app.include_router(groups_router, prefix="/api/v1")
