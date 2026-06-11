# Proposal: Centro de Control — rediseño UX/UI profesional + observabilidad

## Intent
El dashboard actual es plano, sin identidad, no inspira confianza para mover plata real,
y la tabla de grupos obliga a scroll lateral en teléfono. Es nuestro **centro de control**:
debe verse profesional, funcionar en teléfono/iPad/laptop, ser fácil de entender, y —dado
que opera dinero— responder con DATOS "¿corrió la captura de odds? ¿cuántos créditos quedan?".
Referentes: FotMob/Sofascore (móvil, banderas, tablas de grupo que reflowean), Linear/Vercel
(pulido de control-center), dashboards de trading (seriedad de dato vivo).

## Scope

### In Scope
- **Design system** compartido: tokens CSS (light+dark), Tailwind `darkMode:'class'` con colores
  semánticos, ~10-12 primitivas (Card, Badge, Stat, Button, Tabs, Sheet/Drawer, FlagLabel,
  ThemeToggle, AppShell, StatusBadge).
- **Tema AUTO**: sigue `prefers-color-scheme` + toggle manual persistido (localStorage).
- **Identidad**: banderas emoji por equipo/partido/standing (`lib/flags.ts`, nombre→🇲🇽 para 48
  selecciones) + wordmark propio "WC26" (nunca marcas FIFA).
- **Nav responsive**: top-nav en laptop, bottom-tab-bar en teléfono (estilo FotMob); StatusBadge
  siempre visible en el header.
- **Fix tabla grupos (criterio nombrado)**: en teléfono columnas condensadas (Pos·🏳·Equipo·PJ·DG·Pts)
  con fila completa (G/E/P/GF/GC) al expandir; tabla completa en laptop. **Cero scroll lateral.**
- **Rediseño de TODAS las páginas** (Señales, Grupos, Partidos, Modelo, Apuestas) + drawers (Cupón,
  Explain) con las primitivas. Cohesivo, no por fases.
- **Observabilidad**: `GET /api/v1/health/full` (serve-from-DB) con última captura+antigüedad,
  créditos The Odds API restantes, model_version activo, última fecha de resultado FINISHED, último
  tournament_update; cada métrica con verdicto ok/warn/stale + umbral. Página "Estado" (lenguaje de
  hincha) + StatusBadge 🟢/🟡/🔴 que poolea.
- **Logging de captura**: `capture()`/job escribe SyncLog (`odds_api:capture`, rows_inserted,
  credits_remaining, captured_at) → cierra warning de auditoría W5 y la clase de rollback silencioso.

### Out of Scope
- WebSockets/SSE (polling alcanza). Agentes LLM (fase 7). **Cualquier cambio de matemática** de
  modelo/EV/Kelly/staking. Estado de backup (sin marcador) y futures Monte Carlo.

## Capabilities

### New Capabilities
- `design-system`: tokens light/dark, Tailwind dark-class, primitivas base, FlagLabel + `lib/flags.ts`, ThemeToggle, AppShell, nav responsive.
- `health-observability`: endpoint `/api/v1/health/full`, página Estado, StatusBadge con polling y verdictos por umbral.

### Modified Capabilities
- `dashboard-frontend`: las 5 vistas + 2 drawers re-estilados con primitivas; nav top/bottom responsive; tema AUTO; ruta `/estado`; tabla grupos reflow sin scroll lateral; StatusBadge en header. Sin cambios de contrato de datos ni formatters.
- `api-readonly`: agrega requisito `GET /api/v1/health/full` (serve-from-DB, sin recompute).
- `odds-capture`: la captura DEBE persistir una fila SyncLog con rows_inserted + credits_remaining + captured_at.

## Approach
Construir primero el design-system (backbone reusable), migrar cada página a las primitivas sin
tocar hooks de datos ni formatters (rediseño puramente presentacional). Backend aditivo: 1 endpoint
nuevo + columnas `rows_inserted`/`credits_remaining` en `sync_log` (migración Alembic; el upsert
`resource+source` ya existe). Front consume `/health/full` con polling. Invariantes intactas: el
front nunca calcula, todo serve-from-DB, determinista separado.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/components/ui/*` | New | Primitivas + AppShell + StatusBadge |
| `frontend/src/lib/flags.ts`, `theme.ts` | New | Mapa banderas, tema |
| `frontend/src/pages/*` | Modified | Las 6 vistas + nueva `EstadoPage` |
| `frontend/src/components/*` | Modified | Cards/drawers re-estilados |
| `frontend/tailwind.config.js`, `index.css` | Modified | darkMode class + tokens CSS |
| `app/api/health.py`, `app/main.py` | Modified | `/api/v1/health/full` |
| `app/models/sync.py` + migración | Modified | Columnas captura |
| `app/ingestion/odds_pipeline.py`, `app/scheduler/jobs.py` | Modified | Escribir SyncLog |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Regresión en el flujo de apuestas (superficie grande) | Med | Rediseño presentacional; contratos API y hooks intactos; tests verdes |
| Reescritura de tests de componente (markup cambia) | High | Tests adaptan selectores; lógica/formatters intactos; escenarios numéricos preservados |
| Banderas faltantes para nombres canónicos | Low | Fallback 🏳; cobertura de las 48 selecciones |
| Migración sync_log en prod | Low | Columnas nullable, aditivas; sin backfill |

## Rollback Plan
`git revert` del rango: todo es frontend + un endpoint aditivo + columnas nullable en sync_log.
La migración Alembic es reversible (downgrade dropea columnas). Sin cambios de datos ni de matemática.

## Dependencies
- Ninguna externa. The Odds API `last_remaining` ya disponible en `OddsApiSource`.

## Success Criteria
- [ ] Cero scroll lateral en ninguna vista a 360px; tabla de grupos condensa+expande.
- [ ] Tema light y dark ambos diseñados, AUTO por sistema + toggle persistido.
- [ ] Banderas en cada equipo/partido/standing; wordmark propio (cero marcas FIFA).
- [ ] `/api/v1/health/full` responde verdictos ok/warn/stale; StatusBadge refleja salud real.
- [ ] Cada captura deja fila en sync_log → el sistema responde "¿corrió odds?" con DATO.
- [ ] Tests verdes; formatters y escenarios numéricos sin cambios.
