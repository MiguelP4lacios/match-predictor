"""Tests TDD para app/model/montecarlo.py — Motor Monte Carlo WC2026.

Escenarios del spec (verbatim):
  MC1: knockout P(H)=0.45/P(D)=0.28/P(A)=0.27 → P(home_adv)=0.59/P(away_adv)=0.41
  MC2: seed=42 llamado dos veces → dicts byte-idénticos
  MC3: toy 2-grupos: sum(p_champion)∈[0.99,1.01] y equipo de Elo alto → p_champion mayor
  MC4: benchmark — elapsed < 15s en Docker (20k iteraciones)
"""

import time

import pytest

# ---------------------------------------------------------------------------
# MC1: fórmula P(home_adv) en knockout — test puro sin simulación
# ---------------------------------------------------------------------------


def test_mc1_knockout_proba_formula():
    """MC1: P(home_adv) = P(H) + 0.5*P(D); con P(H)=0.45, P(D)=0.28, P(A)=0.27."""
    from app.model.montecarlo import knockout_prob

    p_home_adv = knockout_prob(p_home=0.45, p_draw=0.28, p_away=0.27)
    assert abs(p_home_adv - 0.59) < 1e-9, f"Esperado 0.59, obtenido {p_home_adv}"

    p_away_adv = 1.0 - p_home_adv
    assert abs(p_away_adv - 0.41) < 1e-9, f"Esperado 0.41, obtenido {p_away_adv}"


# ---------------------------------------------------------------------------
# MC2: reproducibilidad — seed=42 dos veces → dicts idénticos
# ---------------------------------------------------------------------------


def test_mc2_seed_42_is_reproducible():
    """MC2: simulate_tournament con seed=42 produce resultados byte-idénticos."""
    from app.model.montecarlo import simulate_tournament
    from app.model.standings import MatchResult

    # Parámetros mínimos del OLM (valores plausibles)
    params = {
        "cutpoints": {"a1": 0.4, "delta": 0.6},
        "beta_diff": 0.003,
        "beta_neutral": -0.1,
    }

    groups = {
        "A": [1, 2, 3, 4],
        "B": [5, 6, 7, 8],
    }
    elo_ratings = {i: 1700.0 if i == 1 else 1500.0 for i in range(1, 9)}

    result1 = simulate_tournament(
        groups=groups,
        elo_ratings=elo_ratings,
        model_params=params,
        completed_results={},
        n_iterations=500,
        seed=42,
    )
    result2 = simulate_tournament(
        groups=groups,
        elo_ratings=elo_ratings,
        model_params=params,
        completed_results={},
        n_iterations=500,
        seed=42,
    )

    assert result1 == result2, "Los resultados con seed=42 deben ser idénticos"


# ---------------------------------------------------------------------------
# MC3: toy 2-grupos — suma de p_champion ≈ 1.0 y Elo alto → mayor p_champion
# ---------------------------------------------------------------------------

# Params OLM plausibles (igual a MC2)
_PARAMS = {
    "cutpoints": {"a1": 0.4, "delta": 0.6},
    "beta_diff": 0.003,
    "beta_neutral": -0.1,
}

# Equipo 1 tiene Elo muy superior (2200 vs 1500 del resto)
_GROUPS = {
    "A": [1, 2, 3, 4],
    "B": [5, 6, 7, 8],
}
_ELO = {1: 2200.0, **{i: 1500.0 for i in [2, 3, 4, 5, 6, 7, 8]}}


def test_mc3a_sum_p_champion_near_one():
    """MC3a: sum(p_champion) sobre todos los equipos debe estar en [0.99, 1.01]."""
    from app.model.montecarlo import simulate_tournament

    result = simulate_tournament(
        groups=_GROUPS,
        elo_ratings=_ELO,
        model_params=_PARAMS,
        completed_results={},
        n_iterations=2000,
        seed=42,
    )

    total = sum(v["p_champion"] for v in result.values())
    assert 0.99 <= total <= 1.01, f"sum(p_champion)={total:.6f} fuera de [0.99, 1.01]"


def test_mc3b_stronger_elo_team_has_higher_p_champion():
    """MC3b: equipo con Elo=2200 debe tener p_champion mayor que cualquier equipo con Elo=1500."""
    from app.model.montecarlo import simulate_tournament

    result = simulate_tournament(
        groups=_GROUPS,
        elo_ratings=_ELO,
        model_params=_PARAMS,
        completed_results={},
        n_iterations=2000,
        seed=42,
    )

    p_strong = result[1]["p_champion"]  # equipo 1, Elo 2200
    p_others = [result[i]["p_champion"] for i in [2, 3, 4, 5, 6, 7, 8]]

    assert p_strong > max(p_others), (
        f"p_champion del equipo fuerte ({p_strong:.4f}) debe superar "
        f"a todos los débiles (max={max(p_others):.4f})"
    )


# ---------------------------------------------------------------------------
# MC4: benchmark — elapsed < 15s para 20k iteraciones en Docker
# ---------------------------------------------------------------------------


def test_mc4_benchmark_20k_iterations_under_15s():
    """MC4: simulate_tournament(n=20_000) debe completar en < 15 segundos."""
    from app.model.montecarlo import simulate_tournament

    params = _PARAMS
    groups = {
        "A": [1, 2, 3, 4],
        "B": [5, 6, 7, 8],
    }
    elo_ratings = {i: 1500.0 for i in range(1, 9)}

    start = time.perf_counter()
    simulate_tournament(
        groups=groups,
        elo_ratings=elo_ratings,
        model_params=params,
        completed_results={},
        n_iterations=20_000,
        seed=42,
    )
    elapsed = time.perf_counter() - start

    assert elapsed < 15.0, f"Benchmark falló: {elapsed:.2f}s ≥ 15s"
