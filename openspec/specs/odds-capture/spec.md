# Odds Capture Specification

## Purpose

Captura confiable de snapshots de cuotas desde The Odds API: persistencia siempre (match_id nullable), trazabilidad por `source_event_id`/`commence_time`, re-linkeo posterior al cargar fixtures, y desambiguación robusta de outcome para evitar odds corruptas.

## Requirements

### Requirement: Always-Persist Odds

`OddsCapturePipeline.capture()` in `app/ingestion/odds_pipeline.py` MUST persist every `Odds` row received from the source, regardless of whether a matching `Match` can be found in the database.

The `odds` table MUST have two new columns:
- `source_event_id VARCHAR(80)` — ID opaco de The Odds API para re-linkeo posterior.
- `commence_time TIMESTAMP` — hora UTC de inicio del evento según la fuente.

The `match` table MUST have a new column:
- `kickoff_at TIMESTAMP` — hora UTC del partido (from `commence_time` when fixture is loaded).

When no match is found, the `Odds` row MUST be inserted with `match_id = NULL`.

A separate job/script `relink_odds` MUST exist that attempts to match unlinked odds (`match_id IS NULL`) to their `Match` using `source_event_id` or the `commence_time ± 1 day` + team-pair strategy, and updates `match_id` in place.

#### Scenario: Odds without fixture are persisted

- GIVEN The Odds API returns a h2h event for teams not yet in the `match` table
- WHEN `capture()` is called
- THEN an `Odds` row is inserted with `match_id = NULL`, `source_event_id` set, `commence_time` set
- AND the return dict `"unlinked_events"` count is > 0

#### Scenario: Odds with fixture get match_id on capture

- GIVEN the `match` table has a scheduled match for `(TeamA, TeamB)` with `kickoff_at` within 1 day of `commence_time`
- WHEN `capture()` is called for that event
- THEN the `Odds` row is inserted with `match_id` set (NOT NULL)

#### Scenario: relink_odds links previously unlinked odds

- GIVEN `odds` table has rows with `match_id = NULL` and valid `source_event_id`
- AND the corresponding `match` row now exists
- WHEN `relink_odds` job runs
- THEN those rows have `match_id` updated to the correct match id
- AND rows that still have no match remain `match_id = NULL`

---

### Requirement: Reliable Outcome Code Resolution

`OddsCapturePipeline._outcome_code()` MUST assign `"DRAW"` ONLY when `ro.outcome_name == "Draw"` (exact string, case-insensitive comparison).

When `self._resolve(ro.outcome_name)` returns `None` for a non-"Draw" outcome name (unresolved team), the pipeline MUST discard the `Odds` row and log a warning containing the unresolved name. It MUST NOT assign `"DRAW"` to an unresolved team name.

Match linking for h2h/totals MUST compare `ro.commence_time` against `Match.kickoff_at` within ±1 day in addition to the team-pair frozenset. If both a team-pair match AND a time constraint are required, time takes precedence for disambiguation when multiple matches exist for the same pair.

#### Scenario: "Draw" outcome code assigned correctly

- GIVEN a h2h market row with `outcome_name = "Draw"`
- WHEN `_outcome_code()` is called
- THEN it returns `"DRAW"`

#### Scenario: Unresolved team name is not treated as DRAW

- GIVEN a h2h market row with `outcome_name = "Côte d'Ivoire"` and the resolver returns `None`
- WHEN `_outcome_code()` is called
- THEN the `Odds` row is discarded (not inserted)
- AND a warning is logged containing `"Côte d'Ivoire"`

#### Scenario: Disambiguation by commence_time when two fixtures share same pair

- GIVEN `match` table has two rows for `(TeamA, TeamB)`: one on 2026-06-14 and one on 2026-06-15
- AND `ro.commence_time` falls within ±1 day of 2026-06-15
- WHEN `_build_match_index()` resolves the match
- THEN the `Odds` row links to the 2026-06-15 match (not the 2026-06-14 one)

---

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

---

## Futures Markets (futures-montecarlo change)

### Requirement: Futures Odds Capture Path

`app/ingestion/sources/odds_api.py` MUST expose `fetch_futures() -> list[OutrightOddsRow]` that calls the outright winner endpoint (`odds_futures_sport_key` from config, market `outrights`). Each `OutrightOddsRow` MUST include `outcome_name` (bookmaker team name) and `decimal_odds`.

`app/ingestion/odds_pipeline.py` MUST implement an outright capture path that:
1. Calls `fetch_futures()`.
2. Resolves `outcome_name` → canonical `team_id` via `TeamAlias` (exact same resolution logic as h2h). If resolution fails, MUST discard the row and log a warning.
3. Persists each resolved row as an `Odds` record with `market_type=OUTRIGHT_WINNER` and `outcome_team_id` populated.
4. Consumes exactly 1 API credit per run.

`app/core/config.py` MUST expose `odds_futures_sport_key: str` and `odds_futures_markets: list[str]` settings (both from environment/yaml).

#### Scenario: Outright odds persisted with outcome_team_id

- GIVEN The Odds API returns outright odds for "Brazil" (alias maps to team_id=12) at decimal_odds=5.50
- WHEN the futures capture pipeline runs
- THEN an `Odds` row is inserted with `market_type=OUTRIGHT_WINNER`, `outcome_team_id=12`, `decimal_odds=5.50`
- AND `sync_log` has a futures capture row with `rows_inserted=1`, `credits_used=1`

#### Scenario: Unresolved team name discarded

- GIVEN The Odds API returns outright odds for "Brasil" and `TeamAlias` has no mapping for "Brasil"
- WHEN the futures capture pipeline runs
- THEN no `Odds` row is inserted for "Brasil"
- AND a warning is logged containing "Brasil"

---

### Requirement: Futures Capture Audit Log

`app/scheduler/jobs.py` MUST expose a `capture_futures_odds` job (daily, configurable). After each run, MUST write or upsert a `sync_log` row with `resource='odds_api:futures_capture'`, `rows_inserted`, `credits_remaining`, and `last_fetched_at`. Uses ON CONFLICT UPDATE on `uq_sync_resource_source`.

#### Scenario: SyncLog upsert on repeated futures capture

- GIVEN `sync_log` already has a `resource='odds_api:futures_capture'` row from a prior run
- WHEN `capture_futures_odds` runs again with `rows_inserted=48`, `credits_remaining=452`
- THEN the table has EXACTLY one row for that resource; `rows_inserted=48`, `credits_remaining=452`

---

### Requirement: Manual BetPlay Odds Entry

The system MUST provide `POST /api/v1/odds/manual` that accepts `{market_type, outcome_team_id, decimal_odds, bookmaker, captured_at}` and persists an `Odds` row. This endpoint enables manual entry of group-advance and reach-final outright odds not available via The Odds API free tier.

Only `market_type` values of `GROUP_ADVANCE`, `REACH_SEMI_FINAL`, and `REACH_FINAL` MAY be submitted via this endpoint; `MATCH_1X2` and `OVER_UNDER` MUST be rejected (HTTP 422).

#### Scenario: Manual BetPlay advance odds persisted

- GIVEN a valid POST body `{market_type: "GROUP_ADVANCE", outcome_team_id: 5, decimal_odds: 1.30, bookmaker: "betplay"}`
- WHEN `POST /api/v1/odds/manual`
- THEN HTTP 201 and an `Odds` row is inserted with those values; `match_id=NULL`

#### Scenario: 1X2 manual entry rejected

- GIVEN POST body `{market_type: "MATCH_1X2", ...}`
- WHEN `POST /api/v1/odds/manual`
- THEN HTTP 422 with message indicating only futures markets are accepted
