# Tasks: Centro de Control — rediseño UX/UI + observabilidad

## Phase 1: Backend Observabilidad [Agent A]

- [x] 1.1 Crear `migrations/versions/m8_sync_log_capture_fields.py`: agrega `rows_inserted Integer nullable` y `credits_remaining Integer nullable` a `sync_log`; `downgrade` dropea ambas. `down_revision='m7parlay'`.
- [x] 1.2 Modificar `app/models/sync.py`: agregar columnas `rows_inserted` y `credits_remaining` al modelo `SyncLog` (nullable).
- [x] 1.3 **TEST RED** `tests/test_sync_log_capture.py`: tras job con source fake → assert fila `odds_api:capture` con `rows_inserted` y `credits_remaining`; segunda ejecución → exactamente 1 fila (upsert).
- [x] 1.4 Modificar `app/scheduler/jobs.py` `capture_odds_job`: upsert fila `sync_log(resource='odds_api:capture', source=ODDS_API, last_fetched_at=now(), rows_inserted=result['inserted'], credits_remaining=int(last_remaining), status='ok')` tras `pipeline.capture()`. → test verde.
- [x] 1.5 Crear `app/model/health_status.py`: función pura `get_health(session)` con umbrales (ok <4h, warn <10h, stale ≥10h; credits ok ≥100, warn <100); retorna `HealthFull` con `overall=peor`.
- [x] 1.6 **TEST RED** `tests/test_health_status.py`: escenarios — `last_fetched_at` hace 2h → ok; 12h → stale; `credits_remaining=50` → warn; sin fila → stale. → verde.
- [x] 1.7 Crear `app/api/routers/health_full.py`: `GET /api/v1/health/full` llama `get_health(session)`; devuelve `HealthFull` sin llamadas externas.
- [x] 1.8 **TEST RED** `tests/test_health_full_router.py`: TestClient — 200 + shape completo; empty-state `last_at=null` sin 500. → verde.
- [x] 1.9 Modificar `app/main.py`: `include_router(health_full_router, prefix='/api/v1')`.

## Phase 2: Design System — Foundation [Agent B]

- [ ] 2.1 Modificar `frontend/index.html`: script inline en `<head>` anti-flash — lee `localStorage['theme']`; si system usa `matchMedia`; setea `<html class="dark">` antes de React.
- [ ] 2.2 Modificar `frontend/src/index.css`: tokens `:root` y `.dark` (8 variables: `--bg`, `--surface`, `--text`, `--text-muted`, `--border`, `--accent`, `--positive`, `--negative`).
- [ ] 2.3 Modificar `frontend/tailwind.config.js`: `darkMode:'class'`; `colors` semánticos → `var(--*)`.
- [ ] 2.4 Crear `frontend/src/context/ThemeContext.tsx`: `ThemePref` (`light|dark|system`), `resolved`, `setTheme`, persistencia `localStorage`.
- [ ] 2.5 **TEST RED** `frontend/src/context/ThemeContext.test.tsx`: system→dark sin preferencia; toggle sobreescribe; recarga persiste. → verde.
- [ ] 2.6 Crear `frontend/src/lib/flags.ts`: `getFlag(name): string` — mapa `name→ISO2→emoji` para 48 selecciones WC26; overrides England/Scotland (tag sequences); fallback `'🏳'`; no lanza excepciones.
- [ ] 2.7 **TEST RED** `frontend/src/lib/flags.test.ts`: `Mexico→🇲🇽`, `South Korea→🇰🇷`, `Côte d'Ivoire→🇨🇮`, `DR Congo→🇨🇩`, desconocido→`🏳`. → verde.
- [ ] 2.8 Crear las 12 primitivas en `frontend/src/ui/`: `Card`, `Badge`, `Stat`, `Button`, `Tabs`, `Sheet`, `FlagLabel`, `ThemeToggle`, `StatusBadge` (poll `/health/full` 60s, peor veredicto), `AppShell` (top-nav ≥lg / bottom-tab <lg, FAB coexiste, `StatusBadge` en header), `Spinner`, `ErrorState`.
- [ ] 2.9 **TEST RED** `frontend/src/ui/*.test.tsx`: render props mínimas por primitiva; `StatusBadge` — allOk→🟢, withWarn→🟡, withStale→🔴, error-fetch→🔴; `AppShell` — nav bottom en 390px, nav top en 1280px. → verde.
- [ ] 2.10 Agregar `getHealthFull()` y tipo `HealthFull` a `frontend/src/api/client.ts`.

## Phase 3: Shell + Nav + Estado [Agent B, tras 2]

- [ ] 3.1 Modificar `frontend/src/App.tsx`: envolver en `ThemeProvider`; usar `AppShell`; agregar ruta `/estado` → `EstadoPage`; remover rutas `ErrorBanner`/`Loading` sueltos; `*` → 404.
- [ ] 3.2 Crear `frontend/src/pages/EstadoPage.tsx`: consume `getHealthFull()`; muestra tarjeta `Stat` por métrica (etiquetas en español de hincha); tiempo relativo "hace Xh"; verdicto coloreado via `Badge`. No computa verdictos.
- [ ] 3.3 **TEST RED** `frontend/src/pages/EstadoPage.test.tsx`: render métricas; `age_hours=2` → "hace 2h"; stale → fila en rojo. → verde.

## Phase 4: Re-estilado de Páginas [Agent C, depende de B]

- [ ] 4.1 Modificar `frontend/src/components/GroupCard.tsx`: reflow `hidden md:table-cell` + `expandedRow` (estado JS); zona classify top-2 con `var(--qualify)`; sin `overflow-x-scroll`. Tests RTL: columnas condensadas 360px; expand tap revela G/E/P; desktop muestra todo.
- [ ] 4.2 Re-estilizar `SignalsPage`, `SignalCard`, `SignalCardGroup`: usar `Card/Badge/FlagLabel`; edge fuerte destacado. Tests actualizados (formatters y escenarios numéricos intactos).
- [ ] 4.3 Re-estilizar `GroupsPage`, `GroupDetailPage`: usar `Card/FlagLabel`. Tests de render actualizados.
- [ ] 4.4 Re-estilizar `MatchesPage`, `MatchProbBar`: usar `FlagLabel`, sticky date-headers, tokens. Tests actualizados.
- [ ] 4.5 Re-estilizar `ModelPage`: stat cards + tabla calibración con `Stat/Card`. Tests actualizados.
- [ ] 4.6 Re-estilizar `BetsPage`, `BetForm`, `BetList`: ROI hero con `Stat`; tokens light/dark. Tests actualizados.
- [ ] 4.7 Modificar `CuponDrawer`, `ExplainDrawer`: chrome vía `<Sheet>`, lógica y estado intactos. Tests `ExplainDrawer` cierra con Escape; skeleton mientras carga. Eliminar `ErrorBanner.tsx` y `Loading.tsx` (reemplazados por `ui/ErrorState`, `ui/Spinner`).

## Phase 5: Cierre [secuencial, tras A+B+C]

- [ ] 5.1 Correr suite completa en Docker — `pytest` (BE) y `vitest` (FE) → todas verdes. Corregir los ~160 tests de markup con nuevos selectores (lógica intacta).
- [ ] 5.2 `ruff check . && ruff format .` — sin errores.
- [ ] 5.3 `npm run build` en Docker — sin errores de TS/Vite.
- [ ] 5.4 Deploy VPS: `alembic upgrade head` (m8); `rsync` + build `api`+`frontend`; `docker compose up -d`.
- [ ] 5.5 Smokes reales: `GET /api/v1/health/full` por URL pública → JSON con 4 métricas y verdictos; dashboard 200; sin scroll lateral a 360px (inspección HTML).
- [ ] 5.6 Commits convencionales + `git push`.
- [ ] 5.7 Guardar `apply-progress` en engram `sdd/centro-de-control/apply-progress`.
