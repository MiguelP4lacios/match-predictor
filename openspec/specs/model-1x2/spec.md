# model-1x2 Specification

## Purpose

Convert Elo ratings to calibrated P(H/D/A) via ordinal logistic model (OLM) with an
empirical binned baseline as sanity-check and fallback. Predictions are written to the
`prediction` table point-in-time; the backtest gates eligibility before any signal can
be generated.

## Requirements

### Requirement: OLM Core

The system MUST produce P(H), P(D), P(A) via a proportional-odds model with features
`{home_adj_elo_diff, neutral_flag}`. Probabilities MUST sum to 1 within 1e-9. P(H)
MUST increase and P(A) MUST decrease monotonically as elo_diff increases. P(D) MUST
peak near diff≈0 and decay with |diff|. `neutral_flag=True` MUST reduce P(H) relative
to the same diff without the flag.

Formulae:
- `logit(P(Y ≤ 0)) = α₀ − β₁·elo_diff − β₂·neutral`  (Y=0: away win)
- `logit(P(Y ≤ 1)) = α₁ − β₁·elo_diff − β₂·neutral`  (Y=1: draw)
- `P(A) = σ(logit₀)`, `P(D) = σ(logit₁) − σ(logit₀)`, `P(H) = 1 − σ(logit₁)`

#### Scenario: OLM numeric forward pass (non-neutral)

- GIVEN fitted params α₀=-0.50, α₁=0.80, β₁=0.004, β₂=-0.30
- WHEN predicting with elo_diff=100, neutral=False
- THEN logit₀=-0.90 → P(A)=0.2891; logit₁=0.40 → P(A)+P(D)=0.5987
- AND P(D)=0.3096, P(H)=0.4013, sum=1.0000 (±0.0001)

#### Scenario: neutral flag reduces home probability

- GIVEN same params, elo_diff=100, neutral=True
- WHEN the OLM predicts
- THEN logit₀=-0.60 → P(A)=0.3543; logit₁=0.70 → P(A)+P(D)=0.6682
- AND P(D)=0.3139, P(H)=0.3318, sum=1.0000 (±0.0001); P(H) < non-neutral P(H)=0.4013

### Requirement: Binned Empirical Baseline

The system MUST implement a binned draw curve using empirical frequencies by |elo_diff|
bucket (50-point bins, sourced from the 1995+ historical dataset). Buckets with fewer
than `min_bucket_support` (default 300) observations MUST raise `NoSupportError` and
MUST NOT return probabilities. Baseline draw rate MUST be monotone non-increasing as
|elo_diff| increases.

#### Scenario: draw-rate monotonicity from empirical table

- GIVEN empirical table: diff 0-49 → 0.296; 100-149 → 0.285; 200-249 → 0.251;
  300-349 → 0.190; 450-499 → 0.111
- WHEN consecutive buckets are queried
- THEN each P(D) ≤ previous P(D) (strict non-increasing)

#### Scenario: low-support bucket rejected

- GIVEN a synthetic bucket with observed count = 150 (< 300)
- WHEN the baseline is asked to predict
- THEN NoSupportError is raised and no probability is returned

### Requirement: Point-in-Time Rating Lookup

The system MUST retrieve each team's Elo rating from `elo_rating` as the row with the
latest `rating_date` strictly less than match date D (no look-ahead). Teams with no
prior rating row MUST be assigned rating=1500 and flagged `low_confidence=True` in the
associated `Prediction` row.

#### Scenario: anti-look-ahead lookup

- GIVEN elo_rating rows for team_id=1 on 2017-12-31 (r=1650), 2018-01-15 (r=1670)
- WHEN predicting a match on 2018-01-15
- THEN the rating used is 1650 (2017-12-31), NOT 1670

#### Scenario: team without prior rating defaults to 1500

- GIVEN a team with no elo_rating row before match date
- WHEN the OLM predicts for that team
- THEN prediction is created with effective_rating=1500 AND low_confidence=True

### Requirement: Walk-Forward Backtest with Gate

The system MUST run a walk-forward backtest: fit on `match_date < 2018-06-01`, evaluate
on 2018–2026. The OLM MUST beat BOTH baselines (uniform 1/3 and binned) on BOTH Brier
score AND log-loss out-of-sample to be eligible. Uniform Brier = 0.2222 (upper bound).
A 10-bin calibration table (predicted-probability bucket vs observed frequency) MUST be
computed and stored.

#### Scenario: gate blocks ineligible model

- GIVEN an OLM with OOS Brier score = 0.225 (≥ 0.2222)
- WHEN the backtest evaluator runs
- THEN BacktestGateError is raised with both metric values in the message
- AND the model_version is NOT marked eligible

### Requirement: Prediction Persistence

The system MUST write exactly three `prediction` rows per match (HOME, DRAW, AWAY) with
`market_type=MATCH_1X2`, `probability` stored to 5 decimal places (Numeric 8,5), and a
valid `model_version_id` FK. Backtest report MUST be persisted in
`ModelVersion.params_json` AND `docs/backtests/elo-to-1x2.md`.

#### Scenario: three predictions written per match

- GIVEN an eligible model_version and a WC2026 fixture (match_id=99)
- WHEN predictions are written
- THEN exactly 3 rows exist with match_id=99 and outcome_codes HOME, DRAW, AWAY
- AND P(HOME) + P(DRAW) + P(AWAY) = 1.00000 (5-decimal sum, within 1e-5)
