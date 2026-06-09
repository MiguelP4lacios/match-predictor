"""Interfaces de fuentes — SEGREGADAS por capacidad (ISP de SOLID).

Una sola interfaz `DataSource` gorda obligaría, p.ej., a eloratings (que NO tiene
partidos) a implementar fetch_matches() con NotImplementedError. Mal. En su lugar,
cada fuente implementa SOLO las capacidades que provee:

    ResultsSource   -> partidos            (martj42, api_football)
    GoalSource      -> goles               (martj42)
    ShootoutSource  -> definiciones penales (martj42)
    OddsSource      -> cuotas              (odds_api)
    RatingSource    -> Elo                 (calculado por nosotros, no se ingesta)
    StatsSource     -> xG / stats          (statsbomb)         [bloque siguiente]

Son `Protocol`s: una fuente "es" un ResultsSource por estructura, sin herencia.
"""

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from app.ingestion.dto import RawGoal, RawMatch, RawOdds, RawShootout
from app.models.enums import DataSource


@runtime_checkable
class ResultsSource(Protocol):
    source: DataSource

    def fetch_matches(self) -> Iterator[RawMatch]: ...


@runtime_checkable
class GoalSource(Protocol):
    source: DataSource

    def fetch_goals(self) -> Iterator[RawGoal]: ...


@runtime_checkable
class ShootoutSource(Protocol):
    source: DataSource

    def fetch_shootouts(self) -> Iterator[RawShootout]: ...


@runtime_checkable
class OddsSource(Protocol):
    source: DataSource

    def fetch_odds(self) -> Iterator[RawOdds]: ...
