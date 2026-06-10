# Prod Deploy Specification

## Purpose

Production deployment of match_predictor on a VPS for Mundial 2026: compose override
(no reload, no bind-mount, single public port via tunnel), scripted data migration
preserving irreplaceable odds, daily tournament loop, and a runbook enabling
reproducible deploys in <30 min.

## Requirements

---

### Requirement: Compose Production Override

A file `docker-compose.prod.yml` MUST exist that overrides `docker-compose.yml` such that:
- `api` uses no bind-mount (`.:/app` removed), no `--reload` (uses Dockerfile CMD), no published ports.
- `db` has no published ports.
- `frontend` is built from `./frontend/Dockerfile` (multi-stage nginx) and publishes ONLY `127.0.0.1:8080:80`.
- `scheduler` is under `profiles: [manual]` (not started by default).
- All non-one-shot services MUST declare `restart: unless-stopped`.

#### Scenario: Exactly one published port after merge

- GIVEN `docker-compose.prod.yml` exists
- WHEN `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` is run
- THEN the merged config contains exactly one `published:` entry binding `127.0.0.1:8080`
- AND no binding references `0.0.0.0`

#### Scenario: Dev compose unaffected

- GIVEN a developer machine with no `COMPOSE_FILE` override
- WHEN `docker compose up -d` is run (base file only)
- THEN `127.0.0.1:5173` (frontend) and `127.0.0.1:8000` (api) are accessible unchanged
- AND `docker-compose.yml` requires no modification

---

### Requirement: Data Migration Script

A script `scripts/migrate_data.sh` MUST implement the full Mac→VPS migration procedure:
1. Run `bash scripts/backup.sh` locally (produces `backups/YYYY-MM-DD_HHMMSS.sql.gz`).
2. `scp` the dump to the VPS.
3. On the VPS, start `db` only: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d db`.
4. Restore: `gunzip -c <dump> | docker compose exec -T db psql -U postgres match_predictor`.
5. Assert row counts (MUST exit non-zero and abort if any assertion fails):
   - `match` table: ≥ 49,443
   - `odds_snapshot` table: > 5,800
   - `value_signal` table: ≥ 69
6. If all counts pass, proceed with full `up`.

#### Scenario: Successful migration unlocks full up

- GIVEN a valid dump is restored into the VPS db container
- WHEN `bash scripts/migrate_data.sh` verifies counts
- THEN `match` ≥ 49,443, `odds_snapshot` > 5,800, `value_signal` ≥ 69 are confirmed
- AND the script continues to `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`

#### Scenario: Incomplete restore blocks startup

- GIVEN the restored DB has `odds_snapshot` count = 0
- WHEN count assertions run
- THEN the script prints the failing assertion and exits non-zero
- AND `docker compose up` is NOT called

---

### Requirement: Tournament Update Script

A script `scripts/tournament_update.sh` MUST chain the following steps using `set -e`
(abort on first non-zero exit). The compose invocation MUST use
`-f docker-compose.yml -f docker-compose.prod.yml`. Step 1 MUST be skipped if
`--skip-odds` flag is passed.

| Step | Command |
|------|---------|
| 1 (optional) | `docker compose ... run --rm scheduler python -m app.scheduler.run --once` |
| 2 | `docker compose ... run --rm api python -m app.ingestion.run --no-download` |
| 3 | `docker compose ... run --rm api python -m app.model.run_elo` |
| 4 | `docker compose ... run --rm api python -m app.model.run_1x2 predict` |
| 5 | `docker compose ... run --rm api python -m app.model.run_1x2 signals` |

The script MUST print a `[OK] tournament_update complete` summary on success.

#### Scenario: Abort on step failure

- GIVEN `python -m app.model.run_elo` exits non-zero
- WHEN `tournament_update.sh` is running
- THEN steps 4 and 5 are NOT executed and the script exits non-zero

#### Scenario: Skip odds step

- GIVEN odds API credits are exhausted
- WHEN `bash scripts/tournament_update.sh --skip-odds` is run
- THEN step 1 is omitted, steps 2–5 run normally, script exits 0

---

### Requirement: Deploy Runbook

A file `docs/deploy.md` MUST contain exact, copy-pasteable commands for each of these
sections in order:

| Section | Required content |
|---------|-----------------|
| VPS bootstrap | Docker install on Ubuntu 24.04 (official `apt` method) |
| Clone | HTTPS+token AND deploy key options (both documented) |
| `.env` creation | File with `ODDS_API_KEY=<your_key>` — warn NEVER commit |
| Data migration | Call `scripts/migrate_data.sh` with pre/post steps |
| Stack up | `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` |
| Tunnel + verify | `ssh -L 8080:localhost:8080 user@VPS_IP` then `curl http://localhost:8080/api/health` |
| Daily ops | `scripts/tournament_update.sh` invocation + cron backup line |
| Logs / troubleshoot | `docker compose logs -f api`, `db`, `frontend` commands |

#### Scenario: Runbook is self-contained

- GIVEN a clean Ubuntu 24.04 VPS with SSH access and the GitHub repo
- WHEN an operator follows `docs/deploy.md` sequentially
- THEN the stack is up and dashboard is reachable via tunnel in < 30 minutes
- AND no undocumented prerequisite is required
