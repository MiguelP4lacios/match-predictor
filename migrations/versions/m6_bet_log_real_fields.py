"""M6: bet_log — campos de apuesta REAL + CHECK ck_bet_resolvable

Revision ID: m6betlogreal
Revises: a1b2c3d4e5f6
Create Date: 2026-06-10 00:00:00.000000

Cambios:
- value_signal_id: DROP NOT NULL (ahora nullable).
- ADD match_id FK(match, nullable) — ruta directa para apuestas REAL.
- ADD outcome_code VARCHAR(20) nullable — resultado apostado en modo REAL.
- ADD settled_at TIMESTAMP nullable — momento de liquidación.
- ADD note VARCHAR(500) nullable — nota libre del apostador.
- ADD CHECK ck_bet_resolvable:
    (value_signal_id IS NOT NULL) OR (match_id IS NOT NULL AND outcome_code IS NOT NULL)
  Toda apuesta debe poder liquidarse por uno de los dos caminos.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m6betlogreal"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. value_signal_id: DROP NOT NULL constraint
    op.alter_column("bet_log", "value_signal_id", nullable=True)

    # 2. ADD match_id FK → match (nullable)
    op.add_column(
        "bet_log",
        sa.Column("match_id", sa.BigInteger(), sa.ForeignKey("match.id"), nullable=True),
    )
    op.create_index("ix_bet_log_match_id", "bet_log", ["match_id"])

    # 3. ADD outcome_code VARCHAR(20) nullable
    op.add_column(
        "bet_log",
        sa.Column("outcome_code", sa.String(20), nullable=True),
    )

    # 4. ADD settled_at TIMESTAMP nullable
    op.add_column(
        "bet_log",
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 5. ADD note VARCHAR(500) nullable
    op.add_column(
        "bet_log",
        sa.Column("note", sa.String(500), nullable=True),
    )

    # 6. ADD CHECK ck_bet_resolvable
    op.create_check_constraint(
        "ck_bet_resolvable",
        "bet_log",
        "(value_signal_id IS NOT NULL) OR (match_id IS NOT NULL AND outcome_code IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_bet_resolvable", "bet_log", type_="check")
    op.drop_index("ix_bet_log_match_id", table_name="bet_log")
    op.drop_column("bet_log", "note")
    op.drop_column("bet_log", "settled_at")
    op.drop_column("bet_log", "outcome_code")
    op.drop_column("bet_log", "match_id")
    op.alter_column("bet_log", "value_signal_id", nullable=False)
