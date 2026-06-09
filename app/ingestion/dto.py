"""DTOs neutrales de ingesta.

Las fuentes (DataSource) hablan ESTE lenguaje, no el de SQLAlchemy. El pipeline
traduce estos objetos a entidades de la BD. Así la fuente es un detalle del borde
(hexagonal): cambiarla no toca el modelo de datos.
"""

from dataclasses import dataclass
from datetime import date, datetime

from app.models.enums import DataSource


@dataclass(frozen=True, slots=True)
class RawMatch:
    source: DataSource
    match_date: date
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    tournament: str
    city: str | None
    country: str | None
    neutral: bool


@dataclass(frozen=True, slots=True)
class RawGoal:
    source: DataSource
    match_date: date
    home_team: str
    away_team: str
    scoring_team: str
    scorer: str | None
    minute: int | None
    own_goal: bool
    penalty: bool


@dataclass(frozen=True, slots=True)
class RawShootout:
    source: DataSource
    match_date: date
    home_team: str
    away_team: str
    winner: str


@dataclass(frozen=True, slots=True)
class RawOdds:
    """Una cotización puntual: un (evento, casa, mercado, outcome) capturado."""

    source: DataSource
    event_id: str
    commence_time: datetime
    home_team: str
    away_team: str
    bookmaker: str
    market_key: str  # h2h | totals | outrights
    outcome_name: str  # nombre de equipo, "Draw", "Over", "Under"
    price: float  # cuota decimal
    line: float | None  # punto de Over/Under; None en h2h
    captured_at: datetime
