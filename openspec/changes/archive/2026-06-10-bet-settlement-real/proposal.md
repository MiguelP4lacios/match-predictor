# Proposal: Liquidación de apuestas + registro de apuestas REALES (BetPlay)

## Intent
El usuario empieza a apostar REAL en BetPlay (COP) mañana (apertura Mundial 2026-06-11). Hoy `bet_log` solo nace PAPER (units) desde señales y **nadie las liquida**: el ROI nunca se cierra. Falta (a) un motor determinista que liquide PENDING contra resultados FINISHED y (b) el primer endpoint de **escritura** para registrar apuestas reales con la cuota y stake REALES de BetPlay (que difieren del best-price). Invariante CLAUDE.md: "registro de cada apuesta para medir ROI y calibración". Determinista, sin LLM.

## Scope
### In Scope
- Motor `settle()` determinista, idempotente: PENDING + match FINISHED → WON/LOST, `pnl`, `settled_at`. Hook en `tournament_update.sh` (tras ingest) + CLI runner.
- Endpoints write: `POST /api/v1/bets` (registrar REAL), `GET /api/v1/bets?mode=`, `DELETE /api/v1/bets/{id}` (solo PENDING).
- Migración m6 (mínima) sobre `bet_log`.
- Página "Apuestas" (ex /paper): 2 bloques ROI (PAPER units / REAL COP), conteos por modo, lista de apuestas y form standalone de registro.

### Out of Scope
- Settlement O/U (hoy bet_log solo lleva 1X2); auth/users por apuesta; edición de settled; gestión de bankroll UI; conversión multi-moneda; VOID automático (cancelaciones = manual).

## Capabilities
### New Capabilities
- `bet-settlement`: función determinista que liquida `bet_log` PENDING contra `match` FINISHED (HOME/DRAW/AWAY por home_score vs away_score), idempotente, + CLI + paso en daily loop.
- `real-bets`: primer endpoint de escritura — alta/listado/borrado de apuestas REAL en `bet_log` con cuota y stake de BetPlay, link a señal opcional.

### Modified Capabilities
- `api-readonly`: R6 `/paper` evoluciona a ROI **por modo** (PAPER y REAL separados; monedas nunca se mezclan).
- `dashboard-frontend`: PaperPage → página "Apuestas" con form de registro y lista.
- `prod-deploy`: `tournament_update.sh` suma paso de settlement tras ingest.

## Approach
Settlement resuelve (match, outcome) por fila: REAL usa columnas directas `match_id`+`outcome_code`; PAPER traversa `value_signal→prediction`. WON si outcome == resultado; `pnl = stake×(odds_taken−1)` si WON, `−stake` si LOST. Solo toca status=PENDING → re-run no liquida dos veces. ROI por modo = `sum(pnl)/sum(stake)` sobre WON+LOST; settled=0 → null. POST valida match SCHEDULED/hoy, odds>1, stake>0.

## Affected Areas
| Area | Impact | Description |
|------|--------|-------------|
| `app/models/betting.py` + migración m6 | Modified | `value_signal_id` → nullable; +`match_id` (FK nullable), +`outcome_code` (str), +`settled_at` (dt), +`note` (str). `odds_taken`/`stake`/`pnl`/`status` ya existen. |
| `app/betting/settlement.py` (nuevo) + CLI | New | Motor + runner |
| `app/api/routers/bets.py` (nuevo) | New | POST/GET/DELETE |
| `app/api/routers/paper.py` | Modified | ROI por modo |
| `scripts/tournament_update.sh` | Modified | Paso settlement |
| `frontend/.../PaperPage.tsx` + componentes | Modified | Página Apuestas + form |

## Risks
| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Primer endpoint write sin validación → datos basura | Med | Validación estricta (match existe+SCHEDULED, odds>1, stake>0); detrás de Caddy basic auth ya existente |
| Mezclar COP con units en ROI | Med | Agregaciones separadas por modo; nunca SUM cross-mode |
| Settlement liquida mal por ET/penales | Low | 1X2 liquida sobre home_score vs away_score (FT); apertura es fase de grupos sin ET; nota en spec |
| Migración rompe filas PAPER existentes | Low | Aditiva; columnas nullable; backfill no requerido |

## Rollback Plan
Migración m6 es aditiva → `alembic downgrade -1`. Quitar paso settlement de `tournament_update.sh`. Endpoints en router nuevo → desregistrar `bets.py` del app. Front revierte a PaperPage previa. PAPER y datos existentes intactos.

## Dependencies
- `match.status=FINISHED` + scores poblados por ingest (ya existe en el daily loop).

## Success Criteria
- [ ] Re-correr settle no cambia nada ya liquidado (idempotente).
- [ ] Apuesta REAL registrada vía POST aparece PENDING y se liquida sola al FINISHED.
- [ ] `/paper` muestra ROI PAPER (units) y REAL (COP) separados; settled=0 → null.
- [ ] Apertura 2026-06-11: usuario registra su apuesta BetPlay con cuota/stake reales.
