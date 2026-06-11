"""Servicio de observabilidad operacional — serve-from-DB, cero llamadas externas.

Lee sync_log + odds + model_version + match para calcular veredictos ok/warn/stale
con umbrales constantes. Puro-ish: recibe session, devuelve HealthFull.

Umbrales (task 1.5 / spec HO1):
  odds_age : ok ≤ 4h · warn > 4h y ≤ 10h · stale > 10h
  credits  : ok ≥ 100 · warn < 100 (null → warn)
  model    : ok si existe ModelVersion · stale si ninguna
  results  : ok si latest_date ≤ 3 días atrás · stale si null o > 3d
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import DataSource, MatchStatus
from app.models.match import Match
from app.models.model import ModelVersion
from app.models.sync import SyncLog

# ---------------------------------------------------------------------------
# Umbrales (constantes del módulo, testables)
# ---------------------------------------------------------------------------

ODDS_AGE_WARN_H: float = 4.0  # > 4h → warn
ODDS_AGE_STALE_H: float = 10.0  # > 10h → stale
CREDITS_WARN: int = 100  # < 100 → warn
RESULTS_STALE_DAYS: int = 3  # > 3 días sin resultado → stale

# Orden de severidad (mayor índice = peor)
_SEVERITY: dict[str, int] = {"ok": 0, "warn": 1, "stale": 2}


def _worst(*verdicts: str) -> str:
    return max(verdicts, key=lambda v: _SEVERITY.get(v, 0))


# ---------------------------------------------------------------------------
# Pydantic schemas de respuesta (usados por el router y los tests)
# ---------------------------------------------------------------------------


class OddsCapture(BaseModel):
    last_at: datetime | None
    age_hours: float | None
    verdict: str  # "ok" | "warn" | "stale"


class OddsCredits(BaseModel):
    remaining: int | None
    verdict: str  # "ok" | "warn"


class ModelHealth(BaseModel):
    name: str | None
    verdict: str  # "ok" | "stale"


class ResultsHealth(BaseModel):
    latest_date: date | None
    verdict: str  # "ok" | "stale"


class HealthFull(BaseModel):
    overall: str  # peor de los veredictos individuales
    odds_capture: OddsCapture
    odds_credits: OddsCredits
    model: ModelHealth
    results: ResultsHealth


# ---------------------------------------------------------------------------
# Funciones puras de veredicto (fáciles de unit-testear)
# ---------------------------------------------------------------------------


def _odds_age_verdict(age_hours: float | None) -> str:
    if age_hours is None:
        return "stale"
    if age_hours <= ODDS_AGE_WARN_H:
        return "ok"
    if age_hours <= ODDS_AGE_STALE_H:
        return "warn"
    return "stale"


def _credits_verdict(remaining: int | None) -> str:
    if remaining is None:
        return "warn"
    return "ok" if remaining >= CREDITS_WARN else "warn"


def _model_verdict(name: str | None) -> str:
    return "ok" if name else "stale"


def _results_verdict(latest_date: date | None) -> str:
    if latest_date is None:
        return "stale"
    cutoff = datetime.now(UTC).date() - timedelta(days=RESULTS_STALE_DAYS)
    return "ok" if latest_date >= cutoff else "stale"


# ---------------------------------------------------------------------------
# Servicio principal
# ---------------------------------------------------------------------------


def get_health(session: Session) -> HealthFull:
    """Lee Postgres y devuelve HealthFull con veredictos por umbral.

    Invariante: CERO llamadas HTTP externas.
    """
    now = datetime.now(UTC).replace(tzinfo=None)

    # --- 1. sync_log odds_api:capture ---
    sync_row: SyncLog | None = session.scalar(
        select(SyncLog)
        .where(
            SyncLog.resource == "odds_api:capture",
            SyncLog.source == DataSource.ODDS_API,
        )
        .order_by(SyncLog.last_fetched_at.desc())
        .limit(1)
    )

    last_at: datetime | None = sync_row.last_fetched_at if sync_row else None
    age_hours: float | None = None
    if last_at is not None:
        delta = now - last_at
        age_hours = round(delta.total_seconds() / 3600, 2)

    credits: int | None = sync_row.credits_remaining if sync_row else None

    # --- 2. Modelo activo ---
    model_name: str | None = session.scalar(
        select(ModelVersion.name).order_by(ModelVersion.id.desc()).limit(1)
    )

    # --- 3. Último partido FINISHED ---
    latest_finished: date | None = session.scalar(
        select(func.max(Match.match_date)).where(Match.status == MatchStatus.FINISHED)
    )

    # --- Veredictos ---
    oc_verdict = _odds_age_verdict(age_hours)
    cr_verdict = _credits_verdict(credits)
    mv_verdict = _model_verdict(model_name)
    res_verdict = _results_verdict(latest_finished)
    overall = _worst(oc_verdict, cr_verdict, mv_verdict, res_verdict)

    return HealthFull(
        overall=overall,
        odds_capture=OddsCapture(
            last_at=last_at,
            age_hours=age_hours,
            verdict=oc_verdict,
        ),
        odds_credits=OddsCredits(
            remaining=credits,
            verdict=cr_verdict,
        ),
        model=ModelHealth(
            name=model_name,
            verdict=mv_verdict,
        ),
        results=ResultsHealth(
            latest_date=latest_finished,
            verdict=res_verdict,
        ),
    )
