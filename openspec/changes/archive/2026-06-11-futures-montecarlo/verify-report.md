# Verification Report

**Change**: futures-montecarlo
**Version**: N/A (engram artifact store)
**Mode**: Standard (no Strict TDD active for this session)

---

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 22 |
| Tasks complete | 18 (Phases 1–6 all [x]) |
| Tasks incomplete in file | 4 (Phase 7: 7.1–7.4) |

**Phase 7 status**: All 4 tasks are functionally complete per git log and test execution, but tasks.md still shows `[ ]`. This is a housekeeping gap, not a functional failure.

- 7.1 Full test suite + ruff + frontend build: ✅ VERIFIED NOW (251 backend / 240 frontend / ruff clean / tsc+vite build)
- 7.2 Top-10 champion probs: Orchestrator confirms VPS producing sane numbers (Spain 20.7%, Colombia 4.2%)
- 7.3 DEPLOY VPS: Orchestrator confirms deployed and serving
- 7.4 Commit + push: `git log` shows conventional commits, `git status` clean, `origin/main` up to date

---

### Build & Tests Execution

**Build (ruff)**: ✅ Passed — `All checks passed!`

**Build (frontend tsc + vite)**: ✅ Passed
```
vite v6.4.3 building for production...
✓ 120 modules transformed.
dist/index.html 0.70 kB | dist/assets/index-*.js 254.62 kB | ✓ built in 1.07s
```

**Backend Tests**: ✅ 251 passed, 0 failed, 1 warning (Starlette deprecation — unrelated)
```
251 passed, 1 warning in 11.49s
```

**Frontend Tests**: ✅ 240 passed, 0 failed
```
31 test files passed — 240 tests in 5.42s
```

**Coverage**: ➖ Not configured with threshold

---

### Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Annex C Data Module | Structural validation (len==495, keys size 8) | `tests/model/test_annex_c.py > test_a1..a5` | ✅ COMPLIANT |
| Annex C Data Module | Opt 1 lookup (EFGHIJKL → expected map) | `tests/model/test_annex_c.py > test_a4_opt1_lookup_is_correct` | ✅ COMPLIANT |
| StandingRow team_id | team_id populated after accumulation | `tests/model/test_standings.py` (modified) | ✅ COMPLIANT |
| Monte Carlo Simulator | Probability sums and ordering (toy tournament) | `test_mc3a_sum_p_champion_near_one`, `test_mc3b_stronger_elo_team_has_higher_p_champion` | ✅ COMPLIANT |
| Monte Carlo Simulator | Reproducibility — same seed → identical output | `test_mc2_seed_42_is_reproducible` | ✅ COMPLIANT |
| Monte Carlo Simulator | Knockout advancement formula P(H)=0.45, P(D)=0.28 → 0.59 | `test_mc1_knockout_proba_formula` | ✅ COMPLIANT |
| Champion Probabilities Endpoint | 48 teams returned, sums to 1, ranked DESC | `tests/api/test_futures.py > test_200_ranked_desc`, `test_p_champion_ranked` | ✅ COMPLIANT |
| Champion Probabilities Endpoint | No predictions → HTTP 200 empty | `tests/api/test_futures.py > test_empty_when_no_predictions` | ✅ COMPLIANT |
| Futures EV Signals Endpoint | EV signal present when p_model > p_fair | `tests/api/test_futures.py > test_200_with_futures_signal` | ✅ COMPLIANT |
| Futures EV Signals Endpoint | No signals when odds not captured | `tests/api/test_futures.py > test_200_empty_when_no_signals` | ✅ COMPLIANT |
| Migration m9 Schema | Unique constraint allows multiple OUTRIGHT_WINNER rows (outcome_team_id distinction) | Round-trip tested in Docker per apply-progress TDD evidence; local tests validate FK path | ⚠️ PARTIAL (no SQLite round-trip for PG enum DDL) |
| Futures Odds Capture Path | Outright odds persisted with outcome_team_id | `tests/ingestion/test_futures_capture.py > test_futures_capture_persists_outright_winner` | ✅ COMPLIANT |
| Futures Odds Capture Path | Unresolved team name discarded + warning | `tests/ingestion/test_futures_capture.py > test_futures_capture_discards_unresolvable_team` | ✅ COMPLIANT |
| Futures Capture Audit Log | SyncLog upsert on repeated capture | `tests/test_futures_jobs.py > test_futures_capture_upserts_not_duplicates` | ✅ COMPLIANT |
| Manual BetPlay Odds Entry | GROUP_ADVANCE persisted (HTTP 201) | `tests/api/test_odds_manual.py > test_manual_odds_group_advance_inserted` | ✅ COMPLIANT |
| Manual BetPlay Odds Entry | MATCH_1X2 rejected (HTTP 422) | `tests/api/test_odds_manual.py > test_manual_odds_rejects_match_1x2` | ✅ COMPLIANT |
| Futures EV — De-Vig N Outcomes | De-vig zero overround [2.00, 3.00, 6.00] | `tests/model/test_futures_signals.py > test_devig_zero_overround` | ✅ COMPLIANT |
| Futures EV — De-Vig N Outcomes | De-vig real overround [1.80, 3.50, 4.50] → [0.5224, 0.2686, 0.2090] | `tests/model/test_futures_signals.py > test_devig_real_overround` | ✅ COMPLIANT |
| Futures Value Signal Emission | EV signal emitted when edge ≥ 0.03 | `tests/model/test_futures_signals.py > test_positive_edge_emits_value_signal` | ✅ COMPLIANT |
| Futures Value Signal Emission | No signal when p_model < p_fair | `tests/model/test_futures_signals.py > test_negative_edge_no_signal` | ✅ COMPLIANT |
| Futures Value Signal Emission | Idempotency — no duplicate on re-run | `tests/model/test_futures_signals.py > test_idempotency_no_duplicate` | ✅ COMPLIANT |
| Futures Value Signal Emission | BacktestRequiredError gate MUST apply | (no test — design chose PAPER-always instead) | ⚠️ PARTIAL — see WARNING #1 |
| R13 — Futures Page (champion table) | Champion table ranked with FlagLabel + % | `frontend/src/pages/FuturesDashboard.test.tsx > FD1` | ✅ COMPLIANT |
| R13 — Futures Page (empty signals) | Empty signals → "Sin señales de futuros disponibles" | `FuturesDashboard.test.tsx > FD3` | ✅ COMPLIANT |
| R13 — Futures Page (error banner) | 500 → ErrorState + "Reintentar" | `FuturesDashboard.test.tsx > FD4` | ✅ COMPLIANT |
| R1 — Routing | /futures accessible from nav | `frontend/src/ui/AppShell.test.tsx` (nav structure) | ✅ COMPLIANT |
| R7 — TypeScript Types | FutureTeamRow, FuturesList, FutureSignal typed | TypeScript build passes (tsc -b exits 0) | ✅ COMPLIANT |

**Compliance summary**: 24/26 scenarios compliant (2 partial — m9 PG enum round-trip + spec honesty gate wording)

---

### Correctness (Static — Structural Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| `app/model/annex_c.py` — 495 entries, validate_annex_c() | ✅ Implemented | Verified live: len=495, validate passes, Opt1 correct |
| `app/model/montecarlo.py` — simulate_tournament() | ✅ Implemented | Vectorized numpy PCG64, correct knockout formula, Annex C lookup |
| `app/model/run_futures.py` loads OLM params (not MC params) | ✅ Implemented | `olm = session.scalar(... ModelVersion.name == '1x2-olm-v1')` confirmed |
| `_build_bracket` returns exactly 32 teams for n_groups==12 | ✅ Implemented | Verified: len(bracket)==32, all unique |
| Monotonic hierarchy p_advance_group ≥ p_reach_sf ≥ p_reach_final ≥ p_champion | ✅ Implemented | `test_reach_semi_final_jerarquia` PASSED; counter logic confirmed |
| Migration m9: autocommit enum ADD, FK column, constraint rebuild | ✅ Implemented | All 4 steps in upgrade(); downgrade() reverses 3→2 (enum drop documented as PG limitation) |
| `uq_prediction_identity` includes `competition_id` | ✅ Implemented | Matches design.md (spec omits it — spec typo, see SUGGESTION #1) |
| `odds_futures_enabled=False` guards scheduler job | ✅ Implemented | config.py default + `if not settings.odds_futures_enabled: return` in jobs.py |
| `GET /futures/probabilities` — no external calls, serve from DB | ✅ Implemented | reads Prediction + Team only via SQLAlchemy; no httpx/requests in path |
| `GET /futures/signals` — no EV re-computation in request path | ✅ Implemented | reads ValueSignal + Prediction + Odds joins only |
| FuturesDashboard — design system primitives only, no hardcoded colors | ✅ Implemented | Only semantic tokens (text-text-muted, border-border, bg-surface) |
| futures_signals.py — PAPER mode always, no BacktestGateError | ✅ Implemented (per design) | Explicitly skips gate; docstring caveat documented; see WARNING #1 |
| Seeded RNG = reproducible/deterministic | ✅ Implemented | `Generator(PCG64(seed))` — test_mc2 confirms byte-identical dicts |

---

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Fixed-lambda Poisson for GD tiebreak (W→1.5/0.8, D→1.1/1.1, L→0.8/1.5) | ✅ Yes | `_GOAL_LAMBDAS` dict in montecarlo.py matches |
| Seeded PCG64 numpy RNG, vectorized 72-match draw | ✅ Yes | `Generator(PCG64(seed))` + `rng.choice`-equivalent vectorized |
| `StandingRow.team_id` as additive field (default 0) | ✅ Yes | `team_id: int = 0` in dataclass |
| New MarketTypes UPPERCASE in PG enum | ✅ Yes | `'REACH_SEMI_FINAL'`, `'REACH_FINAL'` in m9 autocommit block |
| `uq_prediction_identity` with 6 columns including outcome_team_id + competition_id | ✅ Yes | Matches design.md exactly |
| Futures backtest gate skipped — PAPER-always | ✅ Yes (design decision) | Design over-ruled the spec text; see WARNING #1 |
| `OddsCapturePipeline` reused for futures (no new fetch_futures method) | ✅ Yes | Pipeline _MARKET_MAP already had outrights→OUTRIGHT_WINNER |
| `app/model/futures_signals.py` separate from `signals.py` | ✅ Yes | Different JOIN path (competition_id + outcome_team_id vs match_id) |
| Runner pattern: `run_futures.py` with simulate/signals subcommands | ✅ Yes | Matches run_1x2.py pattern |
| Serve from DB only — 0 external calls in GET endpoints | ✅ Yes | Both endpoints read from prediction/value_signal tables |

---

### Adversarial Verification Results

| Check | Result |
|-------|--------|
| `knockout_prob(0.45, 0.28, 0.27)` = 0.59 | ✅ Verified live |
| Seed=42 reproducibility (byte-identical) | ✅ test_mc2 PASSED |
| Monotonic hierarchy p_adv ≥ p_sf ≥ p_final ≥ p_champ | ✅ test_reach_semi_final_jerarquia PASSED |
| `_build_bracket` → exactly 32 qualifiers (n_groups=12) | ✅ Verified live: len=32, all unique |
| `len(ANNEX_C)` = 495 | ✅ Verified live |
| Each ANNEX_C key = 8 distinct A-L letters | ✅ validate_annex_c() passes |
| `sum(p_champion)` ≈ 1.0 | ✅ test_mc3a PASSED |
| run_futures loads 1x2-olm-v1 params (cutpoints/beta) NOT montecarlo-v1 seed/n | ✅ Code confirmed — `olm.params_json` passed to simulate_tournament |
| De-vig [1.80,3.50,4.50] → [0.5224, 0.2686±0.0001, 0.2090] | ✅ Live: [0.5224, 0.2687, 0.2090] within tolerance |
| Futures signals ALWAYS PAPER — no backtest gate | ✅ Confirmed in code + docstring caveat |
| `odds_futures_enabled=False` — NOT in daily loop by default | ✅ Flag confirmed in config.py + job guard |
| FuturesDashboard does NO arithmetic — renders server probs | ✅ Confirmed: all values from API, formatPct() is pure display |
| VPS smoke test (48 teams, monotonic, /futures HTML 200, /signals 200) | ⚠️ DNS unreachable from local; orchestrator evidence accepted |
| Git clean, conventional commits, pushed | ✅ `git status` clean; `git log` shows 7 conventional commits |

---

### Issues Found

**CRITICAL** (must fix before archive):
None

**WARNING** (should fix):

1. **Spec-design coherence — honesty gate** (`openspec/changes/futures-montecarlo/specs/value-signals/spec.md`):
   The spec states: *"The `BacktestRequiredError` honesty gate...MUST apply to futures signals without exception."*
   The design.md explicitly chose to skip this gate ("Skip BacktestGateError; all futures-derived signals flagged PAPER; docstring caveat" — rationale: N=1 WC/year makes historical backtest impossible, honest documentation > false gate). The implementation correctly follows the design decision.
   The spec text is STALE — it was written before the design resolved the tension. Should be updated to reflect the PAPER-always approach before archive.

2. **Phase 7 tasks not checked off in tasks.md**: Tasks 7.1–7.4 remain `[ ]` in `openspec/changes/futures-montecarlo/tasks.md` despite all being complete. Should be marked `[x]` before archive.

**SUGGESTION** (nice to have):

1. **Migration spec typo** (`openspec/changes/futures-montecarlo/specs/futures-api/spec.md`): The constraint definition in the spec omits `competition_id` (lists 5 columns). Design.md and implementation include 6 columns: `(model_version_id, match_id, competition_id, market_type, outcome_code, outcome_team_id)`. The implementation is correct; the spec text should match.

---

### Verdict
**PASS WITH WARNINGS**

All 251 backend tests pass. All 240 frontend tests pass. Ruff clean. Frontend TypeScript + Vite build clean. All adversarial Monte Carlo invariants hold (knockout formula, seed reproducibility, monotonic hierarchy, 32-team bracket, Annex C 495 entries, correct OLM param loading, de-vig math). The PAPER-always honesty invariant is correctly implemented per design. The two warnings are documentation/housekeeping (stale spec text + unchecked task items) — neither blocks correctness or deployment.
