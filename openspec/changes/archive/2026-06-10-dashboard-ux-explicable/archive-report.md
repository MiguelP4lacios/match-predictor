# Archive Report: dashboard-ux-explicable

**Change**: dashboard-ux-explicable  
**Status**: ARCHIVED  
**Archived Date**: 2026-06-10  
**Artifact Store**: hybrid (openspec files + engram)

---

## Lineage: Proposal → Archive

### Phase 1: Proposal (User Intent)

**Proposal.md Summary**:
- User intent: Dashboard UX legible para hincha, no técnica, pero con traza completa de cálculos disponible bajo demanda
- Solution: Señales como tarjetas en lenguaje natural + panel lateral (drawer) con desglose paso a paso trazable
- Scope: Endpoint `/signals/{id}/explain` (read-only, serve-from-DB), SignalCard reemplazando tabla, Drawer reusable, Glosario inline
- Key constraint: **El LLM JAMÁS calcula ni inventa** — frontend SOLO formatea, números ya calculados por el modelo determinista

---

### Phase 2: Specifications

**Artifacts**:
- `signal-explanation/spec.md` (NEW domain) — R1 endpoint requirement
  - 6 secciones: `apuesta` (outcome + cuota + bookmaker + equipos + fecha), `edge` (p_model/devig/p_fair), `origen_p_model` (elo point-in-time), `stake` (kelly), `calidad_modelo` (brier vs baselines), `metadata`
  - Numeric scenario real (id=10): p_model=0.83394, edge=0.14724, kelly_fraction=0.12016, stake="120.16"
  - Reconciliation invariant: |p_fair_reconstructed − p_fair_derived| ≤ 0.0001
  - MUST NOT recomputar; MUST derivar p_fair = p_model − edge; MUST NO external calls

- `dashboard-frontend/spec.md` (DELTA)
  - R2 MODIFIED: Cards reemplazan tabla; orden cronológico del servidor (no edge DESC); formatters exactos
  - R2A MODIFIED: Agrupación por partido con cards, hint exposición correlacionada
  - R2B ADDED: ExplainDrawer (open/close, skeleton, error handling, mobile responsive)
  - R2C ADDED: Glosario inline (6 términos: edge, de-vig, kelly, elo, brier, calibración)
  - R10 MODIFIED: Test list actualizada (SignalCard, ExplainDrawer, groupSignals, glossary)

---

### Phase 3: Design

**Design.md Summary**:
- Architecture: Aditivo, determinista
- Backend: `app/model/explain.py::build_explanation()` + ensamblador de secciones; `app/model/ratings.py` extrae `lookup_rating`; router thin
- Frontend: `SignalCard`, `SignalCardGroup`, `ExplainDrawer`, `GlossaryTerm`, `glossary.ts`; table deleted
- Key decision: Triple de-vig fijado a `captured_at` del odds_id (snapshot point-in-time); p_fair SIEMPRE derivado; canónicos raw, intermedios formatted
- Hallazgo clave: `best_odds_per_outcome` mezcla casas → overround <1 → p_fair derivado reconcilia exacto
- Data flow: SignalCard click → ExplainDrawer open → useQuery lazy fetch → build_explanation → render (verbatim o formatters.ts)

---

### Phase 4: Tasks (18 items across 5 phases)

**Batch A (Backend ratings+explain+router)**:
- 1.1 Extract `lookup_rating`, `DEFAULT_RATING`, `HOME_ADVANTAGE` → `app/model/ratings.py`
- 1.2 Update `predict_1x2` to import from `ratings.py`
- 1.3 Create `app/model/explain.py` with `build_explanation()`, dataclasses `ExplainStep/Section/Explanation`
- 1.4 Add reconciliation logic (p_fair derivation, triple reconstruction, tolerance check)
- 1.5 Modify `app/api/routers/signals.py` to add `GET /signals/{id}/explain`
- 1.6 Modify `app/api/schemas.py` to add `ExplainStep`, `ExplainSection`, `SignalExplanation`

**Batch B (Frontend components in parallel)**:
- 2.1 Create `frontend/src/components/SignalCard.tsx` (humanized, "¿Por qué?" CTA)
- 2.2 Create `frontend/src/lib/glossary.ts` (6 terms, hincha language)
- 2.3 Create `frontend/src/components/GlossaryTerm.tsx` (expandible <details>)
- 3.1 Create `frontend/src/components/ExplainDrawer.tsx` (lazy, a11y, responsive)

**Batch C (Integration)**:
- 4.1 Create `frontend/src/components/SignalCardGroup.tsx` (groupSignals helper, hint correlation)
- 4.2 Modify `frontend/src/pages/SignalsPage.tsx` (render cards + drawer, remove table)
- 4.3 Delete `frontend/src/components/SignalsTable.tsx` + `.test.tsx`
- 4.4 Modify `frontend/src/api/types.ts` (SignalExplanation types)
- 5.1 Smoke real: curl + verify reconciliation at id=10

---

### Phase 5: Apply (3 Batches)

**Status**: COMPLETE (140 backend + 94 frontend tests, 12 commits)

**Batch A**: Backend ratings extraction + explain module
- `app/model/ratings.py` (NEW): lookup_rating, defaults
- `app/model/explain.py` (NEW): build_explanation(), 5 dataclasses, reconciliation logic, tolerance 1e-3
- `app/model/predict_1x2.py` (MODIFIED): import lookup_rating from ratings
- Tests: 15 backend tests covering reconciliation, point-in-time lookup, numeric scenario id=10

**Batch B**: Frontend components (glossary, SignalCard, ExplainDrawer)
- `lib/glossary.ts` (NEW): 6 terms
- `SignalCard.tsx` (NEW): card layout, formatters reuse, "¿Por qué?" CTA
- `GlossaryTerm.tsx` (NEW): <details>-style expandible
- `ExplainDrawer.tsx` (NEW): drawer with skeleton, error state, mobile responsive, a11y
- Tests: 41 frontend tests (formatters, SignalCard scenarios, GlossaryTerm, ExplainDrawer)

**Batch C**: Integration (grouping, page, removal)
- `SignalCardGroup.tsx` (NEW): groupSignals helper, hint logic
- `SignalsPage.tsx` (MODIFIED): render cards + drawer, min_edge filter preserved
- `SignalsTable.tsx` (DELETED): ~200 lines, 10 tests removed
- `types.ts` (MODIFIED): SignalExplanation, ExplainSection, ExplainStep
- Tests: 7 frontend integration tests + 10 removed SignalsTable tests = net +7 tests
- Smoke: curl localhost:8000/api/v1/signals/10/explain → 6 sections, p_fair=0.6867, reconciliation ✓

**Post-Apply Fixes (Strict TDD)**:
1. RED: `test_explain_signal_10_returns_200_with_expected_sections` using `issubset()` → masked missing `apuesta` section
2. GREEN: Added `_build_apuesta_section()` to build_explanation(); 6 sections now returned
3. Fix glossary key typo: `"calibracion"` → `"calibración"` (logloss step match)
4. Updated assertion to exact equality: `section_keys == ["apuesta","edge",...,"metadata"]`

**Test Results**:
- Backend: 140 passed
- Frontend: 94 passed (93 + 1 new for apuesta section)
- Ruff: All checks passed
- npm build: ✅ No type errors

---

### Phase 6: Verification

**Status**: PASS (after 4 post-verify fixes)

**Reconciliation Audit** (Adversarial):
- Signal id=10 (gtbets, HOME): p_model=0.83394 (✅), edge=0.14724 (✅), kelly=0.12016 (✅), p_fair derived=0.68670 (✅)
- Overround=0.99065 (✅), |recon_diff|=0.00001 ≤ 0.0001 (✅)
- Elo point-in-time: Mexico 1980.33, South Africa 1662.98 (✅)
- Signal id=11 (betfair_ex_eu, HOME): All values reconciled ✅

**Spec Compliance** (35/37 scenarios → 37/37 post-fixes):
- R1 signal-explanation: 6 sections, numeric scenario, 404, no external calls ✅
- R2 Vista Señales: Cards (no `<table>`), order preserved, formatters exact, empty state ✅
- R2A Agrupación: groupSignals, hint ≥2 signals, no hint 1 signal ✅
- R2B ExplainDrawer: Open/close (Escape, X, click-outside), skeleton, error, mobile responsive ✅
- R2C Glosario: 6 terms, tooltip inline, no tooltip for unknown terms ✅
- R10 Testing: All formatters, SignalCard, ExplainDrawer, groupSignals, glossary ✅

**TDD Compliance**: RED/GREEN/TRIANGULATE/SAFETY_NET for all 18 tasks (strict TDD mode)
- RED confirmed: `AssertionError: 'edge' != 'apuesta'` (index 0 mismatch)
- GREEN confirmed: 140 backend + 94 frontend passing
- Safety net: predict_1x2 green post-extract; SignalsPage 100/100 post-integration

**Issues Found & Fixed**:
1. ❌ CRITICAL: Missing `apuesta` section → ✅ FIXED (added _build_apuesta_section)
2. ⚠️ WARNING: `"calibracion"` vs `"calibración"` → ✅ FIXED (typo corrected)
3. ⚠️ WARNING: Weak assertion (issubset) → ✅ FIXED (exact equality)
4. ⚠️ TDD evidence table → ✅ NOTED (documented in commit)

---

### Phase 7: Archive

**Specs Merged**:
- ✅ `openspec/changes/dashboard-ux-explicable/specs/signal-explanation/spec.md` → `openspec/specs/signal-explanation/spec.md` (NEW domain, copied as main spec)
- ✅ `openspec/changes/dashboard-ux-explicable/specs/dashboard-frontend/spec.md` → `openspec/specs/dashboard-frontend/spec.md` (MERGED delta: R2 replaced, R2A updated, R2B+R2C added, R10 updated, SignalsTable removed)

**Change Folder Moved**:
- ✅ `openspec/changes/dashboard-ux-explicable/` → `openspec/changes/archive/2026-06-10-dashboard-ux-explicable/`

**State Updated**:
- ✅ `phase: archived`, `archived_at: 2026-06-10`, `archive_report: true`, test count corrected to 94 frontend

---

## Archive Contents

```
openspec/changes/archive/2026-06-10-dashboard-ux-explicable/
├── proposal.md                   ✅ User intent: intuitive UX + traza trazable
├── specs/
│   ├── signal-explanation/
│   │   └── spec.md               ✅ 6 secciones, numeric scenario, reconciliation invariant
│   └── dashboard-frontend/
│       └── spec.md               ✅ Delta: cards, drawer, glossary, 6 sections tested
├── design.md                     ✅ Architecture decisions, data flow, hallazgo key (best_price mixing)
├── tasks.md                      ✅ 18 items complete (5 phases across 3 batches parallel)
├── state.yaml                    ✅ phase: archived, all artifacts true
└── verify-report.md              ✅ PASS (140 backend + 94 frontend, reconciliation audit, 4 fixes documented)
```

---

## Source of Truth Updated

| File | Action | Summary |
|------|--------|---------|
| `openspec/specs/signal-explanation/spec.md` | Created | NEW domain spec: R1 endpoint, 6 sections, numeric scenario, reconciliation |
| `openspec/specs/dashboard-frontend/spec.md` | Merged | R2 cards (no table), R2A grouping, R2B drawer (NEW), R2C glossary (NEW), R10 tests updated |

---

## SDD Cycle Complete

**Status**: ✅ ARCHIVED

The change has been fully:
1. ✅ **Proposed** — User intent documented, scope clear, risks identified
2. ✅ **Specified** — 2 domain specs (signal-explanation, dashboard-frontend delta), numeric scenarios, reconciliation invariants
3. ✅ **Designed** — Architecture decisions, data flow, key finding (best_price mixing), testing strategy
4. ✅ **Tasked** — 18 items across 3 batches (5 phases), dependencies managed
5. ✅ **Applied** — 140 backend + 94 frontend tests, 12 commits, smoke real verified
6. ✅ **Verified** — FAIL (critical) → PASS (post-fixes), reconciliation audit 2 signals, spec compliance 37/37
7. ✅ **Archived** — Specs merged to main, change folder moved, state marked archived

**Ready for**: Next change (extend drawer/glossary to other pages, or new feature)

---

## Key Findings & Decisions

### Architecture Invariants Enforced
- ✅ **Deterministic, separate from LLM** — model.py builds explanation; router serves; frontend formats only
- ✅ **No external calls in explain** — all data from Postgres, no API-Football, no HTTP in handler
- ✅ **Front NEVER calculates** — server provides raw+formatted; front uses formatters.ts (tested, reusable)
- ✅ **p_fair = p_model − edge, ALWAYS** — derived, never recomputed; reconciles exactly with persistent columns

### Gotchas (Now Documented)
1. **best_price mixing** (Design.md) — `best_odds_per_outcome` toma max() de TODO el histórico y mezcla casas → overround <1 → fuerza p_fair derivada
2. **Glossary key accent** — `"calibracion"` vs `"calibración"` — FIXED post-verify
3. **Drawer a11y** — NO `aria-hidden` on backdrop (gotcha correctly avoided per apply-progress notes)

### Next Natural Successor
- Extend drawer/glossary to other pages (Grupos, Partidos, Modelo) — already possible since components are reusable
- Or new feature (agent narrative on top of these 6 sections — Phase 7 per proposal, out of scope this change)

---

## Verification Snapshot

**Live Test**:
```bash
curl -s localhost:8000/api/v1/signals/10/explain | python3 -c "import json,sys; d=json.load(sys.stdin); print([s['key'] for s in d['sections']])"
['apuesta', 'edge', 'origen_p_model', 'stake', 'calidad_modelo', 'metadata']
```

**Test Suites**:
- Backend: 140/140 passed
- Frontend: 94/94 passed
- Linter: ✅ All checks passed
- TypeScript: ✅ No errors
- Build: ✅ npm build successful

**Commits** (12 total, 10 original + 2 post-verify fixes):
- Dashboard UX explicable end-to-end (10 commits)
- fix(model): sección apuesta + glossary calibración (verify) (1 commit)
- test(frontend): ExplainDrawer fixture 6 secciones (1 commit)

---

*Archive created by sdd-archive skill on 2026-06-10*  
*Mode: hybrid (openspec + engram)*
