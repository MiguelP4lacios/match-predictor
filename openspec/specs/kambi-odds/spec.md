# Kambi Odds Specification

## Purpose

Adapter `KambiOddsSource` que implementa el Protocol `OddsSource` para capturar
cuotas del frontend-API de Kambi (white-label BetPlay). Flag-gated `KAMBI_ENABLED=false`
por defecto. NO forma parte del daily loop. Mejora opcional — la entrada manual de
cuotas en el cupón es el camino principal.

---

## Requirements

### Requirement: KambiOddsSource

`KambiOddsSource` MUST implementar `OddsSource` (`fetch_odds() -> Iterator[RawOdds]`).

**Mapeo JSON → RawOdds:**

| Campo RawOdds | Fuente Kambi |
|---|---|
| `source` | `DataSource.KAMBI` |
| `event_id` | `str(event.id)` |
| `commence_time` | `event.start` (ISO Z) |
| `home_team` | `participants[homeAway==HOME].name` → `_KAMBI_NAME_OVERRIDES` |
| `away_team` | `participants[homeAway==AWAY].name` → `_KAMBI_NAME_OVERRIDES` |
| `bookmaker` | `"betplay"` (hardcoded) |
| `market_key` | `criterion.englishLabel == "Full Time"` → `"h2h"` |
| `price` | `outcome.odds / 1000` (milli-odds) |
| `outcome_name` | `outcome.participant` (HOME/AWAY) o `"Draw"` (DRAW) |
| `line` | `None` |

MUST usar `lang=en_US` en la URL (menor riesgo de desajuste de nombres vs `es_CO`).

MUST definir `_KAMBI_NAME_OVERRIDES` (en_US) cubriendo al mínimo:

| Kambi en_US | DB canonical |
|---|---|
| `"USA"` | `"United States"` |
| `"Korea Republic"` | `"South Korea"` |
| `"Côte d'Ivoire"` | `"Ivory Coast"` |
| `"Czechia"` | `"Czech Republic"` |
| `"Congo DR"` | `"DR Congo"` |
| `"Bosnia & Herzegovina"` | `"Bosnia and Herzegovina"` |

MUST filtrar solo betOffers con `criterion.englishLabel == "Full Time"` y `outcome.status == "Open"`.

`DataSource.KAMBI` MUST existir en `app/models/enums.py`.

`KAMBI_ENABLED` en `app/core/config.py` MUST tener default `false`. Cuando
`KAMBI_ENABLED=false`, el scheduler MUST NOT instanciar ni llamar `KambiOddsSource`.

**Nota de fragilidad (honesta, MUST documentar en docstring del módulo):**
API de browser sin clave publicada. IPs de datacenter reciben 429 persistente.
Slug `betplay` sin confirmar desde servidor. Usar solo con IP residencial CO o proxy.
Entrada manual de cuotas es el fallback garantizado.

#### Scenario: Fixture JSON → RawOdds correctos

- GIVEN fixture Kambi JSON con `event.id=123`, `event.start="2026-06-15T15:00:00Z"`,
  participants `Mexico HOME / Argentina AWAY`; betOffer Full Time outcomes:
  `{type=HOME, participant="Mexico", odds=1400}`,
  `{type=DRAW, odds=3200}`,
  `{type=AWAY, participant="Argentina", odds=2100}`
- WHEN `KambiOddsSource(fixture_json).fetch_odds()` itera
- THEN yield 1: `RawOdds(source=KAMBI, home_team="Mexico", away_team="Argentina", market_key="h2h", price=1.40, outcome_name="Mexico")`
- AND yield 2: `price=3.20, outcome_name="Draw"`
- AND yield 3: `price=2.10, outcome_name="Argentina"`

#### Scenario: milli-odds 1700 → decimal 1.70

- GIVEN outcome con `odds=1700`
- WHEN se construye `RawOdds`
- THEN `price=1.70`

#### Scenario: Name override en_US

- GIVEN outcome HOME con `participant="USA"`
- WHEN se aplica `_KAMBI_NAME_OVERRIDES`
- THEN `home_team="United States"`

#### Scenario: KAMBI_ENABLED=false → scheduler no invoca KambiOddsSource

- GIVEN `KAMBI_ENABLED=false` en config
- WHEN el scheduler ejecuta el job de captura de cuotas
- THEN `KambiOddsSource` NO es instanciado ni llamado
