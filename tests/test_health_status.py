"""TDD RED → GREEN — health_status: get_health() con datos sintéticos.

Escenarios verbatim de spec HO1 + task 1.5:
  S1 — last_fetched_at hace 2h, credits=488  → odds_capture.verdict=ok, credits=ok
  S2 — last_fetched_at hace 12h              → odds_capture.verdict=stale
  S3 — credits_remaining=50                 → odds_credits.verdict=warn
  S4 — sin fila sync_log                    → odds_capture.verdict=stale (never captured)
  S5 — last_fetched_at hace 6h (entre 4-10h) → odds_capture.verdict=warn (triangulación)
  S6 — overall = peor de los veredictos individuales

Umbrales (task 1.5):
  odds age: ok ≤ 4h · warn > 4h y ≤ 10h · stale > 10h
  credits : ok ≥ 100 · warn < 100

Nota sobre S6: para aislar el veredicto que queremos testear, sembramos un
ModelVersion + Match FINISHED reciente (así model y results son "ok") y solo
variamos las métricas de odds.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.model.health_status import get_health
from app.models.competition import Competition
from app.models.enums import CompetitionKind, DataSource, MatchStatus
from app.models.match import Match
from app.models.model import ModelVersion
from app.models.sync import SyncLog
from app.models.team import Team

# ---------------------------------------------------------------------------
# Helpers para sembrar datos
# ---------------------------------------------------------------------------


def _seed_sync_log(
    session: Session,
    hours_ago: float,
    credits: int | None = 488,
) -> SyncLog:
    """Inserta una fila sync_log odds_api:capture con last_fetched_at hace N horas."""
    now = datetime.now(UTC).replace(tzinfo=None)
    row = SyncLog(
        resource="odds_api:capture",
        source=DataSource.ODDS_API,
        last_fetched_at=now - timedelta(hours=hours_ago),
        credits_remaining=credits,
        rows_inserted=5,
        status="ok",
    )
    session.add(row)
    session.flush()
    return row


def _seed_ok_model_and_result(session: Session) -> None:
    """Siembra ModelVersion + Match FINISHED reciente para que esas métricas sean 'ok'.

    Permite aislar en los tests de 'overall' solo la métrica que queremos variar.
    """
    mv = ModelVersion(name=f"test-model-{id(session)}", params_json={})
    session.add(mv)

    comp = Competition(name=f"Test Comp {id(session)}", kind=CompetitionKind.WORLD_CUP)
    session.add(comp)
    session.flush()

    home = Team(name=f"H Overall {id(session)}")
    away = Team(name=f"A Overall {id(session)}")
    session.add_all([home, away])
    session.flush()

    today = datetime.now(UTC).date()
    match = Match(
        competition_id=comp.id,
        match_date=today,
        home_team_id=home.id,
        away_team_id=away.id,
        status=MatchStatus.FINISHED,
        home_score=1,
        away_score=0,
    )
    session.add(match)
    session.flush()


# ---------------------------------------------------------------------------
# S1 — captura reciente (2h) + créditos ok → verdicto ok
# ---------------------------------------------------------------------------


def test_recent_capture_ok(db_session):
    """last_fetched_at hace 2h, credits=488 → odds_capture.verdict='ok', credits.verdict='ok'."""
    _seed_sync_log(db_session, hours_ago=2.0, credits=488)

    health = get_health(db_session)

    assert health.odds_capture.verdict == "ok"
    assert health.odds_capture.age_hours is not None
    assert 1.9 < health.odds_capture.age_hours < 2.1  # ~2h
    assert health.odds_credits.verdict == "ok"
    assert health.odds_credits.remaining == 488


# ---------------------------------------------------------------------------
# S2 — captura antigua (12h) → stale
# ---------------------------------------------------------------------------


def test_old_capture_stale(db_session):
    """last_fetched_at hace 12h → odds_capture.verdict='stale', age_hours≈12."""
    _seed_sync_log(db_session, hours_ago=12.0, credits=488)

    health = get_health(db_session)

    assert health.odds_capture.verdict == "stale"
    assert health.odds_capture.age_hours is not None
    assert 11.9 < health.odds_capture.age_hours < 12.1


# ---------------------------------------------------------------------------
# S3 — créditos bajos (50) → warn
# ---------------------------------------------------------------------------


def test_low_credits_warn(db_session):
    """credits_remaining=50 → odds_credits.verdict='warn'."""
    _seed_sync_log(db_session, hours_ago=2.0, credits=50)

    health = get_health(db_session)

    assert health.odds_credits.verdict == "warn"
    assert health.odds_credits.remaining == 50


# ---------------------------------------------------------------------------
# S4 — sin fila sync_log → stale (nunca capturado)
# ---------------------------------------------------------------------------


def test_no_capture_row_stale(db_session):
    """Sin fila odds_api:capture → last_at=None, verdict='stale'."""
    health = get_health(db_session)

    assert health.odds_capture.last_at is None
    assert health.odds_capture.verdict == "stale"
    assert health.odds_credits.remaining is None


# ---------------------------------------------------------------------------
# S5 — captura entre 4-10h → warn (triangulación del umbral)
# ---------------------------------------------------------------------------


def test_borderline_warn(db_session):
    """last_fetched_at hace 6h (entre 4-10h) → odds_capture.verdict='warn'."""
    _seed_sync_log(db_session, hours_ago=6.0, credits=488)

    health = get_health(db_session)

    assert health.odds_capture.verdict == "warn"
    assert health.odds_capture.age_hours is not None
    assert 5.9 < health.odds_capture.age_hours < 6.1


# ---------------------------------------------------------------------------
# S6 — overall = peor de los veredictos
# ---------------------------------------------------------------------------


def test_overall_is_worst(db_session):
    """overall debe reflejar el peor veredicto individual.

    credits=50 (warn) + odds_capture 2h (ok) + model ok + results ok → overall='warn'.
    Sembramos model y results 'ok' para aislar la señal de créditos.
    """
    _seed_ok_model_and_result(db_session)
    _seed_sync_log(db_session, hours_ago=2.0, credits=50)

    health = get_health(db_session)

    assert health.overall == "warn"
    assert health.model.verdict == "ok"
    assert health.results.verdict == "ok"


def test_overall_stale_dominates(db_session):
    """Si hay un stale (odds_capture 12h), overall='stale' aunque créditos sean ok."""
    _seed_ok_model_and_result(db_session)
    _seed_sync_log(db_session, hours_ago=12.0, credits=488)

    health = get_health(db_session)

    assert health.overall == "stale"
