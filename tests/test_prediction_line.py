"""ops-resilience R4.S2 — Prediction guarda la línea de Over/Under.

Sin `line`, el join predicción↔cuota de O/U es imposible: P(Over 2.5) comparada
contra una cuota de Over 3.5 produce un edge falso.
"""

from decimal import Decimal

from sqlalchemy import select

from app.models import ModelVersion, Prediction
from app.models.enums import MarketType


def test_prediction_round_trip_con_line(db_session):
    version = ModelVersion(name="test-line-v1", params_json={})
    db_session.add(version)
    db_session.flush()

    db_session.add(
        Prediction(
            model_version_id=version.id,
            market_type=MarketType.OVER_UNDER,
            outcome_code="OVER",
            probability=0.6123,
            line=2.5,
        )
    )
    db_session.flush()

    saved = db_session.scalar(
        select(Prediction).where(Prediction.model_version_id == version.id)
    )
    assert Decimal(saved.line) == Decimal("2.5")


def test_prediction_1x2_sin_line(db_session):
    version = ModelVersion(name="test-line-v2", params_json={})
    db_session.add(version)
    db_session.flush()

    db_session.add(
        Prediction(
            model_version_id=version.id,
            market_type=MarketType.MATCH_1X2,
            outcome_code="HOME",
            probability=0.4500,
        )
    )
    db_session.flush()

    saved = db_session.scalar(
        select(Prediction).where(Prediction.model_version_id == version.id)
    )
    assert saved.line is None
