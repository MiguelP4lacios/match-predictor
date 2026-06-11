# Parlay Math Specification

## Purpose

Núcleo determinista puro que combina N legs: cuota combinada, probabilidad del modelo
(independencia documentada), EV del cupón, diagnóstico por-leg con flag −EV y
sugerencia de sub-cupón sin los legs negativos.

---

## Requirements

### Requirement: combine_parlay

`combine_parlay(legs: list[ParlayLeg]) -> ParlayResult` MUST calcular:

| Campo | Fórmula |
|---|---|
| `combined_odds` | Π(leg.odds_taken) |
| `model_prob` | Π(leg.p_model) |
| `ev` | `model_prob × combined_odds − 1` |
| `legs_diagnostics` | `[{leg_ev, is_negative_ev}]` por leg |
| `suggested_without_negatives` | sub-lista de legs con `is_negative_ev=False`, solo cuando ≥1 leg es −EV; `None` en caso contrario |

MUST NOT persistir, leer BD ni llamar al LLM.
MUST lanzar `ValueError("Parlay requires at least 2 legs")` para listas vacías o de 1 elemento.

**Caveat de independencia (MUST documentar en docstring):** `model_prob` asume
independencia de resultados — optimista en partidos del mismo torneo (correlación
intra-grupo). El UI MUST mostrar aviso visible.

#### Scenario: 3 legs — verificación numérica

- GIVEN legs: `(odds=1.40, p=0.834)`, `(odds=2.75, p=0.491)`, `(odds=1.84, p=0.780)`
- WHEN `combine_parlay(legs)` ejecuta
- THEN `combined_odds=7.084`, `model_prob=0.3194`, `ev=+1.2627` (+126.3%)
- AND `legs_diagnostics=[{+0.168, False}, {+0.350, False}, {+0.435, False}]`
- AND `suggested_without_negatives=None`

#### Scenario: 2 legs, 1 leg −EV → sugerencia mejorada

- GIVEN legs: `(odds=1.85, p=0.60)`, `(odds=1.10, p=0.75)`
- WHEN `combine_parlay(legs)` ejecuta
- THEN `legs_diagnostics[1]={leg_ev=−0.175, is_negative_ev=True}`
- AND cupón completo: `combined_odds=2.035`, `model_prob=0.450`, `ev=−0.084`
- AND `suggested_without_negatives` = [leg `(odds=1.85, p=0.60)`]
- AND ese sub-cupón tendría `ev=+0.110` (+11.0%) — quitando el leg −EV mejora el EV

#### Scenario: Lista vacía — ValueError

- GIVEN `legs=[]`
- WHEN `combine_parlay(legs)`
- THEN lanza `ValueError("Parlay requires at least 2 legs")`

#### Scenario: 1 leg — ValueError

- GIVEN `legs` con 1 elemento
- WHEN `combine_parlay(legs)`
- THEN lanza `ValueError("Parlay requires at least 2 legs")`
