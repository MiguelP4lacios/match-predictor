"""Ajuste del OLM 1X2 por máxima verosimilitud (MLE).

Requiere scipy/numpy. Usa la misma reparametrización que probabilities.py:
  α₁ = a1, α₂ = a1 + exp(δ)  →  garantiza α₁ < α₂ sin constraints.

Función objetivo: neg-log-likelihood del modelo ordinal logístico sobre
la variable de resultado 0=away, 1=draw, 2=home.

`build_binned_table` construye la tabla empírica de draw-rate por bucket
de 50 puntos de |elo_diff|. Solo incluye buckets con count ≥ min_support.
"""

import math
from typing import Any

import numpy as np
from scipy.optimize import minimize

# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _sigmoid(x: np.ndarray | float) -> np.ndarray | float:
    """Sigmoide vectorizada compatible con numpy y escalares."""
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


def _neg_log_likelihood(
    theta: np.ndarray,
    diffs: np.ndarray,
    neutrals: np.ndarray,
    outcomes: np.ndarray,
) -> float:
    """Neg-log-likelihood del OLM para optimización.

    theta = [a1, delta, beta_diff, beta_neutral]
    outcome: 0=away, 1=draw, 2=home
    """
    a1, delta, beta_diff, beta_neutral = theta
    a2 = a1 + math.exp(delta)  # reparam: garantiza a2 > a1

    linear = beta_diff * diffs + beta_neutral * neutrals

    logit0 = a1 - linear
    logit1 = a2 - linear

    p_le0 = _sigmoid(logit0)  # P(away)
    p_le1 = _sigmoid(logit1)  # P(away) + P(draw)

    p_away = p_le0
    p_draw = p_le1 - p_le0
    p_home = 1.0 - p_le1

    # Clip para evitar log(0)
    eps = 1e-12
    p_away = np.clip(p_away, eps, 1.0)
    p_draw = np.clip(p_draw, eps, 1.0)
    p_home = np.clip(p_home, eps, 1.0)

    ll = np.where(
        outcomes == 0, np.log(p_away), np.where(outcomes == 1, np.log(p_draw), np.log(p_home))
    )
    return -float(np.sum(ll))


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def fit_olm(matches_df) -> dict[str, Any]:
    """Ajusta el OLM por MLE sobre un DataFrame de partidos.

    Args:
        matches_df: pandas DataFrame con columnas:
            - ``elo_diff``: diferencia de Elo ajustada (home_adj - away).
            - ``neutral``: bool / int (0/1).
            - ``outcome``: int (0=away, 1=draw, 2=home).

    Returns:
        dict con keys ``cutpoints.a1``, ``cutpoints.delta``,
        ``beta_diff``, ``beta_neutral``, ``train_n``.
    """
    import pandas as pd  # noqa: F401

    diffs = matches_df["elo_diff"].to_numpy(dtype=float)
    neutrals = matches_df["neutral"].to_numpy(dtype=float)
    outcomes = matches_df["outcome"].to_numpy(dtype=int)

    # Valores iniciales razonables (α₁≈-0.5, δ≈log(1.3), β_diff≈0.004)
    theta0 = np.array([-0.5, math.log(1.3), 0.004, -0.3])

    result = minimize(
        _neg_log_likelihood,
        theta0,
        args=(diffs, neutrals, outcomes),
        method="L-BFGS-B",
        options={"maxiter": 500, "ftol": 1e-10},
    )

    if not result.success:
        import warnings

        warnings.warn(f"OLM minimize no convergió: {result.message}", stacklevel=2)

    a1, delta, beta_diff, beta_neutral = result.x

    return {
        "model": "A-olm",
        "cutpoints": {
            "a1": float(a1),
            "delta": float(delta),
        },
        "beta_diff": float(beta_diff),
        "beta_neutral": float(beta_neutral),
        "fit": {
            "train_n": int(len(diffs)),
            "converged": bool(result.success),
            "neg_log_likelihood": float(result.fun),
        },
    }


def build_binned_table(
    matches_df,
    min_support: int = 300,
    bucket_size: int = 50,
) -> list[dict]:
    """Construye tabla empírica de draw-rate por bucket de |elo_diff|.

    Solo incluye buckets con count ≥ min_support.

    Args:
        matches_df: pandas DataFrame con ``elo_diff`` y ``outcome`` (0/1/2).
        min_support: mínimo de partidos por bucket para incluirlo.
        bucket_size: amplitud del bucket en puntos Elo.

    Returns:
        Lista de dicts: [{bucket_low, bucket_high, draw_rate, count}, …]
        ordenada por bucket_low ascendente.
    """

    abs_diff = matches_df["elo_diff"].abs().to_numpy(dtype=float)
    is_draw = (matches_df["outcome"] == 1).to_numpy(dtype=bool)

    max_diff = int(abs_diff.max()) + bucket_size
    edges = list(range(0, max_diff + bucket_size, bucket_size))

    table = []
    for i in range(len(edges) - 1):
        low, high = edges[i], edges[i + 1] - 1
        mask = (abs_diff >= low) & (abs_diff <= high)
        count = int(mask.sum())
        if count < min_support:
            continue
        draw_rate = float(is_draw[mask].mean())
        table.append(
            {
                "bucket_low": low,
                "bucket_high": high,
                "draw_rate": draw_rate,
                "count": count,
            }
        )

    return table


def to_params(olm_params: dict, binned_table: list[dict]) -> dict:
    """Combina params OLM + tabla binada en el formato de params_json.

    Returns:
        dict listo para persistir en ModelVersion.params_json.
    """
    return {
        **olm_params,
        "binned_table": binned_table,
        "devig": {"method": "proportional"},
        "thresholds": {
            "edge_min": 0.03,
            "kelly_fraction": 0.25,
            "min_bucket_support": 300,
            "bankroll": 1000,
        },
    }
