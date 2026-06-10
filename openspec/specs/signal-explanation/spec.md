# signal-explanation Specification

## Purpose

Endpoint read-only que desglosa los 5 bloques trazables de una señal +EV: cómo
se calculó el edge, el origen del p_model, el stake ¼-Kelly, la calidad del modelo
y los metadatos de captura. Todos los valores son los PERSISTIDOS verbatim; ningún
cálculo se ejecuta dentro del request.

---

## Requirements

### Requirement: R1 — GET /api/v1/signals/{id}/explain

El endpoint MUST devolver HTTP 200 con JSON estructurado en 6 secciones.

**Invariantes de construcción:**

- MUST NOT recomputar `edge`, `ev`, `kelly_fraction`, `recommended_stake` ni `p_model`
  — todos salen verbatim de `value_signal` y `prediction`.
- `p_fair` MUST derivarse por resta: `p_fair = p_model − edge`.
- Los intermedios de de-vig (1/odds_i, overround, p_fair_reconstructed) MUST
  reconstruirse del triple H/D/A best-price point-in-time (vía `odds_id` y su
  `captured_at`) y MUST marcarse con `"ilustrativo": true`.
- Reconciliation invariant: `|p_fair_reconstructed − p_fair_derived| MUST be ≤ 0.0001`.
- Cada paso de la sección `edge` MUST incluir `{label_es, raw, formatted}` — el front
  solo maqueta, no interpreta.
- MUST NOT llamar a ninguna API externa.

**Estructura de respuesta:**

| Sección | Campos clave |
|---------|-------------|
| `apuesta` | `outcome_label`, `cuota`, `bookmaker`, `home_team`, `away_team`, `match_date` |
| `edge` | pasos numerados: `p_model`, triple crudo H/D/A (ilustrativo), `overround` (ilustrativo), `p_fair_derived`, `edge` verbatim |
| `origen_p_model` | `elo_home`, `elo_away`, `rating_date_home`, `rating_date_away`, `advantage`, `elo_diff`, `neutral`, `model_name`, `model_version_id`, `low_confidence` |
| `stake` | `formula_label`, `kelly_fraction`, `bankroll`, `recommended_stake` |
| `calidad_modelo` | `brier`, `brier_uniform`, `brier_binned`, `logloss`, `logloss_uniform`, `logloss_binned`, `beats_baselines`, `eval_n` |
| `metadata` | `captured_at`, `bookmaker`, `odds_id`, `prediction_id`, `signal_id` |

#### Scenario: Explicación numérica — signal id=10 (datos reales de BD)

- GIVEN la BD contiene signal id=10: `p_model=0.83394`, `edge=0.14724`, `ev=0.22589`,
  `kelly_fraction=0.12016`, `recommended_stake="120.16"`, odds_id=70 (gtbets HOME 1.470,
  `captured_at=2026-06-09T17:28:05`), best-price triple: H=1.470, D=4.800, A=9.800;
  Elo point-in-time: Mexico 1980.33 (2026-06-04), South Africa 1662.98 (2026-06-06);
  `model=1x2-olm-v1`, `brier=0.1703`, `beats_baselines=true`, `eval_n=7855`
- WHEN `GET /api/v1/signals/10/explain`
- THEN HTTP 200 con los siguientes valores:
  - `edge.p_model` → raw=0.83394, formatted="83.4%"
  - `edge.p_fair_derived` → raw=0.68670 (= 0.83394 − 0.14724), formatted="68.7%"
  - `edge.edge` → raw=0.14724, formatted="14.7%" (verbatim de `value_signal.edge`)
  - intermedios ilustrativos: overround=0.99064, p_fair_reconstructed_H=0.68671,
    |0.68671 − 0.68670| = 0.00001 ≤ 0.0001 ✓, `ilustrativo: true`
  - `origen_p_model` → elo_home=1980.33, elo_away=1662.98, advantage=100,
    elo_diff=417.35, neutral=false, low_confidence=false
  - `stake` → kelly_fraction=0.12016, bankroll=1000.0, recommended_stake="120.16"
    (verif: 0.25 × (0.83394×1.47−1)/(1.47−1) = 0.25 × 0.22589/0.470 = 0.12016 ✓)
  - `calidad_modelo` → brier=0.1703, brier_uniform=0.2222, brier_binned=0.1887,
    logloss=0.8699, beats_baselines=true, eval_n=7855
  - `metadata` → odds_id=70, prediction_id=59, signal_id=10

#### Scenario: 404 — signal desconocido

- GIVEN no existe signal con id=9999
- WHEN `GET /api/v1/signals/9999/explain`
- THEN HTTP 404, `{"detail": "Signal not found"}`

#### Scenario: Sin llamadas externas

- GIVEN el endpoint se invoca con un id válido
- WHEN el handler ejecuta
- THEN todos los datos provienen exclusivamente de Postgres; ninguna llamada HTTP
  externa es realizada durante el request
