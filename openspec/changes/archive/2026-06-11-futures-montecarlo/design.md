# Design: Futures Monte Carlo — WC2026 Champion & Advance Probabilities

## Technical Approach

Extend the deterministic model layer with a seeded NumPy Monte Carlo engine that simulates the full WC2026 bracket from current state to champion 20 000 times, persists probabilities to `prediction`, serves them from `GET /futures/probabilities`, and compares against captured outright odds to emit PAPER-flagged +EV signals. No new fitted model required — reuses OLM `predict_proba` + existing Elo ratings.

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|---|---|---|---|
| Goal model (GD tiebreak) | Fixed-lambda Poisson conditioned on sampled outcome: W→(Poi(1.5), Poi(0.8)); D→(Poi(1.1), Poi(1.1)); L→(Poi(0.8), Poi(1.5)) | Full Dixon-Coles per-team lambdas; deterministic proxy 1-0/0-0 | No extra fitted model; GD only matters in cross-group 3rd rank (rare); proxy too coarse for pts ties |
| Sim performance | Seeded `numpy.random.Generator(PCG64(seed))`; vectorize 72-match outcome draw per iteration with `rng.choice` over precomputed p-arrays | Pure Python loops | Hits <10s budget without new deps; seed guarantees reproducibility |
| `StandingRow` team_id | Add `team_id: int` field; populate from `_accumulate` dict key; return it from `compute_standings` | New `ranked_with_ids()` helper | Additive dataclass field; `groups.py` reads named fields only — no breakage |
| New MarketTypes | Add `REACH_SEMI_FINAL`, `REACH_FINAL` to PG enum (UPPERCASE, `autocommit_block`) | Reuse GROUP_ADVANCE + outcome_code string | Explicit and queryable; consistent with OUTRIGHT_WINNER casing |
| `uq_prediction_identity` | Drop old; new on `(model_version_id, match_id, competition_id, market_type, outcome_code, outcome_team_id)` | Keep old + partial index | PG NULLs are distinct → futures rows (match_id=NULL, team_id=X) are unique; 1X2 rows (team_id=NULL) unaffected |
| Futures backtest gate | Skip `BacktestGateError`; all futures-derived signals flagged `PAPER`; docstring caveat | Block until MC backtested | Monte Carlo champion probs have no historical backtest (N=1 WC per year). Honest documentation > false gate |
| Futures odds capture | Reuse `OddsCapturePipeline.capture()` + existing `fetch_odds()` with new `odds_futures_sport_key` config; add `capture_futures_odds_job` | New `fetch_futures()` method | Pipeline `_MARKET_MAP` already maps `outrights→OUTRIGHT_WINNER`; only config changes needed |
| Futures EV | New `app/model/futures_signals.py` + `generate_futures_signals()` | Extend existing `signals.py` | `signals.py` JOINs on `match_id`; futures need `competition_id + outcome_team_id` JOIN path; separation avoids coupling |

## Data Flow

```
DB: tournament_group, group_team, elo_rating, match(FINISHED)
         │
         ▼
 run_futures.py simulate
   load_sim_inputs(session) → groups{}, elo{}, completed_results{}, params
   simulate_tournament(...)
     per iter: sample 72 outcomes (numpy) → standings → rank thirds
               → ANNEX_C lookup → R32→R16→QF→SF→Final
               → record deepest_round per team_id
     aggregate / 20 000 → {team_id: {p_champion, p_reach_final, p_reach_sf, p_advance_group}}
   DELETE old futures predictions for mv + INSERT new (idempotent)
         │
         ▼
 run_futures.py signals
   futures_signals.generate_futures_signals(session, mv_id)
     load OUTRIGHT_WINNER predictions + captured odds
     de-vig proportional over N captured teams
     emit ValueSignal(PAPER) where edge > 0
         │
         ▼
 GET /api/v1/futures/probabilities  ← serve from prediction table (0 external calls)
 GET /api/v1/futures/signals        ← serve from value_signal + prediction + odds
```

## File Changes

| File | Action | Description |
|---|---|---|
| `app/model/annex_c.py` | Create | `ANNEX_C: dict[frozenset[str], dict[str,str]]` — 495 entries |
| `app/model/montecarlo.py` | Create | `simulate_tournament()` engine; Annex C lookup; numpy RNG |
| `app/model/run_futures.py` | Create | Runner: `simulate` / `signals` subcommands (follows `run_1x2.py` pattern) |
| `app/model/futures_signals.py` | Create | De-vig + `ValueSignal` writer for OUTRIGHT_WINNER (PAPER-flagged) |
| `app/model/standings.py` | Modify | Add `team_id: int` to `StandingRow`; populate in `_accumulate`; expose in `compute_standings` return |
| `app/model/ratings.py` | Modify | Add `get_current_ratings(session, team_ids) -> dict[int, float]` batch query |
| `app/models/enums.py` | Modify | Add `REACH_SEMI_FINAL = "REACH_SEMI_FINAL"`, `REACH_FINAL = "REACH_FINAL"` |
| `app/models/model.py` | Modify | Add `outcome_team_id FK(team.id) nullable`; update `uq_prediction_identity` columns |
| `migrations/versions/m9_futures_schema.py` | Create | 4-step migration (see Migration section) |
| `app/core/config.py` | Modify | Add `odds_futures_sport_key: str`, `odds_futures_enabled: bool = False` |
| `app/scheduler/jobs.py` | Modify | Add `capture_futures_odds_job()` |
| `app/api/routers/futures.py` | Create | `GET /futures/probabilities`, `GET /futures/signals` |
| `app/api/schemas.py` | Modify | `FuturesProbItem`, `FuturesProbResponse`, `FuturesSignalItem` |
| `app/main.py` | Modify | Import + register `futures_router` with `/api/v1` prefix |
| `frontend/src/pages/FuturesDashboard.tsx` | Create | Champion prob table (ranked, flags) + EV signals |
| `frontend/src/App.tsx` | Modify | Add `/futures` route + nav entry |
| `frontend/src/api/types.ts` | Modify | `FuturesProbResponse`, `FuturesSignalResponse` types |
| `tests/model/test_annex_c.py` | Create | `len(ANNEX_C)==495`; all keys size 8; all letters in A–L |
| `tests/model/test_montecarlo.py` | Create | `sum(p_champion)≈1.0±0.01`; seed determinism; runtime <10s |
| `tests/model/test_standings.py` | Modify | Assert `team_id` populated in returned rows |
| `tests/api/test_futures.py` | Create | 200 + 48 items; probabilities in `[0,1]` |

## Interfaces / Contracts

```python
# app/model/montecarlo.py
def simulate_tournament(
    groups: dict[str, list[int]],                    # {"A": [team_id, ...]}
    elo_ratings: dict[int, float],                   # {team_id: 1820.0}
    model_params: dict,                              # OLM params from ModelVersion
    completed_results: dict[str, list[MatchResult]], # FINISHED group matches keyed by group
    n_iterations: int = 20_000,
    seed: int | None = 42,
) -> dict[int, dict[str, float]]:
    # {team_id: {"p_champion": 0.12, "p_reach_final": 0.24,
    #            "p_reach_sf": 0.38, "p_advance_group": 0.71}}

# Knockout advancement probability (P(D) absorbed 50/50 — documented caveat: slight
# favorite over-estimation since draws skew to even-strength matchups)
p_home_advances = p_home + 0.5 * p_draw

# app/model/annex_c.py
ANNEX_C: dict[frozenset[str], dict[str, str]]
# key = frozenset of 8 qualifying group letters (e.g. frozenset({"A","B","C","D","E","F","G","H"}))
# value = {"1A": "H", "1B": "G", ...}  (slot → group letter whose 3rd-placed team fills it)
```

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | `ANNEX_C` correctness | `len==495`, all frozensets size 8, all letters ⊆ {A..L}, all value dicts have 8 slots |
| Unit | `simulate_tournament` | seed→same result; `sum(p_champion)≈1.0`; benchmark assert `elapsed<10` |
| Unit | `StandingRow.team_id` | non-zero after `compute_standings` |
| Unit | futures de-vig | proportional de-vig over N=3 test odds sums to 1.0 ± 1e-9 |
| Integration | `/futures/probabilities` | 48 teams returned; all probs in `[0,1]` |
| Integration | m9 migration | `alembic upgrade m9 && alembic downgrade m8capfields` round-trips cleanly |

## Migration / Rollout

**m9** (`migrations/versions/m9_futures_schema.py`, revises `m8capfields`) — 4 steps:

1. `autocommit_block`: `ALTER TYPE market_type ADD VALUE IF NOT EXISTS 'REACH_SEMI_FINAL'` then `'REACH_FINAL'` (separate statements; PG requires autocommit for enum extensions)
2. `op.add_column("prediction", Column("outcome_team_id", Integer, ForeignKey("team.id"), nullable=True))`
3. `op.drop_constraint("uq_prediction_identity", "prediction", type_="unique")`
4. `op.create_unique_constraint("uq_prediction_identity", "prediction", ["model_version_id", "match_id", "competition_id", "market_type", "outcome_code", "outcome_team_id"])`

Downgrade: reverses steps 4→2. Enum values cannot be dropped in PG — documented as known limitation (no data with new values exists on downgrade).

`run_futures.py simulate` is idempotent: DELETE existing futures predictions for `model_version.name='montecarlo-v1'` before INSERT. Safe to re-run after each group match settles.

## Open Questions

- [ ] Confirm `odds_futures_sport_key` value via `/v4/sports` (free, no credit cost) — `soccer_fifa_world_cup_winner` vs `outrights` on base key — before enabling scheduler job
- [ ] Benchmark 20k iterations in Docker; reduce to 10k if >10s
