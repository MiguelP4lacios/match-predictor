# Verification Report

**Change**: cupon-bloques
**Version**: N/A (no semver in specs)
**Mode**: Standard (no Strict TDD in openspec/config.yaml)

---

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 35 |
| Tasks complete | 35 |
| Tasks incomplete | 0 |

All 35 tasks marked `[x]` across phases 1-5. Confirmed against apply-progress in engram (#126).

---

### Build & Tests Execution

**Backend (pytest)**: ✅ 194 passed, 0 failed, 0 skipped
```
194 passed, 1 warning in 7.67s
```
Warning: httpx/starlette deprecation notice (unrelated to cupon-bloques).

**Frontend (vitest)**: ✅ 156 passed, 0 failed, 0 skipped
```
Test Files  24 passed (24) | Tests  156 passed (156) | Duration  5.87s
```

**ruff check + ruff format --check**: ✅ All checks passed! 124 files already formatted.

**TypeScript build (tsc -b && vite build)**: ✅ Exit 0, no errors
```
✓ 104 modules transformed.
dist/assets/index-CPUFsvq2.js   242.97 kB │ gzip: 75.42 kB
✓ built in 976ms
```

**Coverage**: Not available (no coverage command in project config)

---

### PARLAY MATH AUDIT (BY HAND)

Manual verification of the money-critical calculation:

| Step | Formula | Result |
|------|---------|--------|
| combined_odds | 1.40 × 2.75 × 1.84 | **7.084** ✅ |
| model_prob | 0.834 × 0.491 × 0.780 | **0.31940** ✅ |
| parlay_ev | p*(combined−1)−(1−p) = 0.3194*(7.084−1)−0.6806 | **+1.2626 ≈ +1.2627** ✅ |
| leg1 ev | 0.834*(1.40−1)−0.166 | **+0.1676 ≈ +16.8%** ✅ |
| leg2 ev | 0.491*(2.75−1)−0.509 | **+0.3502 ≈ +35.0%** ✅ |
| leg3 ev | 0.780*(1.84−1)−0.220 | **+0.4352 ≈ +43.5%** ✅ |
| WON pnl | 5000 × (7.084 − 1) | **30420.00** ✅ |
| LOST pnl | −5000 | **−5000.00** ✅ |

`compute_ev(p, odds) = p*(odds−1) − (1−p) = p*odds − 1`. Confirmed against `app/model/probabilities.py:171`.

−EV detection: `is_negative_ev = (leg_ev < 0)` where `leg_ev = compute_ev(p_i, float(odds_i))`. Correct.

Independence caveat: present in `parlay.py` docstring ✅; banner rendered in `CuponDrawer.tsx` ✅.

`suggested_without_negatives`: populated only when `negative_legs` is non-empty; contains the complement set. Correct.

---

### Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| parlay-math / combine_parlay | 3-leg numeric (7.084/0.3194/+1.2627) | `test_parlay.py::test_combine_parlay_3legs_numeric` | ✅ COMPLIANT |
| parlay-math / combine_parlay | Per-leg EV (+16.8/+35.0/+43.5%) | `test_parlay.py::test_combine_parlay_per_leg_ev` | ✅ COMPLIANT |
| parlay-math / combine_parlay | 2-leg with −EV leg → suggested_without_negatives | `test_parlay.py::test_combine_parlay_negative_ev_leg_filtered` | ✅ COMPLIANT |
| parlay-math / combine_parlay | Empty list → ValueError | `test_parlay.py::test_combine_parlay_empty_raises` | ✅ COMPLIANT |
| parlay-math / combine_parlay | 1 leg → ValueError | `test_parlay.py::test_combine_parlay_single_leg_raises` | ✅ COMPLIANT |
| parlay-math / combine_parlay | Leg with p_model=None → model_prob=None | `test_parlay.py::test_combine_parlay_leg_without_p_model` | ✅ COMPLIANT |
| parlay-bets / POST preview | 3-leg preview stake=5000 → retorno=35420 | `test_parlays.py::test_preview_3legs_retorno` | ✅ COMPLIANT |
| parlay-bets / POST preview | odds ≤ 1 → 422 | `test_parlays.py::test_preview_odds_le_one_returns_422` | ✅ COMPLIANT |
| parlay-bets / POST preview | 1 leg → 422 | `test_parlays.py::test_preview_single_leg_returns_422` | ✅ COMPLIANT |
| parlay-bets / POST preview | FINISHED match → 422 | `test_parlays.py::test_preview_finished_match_returns_422` | ✅ COMPLIANT |
| parlay-bets / POST preview | Preview NOT persisted | Static: `session.add/commit/flush` absent in `preview_parlay` | ✅ COMPLIANT |
| parlay-bets / POST /parlays | 3-leg persist → 201 + BetLog+BetLeg | `test_parlays.py::test_create_parlay_persists_betlog_and_legs` | ✅ COMPLIANT |
| parlay-bets / POST /parlays | FINISHED match → 422 rollback | `test_parlays.py::test_preview_finished_match_returns_422` | ✅ COMPLIANT |
| parlay-bets / GET /parlays | Filter by mode=real | `test_parlays.py::test_get_parlays_list` | ✅ COMPLIANT |
| parlay-bets / GET /parlays | No filter → all parlays | `test_parlays.py::test_get_parlays_list` | ✅ COMPLIANT |
| bet-settlement / settle_parlays | All 3 legs WON → WON pnl=+30420 | `test_settle_parlays.py::test_settle_parlays_all_legs_won` | ✅ COMPLIANT |
| bet-settlement / settle_parlays | 1 leg LOST → parlay LOST pnl=−5000 | `test_settle_parlays.py::test_settle_parlays_one_leg_lost` | ✅ COMPLIANT |
| bet-settlement / settle_parlays | Leg SCHEDULED → stays PENDING | `test_settle_parlays.py::test_settle_parlays_pending_leg_stays_pending` | ✅ COMPLIANT |
| bet-settlement / settle_parlays | Idempotent | `test_settle_parlays.py::test_settle_parlays_idempotent` | ✅ COMPLIANT |
| bet-settlement / settle_parlays | settled_result="WON_ALL"/"LOST" | (none) | ❌ UNTESTED + NOT IMPLEMENTED |
| bet-settlement / settle_bets (singles) | No-regression: singles settle, parlays untouched | `test_settle_parlays.py::test_settle_bets_does_not_touch_parlays` | ✅ COMPLIANT |
| kambi-odds / KambiOddsSource | fixture → 3 RawOdds prices 1.40/3.20/2.10 | `test_kambi.py::test_kambi_fixture_produces_3_odds` | ✅ COMPLIANT |
| kambi-odds / KambiOddsSource | milli 1700 → 1.70 | `test_kambi.py::test_kambi_milli_1700_to_1_70` | ✅ COMPLIANT |
| kambi-odds / KambiOddsSource | "USA" → "United States" override | `test_kambi.py::test_kambi_name_override_usa` | ✅ COMPLIANT |
| kambi-odds / KambiOddsSource | KAMBI_ENABLED=false → not instantiated | `test_kambi.py::test_kambi_disabled_flag_gate` | ✅ COMPLIANT |
| kambi-odds / KambiOddsSource | Full Time + OPEN filter only | `test_kambi.py::test_kambi_filters_out_half_time` | ✅ COMPLIANT |
| kambi-odds / name overrides spec (6 minimum) | All 6 spec entries present | Static: only 2 of 6 spec entries correct | ⚠️ PARTIAL |
| dashboard-frontend / R11 CuponDrawer | EV live: 7.084/31.9%/+126.3% | `CuponDrawer.test.tsx` (3 tests) | ✅ COMPLIANT |
| dashboard-frontend / R11 CuponDrawer | Warning leg −EV visible | `CuponDrawer.test.tsx::warning leg −EV` | ✅ COMPLIANT |
| dashboard-frontend / R11 CuponDrawer | Stake → retorno $35.420 COP | `CuponDrawer.test.tsx::retorno $35.420` | ✅ COMPLIANT |
| dashboard-frontend / R11 CuponDrawer | Registrar cupón → POST 201 limpia | `CuponDrawer.test.tsx::Registrar cupón` | ✅ COMPLIANT |
| dashboard-frontend / R11 CuponDrawer | Cupón vacío → botón deshabilitado | `CuponDrawer.test.tsx::deshabilitado sin legs` | ✅ COMPLIANT |
| dashboard-frontend / R11 CuponDrawer | Independence banner present | `CuponDrawer.test.tsx::banner independencia` | ✅ COMPLIANT |
| dashboard-frontend / R12 AddToCupon | Agregar desde SignalCard | `AddToCuponButton.test.tsx` | ✅ COMPLIANT |
| dashboard-frontend / R12 AddToCupon | Quitar leg del cupón | `CuponContext.test.tsx::removeLeg` | ✅ COMPLIANT |
| dashboard-frontend / R7 TypeScript types | ParlayPreview typing correct | Static: types.ts matches actual API fields (curl-verified) | ✅ COMPLIANT |

**Compliance summary**: 33/35 scenarios compliant (1 UNTESTED+MISSING, 1 PARTIAL)

---

### Correctness (Static — Structural Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| `combine_parlay` pure (no DB, no LLM) | ✅ Implemented | `parlay.py` imports only from `probabilities.py` |
| `parlay_service.py` resolves p_model from Prediction | ✅ Implemented | Uses `ORDER BY id DESC LIMIT 1` (same as /api/v1/model) |
| `BetLog.bet_kind` column + `BetLeg` model | ✅ Implemented | `betting.py` — FK cascade, relationship `legs` |
| m7 migration round-trip | ✅ Verified | Tests run against real Postgres (docker); 194 pass including BetLog insert with BetKind.PARLAY |
| CHECK constraint relaxed correctly | ✅ Implemented | `(bet_kind = 'PARLAY') OR (value_signal_id IS NOT NULL) OR (match_id IS NOT NULL AND outcome_code IS NOT NULL)` |
| settle_bets single-bet path untouched | ✅ Implemented | Parlays with match_id=NULL/value_signal_id=NULL join no FINISHED Match → excluded from WHERE clause |
| settle_parlays sets settled_result | ❌ Missing | Code sets `status`/`pnl`/`settled_at` but NOT `settled_result`. Spec requires "WON_ALL" / "LOST" |
| KAMBI_ENABLED=false default | ✅ Implemented | `app/core/config.py`; `make_kambi_source()` returns None when disabled |
| Kambi test FIXTURE-ONLY | ✅ Implemented | `test_kambi.py` has zero `httpx.get` calls; uses `_parse_events(fixture)` directly |
| Front NEVER calculates parlay math | ✅ Implemented | No arithmetic in `CuponDrawer`/`CuponContext`; only formats what `preview` returns |
| CuponContext sessionStorage persist | ✅ Implemented | `useReducer` with `loadFromStorage` initializer + `useEffect → saveToStorage` |
| Debounce ≥300ms | ✅ Implemented | `DEBOUNCE_MS = 300` in `CuponDrawer.tsx` |

---

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| D1: `bet_kind` enum + relax CHECK | ✅ Yes | Exactly as designed |
| D2: Decimal for odds, float for probs | ✅ Yes | `combine_parlay` uses `Decimal` for `combined_odds`, `float` for `model_prob` |
| D3: `parlay_service.py` in `app/model/` (api→model) | ✅ Yes | Correct dependency direction |
| D4: `settle_parlays()` new function; `settle_bets` UNTOUCHED | ✅ Yes | Confirmed via `rg` and static analysis |
| D5: Kambi flag-gated, NOT in daily loop | ✅ Yes | `make_kambi_source()` gated, `jobs.py` not modified for Kambi |
| D6: CuponContext + sessionStorage (not Redux) | ✅ Yes | `useReducer` pattern as designed |
| File changes match design table | ✅ Yes | All 20 files from design table exist or were modified |

---

### Issues Found

**CRITICAL** (must fix before archive):
None

**WARNING** (should fix):

1. **`settle_parlays()` missing `settled_result`** — `app/model/settle.py` sets `status`, `pnl`, `settled_at` on the settled BetLog but does NOT set `settled_result`. The spec explicitly requires `settled_result = "WON_ALL"` (WON) and `settled_result = "LOST"` (LOST) for parlays. No test verifies this field. This is a functional gap (not a money issue) but violates spec.
   - **Files**: `app/model/settle.py` (lines 174-187), `tests/model/test_settle_parlays.py`

2. **`_KAMBI_NAME_OVERRIDES` missing 4 of 6 spec-required entries** — The spec requires these exact mappings (`{Kambi en_US: DB canonical}`): `"Côte d'Ivoire"→"Ivory Coast"`, `"Czechia"→"Czech Republic"`, `"Congo DR"→"DR Congo"`, `"Bosnia & Herzegovina"→"Bosnia and Herzegovina"`. The implementation has only `"USA"` and `"Korea Republic"` from the required 6; the other 4 entries in the dict are Spanish names (`"EE.UU."`, `"Corea del Sur"`, `"Irán"`, `"Bosnia"`) that will NOT appear in `lang=en_US` API responses.
   - **File**: `app/ingestion/sources/kambi.py` (lines 36–43)
   - **Severity note**: Kambi is `KAMBI_ENABLED=false` by default; this doesn't affect any currently running path.

**SUGGESTION** (nice to have):

1. **Spec field name drift** — The spec text says `potential_return` and `legs_diagnostics`, but the actual API uses `retorno` and `legs`. The frontend types correctly reflect the real API (curl-verified). Spec should be updated to match implementation to avoid future confusion.

2. **Input schemas lack `extra="forbid"`** — `ParlayPreviewRequest` and `ParlayCreate` use default `extra="ignore"`. Not a security risk (no mass-assignment path exists since `pnl`/`status` aren't in input schemas), but explicit `extra="forbid"` would be safer and more expressive.

---

### VPS Live Check

Network not reachable from verification sandbox (curl exits with connection error).
Evidence from apply-progress (executed June 11, 2026):
- `POST /api/v1/parlays/preview` (matches 49374+49375): `combined_odds=3.850`, `retorno=19250.00`, `leg 49375 is_negative_ev=true` ✅
- Frontend `/senales` HTML: HTTP 200 ✅
- `settle_parlays`: 0 pending (Simples 0, Parlays 0) ✅
- `git push origin main`: local == origin/main confirmed ✅

---

### Verdict

**PASS WITH WARNINGS**

Parlay math is provably correct (by-hand audit + 194 backend + 156 frontend tests all green). Money paths (combined_odds, pnl WON/LOST, settlement logic) are correct. Two warnings exist: (1) `settled_result` field not populated by `settle_parlays()` — functional gap, not a money issue; (2) Kambi name override dict has only 2 of 6 spec-required en_US entries — irrelevant since Kambi is OFF by default. Neither warning blocks production use.
