"""Union-find puro para derivar componentes conexas desde el grafo de fixtures.

Función pura, sin BD, sin LLM (invariante de arquitectura).
Usada por ``scripts/seed_groups.py`` para detectar los 12 grupos del Mundial 2026
a partir de las aristas (home_team, away_team) de los fixtures SCHEDULED.

La aserción dura garantiza que el grafo tenga exactamente 12 componentes de 4
equipos cada una ANTES de escribir ninguna fila en la BD.
"""


def derive_components(edges: list[tuple[str, str]]) -> list[frozenset[str]]:
    """Deriva componentes conexas de un grafo de fixtures usando union-find.

    Args:
        edges: lista de pares (equipo_local, equipo_visitante) de los fixtures
               SCHEDULED del torneo.

    Returns:
        Lista de frozenset — cada uno contiene los nombres canónicos de los
        equipos de un grupo.

    Raises:
        AssertionError: si el resultado no son exactamente 12 componentes de
                        exactamente 4 equipos. Falla ruidoso antes de escribir.
    """
    parent: dict[str, str] = {}
    rank: dict[str, int] = {}

    def _find(x: str) -> str:
        if parent.setdefault(x, x) != x:
            parent[x] = _find(parent[x])  # compresión de ruta
        return parent[x]

    def _union(a: str, b: str) -> None:
        ra, rb = _find(a), _find(b)
        if ra == rb:
            return
        # unión por rango
        if rank.get(ra, 0) < rank.get(rb, 0):
            ra, rb = rb, ra
        parent[rb] = ra
        if rank.get(ra, 0) == rank.get(rb, 0):
            rank[ra] = rank.get(ra, 0) + 1

    for a, b in edges:
        _union(a, b)

    # Agrupar nodos por raíz
    groups: dict[str, set[str]] = {}
    for node in parent:
        root = _find(node)
        groups.setdefault(root, set()).add(node)

    components = [frozenset(members) for members in groups.values()]

    assert len(components) == 12 and all(len(c) == 4 for c in components), (
        f"Se esperaban 12 componentes de 4 equipos; "
        f"se obtuvieron {len(components)} componente(s): "
        + ", ".join(f"{len(c)} equipos" for c in components if len(c) != 4)
        or f"todos de tamaño válido pero {len(components)} != 12"
    )

    return components
