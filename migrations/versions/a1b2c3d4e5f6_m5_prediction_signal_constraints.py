"""M5: prediction low_confidence + uq_prediction_identity + uq_signal_identity

Revision ID: a1b2c3d4e5f6
Revises: 633a20b62f7d
Create Date: 2026-06-09 00:00:00.000000

Cambios:
- prediction.low_confidence BOOLEAN NOT NULL DEFAULT false
  Marca predicciones sin historial de rating previo (default 1500).
- uq_prediction_identity (model_version_id, match_id, market_type, outcome_code)
  Upsert idempotente: re-ejecutar predict_1x2 no duplica filas.
- uq_signal_identity (prediction_id, odds_id) en value_signal
  Upsert idempotente: re-ejecutar signals no duplica señales.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "633a20b62f7d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Columna low_confidence en prediction.
    op.add_column(
        "prediction",
        sa.Column(
            "low_confidence",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # UNIQUE para idempotencia de predict_1x2.
    op.create_unique_constraint(
        "uq_prediction_identity",
        "prediction",
        ["model_version_id", "match_id", "market_type", "outcome_code"],
    )

    # UNIQUE para idempotencia de signals.
    op.create_unique_constraint(
        "uq_signal_identity",
        "value_signal",
        ["prediction_id", "odds_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_signal_identity", "value_signal", type_="unique")
    op.drop_constraint("uq_prediction_identity", "prediction", type_="unique")
    op.drop_column("prediction", "low_confidence")
