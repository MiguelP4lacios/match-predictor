# Ops Resilience Specification

## Purpose

Protección de datos irremplazables y hardening operacional antes del Mundial 2026: git, backups de Postgres, restart policies, secretos, build reproducible, e integridad del modelo.

## Requirements

### Requirement: Git Repository Initialization

The project directory MUST be a git repository with at least one commit before any other change in this change-set is applied.

#### Scenario: Git repo exists before first fix commit

- GIVEN the project directory has no `.git/` folder
- WHEN `git init && git add . && git commit -m "chore: initial commit"` is executed
- THEN `git log --oneline` returns at least one line
- AND subsequent fix commits can be reverted individually with `git revert`

---

### Requirement: Database Backup Script

A script `scripts/backup.sh` MUST exist that runs `pg_dump` via `docker compose exec db` and writes the dump to `backups/YYYY-MM-DD_HHMMSS.sql`.

The `backups/` directory MUST be listed in `.gitignore`.

`README.md` MUST contain a warning that `docker compose down -v` deletes all Postgres data permanently, and instruct operators to run the backup script before any destructive operation.

#### Scenario: Backup script produces a dump file

- GIVEN the Postgres container is running
- WHEN `bash scripts/backup.sh` is executed
- THEN a file matching `backups/YYYY-MM-DD_*.sql` is created
- AND `pg_restore --list backups/YYYY-MM-DD_*.sql` exits without error

---

### Requirement: Service Restart Policies

`docker-compose.yml` MUST set `restart: unless-stopped` on both the `db` and `api` services.

The `db` service port binding MUST use `127.0.0.1:5432:5432` (not `0.0.0.0`).

The `api` service port binding MUST use `127.0.0.1:8000:8000` (not `0.0.0.0`).

#### Scenario: Services restart after unexpected stop

- GIVEN `docker compose up -d` has been run
- WHEN `docker kill match_predictor-api-1` is executed
- THEN within 10 seconds `docker compose ps api` shows status `Up`

---

### Requirement: Build and Secret Hardening

The `Dockerfile` MUST copy `uv.lock` before `uv sync` and MUST pass `--frozen` to prevent lock drift in CI/production builds.

The `httpx` exception handler (wherever API keys appear in request URLs or headers) MUST redact the `apiKey` query parameter and `X-RapidAPI-Key` header before logging or re-raising, replacing their values with `***`.

`TeamResolver._get_or_create_team()` in `app/ingestion/resolver.py` MUST perform a case-insensitive lookup: `WHERE lower(team.name) = lower(:norm)` before creating a new team, so `"argentina"` and `"Argentina"` resolve to the same canonical team.

#### Scenario: Frozen build fails on lock mismatch

- GIVEN `uv.lock` and `pyproject.toml` are out of sync
- WHEN `docker compose build api` is run
- THEN the build fails with a lock-file mismatch error (not silently upgrading packages)

#### Scenario: API key not exposed in logs

- GIVEN an httpx request to The Odds API fails with a network error
- WHEN the exception is logged
- THEN the log line MUST NOT contain the literal API key value
- AND the log line MUST contain `***` in place of the key

#### Scenario: Case-insensitive team resolution

- GIVEN team `"Argentina"` exists in the `team` table
- WHEN `TeamResolver.resolve(source, "argentina")` is called
- THEN it returns the existing `Team` with `name="Argentina"` (no duplicate created)

---

### Requirement: Model Version History and Prediction Line

`EloEngine._record_version()` in `app/model/elo_engine.py` MUST NOT overwrite `params_json` of an existing `ModelVersion` row. Instead it MUST insert a new `ModelVersion` row with a versioned name (e.g., `"elo-v2"`, `"elo-v3"`) each time parameters change, preserving the history of all prior versions and their linked `Prediction` rows.

`Prediction` in `app/models/model.py` MUST have a `line` column (`Numeric(5,2)`, nullable) to store the Over/Under line value for which the probability was calculated (e.g., `2.5`).

#### Scenario: Re-running EloEngine creates new version row, not overwrite

- GIVEN `model_version` table has a row with `name="elo-v1"` and `params_json={"k": {"world_cup": 60}}`
- WHEN `EloEngine.compute()` is called after a K-factor config change
- THEN a NEW row is inserted (e.g., `name="elo-v2"`)
- AND the `"elo-v1"` row and its linked `prediction` rows remain intact

#### Scenario: Prediction stores Over/Under line

- GIVEN a Prediction for an Over/Under market with line `2.5`
- WHEN the row is inserted
- THEN `SELECT line FROM prediction WHERE id = :id` returns `2.50`
