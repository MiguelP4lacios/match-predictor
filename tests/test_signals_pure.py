"""Tests puros para de-vig, EV y ¼-Kelly (sin BD).

Spec: value-signals — Req: Proportional De-Vig, EV and Edge, ¼-Kelly Stake
TDD RED: fallan hasta que probabilities.py exista.
"""


from app.model.probabilities import compute_ev, devig_proportional, kelly_quarter

# ---------------------------------------------------------------------------
# SC-VS-01: De-vig proporcional numérico
# H=2.16, D=3.24, A=3.39
# raw = (1/2.16, 1/3.24, 1/3.39) = (0.4630, 0.3086, 0.2950)
# overround = 1.0666
# fair = (0.4341, 0.2894, 0.2765)
# ---------------------------------------------------------------------------


def test_devig_home_probability():
    """SC-VS-01: p_fair_H ≈ 0.4341 para cuotas 2.16/3.24/3.39."""
    fair = devig_proportional(h_odds=2.16, d_odds=3.24, a_odds=3.39)
    assert abs(fair["home"] - 0.4341) < 0.0001


def test_devig_draw_probability():
    """SC-VS-01: p_fair_D ≈ 0.2894 para cuotas 2.16/3.24/3.39."""
    fair = devig_proportional(h_odds=2.16, d_odds=3.24, a_odds=3.39)
    assert abs(fair["draw"] - 0.2894) < 0.0001


def test_devig_away_probability():
    """SC-VS-01: p_fair_A ≈ 0.2765 para cuotas 2.16/3.24/3.39."""
    fair = devig_proportional(h_odds=2.16, d_odds=3.24, a_odds=3.39)
    assert abs(fair["away"] - 0.2765) < 0.0001


def test_devig_sums_to_one():
    """De-vig proporcional: suma exacta = 1.0 dentro de 1e-9."""
    fair = devig_proportional(h_odds=2.16, d_odds=3.24, a_odds=3.39)
    total = fair["home"] + fair["draw"] + fair["away"]
    assert abs(total - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# SC-VS-02: EV numérico
# p_model=0.40, decimal_odds=3.39
# EV = 0.40×2.39 − 0.60 = 0.956 − 0.60 = 0.3560
# ---------------------------------------------------------------------------


def test_ev_numeric_verification():
    """SC-VS-02: EV ≈ 0.3560 para p_model=0.40, odds=3.39."""
    ev = compute_ev(p_model=0.40, decimal_odds=3.39)
    assert abs(ev - 0.3560) < 0.0001


def test_ev_negative_when_underdog_with_bad_odds():
    """Triangulación SC-VS-02: EV negativo cuando p_model < fair_p implícita."""
    # p=0.30, odds=2.50 → EV = 0.30×1.50 − 0.70 = 0.45 − 0.70 = -0.25
    ev = compute_ev(p_model=0.30, decimal_odds=2.50)
    assert ev < 0.0


# ---------------------------------------------------------------------------
# SC-VS-03: ¼-Kelly numérico
# p_model=0.40, decimal_odds=3.39
# full_kelly = (0.40×3.39−1)/(3.39−1) = 0.356/2.39 = 0.1490
# kelly_fraction = 0.25 × 0.1490 = 0.0372
# ---------------------------------------------------------------------------


def test_kelly_quarter_numeric():
    """SC-VS-03: kelly_fraction ≈ 0.0372 para p_model=0.40, odds=3.39."""
    kf = kelly_quarter(p_model=0.40, decimal_odds=3.39)
    assert abs(kf - 0.0372) < 0.0001


# ---------------------------------------------------------------------------
# SC-VS-04: Kelly negativo → floor a 0.0
# p_model=0.30, decimal_odds=2.50, p_fair=0.38 → edge=−0.08
# full_kelly = (0.30×2.50−1)/(2.50−1) = (0.75−1)/1.50 = −0.1667 → floor 0
# ---------------------------------------------------------------------------


def test_kelly_floors_to_zero_when_negative():
    """SC-VS-04: kelly_fraction = 0.0 cuando edge < 0."""
    kf = kelly_quarter(p_model=0.30, decimal_odds=2.50)
    assert kf == 0.0
