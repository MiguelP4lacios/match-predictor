# Tasks: API REST Señales + Grupos WC2026

> Strict TDD — all commands via `docker compose run --rm api`. RED before GREEN, always.

---

## Phase 1: Core puro TDD — standings.py + union-find

- [x] 1.1 RED `tests/model/test_standings.py`: escenarios S1 (sin empate numérico), S2 (DG desempata), S3 (H2H desempata B>C), S4 (0 partidos → orden alfa); triple-empate que cae a nombre. Todos fallan.
- [x] 1.2 RED `tests/model/test_group_utils.py`: función pura `derive_components(edges)` — grafo 12×4 → OK; 11 componentes → AssertionError; componente de 5 → AssertionError. Todos fallan.
- [x] 1.3 GREEN `app/model/standings.py`: `compute_standings(members, results) -> list[StandingRow]`; desempates FIFA (Pts→DG→GF→H2H recursivo `_rank`); docstring con orden de criterios. Tests 1.1 verdes.
- [x] 1.4 GREEN `app/model/group_utils.py`: union-find puro `derive_components`; aserción dura `len==12 and all(len==4)`. Tests 1.2 verdes.

## Phase 2: Helper odds_queries.py

- [x] 2.1 RED `tests/model/test_odds_queries.py`: `best_odds_per_outcome(match_id, session)` devuelve la cuota máxima; `latest_per_bookmaker(match_id, outcome_code, session)` devuelve un registro por bookmaker. Fallan.
- [x] 2.2 GREEN `app/model/odds_queries.py`: implementar ambos helpers con queries SQLAlchemy 2.0 (sin N+1). Tests 2.1 verdes.
- [x] 2.3 REFACTOR `app/model/signals.py`: importar de `odds_queries`; eliminar lógica duplicada. Tests previos de signals siguen verdes.

## Phase 3: Seed TDD + ejecución real

- [x] 3.1 RED `tests/model/test_seed_groups.py`: (a) grafo válido 12×4 ejecuta sin error; (b) grafo roto lanza AssertionError antes de escribir; (c) doble ejecución no duplica filas. Fallan.
- [x] 3.2 GREEN `scripts/seed_groups.py`: mapping oficial A–L embebido como `dict[frozenset[str], str]` con nombres canónicos (consultar `SELECT name FROM team WHERE ...` para resolver "Türkiye vs Turkey", "Czechia vs Czech Republic", "Curaçao vs Curacao", "DR Congo vs Congo DR", "Ivory Coast"); union-find sobre fixtures WC2026 SCHEDULED; aserción dura; upsert `TournamentGroup` (12) + `GroupTeam` (48); backfill `match.stage=GROUP` + `match.group_id`; imprime tabla letra→equipos. Tests 3.1 verdes.

  Mapping A–L (nombres a verificar contra BD):
  A: Mexico, South Africa, South Korea, Czechia | B: Canada, Bosnia and Herzegovina, Qatar, Switzerland | C: Brazil, Morocco, Haiti, Scotland | D: United States, Paraguay, Australia, Türkiye | E: Germany, Curaçao, Ivory Coast, Ecuador | F: Netherlands, Japan, Sweden, Tunisia | G: Belgium, Egypt, Iran, New Zealand | H: Spain, Cape Verde, Saudi Arabia, Uruguay | I: France, Senegal, Iraq, Norway | J: Argentina, Algeria, Austria, Jordan | K: Portugal, DR Congo, Uzbekistan, Colombia | L: England, Croatia, Ghana, Panama

- [x] 3.3 EXECUTE `docker compose run --rm api python scripts/seed_groups.py`: verificar output impreso (12 grupos, composición por letra); confirmar en BD: 12 `tournament_group`, 48 `group_team`, 72 matches con `group_id IS NOT NULL` y `stage='GROUP'`. Reportar tabla impresa (grupo K debe mostrar Colombia).

## Phase 4: API TDD

- [x] 4.1 `app/api/schemas.py`: schemas Pydantic v2 `from_attributes` — `SignalItem`, `SignalList`, `UpcomingMatch`, `MatchDetail`, `ModelInfo`, `PaperStats`, `GroupItem`, `GroupDetail` (con `fixtures`). Sin lógica.
- [x] 4.2 RED `tests/api/test_signals.py`: lista filtrada (R2-S1), vacía (R2-S2), paginación. RED `tests/api/test_matches.py`: upcoming con predicciones (R3-S1), sin predicciones (R3-S2), detail (R4-S1), 404 (R4-S2). Fixture `client(db_session)` con override `get_session`.
- [x] 4.3 RED `tests/api/test_model.py`: R5-S1 (valores exactos de DB). RED `tests/api/test_paper.py`: ROI numérico (R6-S1), settled=0 → roi=null (R6-S2). RED `tests/api/test_groups.py`: 12 grupos (R3-S1), vacío (R3-S2), GET /groups/B (R4-S1), GET /groups/b normalizado (R4-S3), 404 grupo M (R4-S2).
- [x] 4.4 GREEN `app/api/routers/signals.py`: JOIN query anti-N+1; filtros `from/to/min_edge`; `limit`/`offset` (caps: default 50, max 200).
- [x] 4.5 GREEN `app/api/routers/matches.py`: upcoming (2-query anti-N+1, agrupar en Python); detail (`DISTINCT ON` odds, 404).
- [x] 4.6 GREEN `app/api/routers/model.py`: `ModelVersion` de mayor `id`; campos desde `params_json`. GREEN `app/api/routers/paper.py`: counts + ROI `sum(pnl)/sum(stake)` sobre WON/LOST; guard `settled=0 → null`.
- [x] 4.7 GREEN `app/api/routers/groups.py`: GET `/groups` (selectinload members + FINISHED matches, `compute_standings`); GET `/groups/{name}` (case-insensitive, fixtures con predicciones nullable, 404).
- [x] 4.8 `app/core/config.py`: añadir `cors_origins: list[str] = ["http://localhost:5173"]`.
- [x] 4.9 `app/main.py`: `include_router` ×5 con prefijo `/api/v1`; `CORSMiddleware(app, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])` antes de routers.

## Phase 5: Verificación final

- [x] 5.1 Suite completa verde: `docker compose run --rm api pytest` — 0 errores, 0 warnings críticos.
- [x] 5.2 Linter: `docker compose run --rm api ruff check . && ruff format --check .` — zero issues.
- [x] 5.3 Smoke real 7 endpoints con curl contra `docker compose up -d api`; mostrar respuesta de `/api/v1/groups/K` (Colombia visible), `/api/v1/signals`, `/api/v1/model`.
- [x] 5.4 Commit: `feat(api): read-only signals, standings, groups endpoints + seed WC2026`.
