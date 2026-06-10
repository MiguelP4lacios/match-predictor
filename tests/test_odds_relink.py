"""Tests para relink_orphan_odds (odds-capture R1 S3, R2 S3).

Spec: odds-capture R1 S3 (relink linkea filas NULL), R2 S3 (disambiguación por
commence_time cuando dos fixtures comparten el mismo par de equipos).
TDD RED: fallan hasta que relink_orphan_odds exista en odds_pipeline.

Estrategia de relink:
  Para cada source_event_id con match_id NULL → extrae par de equipos de los
  outcome HOME/AWAY (outcome_team_id); busca el match SCHEDULED con ese par
  cuyo kickoff_at esté dentro de ±1 día del commence_time; si hay exactamente 1,
  actualiza match_id; si 0 o >1, omite (log warning).
"""

import datetime

from app.ingestion.odds_pipeline import relink_orphan_odds  # no existe aún
from app.models import Competition, Match, Odds, Team
from app.models.enums import CompetitionKind, MarketType, MatchStatus


def _orphan_h2h(
    source_event_id: str,
    outcome_code: str,
    outcome_team_id: int | None,
    commence_time: datetime.datetime,
) -> Odds:
    """Helper para crear una fila de odds orphan (match_id=NULL)."""
    return Odds(
        match_id=None,
        source_event_id=source_event_id,
        commence_time=commence_time,
        market_type=MarketType.MATCH_1X2,
        outcome_code=outcome_code,
        outcome_team_id=outcome_team_id,
        bookmaker="pinnacle",
        decimal_odds=2.0,
        captured_at=datetime.datetime(2026, 6, 10, 12, 0),
        is_closing=False,
    )


# ---------------------------------------------------------------------------
# S3 (R1): relink_odds links previously unlinked odds
# ---------------------------------------------------------------------------


def test_relink_orphan_odds_links_null_rows(db_session):
    """relink_orphan_odds conecta orphans con match_id=NULL al fixture correcto.

    Se crean filas HOME + AWAY del mismo source_event_id para que el relink
    pueda reconstruir el par de equipos.
    """
    home = Team(name="SpainRelink")
    away = Team(name="PortugalRelink")
    db_session.add_all([home, away])
    db_session.flush()

    comp = Competition(name="FIFA World Cup Relink", kind=CompetitionKind.WORLD_CUP)
    db_session.add(comp)
    db_session.flush()

    match_dt = datetime.datetime(2026, 6, 15, 18, 0)
    match = Match(
        competition_id=comp.id,
        match_date=match_dt.date(),
        home_team_id=home.id,
        away_team_id=away.id,
        neutral_site=True,
        status=MatchStatus.SCHEDULED,
        kickoff_at=match_dt,
    )
    db_session.add(match)
    db_session.flush()

    # Odds orphan: par HOME + AWAY con el mismo source_event_id
    ev_id = "evt-orphan-sp-pt"
    orphan_home = _orphan_h2h(ev_id, "HOME", home.id, match_dt)
    orphan_away = _orphan_h2h(ev_id, "AWAY", away.id, match_dt)
    orphan_draw = _orphan_h2h(ev_id, "DRAW", None, match_dt)
    db_session.add_all([orphan_home, orphan_away, orphan_draw])
    db_session.flush()

    relink_orphan_odds(db_session)

    for row in [orphan_home, orphan_away, orphan_draw]:
        db_session.refresh(row)

    assert orphan_home.match_id == match.id
    assert orphan_away.match_id == match.id
    assert orphan_draw.match_id == match.id


def test_relink_leaves_unmatched_rows_null(db_session):
    """Odds orphan sin fixture correspondiente permanecen con match_id=NULL."""
    # Sin crear ningún fixture en la BD para este par
    orphan = Odds(
        match_id=None,
        source_event_id="evt-no-match",
        commence_time=datetime.datetime(2099, 1, 1, 18, 0),  # fecha sin fixture
        market_type=MarketType.MATCH_1X2,
        outcome_code="HOME",
        outcome_team_id=None,
        bookmaker="bet365",
        decimal_odds=1.9,
        captured_at=datetime.datetime(2026, 6, 10),
        is_closing=False,
    )
    db_session.add(orphan)
    db_session.flush()

    relink_orphan_odds(db_session)

    db_session.refresh(orphan)
    assert orphan.match_id is None  # sin fixture → sigue NULL


# ---------------------------------------------------------------------------
# S3 (R2): Disambiguation by commence_time when two fixtures share same pair
# ---------------------------------------------------------------------------


def test_relink_disambiguates_by_commence_time(db_session):
    """Dos fixtures del mismo par → relink elige el más cercano por commence_time.

    match_14 y match_15 comparten par (home, away).
    orphan con commence_time = dt_15 → debe linkearse a match_15.
    """
    home = Team(name="TeamADisamb")
    away = Team(name="TeamBDisamb")
    db_session.add_all([home, away])
    db_session.flush()

    comp = Competition(name="FIFA World Cup Disamb", kind=CompetitionKind.WORLD_CUP)
    db_session.add(comp)
    db_session.flush()

    dt_14 = datetime.datetime(2026, 6, 14, 18, 0)
    dt_15 = datetime.datetime(2026, 6, 15, 18, 0)

    match_14 = Match(
        competition_id=comp.id,
        match_date=dt_14.date(),
        home_team_id=home.id,
        away_team_id=away.id,
        neutral_site=True,
        status=MatchStatus.SCHEDULED,
        kickoff_at=dt_14,
    )
    match_15 = Match(
        competition_id=comp.id,
        match_date=dt_15.date(),
        home_team_id=home.id,
        away_team_id=away.id,
        neutral_site=True,
        status=MatchStatus.SCHEDULED,
        kickoff_at=dt_15,
    )
    db_session.add_all([match_14, match_15])
    db_session.flush()

    # Orphan event: commence_time = dt_15, debe mapear a match_15
    ev_id = "evt-disamb-15"
    orphan_home = _orphan_h2h(ev_id, "HOME", home.id, dt_15)
    orphan_away = _orphan_h2h(ev_id, "AWAY", away.id, dt_15)
    db_session.add_all([orphan_home, orphan_away])
    db_session.flush()

    relink_orphan_odds(db_session)

    db_session.refresh(orphan_home)
    db_session.refresh(orphan_away)
    assert orphan_home.match_id == match_15.id  # NO el match_14
    assert orphan_away.match_id == match_15.id
