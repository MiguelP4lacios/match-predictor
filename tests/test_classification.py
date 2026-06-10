"""Tests para el clasificador puro app/ingestion/classification.py.

Spec: match-ingestion R1 (K-factor Classification), escenarios S1-S5.
TDD RED: todos deben FALLAR hasta que se cree classification.py.

Cubre:
  - FIFA World Cup → WORLD_CUP (S1)
  - CONIFA/Viva → OTHER (S2), CECAFA → OTHER (S3)
  - Copa América → CONTINENTAL (S4)
  - FIFA WC qualification → QUALIFIER precede a world cup (S5)
  - k_factor(OTHER) == 30 explícito en _K_BY_KIND
  - Whitelist completa de CONTINENTAL_CHAMPIONSHIPS
  - Fallback → OTHER para torneos desconocidos
  - Nations League → NATIONS_LEAGUE
  - Friendly → FRIENDLY
"""

import pytest

from app.ingestion.classification import classify_competition_kind  # no existe aún
from app.model.elo import k_factor
from app.models.enums import CompetitionKind

# ---------------------------------------------------------------------------
# S1: FIFA World Cup → WORLD_CUP (K=60)
# ---------------------------------------------------------------------------

def test_fifa_world_cup_maps_to_world_cup():
    assert classify_competition_kind("FIFA World Cup") == CompetitionKind.WORLD_CUP


def test_world_cup_k_factor_is_60():
    assert k_factor(CompetitionKind.WORLD_CUP) == 60


# ---------------------------------------------------------------------------
# S2: CONIFA / Viva World Cup → OTHER (K=30, NOT WORLD_CUP)
# ---------------------------------------------------------------------------

def test_conifa_world_cup_maps_to_other():
    assert classify_competition_kind("CONIFA World Football Cup") == CompetitionKind.OTHER


def test_viva_world_cup_maps_to_other():
    assert classify_competition_kind("Viva World Cup") == CompetitionKind.OTHER


def test_other_k_factor_is_30():
    assert k_factor(CompetitionKind.OTHER) == 30


def test_conifa_not_world_cup():
    kind = classify_competition_kind("CONIFA World Football Cup")
    assert kind != CompetitionKind.WORLD_CUP


# ---------------------------------------------------------------------------
# S3: CECAFA Cup → OTHER (K=30)
# ---------------------------------------------------------------------------

def test_cecafa_cup_maps_to_other():
    assert classify_competition_kind("CECAFA Cup") == CompetitionKind.OTHER


def test_unknown_tournament_maps_to_other():
    """Cualquier torneo no reconocido cae a OTHER (fallback)."""
    assert classify_competition_kind("World Unity Cup") == CompetitionKind.OTHER
    assert classify_competition_kind("FIFI Wild Cup") == CompetitionKind.OTHER
    assert classify_competition_kind("Beach Soccer World Cup") == CompetitionKind.OTHER


# ---------------------------------------------------------------------------
# S4: Copa América → CONTINENTAL (K=50)
# ---------------------------------------------------------------------------

def test_copa_america_maps_to_continental():
    assert classify_competition_kind("Copa América") == CompetitionKind.CONTINENTAL


def test_continental_k_factor_is_50():
    assert k_factor(CompetitionKind.CONTINENTAL) == 50


# ---------------------------------------------------------------------------
# S5: FIFA World Cup qualification → QUALIFIER (precede a world cup keyword)
# ---------------------------------------------------------------------------

def test_qualification_overrides_world_cup():
    assert classify_competition_kind("FIFA World Cup qualification") == CompetitionKind.QUALIFIER


def test_qualifier_keyword():
    assert classify_competition_kind("UEFA qualifier") == CompetitionKind.QUALIFIER


def test_qualifier_k_factor_is_40():
    assert k_factor(CompetitionKind.QUALIFIER) == 40


# ---------------------------------------------------------------------------
# Whitelist CONTINENTAL_CHAMPIONSHIPS — todos los nombres reales del dataset
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "UEFA Euro",
    "Copa América",
    "African Cup of Nations",
    "AFC Asian Cup",
    "Gold Cup",
    "CONCACAF Championship",
    "Oceania Nations Cup",
    "Confederations Cup",
])
def test_continental_whitelist(name):
    assert classify_competition_kind(name) == CompetitionKind.CONTINENTAL


# ---------------------------------------------------------------------------
# Nations League y Friendly
# ---------------------------------------------------------------------------

def test_nations_league():
    assert classify_competition_kind("UEFA Nations League") == CompetitionKind.NATIONS_LEAGUE


def test_friendly():
    assert classify_competition_kind("Friendly") == CompetitionKind.FRIENDLY


def test_friendly_k_factor_is_20():
    from app.model.elo import K_FRIENDLY
    assert k_factor(CompetitionKind.FRIENDLY) == K_FRIENDLY
