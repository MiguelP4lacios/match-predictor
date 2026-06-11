# Bet Settlement Specification

## Purpose

Motor determinista e idempotente que liquida `bet_log` PENDING contra `match`
FINISHED (1X2: HOME/DRAW/AWAY por marcador). Sin LLM. Corre en
`tournament_update.sh` tras ingest y como CLI standalone.

---

## Requirements

### Requirement: Settle Engine

La función `settle()` MUST iterar sobre `bet_log WHERE status=PENDING`. Para cada
fila cuyo partido tenga `match.status=FINISHED`, MUST derivar el resultado 1X2,
evaluar WON/LOST, fijar `pnl`, `settled_result`, `settled_at`, y `status`.
MUST NOT modificar filas PENDING cuyo partido no sea FINISHED.

**Derivación del resultado (1X2):**

| Condición | Resultado |
|-----------|-----------|
| `home_score > away_score` | `HOME` |
| `home_score < away_score` | `AWAY` |
| `home_score == away_score` | `DRAW` |

**Fase de grupos:** no existe ET ni penales — solo se aplica la tabla anterior.

**Fase eliminatoria:** `home_score`/`away_score` almacenan el marcador al final de
90'+ET (convención martj42). Si el partido se definió por penales, el marcador
permanece empatado (ej. 1-1). Settlement MUST resolver como `DRAW` para 1X2;
los penales NO afectan el outcome 1X2.

**Evaluación:** `WON` iff `bet.outcome_code == resultado_derivado`.

**PnL:**
- WON: `pnl = stake × (odds_taken − 1)`
- LOST: `pnl = −stake`

**Resolución del partido por tipo de apuesta:**
- `mode=REAL`: usa `bet.match_id` + `bet.outcome_code` directamente.
- `mode=PAPER`: traversa `value_signal_id → value_signal → prediction_id →
  prediction` para obtener `match_id` y `outcome_code`.

#### Scenario: WON — verificación numérica

- GIVEN apuesta REAL: `stake=12000.00`, `odds_taken=1.40`, `outcome_code=HOME`,
  partido con `home_score=2`, `away_score=0`, `status=FINISHED`
- WHEN `settle()` corre
- THEN `status=WON`, `pnl=+4800.00`, `settled_result=HOME`, `settled_at` se establece
- AND `pnl = 12000 × (1.40 − 1) = 12000 × 0.40 = 4800.00`

#### Scenario: LOST — verificación numérica

- GIVEN misma apuesta (`stake=12000.00`, `odds_taken=1.40`, `outcome_code=HOME`),
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
  (penales decidieron el avance)
- WHEN `settle()` evalúa apuesta `outcome_code=HOME`
- THEN `status=LOST`, `settled_result=DRAW` (penales no alteran 1X2)

#### Scenario: Apuesta PAPER se liquida por signal→prediction

- GIVEN apuesta PAPER `value_signal_id=7` → `prediction.outcome_code=AWAY`,
  `prediction.match_id=55`; partido 55 FINISHED `away_score > home_score`
- WHEN `settle()` corre
- THEN apuesta queda `status=WON`, `settled_result=AWAY`

---

### Requirement: CLI Standalone

MUST existir un runner `python -m app.model.run_settle` que invoque `settle()` e
imprima el número de filas liquidadas. Exit 0 en éxito, non-zero en excepción.

#### Scenario: Ejecución imprime conteo

- GIVEN 3 apuestas PENDING con partidos FINISHED
- WHEN `python -m app.model.run_settle` corre
- THEN imprime `"Settled: 3 bets"`, exit 0

#### Scenario: Sin nada que liquidar

- GIVEN todas las apuestas PENDING tienen partidos SCHEDULED
- WHEN `python -m app.model.run_settle` corre
- THEN imprime `"Settled: 0 bets"`, exit 0
