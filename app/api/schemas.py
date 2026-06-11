"""Schemas Pydantic v2 para la API de solo lectura.

Un módulo único, organizado por recurso. Todos usan ``from_attributes=True``
para deserializar desde objetos SQLAlchemy directamente.

Sección de schemas:
  - Señales (+EV)
  - Partidos (próximos y detalle)
  - Modelo (versión activa + backtest)
  - Paper (apuestas modo papel + ROI)
  - Grupos (tabla de posiciones WC2026)
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Base compartida con from_attributes=True
# ---------------------------------------------------------------------------


class _ORMBase(BaseModel):
    """Base con from_attributes para deserializar desde ORM objects."""

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Señales (+EV)
# ---------------------------------------------------------------------------


class SignalItem(_ORMBase):
    """Ítem de señal de valor esperado positivo."""

    id: int
    match_id: int | None
    match_date: date
    kickoff_at: datetime | None
    home_team: str
    away_team: str
    market_type: str
    outcome_code: str | None
    p_model: float
    best_odds: float
    bookmaker: str
    edge: float
    ev: float
    kelly_fraction: float
    recommended_stake: Decimal
    captured_at: datetime


class SignalList(BaseModel):
    """Respuesta paginada de señales."""

    items: list[SignalItem]
    total: int


# ---------------------------------------------------------------------------
# Partidos
# ---------------------------------------------------------------------------


class UpcomingMatch(_ORMBase):
    """Partido próximo (SCHEDULED) con predicciones 1X2 opcionales."""

    id: int
    match_date: date
    kickoff_at: datetime | None
    home_team: str
    away_team: str
    neutral_site: bool
    stage: str | None
    p_home: float | None
    p_draw: float | None
    p_away: float | None
    low_confidence: bool | None


class PredictionItem(_ORMBase):
    """Predicción individual (cualquier mercado)."""

    id: int
    market_type: str
    outcome_code: str | None
    probability: float
    low_confidence: bool


class OddsItem(_ORMBase):
    """Snapshot de cuota — último por (bookmaker, outcome_code)."""

    bookmaker: str
    outcome_code: str | None
    decimal_odds: float
    captured_at: datetime


class MatchDetail(_ORMBase):
    """Detalle completo de un partido."""

    id: int
    match_date: date
    kickoff_at: datetime | None
    home_team: str
    away_team: str
    neutral_site: bool
    stage: str | None
    status: str
    home_score: int | None
    away_score: int | None
    predictions: list[PredictionItem]
    last_odds: list[OddsItem]
    signals: list[SignalItem]


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------


class ModelInfo(BaseModel):
    """Versión activa del modelo con métricas de backtest y calibración."""

    name: str
    params_summary: dict | None
    backtest: dict | None
    calibration: list | None


# ---------------------------------------------------------------------------
# Paper (apuestas modo papel)
# ---------------------------------------------------------------------------


class PaperStats(BaseModel):
    """Estadísticas de apuestas en modo papel."""

    total: int
    open: int
    settled: int
    roi: float | None


# ---------------------------------------------------------------------------
# Grupos WC2026
# ---------------------------------------------------------------------------


class StandingRowSchema(BaseModel):
    """Fila de la tabla de posiciones."""

    team_name: str
    pj: int
    g: int
    e: int
    p: int
    gf: int
    gc: int
    dg: int
    pts: int


class GroupItem(BaseModel):
    """Resumen de grupo: equipos + tabla de posiciones actual."""

    name: str
    teams: list[str]
    standings: list[StandingRowSchema]


class FixtureItem(BaseModel):
    """Partido de grupo con predicciones opcionales."""

    id: int
    match_date: date
    kickoff_at: datetime | None
    home_team: str
    away_team: str
    status: str
    home_score: int | None
    away_score: int | None
    p_home: float | None
    p_draw: float | None
    p_away: float | None


class GroupDetail(GroupItem):
    """Detalle de un grupo: equipos + tabla + fixtures con predicciones."""

    fixtures: list[FixtureItem]


# ---------------------------------------------------------------------------
# Explicación de señal (+EV)
# ---------------------------------------------------------------------------


class ExplainStep(BaseModel):
    """Un paso dentro de una sección de explicación.

    formatted=null → el front formatea raw con formatters.ts (canónicos).
    formatted=str  → el servidor ya lo formateó; renderizar verbatim (intermedios).
    """

    key: str
    label_es: str
    raw: float | str | bool | int | None
    formatted: str | None
    glossary_term: str | None = None


class ExplainSection(BaseModel):
    """Sección trazable de la explicación."""

    key: str
    titulo: str
    steps: list[ExplainStep]
    note: str | None = None


class SignalExplanation(BaseModel):
    """Respuesta del endpoint GET /signals/{id}/explain."""

    sections: list[ExplainSection]
