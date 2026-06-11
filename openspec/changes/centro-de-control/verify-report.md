# Verification Report

**Change**: centro-de-control
**Version**: N/A (no semver on specs)
**Mode**: Strict TDD (strict_tdd: true — test runner: docker compose run --rm api pytest)
**Date**: 2026-06-11

---

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 36 |
| Tasks complete [x] | 29 (Phases 1–4 + 5.7) |
| Tasks incomplete [ ] | 7 (Phase 5: 5.1–5.6) |

**Phase 5 tasks not checked off** (although tests do pass — they were run here in the verify phase):

- [ ] 5.1 Correr suite completa en Docker
- [ ] 5.2 ruff check . && ruff format .
- [ ] 5.3 npm run build en Docker
- [ ] 5.4 Deploy VPS
- [ ] 5.5 Smokes reales
- [ ] 5.6 Commits convencionales + git push

Note: 5.1–5.3 were executed during this verify run and all passed. 5.4–5.6 appear done (git is clean, up to date with origin/main, 12 commits matching change), but were never checked off in tasks.md.

---

## Build & Tests Execution

**Build** (npm run build, Docker): ✅ Passed  
`vite v6.4.3 — 117 modules transformed, dist/ emitted, 0 TypeScript errors`

**Backend Tests** (docker compose run --rm api pytest): ✅ 207 passed / 0 failed / 0 skipped  
**Frontend Tests** (docker compose run --rm frontend npx vitest run): ✅ 232 passed / 0 failed / 0 skipped (30 test files)

**Ruff** (ruff check .): ✅ All checks passed

**Coverage**: Not available (no coverage tool configured)

---

## Issues Found

### CRITICAL

**C1 — BE/FE contract mismatch: `/api/v1/health/full` response shape**

The backend `HealthFull` Pydantic model serializes to:
```json
{
  "overall": "ok|warn|stale",
  "odds_capture": { "last_at": "...", "age_hours": 2.0, "verdict": "ok" },
  "odds_credits": { "remaining": 488, "verdict": "ok" },
  "model": { "name": "...", "verdict": "ok" },
  "results": { "latest_date": "...", "verdict": "ok" }
}
```

The frontend TypeScript type `HealthFull` (in `frontend/src/api/health.ts`) expects:
```ts
interface HealthFull {
  overall: Verdict
  last_odds_capture: HealthMetric   // flat structure with { value, verdict, threshold }
  odds_age: HealthMetric
  credits_remaining: HealthMetric
  model_version: HealthMetric
  last_finished: HealthMetric
}
```

`fetchAPI<HealthFull>` is a raw cast — no runtime adapter. At runtime, `data.last_odds_capture`, `data.odds_age`, `data.credits_remaining`, `data.model_version`, and `data.last_finished` are ALL `undefined` because those keys don't exist in the backend response.

**Runtime consequence**: `EstadoPage` renders `<MetricRow metric={data.last_odds_capture} />` where `metric` is `undefined`. Inside `MetricRow`, `metric.value` → `TypeError: Cannot read properties of undefined`. The `/estado` page **crashes at runtime in production**.

`StatusBadge` is unaffected (only reads `data.overall`, which IS present in the BE response).

This violates spec HO4 (Página Estado must render metrics). Tests all pass because they mock `getHealthFull` with the flat shape — the contract break is invisible to Vitest.

**Files involved**:
- `app/model/health_status.py` (BE model — correct per spec HO1)
- `frontend/src/api/health.ts` (FE type — inconsistent with BE)
- `frontend/src/pages/EstadoPage.tsx` (consumer — crashes with real data)

---

### WARNING

**W1 — flags.ts exports `nameToFlag`, spec requires `getFlag`**

Spec DS4 defines the function signature as `getFlag(teamName: string): string`. The implementation exports `nameToFlag(name: string)`. All internal usages consistently use `nameToFlag` (FlagLabel, tests). This is a naming spec deviation, not a functional bug. Rename required for spec compliance.

**W2 — CSS tokens diverge from spec DS1**

Spec DS1 requires: `--bg, --surface, --text, --text-muted, --border, --accent, --positive, --negative`  
Implementation (index.css): `--bg, --bg-elevated, --fg, --fg-muted, --border, --primary, --primary-fg, --success, --warn, --danger, --qualify`

The design.md defines the second set and all components use them consistently. Tailwind config maps `surface → var(--bg-elevated)`, `text → var(--fg)`, etc. No functional dark-mode breakage, but the spec DS1 names are not honored.

**W3 — Ivory Coast (implementation) vs Côte d'Ivoire (spec DS4)**

Spec DS4 requires mapping for `"Côte d'Ivoire"` → 🇨🇮. The implementation maps `"Ivory Coast"` → CI. Tasks spec (2.7) explicitly says `Ivory Coast`, suggesting the canonical DB name is English. If the `group_team.name` column stores the French variant, `FlagLabel` would show 🏳 for those entries. Risk: medium (data-dependent).

**W4 — Phase 5 tasks not checked off in tasks.md**

Tasks 5.1–5.6 remain `[ ]` despite the work having been done (commits are pushed, tests pass, build passes). tasks.md is stale. Pre-archive cleanup needed.

**W5 — Live smoke test not executable from local machine**

`wc26.palaciosdev.com` returns NXDOMAIN from the verification environment. Cannot confirm:
- `GET /api/v1/health/full` (real auth, real data)
- Dashboard 200
- `/estado` route serving (would reveal C1 crash live)
- No horizontal scroll at 360px (manual inspection)

Deployment is verified only by git state (up to date with origin/main, 12 commits on branch).

---

### SUGGESTION

**S1 — Primitives in `src/ui/` instead of spec's `src/components/ui/`**

Spec DS3 says primitives must be importable from `@/components/ui/{nombre}`. Implementation is under `src/ui/`. The design.md documents `src/ui/` so this was an intentional pivot, but the spec was not updated to reflect it.

**S2 — CuponContext.test.tsx: React key warning**

Vitest stderr shows `Warning: Each child in a list should have a unique "key" prop` in `CuponContext.test.tsx`. This doesn't cause a test failure, but indicates a test harness hygiene issue.

---

## Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| HO1 — /health/full | Captura reciente → ok | `test_health_full_router.py > test_health_full_with_recent_capture` | ✅ COMPLIANT |
| HO1 — /health/full | Empty state → stale | `test_health_full_router.py > test_health_full_empty_state_200` | ✅ COMPLIANT |
| HO1 — /health/full | Captura antigua → stale | `test_health_status.py > test_old_capture_stale` | ✅ COMPLIANT |
| HO1 — /health/full | Créditos bajos → warn | `test_health_status.py > test_low_credits_warn` | ✅ COMPLIANT |
| HO1 — /health/full | Sin captura → stale | `test_health_status.py > test_no_capture_row_stale` | ✅ COMPLIANT |
| HO1 — /health/full | No external call | structural (router uses `get_session` only) | ✅ COMPLIANT |
| HO2 — SyncLog audit cols | Migración no rompe filas | `test_sync_log_capture.py > test_capture_writes_sync_log_row` | ✅ COMPLIANT |
| HO3 — StatusBadge poll | allOk → 🟢 | `StatusBadge.test.tsx > muestra 🟢 cuando overall=ok` | ✅ COMPLIANT |
| HO3 — StatusBadge poll | withWarn → 🟡 | `StatusBadge.test.tsx > muestra 🟡 cuando overall=warn` | ✅ COMPLIANT |
| HO3 — StatusBadge poll | withStale → 🔴 | `StatusBadge.test.tsx > muestra 🔴 cuando overall=stale` | ✅ COMPLIANT |
| HO3 — StatusBadge poll | error-fetch → 🔴 | `StatusBadge.test.tsx > muestra 🔴 cuando getHealthFull lanza error` | ✅ COMPLIANT |
| HO4 — /estado page | Render métricas | `EstadoPage.test.tsx > muestra el label de créditos restantes` | ⚠️ PARTIAL — test passes (mocked) but page crashes at runtime (C1) |
| HO4 — /estado page | Stale → rojo | `EstadoPage.test.tsx > muestra badge stale cuando credits son stale` | ⚠️ PARTIAL — test passes (mocked) but page crashes at runtime (C1) |
| DS1 — Design Tokens | Tokens in light+dark | `ThemeContext.test.tsx > system→dark sin preferencia` | ✅ COMPLIANT (tokens work; names differ from spec — W2) |
| DS2 — Theme Resolution | Persistencia entre recargas | `ThemeContext.test.tsx > recarga persiste` | ✅ COMPLIANT |
| DS2 — Theme Resolution | AUTO system dark | `ThemeContext.test.tsx > sistema dark sin localStorage` | ✅ COMPLIANT |
| DS2 — Theme Resolution | Toggle manual sobreescribe | `ThemeContext.test.tsx > toggle manual persistido` | ✅ COMPLIANT |
| DS2 — No flash | Script inline BEFORE module | `index.html` — script in `<head>` before `<script type=module>` | ✅ COMPLIANT |
| DS3 — Primitivas UI | Card/Badge/Stat/Button/Tabs/Sheet/FlagLabel/ThemeToggle/AppShell/StatusBadge/Spinner/ErrorState | `src/ui/*.test.tsx` — all render tests pass | ✅ COMPLIANT |
| DS4 — getFlag function name | `getFlag(...)` exported | `flags.test.ts > nameToFlag tests` — `nameToFlag` exported, not `getFlag` | ⚠️ PARTIAL — functional but spec name not honored (W1) |
| DS4 — FlagLabel 48 teams | Mexico→🇲🇽, South Korea→🇰🇷, DR Congo→🇨🇩, Czech Republic→🇨🇿 | `flags.test.ts > países canónicos` | ✅ COMPLIANT |
| DS4 — Côte d'Ivoire→🇨🇮 | Spec canonical name | `flags.test.ts > Ivory Coast→🇨🇮` | ⚠️ PARTIAL — Ivory Coast maps fine, Côte d'Ivoire maps to 🏳 (W3) |
| DS4 — unknown → 🏳 | Fallback | `flags.test.ts > nombre desconocido → 🏳` | ✅ COMPLIANT |
| DS4 — England override | Tag sequence | `flags.test.ts > England → flag de England` | ✅ COMPLIANT |
| DS5 — AppShell responsive | Nav bottom mobile / top laptop | `AppShell.test.tsx > renderiza ambas navs en DOM` | ✅ COMPLIANT |
| R-DS — No hardcoded colors | bg-white/text-gray-900 absent | `rg "bg-white|text-gray-900|bg-gray-50" pages/ components/` → 0 hits | ✅ COMPLIANT |
| R-DS — Behavior preserved | edge/stake formatters intact | `formatters.test.ts` — all 17 unit tests pass | ✅ COMPLIANT |
| R-GROUPS-RESPONSIVE — No overflow-x scroll | `hidden md:table-cell` mechanism | `GroupCard.tsx` — no overflow-x-auto; hidden md:table-cell confirmed | ✅ COMPLIANT |
| R-GROUPS-RESPONSIVE — Expand tap | `expandedRow` state | `GroupCard.tsx` lines 61–76; Fragment key fix | ✅ COMPLIANT |
| R-GROUPS-RESPONSIVE — Qualify zone top-2 | `border-l-qualify` on idx<2 | `GroupCard.tsx` line 44 | ✅ COMPLIANT |
| R-GROUPS-RESPONSIVE — Server order | No client sort | `GroupCard.tsx` — no .sort() call | ✅ COMPLIANT |
| Odds Capture — Log exitosa | rows_inserted, credits_remaining | `test_sync_log_capture.py > test_capture_writes_sync_log_row` | ✅ COMPLIANT |
| Odds Capture — Upsert, no duplicate | ON CONFLICT UPDATE | `test_sync_log_capture.py > test_capture_upserts_not_duplicates` | ✅ COMPLIANT |
| Invariant — No LLM arithmetic | No math in restyled components | `rg "Math\.\|\.reduce\|edge \*\|stake \*"` → 0 hits | ✅ COMPLIANT |
| Invariant — signals chronological | No reorder in SignalsPage | No .sort() added | ✅ COMPLIANT |

**Compliance summary**: 33/36 scenarios compliant (3 partial — C1 and W1/W3)

---

## Correctness (Static — Structural Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| HO1 health endpoint shape (BE) | ✅ Implemented | `health_status.py` + `health_full.py` match spec exactly |
| HO1 health endpoint shape (FE) | ❌ Missing | `health.ts` HealthFull type diverges from BE shape → EstadoPage crashes (C1) |
| HO2 SyncLog nullable cols | ✅ Implemented | m8 migration + model updated |
| HO3 StatusBadge polling | ✅ Implemented | 60s interval, worst verdict, 🔴 on error |
| HO4 EstadoPage | ⚠️ Partial | Renders correctly with mocked data; crashes with real BE response (C1) |
| DS2 Anti-flash inline script | ✅ Implemented | In `<head>` before module script |
| DS3 12 primitives in src/ui/ | ✅ Implemented | All 12 exist and tested |
| DS4 nameToFlag (spec: getFlag) | ⚠️ Partial | Function works, name differs from spec |
| DS4 Côte d'Ivoire canonical | ⚠️ Partial | "Ivory Coast" works, French name maps to 🏳 |
| DS5 AppShell responsive nav | ✅ Implemented | Both navs from same route config |
| D1 Anti-flash (design) | ✅ Implemented | Script inline in <head> |
| D5 Group table reflow | ✅ Implemented | hidden md:table-cell, expandedRow state, no overflow-x |
| D7 Health thresholds | ✅ Implemented | ok≤4h, warn>4h-10h, stale>10h; credits ok≥100 |
| D8 Migration m8 | ✅ Implemented | m8capfields, down_revision=m7parlay, reversible |

---

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| D1 — Inline anti-flash script | ✅ Yes | Placed before module script in `<head>` |
| D2 — CSS vars → Tailwind semantic | ✅ Yes | tailwind.config uses var(--*) consistently |
| D3 — 12 primitives in src/ui/ | ✅ Yes | All 12 implemented; design lists src/ui/, spec says src/components/ui/ |
| D4 — One route-config for both navs | ✅ Yes | AppShell derives top+bottom from same array |
| D5 — hidden md:table-cell + expandedRow | ✅ Yes | No overflow-x-auto; Fragment key fix applied |
| D6 — nameToFlag (design says "Overrides: England/Scotland") | ✅ Yes | Tag sequences implemented |
| D7 — Health thresholds (design says ok<6h/warn<24h) | ⚠️ Deviated | Implementation uses spec thresholds (ok≤4h/warn≤10h/stale>10h, credits ok≥100). Tasks align with spec HO1, not design D7. Spec wins — this is correct behavior. |
| D7 — FE HealthFull flat shape | ❌ Not in design | Design defines nested BE shape only; FE invented a different flat schema (C1) |
| D8 — Migration aditiva, reversible | ✅ Yes | m8 adds nullable cols, downgrade drops them |

---

### Verdict
**FAIL**

**Critical issue C1 blocks archive**: The `/estado` page crashes at runtime with real backend data due to a shape contract mismatch between `app/model/health_status.py` (correct per spec HO1) and `frontend/src/api/health.ts` (defines a flat HealthMetric type not returned by the BE). All Vitest tests pass because `getHealthFull` is mocked. TypeScript build passes because `fetchAPI<T>` is a cast-only wrapper. The bug is invisible to the test suite and only manifests in production.

Fix required: Either (a) update the BE to return the flat `HealthMetric` shape the FE expects, or (b) update the FE `health.ts` type + `EstadoPage.tsx` to read the nested BE fields (`data.odds_capture.verdict`, `data.odds_credits.remaining`, etc.).

All other critical betting flows (signals, cupón, bet registration, ROI, explain drawer) are unaffected by the redesign.
