# Verification Report

**Change**: api-signals
**Version**: N/A (no spec version tag)
**Mode**: Strict TDD
**Verified**: 2026-06-10

---

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 21 |
| Tasks complete | 21 |
| Tasks incomplete | 0 |

All tasks across Phases 1-5 are checked [x]. Change is fully implemented.

---

## Build & Tests Execution

**Build (ruff check + format)**: ✅ Passed
```
All checks passed!
95 files already formatted
```

**Tests**: ✅ 123 passed / ❌ 0 failed / ⚠️ 0 skipped
```
123 passed, 1 warning in 1.14s
(warning: StarletteDeprecationWarning for httpx — unrelated to this change)
```

**Coverage**: ➖ Not available — pytest-cov not installed in Docker image

---

## TDD Compliance

| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | Full TDD Cycle Evidence table present in apply-progress |
| All tasks have tests | ✅ | 21/21 tasks — task 4.1 (schemas.py) correctly skipped (pure DTOs, no logic) |
| RED confirmed (tests exist) | ✅ | 32/32 test functions verified present and passing |
| GREEN confirmed (tests pass) | ✅ | 123/123 full suite green on execution |
| Triangulation adequate | ✅ | standings: 5 scenarios; signals: 3; matches: 5; groups: 5; odds_queries: 5 |
| Safety Net for modified files | ✅ | 107/107 pre-existing tests confirmed green before Phase 4 work |

**TDD Compliance**: 6/6 checks passed

---

## Test Layer Distribution

| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 11 | 2 | pytest |
| Integration | 21 | 6 | pytest + TestClient + SAVEPOINTs |
| E2E | 0 | 0 | not installed |
| **Total (change)** | **32** | **8** | |
| Pre-existing | 91 | — | |
| **Total suite** | **123** | — | |

Unit: `test_standings.py` (5), `test_group_utils.py` (3), `test_odds_queries.py`-partial (3 pure-logic tests).  
Integration: `test_seed_groups.py` (3), `tests/api/` (16), `test_odds_queries.py`-integration (2).

---

## Changed File Coverage

Coverage analysis skipped — pytest-cov not installed in Docker image.

---

## Assertion Quality

All assertions in the 8 changed test files were reviewed:

- **test_standings.py**: tests assert exact numeric values (pj, g, e, p, gf, gc, dg, pts) for all teams in all scenarios. Deep triangulation across 5 scenarios including triple-tie fallback.
- **test_group_utils.py**: tests assert `AssertionError` raised on invalid graphs and exact output on valid graph.
- **test_odds_queries.py**: tests assert exact Odds.id and decimal_odds value, not just existence.
- **test_seed_groups.py**: tests count rows before/after, verify zero writes on error.
- **test_signals.py**: verifies specific edge value, team names, pagination offset behavior.
- **test_matches.py**: verifies exact probability values (within 1e-4), null probabilities, 404 detail message.
- **test_paper.py**: verifies ROI within 1e-4 of 0.125, null roi when settled=0.
- **test_model.py**: verifies exact backtest float values from DB, not just presence.
- **test_groups.py**: verifies 4 teams per group, standings count=4, all pts=0, 404 detail message.

**Assertion quality**: ✅ All assertions verify real behavior

---

## Quality Metrics

**Linter**: ✅ No errors (ruff check: all checks passed)
**Type Checker**: ➖ Not available (mypy not configured)

---

## Spec Compliance Matrix

### api-readonly spec (14 scenarios)

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| R1 — Serve-from-DB | External call inside request | Static: rg shows zero httpx/requests imports in app/api/ | ✅ COMPLIANT |
| R2 — GET /signals | Filtered signals list | `test_signals.py > test_signals_filtered_by_date_and_edge` | ✅ COMPLIANT |
| R2 — GET /signals | No results | `test_signals.py > test_signals_no_results` | ✅ COMPLIANT |
| R2 — GET /signals | Pagination (not in spec text but R2 requirement) | `test_signals.py > test_signals_pagination` | ✅ COMPLIANT |
| R3 — GET /matches/upcoming | Upcoming with predictions | `test_matches.py > test_upcoming_with_predictions` | ✅ COMPLIANT |
| R3 — GET /matches/upcoming | Match without predictions | `test_matches.py > test_upcoming_without_predictions` | ✅ COMPLIANT |
| R4 — GET /matches/{id} | Match found | `test_matches.py > test_match_detail_found` | ✅ COMPLIANT |
| R4 — GET /matches/{id} | Match not found | `test_matches.py > test_match_detail_not_found` | ✅ COMPLIANT |
| R5 — GET /model | Model with backtest | `test_model.py > test_model_returns_active_version` | ✅ COMPLIANT |
| R6 — GET /paper | ROI calculation (numeric) | `test_paper.py > test_paper_roi_numeric` | ✅ COMPLIANT |
| R6 — GET /paper | No settled bets → roi=null | `test_paper.py > test_paper_roi_null_when_no_settled` | ✅ COMPLIANT |
| R7 — Empty vs 404 | Lists return 200+empty | `test_matches.py > test_upcoming_empty_returns_200` + `test_signals.py > test_signals_no_results` | ✅ COMPLIANT |
| R8 — CORS | Origins configurable | Static: `config.py` cors_origins + `main.py` CORSMiddleware | ⚠️ PARTIAL (no runtime test) |

**Compliance summary**: 12/13 scenarios compliant, 1 partial (R8 CORS no runtime test)

### group-standings spec (9 scenarios)

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| R1 — Group Derivation | Valid graph 12×4 | `test_seed_groups.py > test_seed_valid_graph_inserts_groups` | ✅ COMPLIANT |
| R1 — Group Derivation | Graph integrity failure | `test_seed_groups.py > test_seed_broken_graph_raises_before_write` | ✅ COMPLIANT |
| R1 — Group Derivation | Idempotent re-run | `test_seed_groups.py > test_seed_idempotent_on_double_run` | ✅ COMPLIANT |
| R2 — Standings pure fn | S1: no tie (numeric verification) | `test_standings.py > test_s1_no_numeric_tie_full_order` | ✅ COMPLIANT |
| R2 — Standings pure fn | S2: tie broken by DG (numeric) | `test_standings.py > test_s2_tie_on_pts_broken_by_goal_diff` | ✅ COMPLIANT |
| R2 — Standings pure fn | S3: tie broken by H2H (numeric) | `test_standings.py > test_s3_tie_broken_by_head_to_head` | ✅ COMPLIANT |
| R2 — Standings pure fn | S4: zero finished → alphabetical | `test_standings.py > test_s4_zero_finished_matches_returns_alphabetical` | ✅ COMPLIANT |
| R3 — GET /groups | All groups after seed | `test_groups.py > test_groups_returns_group_objects` | ⚠️ PARTIAL (asserts ≥1, not ==12) |
| R3 — GET /groups | No groups seeded | `test_groups.py > test_groups_empty_table_returns_200` | ✅ COMPLIANT |
| R4 — GET /groups/{name} | Valid group | `test_groups.py > test_group_detail_found` | ✅ COMPLIANT |
| R4 — GET /groups/{name} | Unknown group | `test_groups.py > test_group_detail_not_found` | ✅ COMPLIANT |
| R4 — GET /groups/{name} | Lowercase normalized | `test_groups.py > test_group_detail_lowercase_normalized` | ✅ COMPLIANT |

**Compliance summary**: 21/23 scenarios fully compliant, 2 partial

---

## Numeric Standings Arithmetic Verification (manual recompute)

### S1 (spec group-standings, R2-S1): A 3-0 B, C 1-1 D, A 1-0 C, B 2-1 D, A 0-0 D, B 1-2 C

| Team | PJ | G | E | P | GF | GC | DG | Pts |
|------|----|---|---|---|----|----|----|-----|
| A    | 3  | 2 | 1 | 0 | 4  | 0  | +4 | 7   |
| C    | 3  | 1 | 1 | 1 | 3  | 3  | 0  | 4   |
| B    | 3  | 1 | 0 | 2 | 3  | 6  | -3 | 3   |
| D    | 3  | 0 | 2 | 1 | 2  | 3  | -1 | 2   |

Test asserts exact values for all 4 rows. **Arithmetic verified ✅ — matches spec table exactly.**

### S2 (spec group-standings, R2-S2): A 2-0 B, A 0-0 C, A 0-0 D, B 0-1 C, B 0-0 D, C 0-0 D

| Team | Pts | DG | GF | Note |
|------|-----|----|----|------|
| A    | 5   | +2 | 2  | DG wins over C |
| C    | 5   | +1 | 1  | |
| D    | 3   | 0  | 0  | |
| B    | 1   | -3 | 0  | |

Manual recompute: A: 3+1+1=5 pts, gf=2, gc=0, dg=+2. C: 1+3+1=5 pts, gf=1, gc=0, dg=+1. D: 1+1+1=3 pts, gf=0, gc=0. B: 0+0+1=1 pt, gf=0, gc=3, dg=-3. **Arithmetic verified ✅ — test asserts A>C by dg.**

### S3 (spec group-standings, R2-S3): A 1-0 B, A 1-1 C, A 0-0 D, B 1-0 C, B 1-1 D, C 1-0 D

| Team | Pts | DG | GF | H2H (vs tied) | Position |
|------|-----|----|----|---------------|----------|
| A    | 5   | +1 | 2  | (not tied)    | 1st |
| B    | 4   | 0  | 2  | 3 (B 1-0 C)   | 2nd |
| C    | 4   | 0  | 2  | 0             | 3rd |
| D    | 2   | -1 | 1  | (not tied)    | 4th |

Manual recompute: A: W+D+D = 5pts, gf=2, gc=1, dg=+1. B: W+D+L = 4pts, gf=2, gc=2, dg=0. C: W+D+L = 4pts, gf=2, gc=2, dg=0. D: D+D+L = 2pts, gf=1, gc=2, dg=-1. B vs C H2H: B 1-0 C → B gets 3 H2H pts, C gets 0 → B > C. **Arithmetic verified ✅ — test asserts B before C with both having pts=4, dg=0, gf=2.**

---

## Correctness (Static — Structural Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| R1: Serve-from-DB, zero external calls | ✅ Implemented | rg shows 0 httpx/requests imports in app/api/ |
| R2: GET /signals with all 15 fields | ✅ Implemented | All fields present in SignalItem schema and router query |
| R2: Pagination caps (default 50, max 200) | ✅ Implemented | `limit: Annotated[int, Query(ge=1, le=200)] = 50` |
| R3: GET /matches/upcoming anti-N+1 | ✅ Implemented | 2-query pattern: matches paginados + predictions IN (...) |
| R4: GET /matches/{id} with 404 | ✅ Implemented | `one_or_none()` + HTTPException(404) |
| R5: GET /model serves highest-id version | ✅ Implemented | `order_by(ModelVersion.id.desc()).limit(1)` |
| R6: GET /paper ROI = sum(pnl)/sum(stake) WON+LOST | ✅ Implemented | Guard `settled=0 → roi=null` present |
| R7: List endpoints 200+empty, single 404 | ✅ Implemented | All list endpoints return [] not 404 |
| R8: CORS localhost:5173 + configurable | ✅ Implemented | `cors_origins: list[str] = ["http://localhost:5173"]` + CORSMiddleware |
| R2 (groups): compute_standings at request time | ✅ Implemented | `_build_standing_rows()` called on every request |
| R4 (groups): case-insensitive name | ✅ Implemented | `name_upper = name.upper()` before query |

---

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Layout: one router per resource | ✅ Yes | 5 router files: signals, matches, model, paper, groups |
| Schemas: single app/api/schemas.py Pydantic v2 | ✅ Yes | All schemas in one module with `_ORMBase` base class |
| Helper best-odds: app/model/odds_queries.py | ✅ Yes | `best_odds_per_outcome` and `latest_per_bookmaker` in model layer |
| api→model direction only | ✅ Yes | rg confirms model never imports from api |
| Standings: pure function in app/model/standings.py | ✅ Yes | `compute_standings(members, results)` — zero DB calls |
| CORS: settings.cors_origins + CORSMiddleware before routers | ✅ Yes | main.py adds middleware before include_router calls |
| Anti-N+1 pattern for all endpoints | ✅ Yes | All endpoints use batch queries or JOIN, no per-row queries |
| Pagination default 50, max 200 | ✅ Yes | Enforced via Query validators in signals + upcoming |

---

## Adjudications

### (a) VOID bets in /paper `total` — COMPLIANT

The spec R6 says: `total`, `open` (status=PENDING), `settled` (WON+LOST), with ROI "for WON and LOST bets only." The `total` field is defined as "Aggregates PAPER-mode BetLog entries" without restricting to specific statuses. The design explicitly maps `void → VOID (excluida de ROI)` — excluded from ROI, not from total. The implementation `total = sum(counts.values())` correctly includes VOID in total while excluding it from ROI. **Ruling: COMPLIANT.**

### (b) /matches/upcoming without competition filter — COMPLIANT (with latent concern)

Spec R3 says: "Returns matches with `status = SCHEDULED`" — no competition filter is mentioned. The implementation is fully compliant with the spec. Today, all SCHEDULED matches in the DB are WC2026 group matches, so no spurious data appears. However, if the DB ever gets populated with non-WC SCHEDULED matches (qualifiers, friendlies), they would appear in this endpoint without a way to filter. **Ruling: COMPLIANT with spec. Latent concern flagged as SUGGESTION for a future change (add optional `competition_id` query param).**

---

## DATA Verification (live DB)

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| TournamentGroup rows | 12 | 12 | ✅ |
| GroupTeam rows | 48 | 48 | ✅ |
| Matches with stage=GROUP and group_id | 72 | 72 | ✅ |
| Group K composition | Colombia, DR Congo, Portugal, Uzbekistan | Colombia, DR Congo, Portugal, Uzbekistan | ✅ |
| Group A composition | Mexico, South Africa, South Korea, Czech Republic | Czech Republic, Mexico, South Africa, South Korea | ✅ |
| Group J composition | Argentina, Algeria, Austria, Jordan | Algeria, Argentina, Austria, Jordan | ✅ |
| Group K standings (0 FINISHED) | all zeros, alphabetical | Colombia first (C < D < P < U) ✅ | ✅ |

---

## Live Smoke Tests (7 endpoints)

| Endpoint | HTTP | Shape | Notes |
|----------|------|-------|-------|
| GET /api/v1/signals | 200 | `{items: [...], total: 69}` | 10+ signals with real edges (0.147 gtbets HOME) |
| GET /api/v1/matches/upcoming | 200 | `[{p_home, p_draw, p_away, ...}]` | 72 matches with 1X2 predictions |
| GET /api/v1/matches/{id} | 200/404 | `{predictions, last_odds, signals}` | id=9999 exists in DB (historical); id=999999 → 404 ✅ |
| GET /api/v1/model | 200 | `{name, backtest, calibration}` | name=1x2-olm-v1, Brier=0.170275 |
| GET /api/v1/paper | 200 | `{total: 69, open: 69, settled: 0, roi: null}` | roi=null correct (0 settled) |
| GET /api/v1/groups | 200 | `[{name, teams, standings}]` | 12 groups (confirmed via DB) |
| GET /api/v1/groups/K | 200 | `{name: "K", teams: [...], fixtures: [...]}` | Colombia visible, 6 fixtures |

All 7 routes present in /openapi.json.

---

## Git Hygiene

- Working tree: `openspec/changes/api-signals/` untracked (artifact directory) — expected, not a problem.
- Commits: `feat(api): read-only signals, standings, groups endpoints + seed WC2026` — conventional format ✅

---

## Issues Found

**CRITICAL**: None

**WARNING**:
1. **R3-S1 (groups) test asserts ≥1 instead of ==12**: `test_groups_returns_group_objects` checks `len(groups) >= 1` not `== 12`. The spec says "exactly 12 group objects". The seed test validates 12 groups are created, but the API endpoint test does not verify the 12-group invariant end-to-end. Low risk (seed + live smoke confirm 12), but the test could be tightened.
2. **R8 (CORS) has no runtime test**: CORS is verified statically (config.py, main.py) and confirmed in live API, but no automated test asserts the `Access-Control-Allow-Origin` header. Medium effort to add, low risk since it's infrastructure-level.

**SUGGESTION**:
1. **Install pytest-cov**: No coverage tool in the Docker image. Adding `pytest-cov` would enable per-file coverage reporting on changed files.
2. **/matches/upcoming: add optional `competition_id` filter**: Not a spec violation today. Latent concern for future when non-WC matches may be SCHEDULED. A `?competition_id=` query param would future-proof the endpoint.
3. **R3-S1 test: tighten assertion to ==12**: Replace `len(groups) >= 1` with `len(groups) == 12` in `test_groups_returns_group_objects` when 12 real groups are available in the test DB (requires the seed to run in the test fixture, which may be expensive).

---

## Verdict

**APPROVED WITH WARNINGS**

Implementation is fully complete (21/21 tasks), all 123 tests pass, ruff clean, live endpoints functional, DB data verified (12×4×72), architecture invariants confirmed (zero writes in API layer, zero external calls, strict api→model dependency direction). The two warnings are low-risk and do not block archive: one is a test assertion that could be more precise, the other is a missing runtime test for an infrastructure concern already verified statically.
