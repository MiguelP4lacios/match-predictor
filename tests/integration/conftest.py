"""Fixtures para tests de integración de la API REST."""

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_session
from app.main import app


@pytest.fixture()
def client(db_session):
    """TestClient con la sesión de BD inyectada (SAVEPOINT isolation)."""
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
