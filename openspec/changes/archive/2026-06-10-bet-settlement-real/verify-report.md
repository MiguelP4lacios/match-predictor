# Verification Report

**Change**: bet-settlement-real
**Version**: specs v1 (5 spec files)
**Mode**: Strict TDD (test runner: `docker compose run --rm api pytest`)
**Verified**: 2026-06-10

---

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 26 |
| Tasks complete | 26 |
| Tasks incomplete | 0 |

All 26 tasks across Phases 1–5 are marked [x].

---

### Build & Tests Execution

**Backend — pytest**: ✅ 167 passed, 0 failed, 1 warning (httpx deprecation — cosmetic)
```
167 passed, 1 warning in 2.03s
```

**Backend — ruff**: ✅ All checks passed

**Frontend — vitest**: ✅ 125 passed, 0 failed (21 test files)
```
Tests  125 passed (125)
Duration  3.89s
```

**Frontend — build (tsc + vite)**: ✅ Clean build, no type errors
```
✓ built in 932ms
dist/assets/index-BSSEiOU2.js   234.84 kB │ gzip: 73.51 kB
```

**Coverage**: Not configured — skipped.

---

### Spec Compliance Matrix

#### real-bets spec

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| POST /bets | Registro exitoso 201 | `test_bets.py > test_post_bet_real_201` | ✅ COMPLIANT |
| POST /bets | Match no existe 404 | `test_bets.py > test_post_bet_404_match_not_found` | ✅ COMPLIANT |
| POST /bets | Match FINISHED 422 | `test_bets.py > test_post_bet_422_match_finished` | ✅ COMPLIANT |
| POST /bets | Odds inválidas 422 | `test_bets.py > test_post_bet_422_invalid_odds` | ✅ COMPLIANT |
| POST /bets | Stake cero 422 | `test_bets.py > test_post_bet_422_zero_stake` | ✅ COMPLIANT |
| POST /bets | Con signal — link preservado | (no test específico para value_signal_id) | ⚠️ PARTIAL |
| GET /bets | Filtrado por modo | `test_bets.py > test_get_bets_filter_mode_real` | ✅ COMPLIANT |
| GET /bets | Filtrado combinado mode+status | `test_bets.py > test_get_bets_filter_mode_and_status` | ✅ COMPLIANT |
| GET /bets | Sin filtros — todas | (no test explícito para 0 filtros) | ⚠️ PARTIAL |
| DELETE /bets/{id} | Borrado exitoso 204 | `test_bets.py > test_delete_real_pending_204` | ✅ COMPLIANT |
| DELETE /bets/{id} | Apuesta liquidada 409 | `test_bets.py > test_delete_won_409` | ✅ COMPLIANT |
| DELETE /bets/{id} | Apuesta PAPER 400 | `test_bets.py > test_delete_paper_400` | ✅ COMPLIANT |
| DELETE /bets/{id} | No existe 404 | `test_bets.py > test_delete_nonexistent_404` | ✅ COMPLIANT |

#### bet-settlement spec

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Settle Engine | WON numérico +4800.00 | `test_settle.py > test_settle_won_numeric` | ✅ COMPLIANT |
| Settle Engine | LOST numérico -12000.00 | `test_settle.py > test_settle_lost_numeric` | ✅ COMPLIANT |
| Settle Engine | Idempotencia re-run 0 filas | `test_settle.py > test_settle_idempotent` | ✅ COMPLIANT |
| Settle Engine | SCHEDULED intacto | `test_settle.py > test_settle_scheduled_match_untouched` | ✅ COMPLIANT |
| Settle Engine | Penales DRAW para 1X2 | `test_settle.py > test_settle_penalties_is_draw_for_1x2` | ✅ COMPLIANT |
| Settle Engine | PAPER vía signal→prediction | `test_settle.py > test_settle_paper_via_signal_prediction` | ✅ COMPLIANT |
| Settle Engine | commit-spy exactamente 1 vez | `test_settle.py > test_settle_commits_exactly_once` | ✅ COMPLIANT |
| CLI Standalone | Ejecución imprime conteo | VPS smoke: "Settled: 0 bets" exit 0 | ⚠️ PARTIAL (no unit test del runner) |
| CLI Standalone | Sin nada que liquidar | VPS smoke confirmed | ⚠️ PARTIAL (no unit test del runner) |

#### api-readonly spec (R6)

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| GET /paper per-mode | ROI REAL negativo -0.30 | `test_bets.py > test_paper_real_roi_positive` | ✅ COMPLIANT |
| GET /paper per-mode | ROI REAL positivo 0.20 | `test_bets.py > test_paper_real_roi_0_20` | ✅ COMPLIANT |
| GET /paper per-mode | REAL sin settled → roi null | `test_bets.py > test_paper_real_roi_null_no_settled` | ✅ COMPLIANT |
| GET /paper per-mode | PAPER con datos REAL vacío | (implícito en todos los tests de /paper) | ⚠️ PARTIAL |
| GET /paper per-mode | Modos nunca mezclados | (implícito en separación de funciones) | ⚠️ PARTIAL |

#### dashboard-frontend spec

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| R1 Routing | /paper redirige a /apuestas | `routing.test.tsx` | ✅ COMPLIANT |
| R1 Routing | Ruta desconocida → 404 | `routing.test.tsx` | ✅ COMPLIANT |
| R6 Vista Apuestas | ROI REAL 0.20 → "+20.0%" | `BetsPage.test.tsx > ModeStatsBlock REAL: roi=0.20` | ✅ COMPLIANT |
| R6 Vista Apuestas | ROI null → "—" honestidad | `BetsPage.test.tsx > ModeStatsBlock REAL: roi=null` | ✅ COMPLIANT |
| R6 Vista Apuestas | Borrar con confirmación | `BetList.test.tsx > DELETE llamado al confirmar` | ⚠️ PARTIAL (test pasa; botón roto en prod — ver CRITICAL #2) |
| R6A Formulario | Registro exitoso | `BetForm.test.tsx` | ✅ COMPLIANT |
| R6A Formulario | Pre-carga query params | `BetForm.test.tsx` | ✅ COMPLIANT |
| R6A Formulario | Error validación inline 422 | `BetForm.test.tsx` | ✅ COMPLIANT |
| R2B SignalCard | Registrar navega con prefill | `SignalCard.test.tsx` | ✅ COMPLIANT |
| R7 TypeScript Types | ModeStats / BetsPageStats / BetItem | `types.ts` definidos | ✅ COMPLIANT |

#### prod-deploy spec

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| tournament_update.sh | Settle tras ingest (paso 3) | Script revisado + bash -n ✅ | ✅ COMPLIANT |
| tournament_update.sh | Abort on step failure (set -e) | Script: `set -euo pipefail` | ✅ COMPLIANT |
| tournament_update.sh | Skip odds --skip-odds | Script: flag presente | ✅ COMPLIANT |
| tournament_update.sh | 6 pasos numerados | Script: [1/6] a [6/6] | ✅ COMPLIANT |
| tournament_update.sh | [OK] footer | Script: `[OK] tournament_update complete` | ✅ COMPLIANT |

**Compliance summary**: 34/40 scenarios compliant (4 PARTIAL sin bloqueo, 2 PARTIAL con bugs prod)

---

### Settlement Math Audit (by-hand)

**WON numérico**: `stake=Decimal('12000.00')`, `odds_taken=1.40` (float)
- `odds_taken - 1 = 0.4` (exacto en IEEE 754)
- `Decimal(str(0.4)) = Decimal('0.4')`
- `Decimal('12000.00') * Decimal('0.4') = Decimal('4800.0')`
- `.quantize(Decimal("0.01")) = Decimal('4800.00')` ✅

**LOST numérico**: `(-Decimal('12000.00')).quantize(Decimal("0.01")) = Decimal('-12000.00')` ✅

**pnl column type**: `Numeric(14, 2)` — 2 decimal places, matches ✅

**Idempotencia**: filtro `WHERE status=PENDING` — re-run no toca WON/LOST ✅ (test pasa)

**Ruta PAPER**: LEFT JOIN via value_signal→prediction con COALESCE lógico ✅

**Penales/DRAW**: `home_score == away_score → DRAW` independiente de quién avanzó ✅

---

### Correctness (Static — Structural Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| m6 migration — columnas + CHECK | ✅ Implemented | `m6_bet_log_real_fields.py` — DDL aditiva, ck_bet_resolvable, downgrade limpio |
| BetLog lockstep update | ✅ Implemented | `app/models/betting.py` — todos los campos |
| settle_bets() — dos rutas | ✅ Implemented | REAL directo + PAPER via signal→prediction con COALESCE |
| run_settle.py CLI | ✅ Implemented | `app/model/run_settle.py` — print + sys.exit(1) en excepción |
| POST /bets validaciones | ✅ Implemented | match existe, SCHEDULED, odds>1, stake>0 |
| GET /bets filtros | ✅ Implemented | mode + status, nullslast ordering |
| DELETE /bets/{id} guards | ✅ Implemented | REAL PENDING → 204; settled → 409; PAPER → 400 |
| /paper per-mode ROI | ✅ Implemented | NUNCA mezcla modos; roi null si settled=0 |
| fetchAPI write-capable + ApiError | ✅ Implemented | 422/409 normalization, retrocompatible |
| formatCop / formatPnl | ✅ Implemented | determinista, sin Intl.NumberFormat |
| BetForm prefill + submit | ✅ Implemented | query params, focus cuota, 422 inline |
| BetList delete REAL PENDING | ⚠️ Partial | código presente PERO comparación case-sensitive rota en prod (ver CRITICAL #2) |
| BetsPage /bets fetch | ⚠️ Partial | fetchAPI presente PERO espera shape {items,total} y API retorna array plano (ver CRITICAL #1) |
| SignalCard Registrar | ✅ Implemented | navega con match_id+outcome_code+odds |
| App.tsx /apuestas + /paper redirect | ✅ Implemented | Navigate replace + nav "Apuestas" |
| tournament_update.sh 6 pasos | ✅ Implemented | settle en paso 3, set -euo pipefail |

---

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| m6 aditiva (no tabla separada) | ✅ Yes | |
| settle_bets commitea en su frontera | ✅ Yes | commit al final, test commit-spy pasa |
| Router bets.py thin CRUD (sin lógica de dominio) | ✅ Yes | INSERT puro, sin cálculo de pnl |
| fetchAPI write-capable retrocompatible | ✅ Yes | opts?: RequestInit |
| Ruta CLI: `app/model/run_settle.py` | ✅ Yes (design) | ⚠️ spec dice `app.betting.settle` — spec desincronizada |
| LLM nunca calcula pnl/ROI | ✅ Yes | invariante intacto; front solo formatea |
| ROI por modo en /paper | ✅ Yes | modos nunca mezclados en SQL |

---

### Issues Found

**CRITICAL** (must fix before archive):

1. **BetsPage: shape mismatch entre API y consumidor**
   - `GET /api/v1/bets` retorna `BetItem[]` (array plano — confirmado en VPS: `[{"id":257,"mode":"paper",...}]`)
   - `BetsPage.tsx` hace `useQuery<BetList>` y accede `betList?.items ?? []`
   - `BetList` TS type es `{ items: BetItem[], total: number }` — en producción `betList?.items` es `undefined`, siempre `[]`
   - **Impacto**: la lista de apuestas en `/apuestas` siempre muestra "No hay apuestas registradas" aunque existan 123 bets en el VPS
   - **Evidencia**: `frontend/src/pages/BetsPage.tsx:78-80` + curl VPS confirma array plano
   - **Fix**: cambiar `queryFn: () => fetchAPI<BetItem[]>('/v1/bets')` y `bets={betList ?? []}`, ó hacer que el endpoint retorne `{ items, total }` con `response_model=BetList`
   - **Por qué el test no lo atrapó**: el mock retorna `{ items: [], total: 0 }` — shape incorrecto que coincide con la expectativa del frontend pero no con la API real

2. **BetList: comparación case-sensitive mode/status rota en producción**
   - `BetList.tsx:70` → `const canDelete = bet.mode === 'REAL' && bet.status === 'PENDING'`
   - `StatusBadge` usa keys `PENDING / WON / LOST` (mayúsculas)
   - API retorna `BetMode.REAL = "real"` y `BetStatus.PENDING = "pending"` (StrEnum, minúsculas — confirmado en `enums.py` y en `test_bets.py` assertions `assert body["mode"] == "real"`)
   - **Impacto**: botón "Eliminar" NUNCA aparece en producción; badges de estado siempre usan el fallback (sin colores)
   - **Evidencia**: `app/models/enums.py:57-66` + `tests/api/test_bets.py:149-150`
   - **Fix**: comparar en minúsculas (`bet.mode === 'real' && bet.status === 'pending'`) y actualizar el map de StatusBadge a minúsculas, o normalizar al crear el objeto
   - **Por qué el test no lo atrapó**: `makeBet()` usa `mode: 'REAL'`, `status: 'PENDING'` — fixture en mayúsculas coincide con la guard pero no con la API real

**WARNING** (should fix):

3. **Spec bet-settlement.md desincronizada — módulo CLI incorrecto**
   - `specs/bet-settlement/spec.md` dice `python -m app.betting.settle`
   - Implementación real: `python -m app.model.run_settle` (per design.md y tasks.md)
   - `app/betting/` no existe; el módulo no es invocable con la ruta del spec
   - No afecta el runtime (tournament_update.sh usa la ruta correcta), pero sí la documentación

4. **BetCreate.odds_taken: spec dice > 1.01, impl usa > 1**
   - `specs/real-bets/spec.md`: "MUST ser > 1.01"
   - `app/api/schemas.py:149`: `Annotated[float, Field(gt=1)]` → acepta 1.001–1.01
   - `design.md` ya decía `gt=1`, así que la implementación sigue el diseño; el spec está desincronizado

**SUGGESTION** (nice to have):

5. **Sin límite máximo de stake** — un valor de `1e12` se acepta sin 422. Riesgo bajo para herramienta interna, pero añadir `Field(gt=0, le=1_000_000_000)` sería prudente.

6. **`BetItem` type en types.ts** declara `mode: 'REAL' | 'PAPER' | string` (mayúsculas). Debería ser `'real' | 'paper' | string` para reflejar los valores reales de la API y evitar confusión con el CRITICAL #2.

---

### Verdict

❌ **FAIL**

El backend y la lógica de liquidación están correctos y completos (167/167 tests pasan, ruff clean, settlement math auditado por mano). Sin embargo, la capa UI tiene **dos bugs críticos de producción** ocultos por fixtures de test incorrectos: (1) la lista de apuestas es siempre vacía en `/apuestas` por un mismatch de shape API↔frontend, y (2) el botón "Eliminar" y los badges de estado nunca funcionan correctamente por una comparación case-sensitive que no coincide con los valores reales de la API. Ambos bugs hacen que la feature de registro y visualización de apuestas REALES sea completamente no funcional en producción a pesar de que los tests pasan.

**Blocker mínimo para re-verificar**: corregir `BetsPage.tsx` (array plano) y `BetList.tsx` (comparaciones en minúsculas) + actualizar los mocks/fixtures correspondientes para que reflejen valores reales de la API.

---

## Fixes post-verify

**Fecha**: 2026-06-10 | **Commits**: `58e8eab`, `3887348`

### RED evidence (mocks honestos → tests fallan)

Se actualizaron los fixtures ANTES de corregir los componentes, reproduciendo los bugs en CI:

- `BetList.test.tsx`: `makeBet()` cambiado a `mode: 'real'`, `status: 'pending'`/`'won'`/`'lost'`.  
  → 5 tests fallaron: badges mostraban fallback (texto literal `'pending'` en vez de `'PENDIENTE'`), botón Eliminar ausente para REAL PENDING, DELETE no llamado.
- `BetsPage.test.tsx`: mock de `/v1/bets` cambiado a `[]` (array plano) + test nuevo `"muestra apuestas desde array plano"` con `[exampleBet]`.  
  → 1 test falló: `screen.getByText('Partido #42')` no encontrado porque `betList?.items` es `undefined` sobre un array.

**Total RED**: 6 tests fallando (5 BetList + 1 BetsPage).

### GREEN fixes aplicados

| Archivo | Cambio |
|---------|--------|
| `frontend/src/components/BetList.tsx` | `canDelete`: `'REAL'`→`'real'`, `'PENDING'`→`'pending'`; StatusBadge map keys a minúscula; añadido `void` |
| `frontend/src/pages/BetsPage.tsx` | `useQuery<BetList>` → `useQuery<BetItem[]>`; `betList?.items ?? []` → `betList ?? []`; import actualizado |
| `frontend/src/api/types.ts` | `BetItem.mode`: `'REAL'\|'PAPER'` → `'real'\|'paper'`; `BetItem.status`: `'PENDING'\|'WON'\|'LOST'` → `'pending'\|'won'\|'lost'\|'void'`; interfaz `BetList` eliminada |
| `frontend/src/pages/PaperPage.test.tsx` | Mock `/v1/bets` corregido a `[]` (también tenía la mentira) |
| `openspec/changes/bet-settlement-real/specs/bet-settlement/spec.md` | CLI `app.betting.settle` → `app.model.run_settle` |
| `openspec/changes/bet-settlement-real/specs/real-bets/spec.md` | `odds_taken > 1.01` → `> 1` |

### Test results post-fix

- **Frontend (vitest)**: ✅ 126 passed (126) — 21 test files, build limpio
- **Backend (pytest)**: ✅ 167 passed (167) — sin tocar

### Live proof

```
curl -s -u "miguel:****" "https://162-243-163-165.nip.io/api/v1/bets?mode=PAPER" | head -c 200
[{"id":257,"mode":"paper","status":"pending","match_id":null,"outcome_code":null,"odds_taken":6.5,"stake":"23.55",...
```

Array plano retornado con enums en minúscula (`"mode":"paper"`). Página HTML: HTTP 200.

### Verdict post-fix

✅ **PASS** — Todos los blockers resueltos. Los mocks ahora reflejan el contrato real de la API.
