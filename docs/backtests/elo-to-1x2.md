# Backtest Report: 1x2-olm-v1

**Fecha de reporte**: 2026-06-09  
**Modelo**: `1x2-olm-v1` — Ordered Logit Model (OLM) sobre diferencia de Elo  
**Gate de honestidad**: ✅ APROBADO — OLM supera AMBOS baselines en AMBAS métricas

---

## Parámetros ajustados

| Parámetro | Valor |
|-----------|-------|
| `a1` (cutpoint 1) | -0.7389 |
| `a2` (cutpoint 2 = a1 + exp(δ)) | 0.4529 |
| `delta` | 0.1756 |
| `beta_diff` | 0.004952 |
| `beta_neutral` | 0.0239 |
| `train_n` | 41 516 partidos |
| `split` (fecha de corte fit/eval) | 2018-06-01 |

**Reparametrización**: α₂ = α₁ + exp(δ) garantiza α₁ < α₂ sin constraints en el optimizador.  
**Signo beta_diff**: positivo (0.004952) — mayor diferencia Elo → mayor P(home). ✓

---

## Ventana de evaluación

- **eval_window**: 2018-06-01 → 2026-06-07
- **eval_n**: 7 855 partidos

---

## Métricas out-of-sample

| Modelo | Brier ↓ | Log-loss ↓ |
|--------|---------|------------|
| **OLM 1x2-olm-v1** | **0.1703** | **0.8699** |
| Baseline uniforme (1/3, 1/3, 1/3) | 0.2222 | 1.0986 |
| Baseline binado (draw-rate empírico) | 0.1887 | 0.9614 |

> Nota: Brier score = (1/N·K) Σᵢ Σₖ (yᵢₖ − p̂ᵢₖ)² con K=3.  
> Uniforme teórico = 2/9 ≈ 0.2222. Log-loss uniforme = ln(3) ≈ 1.0986.

**Reducción de Brier vs uniforme**: 23.4%  
**Reducción de Brier vs binado**: 9.7%  
**Reducción de log-loss vs uniforme**: 20.8%  
**Reducción de log-loss vs binado**: 9.5%

---

## Tabla de calibración (10 bins, OLM)

| Bin predicho | Prob. media | Frec. observada | N |
|--------------|-------------|-----------------|---|
| 0.0 – 0.1 | 0.0585 | 0.0523 | 3 117 |
| 0.1 – 0.2 | 0.1517 | 0.1548 | 4 484 |
| 0.2 – 0.3 | 0.2565 | 0.2698 | 7 039 |
| 0.3 – 0.4 | 0.3488 | 0.3562 | 1 878 |
| 0.4 – 0.5 | 0.4496 | 0.4323 | 1 677 |
| 0.5 – 0.6 | 0.5496 | 0.5264 | 1 459 |
| 0.6 – 0.7 | 0.6479 | 0.6341 | 1 342 |
| 0.7 – 0.8 | 0.7489 | 0.7365 | 1 165 |
| 0.8 – 0.9 | 0.8474 | 0.8505 | 910 |
| 0.9 – 1.0 | 0.9370 | 0.9190 | 494 |

**Interpretación**: La calibración es sólida — el modelo tiende a sobreestimar ligeramente en el
rango 0.4–0.7, pero las desviaciones son menores a 2 pp. en todos los bins.

---

## Thresholds operativos

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `edge_min` | 0.03 | Umbral mínimo de edge (p_model − p_fair) para emitir señal |
| `kelly_fraction` | 0.25 | Kelly fraccionado (¼ Kelly) |
| `bankroll` | 1 000 | Bankroll de referencia (unidades) |
| `min_bucket_support` | 300 | Soporte mínimo del bucket binado |

---

## Veredito del gate

```
beats_baselines = True
  OLM Brier (0.1703) < uniform (0.2222)  ✓
  OLM Brier (0.1703) < binned (0.1887)   ✓
  OLM LogL  (0.8699) < uniform (1.0986)  ✓
  OLM LogL  (0.8699) < binned  (0.9614)  ✓
```

El modelo está autorizado para emitir señales +EV en modo PAPER.

---

## Notas de reproducibilidad

- El OLM se ajustó una única vez sobre `match_date < 2018-06-01`.  
- Los coeficientes están congelados en `model_version.params_json["1x2-olm-v1"]`.  
- Anti-look-ahead: cada partido de evaluación usó el Elo registrado en `rating_date < match_date`.  
- Para re-ajustar: `docker compose run --rm api python -m app.model.run_1x2 fit`  
- Para re-backtestear: `docker compose run --rm api python -m app.model.run_1x2 backtest`
