"""Tests puros para app.model.probabilities (sin BD).

Spec: model-1x2 — Requirement: OLM Core
TDD RED: fallan hasta que probabilities.py exista.
"""

import math

from app.model.probabilities import predict_proba

# ---------------------------------------------------------------------------
# SC-OLM-01: Forward pass no-neutral
# α₀=-0.50, α₁=0.80, β₁=0.004, β₂=-0.30, diff=100, neutral=False
# logit₀ = -0.50 - 0.004·100 - (-0.30)·0 = -0.90
# logit₁ = 0.80 - 0.004·100 - (-0.30)·0 = +0.40
# P(A)=σ(-0.90)≈0.2891, P(D)=σ(0.40)−σ(-0.90)≈0.3096, P(H)=1-σ(0.40)≈0.4013
# ---------------------------------------------------------------------------

PARAMS_V1 = {
    "cutpoints": {"a1": -0.50, "delta": math.log(0.80 - (-0.50))},
    "beta_diff": 0.004,
    "beta_neutral": -0.30,
}
# a1 = -0.50, a2 = a1 + exp(delta) = -0.50 + exp(log(1.30)) = -0.50 + 1.30 = 0.80  ✓


def test_olm_forward_pass_nonneutral_p_away():
    """SC-OLM-01: P(A) ≈ 0.2891 para diff=100, neutral=False."""
    probs = predict_proba(PARAMS_V1, elo_diff=100, neutral=False)
    assert abs(probs["away"] - 0.2891) < 0.0001


def test_olm_forward_pass_nonneutral_p_draw():
    """SC-OLM-01: P(D) ≈ 0.3096 para diff=100, neutral=False."""
    probs = predict_proba(PARAMS_V1, elo_diff=100, neutral=False)
    assert abs(probs["draw"] - 0.3096) < 0.0001


def test_olm_forward_pass_nonneutral_p_home():
    """SC-OLM-01: P(H) ≈ 0.4013 para diff=100, neutral=False."""
    probs = predict_proba(PARAMS_V1, elo_diff=100, neutral=False)
    assert abs(probs["home"] - 0.4013) < 0.0001


def test_olm_sum_to_one():
    """Suma de probabilidades = 1.0 dentro de 1e-9."""
    probs = predict_proba(PARAMS_V1, elo_diff=100, neutral=False)
    total = probs["home"] + probs["draw"] + probs["away"]
    assert abs(total - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# SC-OLM-02: neutral=True → P(H) < P(H) no-neutral
# logit₀ = -0.60, logit₁ = 0.70
# P(A)=0.3543, P(D)=0.3139, P(H)=0.3318
# ---------------------------------------------------------------------------


def test_olm_neutral_flag_reduces_home_prob():
    """SC-OLM-02: neutral=True → P(H)=0.3318 < 0.4013."""
    probs_neutral = predict_proba(PARAMS_V1, elo_diff=100, neutral=True)
    probs_nonneutral = predict_proba(PARAMS_V1, elo_diff=100, neutral=False)
    assert abs(probs_neutral["home"] - 0.3318) < 0.0001
    assert probs_neutral["home"] < probs_nonneutral["home"]


def test_olm_neutral_sum_to_one():
    """neutral=True también suma 1.0."""
    probs = predict_proba(PARAMS_V1, elo_diff=100, neutral=True)
    total = probs["home"] + probs["draw"] + probs["away"]
    assert abs(total - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Reparam: exp(δ) garantiza α2 > α1 siempre (cutpoints ordenados)
# ---------------------------------------------------------------------------


def test_cutpoint_ordering_via_reparam():
    """exp(δ) reparam garantiza α2 > α1; no hace falta constraint en minimize."""
    probs = predict_proba(PARAMS_V1, elo_diff=0, neutral=False)
    # Si la reparam funciona correctamente, P(D) > 0 (los cutpoints están bien ordenados)
    assert probs["draw"] > 0.0
    assert probs["home"] > 0.0
    assert probs["away"] > 0.0


# ---------------------------------------------------------------------------
# Monotonicidad: P(H) sube y P(A) baja a medida que elo_diff aumenta
# ---------------------------------------------------------------------------

_DIFFS = [-300, -100, 0, 100, 300]


def test_p_home_monotone_increasing_with_elo_diff():
    """P(H) debe ser monótonamente creciente sobre el rango de elo_diff."""
    probs = [predict_proba(PARAMS_V1, elo_diff=d, neutral=False) for d in _DIFFS]
    homes = [p["home"] for p in probs]
    assert all(homes[i] < homes[i + 1] for i in range(len(homes) - 1))


def test_p_away_monotone_decreasing_with_elo_diff():
    """P(A) debe ser monótonamente decreciente sobre el rango de elo_diff."""
    probs = [predict_proba(PARAMS_V1, elo_diff=d, neutral=False) for d in _DIFFS]
    aways = [p["away"] for p in probs]
    assert all(aways[i] > aways[i + 1] for i in range(len(aways) - 1))
