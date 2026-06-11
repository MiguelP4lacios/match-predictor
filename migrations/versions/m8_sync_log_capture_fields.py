"""M8: sync_log — agregar rows_inserted + credits_remaining

Revision ID: m8capfields
Revises: m7parlay
Create Date: 2026-06-11 00:00:00.000000

Cambios:
- ADD sync_log.rows_inserted Integer nullable
- ADD sync_log.credits_remaining Integer nullable

Aditiva y reversible. Sin backfill — filas históricas quedan con NULL.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "m8capfields"
down_revision: str | None = "m7parlay"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sync_log", sa.Column("rows_inserted", sa.Integer(), nullable=True))
    op.add_column("sync_log", sa.Column("credits_remaining", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("sync_log", "credits_remaining")
    op.drop_column("sync_log", "rows_inserted")
