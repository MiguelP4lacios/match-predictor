"""TDD RED → GREEN — GET /api/v1/health/full.

Escenarios:
  S1 — Estado vacío (empty DB) → 200, shape completo, last_at=null, sin 500.
  S2 — Con sync_log sembrado → 200, odds_capture.age_hours presente y verdict correcto.

Invariantes:
  - NUNCA llama a API externa (validado estructuralmente: el endpoint usa get_session,
    no llama a httpx ni a settings.odds_api_key).
  - Respuesta en < 500ms (solo queries DB).
"""

from datetime import UTC, datetime, timedelta

from app.models.enums import DataSource
from app.models.sync import SyncLog

# ---------------------------------------------------------------------------
# S1 — empty DB: 200 + shape completo, sin 500
# ---------------------------------------------------------------------------


def test_health_full_empty_state_200(client):
    """Sin datos → 200 con shape completo; odds_capture.last_at=null."""
    resp = client.get("/api/v1/health/full")

    assert resp.status_code == 200

    data = resp.json()

    # Claves de primer nivel
    assert "overall" in data
    assert "odds_capture" in data
    assert "odds_credits" in data
    assert "model" in data
    assert "results" in data

    # Sub-shape odds_capture
    oc = data["odds_capture"]
    assert "last_at" in oc
    assert "age_hours" in oc
    assert "verdict" in oc
    assert oc["last_at"] is None  # vacío → null
    assert oc["verdict"] == "stale"  # nunca capturado → stale

    # Sub-shape odds_credits
    cr = data["odds_credits"]
    assert "remaining" in cr
    assert "verdict" in cr

    # Sub-shape model
    mv = data["model"]
    assert "name" in mv
    assert "verdict" in mv

    # Sub-shape results
    res = data["results"]
    assert "latest_date" in res
    assert "verdict" in res

    # overall es stale en DB vacía (sin model, sin results, sin capture)
    assert data["overall"] == "stale"


# ---------------------------------------------------------------------------
# S2 — con sync_log sembrado → age_hours y verdict correctos
# ---------------------------------------------------------------------------


def test_health_full_with_recent_capture(client, db_session):
    """Con capture hace 2h → odds_capture.verdict=ok."""
    now = datetime.now(UTC).replace(tzinfo=None)
    row = SyncLog(
        resource="odds_api:capture",
        source=DataSource.ODDS_API,
        last_fetched_at=now - timedelta(hours=2),
        credits_remaining=488,
        rows_inserted=10,
        status="ok",
    )
    db_session.add(row)
    db_session.flush()

    resp = client.get("/api/v1/health/full")

    assert resp.status_code == 200
    data = resp.json()

    oc = data["odds_capture"]
    assert oc["verdict"] == "ok"
    assert oc["age_hours"] is not None
    assert 1.9 < oc["age_hours"] < 2.1

    cr = data["odds_credits"]
    assert cr["remaining"] == 488
    assert cr["verdict"] == "ok"
