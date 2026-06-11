# Delta for value-signals

## ADDED Requirements

### Requirement: Futures EV — De-Vig over N Outcomes

The system MUST compute fair implied probabilities for `OUTRIGHT_WINNER` markets using proportional de-vig over **all N captured outright outcomes** (N ≤ 48 for WC2026 champion market):

```
p_fair_i = (1/odds_i) / Σ_j(1/odds_j)   for all j with captured odds
```

The sum of all `p_fair_i` MUST equal 1.0 within 1e-9. The de-vig MUST be recomputed each time a new outright odds snapshot is processed (not cached from prior runs).

#### Scenario: De-vig already-normalized book (no overround)

- GIVEN outright odds for 3 outcomes: `[2.00, 3.00, 6.00]`
- WHEN de-vig is applied
- THEN raw implied = `[0.5000, 0.3333, 0.1667]`; overround = 1.0000; `p_fair = [0.5000, 0.3333, 0.1667]` (±0.0001); sum = 1.0000
- AND (verification): this is the zero-overround case; fair probs equal raw implied

#### Scenario: De-vig real overround book

- GIVEN outright odds for 3 outcomes: `[1.80, 3.50, 4.50]`
- WHEN de-vig is applied
- THEN raw implied = `[0.5556, 0.2857, 0.2222]`; overround = 1.0635
- AND `p_fair = [0.5224, 0.2686, 0.2090]` (±0.0001); sum = 1.0000

---

### Requirement: Futures Value Signal Emission

The system MUST generate a `value_signal` row for `OUTRIGHT_WINNER` markets when `edge = p_model − p_fair ≥ edge_min` (default 0.03) AND the active `model_version` has a stored backtest report.

Each emitted signal MUST include `outcome_team_id` (the team) to distinguish champion candidates. Signal uniqueness key MUST be `(prediction_id, odds_id)` — same as existing `MATCH_1X2` signals (idempotency inherited).

The `BacktestRequiredError` honesty gate inherited from the existing `Requirement: Honesty Gate` MUST apply to futures signals without exception.

#### Scenario: Futures EV signal emitted

- GIVEN team_id=7 has `p_model=0.18` (OUTRIGHT_WINNER prediction) and captured outright with de-vigged `p_fair=0.14`
- WHEN futures value signal generation runs
- THEN `edge = 0.18 − 0.14 = 0.04 ≥ edge_min`; one `value_signal` row inserted with `outcome_team_id=7`, `market_type=OUTRIGHT_WINNER`, `edge=0.04`

#### Scenario: No signal when p_model < p_fair

- GIVEN team_id=3 with `p_model=0.06` and de-vigged `p_fair=0.09` (edge=−0.03)
- WHEN futures value signal generation runs
- THEN no `value_signal` row is inserted for team_id=3

#### Scenario: Futures signal idempotency

- GIVEN a `value_signal` already exists for `(prediction_id=101, odds_id=55)` (OUTRIGHT_WINNER)
- WHEN signal generation runs again with the same snapshot
- THEN no duplicate row is created; no exception raised

---
