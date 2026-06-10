"""M1: add OTHER to competition_kind enum

Revision ID: 04aaa08229f6
Revises: 6a5cf736fa47
Create Date: 2026-06-09 23:16:44.740335

"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "04aaa08229f6"
down_revision: str | None = "6a5cf736fa47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Agrega valor 'other' al enum competition_kind.

    PostgreSQL no permite usar un valor de enum recién agregado en la misma
    transacción (D2). Se usa autocommit_block para aislar el ALTER TYPE.
    IF NOT EXISTS hace la migración idempotente.
    """
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE competition_kind ADD VALUE IF NOT EXISTS 'other'")


def downgrade() -> None:
    """PostgreSQL no soporta DROP VALUE en un enum nativo.

    Para revertir hay que recrear el tipo sin 'other'. Como aún no hay datos
    con ese valor, se documenta la restricción pero no se implementa el
    downgrade automático (manual si es necesario).
    """
    pass
