"""Tests para GET /api/v1/groups y GET /api/v1/groups/{name}.

Escenarios de spec group-standings:
  R3-S1: 12 grupos seeded → 200 con 12 objetos, cada uno con 4 equipos
  R3-S2: tabla vacía → 200 con [] (no 404)
  R4-S1: GET /groups/B → 200 con standings + fixtures
  R4-S2: GET /groups/M → 404 con detail="Group not found"
  R4-S3: GET /groups/b (minúscula) → 200 (normalizado)
"""

from datetime import date

from sqlalchemy import text

from app.models.competition import Competition
from app.models.enums import CompetitionKind, MatchStatus
from app.models.match import Match
from app.models.team import Team
from app.models.tournament import GroupTeam, TournamentGroup

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_minimal_group(session, letter: str = "B") -> TournamentGroup:
    """Crea un grupo con 4 equipos y 6 fixtures SCHEDULED."""
    comp = Competition(
        name=f"WC2026 Group {letter} Test",
        kind=CompetitionKind.WORLD_CUP,
    )
    session.add(comp)
    session.flush()

    teams = [Team(name=f"Team {letter}{i}") for i in range(1, 5)]
    session.add_all(teams)
    session.flush()

    group = TournamentGroup(
        competition_id=comp.id,
        season_year=2026,
        name=letter,
    )
    session.add(group)
    session.flush()

    for t in teams:
        session.add(GroupTeam(group_id=group.id, team_id=t.id))
    session.flush()

    # 6 fixtures (round-robin)
    pairs = [(teams[i], teams[j]) for i in range(4) for j in range(i + 1, 4)]
    for h, a in pairs:
        m = Match(
            competition_id=comp.id,
            match_date=date(2026, 6, 20),
            home_team_id=h.id,
            away_team_id=a.id,
            status=MatchStatus.SCHEDULED,
            group_id=group.id,
        )
        session.add(m)
    session.flush()

    return group


# ---------------------------------------------------------------------------
# R3-S2: tabla vacía → 200 + []
# ---------------------------------------------------------------------------


def test_groups_empty_table_returns_200(client, db_session):
    """R3-S2: sin grupos seeded → 200 con lista vacía, no 404."""
    # Limpiar grupos existentes dentro del SAVEPOINT (se hace rollback al finalizar)
    db_session.execute(text("DELETE FROM group_team"))
    db_session.execute(text("UPDATE match SET group_id = NULL WHERE group_id IS NOT NULL"))
    db_session.execute(text("DELETE FROM tournament_group"))
    db_session.flush()

    resp = client.get("/api/v1/groups")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# R3-S1: al menos 1 grupo seeded → 200 con estructura
# ---------------------------------------------------------------------------


def test_groups_returns_group_objects(client, db_session):
    """R3-S1 (parcial): grupo B seeded → aparece en la respuesta con 4 equipos."""
    _seed_minimal_group(db_session, "B")

    resp = client.get("/api/v1/groups")

    assert resp.status_code == 200
    groups = resp.json()
    assert len(groups) >= 1
    b = next(g for g in groups if g["name"] == "B")
    assert len(b["teams"]) == 4
    # Standings deben estar presentes (0 partidos FINISHED → todos en 0)
    assert len(b["standings"]) == 4
    assert all(row["pts"] == 0 for row in b["standings"])


# ---------------------------------------------------------------------------
# R4-S1: GET /groups/B → 200 con fixtures
# ---------------------------------------------------------------------------


def test_group_detail_found(client, db_session):
    """R4-S1: grupo B con fixtures → 200 con standings + fixtures."""
    _seed_minimal_group(db_session, "B")

    resp = client.get("/api/v1/groups/B")

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "B"
    assert len(body["teams"]) == 4
    assert len(body["standings"]) == 4
    assert "fixtures" in body
    assert len(body["fixtures"]) == 6


# ---------------------------------------------------------------------------
# R4-S3: minúscula normalizada
# ---------------------------------------------------------------------------


def test_group_detail_lowercase_normalized(client, db_session):
    """R4-S3: /groups/b → mismo resultado que /groups/B."""
    _seed_minimal_group(db_session, "A")

    resp_upper = client.get("/api/v1/groups/A")
    resp_lower = client.get("/api/v1/groups/a")

    assert resp_upper.status_code == 200
    assert resp_lower.status_code == 200
    assert resp_lower.json()["name"] == resp_upper.json()["name"]


# ---------------------------------------------------------------------------
# R4-S2: grupo no existe → 404
# ---------------------------------------------------------------------------


def test_group_detail_not_found(client, db_session):
    """R4-S2: grupo M no existe → 404 con detail='Group not found'."""
    resp = client.get("/api/v1/groups/M")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Group not found"
