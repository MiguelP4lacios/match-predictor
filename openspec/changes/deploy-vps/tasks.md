# Tasks: Deploy VPS barata con Docker (Mundial 2026)

## Phase 1: docker-compose.prod.yml standalone + smoke local

- [x] 1.1 Crear `docker-compose.prod.yml` standalone con: `db` (sin ports, volume `pgdata_prod`, restart unless-stopped, healthcheck pg_isready), `api` (CMD del Dockerfile sin `--reload`, sin bind-mount `.:/app`, `DEBUG=false`, restart unless-stopped, healthcheck `GET http://localhost:8000/health`), `frontend` (build `context: ./frontend target: prod`, `ports: ["127.0.0.1:8080:80"]`, restart unless-stopped), `scheduler` (profiles: [manual]).
- [x] 1.2 Verificar nginx config en `frontend/nginx.conf` (o `Dockerfile` frontend): proxy `location /api` → `http://api:8000` existe y no reescribe prefijo `/api`.
- [x] 1.3 LOCAL lint: `docker compose -f docker-compose.prod.yml config` — confirmar exactamente un `published:` binding `127.0.0.1:8080`, cero entradas `0.0.0.0`. **EVIDENCIA: `grep -c "published:" → 1`; `grep "0.0.0.0" → CLEAN`**.
- [x] 1.4 LOCAL build: `docker compose -f docker-compose.prod.yml build` exits 0. **EVIDENCIA: build exitoso, imagen nginx multi-stage producida**.
- [x] 1.5 LOCAL smoke up (proyecto aislado, BD efímera): `docker compose -p match_predictor_prod -f docker-compose.prod.yml up -d` — todos los servicios Up/healthy. **EVIDENCIA: api=healthy, db=healthy, frontend=Up; volumen aislado `match_predictor_prod_pgdata`**.
- [x] 1.6 LOCAL smoke verify: `curl -fs http://127.0.0.1:8080` → `<!doctype html>` (HTML dashboard) + `curl -fs http://127.0.0.1:8080/api/v1/signals` → `{"items":[],"total":0}` (JSON real vía nginx→api→db prod vacía). **EVIDENCIA: ambos curls pasan**.
- [x] 1.7 LOCAL teardown: `docker compose -p match_predictor_prod -f docker-compose.prod.yml down -v` — volumen efímero eliminado, stack dev intacto (verificado: `match_predictor_pgdata` ≠ `match_predictor_prod_pgdata`; dev api/db/frontend siguen respondiendo).

## Phase 2: Scripts migrate_data.sh y tournament_update.sh

- [x] 2.1 Crear `scripts/migrate_data.sh` (corre en el Mac, `set -euo pipefail`): params `user@host`; pasos: `bash scripts/backup.sh` → `scp` dump más reciente a `VPS:~/backups/` → `ssh VPS docker compose -f docker-compose.prod.yml up -d db` → `ssh VPS "gunzip -c ~/backups/<dump> | docker compose -f docker-compose.prod.yml exec -T db psql -U postgres match_predictor"` → assertions de counts (`match` ≥49,443, `odds_snapshot` >5,800, `value_signal` ≥69; exit 1 con mensaje si falla) → `ssh VPS docker compose -f docker-compose.prod.yml up -d --build`.
- [x] 2.2 LOCAL shellcheck `migrate_data.sh`: `bash -n scripts/migrate_data.sh` limpio + `shellcheck scripts/migrate_data.sh` sin errores. **EVIDENCIA: `docker run koalaman/shellcheck:stable` → Exit 0**.
- [x] 2.3 Crear `scripts/tournament_update.sh` (corre en VPS, `set -euo pipefail`): variable `COMPOSE="docker compose -f docker-compose.prod.yml"`; flag `--skip-odds`; pasos: [1, skip si --skip-odds] `COMPOSE_PROFILES=manual $COMPOSE run --rm scheduler python -m app.scheduler.run --once` → [2] `$COMPOSE run --rm ingest python -m app.ingestion.run --force` → [3] `$COMPOSE run --rm api python -m app.model.run_elo` → [4] `$COMPOSE run --rm api python -m app.model.run_1x2 predict` → [5] `$COMPOSE run --rm api python -m app.model.run_1x2 signals`; imprime `[OK] tournament_update complete`.
- [x] 2.4 LOCAL shellcheck `tournament_update.sh`: `bash -n scripts/tournament_update.sh` + `shellcheck scripts/tournament_update.sh` sin errores. **EVIDENCIA: `docker run koalaman/shellcheck:stable` → Exit 0 (ambos scripts en el mismo run)**.

## Phase 3: Runbook docs/deploy.md + README

- [x] 3.1 Crear `docs/deploy.md` con secciones en orden: bootstrap VPS (Ubuntu 24.04 DigitalOcean, `curl -fsSL https://get.docker.com | sh`), clone (PAT HTTPS read-only + deploy key como alternativa), `.env` creación (`ODDS_API_KEY=<key>`, advertencia NUNCA commitear), migración de datos (`bash scripts/migrate_data.sh VPS_IP root`), stack up (`docker compose -f docker-compose.prod.yml up -d --build`), túnel+verify (`ssh -L 8080:localhost:8080 root@VPS_IP` → `curl http://localhost:8080/api/v1/signals`), ops diaria (`scripts/tournament_update.sh [--skip-odds]` + línea cron para backup), logs/troubleshoot (`docker compose -f docker-compose.prod.yml logs -f api|db|frontend`). RUNBOOK-ONLY: pasos que requieren VPS real.
- [x] 3.2 Agregar sección `## Deploy` breve en `README.md` apuntando a `docs/deploy.md`.

## Phase 4: Git init + commit

- [x] 4.1 VOID — repo ya existe y está pusheado a `https://github.com/MiguelP4lacios/match-predictor` (origin/main). Verificado: `.env` y `backups/` ya están en `.gitignore`.
- [x] 4.2 Commit con conventional commits sin Co-Authored-By: `feat(ops): compose de producción standalone`, `feat(ops): scripts de migración y operación del torneo`, `docs(ops): runbook de deploy en VPS`.
- [x] 4.3 Push al remote GitHub (origin/main existente).
