"""Tests unitarios TDD para derive_components (union-find puro).

Escenarios:
  - Grafo válido 12×4: retorna exactamente 12 componentes de 4 nodos cada una.
  - 11 componentes: AssertionError antes de retornar.
  - Componente de 5: AssertionError antes de retornar.
"""

import pytest

from app.model.group_utils import derive_components

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wc_edges() -> list[tuple[str, str]]:
    """Genera 72 aristas (6 partidos × 12 grupos) formando 12 componentes de 4."""
    groups = [
        ["A1", "A2", "A3", "A4"],
        ["B1", "B2", "B3", "B4"],
        ["C1", "C2", "C3", "C4"],
        ["D1", "D2", "D3", "D4"],
        ["E1", "E2", "E3", "E4"],
        ["F1", "F2", "F3", "F4"],
        ["G1", "G2", "G3", "G4"],
        ["H1", "H2", "H3", "H4"],
        ["I1", "I2", "I3", "I4"],
        ["J1", "J2", "J3", "J4"],
        ["K1", "K2", "K3", "K4"],
        ["L1", "L2", "L3", "L4"],
    ]
    edges = []
    for g in groups:
        # 6 aristas para 4 nodos: todas las combinaciones
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                edges.append((g[i], g[j]))
    return edges


# ---------------------------------------------------------------------------
# Test: grafo válido 12×4
# ---------------------------------------------------------------------------


def test_derive_components_valid_12x4():
    """Grafo válido → retorna exactamente 12 componentes de 4 nodos cada una."""
    edges = _wc_edges()
    components = derive_components(edges)

    assert len(components) == 12
    for comp in components:
        assert len(comp) == 4


# ---------------------------------------------------------------------------
# Test: grafo con 11 componentes → AssertionError
# ---------------------------------------------------------------------------


def test_derive_components_11_components_raises():
    """Solo 11 grupos (44 equipos) → AssertionError antes de retornar."""
    # Genera 11 grupos válidos de 4
    groups_11 = [[f"T{g}{i}" for i in range(1, 5)] for g in "ABCDEFGHIJK"]
    edges = []
    for g in groups_11:
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                edges.append((g[i], g[j]))

    with pytest.raises(AssertionError):
        derive_components(edges)


# ---------------------------------------------------------------------------
# Test: componente de 5 → AssertionError
# ---------------------------------------------------------------------------


def test_derive_components_group_of_5_raises():
    """Una componente tiene 5 nodos → AssertionError antes de retornar."""
    # 11 grupos de 4 + 1 grupo de 5 = 12 componentes pero una tiene 5
    groups = [[f"T{g}{i}" for i in range(1, 5)] for g in "ABCDEFGHIJK"]
    # El último grupo tiene 5 miembros
    groups.append(["L1", "L2", "L3", "L4", "L5"])

    edges = []
    for g in groups:
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                edges.append((g[i], g[j]))

    with pytest.raises(AssertionError):
        derive_components(edges)
