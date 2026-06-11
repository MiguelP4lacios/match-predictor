"""TDD — Task 4.3: capture_futures_odds_job escribe SyncLog.

Escenarios de spec odds-capture:
  FJ1 — Captura con FakeOutrightSource → fila odds_api:futures_capture en sync_log
  FJ2 — Segunda ejecución → exactamente 1 fila (upsert, no duplicado)
  FJ3 — odds_futures_enabled=False → función devuelve {"skipped": "disabled"}
         sin llamar a la fuente de datos
  FJ4 — last_remaining=None → credits_remaining=None (no crash)

NUNCA usa la API real.
"""

from collections.abc import Iterator

from sqlalchemy import func, select

from app.ingestion.dto import RawOdds
from app.models.enums import DataSource
from app.models.sync import SyncLog

_FUTURES_RESOURCE = "odds_api:futures_capture"


# ---------------------------------------------------------------------------
# Fake source para futuros
# ---------------------------------------------------------------------------


class FakeFuturesSource:
    """Implementa OddsSource; nunca llama a la red."""

    source = DataSource.ODDS_API

    def __init__(self, last_remaining: str | None = "452") -> None:
        self.last_remaining = last_remaining

    def fetch_odds(self) -> Iterator[RawOdds]:
        return iter([])


# ---------------------------------------------------------------------------
# FJ1 — primera captura escribe la fila correcta
# ---------------------------------------------------------------------------


def test_futures_capture_writes_sync_log(db_session):
    """_run_futures_capture() → fila odds_api:futures_capture con rows_inserted y credits."""
    from app.scheduler.jobs import _run_futures_capture

    source = FakeFuturesSource(last_remaining="452")
    _run_futures_capture(db_session, source)

    row = db_session.scalar(select(SyncLog).where(SyncLog.resource == _FUTURES_RESOURCE))
    assert row is not None, "Debe existir una fila odds_api:futures_capture"
    assert row.source == DataSource.ODDS_API
    assert row.rows_inserted == 0
    assert row.credits_remaining == 452
    assert row.status == "ok"
    assert row.last_fetched_at is not None


# ---------------------------------------------------------------------------
# FJ2 — segunda ejecución: upsert, no duplicado
# ---------------------------------------------------------------------------


def test_futures_capture_upserts_not_duplicates(db_session):
    """Dos capturas consecutivas → exactamente 1 fila en sync_log."""
    from app.scheduler.jobs import _run_futures_capture

    source = FakeFuturesSource(last_remaining="452")
    _run_futures_capture(db_session, source)
    _run_futures_capture(db_session, source)

    count = db_session.scalar(
        select(func.count())
        .select_from(SyncLog)
        .where(SyncLog.resource == _FUTURES_RESOURCE)
    )
    assert count == 1, "Upsert por (resource, source) — nunca debe duplicar la fila"


# ---------------------------------------------------------------------------
# FJ3 — odds_futures_enabled=False → skip
# ---------------------------------------------------------------------------


def test_futures_job_skips_when_disabled(monkeypatch):
    """capture_futures_odds_job() con odds_futures_enabled=False → {skipped: disabled}."""
    from app.core.config import settings
    from app.scheduler.jobs import capture_futures_odds_job

    monkeypatch.setattr(settings, "odds_futures_enabled", False)
    result = capture_futures_odds_job()

    assert result == {"skipped": "disabled"}


# ---------------------------------------------------------------------------
# FJ4 — last_remaining=None → credits_remaining=None (no crash)
# ---------------------------------------------------------------------------


def test_futures_capture_handles_none_credits(db_session):
    """Si last_remaining es None → credits_remaining=None propagado."""
    from app.scheduler.jobs import _run_futures_capture

    source = FakeFuturesSource(last_remaining=None)
    _run_futures_capture(db_session, source)

    row = db_session.scalar(select(SyncLog).where(SyncLog.resource == _FUTURES_RESOURCE))
    assert row is not None
    assert row.credits_remaining is None
