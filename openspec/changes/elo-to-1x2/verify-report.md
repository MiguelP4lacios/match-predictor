# Verification Report: elo-to-1x2

**Change**: elo-to-1x2
**Version**: specs/model-1x2 + specs/value-signals (no version tag)
**Mode**: Strict TDD
**Date**: 2026-06-10
**Verifier**: sdd-verify sub-agent

---

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 23 |
| Tasks complete | 23 |
| Tasks incomplete | 0 |

All 23 tasks (phases 1–5) marked `[x]` in tasks.md. ✅

---

## Build & Tests Execution

**Build (ruff)**: ✅ All checks passed — `docker compose run --rm api ruff check .`

**Tests**: ✅ 91 passed / 0 failed / 0 skipped
```
91 passed in 0.49s
```

**Coverage**: ➖ Not available — `pytest-cov` not installed in project dependencies.

---

## TDD Compliance

| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | Found in apply-progress engram #69 |
| All tasks have tests | ✅ | 27 change-specific tests across 5 files |
| RED confirmed (tests exist) | ✅ | 5/5 test files verified in repo |
| GREEN confirmed (tests pass) | ✅ | 27/27 change-specific tests pass on execution |
| Triangulation adequate | ✅ / ⚠️ | 4 of 5 task groups triangulated; SC-OLM-05 single-assertion |
| Safety Net for modified files | ✅ | All new files — N/A (new) is correct |

**TDD Compliance**: 5/5 checks passed (with minor WARNING on SC-OLM-05 assertion depth — see Issues)

---

## Test Layer Distribution

| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit (pure, no DB) | 19 | 3 | pytest + math |
| Integration (db_session SAVEPOINT) | 8 | 2 | pytest + SQLAlchemy |
| E2E | 0 | 0 | not installed |
| **Total (change-related)** | **27** | **5** | |

---

## Changed File Coverage

Coverage analysis skipped — pytest-cov not installed.

Static evidence (rg/read): all changed files have associated tests exercising their public API.

---

## Assertion Quality

| File | Line | Assertion | Issue | Severity |
|------|------|-----------|-------|----------|
| `tests/test_predict_integration.py` | 99–108 | `count == 3` + `all(not p.low_confidence for p in preds)` | SC-OLM-05 (anti-look-ahead): verifies predictions exist and low_confidence=False, but does NOT verify the actual rating used was 1650 (not 1670). A look-ahead bug would still pass this test since both ratings produce non-null, non-low-confidence output. | WARNING |
| `tests/test_probabilities.py` | 83 | `probs["draw"] > 0.0` | Reparam check verifies draw>0 not the actual α₂>α₁ arithmetic. Valid but weaker than asserting specific cutpoint ordering. | WARNING |
| `tests/test_gate_integration.py` | 279 | `select(func.count(ValueSignal.id))` (global count) | SC-VS-08 idempotency: uses global count rather than scoped. Mathematically correct (compares count_after_first == count_after_second across the SAVEPOINT), but fragile if other test-session data bleeds. | WARNING |

**Assertion quality**: 0 CRITICAL, 3 WARNING

---

## Spec Compliance Matrix

### model-1x2 Scenarios

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| OLM Core | SC-OLM-01: forward pass (diff=100, non-neutral) | `test_probabilities.py > test_olm_forward_pass_nonneutral_p_away/draw/home` | ✅ COMPLIANT |
| OLM Core | SC-OLM-01: sum=1.0 | `test_probabilities.py > test_olm_sum_to_one` | ✅ COMPLIANT |
| OLM Core | SC-OLM-02: neutral flag reduces P(H) | `test_probabilities.py > test_olm_neutral_flag_reduces_home_prob` | ✅ COMPLIANT |
| OLM Core | Reparam cutpoint ordering | `test_probabilities.py > test_cutpoint_ordering_via_reparam` | ✅ COMPLIANT |
| OLM Core | P(H) monotone increasing | `test_probabilities.py > test_p_home_monotone_increasing_with_elo_diff` | ✅ COMPLIANT |
| OLM Core | P(A) monotone decreasing | `test_probabilities.py > test_p_away_monotone_decreasing_with_elo_diff` | ✅ COMPLIANT |
| Binned Baseline | SC-OLM-03: draw-rate monotone non-increasing | `test_baseline.py > test_draw_rate_monotone_non_increasing` | ✅ COMPLIANT |
| Binned Baseline | SC-OLM-04: low-support bucket → NoSupportError | `test_baseline.py > test_low_support_bucket_raises_no_support_error` | ✅ COMPLIANT |
| Point-in-Time Lookup | SC-OLM-05: anti-look-ahead (1650 not 1670) | `test_predict_integration.py > test_predict_uses_rating_strictly_before_match_date` | ⚠️ PARTIAL |
| Point-in-Time Lookup | SC-OLM-06: no prior rating → 1500 + low_confidence=True | `test_predict_integration.py > test_predict_defaults_to_1500_when_no_prior_rating` | ✅ COMPLIANT |
| Backtest Gate | SC-OLM-07: Brier≥0.2222 → BacktestGateError with metrics | `test_gate_integration.py > test_gate_raises_backtest_gate_error_when_brier_too_high` | ✅ COMPLIANT |
| Prediction Persistence | SC-OLM-08: exactly 3 rows, sum=1.0, idempotent | `test_predict_integration.py > test_predict_idempotent_two_runs` | ✅ COMPLIANT |

### value-signals Scenarios

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Proportional De-Vig | SC-VS-01: numeric verification (H/D/A fair probs + sum=1) | `test_signals_pure.py > test_devig_*probability* + test_devig_sums_to_one` | ✅ COMPLIANT |
| EV and Edge | SC-VS-02: EV=0.3560 | `test_signals_pure.py > test_ev_numeric_verification` | ✅ COMPLIANT |
| EV and Edge | EV negative triangulation | `test_signals_pure.py > test_ev_negative_when_underdog_with_bad_odds` | ✅ COMPLIANT |
| ¼-Kelly Stake | SC-VS-03: kelly_fraction=0.0372 | `test_signals_pure.py > test_kelly_quarter_numeric` | ✅ COMPLIANT |
| ¼-Kelly Stake | SC-VS-04: negative edge → kelly=0.0 | `test_signals_pure.py > test_kelly_floors_to_zero_when_negative` | ✅ COMPLIANT |
| Signal Emission Gate | SC-VS-05: edge=0.02 → no row | `test_gate_integration.py > test_signal_below_threshold_not_emitted` | ✅ COMPLIANT |
| Signal Emission Gate | SC-VS-06: edge=0.05 + eligible → value_signal + BetLog PAPER | `test_gate_integration.py > test_signal_above_threshold_emitted_as_paper` | ✅ COMPLIANT |
| Honesty Gate | SC-VS-07: params_json={} → BacktestRequiredError | `test_gate_integration.py > test_gate_raises_backtest_required_when_no_backtest_key` | ✅ COMPLIANT |
| Idempotency | SC-VS-08: re-run → no new row | `test_gate_integration.py > test_signal_idempotent_on_rerun` | ✅ COMPLIANT |

**Compliance summary**: 17/18 scenarios compliant, 1 partial (SC-OLM-05)

---

## Correctness (Static — Structural Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| OLM pure forward pass (probabilities.py) | ✅ Implemented | Only `math` and `typing` imports — no DB, no LLM |
| Binned baseline with NoSupportError | ✅ Implemented | predict_baseline correctly checks count < min_support |
| Anti-look-ahead: `rating_date < match_date` (strict) | ✅ Implemented | `EloRating.rating_date < before_date` in _lookup_rating |
| Default 1500 + low_confidence=True when no prior rating | ✅ Implemented | Returns `(_DEFAULT_RATING, True)` when scalar is None |
| Walk-forward backtest gate | ✅ Implemented | run_backtest raises BacktestGateError if not beats_baselines |
| Backtest in params_json | ✅ Implemented | DB confirms all keys present: brier, logloss, beats_baselines, calibration_table, eval_n |
| Backtest doc persisted | ⚠️ Partial | File exists at `docs/backtests/elo-1x2-v1.md`, NOT `docs/backtests/elo-to-1x2.md` as spec requires |
| 3 predictions per match (HOME/DRAW/AWAY) | ✅ Implemented | Explicit loop over outcomes tuple; DB confirms 216 rows (72 × 3) |
| Honesty gate non-bypassable | ✅ Implemented | `_check_gate()` is the FIRST call in `generate_signals()` |
| signals.py ONLY writer of value_signal | ✅ Implemented | `rg 'pg_insert.*ValueSignal'` returns only `signals.py:183` |
| Upsert idempotency on predictions | ✅ Implemented | ON CONFLICT DO UPDATE on `uq_prediction_identity` |
| Upsert idempotency on signals | ✅ Implemented | ON CONFLICT DO NOTHING on `uq_signal_identity` |
| BetLog PAPER for every emitted signal | ✅ Implemented | DB: 69 BetLog rows, all PAPER, each linked to distinct signal |
| Best-price selection across bookmakers | ✅ Implemented | best_odds dict scans all_odds for max decimal_odds per outcome |

---

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| All model files in `app/model/` | ✅ Yes | probabilities, fit_1x2, backtest_1x2, predict_1x2, signals, run_1x2 |
| Pure core: no DB imports in probabilities.py | ✅ Yes | Only `math`, `typing` |
| Reparam α₂ = α₁ + exp(δ) | ✅ Yes | In both probabilities.py and fit_1x2.py |
| Gate in signals.py, not bypassable | ✅ Yes | _check_gate() first in generate_signals() |
| De-vig proportional method | ✅ Yes | devig_proportional implemented correctly |
| Brier score ÷ K=3 → uniform ≈ 0.2222 | ✅ Yes | `np.mean(np.sum(..., axis=1)) / 3.0` |
| Upsert idempotence on both tables | ✅ Yes | uq_prediction_identity + uq_signal_identity |
| ArgParse CLI with 4 subcommands | ✅ Yes | fit|backtest|predict|signals |
| Backtest doc filename | ⚠️ Deviated | Design says `elo-to-1x2.md`; created `elo-1x2-v1.md` |
| home_advantage=100 only for non-neutral | ✅ Yes | `0.0 if match.neutral_site else _HOME_ADVANTAGE` |
| 1x2-olm-v1 as model_version name | ✅ Yes | Confirmed in DB |
| bankroll default 1000 from params_json.thresholds | ✅ Yes | `thresholds.get("bankroll", 1000.0)` |

---

## Adversarial Audit — Top 3 Signals

This section contains a full end-to-end audit of the three signals flagged as implausibly large (edge 0.23–0.34). All arithmetic performed by manual recomputation using DB values.

**Fitted model params confirmed in DB (`1x2-olm-v1`)**:
- a1 = −0.7389, delta = 0.1756 → a2 = a1 + exp(0.1756) = 0.4529
- beta_diff = 0.004952, beta_neutral = 0.0239
- Backtest: Brier=0.1703 (vs uniform 0.2222, binned 0.1887), LogLoss=0.8699 (vs uniform 1.0986, binned 0.9614)
- eval_n=7855, train_n=41516, eval_window=2018-06-01 → 2026-06-07

---

### Signal 1: Ghana vs Panama — AWAY edge=0.3364 @ 3.90

**a. Match orientation**
- match_id=49397, match_date=2026-06-17, neutral_site=TRUE
- home_team=Ghana (Elo=1625.26@2026-06-02), away_team=Panama (Elo=1854.22@2026-06-06)
- Signal outcome_code=AWAY, odds.outcome_code=AWAY → orientation is consistent ✅

**b. Manual OLM recomputation**
```
advantage = 0.0 (neutral=TRUE)
elo_diff = 1625.26 − 1854.22 = −228.96
linear = 0.004952 × (−228.96) + 0.0239 × 1 = −1.1105
logit0 = −0.7389 − (−1.1105) = 0.3716 → p_away = σ(0.3716) = 0.5917 ✓ (DB: 0.59171)
logit1 = 0.4529 − (−1.1105) = 1.5634 → p_home = 1 − σ(1.5634) = 0.1732 ✓ (DB: 0.17321)
p_draw = σ(1.5634) − σ(0.3716) = 0.2351 ✓ (DB: 0.23508)
```

**c. De-vig & edge**
- Best AWAY odds: betfair_ex_eu 3.900
- Synthetic cross-book triple: H=2.120 (betfair), D=3.620 (marathonbet/onexbet), A=3.900 (betfair)
- overround = 1/2.12 + 1/3.62 + 1/3.90 = 0.4717 + 0.2762 + 0.2564 = 1.0043
- fair_AWAY = 0.2564 / 1.0043 = 0.2553
- edge = 0.5917 − 0.2553 = 0.3364 ✓ (DB: 0.33641)
- Cross-book comparison vs betfair single-book (H=2.12/D=3.55/A=3.90, overround=1.0098): fair_AWAY=0.2539, edge=0.3378. Cross-book cherry-picking REDUCES edge by 0.0014 here (not inflating). ✅

**d. Elo plausibility**
- Panama Elo=1854 (#18-ish in our system), Ghana Elo=1625 (outside top 25)
- Market consensus: 22 bookmakers price Ghana at 1.94–2.12 (HOME favorite); Panama at 3.45–3.90
- Market implied Ghana win ≈ 46–50%; model gives Ghana only 17%
- Large discrepancy: Panama had strong WC2026 CONCACAF qualifying results → high Elo in our system; market likely reflects current squad form/availability

**e. VERDICT: MODEL-OVERCONFIDENT** — Code is correct. Edge of 0.33 reflects genuine model-market disagreement (Panama Elo much higher than market implies). No code bug, no orientation bug, no look-ahead. PAPER mode is the correct vehicle to track whether this disagreement resolves in model's favor.

---

### Signal 2: Canada vs Bosnia — HOME edge=0.2495 @ 1.88

**a. Match orientation**
- match_id=49376, match_date=2026-06-12, neutral_site=FALSE (Canada hosts WC2026)
- home_team=Canada (Elo=1898.85@2026-06-05), away_team=Bosnia (Elo=1651.74@2026-06-06)
- Signal outcome_code=HOME, odds.outcome_code=HOME → orientation consistent ✅

**b. Manual OLM recomputation**
```
advantage = 100.0 (neutral=FALSE)
elo_diff = (1898.85 + 100) − 1651.74 = 347.11
linear = 0.004952 × 347.11 + 0 = 1.7183
logit0 = −0.7389 − 1.7183 = −2.4572 → p_away = σ(−2.4572) = 0.0789 ✓ (DB: 0.07886)
logit1 = 0.4529 − 1.7183 = −1.2654 → p_home = 1 − σ(−1.2654) = 0.7800 ✓ (DB: 0.78005)
p_draw = σ(−1.2654) − σ(−2.4572) = 0.1411 ✓ (DB: 0.14109)
```

**c. De-vig & edge**
- Best HOME odds: betfair_ex_eu 1.880
- Synthetic triple: H=1.880 (betfair), D=3.750 (coolbet/everygame), A=4.900 (betfair/nordicbet)
- overround = 0.5319 + 0.2667 + 0.2041 = 1.0027 (very low — 0.27% margin)
- fair_HOME = 0.5319 / 1.0027 = 0.5305
- edge = 0.7800 − 0.5305 = 0.2495 ✓ (DB: 0.24955)
- Note: synthetic overround 1.0027 vs Pinnacle single-book 1.0347 means fair_HOME is HIGHER in synthetic (0.5305 vs 0.5282), so edge is actually SLIGHTLY LOWER than Pinnacle-based computation. Cherry-picking does not inflate edge here. ✅

**d. Elo plausibility**
- Canada Elo=1899 (#13 in our system), Bosnia=1652
- Canada hosting WC2026 → +100 home advantage → elo_diff=+347 is very large
- Model: 78% Canada win; Market: 53% (best odds 1.88 → ~53% implied)
- Gap (78% vs 53%) is the largest absolute disagreement for a non-extreme home win
- Canada has been strong in CONCACAF but market likely applies a lower win probability based on Bosnia's quality at full strength

**e. VERDICT: MODEL-OVERCONFIDENT** — The +347 elo_diff with home advantage is at the upper end of the training distribution, so the model's steeper probability curve may not be well-calibrated at these extremes. Code is correct. No bug.

---

### Signal 3: Ecuador vs Germany — HOME edge=0.2342 @ 5.25

**a. Match orientation**
- match_id=49431, match_date=2026-06-25, neutral_site=TRUE
- home_team=Ecuador (Elo=2028.19@2026-06-07), away_team=Germany (Elo=2004.70@2026-06-06)
- Signal outcome_code=HOME, odds.outcome_code=HOME → orientation consistent ✅

**b. Manual OLM recomputation**
```
advantage = 0.0 (neutral=TRUE)
elo_diff = 2028.19 − 2004.70 = 23.49
linear = 0.004952 × 23.49 + 0.0239 × 1 = 0.1163 + 0.0239 = 0.1402
logit0 = −0.7389 − 0.1402 = −0.8791 → p_away = σ(−0.8791) = 0.2933 ✓ (DB: 0.29335)
logit1 = 0.4529 − 0.1402 = 0.3127 → p_home = 1 − σ(0.3127) = 0.4224 ✓ (DB: 0.42242)
p_draw = σ(0.3127) − σ(−0.8791) = 0.2843 ✓ (DB: 0.28423)
```

**c. De-vig & edge**
- Best HOME odds: betonlineag 5.250 (only bookmaker pricing Ecuador this high)
- Synthetic triple: H=5.250 (betonlineag), D=3.950 (betonlineag), A=1.760 (unibet_nl/unibet_se)
- overround = 0.1905 + 0.2532 + 0.5682 = 1.0119
- fair_HOME = 0.1905 / 1.0119 = 0.1883
- edge = 0.4224 − 0.1883 = 0.2341 ✓ (DB: 0.23417)
- Cross-book comparison vs betonlineag own triple (H=5.25/D=3.95/A=1.69, overround=1.0354): fair_HOME=0.1840, edge=0.2384. Synthetic REDUCES edge by 0.0043 (not inflating). ✅

**d. Elo plausibility**
- Ecuador Elo=2028 (#8 globally in our system), Germany Elo=2005 (#10)
- Ecuador ranked ABOVE Germany (#8 vs #10) reflects recent strong Copa America + WC qualifying results
- Market: Germany priced at 1.65–1.76 (implied ~57–61% Germany win); Ecuador at 4.00–5.25 (implied ~19–25% Ecuador win)
- Model gives Ecuador 42% (slightly favored on Elo diff of +23) vs market's 19%
- The near-equality in Elo (only +23 to Ecuador) explains why model gives roughly even odds. Market disagrees strongly, likely based on squad quality and perceived gap between South American qualifier performance and German elite football level.

**e. VERDICT: MODEL-OVERCONFIDENT** — Ecuador's Elo of 2028 places them 8th globally, slightly ahead of Germany (2005). On a neutral site with only a 23-point Elo edge, the OLM correctly computes near-even odds. The model-market gap is a calibration issue: recent WC qualifying results inflated Ecuador's Elo relative to what the market considers their "true" strength. Code is correct, no bug.

---

### Edge Distribution Assessment

| Bucket | Count | Avg Edge | Range |
|--------|-------|----------|-------|
| 0.03–0.05 | 13 | 0.040 | 0.032–0.049 |
| 0.05–0.10 | 29 | 0.076 | 0.051–0.098 |
| 0.10–0.15 | 17 | 0.129 | 0.103–0.148 |
| 0.15–0.20 | 6 | 0.176 | 0.152–0.199 |
| 0.20–0.30 | 3 | 0.230 | 0.206–0.250 |
| ≥0.30 | 1 | 0.336 | — |

- **Median edge**: ~7–8% (all 69 signals)
- **61% of signals have edge > 5%**, which is systematically higher than typical market efficiency expectations (1–5%)
- Root cause: Elo-only model gives more extreme probabilities than a 25-bookmaker consensus for high-elo-differential matches
- This is EXPECTED behavior for a v1 model with no squad/form features
- PAPER mode is the correct safeguard: real ROI tracking will reveal calibration quality over time

**Global verdict on adversarial audit**: No code bugs found. All three implausibly large signals are MODEL-OVERCONFIDENT due to Elo-market disagreement. The betting loop is NOT generating wrong numbers — it is generating correct numbers that happen to disagree strongly with the market.

---

## Quality Metrics

**Linter (ruff)**: ✅ No errors — `All checks passed!`
**Type Checker**: ➖ Not available (no mypy in project deps)

---

## Issues Found

**CRITICAL** (must fix before archive):
None.

**WARNING** (should fix):
1. **[W1] SC-OLM-05 test only partially validates anti-look-ahead**: `test_predict_uses_rating_strictly_before_match_date` checks that 3 predictions exist and `low_confidence=False`, but does NOT verify that the probability values correspond to using rating=1650 (not 1670). A look-ahead bug would still pass this test. The code is statically correct (`rating_date < before_date` strict), but the test does not dynamically prove it. Fix: add assertion that `abs(float(pred_home.probability) - expected_prob_with_1650) < 0.0001`.

2. **[W2] Backtest doc filename deviates from spec**: Spec requires `docs/backtests/elo-to-1x2.md`; file created is `docs/backtests/elo-1x2-v1.md`. The primary requirement (params_json backtest key) is satisfied. Fix: rename or symlink file to match spec.

3. **[W3] Systematically elevated edge distribution (median 7–8%)**: 61% of signals have edge > 5%. For a 25-bookmaker consensus market, this indicates the Elo-only OLM is miscalibrated for certain match types (large elo_diff, high-profile neutral-site matchups). No code bug — this is expected model behavior. Action: monitor PAPER signal ROI; if edge does not materialize in outcomes, recalibrate with squad features before promoting to real stakes.

4. **[W4] beta_neutral = +0.0239 (positive, counterintuitive)**: The fitted neutral coefficient slightly INCREASES the linear term for neutral matches, meaning "home team on neutral ground" marginally has higher predicted win probability. Effect is tiny (equivalent to ~5 Elo points) but conceptually odd. Likely a statistical artifact from larger/stronger nations more often occupying the "home team" slot in tournament draws. Not a bug; note for future model audit.

**SUGGESTION** (nice to have):
1. Add `test_predict_integration.py` triangulation case that verifies the rating value used by computing expected probabilities at both 1650 and 1670, and asserting the actual DB probability matches the 1650 computation.
2. Rename `elo-1x2-v1.md` → `elo-to-1x2.md` per spec.
3. Add pytest-cov to pyproject.toml dev deps for coverage tracking in CI.
4. Replace `edge > 0.0` implicit Kelly logic with explicit minimum-confidence comment explaining that the per-bookmaker de-vig is intentionally cross-book per spec.

---

## Verdict

**APPROVED WITH WARNINGS**

Implementation is complete (23/23 tasks), tests pass (91/91), ruff clean, gate enforced, all 18 spec scenarios are covered (17 COMPLIANT, 1 PARTIAL). The three flagged large-edge signals are mathematically correct per spec — they reflect model-market disagreement (Elo vs 25-bookmaker consensus), not code bugs. PAPER mode correctly isolates these from real money. Two warnings (W1 and W2) should be addressed before the next change but do not block archive.
