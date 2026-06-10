# Design: Dashboard MVP (frontend React + Vite)

## Technical Approach

`frontend/` monorepo app: Vite + React 18 + TS + Tailwind, TanStack Query para
server-state (polling 60s), react-router para 5 vistas. Cliente fetch fino
(sin axios) contra `/api/v1` (proxy Vite en dev). El front SOLO renderiza números
del servidor — NUNCA recalcula prob/edge/stake ni re-ordena standings (server =
autoridad). Lógica pura (formatters) es el core TDD con vitest. Dockerizado: servicio
dev en compose + `frontend/Dockerfile` multi-stage (dev cableado, prod definido para
el change de deploy).

## Hallazgo crítico de tipos (verificado por curl a la API viva)

Pydantic serializa **`Decimal` → STRING**, `float` → number. Por endpoint:
`recommended_stake` = `"120.16"` (**string**); `p_model/best_odds/edge/ev/kelly_fraction`
= float. `match_date`="2026-06-11" (string), `kickoff_at`=null. `model.calibration`=`null`
top-level — la tabla real vive en **`backtest.calibration_table`**. Standings en
**minúscula** (`pj,g,e,p,gf,gc,dg,pts`). `/signals` envuelve `{items,total}`;
`/matches/upcoming` y `/groups` son arrays pelados. `stage="group"`, `outcome_code="HOME"`,
`market_type="MATCH_1X2"` (lowercase/upper según campo). → `formatMoney` debe
`parseFloat` el string; los tipos TS reflejan `string` en stake.

## Architecture Decisions

| Decisión | Elección | Rechazado | Razón |
|---|---|---|---|
| HTTP client | fetch wrapper propio | axios | 7 endpoints GET; axios = peso muerto. Normaliza network vs HTTP-error |
| Base URL | `import.meta.env.VITE_API_URL ?? '/api'` | hardcode | proxy en dev, override en prod/deploy |
| Tipos | hand-written en `types.ts` | codegen/openapi-ts | contrato estable, MVP; control de string-Decimal |
| Server-state | TanStack Query (`staleTime`/`refetchInterval` 60s) | useEffect | polling+cache+loading/error gratis |
| Filtro señales | `min_edge`/`from`/`to` como query param al server | filtro cliente | menos datos, el param ya existe (R2) |
| Calibración | tabla `backtest.calibration_table` | charts | invariante honestidad visible; charts fuera de scope |
| Mock en tests | hand-mock `fetch` + QueryClient wrapper | MSW | MSW = overhead pa' MVP |
| Scaffolding | archivos a mano (package.json + configs) | `npm create vite` | control fino + TDD-friendly, sin basura del template |
| Stake/money | `parseFloat` del string en `formatMoney` | tratar como number | API lo manda string (Decimal) |

## Estructura `frontend/`

    frontend/
    ├── package.json  vite.config.ts  tsconfig.json  tailwind.config.js
    │   postcss.config.js  vitest.config.ts  index.html  Dockerfile  nginx.conf
    └── src/
        ├── main.tsx  App.tsx (router + QueryClientProvider + ErrorBoundary)
        ├── api/        client.ts (fetch wrapper) · types.ts (interfaces)
        ├── lib/        formatters.ts (PURO — core TDD)
        ├── components/ Layout/Nav · ErrorBanner · Loading · ErrorBoundary
        │               SignalsTable · GroupCard · MatchProbBar · CalibrationTable · PaperStats
        └── pages/      SignalsPage · GroupsPage · GroupDetailPage · MatchesPage · ModelPage · PaperPage

Container-presentational donde paga: `*Page` hace `useQuery`; los componentes de
tabla/card son presentacionales puros (testables sin red). ~13 componentes.

## Data Flow

    Page (useQuery key) → api/client.ts → /api proxy → api:8000 → Postgres
         │                                                          │
         └── render: ErrorBanner | Loading | Presentational ←───────┘
    Polling 60s revalida; render usa SOLO números del server (sin recompute)

## Interfaces / Contracts (`src/api/types.ts`)

```ts
type ISODate = string; type ISODateTime = string;
interface SignalItem { id:number; match_date:ISODate; kickoff_at:ISODateTime|null;
  home_team:string; away_team:string; market_type:string; outcome_code:string;
  p_model:number; best_odds:number; bookmaker:string; edge:number; ev:number;
  kelly_fraction:number; recommended_stake:string; captured_at:ISODateTime; }
interface SignalsResponse { items:SignalItem[]; total:number; }
interface UpcomingMatch { id:number; match_date:ISODate; kickoff_at:ISODateTime|null;
  home_team:string; away_team:string; neutral_site:boolean; stage:string;
  p_home:number|null; p_draw:number|null; p_away:number|null; low_confidence:boolean; }
interface StandingRow { team_name:string; pj:number; g:number; e:number; p:number;
  gf:number; gc:number; dg:number; pts:number; }
interface GroupItem { name:string; teams:string[]; standings:StandingRow[]; }
interface CalibrationBin { bin_low:number; bin_high:number; mean_predicted:number;
  observed_freq:number; count:number; }
interface Backtest { brier:number; logloss:number; beats_baselines:boolean;
  baselines:Record<string,number>; eval_n:number; eval_window:string;
  calibration_table:CalibrationBin[]; }
interface ModelInfo { name:string; params_summary:Record<string,number>;
  backtest:Backtest; calibration:unknown|null; }
interface PaperStats { total:number; open:number; settled:number; roi:number|null; }
// GroupDetail = GroupItem + fixtures:UpcomingMatch[] (endpoint /groups/{name})
```

Formatters puros: `formatPct(0.0832,1)→"8.3%"`; `formatMoney("120.16")→"$120.16"`;
`formatOdds(1.47)→"1.47"`; `formatRoi(null)→"—"`, `formatRoi(0.125)→"+12.5%"`.

## File Changes

| File | Action | Description |
|---|---|---|
| `frontend/**` | Create | App completa (estructura arriba) |
| `frontend/Dockerfile` | Create | multi-stage: dev (node:22-alpine) + prod (build→nginx) |
| `frontend/nginx.conf` | Create | sirve `dist/` + `location /api` proxy a `api:8000` (prod) |
| `docker-compose.yml` | Modify | + servicio `frontend` (dev) |

## Docker dev (compose)

Servicio `frontend`: `image node:22-alpine`, `working_dir /app`, monta **solo
`./frontend:/app`** (no `.` — evita ruido pyc), volumen **anónimo `/app/node_modules`**
(mismo patrón que `/opt/uv-venv`: el mount no tapa deps), `command sh -c "npm install &&
npm run dev -- --host"`, `ports 127.0.0.1:5173:5173`, `depends_on api`, env `VITE_API_URL`
ausente → cae a `/api`. `vite.config.ts`: `server.host=true`, `strictPort=true`,
`proxy['/api'] → http://api:8000` (DNS de compose).

`frontend/Dockerfile`: **stage build** `node:22-alpine` (`npm ci && npm run build`) →
**stage prod** `nginx:alpine` copia `dist/` + `nginx.conf` (proxy `/api`→`api:8000`).
El cableado del compose prod aterriza en el change de deploy.

## Testing Strategy

| Layer | Qué | Cómo |
|---|---|---|
| Unit | `formatters.ts` (pct, money con string-Decimal, odds, roi null/+%) | vitest, escenarios numéricos del spec |
| Component | SignalsTable (orden por edge desc + empty), GroupCard (orden tal-cual del server), PaperStats (roi null→"—"), MatchProbBar (low_confidence badge, p_* null) | Testing Library + jsdom, hand-mock |
| Integration | Page+useQuery con QueryClient wrapper + fetch mock | render loading→data |

`vitest.config.ts`: `environment jsdom`, `setupFiles` con `@testing-library/jest-dom`.

## Migration / Rollout

No migration. Aditivo: borrar `frontend/` + servicio compose para rollback. Deps `^`
(react, react-dom, react-router-dom, @tanstack/react-query, tailwind, vitest,
@testing-library/*). npm SIEMPRE dentro del contenedor.

## Open Questions

- Ninguna que bloquee. (Nota: `model.calibration` top-level es null — se usa
  `backtest.calibration_table`; ya resuelto en tipos.)
