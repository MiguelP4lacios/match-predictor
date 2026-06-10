"""Tests para GET /api/v1/model.

Escenarios de spec api-readonly:
  R5-S1: ModelVersion con backtest → valores exactos del JSON de la BD
"""

from app.models.model import ModelVersion


def test_model_returns_active_version(client, db_session):
    """R5-S1: endpoint devuelve el ModelVersion con mayor id, con backtest exacto."""
    mv = ModelVersion(
        name="dixon-coles-v1",
        params_json={
            "backtest": {
                "brier": 0.198,
                "logloss": 0.541,
                "beats_baselines": True,
            },
            "thresholds": {"min_edge": 0.05},
        },
    )
    db_session.add(mv)
    db_session.flush()

    resp = client.get("/api/v1/model")

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "dixon-coles-v1"
    assert body["backtest"]["brier"] == 0.198
    assert body["backtest"]["logloss"] == 0.541
    assert body["backtest"]["beats_baselines"] is True
