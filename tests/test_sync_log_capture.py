"""TDD RED → GREEN — capture_odds_job escribe/actualiza SyncLog.

Escenarios:
  S1 — Tras captura con FakeOddsSource (0 odds) → fila odds_api:capture en sync_log
       con rows_inserted=0 y credits_remaining correcto.
  S2 — Segunda ejecución → exactamente 1 fila (upsert, no insert duplicado).
  S3 — FakeOddsSource con last_remaining=None → credits_remaining=None (no explota).

NEVER usa la API real. FakeOddsSource devuelve iter vacío; source.last_remaining
simula el header X-Requests-Remaining devuelto por The Odds API.
"""

from collections.abc import Iterator

from sqlalchemy import func, select

from app.ingestion.dto import RawOdds
from app.models.enums import DataSource
from app.models.sync import SyncLog
from app.scheduler.jobs import _run_capture

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_RESOURCE = "odds_api:capture"


class FakeOddsSource:
    """Implementa OddsSource Protocol; nunca llama a la red."""

    source = DataSource.ODDS_API

    def __init__(self, last_remaining: str | None = "488") -> None:
        self.last_remaining = last_remaining

    def fetch_odds(self) -> Iterator[RawOdds]:
        return iter([])


# ---------------------------------------------------------------------------
# S1 — primera captura escribe la fila correcta
# ---------------------------------------------------------------------------


def test_capture_writes_sync_log_row(db_session):
    """Tras _run_capture con fuente fake → fila odds_api:capture con counts correctos."""
    source = FakeOddsSource(last_remaining="488")

    _run_capture(db_session, source)

    row = db_session.scalar(select(SyncLog).where(SyncLog.resource == _RESOURCE))
    assert row is not None, "Debe existir una fila odds_api:capture en sync_log"
    assert row.source == DataSource.ODDS_API
    assert row.rows_inserted == 0  # no odds en fake
    assert row.credits_remaining == 488  # int(last_remaining)
    assert row.status == "ok"
    assert row.last_fetched_at is not None


# ---------------------------------------------------------------------------
# S2 — segunda ejecución: upsert, no duplicado
# ---------------------------------------------------------------------------


def test_capture_upserts_not_duplicates(db_session):
    """Dos capturas consecutivas → exactamente 1 fila en sync_log."""
    source = FakeOddsSource(last_remaining="488")

    _run_capture(db_session, source)
    _run_capture(db_session, source)

    count = db_session.scalar(
        select(func.count()).select_from(SyncLog).where(SyncLog.resource == _RESOURCE)
    )
    assert count == 1, "Upsert por (resource, source) — nunca debe duplicar la fila"


# ---------------------------------------------------------------------------
# S3 — last_remaining=None → credits_remaining=None (no crash)
# ---------------------------------------------------------------------------


def test_capture_handles_none_credits(db_session):
    """Si last_remaining es None (API no envió el header) → credits_remaining=None."""
    source = FakeOddsSource(last_remaining=None)

    _run_capture(db_session, source)

    row = db_session.scalar(select(SyncLog).where(SyncLog.resource == _RESOURCE))
    assert row is not None
    assert row.credits_remaining is None  # None propagado correctamente
    assert row.rows_inserted == 0
