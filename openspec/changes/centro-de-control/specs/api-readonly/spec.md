# Delta for API Read-Only

## ADDED Requirements

### Requirement: R9 — GET /api/v1/health/full

El endpoint MUST retornar el estado operacional del sistema leyendo exclusivamente
de Postgres. Aplica el mismo invariante de R1 (Serve-from-DB Guarantee): MUST NOT
llamar a ninguna API externa ni recomputar valores.

El endpoint está definido completamente en la especificación `health-observability`.
Este requisito existe para registrar la adición al contrato de la API read-only.

Ruta: `GET /api/v1/health/full`
Tags: `["health"]`
Router: `app/api/health.py`

Forma de respuesta (campos mínimos):

```json
{
  "odds_capture": { "last_at": "<iso8601|null>", "age_hours": <float|null>, "verdict": "ok|warn|stale" },
  "odds_credits": { "remaining": <int|null>, "verdict": "ok|warn" },
  "model":        { "name": "<string|null>", "verdict": "ok|stale" },
  "results":      { "latest_date": "<date|null>", "verdict": "ok|stale" }
}
```

#### Scenario: Respuesta completa serve-from-DB

- GIVEN la BD tiene `sync_log` con fila `resource='odds_api:capture'`, `last_fetched_at` hace 2h, `credits_remaining=488`
- AND `model_version` tiene un registro activo con nombre `"dixon-coles-v1"`
- WHEN `GET /api/v1/health/full`
- THEN HTTP 200; `odds_capture.verdict="ok"`, `odds_credits.remaining=488`, `model.name="dixon-coles-v1"`
- AND ningún campo fue computado por llamada externa

#### Scenario: No computa ni llama externo

- GIVEN el handler intenta llamar a The Odds API para obtener créditos frescos
- WHEN el endpoint recibe la solicitud
- THEN la llamada externa MUST estar prohibida (mismo invariante R1 de api-readonly)

#### Scenario: Empty state — nunca hubo captura

- GIVEN no hay filas en `sync_log` con `resource='odds_api:capture'`
- WHEN `GET /api/v1/health/full`
- THEN HTTP 200; `odds_capture.last_at=null`, `odds_capture.verdict="stale"`; sin error 500
