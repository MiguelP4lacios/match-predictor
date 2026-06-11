# value-signals Specification

## Purpose

Convert model probabilities + bookmaker odds into +EV betting signals. De-vig odds
(proportional method), compute edge and EV, size stake with ¼-Kelly, and write
`value_signal` rows (PAPER mode) only when edge meets threshold AND the active model
has a stored backtest report.

## Requirements

### Requirement: Proportional De-Vig

The system MUST convert raw bookmaker decimal odds to fair implied probabilities using
the proportional method: `p_fair_i = (1/odds_i) / Σ(1/odds_j)` summed over the 1X2
triple. Result MUST sum to 1 within 1e-9.

#### Scenario: de-vig numeric verification

- GIVEN bookmaker odds H=2.16, D=3.24, A=3.39
- WHEN de-vig is applied
- THEN raw implied = (0.4630, 0.3086, 0.2950), overround = 1.0666
- AND p_fair = (0.4341, 0.2894, 0.2765) (±0.0001), sum = 1.0000

### Requirement: EV and Edge Calculation

The system MUST compute per outcome:
- `edge = p_model − p_fair`
- `EV = p_model × (decimal_odds − 1) − (1 − p_model)`

Best-price selection MUST scan all bookmakers for each outcome and use the highest
`decimal_odds`. Pinnacle's odds MUST be recorded separately as reference in the
`value_signal` row metadata.

#### Scenario: edge and EV numeric verification

- GIVEN p_model=0.40, p_fair=0.35 (from de-vig), decimal_odds=3.39
- WHEN edge and EV are computed
- THEN edge = 0.0500, EV = 0.40×2.39 − 0.60 = 0.3560 per unit staked

### Requirement: ¼-Kelly Stake

The system MUST compute:
`kelly_fraction = 0.25 × max(0, (p_model × decimal_odds − 1) / (decimal_odds − 1))`

A negative Kelly numerator (edge < 0) MUST floor to 0.0. `recommended_stake` is
`kelly_fraction × bankroll` (bankroll supplied externally, not stored in this change).

#### Scenario: quarter-Kelly numeric verification

- GIVEN p_model=0.40, decimal_odds=3.39
- WHEN kelly_fraction is computed
- THEN full_kelly = (0.40×3.39−1)/(3.39−1) = 0.356/2.39 = 0.1490
- AND kelly_fraction = 0.25 × 0.1490 = 0.0372 (±0.0001)

#### Scenario: negative edge floors to zero

- GIVEN p_model=0.30, decimal_odds=2.50, p_fair=0.38 (edge=−0.08)
- WHEN kelly_fraction is computed
- THEN kelly_fraction = 0.0 (floored, no stake)

### Requirement: Signal Emission Gate

The system MUST emit a `value_signal` row only when `edge ≥ edge_min` (default 0.03)
AND the active `model_version` is backtest-eligible. All emitted signals SHALL have an
associated `BetLog` entry with `mode=PAPER`.

#### Scenario: signal below threshold suppressed

- GIVEN edge=0.02 (< edge_min=0.03)
- WHEN signal generation runs
- THEN no `value_signal` row is inserted for that outcome

#### Scenario: signal above threshold emitted as PAPER

- GIVEN edge=0.05 and eligible model_version
- WHEN signal generation runs
- THEN one `value_signal` row is inserted AND a linked `BetLog` row with mode=PAPER

### Requirement: Honesty Gate

The system MUST abort signal generation with `BacktestRequiredError` if the active
`model_version.params_json` does not contain a stored backtest report key. This is a
code-enforced invariant. No `value_signal` MAY be emitted for an unvalidated model.

#### Scenario: abort when backtest report missing

- GIVEN an active model_version with params_json = {} (no backtest_report key)
- WHEN signal generation is invoked
- THEN BacktestRequiredError is raised with the model_version name in the message
- AND zero `value_signal` rows are created

### Requirement: Idempotency

The system MUST NOT create duplicate `value_signal` rows on repeated runs. The
uniqueness key SHALL be `(prediction_id, odds_id)`. Re-running generation for the same
fixture+snapshot MUST be a no-op for already-existing pairs (upsert or ignore).

#### Scenario: re-run is a no-op

- GIVEN a value_signal already exists for (prediction_id=42, odds_id=77)
- WHEN signal generation runs again for the same inputs
- THEN no new value_signal row is created and no exception is raised

---

## Futures Markets (futures-montecarlo change)

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

The system MUST generate a `value_signal` row for `OUTRIGHT_WINNER` markets when `edge = p_model − p_fair ≥ edge_min` (default 0.03).

Each emitted signal MUST include `outcome_team_id` (the team) to distinguish champion candidates. Signal uniqueness key MUST be `(prediction_id, odds_id)` — same as existing `MATCH_1X2` signals (idempotency inherited).

Futures signals are ALWAYS flagged as `is_paper=True` (PAPER mode). The backtest gate is skipped for futures markets because Monte Carlo simulations of championship outcomes cannot be historically backtested (only 1 World Cup per 4 years). Honesty requires documentation of this limitation in code comments rather than a false validation gate.

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
