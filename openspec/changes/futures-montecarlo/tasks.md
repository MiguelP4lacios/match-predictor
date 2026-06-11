# Tasks: Futures Monte Carlo — WC2026 Champion & Advance Probabilities

## Phase 1: Foundation

- [x] 1.1 `app/model/standings.py` — add `team_id: int = 0` to `StandingRow`; populate from `TeamRef.team_id` in `_accumulate()`; modify `tests/model/test_standings.py` to assert `team_id` is non-zero per row.
- [x] 1.2 `app/model/annex_c.py` — export `ANNEX_C: dict[frozenset[str], dict[str,str]]` with 495 entries and `validate_annex_c()`; create `tests/model/test_annex_c.py` (len==495, keys size 8, letters ⊆ A–L, Opt-1 lookup).
- [x] 1.3 `migrations/versions/m9_futures_schema.py` — 4-step migration: autocommit enum ADD `REACH_SEMI_FINAL`/`REACH_FINAL`; add `outcome_team_id FK(team.id) nullable`; DROP `uq_prediction_identity`; recreate including `outcome_team_id + competition_id`; lockstep update `app/models/enums.py` and `app/models/model.py`; test round-trip upgrade/downgrade in Docker.
- [x] 1.4 Verify futures sport key: `docker compose run --rm scheduler python -m app.scheduler.run --list-sports`; confirm `soccer_fifa_world_cup_winner` or correct key; update `app/core/config.py` with `odds_futures_sport_key` and `odds_futures_enabled: bool = False`.

## Phase 2: Simulator (TDD)

- [x] 2.1 `tests/model/test_montecarlo.py` RED — write three failing tests verbatim: knockout P(H)=0.45/P(D)=0.28/P(A)=0.27 → P(home_adv)=0.59/0.41; seed=42 called twice → byte-identical dicts; toy 2-group `sum(p_champion)∈[0.99,1.01]` and `result[team_1]["p_champion"] > result[team_2]["p_champion"]`.
- [x] 2.2 `app/model/montecarlo.py` GREEN — implement `simulate_tournament(groups, elo_ratings, model_params, completed_results, n_iterations=20_000, seed=42)`; seeded `numpy.random.Generator(PCG64(seed))`; vectorized `rng.choice` for 72-match outcome draw; Poisson GD tiebreak; Annex C third-place slot assignment; knockout `P(home_adv)=P(H)+0.5×P(D)`.
- [x] 2.3 BENCHMARK — add test asserting `elapsed < 15s` in Docker (`time.perf_counter`); if >10s vectorize further; document if reduced to 10k iters.

## Phase 3: Persist (TDD)

- [x] 3.1 `app/model/run_futures.py` RED+GREEN — `simulate` subcommand: `load_sim_inputs(session)` → `simulate_tournament()` → DELETE+INSERT `Prediction` rows (`model_version='montecarlo-v1'`, markets CHAMPION/ADVANCE_GROUP/REACH_SEMI_FINAL/REACH_FINAL, `outcome_team_id`, `competition_id=WC`); idempotent; test with fixture DB.
- [x] 3.2 Hook `run_futures.py simulate` in `tournament_update.sh` after `predict`, before `signals`.

## Phase 4: Futures Odds (TDD)

- [ ] 4.1 `app/ingestion/sources/odds_api.py` — add `fetch_futures() -> list[OutrightOddsRow]` (sport key from config, market `outrights`, 1 credit/run); test with fixture (NEVER live).
- [ ] 4.2 `app/ingestion/odds_pipeline.py` — outright capture path: resolve `outcome_name→team_id` via `TeamAlias`; discard+warn unresolved; persist `Odds(market_type=OUTRIGHT_WINNER, outcome_team_id)`; `SyncLog` upsert `resource='odds_api:futures_capture'`; test idempotency.
- [ ] 4.3 `app/scheduler/jobs.py` — add `capture_futures_odds_job()` (daily, configurable); test SyncLog upsert on repeat run.
- [ ] 4.4 `POST /api/v1/odds/manual` — accept `{market_type, outcome_team_id, decimal_odds, bookmaker, captured_at}`; allow only `GROUP_ADVANCE/REACH_SEMI_FINAL/REACH_FINAL`; reject `MATCH_1X2/OVER_UNDER` with HTTP 422; test both scenarios.

## Phase 5: Futures EV (TDD)

- [ ] 5.1 `app/model/futures_signals.py` RED+GREEN — `generate_futures_signals(session, mv_id)`: proportional de-vig over all N captured OUTRIGHT_WINNER odds; emit `ValueSignal(PAPER)` where `edge=p_model−p_fair≥edge_min`; idempotent on `(prediction_id, odds_id)`; skip `BacktestGateError` for futures (document caveat); test de-vig [1.80,3.50,4.50]→overround 1.0635→p_fair [0.5224,0.2686,0.2090] and edge scenarios (positive/negative/idempotent).

## Phase 6: API + Frontend (TDD)

- [ ] 6.1 `app/api/routers/futures.py` — `GET /api/v1/futures/probabilities` (48 items, p_champion ranked DESC, no external calls) and `GET /api/v1/futures/signals` (pre-computed EV, no recompute in path); add `FuturesProbItem`, `FuturesProbResponse`, `FuturesSignalItem` to `app/api/schemas.py`; register router in `app/main.py`; test 200+48 items, empty case, sum constraint.
- [ ] 6.2 `frontend/src/api/types.ts` — add `FutureTeamRow`, `FuturesList`, `FutureSignal` types per spec R7.
- [ ] 6.3 `frontend/src/pages/FuturesDashboard.tsx` — champion table (ranked, `FlagLabel`, pct 1 decimal), group-advance cards (A–L), EV signals table; `staleTime: 55_000`; skeleton + error banner + "Reintentar"; only design-system primitives; no hardcoded colors; test all three scenarios (table, empty signals, fetch error).
- [ ] 6.4 `frontend/src/App.tsx` — add `/futures` route + "Futuros" nav entry; test deep-link and nav click.

## Phase 7: Cierre

- [ ] 7.1 Run full test suite + ruff check/format + frontend build; fix any failures.
- [ ] 7.2 Run `docker compose run --rm scheduler python -m app.model.run_futures simulate`; capture and report top-10 champion probabilities.
- [ ] 7.3 DEPLOY VPS — rsync, build API + frontend, `docker compose up`; apply m9 via `alembic upgrade head`; smoke `GET /api/v1/futures/probabilities` with auth.
- [ ] 7.4 Commit all changes (conventional commits, no AI attribution); push to remote; save `sdd/futures-montecarlo/apply-progress` to engram.
