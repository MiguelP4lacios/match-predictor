# Design: Liquidación de apuestas + registro de apuestas REALES

## Technical Approach

Tres piezas deterministas + UI, sin tocar el LLM:
1. **Migración m6** (aditiva) que vuelve `bet_log` capaz de representar una apuesta REAL autónoma (sin señal) y guardar el resultado de liquidación.
2. **Motor `settle_bets`** (`app/model/settle.py`) que liquida PENDING contra `match` FINISHED, idempotente, **commitea en su frontera** (lección del rollback silencioso de hoy), con runner `run_settle.py` estilo `run_elo`.
3. **Router de escritura** `bets.py` (primer endpoint write) + evolución de `/paper` a ROI por modo, + página "Apuestas" con form de registro.

Invariantes respetados: pnl/ROI siempre del servidor (front no hace aritmética, solo formatea); la matemática de liquidación vive en `app/model`; el alta es CRUD puro en el router.

## Architecture Decisions

### m6 — forma de la migración
| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Columnas nullable + CHECK de resolubilidad | Aditiva, no rompe PAPER, fuerza integridad | ✅ |
| Tabla `real_bet` separada | Duplica ROI/settle, rompe "un solo registro" | ❌ |

`value_signal_id` → DROP NOT NULL; ADD `match_id` (FK `match`, nullable), `outcome_code` (varchar nullable), `settled_at` (timestamp nullable), `note` (varchar nullable). CHECK `ck_bet_resolvable`: `(value_signal_id IS NOT NULL) OR (match_id IS NOT NULL AND outcome_code IS NOT NULL)` — toda apuesta debe ser liquidable por uno de los dos caminos. `revision="m6...", down_revision="a1b2c3d4e5f6"` (head actual). Entidad `BetLog` actualizada en lockstep.

### Resolución (match, outcome) en settle
| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| LEFT JOIN value_signal→prediction + JOIN match con COALESCE | 1 round-trip, sin N+1, DRY | ✅ |
| UNION de dos ramas (REAL directo / PAPER traversado) | Duplica lógica de derivación | ❌ |

`match_id_resolved = COALESCE(bet.match_id, prediction.match_id)`; `outcome_resolved = COALESCE(bet.outcome_code, prediction.outcome_code)`. Filtro `bet.status=PENDING AND match.status=FINISHED` → **idempotente** (re-run no toca lo liquidado). Derivación: `result = HOME/DRAW/AWAY` por `home_score vs away_score`; `WON` si `outcome_resolved == result`; `pnl = stake*(odds_taken-1)` si WON, `-stake` si LOST. Setea `status`, `settled_result=result`, `settled_at=now`. **`settle_bets(session)` commitea al final** y devuelve `{settled, won, lost}`.

### Dirección API→model en el POST
| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Router hace el INSERT directo (thin CRUD) | El alta no tiene matemática de dominio | ✅ |
| Writer en `app/model` | Indirección sin lógica que justifique | ❌ |

El alta es persistencia pura: ningún cálculo de pnl/edge ocurre ahí. La **matemática de liquidación permanece en `app/model/settle.py`**. Invariante intacto.

### fetchAPI write-capable
GET-only hoy → extender a `fetchAPI(path, {method, body})` retrocompatible: si `body` presente, `JSON.stringify` + header `Content-Type: application/json`. Normalización: lanzar `ApiError {status, fieldErrors?, message}`; en 422 parsear `detail:[{loc,msg}]` → `fieldErrors`; en 409 mensaje plano. GET sin opts no cambia comportamiento.

## Data Flow

    POST /bets ─→ bets.py (valida match SCHEDULED, odds>1, stake>0) ─→ INSERT bet_log (REAL, PENDING)
                                                                              │
    tournament_update.sh: ingest ─→ run_settle ─→ settle_bets(session) ──────┤ (match FINISHED)
                                                       │ COALESCE(direct, signal→prediction)
                                                       └─→ UPDATE status/pnl/settled_at + COMMIT
    GET /paper?mode= ─→ ROI por modo ─→ Apuestas page (formatCop, pnl coloreado)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `migrations/versions/m6_*.py` | Create | DDL aditiva + `ck_bet_resolvable` |
| `app/models/betting.py` | Modify | `value_signal_id` nullable; +`match_id/outcome_code/settled_at/note` |
| `app/model/settle.py` | Create | `settle_bets(session)` — query + derivación + commit |
| `app/model/run_settle.py` | Create | Runner CLI estilo `run_elo` |
| `scripts/tournament_update.sh` | Modify | Paso settlement **justo tras ingest** (renumerar [x/6]) |
| `app/api/routers/bets.py` | Create | POST/GET/DELETE |
| `app/api/routers/paper.py` | Modify | `mode` query param → ROI por modo |
| `app/api/schemas.py` | Modify | `BetCreate`, `BetItem`, `BetList`; `SignalItem` +`match_id` |
| `app/api/routers/signals.py` | Modify | exponer `match_id` (prefill contract) |
| `app/api/main.py` | Modify | `include_router(bets_router)` |
| `frontend/src/api/client.ts` | Modify | write-capable + `ApiError` |
| `frontend/src/lib/formatters.ts` | Modify | `formatCop`, `formatPnlCop` |
| `frontend/src/pages/PaperPage.tsx` → Apuestas | Modify | 2 StatsBlock + BetForm + BetList |
| `frontend/src/components/Bet{Form,List}.tsx` | Create | Form (dropdown /matches/upcoming) + lista por modo |
| `frontend/src/components/SignalCard.tsx` | Modify | botón "Registrar" → `/apuestas?match_id=&outcome=&odds=` |
| `frontend/src/App.tsx` | Modify | ruta `/apuestas`, nav "Apuestas" |

## Interfaces / Contracts

```python
class BetCreate(BaseModel):  # 201/404/422/409
    match_id: int
    outcome_code: Literal["HOME","DRAW","AWAY"]
    odds: Annotated[float, Field(gt=1)]
    stake: Annotated[Decimal, Field(gt=0)]
    mode: BetMode = BetMode.REAL
    value_signal_id: int | None = None
    note: str | None = None
```
- `POST /api/v1/bets`: 201 creado · 404 match inexistente · 422 validación · 409 match no SCHEDULED (LIVE/FINISHED).
- `DELETE /api/v1/bets/{id}`: 204 si PENDING+REAL · 404 inexistente · 409 si liquidada o PAPER.
- `GET /api/v1/bets?mode=`: lista `BetItem` (match, outcome, stake, odds, status, pnl, settled_result).
- **Prefill**: `/apuestas?match_id=<int>&outcome=<HOME|DRAW|AWAY>&odds=<decimal>` (de SignalCard).
- `formatCop(12000) → "$12.000"` (es-CO, sin decimales, prefijo `$` manual).

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Derivación HOME/DRAW/AWAY, pnl WON/LOST, idempotencia (2º run no cambia), PAPER vs REAL path | pytest sobre `settle_bets` con fixtures |
| Unit (regresión) | **commit-spy**: `settle_bets` commitea (bug de hoy) | spy sobre `session.commit` |
| Integration | POST → PENDING → settle → WON/LOST end-to-end; 404/422/409; DELETE sólo PENDING+REAL | FastAPI `TestClient` |
| Front | submit → POST llamado con body correcto; 422 renderiza field errors; 409 banner | vitest + RTL |
| Front | `formatCop`, `formatPnlCop` (positivo/negativo/null) | vitest |

## Migration / Rollout

m6 aditiva → `alembic downgrade -1` segura (PAPER intacto, sin backfill). Quitar paso settlement de `tournament_update.sh` y desregistrar `bets_router` revierte el resto. Front vuelve a PaperPage previa.

## Open Questions

- [ ] `SignalItem` hoy NO trae `match_id`; el contrato de prefill lo exige → agregarlo al schema + router de señales (cambio aditivo de lectura). Confirmar en sdd-tasks.
- [ ] ROI REAL es COP y PAPER es units: misma forma `PaperStats`, la moneda la decide el front por modo (no mezclar SUM cross-mode).
