# API Read-Only Specification

## Purpose

Define the contract for 5 read-only HTTP endpoints that expose predictions,
signals, model transparency, and paper-bet tracking from Postgres.
No endpoint MUST mutate state or call external APIs.

---

## Requirements

### Requirement: R1 — Serve-from-DB Guarantee

Every endpoint MUST read exclusively from Postgres within the request boundary.
MUST NOT call any external HTTP endpoint (The Odds API, API-Football, etc.).
MUST NOT perform EV, edge, or stake recomputation — serve PERSISTED values only.

#### Scenario: External call inside request

- GIVEN a handler that attempts an HTTP call to an external URL
- WHEN the endpoint is invoked
- THEN the system MUST raise a design-time violation (forbidden by architecture invariant)

---

### Requirement: R2 — GET /api/v1/signals

Returns paginated list of +EV signals joined with match, prediction, and best odds.
Supports query params: `from` (ISO date, inclusive), `to` (ISO date, inclusive),
`min_edge` (float ≥ 0), `limit` (int, default 50, max 200), `offset` (int, default 0).
Filters apply to `match.match_date` and `value_signal.edge` respectively.
Response fields per item (grounded in real columns):

| Field | Source column |
|---|---|
| `id` | `value_signal.id` |
| `match_date` | `match.match_date` |
| `kickoff_at` | `match.kickoff_at` |
| `home_team` | `team.name` via `match.home_team_id` |
| `away_team` | `team.name` via `match.away_team_id` |
| `market_type` | `prediction.market_type` |
| `outcome_code` | `prediction.outcome_code` |
| `p_model` | `prediction.probability` |
| `best_odds` | `odds.decimal_odds` (best per outcome) |
| `bookmaker` | `odds.bookmaker` |
| `edge` | `value_signal.edge` (persisted, no recompute) |
| `ev` | `value_signal.ev` |
| `kelly_fraction` | `value_signal.kelly_fraction` |
| `recommended_stake` | `value_signal.recommended_stake` |
| `captured_at` | `odds.captured_at` |

#### Scenario: Filtered signals list

- GIVEN signals exist with `match_date=2026-06-15`, `edge=0.08`
- WHEN `GET /api/v1/signals?from=2026-06-15&min_edge=0.05`
- THEN HTTP 200, body contains those signals; `edge` and `recommended_stake` match DB values exactly

#### Scenario: No results

- GIVEN no signals match the filters
- WHEN `GET /api/v1/signals?min_edge=0.99`
- THEN HTTP 200, `{"items": [], "total": 0}`

---

### Requirement: R3 — GET /api/v1/matches/upcoming

Returns matches with `status = SCHEDULED` joined with their 1X2 predictions.

| Field | Source |
|---|---|
| `id` | `match.id` |
| `match_date` | `match.match_date` |
| `kickoff_at` | `match.kickoff_at` |
| `home_team` | team name |
| `away_team` | team name |
| `neutral_site` | `match.neutral_site` |
| `stage` | `match.stage` |
| `p_home` | prediction.probability WHERE outcome_code=HOME |
| `p_draw` | prediction.probability WHERE outcome_code=DRAW |
| `p_away` | prediction.probability WHERE outcome_code=AWAY |
| `low_confidence` | `prediction.low_confidence` |

#### Scenario: Upcoming with predictions

- GIVEN match M (SCHEDULED) with 1X2 predictions p_home=0.55, p_draw=0.25, p_away=0.20
- WHEN `GET /api/v1/matches/upcoming`
- THEN M appears with those exact probability values and `low_confidence` flag

#### Scenario: Match without predictions

- GIVEN match M2 (SCHEDULED) with no predictions yet
- WHEN `GET /api/v1/matches/upcoming`
- THEN M2 appears with `p_home=null`, `p_draw=null`, `p_away=null`

---

### Requirement: R4 — GET /api/v1/matches/{id}

Returns full match detail: match fields + predictions (all market types) +
last odds snapshot per bookmaker + associated signals.
404 if `match.id` does not exist.

#### Scenario: Match found

- GIVEN match id=42 exists with 3 predictions and 2 odds snapshots
- WHEN `GET /api/v1/matches/42`
- THEN HTTP 200 with predictions list and last-odds-per-bookmaker list

#### Scenario: Match not found

- GIVEN no match with id=9999
- WHEN `GET /api/v1/matches/9999`
- THEN HTTP 404, `{"detail": "Match not found"}`

---

### Requirement: R5 — GET /api/v1/model

Exposes the ACTIVE `ModelVersion` (highest id). MUST NOT invent values.
Fields: `name`, `params_summary` (thresholds sub-object from `params_json`),
`backtest` (brier, logloss, beats_baselines from `params_json.backtest`),
`calibration` (table from `params_json.calibration`, if present).

#### Scenario: Model with backtest

- GIVEN ModelVersion name="dixon-coles-v1" with params_json containing
  `backtest.brier=0.198`, `backtest.logloss=0.541`, `beats_baselines=true`
- WHEN `GET /api/v1/model`
- THEN response includes those exact values verbatim from DB, no computation

---

### Requirement: R6 — GET /api/v1/paper

Aggregates PAPER-mode `BetLog` entries.
Fields: `total`, `open` (status=PENDING), `settled` (WON+LOST), `roi`.
ROI MUST be computed as: `sum(pnl) / sum(stake)` for WON and LOST bets only.
When `settled = 0`, `roi` MUST be `null` (no division by zero).

#### Scenario: ROI calculation (numeric verification)

- GIVEN 3 PAPER bets:
  - bet A: stake=50.00, pnl=+40.00, status=WON
  - bet B: stake=30.00, pnl=−30.00, status=LOST
  - bet C: stake=20.00, pnl=null, status=PENDING
- WHEN `GET /api/v1/paper`
- THEN `total=3`, `open=1`, `settled=2`,
  `roi = (40.00 + (−30.00)) / (50.00 + 30.00) = 10.00 / 80.00 = 0.125`

#### Scenario: No settled bets

- GIVEN all bets are PENDING
- WHEN `GET /api/v1/paper`
- THEN `roi=null`, no error

---

### Requirement: R7 — Empty Collection vs 404 Semantics

List endpoints (`/signals`, `/matches/upcoming`, `/groups`) MUST return
HTTP 200 with an empty collection when no items match.
Single-resource endpoints (`/matches/{id}`, `/groups/{name}`) MUST return HTTP 404.

---

### Requirement: R8 — CORS Configuration

The API MUST allow cross-origin requests from `http://localhost:5173` by default.
Additional origins MUST be configurable via `settings.cors_origins` (list of strings).
CORS MUST be applied as FastAPI middleware before any route handler.
