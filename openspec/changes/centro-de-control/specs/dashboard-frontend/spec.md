# Delta for Dashboard Frontend

## ADDED Requirements

### Requirement: R-DS — Aplicación del Design System

Todas las vistas (Señales, Grupos, Partidos, Modelo, Apuestas) y los drawers (CuponDrawer,
ExplainDrawer) MUST ser re-estilados usando las primitivas del design system
(`Card`, `Badge`, `Stat`, `Button`, `Sheet`, `FlagLabel`, `StatusBadge`).

El rediseño MUST ser exclusivamente presentacional: contratos de API, hooks de datos,
formatters y escenarios numéricos existentes MUST permanecer sin cambios.
Los componentes MUST usar tokens CSS (`--bg`, `--surface`, etc.) via clases Tailwind
semánticas — MUST NOT usar colores hardcodeados (ej. `bg-white`, `text-gray-900`).

#### Scenario: Colores desde tokens, no hardcodeados

- GIVEN la vista Señales renderiza en tema dark
- WHEN se inspecciona el fondo de un SignalCard
- THEN el color proviene de `var(--surface)` (clase `bg-surface`), no de un valor hardcodeado

#### Scenario: Comportamiento existente preservado

- GIVEN señales con edge=0.064 y stake="18.93"
- WHEN la vista Señales renderiza después del rediseño
- THEN muestra "6.4%" y "$18.93" — idéntico al comportamiento pre-rediseño

---

### Requirement: R-FLAGS — Banderas en Equipos

Todos los lugares donde se muestra un nombre de equipo (SignalCard, standings, fixtures,
lista de apuestas, CuponDrawer) MUST usar el componente `FlagLabel`.
El front MUST NOT mostrar nombres de equipo sin bandera en ninguna vista post-rediseño.

#### Scenario: FlagLabel en SignalCard

- GIVEN SignalCard para "Mexico vs South Korea"
- WHEN renderiza
- THEN home team muestra "🇲🇽 Mexico" y away team muestra "🇰🇷 South Korea"

#### Scenario: Fallback para equipo sin mapeo

- GIVEN un equipo con nombre no mapeado en lib/flags.ts
- WHEN FlagLabel renderiza
- THEN muestra "🏳 {nombre}" sin crash

---

### Requirement: R-GROUPS-RESPONSIVE — Tabla de Grupos sin Scroll Lateral

La tabla de standings de grupos MUST implementar un layout responsive SIN scroll
horizontal (`overflow-x` MUST NOT ser el mecanismo de adaptación en mobile).

En viewport < 640px (mobile), la tabla MUST mostrar columnas condensadas:
`Pos`, `🏳 Equipo`, `PJ`, `DG`, `Pts`.

Al tocar/hacer click en una fila, MUST expandir la fila para revelar las columnas
adicionales: `G`, `E`, `P`, `GF`, `GC` — inline bajo la fila o como acordeón.

En viewport ≥ 640px (desktop), MUST mostrar todas las columnas sin expansión.

Las dos primeras posiciones de cada grupo MUST tener color de fondo diferenciado
(zona de clasificación). El orden de filas MUST seguir siendo el del servidor (sin
re-ordenar por el front).

#### Scenario: Mobile — columnas condensadas, sin scroll lateral

- GIVEN viewport 360px
- WHEN GroupCard renderiza la tabla del Grupo A
- THEN solo se ven Pos/🏳 Equipo/PJ/DG/Pts; no hay scroll horizontal; `overflow-x` no está en `scroll` ni `auto`

#### Scenario: Mobile — expansión de fila revela detalle

- GIVEN viewport 390px, tabla condensada del Grupo K
- WHEN el usuario toca la fila de Colombia
- THEN la fila muestra G/E/P/GF/GC de Colombia; las demás filas sin expandir no los muestran

#### Scenario: Desktop — tabla completa

- GIVEN viewport 1280px
- WHEN GroupCard renderiza
- THEN todas las columnas (Pos, Equipo, PJ, G, E, P, GF, GC, DG, Pts) son visibles sin acción

#### Scenario: Zona de clasificación coloreada

- GIVEN grupo con 4 equipos, standings `[Colombia, DR Congo, Portugal, Uzbekistan]`
- WHEN la tabla renderiza
- THEN Colombia y DR Congo tienen fondo diferenciado; Portugal y Uzbekistan no

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
| `/estado` | Estado del sistema (observabilidad) |
| `*` | 404 — "Página no encontrada" |

(Previously: no existía la ruta `/estado`; ruta `/paper` era `Navigate` a `/apuestas`.)

#### Scenario: Deep-link directo a grupo

- GIVEN el usuario navega a `/grupos/K` sin pasar por `/grupos`
- WHEN la app carga
- THEN renderiza el detalle del grupo K (standings + fixtures)

#### Scenario: Ruta desconocida

- GIVEN el usuario navega a `/foo`
- WHEN la app carga
- THEN renderiza la vista 404, sin crash ni pantalla en blanco

#### Scenario: Ruta /estado carga página de observabilidad

- GIVEN el usuario navega a `/estado`
- WHEN la app carga
- THEN renderiza la página Estado con métricas del sistema; sin crash

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
| `<SignalCard signal={...}>` muestra "¿Por qué? →", edge="14.7%", stake="$120.16" | component |
| `groupSignals([...])` retorna grupos en orden de primera aparición | unit |
| `<ExplainDrawer>` cierra con Escape | component |
| `<ExplainDrawer>` muestra skeleton mientras carga | component |
| `<ExplainDrawer>` muestra "Error al cargar explicación" si fetch falla | component |
| `glossary["edge"]` contiene la cadena "Ventaja" | unit |
| `<GroupCard standings={...}>` respeta orden del servidor | component |
| `<PaperStats roi={null}>` muestra `"—"` | component |
| `getFlag("Mexico")` → `"🇲🇽"` | unit lib/flags |
| `getFlag("Equipo Desconocido")` → `"🏳"` | unit lib/flags |
| `<GroupCard standings={...}>` en viewport 360px no produce scroll horizontal | component |
| `<StatusBadge health={allOk}>` muestra 🟢 | component |
| `<StatusBadge health={withWarn}>` muestra 🟡 | component |
| `resolveTheme("dark", "dark")` no produce flash | unit lib/theme |

(Previously: no incluía tests de flags, tema, responsive GroupCard ni StatusBadge.)

#### Scenario: SignalCard renderiza ventaja y stake

- GIVEN signal con `edge=0.14724`, `recommended_stake="120.16"`, `best_odds=1.47`,
  `bookmaker="gtbets"`, `outcome_code="HOME"`, `home_team="Mexico"`
- WHEN `<SignalCard signal={signal} onExplain={() => {}} />` renderiza
- THEN muestra badge "14.7%", stake "$120.16", cuota "1.47 (gtbets)", texto "Apostale a México"

#### Scenario: getFlag cobertura exacta

- GIVEN `getFlag("Côte d'Ivoire")`
- THEN retorna `"🇨🇮"`

- GIVEN `getFlag("DR Congo")`
- THEN retorna `"🇨🇩"`
