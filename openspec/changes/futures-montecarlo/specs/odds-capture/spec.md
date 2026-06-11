# Delta for odds-capture

## ADDED Requirements

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

---
