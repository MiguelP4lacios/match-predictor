# Real Bets Specification

## Purpose

Endpoints de escritura para registrar, listar y borrar apuestas REAL en `bet_log`
con la cuota y stake reales de BetPlay (COP). Primer endpoint write del sistema.
Sin LLM. Las apuestas PAPER las crea el sistema automáticamente.

---

## Requirements

### Requirement: POST /api/v1/bets — Registrar Apuesta REAL

MUST crear una fila `bet_log` con `mode=REAL`, `status=PENDING`, `placed_at=now()`.
MUST validar el body antes de persistir.

| Campo | Tipo | Validación |
|-------|------|-----------|
| `match_id` | int | MUST existir en `match`; MUST tener `status=SCHEDULED` |
| `outcome_code` | str | MUST ser `HOME`, `DRAW`, o `AWAY` (case-insensitive) |
| `odds_taken` | float | MUST ser > 1 |
| `stake` | float/Decimal | MUST ser > 0 (COP) |
| `note` | str? | Opcional; se almacena en `bet_log.note` |
| `value_signal_id` | int? | FK nullable; si provisto, MUST existir en `value_signal` |

Response: HTTP 201 con el objeto `BetLog` creado.

#### Scenario: Registro exitoso — verificación numérica

- GIVEN `match_id=42` existe con `status=SCHEDULED`; body: `outcome_code=HOME`,
  `odds_taken=1.40`, `stake=12000`
- WHEN `POST /api/v1/bets`
- THEN HTTP 201; body contiene `id` (int), `mode=real`, `status=pending`,
  `odds_taken=1.40`, `stake=12000.00`, `pnl=null`, `placed_at` (datetime)

#### Scenario: Match no existe — 404

- GIVEN `match_id=9999` no existe en `match`
- WHEN `POST /api/v1/bets`
- THEN HTTP 404, `{"detail": "Match not found"}`

#### Scenario: Match ya terminado — 422

- GIVEN `match_id=10` existe con `status=FINISHED`
- WHEN `POST /api/v1/bets` con ese `match_id`
- THEN HTTP 422; detalle indica que el partido no está en estado SCHEDULED

#### Scenario: Odds inválidas — 422

- GIVEN body con `odds_taken=0.90`
- WHEN `POST /api/v1/bets`
- THEN HTTP 422

#### Scenario: Stake cero — 422

- GIVEN body con `stake=0`
- WHEN `POST /api/v1/bets`
- THEN HTTP 422

#### Scenario: Con signal — link preservado

- GIVEN `value_signal_id=3` existe; body válido
- WHEN `POST /api/v1/bets`
- THEN HTTP 201; `value_signal_id=3` en la respuesta

---

### Requirement: GET /api/v1/bets — Listar Apuestas

MUST retornar array de apuestas. Query params opcionales:
`mode` (`REAL`|`PAPER`), `status` (`pending`|`won`|`lost`|`void`).
Sin filtros → retorna todas. MUST NOT mezclar aggregados: cada ítem es una fila.

Campos por ítem: `id`, `mode`, `status`, `match_id`, `outcome_code`, `odds_taken`,
`stake`, `pnl`, `settled_result`, `settled_at`, `placed_at`, `note`,
`value_signal_id`.

#### Scenario: Filtrado por modo

- GIVEN existen 3 apuestas `mode=REAL` y 5 `mode=PAPER`
- WHEN `GET /api/v1/bets?mode=REAL`
- THEN retorna exactamente 3 ítems, todos con `mode=real`

#### Scenario: Filtrado combinado

- GIVEN existen 2 apuestas REAL PENDING y 1 REAL WON
- WHEN `GET /api/v1/bets?mode=REAL&status=pending`
- THEN retorna exactamente 2 ítems

#### Scenario: Sin filtros — todas

- GIVEN 8 apuestas en total (mix de modos y estados)
- WHEN `GET /api/v1/bets`
- THEN retorna los 8 ítems

---

### Requirement: DELETE /api/v1/bets/{id} — Borrar Apuesta REAL Pendiente

MUST borrar la apuesta SOLO si `mode=REAL` y `status=PENDING`. Response HTTP 204.
MUST retornar 409 si `status != PENDING` (apuesta liquidada).
Las apuestas `mode=PAPER` MUST NOT borrarse — retornar 400.

#### Scenario: Borrado exitoso

- GIVEN `bet_id=5`, `mode=REAL`, `status=PENDING`
- WHEN `DELETE /api/v1/bets/5`
- THEN HTTP 204; fila eliminada de `bet_log`

#### Scenario: Apuesta liquidada — 409

- GIVEN `bet_id=5`, `mode=REAL`, `status=WON`
- WHEN `DELETE /api/v1/bets/5`
- THEN HTTP 409, `{"detail": "Bet already settled"}`

#### Scenario: Apuesta PAPER — 400

- GIVEN `bet_id=3`, `mode=PAPER`
- WHEN `DELETE /api/v1/bets/3`
- THEN HTTP 400, `{"detail": "PAPER bets cannot be deleted manually"}`

#### Scenario: No existe — 404

- GIVEN `bet_id=9999` no existe
- WHEN `DELETE /api/v1/bets/9999`
- THEN HTTP 404
