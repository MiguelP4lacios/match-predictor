"""Jobs del scheduler. Hoy: capturar odds. Time-sensitive por el Mundial 2026."""

import logging

from app.core.config import settings
from app.core.database import SessionLocal
from app.ingestion.odds_pipeline import OddsCapturePipeline
from app.ingestion.sources.odds_api import OddsApiSource

log = logging.getLogger(__name__)


def make_odds_source() -> OddsApiSource:
    return OddsApiSource(
        api_key=settings.odds_api_key,
        base_url=settings.odds_api_base_url,
        sport_key=settings.odds_sport_key,
        regions=settings.odds_regions,
        markets=settings.odds_markets,
    )


def capture_odds_job() -> dict[str, object]:
    if not settings.odds_api_key:
        log.warning("ODDS_API_KEY no configurada; salto la captura de odds.")
        return {"skipped": "no_api_key"}

    source = make_odds_source()
    with SessionLocal() as session:
        result = OddsCapturePipeline(session, source).capture()
    log.info("Captura odds: %s | cuota restante: %s", result, source.last_remaining)
    return result
