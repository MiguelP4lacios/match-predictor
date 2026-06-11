# Delta for dashboard-frontend

## ADDED Requirements

### Requirement: R13 — Futures Page

La app MUST incluir una página `FuturesDashboard` en `/futures` que muestre:

1. **Tabla de probabilidades campeón**: 48 equipos ordenados por `p_champion` DESC, con columnas `Pos`, `🏳 Equipo` (via `FlagLabel`), `P(Campeón)`, `P(Final)`, `P(Semi)`, `P(Clasifica)`. Los valores MUST formatearse como porcentaje con 1 decimal (ej. `"18.0%"`).
2. **Panel por grupo**: un `Card` por grupo (A–L) con tabla de `p_advance_group` por equipo.
3. **Señales +EV futuros**: tabla de `value_signal` con `OUTRIGHT_WINNER` — columnas Equipo, P(Modelo), Cuota, P(Justa), Ventaja. Si no hay señales: "Sin señales de futuros disponibles".

Todos los nombres de equipo MUST usar `FlagLabel`. La página MUST usar primitivas del design system: `Card`, `Stat`, `Badge`, `FlagLabel`. MUST NOT usar colores hardcodeados.

Data fetching: `GET /api/v1/futures/probabilities` con `staleTime: 55_000`; `GET /api/v1/futures/signals` con el mismo intervalo. Ambos MUST mostrar skeleton de carga y banner de error con botón "Reintentar".

#### Scenario: Tabla campeón ordenada con banderas

- GIVEN `/api/v1/futures/probabilities` retorna 48 equipos; Brazil `p_champion=0.18` (1er lugar), Argentina `p_champion=0.15` (2do)
- WHEN `FuturesDashboard` renderiza
- THEN Brazil aparece en posición 1 con "🇧🇷 Brazil" (FlagLabel) y "18.0%"; Argentina en posición 2

#### Scenario: Estado vacío sin señales

- GIVEN `/api/v1/futures/signals` retorna `{"items": [], "total": 0}`
- WHEN la sección de señales renderiza
- THEN muestra "Sin señales de futuros disponibles", sin crash ni tabla vacía

#### Scenario: Error de fetch — banner y reintentar

- GIVEN `/api/v1/futures/probabilities` retorna 500
- WHEN la página carga
- THEN muestra skeleton luego banner "API no disponible" con botón "Reintentar"; sin pantalla en blanco

---

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
| `/futures` | Futuros: campeón, avance, señales EV |
| `*` | 404 — "Página no encontrada" |

(Previously: sin ruta `/futures`.)

La navegación principal MUST incluir una entrada "Futuros" que enlace a `/futures`.

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

#### Scenario: Ruta /futures accesible desde nav

- GIVEN la app está montada
- WHEN el usuario hace click en "Futuros" en la navegación
- THEN navega a `/futures` y renderiza `FuturesDashboard` sin crash

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
| `ModeStats` | `total: number, pending: number, settled: number, won: number, lost: number, staked: number\|null, returns: number\|null, roi: number\|null` |
| `BetsPageStats` | `paper: ModeStats, real: ModeStats` |
| `BetItem` | `id: number, mode: 'real'\|'paper', status: 'pending'\|'won'\|'lost'\|'void', match_id: number\|null, outcome_code: string\|null, odds_taken: number, stake: string, pnl: string\|null, settled_result: string\|null, settled_at: string\|null, placed_at: string, note: string\|null, value_signal_id: number\|null` |
| `ParlayLegInput` | `match_id: number, outcome_code: 'HOME'\|'DRAW'\|'AWAY', odds_taken: number` |
| `LegDiagnostic` | `leg_ev: number, is_negative_ev: boolean` |
| `ParlayPreview` | `combined_odds: number, model_prob: number, ev: number, potential_return: number\|null, legs_diagnostics: LegDiagnostic[]` |
| `ParlayItem` | `id: number, stake: string, odds_taken: number, status: 'pending'\|'won'\|'lost', pnl: string\|null, placed_at: string, legs: ParlayLegInput[]` |
| `FutureTeamRow` | `team_id: number, team_name: string, p_champion: number, p_reach_final: number, p_reach_semi: number, p_advance_group: number` |
| `FuturesList` | `items: FutureTeamRow[], total: number` |
| `FutureSignal` | `team_id: number, team_name: string, p_model: number, p_fair: number, edge: number, best_odds: number, bookmaker: string` |

(Previously: sin tipos `FutureTeamRow`, `FuturesList`, `FutureSignal`.)

`recommended_stake` MUST ser typed como `string`. `BetItem.mode` y `BetItem.status` MUST tipificar en minúscula. `FutureTeamRow` fields son `number` (nunca `null` si la simulación corrió; endpoint retorna vacío si no hay datos).

#### Scenario: ParlayPreview tipado correctamente

- GIVEN respuesta del preview endpoint con `combined_odds=7.084`, `ev=1.2627`, `potential_return=35420`
- WHEN el componente accede a `preview.legs_diagnostics[0].is_negative_ev`
- THEN TypeScript no lanza error de tipo; valor es `boolean`

#### Scenario: FutureTeamRow tipado correctamente

- GIVEN respuesta de `/api/v1/futures/probabilities` con `p_champion=0.18`
- WHEN el componente accede a `row.p_champion`
- THEN TypeScript infiere `number`; no hay error de tipo

---
