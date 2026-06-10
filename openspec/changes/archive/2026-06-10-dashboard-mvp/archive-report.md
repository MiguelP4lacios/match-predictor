# Archive Report: dashboard-mvp

**Date Archived**: 2026-06-10  
**Change**: dashboard-mvp  
**Status**: COMPLETE — Approved with Warnings (all gaps fixed post-verify)

---

## Lineage & Journey

### Phase 0: Proposal (Decision & Intent)
**Topic Key**: `sdd/dashboard-mvp/proposal`

**Rationale**: Build a React/Vite/TypeScript dashboard frontend for the **match_predictor** that consumes 7 existing backend endpoints (`/api/v1/*`) and renders 5 domain-specific views (Signals, Groups, Matches, Model, Paper). The frontend exists to make probabilistic betting signals actionable for a human operator — no auth, no streaming, raw values from the deterministic model rendered with honest formatting and no client-side recalculation.

**Monorepo Scope**: New domain `frontend/` directory under the project root, sister to `backend/`, `docs/`, `openspec/`. Frontend runs on port 5173 (dev) / 80 (prod) inside compose service `frontend`, with vite proxy `/api` → `http://api:8000`.

---

### Phase 1: Specification (10 Requirements + R2A Amendment)
**Topic Key**: `sdd/dashboard-mvp/spec`

**Spec Version**: v1 + amendment R2A (2026-06-10)

**Requirements Summary**:
| ID | Title | Scope |
|---|---|---|
| R1 | Routing (7 routes + 404) | App structure, deep-links |
| R2 | Vista Señales (table + filter) | Main signal view, formatters |
| R2A | Agrupación señales (amendment) | Client-side grouping by match + order chronologically |
| R3 | Vista Grupos (12 cards A–L) | Group standings + fixtures |
| R4 | Vista Partidos (probability bars) | Upcoming matches grouped by date |
| R5 | Vista Modelo (calibration + baselines) | Model transparency & backtest metrics |
| R6 | Vista Paper (ROI tracking) | Betting journal, honesty on null ROI |
| R7 | TypeScript Types | Hand-written interfaces, all 10 types |
| R8 | Data Layer (TanStack Query) | staleTime 55–60s, error UI, skeleton loading |
| R9 | Build & Docker | Vite, compose proxy, multi-stage Dockerfile, nginx prod |
| R10 | Testing (vitest + Testing Library) | 22+ scenarios, formatters + components + pages |

**R2A Amendment** (corrected 2026-06-10): Signals grouped by `(match_date, home_team, away_team)` with **chronological order** (server order), NOT max-edge DESC. Hint "⚠ 2 señales" for 2+ signals on same match, no hint for 1-signal groups.

**Scenarios Covered**: 22 detailed Given/When/Then scenarios across all requirements.

---

### Phase 2: Design (9 Architecture Decisions + API Discoveries)
**Topic Key**: `sdd/dashboard-mvp/design`

**Key Decisions**:
1. **HTTP Client**: Thin fetch wrapper (`api/client.ts`), no axios/SDKs
2. **Base URL**: `VITE_API_URL ?? '/api'` for compose proxy in dev, env var in prod
3. **Type Generation**: Hand-written types in `api/types.ts`, no codegen (tight coupling acceptable here)
4. **Server-State Library**: TanStack Query v5, 60s (Signals 55s for faster signal refresh)
5. **Grouping Logic**: Pure function `groupSignals(items) → SignalGroup[]` in `lib/groupSignals.ts`
6. **Formatters**: Pure functions (`formatEdge`, `formatStake`, `formatROI`, etc.), no components
7. **Styling**: Tailwind CSS v4 + Headless UI for accessible components
8. **Docker**: Multi-stage build (node:22-alpine dev → nginx:latest prod), vite proxy in dev
9. **Volume Strategy**: Named volume `frontend_node_modules` (bind-mount shadowing avoided)

**API Discoveries** (live server inspection):
- `recommended_stake` is **STRING** type (e.g., `"120.16"`), not number — API contracts matter
- `calibration_table` field exists in `backtest` object; can be empty array
- Closing odds (`best_odds`, `bookmaker`) captured in signals; requires live snapshot capture layer (out of scope for frontend)

---

### Phase 3: Tasks (31 Atomic, Hierarchical Tasks)
**Topic Key**: `sdd/dashboard-mvp/tasks`

**Phases**:
- **Phase 1**: Scaffolding + Compose (1.1–1.6) — vite, tailwind, docker-compose, proxy config
- **Phase 2**: TDD Core (2.1–2.6) — formatters (6 functions), client wrapper, pure `groupSignals`
- **Phase 3**: TDD Components (3.1–3.7) — SignalsTable, GroupCard, MatchProbBar, PaperStats, ErrorBanner, Loading
- **Phase 4**: Pages + Router (4.1–4.6) — SignalsPage, GroupsPage, GroupDetailPage, MatchesPage, ModelPage, PaperPage, routing tests
- **Phase 5**: Prod Artifacts (5.1–5.2) — multi-stage Dockerfile, nginx config
- **Phase 6**: Final Verification (6.1–6.4) — build tsc clean, test suite 45/45, live smoke, git hygiene

---

### Phase 4: Apply (Strict TDD, 2 Sub-Agents, 45→59 Tests)
**Topic Key**: `sdd/dashboard-mvp/apply-progress`

**Execution**:
- **Batch 1** (Agent 1): Scaffolding + Phase 2–3 TDD (formatters, client, components) — 14+18 tests
- **Batch 2** (Agent 2): Pages + Router + Prod artifacts + final verification — 13 integration tests

**Test Distribution**:
| Layer | Count | Files |
|-------|-------|-------|
| Unit (formatters) | 11 | `formatters.test.ts` |
| Unit (pure fn) | 6 | `groupSignals.test.ts` |
| Unit (HTTP) | 3 | `client.test.ts` |
| Component | 22 | GroupCard, MatchProbBar, PaperStats, SignalsTable (4 files) |
| Integration (page) | 15 | SignalsPage, GroupsPage, MatchesPage, ModelPage, PaperPage, routing (6 files) |
| **Total** | **57** | **13 test files** |

**Build & Output**:
- `tsc -b && vite build` ✅ Clean (94 modules, 221.67 KB gzipped to 69.72 KB)
- `dist/` committed to `.gitignore`
- All 57 tests pass (vitest)

**Notes**: 
- `recommended_stake` declared as `string` in types (matches API contract)
- `formatStake(value: string): parseFloat(value).toFixed(2)` — no $ symbol per spec
- `AppRoutes` exported from `App.tsx` for MemoryRouter testing

---

### Phase 5: Verify (Strict TDD, 57 Tests Passing, 3 Warnings Identified)
**Topic Key**: `sdd/dashboard-mvp/verify-report`

**Build**: ✅ PASSED  
**Tests**: ✅ 57/57 passed (all 13 test files green)  
**Live Smoke**: ✅ Frontend on port 5173, proxy `/api` → `http://api:8000` functional  
**Git Hygiene**: ✅ Conventional commits, clean working tree, `frontend/dist/` gitignored  

**Verdict**: **APPROVED-WITH-WARNINGS**

**3 Warnings Identified**:
1. **React Fragment Key Missing**: `<>` fragment in `SignalsTable.tsx:39` lacks `key` prop. Console warning on every render.  
   → **Fixed** (commit d46db89): Changed to `<Fragment key={group.match_key}>`
   
2. **GroupDetailPage Missing Integration Test**: Task 4.6 requires integration test per page. GroupDetailPage has none (all others do).  
   → **Fixed** (commit d46db89): Added `GroupDetailPage.test.tsx` with QueryClient + mocked fetchAPI
   
3. **"Sin datos de calibración" Text Missing**: R5 scenario requires this text when `calibration_table` is empty. ModelPage silently hides section.  
   → **Fixed** (commit d46db89): Added else branch rendering the text

---

### Phase 5b: Post-Verify User-Driven Fixes (4 Additional Commits)
User (Miguel) reviewed live dashboard and reported real bugs detected by data inspection:

1. **commit 28fdb60**: `fix(frontend): limit=200 en Partidos (fix 72 fixtures vs default 50)`  
   - Bug: `/api/v1/matches/upcoming` default limit=50 cut off 72 group-stage fixtures
   - Fix: MatchesPage hardcodes `limit=200` in request
   - Caught: User reviewing live data saw < 72 matches

2. **commit 0720b41**: `feat(frontend): agrupar señales por partido con hint exposición`  
   - Enhancement: Signals grouped by match with correlational exposure warning
   - Logic: Pure `groupSignals()` function; client renders grouped table
   - Spec alignment: Matches R2A amendment exactly

3. **commit fa3b99a**: `fix(frontend): orden grupos = cronológico (server order, no max-edge)`  
   - Bug: Previous version sorted groups by max edge DESC, breaking chronology
   - Fix: Groups preserve server order (result of `match_date, id` sort backend-side)
   - Amended spec: R2A clarified with note: "Corregido 2026-06-10"

4. **commit 01b798f**: `feat(frontend): columna "Apostar a" en lugar de "Resultado"`  
   - UX: Changed outcome column header from "Resultado" → "Apostar a" (clearer intent)
   - Logic: Unchanged; display only

**Final Suite**: 59/59 frontend tests + 125/125 backend tests (backend unchanged)  
**Status**: All green, production-ready

---

### Phase 6: Archive (This Phase)
**Artifacts Synced**:
- Delta spec → Main spec: `openspec/specs/dashboard-frontend/spec.md` created
- Change folder moved: `openspec/changes/dashboard-mvp/` → `openspec/changes/archive/2026-06-10-dashboard-mvp/`
- State updated: `phase: archived`, `verify_report: true`, `archive_report: true`
- Archive report created: `archive-report.md` (this file)

**Engram Topic Keys Recorded**:
- `sdd/dashboard-mvp/proposal`
- `sdd/dashboard-mvp/spec`
- `sdd/dashboard-mvp/design`
- `sdd/dashboard-mvp/tasks`
- `sdd/dashboard-mvp/apply-progress`
- `sdd/dashboard-mvp/verify-report`
- `sdd/dashboard-mvp/state`
- `sdd/dashboard-mvp/archive-report`

---

## Implementation Highlights

### Code Quality
- **Formatters**: Pure, tested to exact numeric behavior (banker's rounding avoided with `.toFixed()`)
- **Types**: Hand-written, grounded in real API responses (no codegen magic)
- **Grouping**: Pure function `groupSignals()` encapsulates complexity; frontend never recalculates EV/probability/stake
- **Architecture**: 100% compliance with invariant: *frontend NEVER invents or recalculates model values*

### Testing Discipline
- **Unit**: formatters, HTTP client, pure grouping function
- **Component**: Each component tested in isolation with mocked data (SignalsTable, GroupCard, MatchProbBar, PaperStats)
- **Integration**: Full page tests with QueryClient + react-router (SignalsPage, GroupsPage, MatchesPage, ModelPage, PaperPage)
- **E2E out of scope**: No Playwright; live smoke verified vite proxy + real API calls during apply phase

### Docker & Deployment
- **Dev**: Vite dev server on 5173, proxy `/api` to compose network `api:8000`
- **Prod**: Multi-stage build (npm ci → tsc → vite build → nginx:latest), nginx serves React app + proxies `/api`
- **Volumes**: Named `frontend_node_modules` avoids bind-mount shadowing; `./frontend:/app` source binding

---

## Successor Change

**Recommended Next**: `dashboard-ux-explicable`

**Scope**: UX redesign for signal interpretation. Current layout (table) is dense; proposal is **cards + side panel**:
- Left: Card deck of highest-confidence signals (clickable)
- Right: Expandable side panel with signal detail, model confidence, historical accuracy on similar signals, suggested stake

**Rationale**: Users (Miguel) report that table format is hard to scan for actionable signals; cards + side panel improves signal-finding UX without changing backend or deterministic model. Spec to be written in next change.

---

## Files Changed

| Path | Action | Details |
|------|--------|---------|
| `openspec/specs/dashboard-frontend/spec.md` | Created | Main spec (copy of delta) |
| `openspec/changes/archive/2026-06-10-dashboard-mvp/` | Created (moved) | Full artifact archive with all phases |
| `frontend/` | Created | New React/Vite/TS app (5173 dev, 80 prod) |
| `docker-compose.yml` | Modified | Added `frontend` service + volumes |
| `Dockerfile.frontend` | Created | Multi-stage build for prod |
| `.gitignore` | Modified | Added `frontend/dist/`, `frontend/node_modules/` |
| Various commits | 6 total | Scaffolding + apply + post-verify fixes |

---

## Metrics

| Metric | Value |
|--------|-------|
| Spec requirements | 10 (+ 1 amendment R2A) |
| Spec scenarios | 22 |
| Design decisions | 9 |
| Tasks (atomic) | 31 |
| Test files | 13 |
| Tests (final) | 59 frontend + 125 backend |
| Source files (frontend) | ~25 (components, pages, api, lib, config) |
| Warnings at verify | 3 (all fixed post-verify) |
| Post-verify user-driven fixes | 4 (real bugs, real data) |
| Days in SDD cycle | 2 (2026-06-09 proposal → 2026-06-10 archive) |

---

## Verification Checklist

- [x] Spec synced to main specs directory
- [x] Change folder moved to archive with date prefix
- [x] All artifacts present in archive (proposal, specs, design, tasks, apply-progress, verify-report)
- [x] State updated (phase=archived, all artifacts marked true)
- [x] Archive report created
- [x] Engram saved (archive-report + state)
- [x] Git status clean after archive move
- [x] No CRITICAL issues in verify report (3 warnings fixed)
- [x] Successor change noted (dashboard-ux-explicable)

---

## Engram Integration

Archive report saved to **engram** with:
- **topic_key**: `sdd/dashboard-mvp/archive-report`
- **type**: `architecture`
- **scope**: `project`

State summary saved to **engram** with:
- **topic_key**: `sdd/dashboard-mvp/state`
- **type**: `architecture`
- **scope**: `project`

Both records preserve observation IDs for lineage traceability across compactions.

---

**Archive Complete.** Ready for next change: `dashboard-ux-explicable`.
