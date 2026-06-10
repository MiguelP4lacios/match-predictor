# Verification Report

**Change**: deploy-vps
**Version**: N/A (openspec artifacts)
**Mode**: Standard (no strict TDD — infra/runbook change, not application logic)
**Verified by**: sdd-verify sub-agent (AUTO mode)
**Date**: 2026-06-10

---

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 16 |
| Tasks complete | 16 |
| Tasks incomplete | 0 |

All 16 tasks across Phases 1–4 are marked `[x]`.

---

## Build & Tests Execution

**Build**: ✅ `docker compose -p verify_prod -f docker-compose.prod.yml up -d --build` — all images built and all services reached healthy/up within 30s.

```
verify_prod-api-1      Up (healthy)  8000/tcp (internal only)
verify_prod-db-1       Up (healthy)  5432/tcp (internal only)
verify_prod-frontend-1 Up            127.0.0.1:8080->80/tcp
```

**Tests**: ✅ 140 passed / 0 failed / 0 skipped (exit code 0)

```
pytest --tb=short -q
140 passed, 1 warning in 1.48s
(warning: starlette deprecation for httpx — unrelated to this change)
```

**Coverage**: ➖ Not configured (infra/ops change; no new application logic to cover)

---

## Executable Gate Results

### Gate 1: Exactly one published port, no 0.0.0.0

```bash
docker compose -f docker-compose.prod.yml config | grep -c "published:"   # → 1 ✅
docker compose -f docker-compose.prod.yml config | grep "0.0.0.0"         # → (empty) ✅
```

Binding: `host_ip: 127.0.0.1 / published: "8080" / target: 80` — only in `frontend`. All other services have no `ports:` entries.

### Gate 2: No --reload, no bind-mount in api

Config `api` service: no `command:` override (uses Dockerfile CMD — uvicorn without `--reload`), no `volumes:` listed, `DEBUG: "false"`. ✅

### Gate 3: Scheduler under profiles:[manual]

`docker compose config` (without `--profile manual`) shows 0 references to `scheduler`. With `--profile manual` it appears with `profiles: [manual]` and `restart: unless-stopped`. ✅

### Gate 4: Restart policies

| Service  | restart           |
|----------|-------------------|
| db       | unless-stopped ✅ |
| api      | unless-stopped ✅ |
| frontend | unless-stopped ✅ |
| scheduler| unless-stopped ✅ |
| migrate  | "no" ✅ (one-shot) |
| ingest   | "no" ✅ (one-shot) |

### Gate 5: Smoke test end-to-end

```bash
# Up
docker compose -p verify_prod -f docker-compose.prod.yml up -d --build
# → All healthy

# Curl HTML
curl -fs http://127.0.0.1:8080
# → <!doctype html>…<title>Mundial 2026 — Dashboard +EV</title>… ✅

# Curl API via nginx proxy
curl -fs http://127.0.0.1:8080/api/v1/signals
# → {"items":[],"total":0} ✅  (empty DB is correct; smoke validates HTTP wiring)

# Teardown
docker compose -p verify_prod -f docker-compose.prod.yml down -v
# → verify_prod_pgdata removed ✅

# Dev stack intact
curl -fs http://127.0.0.1:5173  # → <!doctype html>… ✅
curl -fs http://127.0.0.1:8000/health  # → {"status":"ok"} ✅
docker volume ls | grep pgdata  # → match_predictor_pgdata (NOT verify_prod_pgdata) ✅
```

### Gate 6: Shell script quality

```bash
bash -n scripts/migrate_data.sh     # → OK ✅
bash -n scripts/tournament_update.sh # → OK ✅
docker run koalaman/shellcheck:stable /mnt/scripts/migrate_data.sh \
                                      /mnt/scripts/tournament_update.sh
# → Exit 0 ✅ (SC2029 suppressions are justified: intentional client-side expansion)
```

No secrets echoed anywhere (grep for API_KEY/TOKEN/PASSWORD in script outputs → CLEAN). ✅

### Gate 7: Git state

```
Branch: main
Local == origin/main (no commits ahead, no commits behind)
Working tree: clean
Commits: 3 conventional commits pushed (feat, feat, docs)
```

---

## Spec Compliance Matrix

| Requirement | Scenario | Evidence | Result |
|-------------|----------|----------|--------|
| Compose Production Override | Exactly one published port after merge | `config \| grep -c "published:" → 1`; `host_ip: 127.0.0.1` | ✅ COMPLIANT |
| Compose Production Override | Dev compose unaffected | After `down -v -p verify_prod`: dev :5173 HTML ✅, dev :8000/health ✅, `match_predictor_pgdata` still present | ✅ COMPLIANT |
| Data Migration Script | Successful migration unlocks full up | Static: `FAIL=0` path → `docker compose ... up -d --build` called. Thresholds: 49443/5800/69 match spec exactly | ✅ RUNBOOK-ONLY |
| Data Migration Script | Incomplete restore blocks startup | Static: `FAIL=1` → `exit 1` before any `compose up`. Message printed to stderr | ✅ RUNBOOK-ONLY |
| Tournament Update Script | Abort on step failure | `set -euo pipefail` + no `|| true` guards → any non-zero exits script. Steps 4+5 unreachable if step 3 fails | ✅ RUNBOOK-ONLY |
| Tournament Update Script | Skip odds step | `$SKIP_ODDS == "true"` → step 1 block skipped entirely; steps 2–5 run; exits 0 | ✅ RUNBOOK-ONLY |
| Deploy Runbook | Runbook is self-contained | All 8 required sections present; commands copy-pasteable; DigitalOcean named; Spanish; `.env` warning present; `.env` in `.gitignore` ✅ | ✅ RUNBOOK-ONLY |

**Compliance summary**: 7/7 scenarios compliant (2 locally executed, 5 documented-check via static analysis — no VPS exists yet, per verification instructions).

---

## Correctness (Static — Structural Evidence)

| Requirement | Status | Notes |
|-------------|--------|-------|
| `docker-compose.prod.yml` standalone (no base file needed) | ✅ Implemented | Self-contained file; `docker compose -f docker-compose.prod.yml` only |
| api: no bind-mount, no --reload, no public ports | ✅ Implemented | No `volumes:` in api service; no `command:` override; no `ports:` |
| db: no public ports, healthcheck pg_isready | ✅ Implemented | No `ports:`, `pg_isready -U postgres -d match_predictor` healthcheck |
| frontend: nginx multi-stage, 127.0.0.1:8080 only | ✅ Implemented | `target: prod`, `ports: ["127.0.0.1:8080:80"]` |
| scheduler: profiles [manual] | ✅ Implemented | Not started by default; accessible via `COMPOSE_PROFILES=manual` |
| restart: unless-stopped on all long-running services | ✅ Implemented | db/api/frontend/scheduler=unless-stopped; migrate/ingest="no" |
| nginx proxy `/api` → `http://api:8000` without rewrite | ✅ Implemented | `location /api { proxy_pass http://api:8000; }` — no `rewrite` or strip |
| migrate_data.sh: `set -euo pipefail`, count assertions, no secrets | ✅ Implemented | All three guards present; thresholds exact (49443/5800/69) |
| tournament_update.sh: `set -euo pipefail`, `--skip-odds`, [OK] message | ✅ Implemented | All present; `[OK] tournament_update complete` on success |
| docs/deploy.md: 8 sections in required order | ✅ Implemented | All sections present; DigitalOcean, Spanish, copy-pasteable |
| README.md Deploy section pointing to docs/deploy.md | ✅ Implemented | Section present with migrate + tunnel commands |
| `.env` and `backups/` in .gitignore | ✅ Implemented | Verified in .gitignore |

---

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Standalone `docker-compose.prod.yml` (not override) — OVERRULES proposal | ✅ Yes | Single file, no `-f base -f prod` anywhere |
| ODDS_API_KEY via `.env` only (never committed) | ✅ Yes | `${ODDS_API_KEY:-}` in compose; .env in .gitignore |
| api healthcheck uses `python urllib` (no curl in image) | ✅ Yes | `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"` |
| Volume isolation with project name `-p` flag | ✅ Yes | `verify_prod_pgdata` vs `match_predictor_pgdata` confirmed isolated |
| scheduler `COMPOSE_PROFILES=manual` for `run --rm` in tournament loop | ✅ Yes | Line 42 in tournament_update.sh |
| SSH tunnel only (no public port) | ✅ Yes | `127.0.0.1:8080` binding confirmed; no port 80/443 |
| Step 2: `ingest` service with `--force` (design overrides spec `--no-download` on `api`) | ⚠️ Deviated from spec | Design section "Interfaces/Contracts" explicitly chose `run --rm ingest python -m app.ingestion.run --force`. Spec was not retroactively updated. Functionally correct. |
| Runbook verify curl uses `/api/v1/signals` not `/api/health` (design: `/health` not proxied) | ⚠️ Deviated from spec | Spec says `curl http://localhost:8080/api/health`. Design says "NO `/health`: va sin prefijo, nginx no lo proxya". Implementation is MORE correct than spec. |

---

## Issues Found

**CRITICAL** (must fix before archive):
None.

**WARNING** (should fix):

1. **Spec not updated after design override (tournament_update.sh step 2)**
   - Spec: `docker compose ... run --rm api python -m app.ingestion.run --no-download`
   - Implementation: `docker compose -f docker-compose.prod.yml run --rm ingest python -m app.ingestion.run --force`
   - Design explicitly chose `ingest` service + `--force` (upsert ON CONFLICT, safer) and is justified. The spec was never updated to reflect this. No functional impact, but creates a paper trail inconsistency.
   - Recommendation: Update spec step 2 to match design/implementation, OR add a note in spec acknowledging the design override.

2. **Spec not updated after design override (compose command pattern)**
   - Spec (and originally all scripts) reference `docker compose -f docker-compose.yml -f docker-compose.prod.yml`. 
   - Implementation uses `docker compose -f docker-compose.prod.yml` (standalone, per design decision).
   - Design section "Standalone vs override (OVERRULES proposal)" fully justifies this. No functional impact.
   - Recommendation: Same as above — update spec to match agreed design.

3. **Runbook verify curl (`/api/health` vs `/api/v1/signals`)**
   - Spec says `curl http://localhost:8080/api/health`; runbook uses `curl http://localhost:8080/api/v1/signals`.
   - The runbook is CORRECT (health endpoint is at `/health`, not proxied by nginx). Spec is misleading.
   - Recommendation: Update spec scenario to use `/api/v1/signals` (or any endpoint that actually routes through nginx proxy).

**SUGGESTION** (nice to have):

1. **ODDS_API_KEY visible in `docker compose config` output**
   - When `docker compose config` is run, the `.env` is loaded and `ODDS_API_KEY` appears in plaintext. This is expected Docker behavior. No risk as long as this command is never run in shared logs or CI without masking.
   - Recommendation: Add a note in runbook/troubleshoot section about this.

2. **`ingest` one-shot service in standalone compose does not have the `--force` flag by default**
   - `docker-compose.prod.yml` ingest service `command: python -m app.ingestion.run` (no `--force`). The `--force` is only applied in `tournament_update.sh` via `run --rm ingest`. This means a bare `docker compose up` would run ingestion without `--force`. By design this is intentional (respects `sync_log`), but the comment in compose file (`# Para forzar manualmente: ... --force`) makes this clear.
   - No action needed; already documented.

---

## Verdict

**PASS WITH WARNINGS**

The implementation is functionally complete and correct. All 140 tests pass. The prod stack smoke test verified HTML dashboard and `/api/v1/signals` JSON via nginx proxy end-to-end. Security gates pass (1 port at 127.0.0.1:8080, no 0.0.0.0, no secrets in scripts). Shellcheck clean. Dev stack isolation verified. Git is clean and in sync with origin/main.

The 3 warnings are all paperwork inconsistencies — the spec was not retroactively updated to reflect two design-level overrides (standalone compose and `--force`/`ingest` in step 2) that were explicitly and correctly justified in `design.md`. These do not affect runtime behavior. Spec updates are recommended before archiving.
