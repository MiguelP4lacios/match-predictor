"""Tests para upsert idempotente de match (match-ingestion R2).

Spec: match-ingestion R2, escenarios S1-S3.
TDD RED: fallan hasta que _load_matches use ON CONFLICT DO UPDATE.

Usa DB real (docker compose db) con fixture db_session para rollback automático.
Los equipos usan nombres únicos (prefijo TEST_) para no colisionar con datos
de producción ya cargados en la BD.
"""

import datetime
from collections.abc import Iterator

from sqlalchemy import func, select

from app.ingestion.dto import RawMatch
from app.ingestion.pipeline import ResultsIngestionPipeline
from app.models import Match, SyncLog, Team
from app.models.enums import DataSource

# ---------------------------------------------------------------------------
# Fake source para pruebas
# ---------------------------------------------------------------------------

class FakeResultsSource:
    source = DataSource.MARTJ42

    def __init__(self, matches: list[RawMatch]) -> None:
        self._matches = matches

    def fetch_matches(self) -> Iterator[RawMatch]:
        yield from self._matches


def _make_raw_match(
    home_team: str = "TEST_AlphaFC",
    away_team: str = "TEST_BetaFC",
    match_date: datetime.date = datetime.date(2026, 7, 1),
    home_score: int | None = 2,
    away_score: int | None = 1,
    tournament: str = "FIFA World Cup",
) -> RawMatch:
    return RawMatch(
        source=DataSource.MARTJ42,
        match_date=match_date,
        home_team=home_team,
        away_team=away_team,
        home_score=home_score,
        away_score=away_score,
        neutral=True,
        tournament=tournament,
        city="New York",
        country="USA",
    )


def _count_test_matches(session, home_name: str, away_name: str) -> int:
    """Cuenta solo los matches del par de equipos creados por el test."""
    home = session.scalar(select(Team).where(Team.name == home_name))
    away = session.scalar(select(Team).where(Team.name == away_name))
    if home is None or away is None:
        return 0
    return session.scalar(
        select(func.count(Match.id)).where(
            Match.home_team_id == home.id,
            Match.away_team_id == away.id,
        )
    ) or 0


# ---------------------------------------------------------------------------
# S1: Re-ingestion does not duplicate matches
# ---------------------------------------------------------------------------

def test_reingest_same_data_no_duplicate(db_session):
    """Correr _load_matches dos veces con los mismos datos → exactamente 1 fila."""
    raw = _make_raw_match()
    source1 = FakeResultsSource([raw])
    pipeline1 = ResultsIngestionPipeline(db_session, source1)
    pipeline1._load_matches()

    count_after_first = _count_test_matches(db_session, raw.home_team, raw.away_team)
    assert count_after_first == 1  # insertó 1 fila

    # Segunda ingesta: mismo par, misma fecha → ON CONFLICT DO UPDATE, no INSERT
    source2 = FakeResultsSource([raw])
    pipeline2 = ResultsIngestionPipeline(db_session, source2)
    # Limpiar caché del resolver para que vuelva a consultar la BD
    pipeline2._resolver._name_cache.clear()
    pipeline2._resolver._alias_cache.clear()
    pipeline2._competitions.clear()
    pipeline2._load_matches()

    count_after_second = _count_test_matches(db_session, raw.home_team, raw.away_team)
    assert count_after_second == count_after_first  # sin duplicados


# ---------------------------------------------------------------------------
# S2: Updated score is applied on re-ingestion
# ---------------------------------------------------------------------------

def test_reingest_updates_score(db_session):
    """Upsert actualiza score si el source tiene datos nuevos."""
    raw_original = _make_raw_match(home_score=0, away_score=0)
    source1 = FakeResultsSource([raw_original])
    pipeline1 = ResultsIngestionPipeline(db_session, source1)
    pipeline1._load_matches()

    # Re-ingestar con score distinto
    raw_updated = _make_raw_match(home_score=3, away_score=3)
    source2 = FakeResultsSource([raw_updated])
    pipeline2 = ResultsIngestionPipeline(db_session, source2)
    pipeline2._resolver._name_cache.clear()
    pipeline2._resolver._alias_cache.clear()
    pipeline2._competitions.clear()
    pipeline2._load_matches()

    # Debe haber exactamente 1 fila con el score actualizado
    home = db_session.scalar(select(Team).where(Team.name == raw_original.home_team))
    away = db_session.scalar(select(Team).where(Team.name == raw_original.away_team))
    matches = db_session.scalars(
        select(Match).where(
            Match.home_team_id == home.id,
            Match.away_team_id == away.id,
        )
    ).all()

    assert len(matches) == 1
    assert matches[0].home_score == 3
    assert matches[0].away_score == 3


# ---------------------------------------------------------------------------
# S3: Incremental re-ingest without force stays skipped
# ---------------------------------------------------------------------------

def test_run_force_false_skips_if_already_synced(db_session):
    """run(force=False) retorna skipped=True cuando sync_log ya existe para MARTJ42.

    La BD de producción ya tiene datos de martj42 → sync_log existe → el pipeline
    debe retornar skipped sin tocar match.
    """
    raw = _make_raw_match()
    source = FakeResultsSource([raw])
    pipeline = ResultsIngestionPipeline(db_session, source)

    # En la BD de producción ya existe sync_log para martj42:results.
    # Si no existe (test en BD limpia), lo creamos.
    resource = "martj42:results"
    existing_sync = db_session.scalar(
        select(SyncLog).where(
            SyncLog.resource == resource,
            SyncLog.source == DataSource.MARTJ42,
        )
    )
    if existing_sync is None:
        db_session.add(
            SyncLog(
                resource=resource,
                source=DataSource.MARTJ42,
                last_fetched_at=datetime.datetime(2026, 1, 1),
                status="ok",
            )
        )
        db_session.flush()

    result = pipeline.run(force=False)

    assert result.get("skipped") is True
