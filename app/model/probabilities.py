"""Núcleo puro de probabilidades 1X2: OLM, baseline binado, de-vig, EV, ¼-Kelly.

Funciones PURAS: sin BD, sin estado global, sin LLM. Testeables directamente.

OLM (Ordinal Logistic Model) — proportional-odds:
  logit(P(Y ≤ 0)) = α₀ − β₁·diff − β₂·neutral  (Y=0: away win)
  logit(P(Y ≤ 1)) = α₁ − β₁·diff − β₂·neutral  (Y=1: draw)
  P(A) = σ(logit₀), P(D) = σ(logit₁) − σ(logit₀), P(H) = 1 − σ(logit₁)

Reparametrización de cutpoints: α₁ = a1, α₂ = a1 + exp(δ)
  Garantiza α₁ < α₂ sin restricciones en el optimizador.
"""

import math
from typing import TypedDict

# ---------------------------------------------------------------------------
# Excepciones de dominio
# ---------------------------------------------------------------------------


class NoSupportError(Exception):
    """Bucket con soporte insuficiente (count < min_support)."""


class BacktestRequiredError(Exception):
    """El modelo activo no tiene reporte de backtest en params_json."""


class BacktestGateError(Exception):
    """El backtest no superó ambos baselines — señales bloqueadas."""


# ---------------------------------------------------------------------------
# Tipos auxiliares
# ---------------------------------------------------------------------------


class Probs(TypedDict):
    home: float
    draw: float
    away: float


# ---------------------------------------------------------------------------
# OLM: función sigmoide y predicción de probabilidades
# ---------------------------------------------------------------------------


def _sigmoid(x: float) -> float:
    """Función sigmoide robusta (sin overflow para |x| grande)."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    ex = math.exp(x)
    return ex / (1.0 + ex)


def predict_proba(params: dict, elo_diff: float, neutral: bool) -> Probs:
    """Calcula P(H), P(D), P(A) vía OLM con reparam α₂ = α₁ + exp(δ).

    Args:
        params: dict con keys ``cutpoints.a1``, ``cutpoints.delta``,
                ``beta_diff``, ``beta_neutral``.
        elo_diff: diferencia de Elo ajustada por home advantage
                  (home_adj_rating − away_rating, con +100 si es local).
        neutral: True si el partido es en sede neutral.

    Returns:
        Probs con ``home``, ``draw``, ``away`` que suman 1.0.
    """
    cp = params["cutpoints"]
    a1: float = cp["a1"]
    a2: float = a1 + math.exp(cp["delta"])  # reparam: garantiza a2 > a1
    beta_diff: float = params["beta_diff"]
    beta_neutral: float = params["beta_neutral"]

    linear = beta_diff * elo_diff + beta_neutral * float(neutral)

    logit0 = a1 - linear  # P(Y ≤ 0) → P(away win or less)
    logit1 = a2 - linear  # P(Y ≤ 1) → P(draw or less)

    p_le0 = _sigmoid(logit0)  # P(A)
    p_le1 = _sigmoid(logit1)  # P(A) + P(D)

    p_away = p_le0
    p_draw = p_le1 - p_le0
    p_home = 1.0 - p_le1

    return Probs(home=p_home, draw=p_draw, away=p_away)


# ---------------------------------------------------------------------------
# Baseline binado: tabla empírica de draw-rate por bucket
# ---------------------------------------------------------------------------


def predict_baseline(
    table: list[dict],
    abs_diff: float,
    min_support: int = 300,
) -> float:
    """Devuelve el draw-rate empírico para |elo_diff| según tabla de buckets.

    Args:
        table: lista de dicts con keys ``bucket_low``, ``bucket_high``,
               ``draw_rate``, ``count``.
        abs_diff: |elo_diff| del partido.
        min_support: umbral mínimo de observaciones en el bucket.

    Returns:
        draw_rate (float) del bucket que contiene abs_diff.

    Raises:
        NoSupportError: si el bucket tiene count < min_support.
    """
    # Buscar el bucket que contiene abs_diff
    for bucket in table:
        if bucket["bucket_low"] <= abs_diff <= bucket["bucket_high"]:
            if bucket["count"] < min_support:
                raise NoSupportError(
                    f"Bucket [{bucket['bucket_low']},{bucket['bucket_high']}] "
                    f"tiene count={bucket['count']} < min_support={min_support}"
                )
            return float(bucket["draw_rate"])

    # Si abs_diff está fuera del rango de la tabla, usar el último bucket
    last = table[-1]
    if last["count"] < min_support:
        raise NoSupportError(
            f"Bucket [{last['bucket_low']},{last['bucket_high']}] "
            f"tiene count={last['count']} < min_support={min_support}"
        )
    return float(last["draw_rate"])


# ---------------------------------------------------------------------------
# De-vig proporcional sobre el triple 1X2
# ---------------------------------------------------------------------------


def devig_proportional(h_odds: float, d_odds: float, a_odds: float) -> Probs:
    """Convierte cuotas decimales a probabilidades justas (método proporcional).

    fair_p_i = (1/odds_i) / Σ(1/odds_j)

    Args:
        h_odds: cuota decimal HOME.
        d_odds: cuota decimal DRAW.
        a_odds: cuota decimal AWAY.

    Returns:
        Probs con ``home``, ``draw``, ``away`` que suman 1.0.
    """
    raw_h = 1.0 / h_odds
    raw_d = 1.0 / d_odds
    raw_a = 1.0 / a_odds
    total = raw_h + raw_d + raw_a

    return Probs(
        home=raw_h / total,
        draw=raw_d / total,
        away=raw_a / total,
    )


# ---------------------------------------------------------------------------
# EV y ¼-Kelly
# ---------------------------------------------------------------------------


def compute_ev(p_model: float, decimal_odds: float) -> float:
    """Valor esperado por unidad apostada.

    EV = p_model × (decimal_odds − 1) − (1 − p_model)

    Args:
        p_model: probabilidad estimada por el modelo.
        decimal_odds: mejor cuota decimal disponible.

    Returns:
        EV como float (positivo = valor esperado positivo).
    """
    return p_model * (decimal_odds - 1.0) - (1.0 - p_model)


def kelly_quarter(p_model: float, decimal_odds: float) -> float:
    """Fracción de Kelly al 25%.

    kelly_fraction = 0.25 × max(0, (p_model × odds − 1) / (odds − 1))

    Args:
        p_model: probabilidad estimada por el modelo.
        decimal_odds: mejor cuota decimal disponible.

    Returns:
        Fracción del bankroll a apostar (≥ 0.0).
    """
    numerator = p_model * decimal_odds - 1.0
    if numerator <= 0.0:
        return 0.0
    denominator = decimal_odds - 1.0
    full_kelly = numerator / denominator
    return 0.25 * full_kelly
