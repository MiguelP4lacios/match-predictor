"""TDD RED → GREEN — KambiOddsSource: adapter de cuotas Kambi (fixture-only, NUNCA live).

Escenarios:
  S1 — fixture→3 RawOdds (price=1.40/3.20/2.10 desde odds milli 1400/3200/2100)
  S2 — odds milli 1700→1.70 (test del criterion Full Time en kambi_sample.json)
  S3 — "USA" participant override → "United States" en outcome_name
  S4 — KAMBI_ENABLED=false → source no instanciado (no debe crear instancia)
  S5 — Solo outcomes Full Time + OPEN (Half Time excluido del fixture)

NUNCA httpx live: se usa el JSON fixture cargado directamente.
"""

import json
from pathlib import Path

import pytest

from app.ingestion.sources.kambi import KambiOddsSource
from app.models.enums import DataSource

# Fixture path relativo al repo raíz
FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "kambi_sample.json"


@pytest.fixture()
def sample_payload() -> dict:
    """Carga el JSON fixture kambi_sample.json."""
    return json.loads(FIXTURE_PATH.read_text())


# ---------------------------------------------------------------------------
# S1 — fixture → 3 RawOdds con prices 1.40/3.20/2.10
# ---------------------------------------------------------------------------


def test_kambi_fixture_produces_3_odds(sample_payload):
    """El Full Time betOffer del fixture tiene 3 outcomes → 3 RawOdds."""
    source = KambiOddsSource(operator="betplay", base_url="https://fake.kambi.test")
    odds_list = list(source._parse_events(sample_payload["events"]))

    # Only Full Time + OPEN → 3 outcomes from the first betOffer
    assert len(odds_list) == 3


def test_kambi_prices_milli_to_decimal(sample_payload):
    """Odds milli 1400/3200/2100 → decimal 1.40/3.20/2.10."""
    source = KambiOddsSource(operator="betplay", base_url="https://fake.kambi.test")
    odds_list = list(source._parse_events(sample_payload["events"]))

    prices = sorted(o.price for o in odds_list)
    assert prices == pytest.approx([1.40, 2.10, 3.20], abs=0.001)


# ---------------------------------------------------------------------------
# S2 — milli 1700 → 1.70 (Full Time criterion hardcoded label check)
# ---------------------------------------------------------------------------


def test_kambi_milli_1700_to_1_70():
    """Convierte odds milli 1700 → 1.70 correctamente."""
    source = KambiOddsSource(operator="betplay", base_url="https://fake.kambi.test")
    events = [
        {
            "event": {
                "id": 999,
                "name": "A vs B",
                "start": "2026-07-10T20:00:00Z",
                "homeName": "A",
                "awayName": "B",
            },
            "betOffers": [
                {
                    "id": 111,
                    "criterion": {"id": 1001374577, "label": "Full Time"},
                    "betOfferType": {"id": 2, "name": "Match"},
                    "status": "OPEN",
                    "outcomes": [
                        {
                            "id": 1,
                            "label": "1",
                            "englishLabel": "Home",
                            "odds": 1700,
                            "participant": "A",
                            "type": "OT_ONE",
                        },
                        {
                            "id": 2,
                            "label": "2",
                            "englishLabel": "Away",
                            "odds": 2100,
                            "participant": "B",
                            "type": "OT_TWO",
                        },
                    ],
                }
            ],
        }
    ]
    odds_list = list(source._parse_events(events))
    home_odd = next(o for o in odds_list if "Home" in o.outcome_name or o.outcome_name == "A")
    assert home_odd.price == pytest.approx(1.70, abs=0.001)


# ---------------------------------------------------------------------------
# S3 — "USA" → "United States" via _KAMBI_NAME_OVERRIDES
# ---------------------------------------------------------------------------


def test_kambi_name_override_usa(sample_payload):
    """participant 'USA' en fixture → outcome_name normalizado a 'United States'."""
    source = KambiOddsSource(operator="betplay", base_url="https://fake.kambi.test")
    odds_list = list(source._parse_events(sample_payload["events"]))

    home_odd = next(o for o in odds_list if o.price == pytest.approx(1.40, abs=0.01))
    # USA should be overridden to United States
    assert home_odd.outcome_name == "United States"


# ---------------------------------------------------------------------------
# S4 — KAMBI_ENABLED=false → not instantiating (config gate check)
# ---------------------------------------------------------------------------


def test_kambi_disabled_flag_gate():
    """Si KAMBI_ENABLED=false, make_kambi_source() devuelve None."""
    from app.scheduler.jobs import make_kambi_source

    # Default config has kambi_enabled=False
    result = make_kambi_source()
    assert result is None


# ---------------------------------------------------------------------------
# S5 — Solo Full Time + OPEN incluidos; Half Time (criterion id diferente) excluido
# ---------------------------------------------------------------------------


def test_kambi_filters_out_half_time(sample_payload):
    """El fixture tiene Half Time betOffer → debe excluirse. Solo Full Time retorna."""
    source = KambiOddsSource(operator="betplay", base_url="https://fake.kambi.test")
    odds_list = list(source._parse_events(sample_payload["events"]))

    # Full Time has 3 outcomes; Half Time has 1 outcome but should be filtered
    # Verify total is 3 (not 4)
    assert len(odds_list) == 3


# ---------------------------------------------------------------------------
# S6 — source attribute
# ---------------------------------------------------------------------------


def test_kambi_source_attribute():
    """KambiOddsSource.source == DataSource.KAMBI."""
    source = KambiOddsSource(operator="betplay", base_url="https://fake.kambi.test")
    assert source.source == DataSource.KAMBI
