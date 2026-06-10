# Proposal: API REST de Señales (read-only)

## Intent

El Mundial arranca el 2026-06-11. Ya hay 216 predicciones, 69 señales PAPER y 5.8k
snapshots de odds en Postgres, pero NO hay forma de leerlos por HTTP. Esta API es el
unblocker del dashboard MVP (próximo change) y del deploy a VPS. Solo lectura,
servida 100% desde Postgres — ninguna llamada externa en el request (invariante sagrado).

## Scope

### In Scope
- Router `app/api/signals.py` (o por recurso) montado en `app.main`, prefijo `/api/v1`.
- Endpoints read-only:
  - `GET /api/v1/signals` — filtros `from`/`to`, `min_edge`, paginación `limit`/`offset`; join match+teams+outcome, `p_model`, mejor cuota+bookmaker, edge, ev, stake, captured_at.
  - `GET /api/v1/matches/upcoming` — fixtures SCHEDULED + predicciones H/D/A + `low_confidence` + `kickoff_at`.
  - `GET /api/v1/matches/{id}` — detalle: probabilidades, última cuota por bookmaker, señales. 404 si no existe.
  - `GET /api/v1/model` — versión activa, resumen de params + métricas de backtest y tabla de calibración (transparencia; expone, nunca inventa).
  - `GET /api/v1/paper` — tracking bet_log PAPER: abiertas, settled count, ROI cuando hay resultados.
- `app/api/schemas.py` — modelos de respuesta Pydantic v2 (`from_attributes`).
- CORS configurable: `localhost:5173` + origen extra vía `settings.cors_origins`.

### In Scope — Grupos WC2026 (amendment aprobado)
- **Seed de grupos** (`scripts/seed_groups.py`): poblar `tournament_group` (12) y `group_team`
  (48 membresías) derivando la composición desde la BD. Los 72 fixtures SCHEDULED de
  grupos definen los grupos por construcción: cada grupo es un componente conexo del grafo
  de fixtures (4 selecciones que comparten partidos entre sí). El script deriva los
  componentes; las **letras A–L NO son derivables** del grafo → mapping de letras explícito
  y editable dentro del script (verificable por el usuario contra el output). Cross-check
  con `openfootball/worldcup.json` queda FUERA (sin nueva ingesta externa en este change).
- **Backfill barato de `match.stage`**: durante el seed, los 72 partidos de grupos reciben
  `stage = GROUP` (hoy NULL — gap conocido) y se enlaza `match.group_id`. Detección de stage
  de knockouts se DIFIERE a un change futuro.
- **Cómputo de tablas (`app/model/standings.py`)**: función pura determinista estilo `elo.py`,
  sin estado, que calcula la tabla de un grupo desde los partidos FINISHED:
  Pts/PJ/G/E/P/GF/GC/DG. Desempates FIFA aplicados y documentados en este orden:
  (1) puntos → (2) diferencia de goles → (3) goles a favor → (4) head-to-head entre empatados.
  Fair-play/tarjetas **FUERA de alcance** (no se ingestan tarjetas — se nota explícito; el
  empate persistente queda como tal sin romper). Calculado **al vuelo** en cada request desde
  `match` (sin standings persistidos → se mantiene correcto a medida que entran resultados vía
  re-ingesta idempotente). `group_team` guarda **membresía**, no tablas.
- **Endpoints de grupos**:
  - `GET /api/v1/groups` — los 12 grupos con sus equipos + standings actuales.
  - `GET /api/v1/groups/{name}` — un grupo (letra): standings + sus fixtures con predicciones. 404 si no existe.
- **Fases futuras (documentado, casi gratis)**: los fixtures de knockout llegan vía re-ingesta
  martj42 (upsert idempotente ya existe); el predict runner genera sus probabilidades;
  `/matches/upcoming` y `/matches/{id}` los sirven automáticamente sin cambios.

### Out of Scope
- Dashboard/frontend (próximo change), SSE/streaming, agentes/LLM.
- Auth/login, write endpoints, customización de OpenAPI.
- Postura VPS: bind `127.0.0.1` + túnel SSH (sin auth en código). Documentar, no implementar.

## Capabilities

### New Capabilities
- `api-readonly`: contrato de los 5 endpoints read-only, shapes de respuesta, paginación, códigos de error (404 vs lista vacía), garantía de no-mutación y serve-from-DB.
- `group-standings`: derivación de los 12 grupos WC2026 desde el grafo de fixtures, mapping de letras A–L, backfill de `stage = GROUP`, función pura de cómputo de tablas con desempates FIFA documentados (puntos → DG → GF → head-to-head; fair-play fuera de alcance), y los 2 endpoints de grupos (`GET /api/v1/groups`, `GET /api/v1/groups/{name}`) calculados al vuelo desde `match`.

### Modified Capabilities
- None.

## Approach

Reutilizar el patrón router de `app/api/health.py` (APIRouter + `Depends(get_session)`).
Extraer el helper "mejor cuota / última por bookmaker" desde `app/model/signals.py`
(líneas 124-157) a un módulo de queries compartido para evitar N+1 y duplicación.
Joins explícitos con `selectinload`/`join`. Todos los endpoints son `SELECT` puros.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/api/*.py` | New | Routers por recurso (incl. `groups`) + schemas Pydantic |
| `app/model/standings.py` | New | Función pura: tabla de grupo + desempates FIFA (estilo `elo.py`) |
| `scripts/seed_groups.py` | New | Deriva 12 grupos del grafo de fixtures, mapping de letras, seed + backfill `stage=GROUP` |
| `app/main.py` | Modified | `include_router` + CORS middleware |
| `app/core/config.py` | Modified | `cors_origins` setting |
| `tests/api/` | New | TestClient + db_session fixtures |
| `tests/model/` | New | Escenarios numéricos de standings + desempates |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| N+1 en joins de señales/matches | Med | Helper de query compartido, eager loading |
| Exposición sin auth en VPS | Med | Bind 127.0.0.1 + túnel SSH; documentado |
| Drift de shapes con el front | Low | OpenAPI auto + Pydantic como contrato |
| Grupos mal derivados si el grafo de fixtures tiene errores | Med | Aserción dura: exactamente **12 componentes de exactamente 4 equipos**; fallar ruidoso si no |
| Mapping de letras A–L incorrecto | Low | Output verificable/editable por el usuario; el script imprime la composición por letra |

## Rollback Plan

Cambio aditivo: nuevos routers + ediciones menores. Rollback = revertir los commits;
sin migraciones. El seed toca datos (filas en `tournament_group`/`group_team` y backfill de
`match.stage`/`group_id`), pero es idempotente y reversible (truncar las dos tablas + setear
`stage`/`group_id` a NULL); no destruye resultados ni odds.

## Dependencies

- Datos ya en Postgres (predicciones, señales, odds, 72 fixtures de grupos). Ninguna externa nueva.
- Los endpoints `/groups` requieren correr `scripts/seed_groups.py` una vez (membresía + backfill).

## Success Criteria

- [ ] Los 5 endpoints responden desde Postgres, cero llamadas externas.
- [ ] `GET /api/v1/model` expone backtest + calibración reales.
- [ ] Seed deriva exactamente **12 grupos × 4 equipos** del grafo de fixtures; falla ruidoso si no.
- [ ] Los 72 partidos de grupos quedan con `stage = GROUP` y `group_id` enlazado.
- [ ] Cómputo de standings testeado con **escenarios numéricos** (puntos, DG, GF, head-to-head entre empatados).
- [ ] `GET /api/v1/groups` y `GET /api/v1/groups/{name}` responden con tablas calculadas al vuelo desde `match`.
- [ ] Tests con TestClient pasan en Docker; `ruff check` limpio.
- [ ] Dashboard MVP puede consumir la API sin cambios de backend.
