# Proposal: Futures Monte Carlo — WC2026 Champion & Advance Probabilities

## Intent

WC2026 started 2026-06-11. The system has no champion or advance probabilities → no futures EV signals.
Build the full Monte Carlo bracket simulator before group stage ends, filling the last named target market.

## Scope

### In Scope
- `app/model/annex_c.py` — `ANNEX_C: dict[frozenset[str], dict[str, str]]`, 495 rows; validation test
- `app/model/standings.py` — add `team_id: int` field to `StandingRow` (additive; enables cross-group 3rd ranking)
- `app/model/montecarlo.py` — `simulate_tournament(groups, elo_ratings, model_params, completed_results, n_iterations=20_000, seed)` → `dict[int, dict[str, float]]` with `{p_champion, p_advance_group, p_reach_sf, p_reach_final}`. Group: 1X2 sample + Poisson goals (GD tiebreaker). Knockout: `P(adv) = P(H) + 0.5·P(D)`. Static Elo.
- Migration m9: ADD `outcome_team_id FK(team.id)` to `prediction`; ADD `REACH_SEMI_FINAL`, `REACH_FINAL` to `MarketType` PG enum; update `uq_prediction_identity` to include `outcome_team_id`
- `app/core/config.py` — `odds_futures_sport_key`, `odds_futures_markets` settings
- `app/ingestion/sources/odds_api.py` — `fetch_futures()` method; team name → `outcome_team_id` via `TeamAlias`
- `app/ingestion/odds_pipeline.py` — outright path: `OUTRIGHT_WINNER` + `outcome_team_id`
- `app/scheduler/jobs.py` — `capture_futures_odds` daily job (1 credit/run)
- `app/api/routers/futures.py` + service — `GET /futures/probabilities`, `GET /futures/signals`; serve from DB; EV = proportional de-vig over 48 outcomes
- `frontend/src/pages/FuturesDashboard.tsx` — champion prob table (ranked, flags), EV signal table

### Out of Scope
- In-tournament Elo updates per simulation round
- Fair-play tiebreaker (cards not tracked)
- Live knockout fixture ingestion (bracket is in-memory)
- Group advance odds via Odds API free tier (BetPlay manual fallback only)
- Portfolio-level Kelly / correlation between futures positions
- Quarter-final reach probability (p_reach_qf) — v2

## Capabilities

### New Capabilities
- `futures-montecarlo`: Annex C data module + standings fix + Monte Carlo engine
- `futures-api`: REST endpoints for futures probabilities and EV signals

### Modified Capabilities
- `odds-capture`: extends to outright winner market (config + scheduler + pipeline outright path)
- `value-signals`: EV calculation extended to OUTRIGHT_WINNER with proportional de-vig over N outcomes
- `dashboard-frontend`: Futures page added

## Approach

Full Monte Carlo (Approach A): simulate 72 group matches → Annex C third-place slot lookup → R32→R16→QF→SF→Final knockout chain → aggregate 20k seeded iterations → write to `prediction` table → serve from DB → compare vs captured outright odds → emit `value_signal`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/model/annex_c.py` | New | 495-row lookup constant |
| `app/model/standings.py` | Modified | `team_id` in `StandingRow` |
| `app/model/montecarlo.py` | New | Core simulator |
| `app/models/enums.py` | Modified | Two new MarketType values |
| `app/models/model.py` | Modified | `outcome_team_id` FK + constraint |
| `alembic/versions/m9_*` | New | Schema migration |
| `app/core/config.py` | Modified | Futures config keys |
| `app/ingestion/sources/odds_api.py` | Modified | `fetch_futures()` |
| `app/ingestion/odds_pipeline.py` | Modified | Outright pipeline path |
| `app/scheduler/jobs.py` | Modified | Futures capture job |
| `app/api/routers/futures.py` | New | `/futures/*` endpoints |
| `frontend/src/pages/FuturesDashboard.tsx` | New | Futures MVP page |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Annex C OCR errors (495-row table) | Med | Validation test: 495 unique frozensets of size 8 |
| Sim runtime >10s for 20k × 104 matches | Low | Benchmark in test; NumPy seeded RNG |
| Group advance odds not on free tier | High | Manual fallback; signal simply absent without odds |
| OLM draw renorm overestimates favorites | Low | Documented in montecarlo.py docstring |
| m9 breaks `standings.py` callers | Low | `team_id` is additive field; signature unchanged |

## Rollback Plan

Drop m9 migration (reverts schema — derived data only, no user data lost). Delete `annex_c.py`, `montecarlo.py`, `futures.py` router, `FuturesDashboard.tsx`. Revert config/scheduler/pipeline additions.

## Dependencies

- Migration m9 must run before persisting Monte Carlo output
- Elo ratings batch-loaded from DB at simulation start (all 48 teams)

## Success Criteria

- [ ] 20k-iteration sim runs <10s in Docker (`docker compose run --rm api pytest`)
- [ ] Annex C test: 495 rows, all frozensets unique, exactly 8 letters A-L each
- [ ] `GET /futures/probabilities` returns 48 teams; `sum(p_champion)` ≈ 1.0 ± 0.01
- [ ] Outright odds captured with `outcome_team_id` populated via `TeamAlias`
- [ ] EV signal appears when `p_model > de-vigged implied probability`
- [ ] All new pure functions have tests before implementation (strict TDD)
