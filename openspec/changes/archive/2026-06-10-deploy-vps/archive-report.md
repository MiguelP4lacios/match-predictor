# Archive Report: deploy-vps

**Change Name**: deploy-vps  
**Archived Date**: 2026-06-10  
**Artifact Store Mode**: hybrid  
**Status**: ARCHIVED (PASS WITH WARNINGS — post-verify fixes applied)

---

## Executive Summary

The **deploy-vps** change is complete and archived. It delivers a production-ready VPS deployment strategy for the Mundial 2026 system using Docker Compose standalone, with automated data migration, daily tournament update loops, and a self-contained runbook. All 16 implementation tasks passed. Verification completed with 3 spec-documentation warnings (all fixed post-verify in delta spec). The change is ready for the user's final deployment on their DigitalOcean VPS.

**CRITICAL PENDING ITEM**: This archive represents preparation and validation; the actual VPS deployment by the end user is the final integration test. First deploy on real infrastructure is explicitly noted as out-of-scope for sdd-verify (which validates scripts locally) but is REQUIRED to close this cycle in production.

---

## Lineage

### Proposal → Spec → Design → Tasks → Apply → Verify → Archive

#### Proposal (sdd-propose, 2026-06-09)

**Problem**: The system runs on a developer's Mac; must run 24/7 on a low-cost VPS for Mundial 2026. Odds data (captured live) is irreplaceable and must be preserved. No time for auth/TLS; minimize complexity.

**Scope**:
- Production Compose override file (`docker-compose.prod.yml`)
- Data migration script (Mac → VPS preserving odds)
- Daily tournament update loop script
- Deployment runbook (copy-paste commands for non-ops users)
- Tunnel-only exposure (no public ports)

**Out-of-Scope**: CI/CD, public domain/TLS, auth, external monitoring, automated scheduler (cron documented, manual trigger only).

**Success Criteria**:
- [ ] `docker compose -f docker-compose.prod.yml up -d --build` works on VPS
- [ ] Only `127.0.0.1:8080` listens
- [ ] Dashboard reachable via SSH tunnel with historical odds restored
- [ ] `scripts/tournament_update.sh` runs complete daily loop
- [ ] Deploy reproducible in <30 min

#### Design (sdd-design, 2026-06-10)

**Architectural Decisions**:

1. **Standalone Compose (OVERRULES proposal)**
   - Proposal suggested override: `-f docker-compose.yml -f docker-compose.prod.yml`
   - **Decision**: Single standalone file `docker-compose.prod.yml` (no base file merge)
   - **Rationale**: Local Docker Compose v2.17.2 lacks `!reset` syntax (added in 2.24). Merging additive `ports:` and `volumes:` sections without reset causes silent bugs: dev bind-mounts and ports merge into prod config, exposing `0.0.0.0` ports. Standalone eliminates this entire class of bug.

2. **Network Isolation**
   - `api`, `db`: no `ports:` entries (internal network only)
   - `frontend`: single `ports: ["127.0.0.1:8080:80"]` (nginx)
   - `scheduler`: `profiles: [manual]` (not auto-started; triggered via `run --rm` in tournament loop)

3. **Data Preservation**
   - Dump created on Mac, transferred via `scp`, restored on VPS **before** full stack up
   - Restore validation: count assertions before proceeding (>5,800 odds snapshots)
   - Re-ingestion does NOT recover odds → restore is mandatory

4. **Service Contracts**
   - `api`: no bind-mount `.:/app`, no `--reload`, uses Dockerfile `CMD` (uvicorn), `DEBUG=false`
   - `frontend`: build from `./frontend/Dockerfile` with `target: prod` (multi-stage nginx)
   - `db`: `healthcheck: pg_isready -U postgres -d match_predictor`, `restart: unless-stopped`
   - All long-running services: `restart: unless-stopped`; one-shots (`migrate`, `ingest`): `restart: no`

5. **Bootstrap & Secrets**
   - Docker install: official method (`curl -fsSL https://get.docker.com | sh`)
   - User: root (Hetzner default; single-user, SSH-only access)
   - Secrets: `.env` with `ODDS_API_KEY` never committed (in `.gitignore`)
   - Git access: fine-grained GitHub PAT (read-only) or deploy key (both documented)

#### Spec (sdd-spec, 2026-06-10, post-verify fix)

**4 Requirements** (refined post-design):

1. **Compose Production Override**
   - Requirement: `docker-compose.prod.yml` standalone, exactly one published port at `127.0.0.1:8080`, no `0.0.0.0` bindings
   - Scenario 1: Merge result has exactly 1 `published:` entry
   - Scenario 2: Dev compose (`docker compose up -d`) unaffected

2. **Data Migration Script** (`scripts/migrate_data.sh`, runs on Mac)
   - Requirement: Full Mac→VPS migration with validation assertions
   - Scenario 1: Restore succeeds → full `up -d --build` proceeds
   - Scenario 2: Incomplete restore → script aborts before `compose up`

3. **Tournament Update Script** (`scripts/tournament_update.sh`, runs on VPS)
   - Requirement: Daily loop (odds optional, ingest→elo→predict→signals)
   - Scenario 1: Step failure → entire script exits non-zero
   - Scenario 2: `--skip-odds` flag skips odds, runs steps 2–5

4. **Deploy Runbook** (`docs/deploy.md`)
   - Requirement: Self-contained, copy-pasteable, 8 ordered sections
   - Scenario: Clean Ubuntu 24.04, following docs sequentially → stack up and dashboard accessible in <30 min

**Design Overrides Applied to Spec (post-verify)**:
- Step 2 in `tournament_update.sh` now specifies `ingest` service with `--force` flag (safer upsert ON CONFLICT)
- Compose command pattern throughout specs updated to `docker compose -f docker-compose.prod.yml` (standalone)
- Verify curl endpoint changed from `/api/health` (not proxied) to `/api/v1/signals` (correctly proxied by nginx)

#### Tasks (sdd-tasks, 2026-06-10)

**16 tasks across 4 phases**:

- **Phase 1** (6 tasks): Compose standalone creation, nginx proxy validation, lint, build, smoke up/verify/teardown
- **Phase 2** (4 tasks): `migrate_data.sh` creation + shellcheck, `tournament_update.sh` creation + shellcheck
- **Phase 3** (2 tasks): Runbook creation, README Deploy section
- **Phase 4** (4 tasks): Git state verification, conventional commits, push to remote

**All 16 tasks**: [x] marked complete in `tasks.md`

#### Apply (sdd-apply, 2026-06-10)

**Implementation**: 
- `docker-compose.prod.yml` created standalone (no merge, no override)
- `scripts/migrate_data.sh` with `set -euo pipefail`, count assertions, no secrets
- `scripts/tournament_update.sh` with `--skip-odds` flag, 5-step loop, `[OK]` summary
- `docs/deploy.md` with 8 required sections (DigitalOcean bootstrap, clone, .env, migration, up, tunnel, ops, troubleshoot)
- `README.md` updated with Deploy section pointing to runbook
- `.env` and `backups/` verified in `.gitignore`
- 3 conventional commits pushed to origin/main (feat, feat, docs)

**Code Quality**: 140 tests pass (no new app logic, infra change). Shellcheck clean. No secrets in logs.

#### Verify (sdd-verify, 2026-06-10)

**Result**: PASS WITH WARNINGS (3 spec-documentation issues, all fixed post-verify)

**Executable Gates** (all green):
1. ✅ Exactly one published port (`127.0.0.1:8080`), no `0.0.0.0`
2. ✅ No bind-mount, no `--reload` in api
3. ✅ Scheduler under `profiles: [manual]`
4. ✅ Restart policies on all long-running services
5. ✅ Smoke end-to-end (HTML dashboard, JSON via nginx proxy, dev stack isolated)
6. ✅ Shell scripts pass shellcheck, no secrets
7. ✅ Git state clean (3 commits, origin/main in sync)

**Spec Compliance**: 7/7 scenarios compliant (2 local, 5 documented-check per design).

**Issues Found (all warnings, no critical)**:

1. **Spec not updated: Step 2 `--force`/`ingest` service**
   - Proposal/spec said: `docker compose ... run --rm api python -m app.ingestion.run --no-download`
   - Design decided: `docker compose ... run --rm ingest python -m app.ingestion.run --force` (safer upsert)
   - **Fix applied**: Spec section 3 (Tournament Update Script), line 78, updated to match implementation

2. **Spec not updated: Compose command pattern**
   - Proposal/spec said: `docker compose -f docker-compose.yml -f docker-compose.prod.yml`
   - Design decided: standalone `docker compose -f docker-compose.prod.yml` (no base merge)
   - **Fix applied**: All spec sections referencing compose command updated to standalone pattern

3. **Spec verify curl endpoint**
   - Spec said: `curl http://localhost:8080/api/health`
   - Design: `/health` endpoint has no `/api` prefix (health is at `:8000/health`), not proxied by nginx
   - **Fix applied**: Spec Requirement 4, Scenario 1 (Runbook), line 111, updated to `/api/v1/signals`

---

## Artifacts Synced to Main Specs

| Domain | Source | Target | Action |
|--------|--------|--------|--------|
| `prod-deploy` | `openspec/changes/deploy-vps/specs/prod-deploy/spec.md` | `openspec/specs/prod-deploy/spec.md` | Created (new domain) |

**Requirements merged**: All 4 requirements (Compose, Data Migration, Tournament Update, Runbook) moved to main spec. No previous main spec existed; delta was complete.

---

## Change Folder Moved to Archive

```
openspec/changes/deploy-vps/
  ↓ (moved)
openspec/changes/archive/2026-06-10-deploy-vps/
```

Contents verified in archive:
- proposal.md ✅
- specs/prod-deploy/spec.md ✅
- design.md ✅
- tasks.md ✅
- verify-report.md ✅
- state.yaml ✅

---

## SDD Cycle Completion

| Phase | Status | Output |
|-------|--------|--------|
| Explore | ✅ Completed | (implicit in proposal context) |
| Propose | ✅ Completed | Problem, scope, approach, rollback plan documented |
| Spec | ✅ Completed | 4 requirements + scenarios, design overrides applied post-verify |
| Design | ✅ Completed | Architectural decisions (standalone, network, migration, contracts) |
| Tasks | ✅ Completed | 16 tasks (compose + scripts + runbook + git), all [x] |
| Apply | ✅ Completed | Code written, tests pass, scripts validated, commits pushed |
| Verify | ✅ Completed | PASS WITH WARNINGS, 3 fixes applied, gates green, smoke test end-to-end |
| Archive | ✅ Completed | Specs synced, change folder moved, artifacts indexed |

**SDD is closed.** The change is production-ready for end-user deployment.

---

## Important: Execution Pending

This archive represents **preparation and validation in a controlled environment** (local smoke tests on developer Mac). The implementation is ready for deployment on the user's DigitalOcean VPS.

**NEXT STEP (not part of SDD)**: The end user will follow `docs/deploy.md` to:
1. Provision a Ubuntu 24.04 VPS
2. Install Docker
3. Clone the repo and create `.env` with `ODDS_API_KEY`
4. Run `bash scripts/migrate_data.sh VPS_IP root` (preserves odds from Mac)
5. Verify dashboard via SSH tunnel
6. Schedule `scripts/tournament_update.sh` via cron for daily runs

This **first deployment on real hardware is the final integration test**. It validates:
- SSH tunnel access from Mac to VPS
- Data migration without loss
- PostgreSQL restore integrity
- nginx proxy behavior in production network conditions
- Scaling from 2GB→4GB RAM if needed (Elo/fit performance)

**If VPS deployment fails**: refer to runbook troubleshoot section; rollback is simple (compose down, data preserved in volume).

---

## Risk Assessment

| Risk | Likelihood | Mitigation | Post-Deploy Check |
|------|------------|------------|-------------------|
| 2GB RAM insufficient (Elo fit) | Med | Runbook recommends 4GB (~$7/mo) | Monitor `docker stats` during first tournament_update run |
| Odds lost in migration | Low | Restore assertions before full up | `select count(*) from odds_snapshot` on VPS after migration |
| Secrets (ODDS_API_KEY) exposed | Low | .env in .gitignore, tunnel-only access | `docker compose config \| grep ODDS_API_KEY` (expect plaintext; never share logs) |
| SSH tunnel disconnection | Low | Documented restart: `ssh -L ...` persistent tmux session | Keep tunnel open in dedicated terminal during operations |

---

## Conventions & Compliance

- **Testing**: No new application logic; infra/ops change. 140 existing tests pass. Shellcheck validation replaces unit tests for scripts.
- **Commits**: Conventional commits (feat/docs) without Co-Authored-By attribution (per project CLAUDE.md).
- **Secrets**: `.env` never committed; documented as VPS-only input. `.gitignore` verified.
- **Git State**: Clean, 3 commits pushed, origin/main in sync.

---

## Artifacts Persisted

### Engram (hybrid mode)
Topic keys (if available):
- `sdd/deploy-vps/proposal`
- `sdd/deploy-vps/spec`
- `sdd/deploy-vps/design`
- `sdd/deploy-vps/tasks`
- `sdd/deploy-vps/verify-report`
- `sdd/deploy-vps/archive-report` ← this file

### OpenSpec (hybrid mode)
Files:
- `openspec/specs/prod-deploy/spec.md` (main spec, synced)
- `openspec/changes/archive/2026-06-10-deploy-vps/` (change folder, complete audit trail)

---

## For Next Sessions

If continuing this work:
1. Refer to `docs/deploy.md` for end-user VPS deployment
2. Collect deployment logs and outcomes for future iterations (e.g., monitoring, auto-scaling)
3. Post-deploy: measure Elo/fit performance, odds count stability, tournament_update runtime
4. Consider future changes: TLS (Caddy+cert), auth (basic-auth or Tailscale), external monitoring

---

## Closure

The deploy-vps change is **complete and archived**. All requirements met, warnings addressed, gates passing, and readiness validated. The system is prepared for 24/7 operation on a production VPS.

**Status**: ARCHIVED ✅  
**Date**: 2026-06-10  
**Artifact Store**: hybrid (openspec + engram)  
**Ready for**: End-user VPS deployment following `docs/deploy.md`
