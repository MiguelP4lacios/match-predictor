"""Tests de integración TDD para GET /api/v1/signals/{id}/explain.

Spec signal-explanation R1:
  - GET /api/v1/signals/10/explain → 200 con 5 secciones esperadas
  - GET /api/v1/signals/9999/explain → 404 {"detail": "Signal not found"}

Usa TestClient con override de sesión de BD (SAVEPOINT isolation).
El escenario 200 se basa en la señal real id=10 sembrada en la BD de test.
"""


# RED: falla porque el endpoint no existe todavía
# (import del client viene del conftest de api, accesible vía conftest.py raíz)


def test_explain_signal_10_returns_200_with_expected_sections(client, db_session):
    """GET /api/v1/signals/10/explain → 200 con las 5 secciones esperadas."""
    resp = client.get("/api/v1/signals/10/explain")

    assert resp.status_code == 200, f"Unexpected status: {resp.status_code} — {resp.text}"

    body = resp.json()

    # Debe tener las 5 secciones definidas en el spec
    assert "sections" in body
    section_keys = {s["key"] for s in body["sections"]}
    expected_keys = {"edge", "origen_p_model", "stake", "calidad_modelo", "metadata"}
    assert expected_keys.issubset(section_keys), f"Faltan secciones: {expected_keys - section_keys}"

    # Cada sección tiene steps
    for section in body["sections"]:
        assert "steps" in section, f"Sección '{section['key']}' sin steps"
        assert len(section["steps"]) > 0, f"Sección '{section['key']}' con steps vacíos"

    # Verificación de valores canónicos en sección edge
    edge_sec = next(s for s in body["sections"] if s["key"] == "edge")
    step_keys = {s["key"] for s in edge_sec["steps"]}
    assert "p_model" in step_keys
    assert "edge" in step_keys
    assert "p_fair_derived" in step_keys

    p_model_step = next(s for s in edge_sec["steps"] if s["key"] == "p_model")
    assert abs(float(p_model_step["raw"]) - 0.83394) < 1e-4

    edge_step = next(s for s in edge_sec["steps"] if s["key"] == "edge")
    assert abs(float(edge_step["raw"]) - 0.14724) < 1e-4

    p_fair_step = next(s for s in edge_sec["steps"] if s["key"] == "p_fair_derived")
    assert abs(float(p_fair_step["raw"]) - 0.68670) < 1e-4

    # Verificación de metadata
    meta_sec = next(s for s in body["sections"] if s["key"] == "metadata")
    signal_id_step = next(s for s in meta_sec["steps"] if s["key"] == "signal_id")
    assert signal_id_step["raw"] == 10


def test_explain_unknown_signal_returns_404(client, db_session):
    """GET /api/v1/signals/9999/explain → 404 con detail 'Signal not found'."""
    resp = client.get("/api/v1/signals/9999/explain")

    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"] == "Signal not found"
