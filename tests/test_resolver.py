"""Tests para TeamResolver case-insensitive lookup (ops-resilience R3 S3).

Spec: ops-resilience R3 S3.
TDD RED: falla hasta que _get_or_create_team use lower(team.name) = lower(:norm).

Usa equipos que YA existen en la BD de producción (Argentina, France, Brazil).
No crea teams nuevos para evitar conflictos de unique constraint.
"""

import pytest
from sqlalchemy import select

from app.ingestion.resolver import TeamResolver
from app.models import Team
from app.models.enums import DataSource


def _get_team_or_skip(session, name: str) -> "Team":
    """Devuelve el team o skipea el test si no existe en la BD."""
    team = session.scalar(select(Team).where(Team.name == name))
    if team is None:
        pytest.skip(f"Team '{name}' no existe en la BD — ejecutar ingesta primero")
    return team


def test_resolve_case_insensitive_returns_existing_team(db_session):
    """'argentina' (minúsculas) resuelve al Team('Argentina') existente, sin duplicar."""
    canonical = _get_team_or_skip(db_session, "Argentina")

    resolver = TeamResolver(db_session)
    result = resolver.resolve(DataSource.MARTJ42, "argentina", create_missing=False)

    assert result is not None
    assert result.id == canonical.id
    assert result.name == "Argentina"

    # No se duplicó: solo 1 team con nombre 'Argentina' (case-insensitive)
    db_session.scalars(
        select(Team).where(select(Team).where(Team.name.ilike("argentina")).exists())
    )
    count = db_session.scalar(
        select(__import__("sqlalchemy", fromlist=["func"]).func.count(Team.id)).where(
            Team.name.ilike("argentina")
        )
    )
    assert count == 1


def test_resolve_uppercase_variation_returns_existing_team(db_session):
    """'FRANCE' resuelve al Team('France') existente sin crear duplicado."""
    canonical = _get_team_or_skip(db_session, "France")

    resolver = TeamResolver(db_session)
    result = resolver.resolve(DataSource.MARTJ42, "FRANCE", create_missing=False)

    assert result is not None
    assert result.id == canonical.id
    assert result.name == "France"


def test_resolve_no_duplicate_when_team_exists(db_session):
    """Resolver con create_missing=True no duplica si ya existe con distinta capitalización."""
    from sqlalchemy import func

    canonical = _get_team_or_skip(db_session, "Brazil")
    original_count = db_session.scalar(
        select(func.count(Team.id)).where(func.lower(Team.name) == "brazil")
    )

    resolver = TeamResolver(db_session)
    result = resolver.resolve(DataSource.MARTJ42, "brazil", create_missing=True)

    # Devuelve el canónico, no crea uno nuevo
    assert result is not None
    assert result.id == canonical.id

    final_count = db_session.scalar(
        select(func.count(Team.id)).where(func.lower(Team.name) == "brazil")
    )
    assert final_count == original_count  # sin duplicados
