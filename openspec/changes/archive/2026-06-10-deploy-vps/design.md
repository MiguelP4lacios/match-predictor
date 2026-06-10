# Design: Deploy VPS barata con Docker (Mundial 2026)

## Technical Approach

`docker-compose.prod.yml` **standalone** (no override) levanta el stack 24/7 en una VPS Ubuntu. Frontend nginx multi-stage (único puerto `127.0.0.1:8080:80`, proxy `/api`→`api:8000`); `api`/`db` sin puerto público; `scheduler` en `profiles:[manual]`. Exposición solo por túnel SSH. Migración Mac→VPS preserva odds (irremplazables). Dos scripts: `migrate_data.sh` (corre en el Mac) y `tournament_update.sh` (corre en la VPS). Runbook en `docs/deploy.md`.

## Architecture Decisions

### Standalone vs override (OVERRULES proposal)
| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Override `-f base -f prod` | `ports`/`volumes` cortos MERGEAN (aditivo): el dev publica `:8000`/`:5432` y bind-mount `.:/app` que NO se pueden quitar sin `!reset` (compose ≥2.24). Local es **v2.17.2** → no soporta `!reset`. Requeriría 4+ resets frágiles | ❌ Rechazado |
| **Standalone `-f docker-compose.prod.yml`** | Un archivo autocontenido, independiente de la versión de compose, cero merge magic | ✅ |
**Rationale**: con compose 2.17 local y un usuario sin experiencia ops bajo deadline, el merge aditivo de puertos/volúmenes es una trampa silenciosa (publicaría puertos en `0.0.0.0` por concatenación). Standalone elimina la clase entera de bug. El comando único es `docker compose -f docker-compose.prod.yml ...`.

### Puertos y bind-mount
`api`/`db` SIN `ports:` (solo red interna). `db` sin bind del dev. `api` SIN volumen `.:/app` (corre desde la imagen) y command sin `--reload` (usa el CMD del Dockerfile: `uvicorn ... --host 0.0.0.0 --port 8000`). `DEBUG:"false"`. Frontend `build: {context: ./frontend, target: prod}`, `ports: ["127.0.0.1:8080:80"]`. Anchor `x-app` prod = mismo env, sin volumen de código.

### Bootstrap VPS
| Tema | Decisión | Rechazado |
|------|----------|-----------|
| Docker | `curl -fsSL https://get.docker.com \| sh` (oficial, trae compose v2 plugin actual) | apt docker.io (viejo, multi-paso) |
| Usuario | **root** (Hetzner default; single-user, exposición solo por túnel) | crear deploy-user (pasos extra, sin ganancia real) |
| Repo | **PAT fine-grained read-only** sobre HTTPS, tipeado interactivo en la VPS | deploy key (generar par, registrar en GitHub, ssh-agent) |
Secrets nunca commiteados: `.env` y PAT solo viven en la VPS.

### Migración de datos (`scripts/migrate_data.sh`, corre en el Mac)
Orquestada desde el Mac vía `ssh`/`scp` (menos error-prone que pasos manuales): `backup.sh` local → `scp` dump → en VPS `up -d db` → restore `gunzip -c dump | docker compose exec -T db psql`. El dump plano incluye esquema+datos+`alembic_version`, por eso se restaura ANTES del `up` completo; `migrate` luego es no-op idempotente. Re-ingestar NO recupera odds → restore obligatorio primero.

## Data Flow

    Mac: backup.sh ─scp─→ VPS:backups/  ─restore→ db (schema+odds+elo)
                                                   │
    docker compose -f prod up -d ──→ db→migrate(no-op)→api + frontend(nginx)
                                                   │
    túnel: ssh -L 8080:localhost:8080 root@vps ──→ navegador Mac → :8080

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `docker-compose.prod.yml` | Create | Stack standalone de producción |
| `scripts/migrate_data.sh` | Create | Backup→scp→restore Mac→VPS |
| `scripts/tournament_update.sh` | Create | Loop diario en 1 comando |
| `docs/deploy.md` | Create | Runbook para alguien sin experiencia VPS |

## Interfaces / Contracts

`tournament_update.sh` (corre en VPS, `set -euo pipefail`, flag `--skip-odds`, todo vía `docker compose -f docker-compose.prod.yml run --rm`):

    [odds]   run --rm scheduler python -m app.scheduler.run --once   # salvo --skip-odds
    ingest   run --rm ingest    python -m app.ingestion.run --force  # --force SEGURO (upsert ON CONFLICT)
    elo      run --rm api        python -m app.model.run_elo
    predict  run --rm api        python -m app.model.run_1x2 predict
    signals  run --rm api        python -m app.model.run_1x2 signals
    # resumen final: counts + nº señales

`fit`/`backtest` son one-time (entrenamiento + gate de honestidad), NO en el loop diario.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Smoke | stack arriba | `compose ps` todo Up/healthy; `migrate`+`ingest` exit 0 |
| Red | nada público | `ss -tlnp` solo `127.0.0.1:8080` y `:22` (sshd) |
| API vía nginx | proxy `/api` | `curl -fs localhost:8080/api/v1/signals` (200) — **NO `/health`: va sin prefijo, nginx no lo proxya** |
| Datos | odds preservadas | `psql -c "select count(*) from match; select count(*) from odds"` = counts del Mac |
| Visual | dashboard | abrir `http://localhost:8080` por el túnel |

## Migration / Rollout

Aditiva: el Mac sigue como copia funcional. Rollback = `compose down` (datos en volumen) o destruir VPS; el dump original queda en el Mac.

## Open Questions

- [ ] El frontend React debe llamar a `/api/v1/...` (no `/health`) para pasar por el proxy nginx — verificar en el build del dashboard antes del deploy.
