# Proposal: Deploy a VPS barata con Docker (Mundial 2026)

## Intent

El Mundial arranca mañana (2026-06-11). El stack vive solo en el Mac, que se suspende y corta escrituras. Necesitamos un deploy <30 min en una VPS barata que corra 24/7, **preservando las odds capturadas (IRREMPLAZABLES)** y el Elo. No construir auth ni TLS — minimizar superficie y tiempo.

## Scope

### In Scope
- `docker-compose.prod.yml` (override: `-f docker-compose.yml -f docker-compose.prod.yml`).
- **Migración de datos** Mac→VPS: `backup.sh` → `scp` → restore (parte obligatoria del flow).
- `docs/deploy.md`: prerrequisitos, instalación Docker, clone, `.env`, up, verificación.
- `scripts/tournament_update.sh`: encadena captura→ingest→elo→predict→signals (loop diario, 1 comando).
- Exposición vía túnel SSH (cero superficie pública).

### Out of Scope
- CI/CD, dominio/TLS público, auth, monitoreo externo, scheduler automático de odds (cron documentado, NO activado).

## Capabilities

### New Capabilities
- `prod-deploy`: override de compose para producción (sin `--reload`, sin bind-mount, frontend multi-stage como único puerto, db/api sin puerto público, scheduler en `profiles: [manual]`, restart policies), runbook de deploy, migración de datos y loop de operación del torneo.

### Modified Capabilities
- None (las invariantes de `ops-resilience` — binds 127.0.0.1, restart policies, backup — se heredan y refuerzan; no cambian a nivel spec).

## Approach

- **Override prod**: el frontend usa su `Dockerfile` multi-stage (nginx sirve estático + proxy `/api`→`api:8000`), publicado SOLO en `127.0.0.1:8080:80`. `api`/`db` sin puerto publicado (red interna). `api` con CMD del Dockerfile (sin `--reload`, sin volumen `.:/app`). `migrate`/`ingest` one-shot igual. `scheduler` bajo `profiles: [manual]`.
- **Exposición**: acceso por túnel `ssh -L 8080:localhost:8080 user@vps`. Cero auth que construir, cero puerto abierto. Futuro documentado: Caddy+basic-auth o Tailscale.
- **Datos**: levantar `db` sola → restore del dump → luego `up` completo. Re-ingestar NO recupera las odds.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `docker-compose.prod.yml` | New | Override producción |
| `scripts/tournament_update.sh` | New | Loop diario en 1 comando |
| `docs/deploy.md` | New | Runbook paso a paso |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| 2GB RAM insuficiente (numpy/scipy en Elo sobre 98k partidos) | Med | Recomendar **4GB (~$7)**; Elo/fit son los picos |
| Pérdida de odds en migración | Low | Restore verificado antes del primer `up` completo |
| `.env`/deploy key commiteados | Low | `.env` solo en VPS; deploy key o token, nunca en repo |

## Rollback Plan

La VPS es **aditiva**: el Mac sigue siendo copia local funcional. Si el deploy falla, se sigue operando local (`caffeinate -i docker compose up -d`). Para revertir VPS: `docker compose down` (datos en volumen) o destruir la VPS; el dump original queda en el Mac.

## Dependencies

- Usuario crea: VPS Ubuntu 24.04 + SSH key + repo GitHub privado con remote pusheado + `ODDS_API_KEY`.

## Success Criteria

- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` levanta todo en la VPS.
- [ ] Solo `127.0.0.1:8080` escucha; nada público (`ss -tlnp` sin `0.0.0.0`).
- [ ] Dashboard accesible por túnel SSH con las odds históricas restauradas.
- [ ] `scripts/tournament_update.sh` corre el loop diario completo.
- [ ] Deploy reproducible en <30 min desde prerrequisitos.
