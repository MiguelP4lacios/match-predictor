"""Jobs del scheduler. Hoy: capturar odds. Time-sensitive por el Mundial 2026."""

import logging
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.ingestion.odds_pipeline import OddsCapturePipeline
from app.ingestion.sources.odds_api import OddsApiSource
from app.models.enums import DataSource
from app.models.sync import SyncLog

log = logging.getLogger(__name__)

_CAPTURE_RESOURCE = "odds_api:capture"

# Kambi import diferido (flag-gated) para evitar dependencias no deseadas
# cuando KAMBI_ENABLED=false (default).


def make_kambi_source():
    """Crea KambiOddsSource si KAMBI_ENABLED=true, de lo contrario None.

    NO añadir al loop de captura existente — Kambi es un enhancement
    flag-gated que requiere IP residencial (429 desde datacenter).
    """
    if not settings.kambi_enabled:
        return None

    from app.ingestion.sources.kambi import KambiOddsSource  # noqa: PLC0415

    return KambiOddsSource(
        operator=settings.kambi_operator,
        base_url=settings.kambi_base_url,
    )


def make_odds_source() -> OddsApiSource:
    return OddsApiSource(
        api_key=settings.odds_api_key,
        base_url=settings.odds_api_base_url,
        sport_key=settings.odds_sport_key,
        regions=settings.odds_regions,
        markets=settings.odds_markets,
    )


def _run_capture(session: Session, source) -> dict[str, object]:
    """Ejecuta la captura de odds y escribe la fila de auditoría en sync_log.

    Responsabilidades:
    - Delega la captura al pipeline (que hace su propio commit de odds).
    - Upserta la fila (resource='odds_api:capture', source=ODDS_API) con
      rows_inserted, credits_remaining y last_fetched_at.
    - Siempre escribe la fila, incluso con 0 inserts.
    - Frontera de transacción: este commit cubre solo el upsert de auditoría.
    """
    result = OddsCapturePipeline(session, source).capture()
    inserted: int = result.get("inserted", 0)  # type: ignore[assignment]

    credits: int | None
    if source.last_remaining is not None:
        try:
            credits = int(source.last_remaining)
        except (ValueError, TypeError):
            credits = None
    else:
        credits = None

    now = datetime.now(UTC).replace(tzinfo=None)
    stmt = (
        pg_insert(SyncLog)
        .values(
            resource=_CAPTURE_RESOURCE,
            source=DataSource.ODDS_API,
            last_fetched_at=now,
            rows_inserted=inserted,
            credits_remaining=credits,
            status="ok",
        )
        .on_conflict_do_update(
            constraint="uq_sync_resource_source",
            set_={
                "last_fetched_at": now,
                "rows_inserted": inserted,
                "credits_remaining": credits,
                "status": "ok",
            },
        )
    )
    session.execute(stmt)
    session.commit()

    log.info(
        "Captura odds: %s | créditos restantes: %s",
        result,
        source.last_remaining,
    )
    return result


def capture_odds_job() -> dict[str, object]:
    if not settings.odds_api_key:
        log.warning("ODDS_API_KEY no configurada; salto la captura de odds.")
        return {"skipped": "no_api_key"}

    source = make_odds_source()
    with SessionLocal() as session:
        return _run_capture(session, source)
