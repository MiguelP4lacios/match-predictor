# Tasks: Cupón de Bloques (Parlay +EV estilo BetPlay)

## Phase 1: Backend Core — DB + Entidades + parlay.py

- [x] 1.1 `app/models/enums.py` — añadir `BetKind(SINGLE="single", PARLAY="parlay")` y `DataSource.KAMBI="kambi"`
- [x] 1.2 `app/models/types.py` — añadir `bet_kind_type` (PG enum nativo)
- [x] 1.3 `app/models/betting.py` — `BetLog.bet_kind` column + modelo `BetLeg` + relación `BetLog.legs`
- [x] 1.4 `migrations/versions/m7_parlay.py` — crea `bet_leg`, añade `bet_log.bet_kind DEFAULT single`, relaja `ck_bet_resolvable` a `bet_kind='parlay' OR <resolvable existente>`; revises `m6betlogreal`; `downgrade` limpio
- [x] 1.5 RED: `tests/model/test_parlay.py` — 4 escenarios verbatim: 3-leg (7.084/0.3194/+1.2627), 2-leg con leg −EV + `suggested_without_negatives`, empty → `ValueError`, 1-leg → `ValueError`
- [x] 1.6 GREEN: `app/model/parlay.py` — `Leg`, `LegDiagnosis`, `ParlayDiagnosis`, `combine_parlay()` con `Decimal` para odds, `float` para probs; docstring independencia
- [x] 1.7 Verificar m7 upgrade/downgrade en BD efímera Docker (`alembic upgrade head` + `downgrade -1`)

## Phase 2: Backend Service + API + Settle

- [x] 2.1 RED: `tests/model/test_parlay_service.py` — resuelve `p_model` desde `Prediction` activa; leg sin predicción → `p_model=None`
- [x] 2.2 GREEN: `app/model/parlay_service.py` — query `Prediction` por `match_id/outcome_code/model_version_id` activa → llama `combine_parlay`
- [x] 2.3 `app/api/schemas.py` — añadir `ParlayLegInput`, `ParlayPreviewRequest/Response`, `ParlayLegDiag`, `ParlayCreate`, `ParlayItem`
- [x] 2.4 RED: `tests/api/test_parlays.py` — preview 3 legs (`retorno=35420`), odds≤1→422, 1-leg→422, FINISHED→422; POST persist BetLog+legs 201; GET filtrado por mode
- [x] 2.5 GREEN: `app/api/routers/parlays.py` — `POST /parlays/preview`, `POST /parlays`, `GET /parlays`; validaciones SCHEDULED + ≥2 legs + odds>1 + stake>0
- [x] 2.6 `app/main.py` — registrar router parlays bajo `/api/v1`
- [x] 2.7 RED: `tests/model/test_settle_parlays.py` — WON todas (pnl+30420), 1 leg LOST (pnl−5000), leg PENDING→PENDING; test no-regresión simples intactos
- [x] 2.8 GREEN: `app/model/settle.py` — añadir `settle_parlays()`; `settle_bets` SIN TOCAR
- [x] 2.9 `app/model/run_settle.py` + wirings en `tournament_update` — invocar `settle_parlays()` junto a `settle_bets()`

## Phase 3: Kambi Adapter (flag-gated)

- [x] 3.1 `tests/fixtures/kambi_sample.json` — fixture con `event.id=123`, 3 outcomes (odds milli: 1400/3200/2100), `participant="USA"` para override
- [x] 3.2 RED: `tests/ingestion/test_kambi.py` — fixture→3 `RawOdds` (price=1.40/3.20/2.10), milli 1700→1.70, `"USA"`→`"United States"`, `KAMBI_ENABLED=false`→source no instanciado; NUNCA live
- [x] 3.3 GREEN: `app/ingestion/sources/kambi.py` — `KambiOddsSource` con `_KAMBI_NAME_OVERRIDES` (6 entradas mínimo), milli/1000, filter Full Time + Open, `lang=en_US`; docstring fragilidad 429
- [x] 3.4 `app/core/config.py` — `kambi_enabled=false`, `kambi_operator`, `kambi_base_url`
- [x] 3.5 `app/scheduler/jobs.py` — `make_kambi_source()` gated; NO añadir al loop existente

## Phase 4: Frontend

- [ ] 4.1 `frontend/src/api/types.ts` — añadir `ParlayLegInput`, `LegDiagnostic`, `ParlayPreview`, `ParlayItem`
- [ ] 4.2 `frontend/src/api/parlays.ts` — wrappers `previewParlay()`, `createParlay()`, `fetchParlays()` sobre `fetchAPI`
- [ ] 4.3 RED: `tests/context/CuponContext.test.tsx` — `addLeg/removeLeg/clear`, persistencia `sessionStorage`, sin duplicados
- [ ] 4.4 GREEN: `frontend/src/context/CuponContext.tsx` — Provider `addLeg/removeLeg/clear`, `sessionStorage`
- [ ] 4.5 RED: `tests/components/CuponDrawer.test.tsx` — EV live (7.084/31.9%/+126.3%), warning leg −EV, retorno 35.420 COP, "Registrar cupón" POST+limpia, botón deshabilitado sin legs
- [ ] 4.6 GREEN: `frontend/src/components/CuponDrawer.tsx` + `CuponLegRow.tsx` — preview debounced ≥300ms, inputs odds + stake COP, banner independencia, "Registrar cupón"
- [ ] 4.7 RED: `tests/components/AddToCuponButton.test.tsx` — desde SignalCard añade leg; desde MatchesPage añade leg
- [ ] 4.8 GREEN: `frontend/src/components/AddToCuponButton.tsx` — botón reutilizable; `SignalCard.tsx` y `pages/MatchesPage.tsx` lo montan
- [ ] 4.9 `frontend/src/App.tsx` — montar `CuponContext` Provider + `CuponDrawer`

## Phase 5: Cierre

- [ ] 5.1 `pytest` full suite Docker — verde; `ruff check . && ruff format .` limpio
- [ ] 5.2 `npm run build` (o `vite build`) — sin errores TS
- [ ] 5.3 Deploy VPS — `rsync` + `docker compose up -d`; m7 corre al levantar
- [ ] 5.4 Smoke real — preview parlay 2 partidos SCHEDULED vía URL pública (auth `miguel:2lYdO0TmxfHTSi4oXl+a`): math correcta; `settle_parlays` con 0 pendientes
- [ ] 5.5 Commits convencionales + `git push`; `mem_save` apply-progress en engram
