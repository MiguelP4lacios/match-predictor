"""M7: parlay — bet_leg table + bet_log.bet_kind + relax ck_bet_resolvable

Revision ID: m7parlay
Revises: m6betlogreal
Create Date: 2026-06-10 00:00:00.000000

Cambios:
- CREATE TYPE bet_kind AS ENUM ('single', 'parlay')
- ADD bet_log.bet_kind (DEFAULT 'single', server_default 'single') — existing rows → single
- DROP CHECK ck_bet_resolvable (old)
- ADD CHECK ck_bet_resolvable (new):
    (bet_kind = 'parlay') OR (value_signal_id IS NOT NULL) OR (match_id IS NOT NULL AND outcome_code IS NOT NULL)
  Un parlay no tiene match_id/outcome/signal en la fila principal; sus legs viven en bet_leg.
- CREATE TABLE bet_leg (id, bet_log_id FK→bet_log CASCADE, match_id FK→match CASCADE,
    outcome_code, odds_taken Numeric(8,3), settled_result varchar nullable, leg_status varchar nullable)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m7parlay"
down_revision: str | None = "m6betlogreal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# PG enum name shared with the SQLAlchemy type defined in app/models/types.py
_BET_KIND_ENUM = sa.Enum("SINGLE", "PARLAY", name="bet_kind")


def upgrade() -> None:
    # 1. Create the bet_kind PG enum type
    _BET_KIND_ENUM.create(op.get_bind(), checkfirst=True)

    # 2. Add bet_log.bet_kind column with server default 'single'
    #    Existing rows (all SINGLE bets) get 'single' automatically.
    op.add_column(
        "bet_log",
        sa.Column(
            "bet_kind",
            sa.Enum("SINGLE", "PARLAY", name="bet_kind", create_type=False),
            nullable=False,
            server_default="SINGLE",
        ),
    )

    # 3. Drop old restrictive CHECK
    op.drop_constraint("ck_bet_resolvable", "bet_log", type_="check")

    # 4. Add relaxed CHECK — parlays bypass the match/signal requirement
    op.create_check_constraint(
        "ck_bet_resolvable",
        "bet_log",
        "(bet_kind = 'PARLAY') OR (value_signal_id IS NOT NULL) OR "
        "(match_id IS NOT NULL AND outcome_code IS NOT NULL)",
    )

    # 5. Create bet_leg table
    op.create_table(
        "bet_leg",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "bet_log_id",
            sa.BigInteger(),
            sa.ForeignKey("bet_log.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "match_id",
            sa.BigInteger(),
            sa.ForeignKey("match.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("outcome_code", sa.String(20), nullable=False),
        sa.Column("odds_taken", sa.Numeric(8, 3), nullable=False),
        sa.Column("settled_result", sa.String(20), nullable=True),
        sa.Column("leg_status", sa.String(20), nullable=True),
    )
    op.create_index("ix_bet_leg_bet_log_id", "bet_leg", ["bet_log_id"])


def downgrade() -> None:
    # 5. Drop bet_leg
    op.drop_index("ix_bet_leg_bet_log_id", table_name="bet_leg")
    op.drop_table("bet_leg")

    # 4. Drop relaxed CHECK
    op.drop_constraint("ck_bet_resolvable", "bet_log", type_="check")

    # 3. Restore old restrictive CHECK
    op.create_check_constraint(
        "ck_bet_resolvable",
        "bet_log",
        "(value_signal_id IS NOT NULL) OR (match_id IS NOT NULL AND outcome_code IS NOT NULL)",
    )

    # 2. Remove bet_kind column
    op.drop_column("bet_log", "bet_kind")

    # 1. Drop bet_kind PG enum type
    _BET_KIND_ENUM.drop(op.get_bind(), checkfirst=True)
