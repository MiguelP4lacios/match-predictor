"""Tests puros para la baseline binada (predict_baseline / NoSupportError).

Spec: model-1x2 — Requirement: Binned Empirical Baseline
TDD RED: fallan hasta que probabilities.py exista.
"""

import pytest

from app.model.probabilities import NoSupportError, predict_baseline

# Tabla empírica de la spec (diff 0-49, 100-149, 200-249, 300-349, 450-499)
_EMPIRICAL_TABLE = [
    {"bucket_low": 0, "bucket_high": 49, "draw_rate": 0.296, "count": 500},
    {"bucket_low": 100, "bucket_high": 149, "draw_rate": 0.285, "count": 450},
    {"bucket_low": 200, "bucket_high": 249, "draw_rate": 0.251, "count": 420},
    {"bucket_low": 300, "bucket_high": 349, "draw_rate": 0.190, "count": 400},
    {"bucket_low": 450, "bucket_high": 499, "draw_rate": 0.111, "count": 380},
]


# ---------------------------------------------------------------------------
# SC-OLM-03: Monotonicidad del draw-rate empírico
# ---------------------------------------------------------------------------


def test_draw_rate_monotone_non_increasing():
    """SC-OLM-03: cada P(D) ≤ el anterior según diff creciente."""
    draw_rates = []
    for bucket in _EMPIRICAL_TABLE:
        # Llamamos con el centro del bucket
        mid = (bucket["bucket_low"] + bucket["bucket_high"]) / 2
        p = predict_baseline(_EMPIRICAL_TABLE, abs_diff=mid)
        draw_rates.append(p)

    for i in range(len(draw_rates) - 1):
        assert draw_rates[i] >= draw_rates[i + 1], (
            f"draw_rate[{i}]={draw_rates[i]:.4f} < draw_rate[{i+1}]={draw_rates[i+1]:.4f}"
        )


# ---------------------------------------------------------------------------
# SC-OLM-04: Bucket con soporte bajo → NoSupportError
# ---------------------------------------------------------------------------


def test_low_support_bucket_raises_no_support_error():
    """SC-OLM-04: count=150 < 300 → NoSupportError; no se devuelven probabilidades."""
    low_support_table = [
        {"bucket_low": 0, "bucket_high": 49, "draw_rate": 0.296, "count": 150},
    ]
    with pytest.raises(NoSupportError):
        predict_baseline(low_support_table, abs_diff=25)
