"""M3: uq_match_identity, ck_odds_target, uq_team_name_lower

Revision ID: 067ababdda5c
Revises: ce5f5f676dea
Create Date: 2026-06-09 23:19:33.985441

Prerrequisito: scripts/dedup.py debe haberse ejecutado sin errores ANTES de
aplicar esta migración. Los UNIQUE/CHECK fallarán si quedan duplicados.

Constraints creados:
- uq_match_identity: UNIQUE (match_date, home_team_id, away_team_id) en match.
  Sin competition_id (D1) — la clave de identidad ya asumida por el linker.
- ck_odds_target: CHECK NOT (match_id IS NOT NULL AND competition_id IS NOT NULL)
  en odds. Estados válidos: partido-linkeado, outright, pendiente (D3).
- uq_team_name_lower: índice funcional UNIQUE lower(name) en team.
  Evita equipos case-duplicados sin tocar la columna original (D7).
"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "067ababdda5c"
down_revision: str | None = "ce5f5f676dea"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # UNIQUE constraint en match: clave de identidad de partido (D1).
    # Ejecutar SOLO después de scripts/dedup.py (sin duplicados previos).
    op.create_unique_constraint(
        "uq_match_identity",
        "match",
        ["match_date", "home_team_id", "away_team_id"],
    )

    # CHECK en odds: match_id y competition_id no pueden estar ambos SET (D3).
    # Permite: solo match_id, solo competition_id, o ambos NULL (pendiente).
    op.create_check_constraint(
        "ck_odds_target",
        "odds",
        "NOT (match_id IS NOT NULL AND competition_id IS NOT NULL)",
    )

    # Índice funcional UNIQUE lower(name) en team (D7).
    # Impide insertar "Argentina" y "argentina" como dos equipos distintos.
    op.execute("CREATE UNIQUE INDEX uq_team_name_lower ON team (lower(name))")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_team_name_lower")
    op.drop_constraint("ck_odds_target", "odds", type_="check")
    op.drop_constraint("uq_match_identity", "match", type_="unique")
