# Design: API REST de Señales (read-only) + Grupos WC2026

## Technical Approach

Routers FastAPI por recurso (patrón `health.py`: `APIRouter` + `Depends(get_session)`),
montados con prefijo `/api/v1`. Todos `SELECT` puros desde Postgres (invariante: cero
llamadas externas en request). El helper "mejor cuota / última por bookmaker" se extrae de
`signals.py` a `app/model/odds_queries.py` (dirección `api → model`; el modelo NUNCA importa
de `api`). Standings = función pura determinista en `app/model/standings.py` (estilo `elo.py`).
Seed de grupos = script one-shot con union-find sobre el grafo de fixtures.

## Architecture Decisions

| Decisión | Elección | Rechazado | Rationale |
|----------|----------|-----------|-----------|
| Layout routers | `app/api/routers/{signals,matches,model,paper,groups}.py` | Todo en `signals.py` | 5 recursos en un archivo no escala; un router por recurso = cohesión. `health.py` queda donde está (sin churn). |
| Schemas | `app/api/schemas.py` único, Pydantic v2 `from_attributes`, sección por recurso | Schema-por-router | Superficie de import única; shapes chicas. |
| Helper best-odds | `app/model/odds_queries.py`, usado por `signals.py` Y la API | `app/api/queries.py` | `api → model` es la dirección sana; el modelo no puede depender de `api`. El motor ya es dueño de la query. |
| Standings | función pura en `app/model/standings.py` | Método en modelo SQLAlchemy / SQL window | Testeable sin BD, replica patrón `elo.py`; desempates FIFA en código puro. |
| CORS | `settings.cors_origins: list[str] = ["http://localhost:5173"]` + `CORSMiddleware` en `main.py` | Hardcode origins | Configurable por env; pydantic-settings parsea lista. |

## Query Design (anti N+1)

| Endpoint | Query | Forma |
|----------|-------|-------|
| `GET /signals` | `value_signal` JOIN `prediction` JOIN `match` JOIN home/away `team`, JOIN `odds` (FK `odds_id`). Filtros `match_date` ∈ [from,to], `edge >= min_edge`. `limit/offset`. | Lista plana de señales |
| `GET /matches/upcoming` | 1) `match` status=SCHEDULED ORDER BY `match_date,kickoff_at` (paginado); 2) UNA query `prediction` WHERE `match_id IN (...)` AND `MATCH_1X2`. Agrupar en Python. | `{home,draw,away}` anidado + `low_confidence` |
| `GET /matches/{id}` | `match`+teams; predicciones; odds `DISTINCT ON (bookmaker, outcome_code) ORDER BY captured_at DESC`; señales. 404 si no existe. | Detalle |
| `GET /groups` / `/groups/{name}` | grupos + `members` (selectinload) + matches del grupo (FINISHED+SCHEDULED). Standings al vuelo. 404 si letra no existe. | Tabla calculada |

**Paginación**: `limit` default 50, máx 200; `offset >= 0`. Caps validados en el schema de query.

## Group Seed Algorithm (`scripts/seed_groups.py`)

1. **Selección de fixtures**: competición `WORLD_CUP` season 2026, `status=SCHEDULED`,
   `stage IS NULL OR stage == GROUP` (idempotente tras backfill; los knockouts aún no existen).
2. **Componentes conexos**: union-find sobre aristas (home_team, away_team). Resultado esperado:
   exactamente **12 componentes de exactamente 4 equipos**.
3. **Aserción dura** ANTES de escribir: `len(comps)==12` y `all(len(c)==4)`. Falla ruidoso si no.
4. **Mapping letras A–L**: dict editable en el script, keyed por firma determinista
   (`tuple(sorted(team_names))` → letra). Imprime composición por letra para verificación del usuario.
5. **Escritura transaccional**: upsert `tournament_group` (12) + `group_team` (48); backfill
   `match.stage=GROUP` + `match.group_id` en los 72 fixtures. Idempotente (upsert por uniques).

## Standings Contract (`app/model/standings.py`)

```python
def compute_standings(
    members: list[TeamRef],            # team_id + name (fallback determinista)
    results: list[MatchResult],        # (home_id, away_id, home_score, away_score) FINISHED
) -> list[StandingRow]:                # ordenada: pos, pj, g, e, p, gf, gc, dg, pts
```

Desempates FIFA: (1) puntos → (2) DG → (3) GF → (4) **head-to-head** entre empatados →
(5) nombre. H2H = mini-standings restringida a partidos *entre los empatados*; helper
`_rank(subset, matches)` recursivo (maneja triples: si el subgrupo sigue empatado, cae a nombre).
Tarjetas/fair-play FUERA de alcance (no se ingestan). Puro, sin BD.

## Paper / ROI Semantics

| Estado | Mapeo `BetStatus` |
|--------|-------------------|
| open | `PENDING` |
| settled | `WON` / `LOST` |
| void | `VOID` (excluida de ROI) |

`ROI = (Σ returns − Σ staked) / Σ staked` sobre **settled** (WON/LOST). `returns = stake*odds_taken`
si WON, `0` si LOST (usa `pnl` si está, si no calcula). **0 settled → `roi: null` + counts**
(`open_count`, `settled_count=0`, `staked_total`). **Quién liquida las apuestas: FUERA de este
change** (un change futuro setea `status/pnl` tras ingestar resultados). El endpoint solo lee.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/api/routers/{signals,matches,model,paper,groups}.py` | Create | Routers por recurso |
| `app/api/schemas.py` | Create | Schemas Pydantic v2 `from_attributes` |
| `app/model/odds_queries.py` | Create | Helper best-odds / latest-por-bookmaker compartido |
| `app/model/standings.py` | Create | Tabla pura + desempates FIFA |
| `scripts/seed_groups.py` | Create | Union-find, mapping letras, seed + backfill `stage=GROUP` |
| `app/model/signals.py` | Modify | Usa `odds_queries` (sin duplicar lógica) |
| `app/main.py` | Modify | `include_router` (×5) + `CORSMiddleware` |
| `app/core/config.py` | Modify | `cors_origins: list[str]` |
| `tests/api/`, `tests/model/test_standings.py` | Create | Integración + unit numérico |

## Testing Strategy

| Layer | Qué | Cómo |
|-------|-----|------|
| Unit | `standings` (puntos, DG, GF, H2H 2-way y 3-way) | Escenarios numéricos sin BD |
| Integration | 5 endpoints + grupos, 404 vs lista vacía, paginación | `TestClient` + override `get_session` → `db_session` (SAVEPOINT) |
| Seed | 12×4 asserts, idempotencia, backfill stage | Datos en savepoint |

**Override pattern**: `app.dependency_overrides[get_session] = lambda: db_session` dentro de un
fixture `client(db_session)`; limpiar el override al finalizar.

## Migration / Rollout

Sin migración de esquema (aditivo). El seed es idempotente y reversible (truncar
`tournament_group`/`group_team` + `stage/group_id = NULL`). VPS: bind `127.0.0.1` + túnel SSH
(documentado, no implementado).

## Open Questions

- Ninguna que bloquee. (Cross-check letras vs `openfootball` queda diferido por proposal.)
