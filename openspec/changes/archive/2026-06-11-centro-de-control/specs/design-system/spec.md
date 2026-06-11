# Design System Specification

## Purpose

Sistema de diseño compartido que provee tokens CSS (light + dark), configuración Tailwind
`darkMode:'class'`, ~10-12 primitivas reutilizables, resolución de tema automática y
mapeo de banderas emoji para las 48 selecciones WC26.

---

## Requirements

### Requirement: DS1 — Design Tokens (CSS Custom Properties)

El sistema MUST definir tokens CSS en `:root` (tema light) y `.dark` (tema dark) con
exactamente las siguientes variables semánticas:

| Token | Rol |
|-------|-----|
| `--bg` | Fondo de página |
| `--surface` | Fondo de cards/componentes |
| `--text` | Texto principal |
| `--text-muted` | Texto secundario/atenuado |
| `--border` | Bordes y separadores |
| `--accent` | Acción primaria / CTA |
| `--positive` | Indicador positivo (+EV, ganado) |
| `--negative` | Indicador negativo (−EV, perdido) |

Tailwind MUST estar configurado con `darkMode: 'class'` y colores semánticos que
referencien estos tokens (ej. `bg: 'var(--bg)'`). La clase `dark` se aplica en `<html>`.

#### Scenario: Tokens disponibles en light y dark

- GIVEN el sistema carga con tema light (sin clase `dark` en `<html>`)
- WHEN un componente usa `bg-surface text-text-muted`
- THEN los tokens resuelven los valores del tema light

- GIVEN la clase `dark` está presente en `<html>`
- WHEN un componente usa `bg-surface text-text-muted`
- THEN los tokens resuelven los valores del tema dark

---

### Requirement: DS2 — Resolución de Tema

El sistema MUST inicializar el tema en este orden de prioridad:
1. Valor persistido en `localStorage` bajo clave `"theme"` (`"light"` | `"dark"`).
2. `prefers-color-scheme` del sistema operativo.
3. Fallback: `"light"`.

El sistema MUST persistir en `localStorage` la elección manual del usuario.
El sistema MUST NOT producir flash-of-wrong-theme: la lógica de resolución MUST
ejecutarse en un `<script>` inline síncrónico antes que cualquier CSS de componentes.

El componente `ThemeToggle` MUST cambiar el tema activo al alternar y MUST actualizar
`localStorage` inmediatamente.

#### Scenario: Persistencia entre recargas

- GIVEN el usuario selecciona tema dark y recarga la página
- WHEN la app inicializa
- THEN el tema dark se aplica sin parpadeo visible; `localStorage["theme"] === "dark"`

#### Scenario: AUTO — sistema en dark, sin preferencia guardada

- GIVEN no hay valor en `localStorage["theme"]`
- AND `prefers-color-scheme: dark` está activo en el sistema
- WHEN la app inicializa
- THEN el tema dark se aplica automáticamente

#### Scenario: Toggle manual sobreescribe sistema

- GIVEN el sistema tiene `prefers-color-scheme: dark`
- AND el usuario pulsa ThemeToggle para cambiar a light
- THEN el tema cambia a light; `localStorage["theme"] === "light"`
- AND una recarga posterior mantiene light independientemente del sistema

---

### Requirement: DS3 — Primitivas de UI

El sistema MUST proveer estas primitivas en `frontend/src/components/ui/`:

| Componente | Responsabilidad mínima |
|------------|------------------------|
| `Card` | Contenedor con `--surface`, `--border`, padding, radius |
| `Badge` | Etiqueta coloreada (variante: ok/warn/stale/neutral) |
| `Stat` | Par label + valor numérico prominente |
| `Button` | Variantes primary/secondary/ghost, estado disabled |
| `Tabs` | Navegación por pestañas accesible |
| `Sheet` | Overlay deslizable (bottom-sheet en mobile, lateral en desktop) |
| `ThemeToggle` | Botón para alternar tema light/dark |
| `AppShell` | Layout raíz: nav top (laptop) / bottom-tab-bar (mobile) + slot de contenido |
| `StatusBadge` | Indicador 🟢/🟡/🔴 del estado del sistema, siempre visible en el header |
| `FlagLabel` | Nombre de equipo precedido por bandera emoji |

Cada primitiva MUST ser importable desde `@/components/ui/{nombre}`.
Las primitivas MUST NOT importar lógica de negocio ni hooks de datos.

#### Scenario: Card aplica tokens

- GIVEN el tema activo es dark
- WHEN se renderiza `<Card>`
- THEN el fondo usa `var(--surface)` y el borde usa `var(--border)` del tema dark

#### Scenario: Button disabled no dispara acción

- GIVEN `<Button disabled onClick={handler}>`
- WHEN el usuario hace click
- THEN `handler` no se invoca; el elemento tiene `aria-disabled="true"` o `disabled`

#### Scenario: Sheet cierra con Escape en mobile

- GIVEN `<Sheet>` abierto en viewport 375px
- WHEN el usuario presiona Escape
- THEN el Sheet se cierra

---

### Requirement: DS4 — FlagLabel y lib/flags.ts

`lib/flags.ts` MUST exportar una función `getFlag(teamName: string): string` que
mapee el nombre canónico del equipo a su bandera emoji.

El mapeo MUST incluir las 48 selecciones del WC26. Nombres canónicos y banderas
MUST incluir al menos:

| Nombre canónico | Bandera |
|-----------------|---------|
| `"Mexico"` | 🇲🇽 |
| `"United States"` | 🇺🇸 |
| `"South Korea"` | 🇰🇷 |
| `"Côte d'Ivoire"` | 🇨🇮 |
| `"DR Congo"` | 🇨🇩 |
| `"Czech Republic"` | 🇨🇿 |

Para nombres no reconocidos, `getFlag` MUST retornar `"🏳"` (bandera neutral).
`getFlag` MUST NOT lanzar excepciones para ningún input de tipo string.

El componente `FlagLabel` MUST renderizar `{getFlag(teamName)} {teamName}`.
El wordmark de la app MUST usar "WC26"; MUST NOT usar marcas ni logos FIFA.

#### Scenario: Mapeo exacto de equipos conocidos

- GIVEN `getFlag("Mexico")`
- THEN retorna `"🇲🇽"`

- GIVEN `getFlag("South Korea")`
- THEN retorna `"🇰🇷"`

- GIVEN `getFlag("Côte d'Ivoire")`
- THEN retorna `"🇨🇮"`

#### Scenario: Fallback para nombre desconocido

- GIVEN `getFlag("Equipo Ficticio")`
- THEN retorna `"🏳"` sin lanzar excepción

#### Scenario: FlagLabel renderiza flag + nombre

- GIVEN `<FlagLabel teamName="DR Congo" />`
- WHEN renderiza
- THEN el texto visible contiene "🇨🇩" y "DR Congo"

---

### Requirement: DS5 — AppShell y Nav Responsive

`AppShell` MUST implementar:
- En viewport ≥ 1024px (`lg`): barra de navegación **top**, contenido centrado.
- En viewport < 1024px: barra de navegación **bottom-tab-bar** fija al pie, estilo FotMob.

La navegación MUST incluir accesos a: Señales, Grupos, Partidos, Modelo, Apuestas, Estado.
`StatusBadge` MUST ser visible en el header/top-nav en todo momento.
El layout MUST NOT producir scroll lateral en ninguna ruta a viewport 360px.

#### Scenario: Nav bottom en mobile

- GIVEN viewport 390px de ancho
- WHEN la app renderiza AppShell
- THEN la barra de navegación aparece fija al pie de la pantalla
- AND no hay scroll horizontal en ninguna ruta

#### Scenario: Nav top en laptop

- GIVEN viewport 1280px de ancho
- WHEN la app renderiza AppShell
- THEN la barra de navegación aparece en la parte superior
- AND StatusBadge es visible en el header
