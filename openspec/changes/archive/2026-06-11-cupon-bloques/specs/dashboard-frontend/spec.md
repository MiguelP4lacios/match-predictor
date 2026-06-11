# Delta for Dashboard Frontend

## ADDED Requirements

### Requirement: R11 — CuponDrawer (bet-slip)

La app MUST incluir un drawer lateral `CuponDrawer` estilo bet-slip de BetPlay.

El estado del cupón MUST vivir en contexto global (o store) accesible desde cualquier
componente. El cupón MUST permitir agregar y quitar legs individualmente.

**CuponDrawer MUST mostrar:**
- Lista de legs agregados: partido (home vs away), outcome humanizado, input `<input type="number">` para cuota BetPlay (odds_taken, placeholder "1.40", validación > 1)
- Cuota combinada + prob. modelo + EV (live, actualizados en cada cambio de cuota vía `POST /api/v1/parlays/preview`)
- Warnings individuales por leg con `is_negative_ev=true`: "⚠ Este leg reduce el EV del cupón"
- Banner fijo "⚠ EV calculado bajo independencia — puede sobreestimar el edge en partidos del mismo torneo"
- Stake (COP): `<input type="number">` → `potential_return` live
- Botón "Registrar cupón" → `POST /api/v1/parlays` → en 201 limpia el cupón y refresca lista de parlays

El front MUST NOT calcular cuota combinada, model_prob ni EV — SOLO muestra lo que
retorna el endpoint `preview`. El endpoint MUST llamarse con debounce (≥300 ms).

(Previously: no existía componente de cupón combinado.)

#### Scenario: EV live al ingresar cuotas

- GIVEN CuponDrawer con 3 legs, cuotas `[1.40, 2.75, 1.84]` ingresadas
- WHEN el usuario completa la última cuota (debounce dispara preview)
- THEN muestra `combined_odds=7.084`, `model_prob=31.9%`, `ev=+126.3%`

#### Scenario: Warning leg −EV visible

- GIVEN CuponDrawer con leg de `odds_taken=1.10` cuya `p_model=0.75` (−EV)
- WHEN preview retorna `legs_diagnostics[i].is_negative_ev=true`
- THEN ese leg muestra "⚠ Este leg reduce el EV del cupón"

#### Scenario: Stake → retorno potencial

- GIVEN cupón con `combined_odds=7.084` y `stake=5000`
- WHEN preview responde
- THEN muestra `potential_return=$35.420` (COP, separador de miles)

#### Scenario: Registrar cupón — éxito

- GIVEN cupón válido con 3 legs y stake ingresado
- WHEN usuario pulsa "Registrar cupón"
- THEN `POST /api/v1/parlays` recibe los legs; en HTTP 201 el drawer se limpia

#### Scenario: Cupón vacío — botón deshabilitado

- GIVEN CuponDrawer con 0 legs
- WHEN el drawer está abierto
- THEN "Registrar cupón" está deshabilitado; no se muestra ningún EV

---

### Requirement: R12 — "Agregar al cupón" en SignalCard y MatchesPage

`SignalCard` MUST incluir botón secundario "Agregar al cupón" (además del CTA
"¿Por qué? →" y "Registrar apuesta" existentes). Al pulsar MUST agregar un leg al
estado del cupón con `{match_id, outcome_code, odds_taken=null}`.

Las filas de partidos en `MatchesPage` MUST incluir botón "Agregar al cupón" con el
mismo comportamiento.

(Previously: SignalCard no tenía acción para cupones combinados.)

#### Scenario: Agregar desde SignalCard

- GIVEN SignalCard de partido 42, `outcome_code=HOME`
- WHEN usuario pulsa "Agregar al cupón"
- THEN cupón recibe leg `{match_id=42, outcome_code=HOME, odds_taken=null}`
- AND el CuponDrawer abre (o badge del cupón incrementa su conteo)

#### Scenario: Quitar leg del cupón

- GIVEN cupón con leg del partido 42
- WHEN usuario pulsa "×" en ese leg dentro del CuponDrawer
- THEN leg se elimina; preview se recalcula; EV se actualiza

---

## MODIFIED Requirements

### Requirement: R7 — TypeScript Types

El proyecto MUST definir tipos hand-written que reflejen los campos de la API.
Tipos críticos (grounded en shapes reales de la API):

| Tipo | Campos clave |
|---|---|
| `Signal` | `id, match_date, home_team, away_team, outcome_code, p_model: number, best_odds: number, bookmaker, edge: number, recommended_stake: string, captured_at` |
| `SignalsList` | `items: Signal[], total: number` |
| `UpcomingMatch` | `id, match_date, home_team, away_team, stage, p_home: number\|null, p_draw: number\|null, p_away: number\|null, low_confidence: boolean` |
| `StandingRow` | `team_name: string, pj: number, g: number, e: number, p: number, gf: number, gc: number, dg: number, pts: number` |
| `GroupDetail` | `name: string, teams: string[], standings: StandingRow[], fixtures: GroupFixture[]` |
| `GroupFixture` | `id, match_date, home_team, away_team, status, p_home: number\|null, p_draw: number\|null, p_away: number\|null` |
| `ModelVersion` | `name: string, backtest: Backtest, calibration: null` |
| `Backtest` | `brier: number, logloss: number, beats_baselines: boolean, calibration_table: CalibrationRow[], baselines: Record<string, number>` |
| `CalibrationRow` | `bin_low: number, bin_high: number, mean_predicted: number, observed_freq: number, count: number` |
| `ModeStats` | `total: number, pending: number, settled: number, won: number, lost: number, staked: number\|null, returns: number\|null, roi: number\|null` |
| `BetsPageStats` | `paper: ModeStats, real: ModeStats` |
| `BetItem` | `id: number, mode: 'real'\|'paper', status: 'pending'\|'won'\|'lost'\|'void', match_id: number\|null, outcome_code: string\|null, odds_taken: number, stake: string, pnl: string\|null, settled_result: string\|null, settled_at: string\|null, placed_at: string, note: string\|null, value_signal_id: number\|null` |
| `ParlayLegInput` | `match_id: number, outcome_code: 'HOME'\|'DRAW'\|'AWAY', odds_taken: number` |
| `LegDiagnostic` | `leg_ev: number, is_negative_ev: boolean` |
| `ParlayPreview` | `combined_odds: number, model_prob: number, ev: number, potential_return: number\|null, legs_diagnostics: LegDiagnostic[]` |
| `ParlayItem` | `id: number, stake: string, odds_taken: number, status: 'pending'\|'won'\|'lost', pnl: string\|null, placed_at: string, legs: ParlayLegInput[]` |

(Previously: sin tipos de parlay — `ParlayLegInput`, `LegDiagnostic`, `ParlayPreview`, `ParlayItem` son nuevos.)

#### Scenario: ParlayPreview tipado correctamente

- GIVEN respuesta del preview endpoint con `combined_odds=7.084`, `ev=1.2627`, `potential_return=35420`
- WHEN el componente accede a `preview.legs_diagnostics[0].is_negative_ev`
- THEN TypeScript no lanza error de tipo; valor es `boolean`
