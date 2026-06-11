# Archive Report: futures-montecarlo

**Change**: futures-montecarlo  
**Archived**: 2026-06-11  
**Status**: PASS WITH WARNINGS (2 stale-spec warnings fixed, all behavioral tests pass)

---

## Lineage

### Exploration
- **Topic**: WC2026 bracket format + futures markets (champion, advance, semis, final)
- **Source**: FIFA official reglamento (Annex C: 495 third-place slot assignments for 8 best thirds across 12 groups of 4)
- **Findings**: Standard 12-group league stage (72 matches), 32-team knockout (R32→SF→Final), Elo static throughout tournament
- **Key document**: `openspec/changes/futures-montecarlo/exploration.md` (comprehensive 46KB exploration)

### Proposal
- **Intent**: Add Monte Carlo tournament simulator for WC2026 futures markets (OUTRIGHT_WINNER, GROUP_ADVANCE, REACH_SEMI_FINAL, REACH_FINAL)
- **Scope**: 5 domains (futures-montecarlo, futures-api, odds-capture delta, value-signals delta, dashboard-frontend delta)
- **Key innovation**: Deterministic simulator (seeded numpy PCG64, 20k iterations, ~1.08s), PAPER-always honesty gate for unfalsifiable championship probabilities
- **Market justification**: N=1 WC per 4 years makes historical backtest impossible → skip BacktestGateError for futures, document caveat

### Specs (5 domains)
1. **futures-montecarlo**: Annex C module (495 entries), StandingRow.team_id field, Monte Carlo simulator
2. **futures-api**: GET /futures/probabilities (48 teams ranked by p_champion), GET /futures/signals (pre-computed EV)
3. **odds-capture (delta)**: fetch_futures() + manual POST /odds/manual for group-advance/reach-final (free tier limits)
4. **value-signals (delta)**: Proportional de-vig (N outcomes), futures signals ALWAYS PAPER, EV ≥ 0.03 threshold
5. **dashboard-frontend (delta)**: /futures route, FuturesDashboard (champion table 48 teams, group cards, signals table)

### Design (8 decisions)
1. Seeded numpy.random.Generator(PCG64) for reproducibility
2. Vectorized 72-match draw per iteration (rng.choice)
3. Fixed-lambda Poisson for GD tiebreak (W→1.5/0.8, D→1.1/1.1, L→0.8/1.5)
4. Knockout formula: P(home_adv) = P(H) + 0.5×P(D)
5. Migration m9: +outcome_team_id FK, MarketType enum REACH_SEMI_FINAL/REACH_FINAL, uq_prediction_identity 6-column
6. Futures backtest gate SKIPPED → PAPER-always (design over-ruled spec text; rationale: N=1 WC/year)
7. OddsCapturePipeline reused for futures (no new method)
8. App model futures_signals.py separate (different JOIN: competition_id + outcome_team_id vs match_id)

### Tasks (22 total — all complete)
- **Phase 1 (Foundation)**: Annex C module, StandingRow.team_id, m9 migration, config
- **Phase 2 (Simulator)**: Monte Carlo RED → GREEN → BENCHMARK
- **Phase 3 (Persist)**: run_futures.py simulate subcommand, tournament_update.sh hook
- **Phase 4 (Futures Odds)**: fetch_futures(), pipeline capture, scheduler job, manual POST endpoint
- **Phase 5 (Futures EV)**: generate_futures_signals(), de-vig math, idempotency, PAPER-always
- **Phase 6 (API + Frontend)**: /futures/probabilities, /futures/signals, FuturesDashboard component
- **Phase 7 (Cierre)**: 251 backend + 240 frontend tests, ruff clean, VPS deploy, git push

### Implementation & Verification
- **Deployed**: VPS with m9 applied, /api/v1/futures live
- **Live data**: Spain 20.7% champion, Colombia 4.2% champ / 76.3% advance, monotonic hierarchy across 48 teams
- **Tests**: 251 backend (pytest) + 240 frontend (vitest) all pass
- **Build**: ruff clean, TypeScript + Vite build clean
- **Artifacts read from DB only** (0 external calls in GET endpoints)

---

## Issues Found & Fixed During Apply

### Behavioral Bugs (Found & Fixed)

1. **run_futures loaded wrong model params** (`app/model/run_futures.py`)
   - **Symptom**: `predict_proba(KeyError: '1x2-olm-v1')` when trying to load OLM coefficients
   - **Root cause**: `simulate` subcommand fetched `montecarlo-v1` params instead of `1x2-olm-v1` params from DB
   - **Fix**: Changed query to load `1x2-olm-v1` model_version and pass `olm.params_json` to `predict_proba`
   - **Impact**: Critical — blocked all futures simulations until fixed

2. **_build_bracket returned wrong team count** (`app/model/montecarlo.py`)
   - **Symptom**: `zip(bracket, outcomes, strict=True)` crash when 24 teams but 32 expected
   - **Root cause**: For 12-group format with 2 teams per group advancing + 8 best thirds, logic counted (2×12 + 8 = 32), but the 8 third-place selection was off by one
   - **Fix**: Corrected third-place ranking logic and bracket assembly to always return exactly 32 teams
   - **Impact**: Critical — only exposed by live data (toy 2-group tests passed because they have fewer groups)

3. **REACH_SEMI_FINAL / REACH_FINAL counters off-by-one** (`app/model/montecarlo.py`)
   - **Symptom**: p_reach_semi and p_reach_final were inverted (semi counted finalists, final counted champion)
   - **Root cause**: Counter logic grouped by round size incorrectly: `if len(bracket) == 4` should count SF, `if len(bracket) == 2` should count Final
   - **Fix**: Fixed counter logic to iterate by round size (32 → 16 → 8 → 4 → 2 → 1) and count correctly
   - **Impact**: Medium — probabilities were wrong but monotonic hierarchy was preserved

4. **Dev-DB pollution from real simulate run** (test isolation)
   - **Symptom**: Test suite failed when run after live simulation because predictions/signals from live data conflicted with fixture expectations
   - **Root cause**: Tests used same test DB without cleanup; live run persisted predictions that broke idempotency tests
   - **Fix**: Added transaction rollback + fixture isolation in test setup
   - **Impact**: Medium — CI/CD reliability issue, not a logic bug

### Documentation Warnings Fixed

1. **value-signals/spec.md — BacktestRequiredError text stale** (FIXED IN THIS PHASE)
   - Was: "MUST apply to futures signals without exception"
   - Now: "Futures signals ALWAYS flagged is_paper=True; backtest gate skipped (N=1 WC/year makes historical backtest impossible)"
   - Rationale: Design decision to honor unfalsifiable championship probabilities

2. **futures-api/spec.md — uq_prediction_identity column count** (FIXED IN THIS PHASE)
   - Was: Listed 5 columns (missing competition_id)
   - Now: Corrected to 6 columns: (model_version_id, match_id, competition_id, market_type, outcome_code, outcome_team_id)

3. **Phase 7 tasks not checked off** (FIXED IN THIS PHASE)
   - Tasks 7.1–7.4 were functionally complete but marked `[ ]` in tasks.md
   - Now: Marked `[x]` to reflect actual completion

---

## Achievements

### Simulator
- **Monte Carlo engine**: 20,000 iterations in ~1.08s (vectorized numpy operations)
- **Reproducibility**: Seeded PCG64 → byte-identical output across runs
- **Accuracy invariants**: 
  - `sum(p_champion)` ∈ [0.99, 1.01] ✓
  - Monotonic hierarchy: p_advance ≥ p_semi ≥ p_final ≥ p_champion ✓
  - Stronger Elo team has higher p_champion ✓

### Data
- **Annex C**: 495-entry lookup table from FIFA official reglamento (Annex C of tournament rules)
- **Bracket assembly**: Correctly builds 32-team knockout from 12 groups (2 direct + 8 best thirds)
- **StandingRow.team_id**: Cross-group ranking now possible (enables Annex C third-place selection)

### API
- **GET /api/v1/futures/probabilities**: 48 teams ranked by p_champion DESC, sum constraint validated
- **GET /api/v1/futures/signals**: Pre-computed EV (no re-computation in request), only OUTRIGHT_WINNER market
- **POST /api/v1/odds/manual**: Manual futures odds entry (group-advance, reach-semi, reach-final)

### Frontend
- **FuturesDashboard**: 3-panel layout (champion table 48 teams, group cards A–L, EV signals table)
- **Design system integration**: Card, Badge, FlagLabel, semantic tokens (no hardcoded colors)
- **Data integrity**: All values from API, no client-side arithmetic

### Test Coverage
- **Backend**: 251 tests (Monte Carlo invariants, bracket assembly, API contracts, DB migrations)
- **Frontend**: 240 tests (component rendering, error states, empty states, data formatting)
- **Code quality**: Ruff clean (0 violations), TypeScript strict (tsc -b passes), Vite build successful

### Real-World Results (VPS)
- **Top 3 champion candidates**:
  1. Spain: 20.7%
  2. Argentina: 16.4%
  3. France: 14.1%
- **Colombia**: 4.2% champion, 76.3% advance (strong in group, weaker deep run)
- **All 48 teams**: Monotonic hierarchy holds; no inversions

---

## Specs Synced to Main

| Domain | Action | Details |
|--------|--------|---------|
| futures-montecarlo | Created | 3 requirements (Annex C, StandingRow.team_id, Monte Carlo Simulator) |
| futures-api | Created | 3 requirements (Champion endpoint, Signals endpoint, Migration m9) |
| odds-capture | Updated | +3 ADDED requirements (Futures Odds Capture Path, Futures Capture Audit Log, Manual BetPlay Entry) |
| value-signals | Updated | +2 ADDED requirements (Futures EV De-Vig, Futures Value Signal Emission) with PAPER-always honesty gate |
| dashboard-frontend | Updated | +1 ADDED (R13 Futures Page), +2 MODIFIED (R1 Routing /futures, R7 TypeScript futures types) |

All delta specs merged; stale text corrected; spec constraints validated against implementation.

---

## SDD Cycle Status

✅ **Exploration** — Completed 2026-06-11  
✅ **Proposal** — Completed 2026-06-11  
✅ **Specs** — Completed 2026-06-11 (5 domains, deltas merged)  
✅ **Design** — Completed 2026-06-11 (8 architectural decisions documented)  
✅ **Tasks** — Completed 2026-06-11 (22 tasks across 7 phases)  
✅ **Apply** — Completed 2026-06-11 (4 behavioral bugs fixed, 3 documentation warnings fixed)  
✅ **Verify** — Completed 2026-06-11 (PASS WITH WARNINGS → all issues resolved)  
✅ **Archive** — Completed 2026-06-11  

**Change is ARCHIVED. Ready for next change.**

---

## Successor Phases

Per ADR-0002 (sistema de apuestas +EV), the next planned change is:
- **Phase 8 (LLM Narrators)**: sdd-narrate sub-agents (Anthropic + tool-use) that explain Monte Carlo results, signal diagnostics, Kelly sizing, and calibration to end users
  - `GET /api/v1/futures/{team_id}/explain` → streaming SSE explanation
  - `GET /api/v1/signals/{signal_id}/explain` → signal deep-dive narrative
  - Frontend: ExplainDrawer integration (already stubbed in this change)

---
