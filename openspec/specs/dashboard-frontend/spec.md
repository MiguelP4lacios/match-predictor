# Dashboard Frontend Specification

## Purpose

App React/Vite/TS que consume los 7 endpoints `/api/v1` y renderiza 5 vistas:
Señales, Grupos, Partidos, Modelo, Paper. UI en español. Sin auth ni SSE.

---

## Requirements

### Requirement: R1 — Routing

La app MUST implementar react-router-dom v6 con las siguientes rutas:

| Ruta | Vista |
|---|---|
| `/` | Señales (tabla +EV) |
| `/grupos` | Lista 12 grupos |
| `/grupos/:letra` | Detalle grupo + fixtures |
| `/partidos` | Fixtures próximos |
| `/modelo` | Transparencia del modelo |
| `/paper` | Registro paper-betting |
| `*` | 404 — "Página no encontrada" |

#### Scenario: Deep-link directo a grupo

- GIVEN el usuario navega a `/grupos/K` sin pasar por `/grupos`
- WHEN la app carga
- THEN renderiza el detalle del grupo K (standings + fixtures)

#### Scenario: Ruta desconocida

- GIVEN el usuario navega a `/foo`
- WHEN la app carga
- THEN renderiza la vista 404, sin crash ni pantalla en blanco

---

### Requirement: R2 — Vista Señales

La vista MUST consumir `GET /api/v1/signals` y renderizar tabla ordenada por
`edge` DESC. Columnas: fecha, partido ("Home vs Away"), outcome (HOME→nombre equipo
local, DRAW→"Empate", AWAY→nombre equipo visitante), p\_model, mejor cuota +
bookmaker, edge, stake. MUST soportar filtro `min_edge` enviado como query param
a la API.

Formatters MUST cumplir exactamente:

| Campo raw | Valor ejemplo | Formato renderizado |
|---|---|---|
| `edge` (float) | `0.0832` | `"8.3%"` (1 decimal) |
| `p_model` (float) | `0.4202` | `"42.0%"` (1 decimal) |
| `recommended_stake` (string) | `"112.7345"` | `"112.73"` (2 dec) |
| `best_odds` (float) | `3.9` | `"3.90"` (2 dec) |

#### Scenario: Tabla señales (verificación orden)

- GIVEN la API retorna items con edge `[0.14, 0.08, 0.20]`
- WHEN la vista renderiza
- THEN las filas aparecen en orden `[0.20, 0.14, 0.08]` DESC

#### Scenario: Formato edge — verificación numérica

- GIVEN `edge = 0.0832`
- WHEN `formatEdge(0.0832)` es invocado
- THEN retorna la cadena `"8.3%"`

#### Scenario: Formato stake — verificación numérica

- GIVEN `recommended_stake = "112.7345"`
- WHEN `formatStake("112.7345")` es invocado
- THEN retorna la cadena `"112.73"`

#### Scenario: Estado vacío

- GIVEN la API retorna `{"items": [], "total": 0}`
- WHEN la vista carga
- THEN renderiza el texto "Sin señales con ese filtro", sin filas ni crash

---

### Requirement: R2A — Agrupación por partido en vista Señales

Las señales MUST mostrarse agrupadas por partido en la vista Señales. La agrupación
es una responsabilidad de presentación exclusiva del cliente: el frontend reagrupa
visualmente los items ya calculados por el servidor; NUNCA recalcula p\_model, edge
ni stake.

Reglas de agrupación:
- Las señales se agrupan por combinación `(match_date, home_team, away_team)`.
- Los grupos preservan el orden de PRIMERA APARICIÓN en la respuesta del servidor
  (el server ordena por `(match_date, id)` → lectura cronológica). El cliente NO
  re-ordena — el servidor es la autoridad. *(Corregido 2026-06-10: la versión
  inicial ordenaba por max edge DESC y rompía el orden cronológico.)*
- Dentro de cada grupo, el orden de señales es el que entrega el servidor
  (el cliente NO altera el orden relativo).
- El encabezado de partido (fecha + "Home vs Away") se renderiza UNA SOLA VEZ
  por grupo, como fila de cabecera antes de las filas de outcome del grupo.
- Grupos con 2 o más señales MUST mostrar el texto de alerta de exposición
  correlacionada: `"⚠ 2 señales sobre este partido — exposición correlacionada"`.
- Grupos con 1 señal NO muestran dicho texto.

La función pura `groupSignals(items: SignalItem[]): SignalGroup[]` encapsula la
lógica de agrupación y ordenación; el componente la llama y renderiza el resultado.

#### Scenario: Orden de grupos = orden del servidor (cronológico) — escenario numérico

- GIVEN la API retorna 3 señales en orden del servidor (`match_date, id`):
  - Partido A (Haiti vs Scotland, 2026-06-20): HOME edge=9.7%, DRAW edge=5.1%
  - Partido B (Brasil vs Argentina, 2026-06-21): AWAY edge=14.1%
  - Orden del servidor: A-HOME(9.7%), A-DRAW(5.1%), B-AWAY(14.1%)
- WHEN la vista renderiza
- THEN los grupos aparecen en este orden:
  1. Grupo A (Haiti vs Scotland, 2026-06-20) — primero por fecha, con señales HOME(9.7%) y DRAW(5.1%) en ese orden
  2. Grupo B (Brasil vs Argentina, 2026-06-21) — segundo por fecha, aunque su edge (14.1%) sea mayor

#### Scenario: Hint de exposición correlacionada

- GIVEN el partido A (Haiti vs Scotland) tiene 2 señales
- WHEN la vista renderiza el grupo A
- THEN muestra "⚠ 2 señales sobre este partido — exposición correlacionada"
  junto al encabezado del grupo

#### Scenario: Sin hint para partido de señal única

- GIVEN el partido B (Brasil vs Argentina) tiene 1 sola señal
- WHEN la vista renderiza el grupo B
- THEN NO muestra texto de exposición correlacionada para ese grupo

---

### Requirement: R3 — Vista Grupos

La vista MUST renderizar 12 cards en orden A–L. Cada card MUST incluir
tabla standings con columnas: Pos, Equipo, PJ, G, E, P, GF, GC, DG, Pts.
El frontend MUST NOT re-ordenar las filas — el servidor es la autoridad
de tiebreakers; el orden de la API se reproduce exactamente.

#### Scenario: Orden standings respetado

- GIVEN `/api/v1/groups/K` retorna standings `[Colombia, DR Congo, Portugal, Uzbekistan]`
- WHEN la vista renderiza el grupo K
- THEN las filas aparecen en ese orden exacto, sin reordenar

#### Scenario: Todos ceros (torneo no iniciado)

- GIVEN todos los partidos del grupo están SCHEDULED (pj=0 todos)
- WHEN la vista carga
- THEN 4 filas con valores `0`, sin crash

#### Scenario: Deep-link `/grupos/:letra` muestra fixtures

- GIVEN grupo K con 6 fixtures en la respuesta de la API
- WHEN el usuario accede a `/grupos/K`
- THEN se muestran los fixtures con `p_home`, `p_draw`, `p_away`;
  los campos `null` no crash

---

### Requirement: R4 — Vista Partidos

La vista MUST consumir `GET /api/v1/matches/upcoming` (retorna array directo,
no envuelto). Partidos agrupados por `match_date`. Cada partido MUST mostrar
barras de probabilidad P(H/D/A) que sumen visualmente al 100%.
Cuando `low_confidence = true`, MUST mostrar "⚠ datos limitados".
Cuando `p_home`, `p_draw`, `p_away` son `null`, las barras MUST NOT renderizarse.

#### Scenario: Flag low_confidence visible

- GIVEN un partido con `low_confidence: true`
- WHEN la vista renderiza ese partido
- THEN muestra "⚠ datos limitados" junto al partido

#### Scenario: Partido sin predicciones

- GIVEN un partido con `p_home: null, p_draw: null, p_away: null`
- WHEN la vista renderiza ese partido
- THEN no se muestran barras de probabilidad, sin crash

---

### Requirement: R5 — Vista Modelo

La vista MUST mostrar: nombre del modelo, tabla Brier/log-loss vs baselines
(del objeto `backtest.baselines`), tabla de calibración (`backtest.calibration_table`
con columnas bin\_low–bin\_high, mean\_predicted, observed\_freq, count), y
veredicto `beats_baselines` como semáforo (verde = true, rojo = false).
MUST NOT inventar valores — todo se lee de la API.

#### Scenario: beats_baselines = true

- GIVEN la API retorna `backtest.beats_baselines: true`
- WHEN la vista renderiza
- THEN muestra semáforo verde y texto "Supera baselines"

#### Scenario: calibration_table vacía

- GIVEN `backtest.calibration_table` es array vacío
- WHEN la vista renderiza
- THEN muestra "Sin datos de calibración", sin crash

---

### Requirement: R6 — Vista Paper

La vista MUST mostrar `total`, `open`, `settled` y `roi`.
Cuando `roi = null`, MUST renderizar `"—"`.
MUST NOT renderizar `"0%"` cuando `roi` es `null` — invariante de honestidad.

Formatter MUST cumplir:

| roi raw | Formato renderizado |
|---|---|
| `null` | `"—"` |
| `0.125` | `"+12.5%"` (1 decimal, signo explícito) |
| `-0.05` | `"-5.0%"` |

#### Scenario: ROI null — verificación honestidad

- GIVEN la API retorna `roi: null`
- WHEN la vista Paper renderiza
- THEN muestra `"—"`, NO `"0%"` ni `"0.0%"`

#### Scenario: ROI positivo — verificación numérica

- GIVEN la API retorna `roi: 0.125` (staked 80.00, returns 90.00)
- WHEN `formatROI(0.125)` es invocado
- THEN retorna `"+12.5%"`

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
| `PaperStats` | `total: number, open: number, settled: number, roi: number\|null` |

`recommended_stake` MUST ser typed como `string` — la API lo retorna como string
(ej. `"120.16"`). `UpcomingMatch` se tipea como array directo, no envuelto.

---

### Requirement: R8 — Data Layer

Las queries de Señales, Grupos y Partidos MUST usar:
`staleTime: 55_000`, `refetchInterval: 60_000`.
Cada vista MUST mostrar skeleton de carga y banner "API no disponible" + botón
"Reintentar" en estado de error. MUST NOT mostrar pantalla en blanco en ningún estado.

#### Scenario: API caída

- GIVEN la API retorna error 5xx
- WHEN la query falla
- THEN la vista muestra banner "API no disponible" con botón "Reintentar",
  sin pantalla en blanco

---

### Requirement: R9 — Build e Integración Docker

El vite dev server MUST configurar proxy `/api` → `http://api:8000` (red compose).
`VITE_API_URL` MUST sobreescribir la URL base en producción.
El servicio `frontend` en `docker-compose.yml` MUST usar `node:22-alpine`,
bind-mount de `./frontend:/app`, y volumen anónimo para `/app/node_modules`
(evitar shadow del bind-mount). Puerto 5173 expuesto.
`npm test` MUST ejecutarse dentro del contenedor.

#### Scenario: Proxy dev sin CORS

- GIVEN la app corre en compose con el servicio `api` en la misma red
- WHEN el cliente hace fetch a `/api/v1/signals`
- THEN el proxy redirige a `http://api:8000/api/v1/signals` sin error CORS

---

### Requirement: R10 — Testing

Los tests MUST usar vitest + Testing Library. MUST cubrir:

| Test | Tipo |
|---|---|
| `formatEdge(0.0832)` → `"8.3%"` | unit formatter |
| `formatProbability(0.4202)` → `"42.0%"` | unit formatter |
| `formatStake("112.7345")` → `"112.73"` | unit formatter |
| `formatOdds(3.9)` → `"3.90"` | unit formatter |
| `formatROI(null)` → `"—"` | unit formatter |
| `formatROI(0.125)` → `"+12.5%"` | unit formatter |
| `<SignalsTable items={...}>` renderiza filas en orden edge DESC | component |
| `<SignalsTable items={[]}>` renderiza "Sin señales con ese filtro" | component |
| `<GroupCard standings={...}>` respeta orden del servidor sin reordenar | component |
| `<PaperStats roi={null}>` muestra `"—"` | component |

E2E tests están FUERA de scope (no vitest-browser, no Playwright).
