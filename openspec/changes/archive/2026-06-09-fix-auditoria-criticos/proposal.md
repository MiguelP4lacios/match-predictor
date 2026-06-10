# Proposal: Fix de críticos de auditoría pre-Mundial

## Intent

La auditoría Fable 5 (2026-06-09) encontró 4 bugs de modelo que producen **Elo distorsionado y odds corruptas/perdidas**, y 3 fallas operacionales que ponen en riesgo datos irremplazables. El Mundial arranca ~2026-06-11 y se va a apostar plata real: hay que arreglar esto **antes** de construir el modelo de probabilidades (fase 4). Findings verificados contra el código actual.

## Scope

### In Scope
- **F1 — K-factor:** agregar `CompetitionKind.OTHER` (enum migration), whitelist de continentales reales, matcheo estricto de "world cup" (excluir CONIFA/"Viva"), backfill de `competition.kind`.
- **F2 — Idempotencia:** unique constraint en identidad de match + upsert real (`ON CONFLICT DO UPDATE` sobre score/status); re-ingesta incremental sin `--force`.
- **F3 — Persistencia de odds:** persistir SIEMPRE (`match_id` nullable) + columnas `source_event_id`/`commence_time` en `odds`; `Match.kickoff_at` (nueva columna) desde `commence_time`; job de re-linkeo.
- **F4 — Linkeo de odds:** desambiguar por `commence_time` vs fecha del match (±1 día); `DRAW` solo si `outcome_name == "Draw"`; mismatch → descartar + log.
- **F5 — Git:** `git init` + commit inicial + recomendación de remoto privado. **Primer paso, todo lo demás son commits.**
- **F6 — Backups:** script `pg_dump` vía docker, `backups/` gitignored, warning en README sobre `down -v`.
- **F7 — Resiliencia:** `restart: unless-stopped` en `db`/`api` + nota ops (`caffeinate` durante el torneo).
- **Warnings baratos (misma ola de migración):** redactar apiKey en excepciones httpx; bind `127.0.0.1` en Postgres/API; `COPY uv.lock` + `--frozen` en Dockerfile; columna `line` en `Prediction`; preservar histórico de `ModelVersion` (no sobreescribir params); resolver case-insensitive.

### Out of Scope (próximos changes, NO absorber)
- Modelo Elo→1X2, EV/Kelly, captura de futures, poblar tablas de grupo, backtest, endpoints API, agentes, dashboard.

## Capabilities

### New Capabilities
- `match-ingestion`: ingesta idempotente de resultados/fixtures (F1, F2).
- `odds-capture`: captura, persistencia y linkeo confiable de snapshots de cuotas (F3, F4).
- `ops-resilience`: git, backups, restart policies, hardening de secrets/red (F5, F6, F7, warnings).

### Modified Capabilities
- None (no hay specs previas; fases 1-3 se construyeron sin SDD).

## Approach

Un solo change, secuenciado: **git init primero**, luego una **ola de migración Alembic** que agrupa todos los cambios de schema (enum OTHER, unique constraint, columnas de odds, `kickoff_at`, `line`), luego fixes de pipeline con **tests primero (strict TDD)**, backfill de datos, y **recompute de Elo al final**. Cada finding = commit pequeño y verificable.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/models/enums.py` | Modified | `CompetitionKind.OTHER` |
| `app/ingestion/pipeline.py` | Modified | F1 whitelist/matcheo, F2 upsert idempotente |
| `app/ingestion/odds_pipeline.py` | Modified | F3 persistir siempre, F4 desambiguación/DRAW estricto |
| `app/models/odds.py`, `match.py`, `model.py` | Modified | `source_event_id`/`commence_time`, `kickoff_at`, `line` |
| `migrations/versions/` | New | Ola única: enum + constraint + columnas + backfill |
| `app/model/elo_engine.py` | Modified | preservar histórico `ModelVersion` + recompute |
| `app/ingestion/resolver.py` | Modified | case-insensitive |
| `docker-compose.yml`, `Dockerfile`, `README.md` | Modified | restart, bind 127.0.0.1, `--frozen`, warning |
| `scripts/backup.sh`, `.gitignore` | New | backup + ignore `backups/` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **Recompute de Elo cambia TODOS los ratings**: cualquier consumidor downstream debe re-leer | High | Aún no hay consumidor (fase 4 pendiente); recompute es determinista (borra+recalcula); correr al final |
| Enum migration sobre BD viva (ALTER TYPE ADD VALUE) | Med | `ADD VALUE` es no-bloqueante en PG; backfill en transacción separada con conteo antes/después |
| Unique constraint falla si ya hay duplicados | Med | Verificar duplicados con query antes de aplicar; si existen, dedup primero |
| Backfill de `kind` reclasifica miles de competiciones | Med | Snapshot de distribución `kind` antes/después; el recompute lo absorbe |
| Re-linkeo de odds históricas escaso (1 snapshot hoy) | Low | Impacto bajo ahora; el valor es a futuro (knockout) |

## Rollback Plan

- **Schema:** cada cambio en su propia migración Alembic → `alembic downgrade -1`. Backup `pg_dump` ANTES de migrar/backfill (F6 entra primero).
- **Código:** git ya inicializado (F5) → cada fix es un commit revertible con `git revert`.
- **Elo:** recompute es idempotente; revertir kind/K y volver a correr `EloEngine.compute()` restaura el estado previo.
- **Datos:** restaurar desde el `pg_dump` previo si el backfill corrompe.

## Dependencies

- Postgres corriendo en docker (`docker compose`). Migraciones y tests vía `docker compose run --rm api ...`.
- Sin dependencias externas nuevas.

## Success Criteria

- [ ] Repo git inicializado; cada fix en un commit conventional.
- [ ] Backup `pg_dump` ejecutable y documentado; warning de `down -v` en README.
- [ ] `db`/`api` con `restart: unless-stopped`; puertos en `127.0.0.1`.
- [ ] Tests (RED→GREEN) para F1–F4 antes del fix; `pytest` verde.
- [ ] Torneos menores con `kind=OTHER` (K=30); CONIFA fuera de WORLD_CUP; whitelist de continentales aplicada.
- [ ] Re-ingesta con `--force` NO duplica matches (upsert verificado).
- [ ] Odds sin fixture se persisten (`match_id` NULL) y se re-linkean al cargar el fixture.
- [ ] `line` en `Prediction`; apiKey nunca en logs/tracebacks; build con `--frozen`.
- [ ] Elo recalculado tras los fixes; distribución de `kind` documentada antes/después.
