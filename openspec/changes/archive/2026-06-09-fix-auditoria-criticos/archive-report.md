# Archive Report: fix-auditoria-criticos

**Date Archived**: 2026-06-09  
**Change**: fix-auditoria-criticos  
**Verdict**: APPROVED (APPROVED WITH WARNINGS — all warnings fixed post-verify)  
**Status**: CLOSED AND ARCHIVED

---

## Executive Summary

Fix de 4 bugs de modelo + 3 fallas operacionales críticos pre-Mundial 2026. Todos identificados por auditoría Fable 5, verificados contra código, corregidos con TDD strict, backfill de datos, recompute de Elo (49,371 partidos), y hardening operacional. **Zero CRITICAL issues.** Change complete, tested (64/64), committed, and ready for next phase.

---

## Lineage

### Proposal
**File**: `proposal.md`  
**Scope**: 7 findings (F1–F7) + 4 warnings económicos, secuenciados en 1 change.
- F1: K-factor classification (WORLD_CUP vs OTHER vs CONIFA)
- F2: Idempotent match ingestion (upsert, no duplicates)
- F3: Always-persist odds (match_id nullable)
- F4: Reliable odds linkage (outcome_code DRAW stricto, desambiguación por commence_time)
- F5: Git initialization + conventional commits
- F6: Database backups (pg_dump via docker)
- F7: Service restart policies + secret redaction
- Warnings: redact apiKey, bind 127.0.0.1, frozen builds, case-insensitive resolver, ModelVersion history, Prediction.line column

### Design
**File**: `design.md`  
**Key Decisions**:
- **D1**: Match identity = `(match_date, home_team_id, away_team_id)` — no `competition_id` (prevents Elo double-count on reclassification)
- **D2**: Enum migration with `autocommit_block` (PG constraint: new enum values not usable same transaction)
- **D3**: Odds CHECK constraint `ck_odds_target` — allows both `match_id` and `competition_id` NULL (pending fixture)
- **D4**: Shared classifier (`classification.py`) — used by ingestion and backfill, no duplication
- **D5**: Upsert `ON CONFLICT uq_match_identity DO UPDATE` — preserves `id` and `competition_id`, updates score/status/stage
- **D6**: ModelVersion immutable — INSERT new version only on params change, reuse when unchanged (idempotent recompute)
- **D7**: Pre-dedup before UNIQUE constraints; case-insensitive resolver (`lower(team.name)`)
- **D8**: API key redaction in error paths (`_raise_for_status_redacted`)

### Specifications
**Files**: `specs/match-ingestion/spec.md`, `specs/odds-capture/spec.md`, `specs/ops-resilience/spec.md`

#### match-ingestion
- **R1: K-factor Classification** — 5 scenarios: FIFA WC→WORLD_CUP(60), CONIFA→OTHER(30), Copa América→CONTINENTAL(50), Qualifier→QUALIFIER(40), fallback→OTHER(30)
- **R2: Idempotent Match Ingestion** — 3 scenarios: re-ingest no duplicates, updated scores applied, incremental skip if synced

#### odds-capture
- **R1: Always-Persist Odds** — persist with `match_id=NULL` if no fixture; include `source_event_id`, `commence_time`; relink job exists
- **R2: Reliable Outcome Code** — "Draw" only if `outcome_name=="Draw"` (exact); unresolved team → discard (not DRAW); disambiguate by commence_time ±1d

#### ops-resilience
- **R1: Git Initialization** — repo with commits before any fix
- **R2: Database Backup** — script `pg_dump` via docker to `backups/`
- **R3: Service Restart Policies** — `restart: unless-stopped` on db/api; port binds 127.0.0.1
- **R3: Build + Secret Hardening** — Dockerfile `--frozen` + uv.lock; redact apiKey; case-insensitive resolver
- **R4: Model Version History + Prediction.line** — ModelVersion immutable (INSERT on params change); Prediction.line column for O/U lines

### Implementation (4 Apply Batches)

#### Batch A: Git + Migrations + Dedup (Commits 1–4)
- `chore: initial commit pre-fix` — baseline
- `feat(ingestion): add CompetitionKind.OTHER enum` — M1 (autocommit_block)
- `feat(models): add odds.source_event_id, .commence_time; match.kickoff_at; prediction.line` — M2
- `feat(ingestion): dedup matches and teams; add uq_match_identity + ck_odds_target + functional index` — M3/M4

**Result**: 49,445 initial rows → 2 duplicates removed → 49,443 idempotent baseline; `ModelVersion.name` immutable (M1); enums uppercase serialization (M4)

#### Batch B: TDD RED→GREEN (Commits 5–10)
- Tests created (RED): classification, upsert, odds persist/relink, outcome_code, resolver, model_version
- Code fixes (GREEN):
  - `classification.py` — pure classifier + CONTINENTAL_CHAMPIONSHIPS frozenset (D4)
  - `pipeline.py` — import classifier, ON CONFLICT upsert (D5)
  - `elo_engine.py` — explicit K_OTHER=30, immutable ModelVersion (D6)
  - `odds_pipeline.py` — always-persist, strict DRAW, relink_orphan_odds (D3/D4)
  - `resolver.py` — case-insensitive `lower(name)` (D7)
  - `odds_api.py` — `_raise_for_status_redacted` (D8)

**Tests**: 62 passed initially, 64 after W3 fix (added Prediction.line round-trip test)

#### Batch C: Backfill + Recompute (Commits 11–13)
- `scripts/dedup.py` — removed 2 duplicates (Tahiti/New Caledonia score conflict, Gibraltar/Cayman Islands double-entry)
- `scripts/backfill_kind.py` — reclassified all competitions; distribution:
  - Before: WORLD_CUP=1 (FIFA), CONTINENTAL=8, QUALIFIER=18, NATIONS_LEAGUE=2, FRIENDLY=1, OTHER=0, NULL=~170
  - After: WORLD_CUP=1, CONTINENTAL=8, QUALIFIER=18, NATIONS_LEAGUE=2, FRIENDLY=1, **OTHER=170** (all reclassified minor tournaments)
- `EloEngine.compute()` — recompute 49,371 matches with corrected K-factors; top-4 ratings: España 2250, Argentina 2242, Francia 2150, Colombia 2147

#### Batch D: Ops Hardening + Final (Commits 14–15)
- `docker-compose.yml` — `restart: unless-stopped`, port binds 127.0.0.1
- `Dockerfile` — COPY uv.lock, `uv sync --frozen`
- `scripts/backup.sh` — pg_dump via docker to `backups/YYYY-MM-DD_HHMMSS.sql`
- `.gitignore` — added `backups/`
- `README.md` — warning on `down -v`, backup instruction, `caffeinate` note for tournament

### Verification
**File**: `verify-report.md`  
**Verdict**: APPROVED WITH WARNINGS (all 3 warnings fixed post-verify)

| Metric | Value | Status |
|--------|-------|--------|
| Tasks Complete | 22/22 (phases 1–7) | ✅ |
| Tests | 64/64 passed | ✅ |
| Linter | ruff clean | ✅ |
| CRITICAL Issues | 0 | ✅ |
| WARNINGS | 3 (all fixed post-verify) | ✅ |

**Warnings Fixed Post-Verify**:
1. **W1** — Spec R2 text was stale (said `(competition_id, match_date, home_team_id, away_team_id)` but design D1 chose `(match_date, home_team_id, away_team_id)` to prevent Elo double-count). **Fixed**: Updated spec text to match D1 decision. ✅
2. **W2** — R2.S1 scenario count was pre-dedup (49,445 vs actual 49,443). **Fixed**: Updated scenario to 49,443. ✅
3. **W3** — Prediction.line behavioral test missing (schema column existed but no round-trip test). **Fixed**: Added test to verify INSERT/SELECT round-trip of `line=2.5` → `2.50`. Suite now 64/64. ✅

**Compliance Summary**: 17/20 spec scenarios directly compliant; 2 partial (manual-optional config tests); 1 untested → TESTED post-verify. ✅

---

## Specs Merged to Source of Truth

| Domain | File | Action | Content |
|--------|------|--------|---------|
| match-ingestion | `openspec/specs/match-ingestion/spec.md` | **Created** | K-factor classification (5 scenarios), Idempotent match ingestion (3 scenarios) |
| odds-capture | `openspec/specs/odds-capture/spec.md` | **Created** | Always-persist odds (3 scenarios), Reliable outcome code (3 scenarios) |
| ops-resilience | `openspec/specs/ops-resilience/spec.md` | **Created** | Git initialization, Backup script, Restart policies, Build hardening, Model version history (5 requirements) |

**First SDD change in project**: No prior main specs existed. Delta specs copied directly to `openspec/specs/` as new source of truth.

---

## Artifacts Archive

All artifacts moved to `openspec/changes/archive/2026-06-09-fix-auditoria-criticos/`:

```
2026-06-09-fix-auditoria-criticos/
├── proposal.md                          # Intent, scope, risks, rollback
├── design.md                            # 8 architecture decisions, data flow, testing strategy
├── specs/
│   ├── match-ingestion/spec.md         # K-factor classification + idempotency (6 reqs, 8 scenarios)
│   ├── odds-capture/spec.md            # Always-persist + outcome code reliability (2 reqs, 6 scenarios)
│   └── ops-resilience/spec.md          # Git, backup, restart, hardening (5 reqs, 8 scenarios)
├── tasks.md                             # 22 completed tasks across 7 phases (56 lines)
├── verify-report.md                     # 64/64 tests, APPROVED WITH WARNINGS (warnings fixed post-verify)
├── state.yaml                           # SDD DAG state: archived
└── archive-report.md                    # This file
```

---

## Engram Artifacts (Hybrid Mode)

Corresponding entries saved to Engram with full observation IDs for audit trail:

| Artifact | Topic Key | Type |
|----------|-----------|------|
| Proposal | `sdd/fix-auditoria-criticos/proposal` | architecture |
| Design | `sdd/fix-auditoria-criticos/design` | architecture |
| Spec: match-ingestion | `sdd/fix-auditoria-criticos/spec-match-ingestion` | architecture |
| Spec: odds-capture | `sdd/fix-auditoria-criticos/spec-odds-capture` | architecture |
| Spec: ops-resilience | `sdd/fix-auditoria-criticos/spec-ops-resilience` | architecture |
| Tasks | `sdd/fix-auditoria-criticos/tasks` | architecture |
| Apply Progress (4 batches) | `sdd/fix-auditoria-criticos/apply-progress` | architecture |
| Verify Report | `sdd/fix-auditoria-criticos/verify-report` | architecture |
| State | `sdd/fix-auditoria-criticos/state` | architecture |
| Archive Report | `sdd/fix-auditoria-criticos/archive-report` | architecture |

---

## SDD Cycle Completion

| Phase | Status | Result |
|-------|--------|--------|
| **sdd-init** | ✅ Complete | Stack detected (Python 3.12 + FastAPI + PostgreSQL + SQLAlchemy), Strict TDD enabled |
| **sdd-explore** | ✅ Complete | 4 model bugs + 3 ops risks identified by audit |
| **sdd-propose** | ✅ Complete | 7 findings scoped, 1-change approach approved |
| **sdd-spec** | ✅ Complete | 3 domains, 20 scenarios, 8 requirements specified |
| **sdd-design** | ✅ Complete | 8 architecture decisions (D1–D8), data flows, migration strategy |
| **sdd-tasks** | ✅ Complete | 22 tasks across 7 phases, all `[x]` marked |
| **sdd-apply** | ✅ Complete | 4 implementation batches, 64/64 tests, ruff clean, zero criticals |
| **sdd-verify** | ✅ Complete | APPROVED WITH WARNINGS; all 3 warnings fixed post-verify |
| **sdd-archive** | ✅ Complete | Specs merged to main, change archived, state updated, engram saved |

**Next Phase**: None. Change is fully closed. Next SDD change can now proceed (e.g., Elo→1X2 probabilities, EV/Kelly staking, futures backtesting).

---

## Success Criteria Met

- [x] Repo git initialized; all 15 fixes as conventional commits (revertible)
- [x] Backup `pg_dump` created and documented (`backups/2026-06-09_231625.sql.gz`, 2.8 MB)
- [x] Docker services `db`/`api` with `restart: unless-stopped`; ports on `127.0.0.1`
- [x] Tests RED→GREEN: 64/64 passing (11 test modules, strict TDD)
- [x] K-factor classification: CONIFA→OTHER (not WORLD_CUP), CECAFA→OTHER, Copa América→CONTINENTAL, WC Qualifier→QUALIFIER
- [x] Idempotency verified: re-ingest count stays 49,443; upsert preserves `id` + `competition_id`
- [x] Odds always-persist: unlinked events stored with `match_id=NULL`; re-linkeo job exists and functional
- [x] DRAW strict: only `outcome_name=="Draw"` maps to DRAW; unresolved teams discarded + logged
- [x] Elo recomputed: 49,371 matches with corrected K-factors; distribution before/after documented
- [x] Data integrity: 0 schema violations, 0 NULL kinds, 2 duplicates removed, case-insensitive team resolver active
- [x] Secret hardening: apiKey never in logs; Dockerfile frozen; build fails on lock mismatch
- [x] Model version history: elo-v1 preserved + linked predictions; recompute idempotent (no spam)
- [x] Prediction.line: column exists, round-trip tested (2.5→2.50)

---

## Known Limitations

- **Idempotency scope**: goal_event/shootout tables not covered (auditoría no lo flaggeó; open question in D6)
- **Team resolver**: `_NAME_OVERRIDES` (legacy alias mapping) not merged into team resolution — deferrable to future change
- **Odds history**: Only 1 snapshot captured to date; re-linkeo value realized at tournament knockout phase

---

## Rollback Instructions

| Component | Rollback Method | Notes |
|-----------|-----------------|-------|
| Schema | `alembic downgrade -1` per M (4 migrations) | Idempotent (M1 `IF NOT EXISTS`, dedup pre-UNIQUE) |
| Code fixes | `git revert` commit hash | Each fix is a separate commit |
| Elo | Re-run `EloEngine.compute()` after reverting kind backfill | Deterministic; restores prior state |
| Data | Restore `backups/2026-06-09_*.sql.gz` | Pre-fix backup available |

---

## Closed/Archived
**Change Status**: ✅ ARCHIVED  
**Source of Truth**: `openspec/specs/` (3 domains, 20 scenarios, 8 requirements)  
**Audit Trail**: `openspec/changes/archive/2026-06-09-fix-auditoria-criticos/` + Engram  
**Next Change**: Ready to proceed with phase 4 (Elo→1X2 probabilities)
