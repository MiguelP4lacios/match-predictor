# Delta for Odds Capture

## ADDED Requirements

### Requirement: Capture Audit Logging

`OddsCapturePipeline.capture()` MUST persistir una fila en `sync_log` al finalizar
cada ejecución, independientemente de si se insertaron filas de odds o no.

La fila MUST usar `resource='odds_api:capture'` (upsert por `resource+source`).
Los campos MUST ser:

| Campo | Valor |
|-------|-------|
| `resource` | `"odds_api:capture"` |
| `source` | `DataSource.ODDS_API` (o equivalente del enum) |
| `last_fetched_at` | timestamp UTC de finalización del job |
| `rows_inserted` | cantidad de filas `Odds` insertadas en esa ejecución |
| `credits_remaining` | valor de `source.last_remaining` tras la llamada |

El upsert MUST usar la constraint `uq_sync_resource_source` existente:
si ya existe la fila, MUST actualizarla (ON CONFLICT UPDATE).

Si `capture()` falla antes de insertar odds, MUST igualmente intentar escribir
el log con `rows_inserted=0` y el error capturado en `status`.

#### Scenario: Log escrito tras captura exitosa

- GIVEN `capture()` inserta 24 filas de Odds con `source.last_remaining=476`
- WHEN el job finaliza
- THEN `sync_log` tiene una fila con `resource='odds_api:capture'`,
  `rows_inserted=24`, `credits_remaining=476`, `last_fetched_at` en los últimos 5 segundos

#### Scenario: Log escrito con cero inserciones

- GIVEN `capture()` no recibe eventos de The Odds API (respuesta vacía)
- WHEN el job finaliza
- THEN `sync_log` tiene una fila con `rows_inserted=0`, `credits_remaining` del valor devuelto

#### Scenario: Upsert — segunda captura actualiza la fila

- GIVEN `sync_log` ya tiene fila `resource='odds_api:capture'` de ejecución anterior
- WHEN `capture()` corre nuevamente con `rows_inserted=10`, `credits_remaining=466`
- THEN la tabla tiene EXACTAMENTE una fila para `resource='odds_api:capture'`;
  `rows_inserted=10`, `credits_remaining=466` (no se crea duplicado)

#### Scenario: Sistema responde "¿corrió odds?" con dato real

- GIVEN se ejecutó al menos una captura
- WHEN `GET /api/v1/health/full`
- THEN `odds_capture.last_at` no es null; el sistema puede responder cuándo corrió y cuántos créditos quedan
