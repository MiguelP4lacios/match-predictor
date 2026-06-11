"""Tests TDD para app/model/annex_c.py — tabla de asignación de 3ros (FIFA Annex C).

Escenarios:
  A1: len(ANNEX_C) == 495
  A2: Todas las claves son frozensets de tamaño 8
  A3: Todas las letras de claves están en {A..L}
  A4: Lookup de la Opción 1 devuelve el mapa correcto
  A5: validate_annex_c() no lanza excepción (internamente verifica invariantes)
"""

import pytest

from app.model.annex_c import ANNEX_C, validate_annex_c

_VALID_LETTERS = frozenset("ABCDEFGHIJKL")

# Opción 1 (primera fila): qualifying groups = {E,F,G,H,I,J,K,L}
# Columnas 1A→E, 1B→J, 1D→I, 1E→F, 1G→H, 1I→G, 1K→L, 1L→K
_OPT1_KEY = frozenset("EFGHIJKL")
_OPT1_MAP = {"1A": "E", "1B": "J", "1D": "I", "1E": "F", "1G": "H", "1I": "G", "1K": "L", "1L": "K"}


# ---------------------------------------------------------------------------
# A1: Exactamente 495 entradas
# ---------------------------------------------------------------------------


def test_a1_annex_c_has_495_entries():
    """A1: ANNEX_C debe tener exactamente 495 entradas (C(12,8) = 495)."""
    assert len(ANNEX_C) == 495


# ---------------------------------------------------------------------------
# A2: Todas las claves son frozensets de tamaño 8
# ---------------------------------------------------------------------------


def test_a2_all_keys_are_frozensets_of_size_8():
    """A2: Cada clave es un frozenset con exactamente 8 letras de grupo."""
    for key in ANNEX_C:
        assert isinstance(key, frozenset), f"Clave no es frozenset: {key}"
        assert len(key) == 8, f"Clave tiene {len(key)} letras, esperado 8: {key}"


# ---------------------------------------------------------------------------
# A3: Todas las letras son de A a L
# ---------------------------------------------------------------------------


def test_a3_all_letters_in_a_to_l():
    """A3: Las letras en las claves y valores deben estar en {A..L}."""
    for key, slotmap in ANNEX_C.items():
        # Key letters
        for letter in key:
            assert letter in _VALID_LETTERS, f"Letra inválida en clave: {letter!r}"
        # Value letters
        for slot, letter in slotmap.items():
            assert letter in _VALID_LETTERS, (
                f"Letra inválida en valor ({slot}={letter!r}) para key={key}"
            )


# ---------------------------------------------------------------------------
# A4: Lookup de Opción 1 es correcto
# ---------------------------------------------------------------------------


def test_a4_opt1_lookup_is_correct():
    """A4: Opción 1 — {E,F,G,H,I,J,K,L} → mapa exacto de slots."""
    assert _OPT1_KEY in ANNEX_C, f"Clave opt-1 {_OPT1_KEY} no encontrada en ANNEX_C"
    result = ANNEX_C[_OPT1_KEY]
    assert result == _OPT1_MAP, f"Opt-1 esperado {_OPT1_MAP}, obtenido {result}"


# ---------------------------------------------------------------------------
# A5: validate_annex_c() no lanza
# ---------------------------------------------------------------------------


def test_a5_validate_annex_c_passes():
    """A5: validate_annex_c() debe pasar sin excepción si los datos son correctos."""
    validate_annex_c()  # debe terminar sin levantar
