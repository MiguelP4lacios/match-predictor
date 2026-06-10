"""Tests unitarios TDD para compute_standings — desempates FIFA.

Escenarios del spec group-standings/spec.md:
  S1: sin empate numérico → orden por Pts (verificación aritmética completa)
  S2: DG desempata (mismo Pts) → verificación aritmética completa
  S3: H2H desempata B>C (mismo Pts + DG + GF) → verificación aritmética completa
  S4: 0 partidos terminados → 4 equipos con todo en 0, orden alfabe ́tico
  S5: triple-empate sin resolución H2H → cae a nombre alfabético

Aritmética verificada manualmente antes de escribir el test:
  S1: A 3-0 B, C 1-1 D, A 1-0 C, B 2-1 D, A 0-0 D, B 1-2 C
    A: pj=3 g=2 e=1 p=0 gf=4 gc=0 dg=+4 pts=7
    C: pj=3 g=1 e=1 p=1 gf=3 gc=3 dg=0  pts=4
    B: pj=3 g=1 e=0 p=2 gf=3 gc=6 dg=-3 pts=3
    D: pj=3 g=0 e=2 p=1 gf=2 gc=3 dg=-1 pts=2

  S2: A 2-0 B, A 0-0 C, A 0-0 D, B 0-1 C, B 0-0 D, C 0-0 D
    A: pts=5 dg=+2 gf=2
    C: pts=5 dg=+1 gf=1   ← A>C por DG
    D: pts=3 dg=0  gf=0
    B: pts=1 dg=-3 gf=0

  S3: A 1-0 B, A 1-1 C, A 0-0 D, B 1-0 C, B 1-1 D, C 1-0 D
    A: pts=5 dg=+1 gf=2  (no empate)
    B: pts=4 dg=0  gf=2  ← B>C por H2H (B 1-0 C → 3 pts H2H vs 0)
    C: pts=4 dg=0  gf=2
    D: pts=2 dg=-1 gf=1  (no empate)
"""

from app.model.standings import MatchResult, TeamRef, compute_standings

# ---------------------------------------------------------------------------
# Helpers de construcción de fixtures de test
# ---------------------------------------------------------------------------

_TEAMS_ABCD = [
    TeamRef(team_id=1, name="A"),
    TeamRef(team_id=2, name="B"),
    TeamRef(team_id=3, name="C"),
    TeamRef(team_id=4, name="D"),
]

_ID = {t.name: t.team_id for t in _TEAMS_ABCD}


def _mr(h: str, a: str, hg: int, ag: int) -> MatchResult:
    """Shorthand para MatchResult usando letras."""
    return MatchResult(home_id=_ID[h], away_id=_ID[a], home_score=hg, away_score=ag)


# ---------------------------------------------------------------------------
# Scenario S1: sin empate numérico (verificación aritmética completa)
# ---------------------------------------------------------------------------


def test_s1_no_numeric_tie_full_order():
    """S1: 6 partidos, orden A>C>B>D sin empate numérico.

    Aritmética:
      A: pts=7 dg=+4 | C: pts=4 dg=0 | B: pts=3 dg=-3 | D: pts=2 dg=-1
    """
    results = [
        _mr("A", "B", 3, 0),
        _mr("C", "D", 1, 1),
        _mr("A", "C", 1, 0),
        _mr("B", "D", 2, 1),
        _mr("A", "D", 0, 0),
        _mr("B", "C", 1, 2),
    ]
    table = compute_standings(_TEAMS_ABCD, results)

    assert [r.team_name for r in table] == ["A", "C", "B", "D"]

    a = table[0]
    assert a.pj == 3 and a.g == 2 and a.e == 1 and a.p == 0
    assert a.gf == 4 and a.gc == 0 and a.dg == 4 and a.pts == 7

    c = table[1]
    assert c.pj == 3 and c.g == 1 and c.e == 1 and c.p == 1
    assert c.gf == 3 and c.gc == 3 and c.dg == 0 and c.pts == 4

    b = table[2]
    assert b.pj == 3 and b.g == 1 and b.e == 0 and b.p == 2
    assert b.gf == 3 and b.gc == 6 and b.dg == -3 and b.pts == 3

    d = table[3]
    assert d.pj == 3 and d.g == 0 and d.e == 2 and d.p == 1
    assert d.gf == 2 and d.gc == 3 and d.dg == -1 and d.pts == 2


# ---------------------------------------------------------------------------
# Scenario S2: empate en Pts, desempata DG (verificación aritmética completa)
# ---------------------------------------------------------------------------


def test_s2_tie_on_pts_broken_by_goal_diff():
    """S2: A y C empatados a 5 pts; A>C porque DG +2 > +1.

    Aritmética:
      A: pts=5 dg=+2 gf=2 | C: pts=5 dg=+1 gf=1 | D: pts=3 dg=0 gf=0 | B: pts=1 dg=-3 gf=0
    """
    results = [
        _mr("A", "B", 2, 0),
        _mr("A", "C", 0, 0),
        _mr("A", "D", 0, 0),
        _mr("B", "C", 0, 1),
        _mr("B", "D", 0, 0),
        _mr("C", "D", 0, 0),
    ]
    table = compute_standings(_TEAMS_ABCD, results)

    assert [r.team_name for r in table] == ["A", "C", "D", "B"]
    assert table[0].pts == 5 and table[0].dg == 2
    assert table[1].pts == 5 and table[1].dg == 1


# ---------------------------------------------------------------------------
# Scenario S3: empate en Pts+DG+GF, desempata H2H (verificación aritmética)
# ---------------------------------------------------------------------------


def test_s3_tie_broken_by_head_to_head():
    """S3: B y C empatados en Pts=4, DG=0, GF=2; B>C por H2H (B 1-0 C → 3 pts H2H).

    Aritmética:
      A: pts=5 dg=+1 (no empate)
      B: pts=4 dg=0 gf=2  — H2H vs C: 3 pts  ← B 2do
      C: pts=4 dg=0 gf=2  — H2H vs B: 0 pts  ← C 3ro
      D: pts=2 dg=-1 (no empate)
    """
    results = [
        _mr("A", "B", 1, 0),
        _mr("A", "C", 1, 1),
        _mr("A", "D", 0, 0),
        _mr("B", "C", 1, 0),
        _mr("B", "D", 1, 1),
        _mr("C", "D", 1, 0),
    ]
    table = compute_standings(_TEAMS_ABCD, results)

    assert [r.team_name for r in table] == ["A", "B", "C", "D"]
    # B antes que C
    b_pos = next(i for i, r in enumerate(table) if r.team_name == "B")
    c_pos = next(i for i, r in enumerate(table) if r.team_name == "C")
    assert b_pos < c_pos

    # Verificar estadísticas globales
    b = table[b_pos]
    assert b.pts == 4 and b.dg == 0 and b.gf == 2

    c = table[c_pos]
    assert c.pts == 4 and c.dg == 0 and c.gf == 2


# ---------------------------------------------------------------------------
# Scenario S4: 0 partidos terminados → 4 equipos, todo en 0, orden alfabético
# ---------------------------------------------------------------------------


def test_s4_zero_finished_matches_returns_alphabetical():
    """S4: sin resultados → lista de 4 con todo en 0, ordenada alfabe ́ticamente."""
    table = compute_standings(_TEAMS_ABCD, [])

    assert len(table) == 4
    assert [r.team_name for r in table] == ["A", "B", "C", "D"]
    for row in table:
        assert row.pj == 0
        assert row.g == 0
        assert row.e == 0
        assert row.p == 0
        assert row.gf == 0
        assert row.gc == 0
        assert row.dg == 0
        assert row.pts == 0


# ---------------------------------------------------------------------------
# Scenario S5: triple empate que cae a nombre alfabe ́tico
#
# Setup: A gana todos. X, Y, Z empatan entre sí 1-1.
# Global: X=Y=Z con pts=2, dg=-3, gf=2
# H2H X vs Y vs Z: cada par 1-1, todos pts=2 H2H dg=0 gf=2 → sin resolución → alfa
# Esperado orden H2H: X < Y < Z
# ---------------------------------------------------------------------------

_TEAMS_AXYZ = [
    TeamRef(team_id=10, name="A"),
    TeamRef(team_id=11, name="X"),
    TeamRef(team_id=12, name="Y"),
    TeamRef(team_id=13, name="Z"),
]

_ID_XYZ = {t.name: t.team_id for t in _TEAMS_AXYZ}


def _mr2(h: str, a: str, hg: int, ag: int) -> MatchResult:
    return MatchResult(home_id=_ID_XYZ[h], away_id=_ID_XYZ[a], home_score=hg, away_score=ag)


def test_s5_triple_tie_falls_to_alphabetical():
    """S5: X=Y=Z con stats idénticas incluso en H2H → orden alfa X<Y<Z."""
    results = [
        _mr2("A", "X", 3, 0),
        _mr2("A", "Y", 3, 0),
        _mr2("A", "Z", 3, 0),
        _mr2("X", "Y", 1, 1),
        _mr2("Y", "Z", 1, 1),
        _mr2("Z", "X", 1, 1),
    ]
    table = compute_standings(_TEAMS_AXYZ, results)

    # A primero (9 pts), luego X < Y < Z alfabéticamente
    assert table[0].team_name == "A"
    assert [r.team_name for r in table[1:]] == ["X", "Y", "Z"]
