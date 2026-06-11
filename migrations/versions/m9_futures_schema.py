"""M9: futures schema — outcome_team_id FK + REACH_* enum values + uq_prediction_identity update

Revision ID: m9futures
Revises: m8capfields
Create Date: 2026-06-11 00:00:00.000000

Cambios:
  1. ALTER TYPE market_type ADD VALUE IF NOT EXISTS 'REACH_SEMI_FINAL' (autocommit)
  2. ALTER TYPE market_type ADD VALUE IF NOT EXISTS 'REACH_FINAL' (autocommit)
  3. ADD prediction.outcome_team_id INTEGER nullable FK → team.id
  4. DROP uq_prediction_identity (columnas antiguas sin competition_id ni outcome_team_id)
  5. CREATE uq_prediction_identity (model_version_id, match_id, competition_id,
                                    market_type, outcome_code, outcome_team_id)

Nota: los valores de enum añadidos en PG no se pueden eliminar en downgrade.
El downgrade documenta este comportamiento y solo revierte columna + constraint.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "m9futures"
down_revision: str | None = "m8capfields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1-2. Agregar valores al enum market_type (requiere autocommit en PG)
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE market_type ADD VALUE IF NOT EXISTS 'REACH_SEMI_FINAL'")
        op.execute("ALTER TYPE market_type ADD VALUE IF NOT EXISTS 'REACH_FINAL'")

    # 3. Agregar columna outcome_team_id (nullable FK → team.id)
    op.add_column(
        "prediction",
        sa.Column(
            "outcome_team_id",
            sa.Integer(),
            sa.ForeignKey("team.id"),
            nullable=True,
        ),
    )

    # 4. Eliminar el constraint anterior (sin competition_id ni outcome_team_id)
    op.drop_constraint("uq_prediction_identity", "prediction", type_="unique")

    # 5. Recrear con las columnas completas (NULLs son distintos en PG → filas 1X2
    #    con outcome_team_id=NULL siguen siendo únicas entre sí)
    op.create_unique_constraint(
        "uq_prediction_identity",
        "prediction",
        [
            "model_version_id",
            "match_id",
            "competition_id",
            "market_type",
            "outcome_code",
            "outcome_team_id",
        ],
    )


def downgrade() -> None:
    # Nota: los valores 'REACH_SEMI_FINAL' y 'REACH_FINAL' no se pueden eliminar
    # del enum market_type en PostgreSQL. Se documentan como "conocidos tras downgrade".

    # 5→4. Eliminar nuevo constraint y restaurar el anterior
    op.drop_constraint("uq_prediction_identity", "prediction", type_="unique")
    op.create_unique_constraint(
        "uq_prediction_identity",
        "prediction",
        ["model_version_id", "match_id", "market_type", "outcome_code"],
    )

    # 3. Eliminar columna outcome_team_id
    op.drop_column("prediction", "outcome_team_id")
