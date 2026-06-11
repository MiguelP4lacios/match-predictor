# Delta for Dashboard Frontend

## MODIFIED Requirements

### Requirement: R1 — Routing

La app MUST implementar react-router-dom v6 con las siguientes rutas:

| Ruta | Vista |
|---|---|
| `/` | Señales (tabla +EV) |
| `/grupos` | Lista 12 grupos |
| `/grupos/:letra` | Detalle grupo + fixtures |
| `/partidos` | Fixtures próximos |
| `/modelo` | Transparencia del modelo |
| `/apuestas` | Registro y seguimiento de apuestas |
| `*` | 404 — "Página no encontrada" |

(Previously: ruta `/paper` → Vista "Registro paper-betting".)

#### Scenario: Deep-link directo a grupo

- GIVEN el usuario navega a `/grupos/K` sin pasar por `/grupos`
- WHEN la app carga
- THEN renderiza el detalle del grupo K (standings + fixtures)

#### Scenario: Ruta desconocida

- GIVEN el usuario navega a `/foo`
- WHEN la app carga
- THEN renderiza la vista 404, sin crash ni pantalla en blanco

#### Scenario: Ruta /paper redirige a /apuestas

- GIVEN el usuario navega a `/paper` (ruta vieja)
- WHEN la app carga
- THEN redirige a `/apuestas` con `<Navigate replace />`

---

### Requirement: R6 — Vista Apuestas

La vista MUST mostrar dos bloques de stats (PAPER / REAL) y una lista de apuestas
con formulario de registro. MUST NOT mezclar monedas ni unidades entre bloques.

(Previously: Vista Paper — un único bloque con `total`, `open`, `settled`, `roi`.)

**Bloque PAPER:** campos `total`, `pending`, `settled`, `won`, `lost`, `roi`.
**Bloque REAL (COP):** mismos campos + `staked` y `returns` formateados en COP.

Formato COP: entero sin decimales con separador de miles (`$12.000`).
Formato pnl: con signo explícito (`+$4.800` / `−$12.000`).
Formato ROI: `null` → `"—"`; `0.20` → `"+20.0%"`; `−0.30` → `"−30.0%"`.
MUST NOT renderizar `"0%"` cuando `roi` es `null` — invariante de honestidad.

**Lista de apuestas:** renderiza filas ordenadas por `placed_at DESC`.
Cada fila MUST mostrar: partido (home vs away), outcome humanizado, cuota, stake,
estado con color (`pending`=gris, `won`=verde, `lost`=rojo), pnl con signo y color.
Botón "Borrar" MUST aparecer solo para `mode=REAL status=PENDING`; al pulsar MUST
pedir confirmación antes de llamar `DELETE /api/v1/bets/{id}`.

#### Scenario: ROI REAL — verificación numérica

- GIVEN `real.staked=24000`, `real.returns=28800`, `real.roi=0.20`
- WHEN la vista renderiza el bloque REAL
- THEN muestra `staked "$24.000"`, `returns "$28.800"`, `roi "+20.0%"`

#### Scenario: ROI null — honestidad

- GIVEN `real.roi=null` (no hay apuestas liquidadas REAL)
- WHEN la vista renderiza el bloque REAL
- THEN muestra `"—"`, NO `"0%"` ni `"0.0%"`

#### Scenario: Borrar con confirmación

- GIVEN apuesta REAL PENDING en lista
- WHEN usuario pulsa "Borrar"
- THEN aparece diálogo de confirmación; al confirmar llama `DELETE /api/v1/bets/{id}`;
  la fila desaparece de la lista

---

### Requirement: R6A — Formulario "Registrar Apuesta"

La vista Apuestas MUST incluir formulario standalone para crear apuestas REAL.

Campos del formulario:

| Campo | Control | Notas |
|-------|---------|-------|
| Partido | `<select>` | MUST listar solo partidos `status=SCHEDULED`; opción por "Home vs Away (fecha)" |
| Outcome | `<select>` | MUST mostrar nombres de equipos: "Local" / "Empate" / "Visitante" |
| Cuota (BetPlay) | `<input type="number">` | Placeholder "1.40"; validación > 1.01 |
| Stake (COP) | `<input type="number">` | Placeholder "$12.000"; validación > 0 |
| Nota | `<input type="text">` | Opcional |

Al enviar MUST llamar `POST /api/v1/bets`. En 201 MUST refrescar la lista de
apuestas y limpiar el formulario. En error MUST mostrar mensaje inline, sin
navegar ni mostrar pantalla en blanco.

El formulario MUST soportar pre-carga vía query params `?match_id=<id>&outcome=<HOME|DRAW|AWAY>` — los campos correspondientes se pre-rellenan y el foco recae en el campo cuota.

#### Scenario: Registro exitoso

- GIVEN formulario con `match_id=42`, `outcome=HOME`, `odds_taken=1.40`, `stake=12000`
- WHEN usuario envía
- THEN `POST /api/v1/bets` recibe esos valores; en 201 la lista muestra la nueva
  apuesta con `status=pending`, `stake=$12.000`, `odds=1.40`

#### Scenario: Pre-carga por query params

- GIVEN usuario navega a `/apuestas?match_id=42&outcome=HOME`
- WHEN el formulario monta
- THEN el selector de partido pre-selecciona el partido 42 y el outcome HOME;
  foco en campo cuota

#### Scenario: Error de validación inline

- GIVEN `odds_taken=0.80` (inválido)
- WHEN usuario envía
- THEN muestra error inline "Cuota debe ser > 1.01", formulario no se limpia

---

### Requirement: R2B-SignalCard-Register — Botón secundario en SignalCard

`SignalCard` MUST incluir un botón secundario `"Registrar apuesta"` (además del CTA
`"¿Por qué? →"` existente). Al pulsar MUST navegar a
`/apuestas?match_id={match_id}&outcome={outcome_code}`.

(Previously: SignalCard no tenía botón de registro; solo "¿Por qué? →".)

#### Scenario: Navegación con pre-fill

- GIVEN signal con `match_id=42`, `outcome_code=HOME`
- WHEN usuario pulsa "Registrar apuesta" en la SignalCard
- THEN navega a `/apuestas?match_id=42&outcome=HOME`; formulario pre-rellena partido y outcome

---

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
| `ModeStats` | `total: number, pending: number, settled: number, won: number, lost: number, staked: string\|null, returns: string\|null, roi: number\|null` |
| `BetsPageStats` | `paper: ModeStats, real: ModeStats` |
| `BetLog` | `id: number, mode: string, status: string, match_id: number\|null, outcome_code: string\|null, odds_taken: string, stake: string, pnl: string\|null, settled_result: string\|null, settled_at: string\|null, placed_at: string\|null, note: string\|null, value_signal_id: number\|null` |

(Previously: `PaperStats` con `total, open, settled, roi: number|null`. Reemplazado
por `ModeStats` + `BetsPageStats`. `PaperStats` puede mantenerse como alias para
compatibilidad durante transición.)

`recommended_stake` MUST ser typed como `string` — la API lo retorna como string.

---

### Requirement: R10 — Testing

Los tests MUST usar vitest + Testing Library. Lista completa MUST cubrir:

| Test | Tipo |
|---|---|
| `formatEdge(0.0832)` → `"8.3%"` | unit formatter |
| `formatProbability(0.4202)` → `"42.0%"` | unit formatter |
| `formatStake("18.93")` → `"$18.93"` | unit formatter |
| `formatOdds(1.47)` → `"1.47"` | unit formatter |
| `formatROI(null)` → `"—"` | unit formatter |
| `formatROI(0.125)` → `"+12.5%"` | unit formatter |
| `formatROI(0.20)` → `"+20.0%"` | unit formatter |
| `formatCOP(12000)` → `"$12.000"` | unit formatter |
| `formatPnl(4800)` → `"+$4.800"` | unit formatter |
| `formatPnl(-12000)` → `"−$12.000"` | unit formatter |
| `<SignalCard signal={...}>` muestra "¿Por qué? →" y "Registrar apuesta" | component |
| `<SignalCard ...>` "Registrar apuesta" navega a `/apuestas?match_id=...&outcome=...` | component |
| `groupSignals([...])` retorna grupos en orden de primera aparición | unit |
| `<ExplainDrawer>` cierra con Escape | component |
| `<ExplainDrawer>` muestra skeleton mientras carga | component |
| `<ExplainDrawer>` muestra "Error al cargar explicación" si fetch falla | component |
| `glossary["edge"]` contiene la cadena "Ventaja" | unit |
| `<GroupCard standings={...}>` respeta orden del servidor | component |
| `<ModeStatsBlock stats={...} roi={null}>` muestra `"—"` | component |
| `<ModeStatsBlock stats={...} roi={0.20}>` muestra `"+20.0%"` | component |
| `<BetRegisterForm>` pre-rellena match+outcome desde query params | component |
| `<BetRegisterForm>` muestra error inline en 422 | component |
| `<BetList>` botón "Borrar" solo visible para REAL PENDING | component |

(Previously: incluía test de `<PaperStats roi={null}>` — reemplazado por
`<ModeStatsBlock>`. Agregados tests de formatCOP, formatPnl, BetRegisterForm,
BetList, SignalCard con nuevo botón.)
