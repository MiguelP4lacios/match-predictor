"""Tests para ModelVersion immutability (ops-resilience R4 S1).

Spec: ops-resilience R4 S1.
TDD RED: falla hasta que _record_version haga INSERT elo-v2 en vez de UPDATE elo-v1.

Usa DB real con fixture db_session.
"""

from sqlalchemy import func, select

from app.model.elo_engine import EloEngine
from app.models import ModelVersion


def _record_version_via_engine(session, initial=1500.0, home_adv=100.0):
    """Llama a _record_version() directamente (sin compute() para no necesitar datos)."""
    engine = EloEngine(session, initial=initial, home_advantage=home_adv)
    engine._record_version()
    session.flush()


# ---------------------------------------------------------------------------
# S1: Re-running EloEngine creates new version row, not overwrite
# ---------------------------------------------------------------------------

def test_first_record_creates_elo_v1(db_session):
    """Primera llamada a _record_version → INSERT con name='elo-v1'."""
    _record_version_via_engine(db_session)

    versions = db_session.scalars(select(ModelVersion)).all()
    assert len(versions) == 1
    assert versions[0].name == "elo-v1"


def test_record_same_params_reuses_existing_version(db_session):
    """Mismos params → NO crea versión nueva; reutiliza elo-v1."""
    _record_version_via_engine(db_session)
    _record_version_via_engine(db_session)

    count = db_session.scalar(select(func.count(ModelVersion.id)))
    assert count == 1  # sigue siendo 1, no 2


def test_changed_params_creates_new_version(db_session):
    """Params distintos → INSERT elo-v2; elo-v1 queda intacto."""
    # Crear elo-v1 con parámetros originales
    _record_version_via_engine(db_session, initial=1500.0, home_adv=100.0)

    # Cambiar parámetros → debe crear elo-v2
    _record_version_via_engine(db_session, initial=1500.0, home_adv=120.0)  # home_adv diferente

    versions = db_session.scalars(
        select(ModelVersion).order_by(ModelVersion.name)
    ).all()
    assert len(versions) == 2

    names = {v.name for v in versions}
    assert "elo-v1" in names
    assert "elo-v2" in names


def test_elo_v1_params_preserved_after_v2_created(db_session):
    """elo-v1 y sus params NO son modificados cuando se crea elo-v2."""
    _record_version_via_engine(db_session, initial=1500.0, home_adv=100.0)
    v1_before = db_session.scalar(
        select(ModelVersion).where(ModelVersion.name == "elo-v1")
    )
    original_params = dict(v1_before.params_json)

    # Cambio de params → nueva versión
    _record_version_via_engine(db_session, initial=1500.0, home_adv=120.0)

    v1_after = db_session.scalar(
        select(ModelVersion).where(ModelVersion.name == "elo-v1")
    )
    assert v1_after is not None
    assert v1_after.params_json == original_params  # intacto
