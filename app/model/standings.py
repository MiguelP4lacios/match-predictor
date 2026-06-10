"""Tabla de posiciones con desempates FIFA — función pura, sin BD.

Invariante de arquitectura: cero llamadas a BD, cero LLM, resultado determinista.
Replica el patrón de elo.py: módulo puro fácilmente testeable.

Orden de criterios de desempate (FIFA fase de grupos):
  1. Puntos (Pts)
  2. Diferencia de goles (DG = GF − GC)
  3. Goles a favor (GF)
  4. Head-to-head: puntos en partidos entre los empatados
  5. Head-to-head: diferencia de goles en esos partidos
  6. Head-to-head: goles a favor en esos partidos
  7. Nombre del equipo (orden alfabético) — desempate determinista final

Tarjetas / fair-play: FUERA de alcance (datos no ingestados).

H2H se calcula como mini-tabla restringida a partidos ENTRE el subgrupo empatado.
El helper ``_rank_subset`` es recursivo: si después de aplicar H2H el subgrupo sigue
empatado, cae directamente al criterio alfabético (nombre) para garantizar orden
determinista sin bucles infinitos.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TeamRef:
    """Referencia mínima a un equipo: ID y nombre canónico."""

    team_id: int
    name: str


@dataclass(frozen=True)
class MatchResult:
    """Resultado de un partido terminado (FINISHED)."""

    home_id: int
    away_id: int
    home_score: int
    away_score: int


@dataclass
class StandingRow:
    """Fila de la tabla de posiciones de un grupo."""

    team_name: str
    pj: int = 0   # partidos jugados
    g: int = 0    # ganados
    e: int = 0    # empatados
    p: int = 0    # perdidos
    gf: int = 0   # goles a favor
    gc: int = 0   # goles en contra
    dg: int = 0   # diferencia de goles (GF − GC)
    pts: int = 0  # puntos


def _accumulate(
    members: list[TeamRef], results: list[MatchResult]
) -> dict[int, StandingRow]:
    """Calcula estadísticas globales de cada equipo a partir de los resultados."""
    rows: dict[int, StandingRow] = {
        m.team_id: StandingRow(team_name=m.name) for m in members
    }

    for r in results:
        h = rows.get(r.home_id)
        a = rows.get(r.away_id)
        if h is None or a is None:
            continue

        h.pj += 1
        a.pj += 1
        h.gf += r.home_score
        h.gc += r.away_score
        a.gf += r.away_score
        a.gc += r.home_score
        h.dg = h.gf - h.gc
        a.dg = a.gf - a.gc

        if r.home_score > r.away_score:
            h.g += 1
            h.pts += 3
            a.p += 1
        elif r.home_score < r.away_score:
            a.g += 1
            a.pts += 3
            h.p += 1
        else:
            h.e += 1
            h.pts += 1
            a.e += 1
            a.pts += 1

    return rows


def _h2h_stats(
    subset_ids: frozenset[int], results: list[MatchResult]
) -> dict[int, tuple[int, int, int]]:
    """Calcula (pts, dg, gf) H2H de cada equipo del subgrupo en partidos internos.

    Solo considera partidos donde AMBOS equipos están dentro del subconjunto.
    """
    stats: dict[int, list[int]] = {tid: [0, 0, 0] for tid in subset_ids}

    for r in results:
        if r.home_id not in subset_ids or r.away_id not in subset_ids:
            continue
        h = stats[r.home_id]
        a = stats[r.away_id]
        h[2] += r.home_score   # gf H2H
        a[2] += r.away_score
        h[1] += r.home_score - r.away_score   # dg H2H
        a[1] += r.away_score - r.home_score
        if r.home_score > r.away_score:
            h[0] += 3
        elif r.home_score < r.away_score:
            a[0] += 3
        else:
            h[0] += 1
            a[0] += 1

    return {tid: (v[0], v[1], v[2]) for tid, v in stats.items()}


def _rank_subset(
    subset: list[tuple[int, StandingRow]],  # (team_id, row)
    results: list[MatchResult],
    *,
    _h2h_applied: bool = False,
) -> list[tuple[int, StandingRow]]:
    """Ordena un subgrupo de equipos empatados usando H2H y luego nombre.

    El subgrupo está empatado en Pts+DG+GF (criterios globales 1-3).
    Aplica una ronda de H2H y, si sigue empatado, cae al nombre alfabético.

    Args:
        subset:        pares (team_id, StandingRow) a ordenar.
        results:       todos los resultados del grupo.
        _h2h_applied:  True cuando ya se aplicó una ronda H2H (evita re-aplicar).
    """
    if len(subset) <= 1:
        return subset

    if _h2h_applied:
        # Ya se aplicó H2H y siguen empatados → criterio determinista final: nombre
        return sorted(subset, key=lambda x: x[1].team_name)

    # Calcular H2H dentro del subconjunto
    subset_ids = frozenset(tid for tid, _ in subset)
    h2h = _h2h_stats(subset_ids, results)

    def _h2h_key(item: tuple[int, StandingRow]) -> tuple:
        tid, _ = item
        pts, dg, gf = h2h[tid]
        return (-pts, -dg, -gf)

    sorted_sub = sorted(subset, key=_h2h_key)

    # Reagrupar: si aún hay empate en H2H, caer a nombre
    result: list[tuple[int, StandingRow]] = []
    i = 0
    while i < len(sorted_sub):
        j = i + 1
        while j < len(sorted_sub) and _h2h_key(sorted_sub[j]) == _h2h_key(sorted_sub[i]):
            j += 1
        group = sorted_sub[i:j]
        result.extend(_rank_subset(group, results, _h2h_applied=True))
        i = j

    return result


def compute_standings(
    members: list[TeamRef],
    results: list[MatchResult],
) -> list[StandingRow]:
    """Calcula y retorna la tabla de posiciones del grupo.

    Desempates FIFA (en orden):
      1. Pts  2. DG  3. GF  4. H2H-Pts  5. H2H-DG  6. H2H-GF  7. Nombre (alfa)

    H2H se aplica únicamente dentro del subgrupo empatado (no globalmente).
    Tarjetas/fair-play FUERA de alcance.

    Args:
        members: equipos del grupo (team_id + name).
        results: resultados FINISHED del grupo.

    Returns:
        Lista de StandingRow ordenada por posición (índice 0 = 1er lugar).
    """
    rows_by_id = _accumulate(members, results)

    if not results:
        # Sin resultados: todos en 0, orden alfabético
        return sorted(rows_by_id.values(), key=lambda r: r.team_name)

    # Paso 1: ordenar por criterios globales (Pts, DG, GF)
    items = list(rows_by_id.items())  # [(team_id, StandingRow)]

    def _global_key(item: tuple[int, StandingRow]) -> tuple:
        _, row = item
        return (-row.pts, -row.dg, -row.gf)

    items.sort(key=_global_key)

    # Paso 2: para cada grupo empatado en criterios globales, aplicar H2H subset
    ranked: list[tuple[int, StandingRow]] = []
    i = 0
    while i < len(items):
        j = i + 1
        while j < len(items) and _global_key(items[j]) == _global_key(items[i]):
            j += 1
        group = items[i:j]
        if len(group) == 1:
            ranked.extend(group)
        else:
            ranked.extend(_rank_subset(group, results))
        i = j

    return [row for _, row in ranked]
