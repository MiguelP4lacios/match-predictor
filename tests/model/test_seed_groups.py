"""Tests de integración TDD para scripts/seed_groups.py.

Escenarios:
  (a) Grafo válido 12×4 (WC2026 real): ejecuta sin error, inserta 12 grupos + 48 miembros.
  (b) Grafo roto (componente < 4): AssertionError ANTES de escribir ninguna fila.
  (c) Doble ejecución: idempotente, sin duplicados ni IntegrityError.
"""

import datetime

import pytest
from sqlalchemy import func, select

from app.models import Competition, GroupTeam, Match, Team, TournamentGroup
from app.models.enums import CompetitionKind, MatchStatus

# ID real de "FIFA World Cup" en la BD (seed histórico martj42).
WC_COMPETITION_ID = 23
WC_SEASON_YEAR = 2026


# ---------------------------------------------------------------------------
# (a) Grafo válido 12×4 — ejecuta sin error e inserta filas correctas
# ---------------------------------------------------------------------------


def test_seed_valid_graph_inserts_groups(db_session):
    """(a) seed_groups() con 72 fixtures WC2026 → 12 TournamentGroup + 48 GroupTeam."""
    from scripts.seed_groups import seed_groups

    seed_groups(db_session, competition_id=WC_COMPETITION_ID, season_year=WC_SEASON_YEAR)

    n_groups = db_session.scalar(
        select(func.count(TournamentGroup.id)).where(
            TournamentGroup.competition_id == WC_COMPETITION_ID,
            TournamentGroup.season_year == WC_SEASON_YEAR,
        )
    )
    n_members = db_session.scalar(
        select(func.count(GroupTeam.id))
        .join(TournamentGroup)
        .where(
            TournamentGroup.competition_id == WC_COMPETITION_ID,
            TournamentGroup.season_year == WC_SEASON_YEAR,
        )
    )

    assert n_groups == 12, f"Se esperaban 12 grupos, se obtuvieron {n_groups}"
    assert n_members == 48, f"Se esperaban 48 miembros, se obtuvieron {n_members}"


# ---------------------------------------------------------------------------
# (b) Grafo roto → AssertionError antes de escribir
# ---------------------------------------------------------------------------


def test_seed_broken_graph_raises_before_write(db_session):
    """(b) Grafo con sólo 3 equipos → AssertionError; BD sin cambios."""
    from scripts.seed_groups import seed_groups

    # Crear una competición de prueba con un grafo roto (3 equipos, 3 partidos)
    broken_comp = Competition(name="TEST_BROKEN_WC_SEED", kind=CompetitionKind.WORLD_CUP)
    db_session.add(broken_comp)
    db_session.flush()

    teams = [Team(name=f"BrokenTeam{i}") for i in range(3)]
    db_session.add_all(teams)
    db_session.flush()

    # 3 partidos entre 3 equipos → 1 componente de 3 (no 12×4)
    matches = [
        Match(
            competition_id=broken_comp.id,
            match_date=datetime.date(2026, 6, 20),
            home_team_id=teams[0].id,
            away_team_id=teams[1].id,
            neutral_site=False,
            status=MatchStatus.SCHEDULED,
            went_to_extra_time=False,
            went_to_penalties=False,
        ),
        Match(
            competition_id=broken_comp.id,
            match_date=datetime.date(2026, 6, 21),
            home_team_id=teams[1].id,
            away_team_id=teams[2].id,
            neutral_site=False,
            status=MatchStatus.SCHEDULED,
            went_to_extra_time=False,
            went_to_penalties=False,
        ),
        Match(
            competition_id=broken_comp.id,
            match_date=datetime.date(2026, 6, 22),
            home_team_id=teams[0].id,
            away_team_id=teams[2].id,
            neutral_site=False,
            status=MatchStatus.SCHEDULED,
            went_to_extra_time=False,
            went_to_penalties=False,
        ),
    ]
    db_session.add_all(matches)
    db_session.flush()

    count_before = db_session.scalar(
        select(func.count(TournamentGroup.id)).where(
            TournamentGroup.competition_id == broken_comp.id
        )
    )
    assert count_before == 0  # Ningún grupo antes del intento

    with pytest.raises(AssertionError):
        seed_groups(db_session, competition_id=broken_comp.id, season_year=WC_SEASON_YEAR)

    # Después del error: sin grupos ni miembros escritos
    count_after = db_session.scalar(
        select(func.count(TournamentGroup.id)).where(
            TournamentGroup.competition_id == broken_comp.id
        )
    )
    assert count_after == 0, "La BD NO debe tener filas tras un AssertionError"


# ---------------------------------------------------------------------------
# (c) Doble ejecución — idempotente, sin duplicados
# ---------------------------------------------------------------------------


def test_seed_idempotent_on_double_run(db_session):
    """(c) Segunda ejecución no duplica filas ni lanza IntegrityError."""
    from scripts.seed_groups import seed_groups

    seed_groups(db_session, competition_id=WC_COMPETITION_ID, season_year=WC_SEASON_YEAR)

    n_groups_first = db_session.scalar(
        select(func.count(TournamentGroup.id)).where(
            TournamentGroup.competition_id == WC_COMPETITION_ID,
            TournamentGroup.season_year == WC_SEASON_YEAR,
        )
    )

    # Segunda ejecución: no debe lanzar ni duplicar
    seed_groups(db_session, competition_id=WC_COMPETITION_ID, season_year=WC_SEASON_YEAR)

    n_groups_second = db_session.scalar(
        select(func.count(TournamentGroup.id)).where(
            TournamentGroup.competition_id == WC_COMPETITION_ID,
            TournamentGroup.season_year == WC_SEASON_YEAR,
        )
    )

    assert n_groups_first == n_groups_second == 12
