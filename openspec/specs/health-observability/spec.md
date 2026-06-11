# Health Observability Specification

## Purpose

Proveer observabilidad operacional del sistema desde la base de datos: endpoint
`GET /api/v1/health/full` que sirve métricas con veredictos ok/warn/stale, página
"Estado" en el frontend (lenguaje de hincha), y `StatusBadge` global 🟢/🟡/🔴.
Invariante: NUNCA llama a API externa en el request; todo serve-from-DB.

---

## Requirements

### Requirement: HO1 — Endpoint GET /api/v1/health/full

El endpoint MUST retornar un objeto JSON con las siguientes métricas, cada una con
`value` (dato crudo) y `verdict` (`"ok"` | `"warn"` | `"stale"`):

| Métrica | Fuente DB | Umbral warn | Umbral stale |
|---------|-----------|-------------|--------------|
| `odds_capture.last_at` | `sync_log` WHERE `resource='odds_api:capture'` → `last_fetched_at` | — | age > 10h |
| `odds_capture.age_hours` | calculado desde `last_at` hasta NOW() | > 4h | > 10h |
| `odds_credits.remaining` | `sync_log` WHERE `resource='odds_api:capture'` → `credits_remaining` | < 100 | — |
| `model.name` | `model_version` → nombre activo (max id) | — | NULL |
| `results.latest_date` | `match` WHERE `status='FINISHED'` → `MAX(match_date)` | — | NULL o > 3 días atrás |

El veredicto de `odds_capture` MUST ser `"ok"` si `age_hours ≤ 4`, `"warn"` si `4 < age_hours ≤ 10`, `"stale"` si `age_hours > 10` o si nunca hubo captura (`last_at = null`).

El veredicto de `odds_credits` MUST ser `"ok"` si `remaining ≥ 100`, `"warn"` si `remaining < 100` o si `remaining = null`.

El endpoint MUST NOT realizar ninguna llamada HTTP externa.
El endpoint MUST responder en < 500ms bajo carga normal (solo queries DB).

Forma de respuesta:

```json
{
  "odds_capture": { "last_at": "<iso8601|null>", "age_hours": <float|null>, "verdict": "ok|warn|stale" },
  "odds_credits": { "remaining": <int|null>, "verdict": "ok|warn" },
  "model":        { "name": "<string|null>", "verdict": "ok|stale" },
  "results":      { "latest_date": "<date|null>", "verdict": "ok|stale" }
}
```

#### Scenario: Captura reciente — ok

- GIVEN `sync_log` tiene fila `resource='odds_api:capture'` con `last_fetched_at` hace 2h y `credits_remaining=488`
- WHEN `GET /api/v1/health/full`
- THEN `odds_capture.verdict="ok"`, `odds_capture.age_hours≈2.0`, `odds_credits.remaining=488`, `odds_credits.verdict="ok"`

#### Scenario: Captura antigua — stale

- GIVEN `last_fetched_at` hace 12h
- WHEN `GET /api/v1/health/full`
- THEN `odds_capture.age_hours≈12.0`, `odds_capture.verdict="stale"`

#### Scenario: Créditos bajos — warn

- GIVEN `credits_remaining=50`
- WHEN `GET /api/v1/health/full`
- THEN `odds_credits.remaining=50`, `odds_credits.verdict="warn"`

#### Scenario: Sin captura nunca — stale

- GIVEN no hay filas en `sync_log` con `resource='odds_api:capture'`
- WHEN `GET /api/v1/health/full`
- THEN `odds_capture.last_at=null`, `odds_capture.verdict="stale"`

#### Scenario: No external call

- GIVEN un handler que intenta llamar a The Odds API dentro del request
- WHEN el endpoint recibe la solicitud
- THEN la llamada externa MUST estar prohibida por arquitectura (mismo invariante R1 de api-readonly)

---

### Requirement: HO2 — SyncLog: columnas de auditoría de captura

El modelo `SyncLog` MUST agregar dos columnas nullable (migración Alembic aditiva):

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| `rows_inserted` | `INTEGER` | sí | Cantidad de filas `Odds` insertadas en la captura |
| `credits_remaining` | `INTEGER` | sí | Créditos restantes de The Odds API tras la captura |

Las columnas MUST ser nullable para compatibilidad con filas históricas (sin backfill).
La migración Alembic MUST ser reversible (downgrade dropea ambas columnas).

#### Scenario: Migración no rompe filas existentes

- GIVEN `sync_log` tiene filas históricas sin las nuevas columnas
- WHEN se ejecuta `alembic upgrade head`
- THEN las filas existentes tienen `rows_inserted=null`, `credits_remaining=null`; la tabla es legible

---

### Requirement: HO3 — StatusBadge con polling

El componente `StatusBadge` MUST:
- Llamar `GET /api/v1/health/full` al montar y luego cada 60s (polling).
- Calcular el veredicto agregado como el peor entre todas las métricas:
  `"stale"` > `"warn"` > `"ok"`.
- Renderizar `🟢` para `"ok"`, `🟡` para `"warn"`, `🔴` para `"stale"`.
- MUST NOT calcular ningún valor — solo lee la respuesta del endpoint.
- En error de fetch, MUST mostrar `🔴` (peor caso conservador).

#### Scenario: Veredicto ok — todo verde

- GIVEN `health/full` retorna todos los campos con `verdict="ok"`
- WHEN StatusBadge recibe la respuesta
- THEN muestra 🟢

#### Scenario: Un warn → amarillo

- GIVEN `health/full` retorna `odds_credits.verdict="warn"`, resto `"ok"`
- WHEN StatusBadge recibe la respuesta
- THEN muestra 🟡

#### Scenario: Un stale → rojo

- GIVEN `health/full` retorna `odds_capture.verdict="stale"`, resto `"ok"`
- WHEN StatusBadge recibe la respuesta
- THEN muestra 🔴

#### Scenario: Error de fetch

- GIVEN `GET /api/v1/health/full` retorna 500
- WHEN StatusBadge intenta el fetch
- THEN muestra 🔴; no muestra pantalla en blanco ni crash

---

### Requirement: HO4 — Página Estado (/estado)

La ruta `/estado` MUST renderizar una página con:
- Título "Estado del sistema" (o equivalente en lenguaje de hincha).
- Una fila por métrica con: nombre en español de hincha, valor legible, veredicto con color.
- Tiempo relativo: "hace Xh" calculado desde `last_at` hasta ahora en el cliente.
- El frontend MUST NOT computar veredictos — solo muestra los que retorna la API.

Textos de métricas en español de hincha:

| Métrica | Etiqueta |
|---------|----------|
| `odds_capture` | "Última captura de cuotas" |
| `odds_credits` | "Créditos The Odds API" |
| `model` | "Modelo activo" |
| `results` | "Último resultado cargado" |

#### Scenario: Página muestra veredicto y tiempo relativo

- GIVEN `odds_capture.last_at` es hace 2h, `verdict="ok"`
- WHEN el usuario visita `/estado`
- THEN ve "Última captura de cuotas · hace 2h · 🟢"

#### Scenario: Stale se muestra en rojo

- GIVEN `odds_capture.verdict="stale"`, `age_hours=12.5`
- WHEN el usuario visita `/estado`
- THEN la fila muestra veredicto en rojo; texto "hace 12h" (redondeado)
