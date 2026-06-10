# Proposal: Dashboard MVP (frontend React + Vite)

## Intent
El Mundial empieza mañana (2026-06-11). La API ya sirve 7 endpoints read-only desde
Postgres, pero no hay UI. Necesito una herramienta que YO use mirando partidos HOY:
ver señales +EV, grupos, fixtures y la honestidad del modelo. Útil hoy > bonito la
semana que viene.

## Scope
### In Scope
- App `frontend/` en este repo (monorepo, package.json propio), Vite + React 18 + TypeScript.
- 5 páginas (router): **Señales** (tabla de value signals: partido, fecha, outcome, p_model, mejor cuota+bookmaker, edge%, stake sugerido; orden por edge; filtro min_edge/fecha), **Grupos** (12 cards con standings, detalle `/grupos/:letra`), **Partidos** (fixtures con barras P(H/D/A) + flag low_confidence), **Modelo** (backtest Brier/log-loss + tabla de calibración = invariante de honestidad visible), **Paper** (open/settled/ROI).
- Servicio `frontend` en docker-compose (node:22-alpine, bind-mount, vite dev :5173, hot-reload, `VITE_API_URL`). Todo dockerizado.
- Tests: vitest + Testing Library sobre lógica pura (formato edge%/stake/ROI, orden por edge, render de standings) con escenarios numéricos.

### Out of Scope
- Auth, SSE/streaming, agentes/LLM, charts (calibración = tabla), diseño mobile-perfect (responsive-razonable), i18n (UI en español hardcodeada).
- Página detalle de partido (`/matches/{id}`) → diferida.
- Compose de **producción** + nginx real → va en el change de deploy.

## Capabilities
### New Capabilities
- `dashboard-frontend`: app React que consume los 7 endpoints `/api/v1`, renderiza las 5 vistas, formatea números financieros y refresca por polling.
### Modified Capabilities
- None. (Specs de API y CORS no cambian; el dev proxy ya evita CORS en dev.)

## Approach
| Decisión | Elección | Razón |
|---|---|---|
| Tipos | Hand-written mínimos | 7 endpoints estables; codegen es overhead innecesario en MVP |
| Data fetching | TanStack Query | polling, cache, loading/error gratis vs boilerplate useEffect |
| Estilos | Tailwind | velocidad de iteración |
| State lib | Ninguna | Query cubre el server-state; no hay client-state global |
| Routing | react-router-dom | URLs compartibles, deep-link a grupo |
| Refresh | Polling 60s (Señales/Grupos/Partidos) + refetch manual | SSE explícitamente fuera |
| Dev → API | Vite proxy `/api`→`api:8000` | mismo origen, cero CORS en dev |
| Prod (estructura ya) | `Dockerfile` multi-stage (node build → nginx static + reverse proxy `/api`) | definir hoy para no rehacer; compose prod = deploy change |

**Este change entrega**: `frontend/` + servicio dev en compose + `frontend/Dockerfile` con ambos stages definidos (solo dev cableado). El stage prod existe pero se wirea en el change de deploy.

## Affected Areas
| Area | Impact | Description |
|---|---|---|
| `frontend/` | New | App Vite/React/TS, 5 páginas, api client, tests |
| `docker-compose.yml` | Modified | + servicio `frontend` (dev) |
| `frontend/Dockerfile` | New | multi-stage (dev + prod-nginx) |

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| Endpoint devuelve null/vacío en vivo | High | UI maneja `null` (p_*, roi) y colecciones vacías explícitamente |
| node_modules vs bind-mount choca | Med | volumen anónimo para `node_modules` (patrón venv-fuera-del-mount) |
| Polling agota nada externo | Low | pega solo a Postgres vía API; sin coste de cuotas |

## Rollback Plan
Aditivo: borrar `frontend/` y el servicio `frontend` de `docker-compose.yml`. El backend queda intacto.

## Dependencies
- API read-only (7 endpoints) ya operativa. CORS `http://localhost:5173` ya configurado.

## Success Criteria
- [ ] `docker compose up` levanta `frontend` en :5173 con hot-reload, consumiendo la API.
- [ ] Las 5 vistas renderizan datos reales; edge%, stake y ROI con formato correcto.
- [ ] `null`/colecciones vacías no rompen ninguna vista.
- [ ] vitest verde sobre formatters y orden por edge (escenarios numéricos).
