# Exploration: elo-to-1x2

> Generado: 2026-06-09 | Autor: sdd-explore  
> Cambio: `elo-to-1x2` — convertir ratings Elo a probabilidades 1X2 calibradas (H/D/A)
> + calcular edge/EV vs cuotas capturadas → `value_signal`

---

## Current State

### Motor Elo (listo, determinista, anti-look-ahead)

- **`app/model/elo.py`**: fórmula World Football Elo pura — funciones sin estado. `expected_score()` retorna `We` en [0,1] que mezcla win+half_draw. `update_ratings()` aplica K·G·(W−We).
- **`app/model/elo_engine.py`**: replay cronológico completo sobre `match` → puebla `elo_rating`. Convention anti-look-ahead: rating para fecha D = last row con `rating_date < D`.
- **`app/models/model.py`**: `ModelVersion` (params_json traceable) + `Prediction` (market_type, outcome_code, probability, line). Schema listo para recibir 1X2.
- **`app/models/betting.py`**: `ValueSignal` (edge, ev, kelly_fraction, recommended_stake) + `BetLog`. Schema completo.
- **`app/models/odds.py`**: `Odds` con bookmaker, decimal_odds, is_closing, market_type/outcome_code. Polimórfico (1X2, O/U, futures).

### Datos disponibles (verificados en BD)

**Elo ratings**: 98,602 puntos, 49,371 partidos terminados desde 1872.  
**Cuotas WC2026**: 72 fixtures linkeados, 1 snapshot capturado.
- 1X2: 1,429 rows, 25 bookmakers (incl. Pinnacle).
- O/U: 758 rows, 14 bookmakers.

**El problema concreto**: `We = 1 / (1 + 10^(-dr/400))` es la probabilidad de ganar (más la mitad de empatar). No hay manera directa de separar P(draw) de P(win) sin datos empíricos o un modelo adicional.

---

## Datos Empíricos — La Tabla que Decide el Modelo

### Draw rate por bucket de |Elo diff (home-adjusted)| — partidos no-neutrales, 1995+

| Elo diff | Partidos | Empate % | Local % | Visitante % |
|----------|----------|----------|---------|-------------|
| 0–49     | 3,056    | **29.6** | 37.8    | 32.6        |
| 50–99    | 2,997    | **30.2** | 37.6    | 32.2        |
| 100–149  | 2,674    | **28.5** | 42.9    | 28.6        |
| 150–199  | 2,462    | **25.6** | 47.2    | 27.1        |
| 200–249  | 2,169    | **25.1** | 51.2    | 23.7        |
| 250–299  | 1,753    | **21.2** | 56.2    | 22.6        |
| 300–349  | 1,557    | **19.0** | 61.2    | 19.8        |
| 350–399  | 1,169    | **15.7** | 64.4    | 19.9        |
| 400–449  | 891      | **13.1** | 67.3    | 19.5        |
| 450–499  | 686      | **11.1** | 71.1    | 17.8        |
| 500–549  | 452      | **8.4**  | 73.2    | 18.4        |
| 550–599  | 339      | **6.5**  | 72.9    | 20.6        |
| 600+     | ~700     | **<4**   | ~78     | ~18         |

**Observaciones clave**:
1. Draw rate baja de ~30% (diffs pequeños) a ~8% (diffs 500+) — variación de **4x**. Un parámetro constante NO captura esto.
2. Los buckets 0-99 tienen >2,900 partidos cada uno — estadísticamente robustos.
3. Buckets >600 tienen pocos datos (ruido creciente), pero son raros en WC2026.

### Draw rate — partidos neutrales (WC, finales continentales), 1995+

| Elo diff | Partidos | Empate % |
|----------|----------|----------|
| 0–99     | 3,119    | 27.2     |
| 100–199  | 2,410    | 26.4     |
| 200–299  | 1,446    | 21.0     |
| 300–399  | 726      | 15.4     |
| 400–499  | 289      | 8.0      |

**Partidos neutrales: draw rate ~2-3 pp menor en buckets compactos** (sin ventaja de local). WC2026 son mayormente neutrales (sede única).

### World Cup específico (1982–2026)
- 656 partidos, **24.5% empate**, 2.55 goles promedio, elo diff promedio 130.
- Draw rate WC ≈ draw rate general para diffs ~130 (28.5% en bucket 100-149) — ligeramente por debajo, lo que es coherente con que WC es casi todo neutral (−2-3 pp esperado).

### Dataset completo 1995+ (29,260 partidos)
- 23.3% empate overall, 2.77 goles promedio.

---

## Affected Areas

- `app/model/elo.py` — se lee (no se toca); se usa `expected_score()`
- `app/model/elo_engine.py` — se lee (no se toca)
- `app/model/` — **nueva**: `elo_1x2.py` (conversión Elo → P(H/D/A)) + `backtest.py` (walk-forward, Brier, log-loss, calibración)
- `app/model/run_elo.py` — se revisa para ver si hay patrón a seguir para el runner
- `app/models/model.py` — `Prediction` ya está lista; `ModelVersion` ya está lista
- `app/models/betting.py` — `ValueSignal` ya está lista
- `pyproject.toml` — **agregar**: `numpy`, `scipy` (ausentes; ver constraints)
- `tests/` — nuevos tests unitarios para `elo_1x2.py` + test de backtest sanity-check
- `migrations/versions/` — probablemente no necesita nueva migración (schemas ya existen)

---

## Constraint Crítico: Dependencias Faltantes

**numpy y scipy NO están en `pyproject.toml`**. Presentes en el stack planeado (CLAUDE.md) pero no instalados. Cualquier enfoque que los requiera (regresión logística ordinal, fits estadísticos) necesita añadirlos.

```toml
# A agregar en pyproject.toml:
"numpy>=1.26",
"scipy>=1.14",
```

Esto requiere rebuild del container. Tiempo estimado: ~2 min. No es bloqueante pero debe hacerse al inicio del apply.

Alternativa sin deps: **enfoque empírico binado** funciona con Python puro + `statistics` stdlib (monotone smoothing con interpolación lineal). Viable como fallback.

---

## Approaches

### A. Ordinal Logistic Regression (Proportional Odds Model)

Fit una OLM sobre Elo diff home-adjusted (+ flag neutral) → P(home win), P(draw), P(away win) directamente. Modelo: `logit(P(Y ≤ j)) = αⱼ − β·x` para j ∈ {win, draw}.

- **Pros**: Probabilidades normalizadas por construcción; maneja neutro/no-neutro como feature; una sola calibración "de punta a punta"; well-studied; producción en `scipy.stats` o equivalente.
- **Cons**: Asunción de proportional odds puede no cumplirse (test de Brant); requiere numpy+scipy; fitting en ~29k filas es fast pero hay que hacerlo walk-forward para honestidad.
- **Effort**: Medium (3-4 días incluyendo backtest)
- **Calibración**: clara — reportar Brier y log-loss por ventana temporal.
- **Look-ahead safety**: fit sobre datos hasta fecha t-1, predict en t → walk-forward limpio.

### B. Davidson / Rao-Kupper Draw Extension

Extiende Bradley-Terry con parámetro ν de tendencia a empate:
- `P(H) = pₕ / (pₕ + pₐ + ν√(pₕ·pₐ))`
- `P(D) = ν√(pₕ·pₐ) / (pₕ + pₐ + ν√(pₕ·pₐ))`
- `P(A) = pₐ / (pₕ + pₐ + ν√(pₕ·pₐ))`

donde pₕ y pₐ se derivan de We.

- **Pros**: Elegante; un solo parámetro; closed-form dado ν; directamente sobre We existente.
- **Cons**: **ν constante** — los datos muestran draw rate que varía 4x según el diff; un ν único subestimará draws en diffs ~0-100 y sobreestimará en diffs >400. Calibración estructuralmente débil.
- **Effort**: Low (1-2 días)
- **Calibración**: reportable pero con bias sistemático esperado en los extremos.

### C. Empirical Binned Draw Curve (Baseline Transparente)

P(draw | elo_diff) = frecuencia empírica del bucket. P(home) y P(away) = distribución proporcional del resto según We.

Formula:
```
draw_p = lookup_table[bucket(elo_diff)]
remaining = 1 - draw_p
home_p = We * remaining / (We + (1-We))  → pero We ya es la mezcla win+½draw
# Ajuste: We_pure_win = We - 0.5*draw_p (aprox.), luego normalizar
```

- **Pros**: Sin deps externos (Python puro); 100% transparente y auditable; directamente de nuestros datos; monotone-smoothable con interpolación lineal; cold-start friendly.
- **Cons**: Discontinuidades entre buckets si no se interpola; extrapolación al borde ruidosa (buckets >600); no generaliza a features adicionales (forma, descanso); la formula de separar We→win/draw es una aproximación.
- **Effort**: Low (1-2 días incluyendo backtest básico)
- **Calibración**: reportable; simple de implementar.

### D. Dixon-Coles (Poisson bivariado + ajuste 0-0/1-0/0-1/1-1)

Fit tasa de ataque/defensa por equipo → λ_home, λ_away → distribución de marcadores → 1X2 + O/U. El ajuste DC corrige independencia en scores bajos.

- **Pros**: Genera 1X2 AND O/U desde el mismo modelo — importante porque ya tenemos odds de O/U capturadas (758 rows). ADR 0002 lo menciona explícitamente.
- **Cons**: Requiere datos de goles por equipo (disponibles pero hay que agregarlos por equipo); fitting es iterativo (L-BFGS-B sobre >49k partidos); implementación considerable (~500-700 líneas); mucho más de 2 días.
- **Effort**: High (5-7 días)
- **Calibración**: la más completa, pero la más tardada.

---

## Recommendation

### Primaria: **Approach A — Ordinal Logistic Regression** (+ EV en el mismo change)

**Rationale**:
1. Los datos muestran una relación monotónica clara entre Elo diff y draw rate — exactamente lo que la OLM captura bien.
2. Una sola ecuación da P(H/D/A) normalizadas con las propiedades probabilísticas correctas.
3. Incorporar `neutral_site` como feature es inmediato (un coeficiente extra).
4. El modelo de predicción es **auditablemente determinista** — sus coeficientes son constantes pre-calculadas, no hay estado mutable en producción.
5. scipy es una dependencia que se añadirá de todas formas cuando se implemente Dixon-Coles en el futuro; no es deuda técnica.
6. El backtest walk-forward es claro: fit en pre-2018, eval en 2018-2026 (8 años, ~8,000 partidos post-2018 en dataset).

**Implementación**:
```python
# app/model/elo_1x2.py (sketch conceptual)
from scipy.stats import OrderedModel  # o mle_ordinal custom

class EloTo1X2:
    """Convierte Elo diff → P(H/D/A). Determinista, sin estado global."""
    
    def fit(self, matches: list[MatchRow]) -> "EloTo1X2":
        # X = [home_adj_elo_diff, is_neutral]
        # y ordinal: 0=away_win, 1=draw, 2=home_win  
        # fit OrderedModel
        ...
    
    def predict(self, home_elo: float, away_elo: float, *, neutral: bool) -> Probabilities:
        # Returns namedtuple(home=float, draw=float, away=float)
        ...
    
    def to_params(self) -> dict:  # para ModelVersion.params_json
        ...
```

**Backtest design**:
- **Split**: fit en `match_date < 2018-06-01` (~21k partidos), walk-forward año a año 2018-2026.
- **Métricas**: Brier score 1X2 (multi-class), log-loss, calibración table (10 buckets de probabilidad predicha vs observada).
- **Baselines**: (i) uniforme 1/3, (ii) cuota implícita Pinnacle donde disponible (72 fixtures WC2026 — puede validar marginal).
- Brier score uniforme = 0.222 (cota superior obvia). El modelo DEBE mejorarla.

**EV + value_signal** (trivial, mismo change):
```
# De-vig: método proporcional (simple, estándar)
fair_prob = (1/odds) / sum(1/o for o in [odds_H, odds_D, odds_A])
edge = p_model - fair_prob
ev = edge * (decimal_odds - 1) - (1 - p_model)  # equivalente: p*(o-1) - (1-p)
kelly = max(0, edge / (decimal_odds - 1)) * 0.25  # ¼ Kelly
```

Poblar `value_signal` solo donde `edge > umbral mínimo` (ej. 2% → configurable).

### Fallback: **Approach C — Empirical Binned Draw Curve**

Si el tiempo es crítico (WC en 2 días) y no hay tiempo para añadir scipy + rebuild + OLM fit, el enfoque binado da resultados razonables con los datos que ya tenemos, sin deps. La tabla de arriba ES el modelo. Implementación: 1 día.

---

## Scope Recommendation

### UN solo change: `elo-to-1x2`

Incluye: modelo OLM + backtest + EV cálculo + poblar `prediction` + poblar `value_signal`.

**Justificación**:
- El EV es 3 líneas de código. Separarlo en otro change sería burocracia sin valor.
- El backtest es el gating — sin él el modelo no se usa (invariante: "sin backtest reportado, no se usa para apostar"). Backtest y modelo van juntos.
- Las señales en `value_signal` son el output útil; tenerlas al final de este change es el "done" real.
- Tiempo: ~3-4 días para Approach A. Approach C: 1-2 días (si urgencia extrema).

**Nota de timing**: WC2026 arranca ~2026-06-11. Hoy es 2026-06-09. Hay 2 días. Si la urgencia es servir señales para el partido inaugural, el Approach C (binado) es la única opción honesta. Si se acepta perder los primeros partidos y calibrar mientras el torneo corre, Approach A es correcto. **Esta decisión la toma el usuario** — ambas opciones están ready para la propuesta.

---

## Risks

1. **scipy/numpy ausentes** — rebuild del container requerido antes de implementar Approach A. No bloqueante pero es trabajo visible en apply.
2. **WC2026 es mayormente neutral-site** — el modelo debe tener un path claro para `neutral=True`. Los datos muestran draw rate 2-3 pp menor en neutral; si el modelo ignora esto sobreestimará draws en el torneo.
3. **72 fixtures de odds = muestra de validación pequeña** — el backtest de calibración usa el histórico (robusto), pero el backtest de *rentabilidad* (¿el edge real es positivo?) necesita partidos con resultado. En el momento del apply solo hay odds pre-torneo; el backtest de rentabilidad madurará conforme el torneo avance.
4. **Buckets de Elo diff extremos (>500)** tienen pocos datos — ruido alto. Para esos casos (e.g., Brasil vs San Marino en clasificatoria) la draw prob será muy baja de todos modos y el edge no estará en el draw.
5. **De-vig method**: proporcional es simple y estándar; el método power es más preciso para cuotas asimétricas pero complica el cálculo. Se recomienda proporcional en v1, documentar como mejora futura.
6. **No hay índice en `elo_rating(team_id, rating_date)`** — el LATERAL join para lookup point-in-time ya fue identificado como área de mejora; puede ser lento en backtest si no existe. Verificar en apply.

---

## Ready for Proposal

**Sí.** Los datos empíricos están claros, el schema está listo, los approaches están evaluados. La única pregunta abierta para la propuesta es la elección de timing: Approach A (robusto, 3-4 días, pierde primeros partidos del WC) vs Approach C (rápido, 1-2 días, resultados en el partido inaugural). Proponer ambas opciones al usuario con este tradeoff explícito.
