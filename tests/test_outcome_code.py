"""Tests para outcome code resolution (odds-capture R2).

Spec: odds-capture R2, escenarios S1-S2.
TDD RED: fallan hasta que _outcome_code SOLO asigne DRAW para outcome_name=="Draw"
y descarte/log si el equipo no se resuelve.

Estos tests son unitarios puros: no tocan la BD.
Testean la lógica de OddsCapturePipeline._outcome_code() y el comportamiento
de captura ante nombres de equipo irresolutos.
"""

import datetime
import logging
from collections.abc import Iterator
from unittest.mock import MagicMock

from app.ingestion.dto import RawOdds
from app.ingestion.odds_pipeline import OddsCapturePipeline
from app.models.enums import DataSource


def _make_h2h_odds(outcome_name: str, event_id: str = "ev1") -> RawOdds:
    return RawOdds(
        source=DataSource.ODDS_API,
        event_id=event_id,
        commence_time=datetime.datetime(2026, 6, 14, 18, 0),
        home_team="France",
        away_team="Germany",
        bookmaker="pinnacle",
        market_key="h2h",
        outcome_name=outcome_name,
        price=2.0,
        line=None,
        captured_at=datetime.datetime(2026, 6, 10, 12, 0),
    )


class _MockTeam:
    def __init__(self, team_id: int):
        self.id = team_id


class _AlwaysResolvesResolver:
    """Resuelve siempre: 'France' → team 1, 'Germany' → team 2, otros → None."""

    def resolve(self, source, name, canonical_name=None, create_missing=False):
        mapping = {"France": _MockTeam(1), "Germany": _MockTeam(2)}
        return mapping.get(canonical_name or name)


class _NeverResolvesResolver:
    """Nunca resuelve equipos → simula un nombre desconocido."""

    def resolve(self, source, name, canonical_name=None, create_missing=False):
        return None


def _pipeline_with_resolver(resolver) -> OddsCapturePipeline:
    """Pipeline stub con session y source falsos."""
    session = MagicMock()
    source = MagicMock()
    source.source = DataSource.ODDS_API
    pipeline = OddsCapturePipeline(session, source)
    pipeline._resolver = resolver
    return pipeline


# ---------------------------------------------------------------------------
# S1: "Draw" outcome code assigned correctly
# ---------------------------------------------------------------------------


def test_draw_outcome_from_literal_draw():
    """outcome_name == 'Draw' (exacto) → 'DRAW'."""
    pipeline = _pipeline_with_resolver(_AlwaysResolvesResolver())
    ro = _make_h2h_odds("Draw")
    code = pipeline._outcome_code(ro, our_home_id=1, our_away_id=2)
    assert code == "DRAW"


def test_draw_case_insensitive():
    """outcome_name 'draw' (lowercase) → también 'DRAW'."""
    pipeline = _pipeline_with_resolver(_AlwaysResolvesResolver())
    ro = _make_h2h_odds("draw")
    code = pipeline._outcome_code(ro, our_home_id=1, our_away_id=2)
    assert code == "DRAW"


def test_home_outcome_code():
    """outcome_name == equipo home → 'HOME'."""
    pipeline = _pipeline_with_resolver(_AlwaysResolvesResolver())
    ro = _make_h2h_odds("France")
    code = pipeline._outcome_code(ro, our_home_id=1, our_away_id=2)
    assert code == "HOME"


def test_away_outcome_code():
    """outcome_name == equipo away → 'AWAY'."""
    pipeline = _pipeline_with_resolver(_AlwaysResolvesResolver())
    ro = _make_h2h_odds("Germany")
    code = pipeline._outcome_code(ro, our_home_id=1, our_away_id=2)
    assert code == "AWAY"


# ---------------------------------------------------------------------------
# S2: Unresolved team name is NOT treated as DRAW
# ---------------------------------------------------------------------------


def test_unresolved_team_returns_none_not_draw(caplog):
    """outcome_name desconocido (resolver → None) → retorna None y loguea warning."""
    pipeline = _pipeline_with_resolver(_NeverResolvesResolver())
    ro = _make_h2h_odds("Côte d'Ivoire")

    with caplog.at_level(logging.WARNING):
        code = pipeline._outcome_code(ro, our_home_id=1, our_away_id=2)

    assert code is None  # NO 'DRAW'
    assert "Côte d'Ivoire" in caplog.text


def test_unresolved_team_not_inserted(db_session, caplog):
    """Odds con equipo irresoluto → NO se inserta fila, se loguea warning."""
    from sqlalchemy import select

    from app.models import Odds

    class FakeOddsSourceUnresolved:
        source = DataSource.ODDS_API

        def fetch_odds(self) -> Iterator[RawOdds]:
            yield _make_h2h_odds("EquipoDesconocidoXYZ")

    source = FakeOddsSourceUnresolved()
    pipeline = OddsCapturePipeline(db_session, source)

    with caplog.at_level(logging.WARNING):
        pipeline.capture()

    # No se insertó la fila para este event_id específico

    inserted_row = db_session.scalar(select(Odds).where(Odds.source_event_id == "ev1"))
    assert inserted_row is None
    # El warning debe mencionar el nombre irresoluto
    assert "EquipoDesconocidoXYZ" in caplog.text
