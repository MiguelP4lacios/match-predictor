# Delta for dashboard-frontend

## MODIFIED Requirements

### Requirement: R2 — Vista Señales

La vista MUST consumir `GET /api/v1/signals` y renderizar **`SignalCard`s** en el
orden cronológico que devuelve el servidor. MUST NOT renderizar ningún elemento
`<table>`, `<tr>` ni `<td>` en la página Señales.

Cada `SignalCard` MUST mostrar:

| Campo | Formato |
|-------|---------|
| Fecha + partido | "11/06/2026 · Mexico vs South Africa" |
| Apuesta | "🎯 Apostale a México" (outcome humanizado, idioma del equipo) |
| Cuota + bookmaker | "1.47 (gtbets)" |
| Ventaja (edge) | barra/badge coloreado "14.7%" |
| Stake sugerido | "$120.16" |
| Botón CTA | "¿Por qué? →" |

Formatters MUST cumplir exactamente:

| Campo raw | Valor ejemplo | Formato renderizado |
|---|---|---|
| `edge` (float) | `0.0640` | `"6.4%"` (1 decimal) |
| `p_model` (float) | `0.4202` | `"42.0%"` (1 decimal) |
| `recommended_stake` (string) | `"18.93"` | `"$18.93"` (2 dec, signo $) |
| `best_odds` (float) | `1.47` | `"1.47"` (2 dec) |

(Previously: tabla con columnas p_model/edge/stake ordenada por edge DESC; ahora
cards en orden cronológico del server sin tabla)

#### Scenario: Cards en orden cronológico — verificación

- GIVEN la API retorna señales en orden del servidor:
  Mexico HOME (2026-06-11, edge=14.7%), South Korea HOME (2026-06-11, edge=13.2%)
- WHEN la vista renderiza
- THEN SignalCard de Mexico aparece antes que la de South Korea — orden server intacto,
  sin reordenar por edge

#### Scenario: Formato edge/stake — verificación numérica

- GIVEN signal con `edge=0.064`, `recommended_stake="18.93"`, `best_odds=1.47`,
  `bookmaker="gtbets"`
- WHEN el card renderiza
- THEN muestra badge "6.4%", stake "$18.93", cuota "1.47 (gtbets)"

#### Scenario: Estado vacío

- GIVEN la API retorna `{"items": [], "total": 0}`
- WHEN la vista carga
- THEN renderiza "Sin señales con ese filtro", sin cards ni crash

---

### Requirement: R2A — Agrupación por partido en vista Señales

Las señales MUST agruparse visualmente por partido usando `SignalCard`s bajo un
encabezado de grupo (sin tabla). La función pura
`groupSignals(items: SignalItem[]): SignalGroup[]` MUST encapsular la lógica;
el componente la llama y renderiza el resultado.

Reglas de agrupación (comportamiento sin cambios):
- Agrupación por clave `(match_date, home_team, away_team)`.
- Orden de grupos = primera aparición en la respuesta del servidor.
- Orden relativo dentro del grupo = el del servidor.
- Grupos con ≥2 señales MUST mostrar `"⚠ {n} señales sobre este partido — exposición
  correlacionada"` como subtítulo del grupo de cards.
- Grupos con 1 señal NO muestran dicho texto.

(Previously: agrupación mediante fila de cabecera `<tr>` + filas de outcome en tabla;
ahora cards agrupadas visualmente bajo encabezado de grupo, sin tabla)

#### Scenario: Agrupación con hint de exposición — escenario numérico

- GIVEN la API retorna: Haiti HOME (2026-06-20, edge=9.7%), Haiti DRAW (2026-06-20,
  edge=5.1%), Brasil AWAY (2026-06-21, edge=14.1%)
- WHEN la vista renderiza
- THEN grupo Haiti muestra 2 cards con hint "⚠ 2 señales sobre este partido —
  exposición correlacionada"; grupo Brasil muestra 1 card sin hint; orden: Haiti → Brasil

#### Scenario: Sin hint para partido de señal única

- GIVEN el partido Brasil vs Argentina tiene 1 sola señal
- WHEN la vista renderiza ese grupo
- THEN NO muestra texto de exposición correlacionada para ese grupo

---

## ADDED Requirements

### Requirement: R2B — ExplainDrawer

La vista Señales MUST incluir el componente `ExplainDrawer` que:
- MUST abrirse al pulsar "¿Por qué? →" en cualquier `SignalCard`, cargando
  `GET /api/v1/signals/{id}/explain`.
- MUST mostrar skeleton de carga dentro del drawer (no overlay blanco ni spinner global).
- MUST cerrarse con X, tecla Escape, o click fuera del drawer.
- MUST renderizar las secciones de la respuesta con sus `label_es` como títulos y
  valores `formatted` verbatim — MUST NOT interpretar ni recomputar números.
- En error MUST mostrar "Error al cargar explicación" dentro del drawer.
- En mobile (viewport < 640px) MUST renderizarse como bottom sheet a ancho completo.

#### Scenario: Apertura y contenido

- GIVEN signal id=10 con explain disponible (edge="14.7%", stake="120.16")
- WHEN el usuario pulsa "¿Por qué? →" en la SignalCard de Mexico HOME
- THEN el drawer se abre con skeleton, luego muestra bloques edge/p_model/stake/calidad
  con p_model formatted="83.4%", edge formatted="14.7%", recommended_stake="$120.16"

#### Scenario: Cierre por Escape

- GIVEN el ExplainDrawer está abierto
- WHEN el usuario presiona tecla Escape
- THEN el drawer se cierra; foco retorna al botón "¿Por qué? →" del card

#### Scenario: Error de fetch en drawer

- GIVEN el endpoint retorna 500
- WHEN el drawer intenta cargar la explicación
- THEN muestra "Error al cargar explicación" dentro del drawer, sin pantalla en blanco

---

### Requirement: R2C — Glosario inline (lib/glossary.ts)

El módulo `lib/glossary.ts` MUST exportar:
```ts
export const glossary: Record<string, string>
```
con estas entradas exactas (español de hincha):

| Clave | Definición |
|-------|-----------|
| `edge` | "Ventaja — tu probabilidad estimada menos la implícita en la cuota" |
| `de-vig` | "Quitar el margen de la casa para ver la probabilidad justa" |
| `kelly` | "Fórmula para apostar justo lo que vale la ventaja" |
| `elo` | "Puntaje de fuerza del equipo, actualizado tras cada partido" |
| `brier` | "Error cuadrático de las predicciones (menor = mejor)" |
| `calibración` | "Qué tan seguido se cumple lo que el modelo predice" |

El `ExplainDrawer` MUST renderizar un ícono de ayuda (?) junto a cada `label_es` que
coincida con una clave del glosario; al hacer hover/focus MUST mostrar su definición
como tooltip.

#### Scenario: Tooltip de glosario en drawer

- GIVEN el drawer muestra el paso con label_es que contiene "edge"
- WHEN el usuario hace hover/focus en el ícono (?) junto a ese label
- THEN aparece tooltip: "Ventaja — tu probabilidad estimada menos la implícita en la cuota"

#### Scenario: Términos sin entrada — sin tooltip

- GIVEN un label_es sin coincidencia en `glossary`
- WHEN el drawer renderiza ese paso
- THEN no muestra ícono de ayuda para ese paso

---

## REMOVED Requirements

### Requirement: SignalsTable

(Reason: reemplazada por `SignalCard` + `ExplainDrawer`. La vista Señales MUST NOT
renderizar `<table>`. El componente `SignalsTable.tsx` MUST eliminarse del proyecto.)

---

## MODIFIED Requirements

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
| `<SignalCard signal={...}>` muestra "¿Por qué? →", edge="14.7%", stake="$120.16" | component |
| `groupSignals([...])` retorna grupos en orden de primera aparición | unit |
| `<ExplainDrawer>` cierra con Escape | component |
| `<ExplainDrawer>` muestra skeleton mientras carga | component |
| `<ExplainDrawer>` muestra "Error al cargar explicación" si fetch falla | component |
| `glossary["edge"]` contiene la cadena "Ventaja" | unit |
| `<GroupCard standings={...}>` respeta orden del servidor | component |
| `<PaperStats roi={null}>` muestra `"—"` | component |

(Previously: incluía tests de `<SignalsTable>` — reemplazados por tests de `<SignalCard>`
y `<ExplainDrawer>`)

#### Scenario: SignalCard renderiza ventaja y stake

- GIVEN signal con `edge=0.14724`, `recommended_stake="120.16"`, `best_odds=1.47`,
  `bookmaker="gtbets"`, `outcome_code="HOME"`, `home_team="Mexico"`
- WHEN `<SignalCard signal={signal} onExplain={() => {}} />` renderiza
- THEN muestra badge "14.7%", stake "$120.16", cuota "1.47 (gtbets)", texto "Apostale a México"
