# Tasks: Fix de críticos de auditoría pre-Mundial

## Phase 1: Git + Backup

- [x] 1.1 `git init && git add . && git commit -m "chore: initial commit pre-fix"` en el root del proyecto. ops-resilience R1.S1
- [x] 1.2 Crear `scripts/backup.sh` (pg_dump via `docker compose exec db` → `backups/YYYY-MM-DD_HHMMSS.sql`); añadir `backups/` a `.gitignore`; ejecutar backup. **MANUAL-OPTIONAL** ops-resilience R2.S1

## Phase 2: Alembic Migration Wave

- [x] 2.1 `app/models/enums.py`: añadir `OTHER = "other"` a `CompetitionKind`. Prereq de M1.
- [x] 2.2 M1: `alembic revision` con `autocommit_block` → `ALTER TYPE competition_kind ADD VALUE IF NOT EXISTS 'other'`; `docker compose run --rm migrate alembic upgrade head`. D2
- [x] 2.3 `app/models/odds.py` (+`source_event_id VARCHAR(80)`, `commence_time TIMESTAMP`), `match.py` (+`kickoff_at TIMESTAMP`), `model.py` (+`Prediction.line Numeric(5,2)` nullable). odds-capture R1, ops-resilience R4
- [x] 2.4 M2: `alembic revision --autogenerate` para columnas nuevas; revisar diff; upgrade head.
- [x] 2.5 Crear `scripts/dedup.py` (conservar `MIN(id)`, re-apuntar FKs, borrar duplicados en `match` y teams case-dup). M3: UNIQUE `(match_date, home_team_id, away_team_id)` + CHECK `ck_odds_target` + índice funcional `lower(team.name)`; ejecutar dedup ANTES de M3. D7

## Phase 3: TDD RED

- [x] 3.1 `tests/test_classification.py`: FIFA WC→WORLD_CUP; CONIFA/CECAFA→OTHER; Copa América→CONTINENTAL; WC qualification→QUALIFIER; k_factor correcto por kind. match-ingestion R1.S1–S5
- [x] 3.2 `tests/test_upsert.py`: re-ingest no duplica (count fijo); status SCHEDULED→FINISHED se aplica. match-ingestion R2.S1–S3
- [x] 3.3 `tests/test_odds_persist.py`: sin fixture → `match_id IS NULL`, `unlinked_events > 0`; con fixture → `match_id NOT NULL`. odds-capture R1.S1–S2
- [x] 3.4 `tests/test_odds_relink.py`: `relink_orphan_odds` linkea fila NULL; commence_time desambigua entre dos fixtures del mismo par. odds-capture R1.S3, R2.S3
- [x] 3.5 `tests/test_outcome_code.py`: `outcome_name == "Draw"` → DRAW; equipo sin resolver → descartar + log warning. odds-capture R2.S1–S2
- [x] 3.6 `tests/test_resolver.py`: `"argentina"` → `Team("Argentina")` existente, sin duplicado. ops-resilience R3.S3
- [x] 3.7 `tests/test_model_version.py`: params cambiados → INSERT `elo-v2`; `elo-v1` y sus predictions intactos. ops-resilience R4.S1

> Confirmar RED: `docker compose run --rm api pytest -x` — todos deben fallar aquí.

## Phase 4: TDD GREEN

- [x] 4.0 (añadida) M4: `ALTER TYPE competition_kind ADD VALUE IF NOT EXISTS 'OTHER'` (uppercase) — SQLAlchemy serializa NOMBRES de miembros; el label `'other'` de M1 queda como cruft inofensivo. Verificado con round-trip ORM.
- [x] 4.1 Crear `app/ingestion/classification.py`: `classify_competition_kind(name) → CompetitionKind` + `CONTINENTAL_CHAMPIONSHIPS` frozenset; actualizar `pipeline.py` para importarlo. D4
- [x] 4.2 `app/ingestion/pipeline.py` `_load_matches`: upsert `ON CONFLICT(match_date, home_team_id, away_team_id) DO UPDATE` (score, status, neutral, stage) en lotes de 1000. D5
- [x] 4.3 `app/model/elo_engine.py`: `OTHER: 30` explícito en `_K_BY_KIND`; `_record_version` → INSERT nuevo row si `params_json` difiere, reusar si idéntico. D6
- [x] 4.4 `app/ingestion/odds_pipeline.py`: persistir siempre (`match_id` nullable); guardar `source_event_id`/`commence_time`; DRAW estricto; discard + log si equipo no resuelto; `relink_orphan_odds(session)` con ventana ±1d. D3
- [x] 4.5 `app/ingestion/resolver.py`: lookup `WHERE lower(team.name) = lower(:norm)`. D7
- [x] 4.6 `app/ingestion/sources/odds_api.py`: `_raise_for_status_redacted(resp)` — enmascara `apiKey` query param y `X-RapidAPI-Key` con `***`. D8

> Confirmar GREEN: `docker compose run --rm api pytest` — todos deben pasar.

## Phase 5: Backfill competition.kind

- [x] 5.1 Crear `scripts/backfill_kind.py`: snapshot distribución `kind` antes; reclasifica todas las filas con `classify_competition_kind`; snapshot después. Correr: `docker compose run --rm api python scripts/backfill_kind.py`. match-ingestion R1 (backfill)
- [x] 5.2 Verificar en output que torneos CONIFA/Viva/minor pasaron a `OTHER`; registrar distribución antes/después en el commit message.

## Phase 6: Ops Hardening

- [x] 6.1 `docker-compose.yml`: `restart: unless-stopped` en `db` y `api`; binds `127.0.0.1:5432:5432` y `127.0.0.1:8000:8000`. ops-resilience R3.S1
- [x] 6.2 `Dockerfile`: añadir `COPY uv.lock .` antes de `RUN uv sync`; añadir flag `--frozen`. **MANUAL**: verificar que build falla con lock desincronizado. ops-resilience R3.S2
- [x] 6.3 `README.md`: warning `down -v elimina todos los datos de Postgres`; instrucción de ejecutar backup previo; nota `caffeinate` durante el torneo. ops-resilience R2, R3

## Phase 7: Elo Recompute + Verificación Final

- [x] 7.1 Recompute Elo: `docker compose run --rm api python -m app.model.run_elo`. Verificar nueva fila `elo-vN` en `model_version`. ops-resilience R4
- [x] 7.2 Suite final: `docker compose run --rm api pytest` verde; `docker compose run --rm api ruff check .` sin errores.
- [x] 7.3 **MANUAL-OPTIONAL**: `SELECT kind, count(*) FROM competition GROUP BY kind ORDER BY count DESC` — confirmar 0 rows WORLD_CUP para torneos no-FIFA; sin kind NULL.
