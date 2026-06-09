"""M4: add OTHER (uppercase) to competition_kind enum

Revision ID: 633a20b62f7d
Revises: 067ababdda5c
Create Date: 2026-06-09 23:28:32.827185

Por qué existe esta migración:
  El enum PG competition_kind fue creado con labels UPPERCASE (WORLD_CUP,
  CONTINENTAL, etc.) porque SQLAlchemy serializó los member *names*, no los
  *values*. La migración M1 agregó el label lowercase 'other', que es INCORRECTO:
  el ORM envía 'OTHER' (el .name del miembro) y PG rechaza 'OTHER' porque solo
  existe 'other'.

  Esta migración (M4) agrega el label UPPERCASE 'OTHER' que el ORM necesita.
  El label 'other' de M1 queda como cruft inocuo: Postgres no permite eliminar
  labels de un enum sin reconstruir el tipo, pero 'other' nunca será enviado
  por el ORM, así que no causa problemas.
"""
from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '633a20b62f7d'
down_revision: str | None = '067ababdda5c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Agrega el label 'OTHER' (uppercase) al enum competition_kind.

    Usa autocommit_block porque PG no permite usar un valor recién agregado
    en la misma transacción (misma restricción que M1). IF NOT EXISTS hace
    la migración idempotente.
    """
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE competition_kind ADD VALUE IF NOT EXISTS 'OTHER'")


def downgrade() -> None:
    """PostgreSQL no soporta DROP VALUE en un enum nativo.

    Para revertir habría que reconstruir el tipo manualmente. El label
    'OTHER' es inofensivo si no hay filas que lo usen.
    """
    pass
