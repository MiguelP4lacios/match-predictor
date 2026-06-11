# Parlay Bets Specification

## Purpose

Endpoints para previsualizar (sin persistir), registrar y listar parlays. Todo
cálculo es server-side vía `combine_parlay()`; el frontend NUNCA calcula ni recomputa.

---

## Requirements

### Requirement: POST /api/v1/parlays/preview

MUST calcular math del cupón y retornar resultado + diagnóstico por-leg. MUST NOT
persistir. Response HTTP 200.

**Body:** `{ legs: [{match_id, outcome_code, odds_taken}], stake?: float }`

**Validaciones (HTTP 422 si fallan):**
- Cada leg: `match` MUST existir con `status=SCHEDULED`; `outcome_code` MUST ser `HOME|DRAW|AWAY`; `odds_taken` MUST ser `> 1`
- MUST haber ≥2 legs
- `stake` si presente MUST ser `> 0`

#### Scenario: Preview 3 legs — verificación numérica

- GIVEN 3 legs válidos: `odds=[1.40, 2.75, 1.84]`, partidos SCHEDULED, `stake=5000`
- WHEN `POST /api/v1/parlays/preview`
- THEN HTTP 200; `combined_odds=7.084`, `model_prob=0.3194`, `ev=1.2627`
- AND `potential_return=35420.00` (5000 × 7.084)
- AND `legs_diagnostics` con 3 entradas, `is_negative_ev=false` en todas

#### Scenario: odds_taken ≤ 1 en un leg — 422

- GIVEN leg con `odds_taken=0.90`
- WHEN `POST /api/v1/parlays/preview`
- THEN HTTP 422

#### Scenario: Solo 1 leg — 422

- GIVEN `legs` con 1 elemento
- WHEN `POST /api/v1/parlays/preview`
- THEN HTTP 422

#### Scenario: Partido no SCHEDULED — 422

- GIVEN leg con `match_id` de partido `status=FINISHED`
- WHEN `POST /api/v1/parlays/preview`
- THEN HTTP 422

---

### Requirement: POST /api/v1/parlays

MUST persistir 1 `BetLog` (`stake`, `odds_taken`=combinada, `mode`, `status=PENDING`)
+ N filas `bet_leg` (FK `bet_log_id`, `match_id`, `outcome_code`, `odds_taken`).
Response HTTP 201 con `BetLog` + `legs`.

Mismas validaciones que preview.

#### Scenario: Registro parlay 3 legs exitoso

- GIVEN body válido, 3 legs, `stake=5000`, `mode=REAL`
- WHEN `POST /api/v1/parlays`
- THEN HTTP 201; `BetLog.stake=5000`, `BetLog.odds_taken=7.084`, `BetLog.status=pending`
- AND 3 filas `bet_leg` con FK al BetLog creado

#### Scenario: Match ya terminado — 422

- GIVEN leg con `match_id` de partido FINISHED
- WHEN `POST /api/v1/parlays`
- THEN HTTP 422; nada persiste (transacción rollback)

---

### Requirement: GET /api/v1/parlays

MUST retornar lista de parlays con sus legs. Query param opcional `mode=REAL|PAPER`.
Cada ítem MUST incluir array `legs`.

#### Scenario: Filtrado por modo

- GIVEN 2 parlays REAL y 1 PAPER
- WHEN `GET /api/v1/parlays?mode=REAL`
- THEN retorna 2 ítems; cada uno incluye array `legs` con sus filas `bet_leg`

#### Scenario: Sin filtro — todos

- GIVEN 3 parlays (mix REAL/PAPER)
- WHEN `GET /api/v1/parlays`
- THEN retorna los 3 ítems
