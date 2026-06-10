# Tasks: Elo → 1X2 calibrado + cierre del loop +EV

## Phase 1: Deps + Migration

- [x] 1.1 Add `numpy>=1.26` and `scipy>=1.14` to `pyproject.toml`; run `docker compose run --rm api uv lock` and commit updated `uv.lock`
- [x] 1.2 Rebuild image: `docker compose build api`; verify `python -c "import numpy, scipy"` inside container
- [x] 1.3 Create migration `migrations/versions/*_m5_prediction_signal_constraints.py`: add `prediction.low_confidence BOOLEAN NOT NULL DEFAULT false`, `uq_prediction_identity (model_version_id, match_id, market_type, outcome_code)`, `uq_signal_identity (prediction_id, odds_id)`
- [x] 1.4 Round-trip verify: `docker compose run --rm api alembic upgrade head`; `alembic downgrade -1`; `alembic upgrade head`

## Phase 2: TDD RED — Failing Tests (18 scenarios)

- [x] 2.1 Create `tests/test_probabilities.py` (pure, no DB): SC-OLM-01 (logit₀=-0.90 → P(A)=0.2891, P(D)=0.3096, P(H)=0.4013 ±0.0001), SC-OLM-02 (neutral=True → P(H)=0.3318 < 0.4013), sum-to-1 (±1e-9), cutpoint ordering via reparam exp(δ), P(H) monotonically increasing over elo_diff range
- [x] 2.2 Create `tests/test_baseline.py` (pure): SC-OLM-03 (draw-rate non-increasing over 5-bucket table), SC-OLM-04 (count=150 < 300 → `NoSupportError`)
- [x] 2.3 Create `tests/test_signals_pure.py` (pure, no DB): SC-VS-01 (H=2.16/D=3.24/A=3.39 → p_fair=(0.4341,0.2894,0.2765) ±0.0001), SC-VS-02 (EV=0.3560), SC-VS-03 (¼-Kelly=0.0372 ±0.0001), SC-VS-04 (negative Kelly floors to 0.0)
- [x] 2.4 Create `tests/test_predict_integration.py` (db_session fixture): SC-OLM-05 (match 2018-01-15 → rating 1650@2017-12-31, NOT 1670@2018-01-15), SC-OLM-06 (no prior rating → effective=1500, `low_confidence=True`), SC-OLM-08 (2 runs → exactly 3 rows with P(H)+P(D)+P(A)=1.00000)
- [x] 2.5 Create `tests/test_gate_integration.py` (db_session fixture): SC-VS-07 (`params_json={}` → `BacktestRequiredError`), SC-OLM-07 (Brier≥0.2222 → `BacktestGateError` with metrics), SC-VS-05 (edge=0.02 → no row), SC-VS-06 (edge=0.05 + eligible model → `value_signal` + `BetLog` PAPER), SC-VS-08 (re-run (prediction_id=42, odds_id=77) → no new row)

## Phase 3: TDD GREEN — Implementation

- [x] 3.1 Create `app/model/probabilities.py` (pure, no DB): `predict_proba(params, elo_diff, neutral)` with reparam α2=α1+exp(δ), `predict_baseline(table, diff)`, `devig_proportional(triple)`, `compute_ev(p, odds)`, `kelly_quarter(p, odds)`
- [x] 3.2 Create `app/model/fit_1x2.py`: `fit_olm(matches_df)` via `scipy.optimize.minimize` (neg-log-likelihood), `build_binned_table(matches_df, min_support=300)`, `to_params() → dict`
- [x] 3.3 Create `app/model/backtest_1x2.py`: in-memory chronological sweep (fit <2018-06-01, eval 2018→today), Brier/log-loss/10-bin calibration, `beats_baselines(metrics) → bool`; raises `BacktestGateError` if OLM fails to beat both baselines on both metrics
- [x] 3.4 Create `app/model/predict_1x2.py`: point-in-time Elo lookup (`rating_date < match_date ORDER BY rating_date DESC LIMIT 1`, default 1500 + `low_confidence=True`), upsert 3 `Prediction` rows on `uq_prediction_identity`
- [x] 3.5 Create `app/model/signals.py`: honesty gate (reads `params_json["backtest"]["beats_baselines"]`, raises `BacktestRequiredError`/`BacktestGateError`), latest-snapshot lookup, de-vig, edge, EV, ¼-Kelly, upsert `ValueSignal` (PAPER) on `uq_signal_identity`; bankroll default 1000 from `params_json.thresholds.bankroll`
- [x] 3.6 Create `app/model/run_1x2.py`: argparse subcommands `fit | backtest | predict | signals`; mirrors `run_elo.py` style; docker-only entrypoint

## Phase 4: Execution on Real Data

- [ ] 4.1 Run fit (train <2018-06-01): `docker compose run --rm api python -m app.model.run_1x2 fit`; persist coefficients + binned table to `model_version.params_json` for `1x2-olm-v1`
- [ ] 4.2 Run backtest (eval 2018→today): `docker compose run --rm api python -m app.model.run_1x2 backtest`; **if gate fails → report Brier/log-loss honestly and STOP — signals stay locked (this is the system working)**
- [ ] 4.3 If gate passes: create `docs/backtests/elo-to-1x2.md` with Brier, log-loss, calibration table (10 bins), `beats_baselines` verdict, `eval_n`, `eval_window`
- [ ] 4.4 Run predict for 72 WC2026 fixtures: `docker compose run --rm api python -m app.model.run_1x2 predict`; verify 216 rows in `prediction` (3 per match)
- [ ] 4.5 Run signals PAPER: `docker compose run --rm api python -m app.model.run_1x2 signals`; record signal count and top edges here — MANUAL-OPTIONAL if no odds snapshot available

## Phase 5: Cleanup + Commit

- [ ] 5.1 Full suite GREEN: `docker compose run --rm api pytest`
- [ ] 5.2 Lint + format clean: `docker compose run --rm api ruff check . && ruff format .`
- [ ] 5.3 Conventional commit: `feat(model): add OLM 1x2 fit/backtest/predict/signals and migration m5`; check all task boxes in this file
