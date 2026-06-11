# Tasks: Liquidación de apuestas + registro REAL (bet-settlement-real)

## Phase 1: Backend Base — m6 + SignalItem.match_id

- [x] 1.1 Create `migrations/versions/m6_bet_log_real_fields.py`: ALTER bet_log — value_signal_id DROP NOT NULL; ADD match_id FK(match nullable), outcome_code varchar nullable, settled_at timestamp nullable, note varchar nullable; ADD CHECK ck_bet_resolvable `(value_signal_id IS NOT NULL) OR (match_id IS NOT NULL AND outcome_code IS NOT NULL)`; down_revision="a1b2c3d4e5f6".
- [x] 1.2 Update `app/models/betting.py` BetLog in lockstep: value_signal_id nullable, +match_id/outcome_code/settled_at/note; add FK relationship to Match.
- [x] 1.3 pytest round-trip test `tests/models/test_bet_log_m6.py`: insert BetLog with match_id+outcome_code (no signal) → persists; insert with neither → ck_bet_resolvable fires IntegrityError.
- [x] 1.4 Update `app/api/schemas.py` SignalItem: add `match_id: int | None`.
- [x] 1.5 Update `app/api/routers/signals.py`: include `match_id` in signal query/response.
- [x] 1.6 pytest `tests/api/test_signals_match_id.py` (TestClient): GET /api/v1/signals items contain `match_id` field.

## Phase 2: Settle TDD

- [x] 2.1 RED — `tests/model/test_settle.py`: WON scenario (stake=12000, odds=1.40, HOME, 2-0 → pnl=+4800.00); LOST scenario (same bet, 1-1 → pnl=-12000.00, settled_result=DRAW); idempotence (re-run → 0 rows changed); SCHEDULED untouched; penales/knockout DRAW for 1X2; PAPER via value_signal_id→prediction path; commit-spy (assert session.commit called exactly once on settlement).
- [x] 2.2 GREEN — Create `app/model/settle.py`: `settle_bets(session) -> dict` — LEFT JOIN value_signal/prediction, COALESCE(bet.match_id, prediction.match_id) + COALESCE(bet.outcome_code, prediction.outcome_code); filter PENDING+FINISHED; derive HOME/DRAW/AWAY; set status/pnl/settled_result/settled_at; COMMIT in this function; return `{settled, won, lost}`.
- [x] 2.3 Create `app/model/run_settle.py`: CLI runner (`if __name__ == "__main__"`), call settle_bets, print `"Settled: N bets"`, exit 0; non-zero on exception. Module path: `python -m app.model.run_settle`.
- [x] 2.4 Modify `scripts/tournament_update.sh`: insert step 3 `python -m app.model.run_settle` after ingest, before elo; renumber to 6 steps; update log messages; add `[OK] tournament_update complete` footer.

## Phase 3: API Write TDD

- [x] 3.1 RED — `tests/api/test_bets.py` (TestClient): POST 201 (match_id=42 SCHEDULED, stake=12000, odds=1.40, outcome_code=HOME); POST 404 (match_id=9999); POST 422 (odds=0.90; stake=0; match FINISHED→422); GET ?mode=REAL → 3 items; GET ?mode=REAL&status=pending → 2 items; DELETE REAL PENDING → 204; DELETE WON → 409; DELETE PAPER → 400; DELETE 9999 → 404. GET /api/v1/paper: REAL staked=24000, returns=28800 → roi=0.20; REAL 0 settled → roi=null.
- [x] 3.2 Add to `app/api/schemas.py`: `BetCreate`, `BetItem`, `BetList`, `ModeStats`, `BetsPageStats`.
- [x] 3.3 GREEN — Create `app/api/routers/bets.py`: POST (validate match exists+SCHEDULED, odds>1, stake>0; INSERT mode=REAL status=PENDING); GET (filter by mode/status); DELETE (REAL PENDING only → 204; settled → 409; PAPER → 400).
- [x] 3.4 Modify `app/api/routers/paper.py`: add `mode` query param; aggregate PAPER and REAL separately; roi=null when settled=0 per mode.
- [x] 3.5 Modify `app/api/main.py`: `include_router(bets_router, prefix="/api/v1")`.

## Phase 4: Frontend TDD

- [x] 4.1 RED `frontend/src/api/client.test.ts`: POST with body sends Content-Type application/json; 422 → ApiError with fieldErrors (loc+msg parsed); 409 → ApiError with message.
- [x] 4.2 GREEN — Modify `frontend/src/api/client.ts`: extend fetchAPI to accept `{method, body}`; add ApiError class; normalize 422/409.
- [x] 4.3 RED `frontend/src/lib/formatters.test.ts`: formatCop(12000)→"$12.000"; formatPnl(4800)→"+$4.800"; formatPnl(-12000)→"−$12.000".
- [x] 4.4 GREEN — Modify `frontend/src/lib/formatters.ts`: add `formatCop` (es-CO, no decimals, manual `$` prefix) and `formatPnl`.
- [x] 4.5 Create `frontend/src/components/BetForm.tsx`: `<select>` of /matches/upcoming (SCHEDULED); outcome select with team names; cuota input (>1.01); stake COP input (>0); optional nota; prefill from `?match_id=&outcome=&odds=` → focus cuota; POST on submit; on 201 clear form + refresh; inline error on 422/409.
- [x] 4.6 Create `frontend/src/components/BetList.tsx`: rows by placed_at DESC; partido, outcome humanized, cuota, stake, status colored (pending=gray/won=green/lost=red), pnl with sign+color; Delete button only REAL PENDING → confirm dialog → DELETE /api/v1/bets/{id}.
- [x] 4.7 Create `frontend/src/pages/BetsPage.tsx`: fetch /paper (BetsPageStats) + /bets; render 2 ModeStatsBlock (PAPER / REAL COP with formatCop); render BetForm + BetList; handle empty/error states.
- [x] 4.8 Modify `frontend/src/components/SignalCard.tsx`: add secondary button "Registrar apuesta" → navigate `/apuestas?match_id={match_id}&outcome={outcome_code}&odds={best_odds}` (requires Signal.match_id from Phase 1).
- [x] 4.9 Modify `frontend/src/App.tsx`: add route `/apuestas` → BetsPage; add `<Navigate from="/paper" to="/apuestas" replace />`; rename nav item "Paper" → "Apuestas".
- [x] 4.10 vitest+RTL tests: BetForm prefills match+outcome from query params; BetForm shows inline error on 422; BetList delete button visible only for REAL PENDING; ModeStatsBlock roi=null→"—"; ModeStatsBlock roi=0.20→"+20.0%"; SignalCard "Registrar apuesta" navigates to correct URL.

## Phase 5: Cierre

- [x] 5.1 Run `pytest` full suite; fix failures; run `ruff check . && ruff format .`.
- [x] 5.2 Run `npm run test` (vitest); fix failures.
- [x] 5.3 VPS deploy: rsync + `docker compose -f docker-compose.prod.yml build api frontend` + `docker compose ... up -d`.
- [x] 5.4 Smoke settle on VPS: `docker compose ... run --rm api python -m app.model.run_settle` → `"Settled: 0 bets"`.
- [x] 5.5 Smoke POST REAL (curl with basic auth on public URL): POST apuesta → 201; GET lista → aparece; DELETE → 204.
- [x] 5.6 `git add` changed files; `git commit` (conventional) + `git push`.
- [x] 5.7 Save apply-progress to engram (topic_key `sdd/bet-settlement-real/apply-progress`).

---

## Batching for apply (2 agents)

| Agent | Phases | Focus |
|-------|--------|-------|
| Agent A (backend) | 1 → 2 → 3 → 5.1 partial | DB migration, settle engine, API write, ruff |
| Agent B (frontend) | 4 → 5.2 | fetchAPI, formatters, BetForm/BetList/BetsPage, SignalCard, routing, vitest |
| Agent A (cierre) | 5.3 → 5.7 | Deploy, smoke tests, commit, engram |

> Agent B can start Phase 4 independently once Phase 1.4–1.5 (SignalItem.match_id schema) is confirmed, since BetForm/SignalCard only need the type definition.
