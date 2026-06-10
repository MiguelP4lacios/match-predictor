"""Backtest walk-forward del OLM 1X2.

Barrido cronológico en memoria (anti-look-ahead inherente):
  - fit: match_date < cutoff (defecto 2018-06-01)
  - eval: match_date >= cutoff

Métricas: Brier score, log-loss, tabla de calibración (10 bins).
Gate de honestidad: el OLM DEBE superar uniform(1/3) y binned en
AMBAS métricas (Brier y log-loss) para ser elegible.

Uniform Brier = 0.2222... (exactamente (1/3)·(2/3)²×2 + (1/3)·(1/3)²
= (1/3)·(4/9+4/9+4/9) = (1/3)·(4/3) = 4/9 ≈ 0.4444 — ERROR:
ver abajo para el cálculo correcto).

Brier score multiclase (regla de Brier estándar para K=3):
  BS = (1/N) Σᵢ Σₖ (p̂ᵢₖ − yᵢₖ)²

Para uniforme (1/3, 1/3, 1/3):
  BS_uniform = (1/3)·[(1/3-1)²+(1/3-0)²+(1/3-0)²]·3 = [4/9+1/9+1/9] = 6/9 = 2/3
  — esto tampoco es 0.2222. Usando la formulación "proper" (promedio por outcome):
  BS_proper = (1/N) Σᵢ Σₖ (yᵢₖ − p̂ᵢₖ)² / K
  No existe definición universal. El spec usa 0.2222 como upper-bound
  del Brier score OLM (si OLM ≥ 0.2222, no es mejor que uniforme).

Usamos la definición del spec: Brier de la clase predicha (estilo binario):
  BS = (1/N) Σᵢ (1 − p̂_correct_i)²   ← "probability of correct outcome"
  Para uniforme: (1/3)(2/3)² × 3 = (1/3)(4/9)×3 ... no.

Para simplificar y respetar el spec (upper-bound 0.2222 ≈ 2/9):
  Usamos Brier score "binario" de la probabilidad del resultado correcto:
  BS = (1/N) Σᵢ (1 − p_correct)²  → uniforme = (2/3)² = 4/9 ... tampoco.

El spec dice literalmente "Uniform Brier = 0.2222 (upper bound)". Con la
formulación estándar de Brier multiclase dividido por K=3:
  BS_uniform = (1/3)(4/9 + 1/9 + 1/9) = (1/3)(6/9) = 2/9 ≈ 0.2222 ✓

Usamos esta formulación: BS = (1/N·K) Σᵢ Σₖ (yᵢₖ − p̂ᵢₖ)²
"""

import math
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

TRAIN_CUTOFF = "2018-06-01"
BRIER_UNIFORM = 2.0 / 9.0  # ≈ 0.2222


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------


def brier_score(probs: np.ndarray, outcomes: np.ndarray) -> float:
    """Brier score multiclase dividido por K=3.

    Args:
        probs:    (N, 3) array de probabilidades [P(away), P(draw), P(home)].
        outcomes: (N,) array de int 0=away, 1=draw, 2=home.

    Returns:
        Brier score (menor = mejor). Uniforme ≈ 0.2222.
    """
    n = len(outcomes)
    one_hot = np.zeros((n, 3))
    one_hot[np.arange(n), outcomes] = 1.0
    return float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)) / 3.0)


def log_loss(probs: np.ndarray, outcomes: np.ndarray) -> float:
    """Log-loss multiclase.

    Args:
        probs:    (N, 3) array de probabilidades.
        outcomes: (N,) array de int.

    Returns:
        Log-loss (menor = mejor).
    """
    n = len(outcomes)
    eps = 1e-12
    p_correct = np.clip(probs[np.arange(n), outcomes], eps, 1.0)
    return float(-np.mean(np.log(p_correct)))


def calibration_table(probs: np.ndarray, outcomes: np.ndarray, n_bins: int = 10) -> list[dict]:
    """Tabla de calibración de 10 bins (predicted prob vs observed freq).

    Aplana todas las probabilidades individuales (N×3 → 3N puntos).

    Returns:
        Lista de dicts: [{bin_low, bin_high, mean_predicted, observed_freq, count}]
    """
    # Aplanar: cada fila de probs tiene 3 valores, con su outcome one-hot
    n = len(outcomes)
    one_hot = np.zeros((n, 3))
    one_hot[np.arange(n), outcomes] = 1.0

    flat_pred = probs.flatten()
    flat_obs = one_hot.flatten()

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    table = []
    for i in range(n_bins):
        mask = (flat_pred >= edges[i]) & (flat_pred < edges[i + 1])
        if i == n_bins - 1:
            mask = (flat_pred >= edges[i]) & (flat_pred <= edges[i + 1])
        count = int(mask.sum())
        if count == 0:
            continue
        table.append({
            "bin_low": round(float(edges[i]), 2),
            "bin_high": round(float(edges[i + 1]), 2),
            "mean_predicted": round(float(flat_pred[mask].mean()), 4),
            "observed_freq": round(float(flat_obs[mask].mean()), 4),
            "count": count,
        })
    return table


# ---------------------------------------------------------------------------
# Baselines en el conjunto de evaluación
# ---------------------------------------------------------------------------


def _brier_uniform(n: int) -> float:
    """Brier del uniforme 1/3 — constante 2/9 ≈ 0.2222."""
    return BRIER_UNIFORM


def _brier_binned(probs_binned: np.ndarray, outcomes: np.ndarray) -> float:
    return brier_score(probs_binned, outcomes)


def _logloss_uniform(outcomes: np.ndarray) -> float:
    """Log-loss del uniforme 1/3 — constante ln(3)."""
    return math.log(3.0)


def _logloss_binned(probs_binned: np.ndarray, outcomes: np.ndarray) -> float:
    return log_loss(probs_binned, outcomes)


# ---------------------------------------------------------------------------
# Gate de honestidad
# ---------------------------------------------------------------------------


class BacktestGateError(Exception):
    """OLM no supera ambos baselines en ambas métricas."""


def beats_baselines(metrics: dict) -> bool:
    """True si el OLM supera uniform y binned en Brier y log-loss.

    Args:
        metrics: dict devuelto por ``run_backtest``.

    Returns:
        True si todas las comparaciones favorecen al OLM.
    """
    brier_olm = metrics["brier"]
    ll_olm = metrics["logloss"]
    baselines = metrics["baselines"]

    return (
        brier_olm < baselines["uniform_brier"]
        and brier_olm < baselines["binned_brier"]
        and ll_olm < baselines["uniform_logloss"]
        and ll_olm < baselines["binned_logloss"]
    )


# ---------------------------------------------------------------------------
# Walk-forward backtest
# ---------------------------------------------------------------------------


def run_backtest(
    matches_df,
    params: dict,
    binned_table: list[dict],
    cutoff: str = TRAIN_CUTOFF,
) -> dict[str, Any]:
    """Barrido cronológico: fit < cutoff, eval >= cutoff.

    Args:
        matches_df: DataFrame con ``match_date`` (str o date), ``elo_diff``,
                    ``neutral``, ``outcome`` (0/1/2).
        params:     dict de params OLM (resultado de fit_olm).
        binned_table: tabla empírica de baseline binado.
        cutoff:     fecha de corte (ISO str). Default 2018-06-01.

    Returns:
        dict con brier, logloss, baselines, beats_baselines, calibration_table,
        eval_n, eval_window.

    Raises:
        BacktestGateError: si OLM no supera ambos baselines en ambas métricas.
    """
    import pandas as pd

    from app.model.probabilities import NoSupportError, predict_baseline, predict_proba

    df = matches_df.copy()
    df["match_date"] = pd.to_datetime(df["match_date"])
    cutoff_dt = pd.Timestamp(cutoff)

    eval_df = df[df["match_date"] >= cutoff_dt].copy()

    if len(eval_df) == 0:
        raise ValueError(f"No hay datos de evaluación (cutoff={cutoff})")

    diffs = eval_df["elo_diff"].to_numpy(dtype=float)
    neutrals = eval_df["neutral"].to_numpy(dtype=float)
    outcomes_arr = eval_df["outcome"].to_numpy(dtype=int)

    # Predicciones OLM en evaluación
    olm_probs = np.array([
        [
            predict_proba(params, elo_diff=d, neutral=bool(n))["away"],
            predict_proba(params, elo_diff=d, neutral=bool(n))["draw"],
            predict_proba(params, elo_diff=d, neutral=bool(n))["home"],
        ]
        for d, n in zip(diffs, neutrals, strict=True)
    ])

    # Predicciones del baseline binado
    binned_probs = []
    for d, n in zip(diffs, neutrals, strict=True):
        abs_d = abs(d)
        try:
            draw_rate = predict_baseline(binned_table, abs_d)
        except NoSupportError:
            draw_rate = 0.28  # fallback al promedio histórico aproximado
        # Distribuir el resto proporcional entre home y away según elo_diff
        rest = 1.0 - draw_rate
        # P(home) proporcional a σ(d/400)
        p_home_raw = 1.0 / (1.0 + math.exp(-d / 400.0))
        p_away_raw = 1.0 - p_home_raw
        total_raw = p_home_raw + p_away_raw
        p_home = rest * p_home_raw / total_raw
        p_away = rest * p_away_raw / total_raw
        # ajuste neutral
        if n:
            p_home = rest * 0.5
            p_away = rest * 0.5
        binned_probs.append([p_away, draw_rate, p_home])
    binned_probs_arr = np.array(binned_probs)

    # Métricas OLM
    brier_olm = brier_score(olm_probs, outcomes_arr)
    ll_olm = log_loss(olm_probs, outcomes_arr)

    # Métricas baselines
    brier_unif = _brier_uniform(len(outcomes_arr))
    ll_unif = _logloss_uniform(outcomes_arr)
    brier_bin = brier_score(binned_probs_arr, outcomes_arr)
    ll_bin = log_loss(binned_probs_arr, outcomes_arr)

    cal_table = calibration_table(olm_probs, outcomes_arr)

    eval_min = str(eval_df["match_date"].min().date())
    eval_max = str(eval_df["match_date"].max().date())

    metrics = {
        "brier": round(brier_olm, 6),
        "logloss": round(ll_olm, 6),
        "baselines": {
            "uniform_brier": round(brier_unif, 6),
            "binned_brier": round(brier_bin, 6),
            "uniform_logloss": round(ll_unif, 6),
            "binned_logloss": round(ll_bin, 6),
        },
        "beats_baselines": beats_baselines({
            "brier": brier_olm,
            "logloss": ll_olm,
            "baselines": {
                "uniform_brier": brier_unif,
                "binned_brier": brier_bin,
                "uniform_logloss": ll_unif,
                "binned_logloss": ll_bin,
            },
        }),
        "calibration_table": cal_table,
        "eval_n": int(len(eval_df)),
        "eval_window": f"{eval_min} → {eval_max}",
        "split": cutoff,
    }

    if not metrics["beats_baselines"]:
        raise BacktestGateError(
            f"OLM no supera los baselines: "
            f"brier={metrics['brier']:.6f} (uniform={brier_unif:.4f}, "
            f"binned={brier_bin:.4f}), "
            f"logloss={metrics['logloss']:.6f} (uniform={ll_unif:.4f}, "
            f"binned={ll_bin:.4f}). "
            "Señales bloqueadas."
        )

    return metrics
