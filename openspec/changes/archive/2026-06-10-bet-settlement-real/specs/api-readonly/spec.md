# Delta for API Read-Only

## MODIFIED Requirements

### Requirement: R6 — GET /api/v1/paper

Agrega estadísticas de `BetLog` **por modo** (PAPER y REAL separados).
Las monedas y unidades de cada modo MUST NOT mezclarse en ningún cómputo.
ROI MUST calcularse como `sum(pnl) / sum(stake)` sobre WON+LOST por modo.
Cuando `settled = 0` para un modo, `roi` de ese modo MUST ser `null`.

(Previously: retornaba un único bloque con stats solo de PAPER, campos `total`,
`open`, `settled`, `roi`.)

Response shape:

```json
{
  "paper": {
    "total": <int>,
    "pending": <int>,
    "settled": <int>,
    "won": <int>,
    "lost": <int>,
    "staked": <decimal|null>,
    "returns": <decimal|null>,
    "roi": <float|null>
  },
  "real": {
    "total": <int>,
    "pending": <int>,
    "settled": <int>,
    "won": <int>,
    "lost": <int>,
    "staked": <decimal|null>,
    "returns": <decimal|null>,
    "roi": <float|null>
  }
}
```

`staked` = `sum(stake)` sobre WON+LOST del modo.
`returns` = `staked + sum(pnl)` sobre WON+LOST del modo.
`roi` = `sum(pnl) / sum(stake)` sobre WON+LOST del modo; `null` si `settled=0`.

#### Scenario: ROI REAL — verificación numérica

- GIVEN 2 apuestas REAL: bet A `stake=12000.00 pnl=+4800.00 WON`,
  bet B `stake=12000.00 pnl=−12000.00 LOST`
- WHEN `GET /api/v1/paper`
- THEN `real.staked=24000.00`, `real.returns=16800.00`,
  `real.roi = (4800 − 12000) / 24000 = −7200/24000 = −0.30`

#### Scenario: ROI REAL positivo — verificación numérica

- GIVEN 2 apuestas REAL: `staked=24000` total, `returns=28800`
  (pnl neto = +4800)
- WHEN `GET /api/v1/paper`
- THEN `real.roi = 4800 / 24000 = 0.20` → frontend renderiza `"+20.0%"`

#### Scenario: REAL sin settled — roi null

- GIVEN todas las apuestas REAL tienen `status=PENDING`
- WHEN `GET /api/v1/paper`
- THEN `real.settled=0`, `real.roi=null`

#### Scenario: PAPER con datos, REAL vacío

- GIVEN 3 apuestas PAPER (2 WON, 1 PENDING), 0 apuestas REAL
- WHEN `GET /api/v1/paper`
- THEN `paper.total=3`, `paper.settled=2`, `paper.roi` calculado;
  `real.total=0`, `real.roi=null`

#### Scenario: Modos nunca mezclados

- GIVEN 5 PAPER bets con `pnl` y 3 REAL bets con `pnl`
- WHEN `GET /api/v1/paper`
- THEN `paper.roi` y `real.roi` calculados independientemente;
  ningún campo de `real` incluye sumas de PAPER ni viceversa
