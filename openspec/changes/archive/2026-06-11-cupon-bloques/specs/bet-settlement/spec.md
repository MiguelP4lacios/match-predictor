# Delta for Bet Settlement

## MODIFIED Requirements

### Requirement: Settle Engine

La función `settle()` MUST iterar sobre `bet_log WHERE status=PENDING`. Para cada
fila cuyo partido tenga `match.status=FINISHED`, MUST derivar el resultado 1X2,
evaluar WON/LOST, fijar `pnl`, `settled_result`, `settled_at`, y `status`.
MUST NOT modificar filas PENDING cuyo partido no sea FINISHED.

**Parlays (BetLog con `bet_leg` asociados):** `settle()` MUST detectar si el `BetLog`
tiene filas `bet_leg`. Si tiene, MUST aplicar lógica parlay:
- WON iff TODOS los legs tienen partido `FINISHED` y `outcome_code` correcto.
- LOST si CUALQUIER leg tiene partido `FINISHED` y `outcome_code` incorrecto.
- Permanece PENDING si algún leg tiene partido aún no `FINISHED`.
- `pnl` WON = `stake × (combined_odds − 1)`; LOST = `−stake`.
- `combined_odds` se recalcula como Π(leg.odds_taken) en settlement.
- `settled_result = "WON_ALL"` (WON) o `"LOST"` (LOST) para parlays.

**Apuestas simples (sin legs):** lógica intacta, sin cambio.

(Previously: solo liquidaba apuestas simples 1X2; parlays no existían.)

**Derivación del resultado 1X2:**

| Condición | Resultado |
|-----------|-----------|
| `home_score > away_score` | `HOME` |
| `home_score < away_score` | `AWAY` |
| `home_score == away_score` | `DRAW` |

**Fase eliminatoria:** penales no afectan el resultado 1X2 (marcador 90'+ET).

**Evaluación simple:** `WON` iff `bet.outcome_code == resultado_derivado`.

**PnL simple:**
- WON: `pnl = stake × (odds_taken − 1)`
- LOST: `pnl = −stake`

**Resolución por tipo de apuesta:**
- `mode=REAL`: usa `bet.match_id` + `bet.outcome_code` directamente.
- `mode=PAPER`: traversa `value_signal_id → value_signal → prediction_id → prediction`.

#### Scenario: WON simple — verificación numérica

- GIVEN apuesta REAL: `stake=12000.00`, `odds_taken=1.40`, `outcome_code=HOME`,
  partido `home_score=2`, `away_score=0`, `status=FINISHED`
- WHEN `settle()` corre
- THEN `status=WON`, `pnl=+4800.00`, `settled_result=HOME`, `settled_at` se establece
- AND `pnl = 12000 × (1.40 − 1) = 4800.00`

#### Scenario: LOST simple — verificación numérica

- GIVEN apuesta `stake=12000.00`, `odds_taken=1.40`, `outcome_code=HOME`;
  partido `home_score=1`, `away_score=1`, `status=FINISHED`
- WHEN `settle()` corre
- THEN `status=LOST`, `pnl=−12000.00`, `settled_result=DRAW`

#### Scenario: Idempotencia — re-run no modifica settled

- GIVEN apuesta ya con `status=WON`, `pnl=+4800.00`
- WHEN `settle()` corre nuevamente
- THEN 0 filas modificadas; `status`, `pnl`, `settled_at` permanecen igual

#### Scenario: Partido no terminado — intacto

- GIVEN apuesta PENDING cuyo partido tiene `status=SCHEDULED`
- WHEN `settle()` corre
- THEN la apuesta permanece PENDING; `pnl`, `settled_at`, `settled_result` = null

#### Scenario: Penales en knockout — DRAW para 1X2

- GIVEN partido eliminatorio `home_score=1`, `away_score=1`, `status=FINISHED`
- WHEN `settle()` evalúa apuesta `outcome_code=HOME`
- THEN `status=LOST`, `settled_result=DRAW`

#### Scenario: Apuesta PAPER se liquida por signal→prediction

- GIVEN apuesta PAPER `value_signal_id=7` → `prediction.outcome_code=AWAY`,
  `prediction.match_id=55`; partido 55 FINISHED `away_score > home_score`
- WHEN `settle()` corre
- THEN apuesta queda `status=WON`, `settled_result=AWAY`

#### Scenario: Parlay 3 legs todos WON — verificación numérica

- GIVEN BetLog parlay `stake=5000`, legs con `odds_taken=[1.40, 2.75, 1.84]`;
  los 3 partidos FINISHED con outcomes correctos
- WHEN `settle()` corre
- THEN `status=WON`, `pnl=+30420.00` (5000 × (7.084 − 1) = 5000 × 6.084)
- AND `settled_result="WON_ALL"`

#### Scenario: Parlay 1 leg LOST → cupón LOST — verificación numérica

- GIVEN BetLog parlay `stake=5000`, `combined_odds=7.084`;
  leg3 partido FINISHED con outcome incorrecto
- WHEN `settle()` corre
- THEN `status=LOST`, `pnl=−5000.00`, `settled_result="LOST"`

#### Scenario: Parlay con leg aún PENDING → no se liquida

- GIVEN BetLog parlay con 3 legs; 2 partidos FINISHED, 1 SCHEDULED
- WHEN `settle()` corre
- THEN BetLog permanece PENDING; no se toca `pnl` ni `settled_at`
