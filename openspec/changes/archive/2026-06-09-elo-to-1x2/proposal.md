# Proposal: Elo → 1X2 calibrado + cierre del loop +EV

## Intent

El motor Elo produce `We` (win + ½draw), no P(H/D/A) separadas. Sin eso no hay
predicción 1X2, ni EV, ni señales. Este change convierte Elo → P(H/D/A) calibradas,
las backtestea (gate de honestidad) y cierra el loop: predicción → de-vig → EV →
¼-Kelly → `value_signal` (modo PAPER). WC2026 arranca 2026-06-11.

## Scope

### In Scope
- Deps `numpy`/`scipy` en `pyproject.toml` (rebuild container).
- Modelo **A — ordinal logistic proportional-odds** sobre `{elo_diff home-adj, neutral_flag}`, fit por MLE (`scipy.optimize`). Determinista: coeficientes constantes en `params_json`.
- Baseline **C — curva empírica binada** (Python puro) que el backtest DEBE superar; doble función: sanity-check + fallback.
- Backtest walk-forward (fit <2018-06, eval 2018→2026): Brier, log-loss, tabla de calibración vs baselines (uniforme 1/3 y binado).
- Writer de `prediction` (P H/D/A) con `model_version_id` + lookup de rating point-in-time (anti-look-ahead).
- De-vig **proporcional** (power = mejora futura documentada); EV vs odds capturadas (mejor precio + referencia Pinnacle); stake ¼-Kelly.
- Writer de `value_signal` (default `BetMode.PAPER`) sólo si `edge ≥ umbral`.
- CLI runner dockerizado (patrón `run_elo.py`) que genera predicciones + señales para fixtures WC2026 próximos.

### Out of Scope
- Probabilidades O/U y modelo **D — Dixon-Coles** (próximo change: desbloquea O/U; no absorberlo).
- Davidson/ν-constante (eliminado: draw rate varía 4x con el diff).
- Futures/Monte Carlo, tablas de grupo, endpoints API, dashboard, apuestas automáticas (real-money).

## Capabilities

### New Capabilities
- `model-1x2`: conversión Elo→P(H/D/A) (OLM + baseline binado), writer de `prediction` point-in-time, y backtest con gate de calibración persistido.
- `value-signals`: de-vig, EV, ¼-Kelly y writer de `value_signal` (PAPER) con gate "sin backtest no hay señal".

### Modified Capabilities
- None (`match-ingestion`, `odds-capture`, `ops-resilience` no cambian a nivel de requisito).

## Approach

OLM da P(H/D/A) normalizadas de una sola ecuación; `neutral_flag` es feature obligatoria (WC2026 es casi todo sede neutral). El backtest es el gate: el `value_signal` writer LEE el reporte de backtest del `model_version` activo y **se niega a correr** (excepción en código, no disciplina) si falta. No recalcula `elo_rating` (lo lee); **sí exige un reporte de backtest nuevo** antes de habilitar señales.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/model/elo_1x2.py` | New | OLM fit/predict + baseline binado + `to_params()` |
| `app/model/backtest.py` | New | walk-forward, Brier/log-loss/calibración |
| `app/model/run_1x2.py` | New | CLI: predicciones + señales WC2026 |
| `app/services/signals.py` | New | de-vig, EV, ¼-Kelly, writer `value_signal` con gate |
| `app/models/{model,betting,odds}.py` | Read | schemas ya listos (`Prediction`, `ValueSignal`) |
| `pyproject.toml` | Modified | + numpy, scipy |
| `docs/backtests/elo-to-1x2.md` | New | reporte de backtest (artefacto del gate) |
| `tests/` | New | unit OLM/baseline + sanity backtest + gate-refusal |

## Gate de calibración (numérico, en CÓDIGO)

- Aceptación: OLM **supera ambos baselines** (uniforme 1/3 y binado) en **Brier Y log-loss** out-of-sample (uniforme ≈ 0.222 cota superior).
- Persistencia: tabla de calibración + métricas en `ModelVersion.params_json` **Y** en `docs/backtests/elo-to-1x2.md` (committeable).
- Enforcement: `signals` aborta con excepción si el `model_version` activo no tiene reporte de backtest almacenado.

## Umbrales de señal (defaults tunables en `params_json`)

| Param | Default | Nota |
|-------|---------|------|
| `edge_min` | `0.03` | edge mínimo (3 pp) para emitir señal |
| `kelly_fraction` | `0.25` | ¼-Kelly, nunca pleno |
| `min_bucket_support` | `300` | no emitir en buckets de Elo diff con soporte ruidoso |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| WC2026 dominado por sede neutral | High | `neutral_flag` feature obligatoria; backtest separa neutral/no-neutral |
| Sólo 1 snapshot de odds → backtest de rentabilidad inmaduro | High | El gate es la **calibración** (histórico robusto); rentabilidad madura con el torneo |
| K chico de fixtures próximos | Med | PAPER mode; sin stake real; medir ROI/calibración en producción |
| scipy/numpy ausentes → rebuild | Med | Añadir al inicio del apply (~2 min); baseline binado corre sin deps |
| Proportional-odds no se cumple (Brant) | Med | Baseline binado como red de seguridad + fallback si OLM no supera el gate |
| Falta índice `elo_rating(team_id, rating_date)` | Low | Verificar en apply; añadir índice si el lookup es lento |

## Rollback Plan

Todo es aditivo (archivos nuevos + 2 deps). Rollback = no correr `run_1x2`, revertir `pyproject.toml` y borrar archivos nuevos; `elo.py`/`elo_engine.py`/schemas intactos. A nivel datos: marcar el `model_version` como inactivo y borrar sus filas de `prediction`/`value_signal` (PAPER, sin efecto monetario). `elo_rating` nunca se toca.

## Dependencies

- `numpy>=1.26`, `scipy>=1.14`.
- Odds WC2026 capturadas (existen: 1.429 rows 1X2, incl. Pinnacle).

## Success Criteria

- [ ] OLM supera uniforme 1/3 y baseline binado en Brier Y log-loss OOS.
- [ ] Tabla de calibración persistida en `params_json` y `docs/backtests/elo-to-1x2.md`.
- [ ] `value_signal` writer aborta si el modelo activo no tiene backtest reportado (test que lo prueba).
- [ ] `run_1x2` genera `prediction` + `value_signal` (PAPER) para fixtures WC2026 con `edge ≥ edge_min`.
- [ ] Lookup de rating es point-in-time (test anti-look-ahead).
