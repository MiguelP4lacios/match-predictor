# Tasks: Dashboard MVP

## Phase 1: Scaffolding

- [x] 1.1 Crear `frontend/package.json` con deps exactas (react, react-dom, react-router-dom, @tanstack/react-query, tailwindcss, vite, typescript, vitest, @testing-library/react, @testing-library/jest-dom, jsdom) y scripts `dev/build/test`.
- [x] 1.2 Crear `frontend/vite.config.ts`: `server.host=true`, `strictPort=true`, proxy `/api`→`http://api:8000`, test config (`environment:jsdom`, `setupFiles:@testing-library/jest-dom`).
- [x] 1.3 Crear `frontend/tsconfig.json`, `frontend/tailwind.config.js`, `frontend/postcss.config.js`, `frontend/index.html`.
- [x] 1.4 Crear `frontend/src/main.tsx` mínimo (`ReactDOM.createRoot`).
- [x] 1.5 Agregar servicio `frontend` en `docker-compose.yml`: `node:22-alpine`, bind-mount `./frontend:/app`, volumen nombrado `frontend_node_modules:/app/node_modules`, command `sh -c "npm install && npm run dev -- --host"`, `ports 127.0.0.1:5173:5173`, `depends_on api`.
- [x] 1.6 `docker compose up -d frontend` → verificar `curl http://localhost:5173` retorna HTML.

## Phase 2: TDD Core — Formatters y API Client

- [x] 2.1 RED: `frontend/src/lib/formatters.test.ts` — 6 escenarios VERBATIM: `formatEdge(0.0832)→"8.3%"`, `formatProbability(0.4202)→"42.0%"`, `formatStake("112.7345")→"112.73"`, `formatOdds(3.9)→"3.90"`, `formatROI(null)→"—"`, `formatROI(0.125)→"+12.5%"`. Tests deben FALLAR.
- [x] 2.2 GREEN: `frontend/src/lib/formatters.ts` — implementar los 6 formatters (`formatStake` hace `parseFloat` del string; `formatROI(null)→"—"`, signo explícito).
- [x] 2.3 Crear `frontend/src/api/types.ts` — interfaces hand-written: `SignalItem` (`recommended_stake:string`), `SignalsResponse`, `UpcomingMatch`, `StandingRow`, `GroupItem`, `CalibrationBin`, `Backtest`, `ModelInfo`, `PaperStats`.
- [x] 2.4 RED: `frontend/src/api/client.test.ts` — 3 casos: respuesta ok (data), HTTP 500 (lanza error), network error (lanza error).
- [x] 2.5 GREEN: `frontend/src/api/client.ts` — `fetchAPI<T>(path, opts?)` con `if(!res.ok) throw` + try/catch para network errors.
- [x] 2.6 `docker compose run --rm frontend npm test` — todos los tests de Phase 2 en verde.

## Phase 3: TDD Componentes

- [x] 3.1 Crear `frontend/src/components/ErrorBanner.tsx` (banner "API no disponible" + botón "Reintentar") y `Loading.tsx` (skeleton).
- [x] 3.2 RED: `SignalsTable.test.tsx` — (a) filas en orden edge DESC tal-cual-server; (b) empty state "Sin señales con ese filtro".
- [x] 3.3 GREEN: `frontend/src/components/SignalsTable.tsx` — tabla presentacional, sin reordenar, formateadores, empty state.
- [x] 3.4 RED+GREEN: `GroupCard.test.tsx` (standings as-given + todos ceros sin crash) + `frontend/src/components/GroupCard.tsx` (columnas Pos/Equipo/PJ/G/E/P/GF/GC/DG/Pts).
- [x] 3.5 RED+GREEN: `MatchProbBar.test.tsx` (low_confidence badge + p=null sin barras) + `frontend/src/components/MatchProbBar.tsx` (barras P(H/D/A), badge "⚠ datos limitados", null guard).
- [x] 3.6 RED+GREEN: `PaperStats.test.tsx` (`roi null→"—"`, NO "0%") + `frontend/src/components/PaperStats.tsx`.
- [x] 3.7 `docker compose run --rm frontend npm test` — todos los tests de Phase 3 en verde.

## Phase 4: Páginas + Router

- [x] 4.1 Crear `frontend/src/App.tsx`: `QueryClientProvider`, `BrowserRouter`, `<nav>` con links a 5 rutas, `<Routes>` incluyendo `*`→404 "Página no encontrada".
- [x] 4.2 Crear `frontend/src/pages/SignalsPage.tsx`: `useQuery` `GET /api/v1/signals` (`staleTime:55000`, `refetchInterval:60000`), filtro `min_edge`, usa `SignalsTable/Loading/ErrorBanner`.
- [x] 4.3 Crear `frontend/src/pages/GroupsPage.tsx` y `GroupDetailPage.tsx`: queries `/api/v1/groups` y `/api/v1/groups/:letter`; usa `GroupCard`.
- [x] 4.4 Crear `frontend/src/pages/MatchesPage.tsx`: query `/api/v1/matches/upcoming`, partidos agrupados por `match_date`, usa `MatchProbBar`.
- [x] 4.5 Crear `frontend/src/pages/ModelPage.tsx` (baselines + calibration_table + semáforo `beats_baselines`) y `PaperPage.tsx` (usa `PaperStats`).
- [x] 4.6 Integration tests (1 por página): `QueryClient` wrapper + fetch mock con shapes reales → loading→data + error→`ErrorBanner`.

## Phase 5: Artefactos Prod

- [x] 5.1 Crear `frontend/Dockerfile` multi-stage: stage `build` (`node:22-alpine`, `npm ci && npm run build`) → stage `prod` (`nginx:alpine`, copia `dist/` + `nginx.conf`).
- [x] 5.2 Crear `frontend/nginx.conf` (`location /api` proxy a `api:8000`); smoke: `docker build --target prod -t frontend-prod frontend/` debe compilar sin error.

## Phase 6: Verificación Final

- [x] 6.1 `docker compose run --rm frontend npm test` — todos los tests en verde (unit + component + integration).
- [x] 6.2 `docker compose run --rm frontend npm run build` — sin errores TypeScript.
- [x] 6.3 Smoke real: `docker compose up -d frontend` → `curl http://localhost:5173` retorna HTML con `<div id="root">`; documentar URLs de navegación manual.
- [x] 6.4 Commits conventional + marcar tasks completadas + merge apply-progress en engram.
