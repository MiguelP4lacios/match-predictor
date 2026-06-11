# futures-api Specification

## Purpose

API REST que sirve probabilidades de torneo (campeón, avance, semi, final) y señales +EV de futuros desde la BD, sin invocar simulación en request.

---

## Requirements

### Requirement: Champion Probabilities Endpoint

`GET /api/v1/futures/probabilities` MUST return the 48-team champion/advance/semi/final probabilities ranked by `p_champion` DESC, served from the latest `prediction` rows in the DB for the active `model_version`. The sum of `p_champion` across all 48 teams MUST be ≥ 0.99 and ≤ 1.01.

Response shape per team:

| Field | Type | Source |
|-------|------|--------|
| `team_id` | int | `prediction.outcome_team_id` |
| `team_name` | str | joined from `team` table |
| `p_champion` | float | `prediction.probability` where `market_type=OUTRIGHT_WINNER` |
| `p_advance_group` | float | `market_type=GROUP_ADVANCE` |
| `p_reach_semi` | float | `market_type=REACH_SEMI_FINAL` |
| `p_reach_final` | float | `market_type=REACH_FINAL` |

The endpoint MUST NOT call the simulator or any external API in the request path.

#### Scenario: 48 teams returned, sums to 1

- GIVEN the `prediction` table has rows written by the last simulator run
- WHEN `GET /api/v1/futures/probabilities`
- THEN response contains 48 items; `sum(item.p_champion)` ∈ [0.99, 1.01]; items ordered by `p_champion` DESC

#### Scenario: No predictions yet

- GIVEN no `prediction` rows exist for `OUTRIGHT_WINNER`
- WHEN `GET /api/v1/futures/probabilities`
- THEN response returns HTTP 200 with `{"items": [], "total": 0}` — no crash

---

### Requirement: Futures EV Signals Endpoint

`GET /api/v1/futures/signals` MUST return teams where a `value_signal` row exists for `OUTRIGHT_WINNER`, joined with the latest captured outright odds and the model `p_champion`. The response MUST include `edge`, `p_model`, `p_fair`, `best_odds`, and `bookmaker`.

EV is pre-computed (stored in `value_signal.ev`). The endpoint MUST NOT re-compute EV in the request path.

#### Scenario: EV signal present when p_model > p_fair

- GIVEN team_id=7 has `prediction.probability=0.18` (OUTRIGHT_WINNER) and a captured outright odd with de-vigged implied `p_fair=0.14`
- WHEN `GET /api/v1/futures/signals`
- THEN response includes team_id=7 with `edge=0.04`, `p_model=0.18`, `p_fair=0.14`

#### Scenario: No signals when odds not captured

- GIVEN no `odds` rows exist for `OUTRIGHT_WINNER` market
- WHEN `GET /api/v1/futures/signals`
- THEN response returns `{"items": [], "total": 0}`

---

### Requirement: Migration m9 Schema

Migration `m9` MUST:
1. ADD column `outcome_team_id INTEGER REFERENCES team(id)` (nullable) to `prediction`.
2. ADD values `REACH_SEMI_FINAL` and `REACH_FINAL` to the `MarketType` PostgreSQL enum.
3. DROP constraint `uq_prediction_identity` and recreate as UNIQUE on `(model_version_id, match_id, market_type, outcome_code, outcome_team_id)`.

The migration MUST be reversible (downgrade drops `outcome_team_id`, removes enum values, restores old constraint).

#### Scenario: Unique constraint allows multiple OUTRIGHT_WINNER rows

- GIVEN migration m9 has run
- WHEN inserting two `prediction` rows with `market_type=OUTRIGHT_WINNER`, same `model_version_id`, `match_id=NULL`, `outcome_team_id=5` and `outcome_team_id=9` respectively
- THEN both rows are accepted (no unique constraint violation)

---
