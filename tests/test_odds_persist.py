"""Tests para persistencia siempre de odds (odds-capture R1).

Spec: odds-capture R1, escenarios S1-S2.
TDD RED: fallan hasta que OddsCapturePipeline.capture() persista con match_id NULL.

NUNCA se llama a The Odds API: se usa un OddsSource falso.
Los equipos se crean en la BD del test (rollback al terminar).
"""

import datetime
from collections.abc import Iterator

from sqlalchemy import select

from app.ingestion.dto import RawOdds
from app.ingestion.odds_pipeline import OddsCapturePipeline
from app.models import Competition, Match, Odds, Team
from app.models.enums import CompetitionKind, DataSource, MatchStatus

# ---------------------------------------------------------------------------
# Fake OddsSource
# ---------------------------------------------------------------------------


class FakeOddsSource:
    source = DataSource.ODDS_API

    def __init__(self, odds: list[RawOdds]) -> None:
        self._odds = odds

    def fetch_odds(self) -> Iterator[RawOdds]:
        yield from self._odds


def _make_raw_h2h(
    home_team: str,
    away_team: str,
    outcome_name: str,
    price: float = 2.0,
    event_id: str = "evt-001",
    commence_time: datetime.datetime | None = None,
) -> RawOdds:
    return RawOdds(
        source=DataSource.ODDS_API,
        event_id=event_id,
        commence_time=commence_time or datetime.datetime(2026, 6, 14, 18, 0),
        home_team=home_team,
        away_team=away_team,
        bookmaker="pinnacle",
        market_key="h2h",
        outcome_name=outcome_name,
        price=price,
        line=None,
        captured_at=datetime.datetime(2026, 6, 10, 12, 0),
    )


# ---------------------------------------------------------------------------
# S1: Odds without fixture → match_id IS NULL, unlinked_events > 0
# ---------------------------------------------------------------------------


def test_odds_without_fixture_persisted_with_null_match_id(db_session):
    """Teams existen pero NO hay fixture → INSERT con match_id=NULL, unlinked_events>0."""
    # Crear teams que el resolver pueda encontrar
    home = Team(name="TEST_NoMatchHome")
    away = Team(name="TEST_NoMatchAway")
    db_session.add_all([home, away])
    db_session.flush()

    # SIN fixture en la BD para este par
    raw = _make_raw_h2h(
        "TEST_NoMatchHome",
        "TEST_NoMatchAway",
        outcome_name="TEST_NoMatchHome",  # el home team
        event_id="evt-no-match",
    )
    source = FakeOddsSource([raw])
    pipeline = OddsCapturePipeline(db_session, source)

    result = pipeline.capture()

    assert result["unlinked_events"] > 0
    odds_row = db_session.scalar(select(Odds).where(Odds.source_event_id == "evt-no-match"))
    assert odds_row is not None
    assert odds_row.match_id is None
    assert odds_row.source_event_id == "evt-no-match"
    assert odds_row.commence_time is not None


# ---------------------------------------------------------------------------
# S2: Odds with fixture → match_id NOT NULL (linked during capture)
# ---------------------------------------------------------------------------


def test_odds_with_fixture_gets_match_id(db_session):
    """Teams y fixture existen → match_id seteado en INSERT durante capture()."""
    home = Team(name="TEST_WCHome")
    away = Team(name="TEST_WCAway")
    db_session.add_all([home, away])
    db_session.flush()

    # Usar "FIFA World Cup" EXACTO para que _build_match_index lo encuentre
    wc_comp = db_session.scalar(select(Competition).where(Competition.name == "FIFA World Cup"))
    if wc_comp is None:
        wc_comp = Competition(name="FIFA World Cup", kind=CompetitionKind.WORLD_CUP)
        db_session.add(wc_comp)
        db_session.flush()

    match_dt = datetime.datetime(2026, 6, 14, 18, 0)
    match = Match(
        competition_id=wc_comp.id,
        match_date=match_dt.date(),
        home_team_id=home.id,
        away_team_id=away.id,
        neutral_site=True,
        status=MatchStatus.SCHEDULED,
        kickoff_at=match_dt,
    )
    db_session.add(match)
    db_session.flush()

    # Odds para ese mismo par
    raw = _make_raw_h2h(
        "TEST_WCHome",
        "TEST_WCAway",
        outcome_name="TEST_WCHome",
        event_id="evt-wc-home",
        commence_time=match_dt,
    )
    source = FakeOddsSource([raw])
    pipeline = OddsCapturePipeline(db_session, source)

    result = pipeline.capture()

    assert result["unlinked_events"] == 0
    odds_row = db_session.scalar(select(Odds).where(Odds.source_event_id == "evt-wc-home"))
    assert odds_row is not None
    assert odds_row.match_id == match.id


def test_capture_commitea_la_transaccion(db_session, monkeypatch):
    """REGRESIÓN (bug de producción 2026-06-10): capture() debe COMMITEAR.

    El rewrite de F3 perdió el commit: jobs.py cierra la sesión sin commitear
    → rollback silencioso. 2 créditos gastados, 5.339 filas perdidas en la VPS.
    El fixture SAVEPOINT no lo caza consultando: se espía el commit explícito.
    """
    source = FakeOddsSource([])  # sin odds: el commit debe ocurrir igual

    commits = {"n": 0}
    original_commit = db_session.commit

    def spy_commit():
        commits["n"] += 1
        original_commit()

    monkeypatch.setattr(db_session, "commit", spy_commit)

    OddsCapturePipeline(db_session, source).capture()

    assert commits["n"] >= 1, "capture() no commiteó — rollback silencioso al cerrar la sesión"
