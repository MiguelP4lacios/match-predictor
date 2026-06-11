"""TDD — Task 4.1 + 4.2: captura de odds de futuros (OUTRIGHT_WINNER).

Escenarios de spec odds-capture:
  FC1 — Odds outright para "Brazil" → Odds(OUTRIGHT_WINNER, outcome_team_id=brazil_id)
  FC2 — Nombre irresoluble "Brasil" → row descartado, sin inserción
  FC3 — fetch_odds() con evento sin home_team/away_team → no KeyError (outright shape)

NUNCA llama a la API real: FakeOutrightSource devuelve datos de fixture.
"""

import datetime
from collections.abc import Iterator

import pytest
from sqlalchemy import select

from app.ingestion.dto import RawOdds
from app.ingestion.odds_pipeline import OddsCapturePipeline
from app.models import Competition, Odds, Team
from app.models.enums import CompetitionKind, DataSource, MarketType

# ---------------------------------------------------------------------------
# Fake source: simula la respuesta de The Odds API para outrights
# ---------------------------------------------------------------------------


class FakeOutrightSource:
    """Implementa OddsSource para mercados outrights — nunca llama a la red."""

    source = DataSource.ODDS_API
    last_remaining: str | None = "452"

    def __init__(self, odds: list[RawOdds]) -> None:
        self._odds = odds

    def fetch_odds(self) -> Iterator[RawOdds]:
        yield from self._odds


_CAPTURED_AT = datetime.datetime(2026, 6, 11, 12, 0)
_COMMENCE_AT = datetime.datetime(2026, 11, 1, 0, 0)  # Final del Mundial


def _make_outright(
    outcome_name: str,
    price: float = 5.5,
    bookmaker: str = "pinnacle",
    event_id: str = "wc2026-winner",
) -> RawOdds:
    """Construye un RawOdds de tipo 'outrights' (home_team/away_team vacíos)."""
    return RawOdds(
        source=DataSource.ODDS_API,
        event_id=event_id,
        commence_time=_COMMENCE_AT,
        home_team="",   # outright events no tienen home/away
        away_team="",
        bookmaker=bookmaker,
        market_key="outrights",
        outcome_name=outcome_name,
        price=price,
        line=None,
        captured_at=_CAPTURED_AT,
    )


# ---------------------------------------------------------------------------
# Helpers de setup
# ---------------------------------------------------------------------------


def _wc_competition(session) -> Competition:
    comp = session.scalar(select(Competition).where(Competition.name == "FIFA World Cup"))
    if comp is None:
        comp = Competition(name="FIFA World Cup", kind=CompetitionKind.WORLD_CUP)
        session.add(comp)
        session.flush()
    return comp


def _team(session, name: str) -> Team:
    t = session.scalar(select(Team).where(Team.name == name))
    if t is None:
        t = Team(name=name)
        session.add(t)
        session.flush()
    return t


# ---------------------------------------------------------------------------
# FC1 — Odds resueltas → Odds(OUTRIGHT_WINNER, outcome_team_id) inserted
# ---------------------------------------------------------------------------


def test_futures_capture_persists_outright_winner(db_session):
    """Brazil a 5.50 → Odds(OUTRIGHT_WINNER, outcome_team_id=brazil.id, decimal_odds=5.50)."""
    _wc_competition(db_session)
    brazil = _team(db_session, "Brazil")

    raw = _make_outright("Brazil", price=5.50)
    source = FakeOutrightSource([raw])
    result = OddsCapturePipeline(db_session, source).capture()

    assert result["inserted"] == 1

    row = db_session.scalar(
        select(Odds).where(
            Odds.market_type == MarketType.OUTRIGHT_WINNER,
            Odds.outcome_team_id == brazil.id,
        )
    )
    assert row is not None, "Debe insertar 1 fila OUTRIGHT_WINNER para Brazil"
    assert float(row.decimal_odds) == pytest.approx(5.50, abs=0.001)
    assert row.bookmaker == "pinnacle"
    assert row.match_id is None  # futures no tienen match


# ---------------------------------------------------------------------------
# FC2 — Nombre irresoluble → descartado (sin inserción, sin crash)
# ---------------------------------------------------------------------------


def test_futures_capture_discards_unresolvable_team(db_session):
    """'Brasil' sin alias → row descartado, inserted=0."""
    _wc_competition(db_session)
    # No creamos Team/alias para "Brasil"

    raw = _make_outright("Brasil", price=4.0)
    source = FakeOutrightSource([raw])
    result = OddsCapturePipeline(db_session, source).capture()

    assert result["inserted"] == 0

    row = db_session.scalar(select(Odds).where(Odds.market_type == MarketType.OUTRIGHT_WINNER))
    assert row is None, "Nombre irresoluble no debe insertar ninguna fila"


# ---------------------------------------------------------------------------
# FC3 — Mezcla: 1 resoluble + 1 irresoluble → solo 1 insertada
# ---------------------------------------------------------------------------


def test_futures_capture_mixed_resolved_unresolved(db_session):
    """Brazil resuelto + 'Xyzland' no → inserted=1."""
    _wc_competition(db_session)
    brazil = _team(db_session, "Brazil")

    raws = [
        _make_outright("Brazil", price=5.5, event_id="wc2026-winner"),
        _make_outright("Xyzland", price=100.0, event_id="wc2026-winner"),
    ]
    source = FakeOutrightSource(raws)
    result = OddsCapturePipeline(db_session, source).capture()

    assert result["inserted"] == 1

    rows = db_session.scalars(
        select(Odds).where(Odds.market_type == MarketType.OUTRIGHT_WINNER)
    ).all()
    assert len(rows) == 1
    assert rows[0].outcome_team_id == brazil.id


# ---------------------------------------------------------------------------
# FC4 — competition_id poblado en la fila insertada
# ---------------------------------------------------------------------------


def test_futures_capture_populates_competition_id(db_session):
    """Fila OUTRIGHT_WINNER debe tener competition_id = WC competition."""
    wc = _wc_competition(db_session)
    _team(db_session, "France")

    raw = _make_outright("France", price=7.0)
    source = FakeOutrightSource([raw])
    OddsCapturePipeline(db_session, source).capture()

    row = db_session.scalar(select(Odds).where(Odds.market_type == MarketType.OUTRIGHT_WINNER))
    assert row is not None
    assert row.competition_id == wc.id
