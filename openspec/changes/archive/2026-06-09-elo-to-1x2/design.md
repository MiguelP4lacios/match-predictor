# Design: Elo → 1X2 calibrado + cierre del loop +EV

## Technical Approach

Mirror del patrón existente **núcleo-puro + engine + runner** (`elo.py` / `elo_engine.py` / `run_elo.py`).
Todo el cómputo determinista vive en `app/model/` (no se crea `app/services/` — divergencia consciente
del proposal: las señales son cálculo determinista EV/Kelly, pertenecen al modelo). OLM produce P(H/D/A)
de una ecuación; el backtest es el gate de honestidad en CÓDIGO; el writer de `value_signal` lo lee y
**aborta con excepción** si falta. Predicciones NO gated (números crudos inofensivos); SEÑALES sí.

## Architecture Decisions

| # | Decisión | Elegido | Rechazado | Rationale |
|---|----------|---------|-----------|-----------|
| 1 | Layout | Todo en `app/model/`: `probabilities.py` (puro), `fit_1x2.py` (MLE), `backtest_1x2.py`, `predict_1x2.py` (engine), `signals.py` (engine), `run_1x2.py` (CLI subcomandos) | `app/services/signals.py` (proposal); 4 runners separados | Cohesión con `app/model/`; un solo entrypoint docker; señales = determinista |
| 2 | Parametrización OLM | cutpoints α1, α2=α1+exp(δ); β_diff, β_neutral; `logit P(Y≤j)=αⱼ−(β_diff·diff+β_neutral·neutral)` | α1<α2 con constraint en `minimize` | exp(δ) garantiza α1<α2 sin constraints → optimización sin bordes |
| 3 | Anti-look-ahead a escala | **Backtest**: barrido cronológico en memoria (replica `elo_engine`), predict-antes-de-update, O(N) sin queries | 40k queries point-in-time | Sweep bate N queries; anti-look-ahead inherente |
| 4 | Lookup predict (N chico) | `SELECT rating WHERE team_id=:t AND rating_date<:d ORDER BY rating_date DESC LIMIT 1` vía índice `uq_elo_team_date (team_id, rating_date)` | índice nuevo `(team_id, rating_date DESC)` | El uq btree ya sirve; verificar lentitud en apply, índice solo si hace falta |
| 5 | Cadencia fit | **Estático**: fit `match_date<2018-06-01`, coeficientes congelados en `params_json` | rolling refit | Determinismo auditable; rolling = future change |
| 6 | Versiones | `1x2-olm-v1` (primario) y `1x2-binned-v1` (baseline/fallback) como `model_version` separados | una versión compartida | Cada señal traza a UN `model_version_id` |
| 7 | Gate | En `signals.py`: lee `params_json["backtest"]` del modelo activo, valida presencia y `beats_baselines==true`, sino `raise BacktestGateError` | flag/disciplina externa | Único writer de `value_signal`; check es lo primero → no bypasseable |
| 8 | De-vig | **Proporcional**: `fair_p_o=(1/odds_o)/Σ(1/odds)` sobre el triple H/D/A del mismo bookmaker | power method | Estándar v1; power = mejora futura documentada |
| 9 | Deps | `numpy>=1.26`, `scipy>=1.14` (>= como el resto); rebuild docker. fit/backtest usan scipy; `probabilities.py`/predict/signals solo stdlib `math` | — | Baseline + predict corren aunque el fit scipy falle (resiliencia) |

## Data Flow

```mermaid
sequenceDiagram
    participant R as run_1x2 signals
    participant DB as Postgres
    participant P as probabilities.py (puro)
    participant S as signals.py engine
    R->>DB: ModelVersion activo (params_json)
    S->>S: gate: backtest.beats_baselines? sino BacktestGateError
    R->>DB: Prediction P(H/D/A) del match
    R->>DB: Odds: LATEST snapshot por bookmaker (max captured_at)
    S->>P: de-vig proporcional cada triple → fair_p
    S->>P: best decimal_odds por outcome (mejor pago)
    P-->>S: edge = p_model − fair_p(best book); EV; ¼-Kelly
    alt edge ≥ edge_min y bucket_support ≥ min
        S->>DB: UPSERT value_signal (PAPER, odds_id=best book)
    else
        S-->>R: skip (sin señal)
    end
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/model/probabilities.py` | Create | Puro: OLM pmf (normaliza, suma 1), baseline binado (lookup+interp), de-vig proporcional, EV, ¼-Kelly |
| `app/model/fit_1x2.py` | Create | MLE `scipy.optimize.minimize` neg-log-lik; reparam α2=α1+exp(δ); construye tabla binada; `to_params()` |
| `app/model/backtest_1x2.py` | Create | Walk-forward sweep cronológico; Brier, log-loss, tabla calibración, comparación baselines |
| `app/model/predict_1x2.py` | Create | Engine: lookup point-in-time, escribe `Prediction` (upsert idempotente) |
| `app/model/signals.py` | Create | Engine: gate, latest-snapshot, de-vig, edge, ¼-Kelly, escribe `ValueSignal` (PAPER) |
| `app/model/run_1x2.py` | Create | CLI subcomandos `fit|backtest|predict|signals` (argparse), estilo `run_elo` |
| `migrations/versions/*_m5_*.py` | Create | `uq_prediction_identity`, `uq_signal_identity` |
| `pyproject.toml` + `uv.lock` | Modify | + numpy, scipy; regen lock + rebuild |
| `docs/backtests/elo-to-1x2.md` | Create | Reporte de backtest committeable (artefacto del gate) |
| `tests/test_*1x2*.py` | Create | Unit puros + integración (gate-refusal, point-in-time, idempotencia) |

## Interfaces / Contracts

**`params_json` (`1x2-olm-v1`)**: `{model:"A-olm", cutpoints:{a1,a2}, beta_diff, beta_neutral, home_adj:100,
fit:{split:"2018-06-01", train_n}, backtest:{brier, logloss, baselines:{uniform, binned}, beats_baselines:bool,
calibration_table, eval_window, eval_n}, thresholds:{edge_min:0.03, kelly_fraction:0.25, min_bucket_support:300,
bankroll:1000}, devig:{method:"proportional"}}`. Baseline `1x2-binned-v1`: `{model:"C-binned", bucket_edges,
draw_rate_by_bucket, neutral_adjustment, backtest:{...}}`.

**Idempotencia**: `Prediction` upsert on `(model_version_id, match_id, market_type, outcome_code)`;
`ValueSignal` upsert on `(prediction_id, odds_id)`. `recommended_stake = ¼-Kelly · bankroll`. `odds_id` = fila del
mejor precio (la que se apostaría). Referencia Pinnacle: NO se persiste (sin columna free-form; evitar churn) —
se usa solo como baseline en backtest.

**Selección fixtures (predict)**: `status==SCHEDULED AND competition.kind==WORLD_CUP AND match_date ∈ [today, today+N]`.
`neutral_site` del match alimenta `β_neutral`; home_advantage solo si `neutral_site==False` (igual que Elo).
VERIFICAR en apply los valores reales del flag en fixtures WC2026.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit (puro, sin BD) | pmf suma 1 y monotonía; α1<α2 vía reparam; de-vig suma 1; EV/Kelly numéricos; baseline interp | pytest, valores hardcodeados |
| Integration (`db_session`) | predict escribe `Prediction` point-in-time (anti-look-ahead); gate-refusal `raise BacktestGateError`; upsert idempotente | SAVEPOINT fixture |
| Integration | backtest sanity: OLM supera uniforme 1/3 en set sintético cronológico | pytest |

## Migration / Rollout

Migración `m5` aditiva: 2 UNIQUE constraints (down: drop). Resto = archivos nuevos + 2 deps.
Rollback: no correr `run_1x2`, revertir `pyproject.toml`, borrar archivos, marcar `model_version` inactivo y
borrar sus `prediction`/`value_signal` (PAPER, sin efecto monetario). `elo_rating`/`elo.py` intactos.

## Open Questions

- [ ] Verificar en apply: `neutral_site` real de fixtures WC2026 y si existe índice suficiente para el lookup.
- [ ] `bankroll` default (1000 units) — confirmar fuente (params_json vs settings).
