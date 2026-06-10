"""Tests de integración para el gate y señales (usa db_session con SAVEPOINT).

Spec: value-signals — Req: Honesty Gate, Signal Emission Gate, Idempotency
Spec: model-1x2 — Req: Walk-Forward Backtest with Gate
TDD RED: fallan hasta que signals.py y backtest_1x2.py existan.
"""

import datetime

import pytest
from sqlalchemy import func, select

from app.model.probabilities import BacktestGateError, BacktestRequiredError
from app.models import (
    BetLog,
    Competition,
    Match,
    ModelVersion,
    Odds,
    Prediction,
    Team,
    ValueSignal,
)
from app.models.enums import BetMode, CompetitionKind, MarketType, MatchStatus

# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------


def _setup_eligible_model(session, name: str = "1x2-olm-v1-gate-test") -> ModelVersion:
    """ModelVersion con backtest.beats_baselines=True."""
    mv = ModelVersion(
        name=name,
        params_json={
            "model": "A-olm",
            "cutpoints": {"a1": -0.50, "delta": 1.0},
            "beta_diff": 0.004,
            "beta_neutral": -0.30,
            "backtest": {
                "brier": 0.210,
                "logloss": 1.02,
                "baselines": {"uniform": 0.2222, "binned": 0.215},
                "beats_baselines": True,
                "eval_n": 1000,
                "eval_window": "2018-2026",
            },
            "thresholds": {
                "edge_min": 0.03,
                "kelly_fraction": 0.25,
                "min_bucket_support": 300,
                "bankroll": 1000,
            },
        },
    )
    session.add(mv)
    session.flush()
    return mv


def _setup_match_and_prediction(
    session, model_version: ModelVersion, p_model: float = 0.40
):
    """Crea competición, equipos, partido y predicción mínimos."""
    comp = Competition(name="Gate Test WC", kind=CompetitionKind.WORLD_CUP)
    session.add(comp)
    session.flush()

    home = Team(name="GateHome")
    away = Team(name="GateAway")
    session.add_all([home, away])
    session.flush()

    match = Match(
        competition_id=comp.id,
        match_date=datetime.date(2026, 6, 20),
        home_team_id=home.id,
        away_team_id=away.id,
        neutral_site=False,
        status=MatchStatus.SCHEDULED,
        went_to_extra_time=False,
        went_to_penalties=False,
    )
    session.add(match)
    session.flush()

    pred = Prediction(
        match_id=match.id,
        model_version_id=model_version.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code="HOME",
        probability=p_model,
        low_confidence=False,
    )
    session.add(pred)
    session.flush()
    return match, pred


def _setup_odds(session, match, decimal_odds: float = 3.39) -> Odds:
    """Crea una fila de odds para el partido (solo HOME — para tests sin emisión)."""
    o = Odds(
        match_id=match.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code="HOME",
        bookmaker="TestBook",
        decimal_odds=decimal_odds,
        captured_at=datetime.datetime(2026, 6, 19, 12, 0),
        is_closing=False,
    )
    session.add(o)
    session.flush()
    return o


def _setup_odds_triple(
    session,
    match,
    h_odds: float = 2.16,
    d_odds: float = 3.24,
    a_odds: float = 3.39,
) -> tuple[Odds, Odds, Odds]:
    """Crea el triple H/D/A de odds (necesario para de-vig proporcional)."""
    now = datetime.datetime(2026, 6, 19, 12, 0)
    rows = []
    for code, odds_val in [("HOME", h_odds), ("DRAW", d_odds), ("AWAY", a_odds)]:
        o = Odds(
            match_id=match.id,
            market_type=MarketType.MATCH_1X2,
            outcome_code=code,
            bookmaker="TestBook",
            decimal_odds=odds_val,
            captured_at=now,
            is_closing=False,
        )
        session.add(o)
        rows.append(o)
    session.flush()
    return tuple(rows)


# ---------------------------------------------------------------------------
# SC-VS-07: params_json={} → BacktestRequiredError
# ---------------------------------------------------------------------------


def test_gate_raises_backtest_required_when_no_backtest_key(db_session):
    """SC-VS-07: params_json sin clave backtest → BacktestRequiredError."""
    from app.model.signals import generate_signals

    mv = ModelVersion(name="1x2-no-backtest", params_json={})
    db_session.add(mv)
    db_session.flush()

    with pytest.raises(BacktestRequiredError):
        generate_signals(db_session, model_version_id=mv.id)


# ---------------------------------------------------------------------------
# SC-OLM-07: Brier ≥ 0.2222 → BacktestGateError con métricas en el mensaje
# ---------------------------------------------------------------------------


def test_gate_raises_backtest_gate_error_when_brier_too_high(db_session):
    """SC-OLM-07: beats_baselines=False → BacktestGateError con métricas."""
    from app.model.signals import generate_signals

    mv = ModelVersion(
        name="1x2-failed-backtest",
        params_json={
            "model": "A-olm",
            "backtest": {
                "brier": 0.225,
                "logloss": 1.10,
                "beats_baselines": False,
            },
        },
    )
    db_session.add(mv)
    db_session.flush()

    with pytest.raises(BacktestGateError) as exc_info:
        generate_signals(db_session, model_version_id=mv.id)

    # El mensaje debe contener las métricas
    msg = str(exc_info.value)
    assert "0.225" in msg or "brier" in msg.lower()


# ---------------------------------------------------------------------------
# SC-VS-05: edge=0.02 → no se inserta value_signal
# ---------------------------------------------------------------------------


def test_signal_below_threshold_not_emitted(db_session):
    """SC-VS-05: edge=0.02 < edge_min=0.03 → 0 filas en value_signal."""
    from app.model.signals import generate_signals

    mv = _setup_eligible_model(db_session, name="1x2-olm-vs05")
    match, pred = _setup_match_and_prediction(db_session, mv, p_model=0.40)

    # odds tal que fair_p ≈ 0.38 → edge = 0.40 - 0.38 = 0.02 (< 0.03)
    # Para fair_p ≈ 0.38: si odds ≈ 2.63 → 1/2.63 = 0.380
    # Usamos un triple donde la fair_p del HOME queda en ~0.38
    _setup_odds(db_session, match, decimal_odds=2.63)

    generate_signals(db_session, model_version_id=mv.id, match_id=match.id)

    count = db_session.scalar(select(func.count(ValueSignal.id)))
    assert count == 0


# ---------------------------------------------------------------------------
# SC-VS-06: edge=0.05 + modelo elegible → value_signal + BetLog PAPER
# ---------------------------------------------------------------------------


def test_signal_above_threshold_emitted_as_paper(db_session):
    """SC-VS-06: edge=0.05 y modelo elegible → 1 value_signal + BetLog PAPER.

    p_model=0.40, odds H=2.16/D=3.24/A=3.39 → fair_p_H≈0.4341 (del de-vig).
    edge_HOME = 0.40 - 0.4341 = -0.034 (negativo). Para asegurar edge > 0.03 en HOME:
    usamos odds H=5.00/D=3.50/A=2.50 → fair_p_H ≈ 1/(5.00) / (1/5+1/3.5+1/2.5)
    = 0.20 / (0.20+0.286+0.40) = 0.20/0.886 ≈ 0.226.
    p_model=0.40, fair_p=0.226 → edge=0.174 (bien por encima del 0.03).
    """
    from app.model.signals import generate_signals

    mv = _setup_eligible_model(db_session, name="1x2-olm-vs06")
    match, pred = _setup_match_and_prediction(db_session, mv, p_model=0.40)
    # Triple con fair_p_HOME bajo → edge positivo para HOME
    h_row, d_row, a_row = _setup_odds_triple(
        db_session, match, h_odds=5.00, d_odds=3.50, a_odds=2.50
    )

    generate_signals(db_session, model_version_id=mv.id, match_id=match.id)

    vs_count = db_session.scalar(select(func.count(ValueSignal.id)))
    assert vs_count == 1

    vs = db_session.scalar(select(ValueSignal))
    assert vs is not None
    assert vs.odds_id == h_row.id
    assert vs.prediction_id == pred.id

    bet_log = db_session.scalar(select(BetLog).where(BetLog.value_signal_id == vs.id))
    assert bet_log is not None
    assert bet_log.mode == BetMode.PAPER


# ---------------------------------------------------------------------------
# SC-VS-08: Re-run (prediction_id=42, odds_id=77) → no new row (idempotencia)
# ---------------------------------------------------------------------------


def test_signal_idempotent_on_rerun(db_session):
    """SC-VS-08: re-run produce 0 nuevas filas en value_signal."""
    from app.model.signals import generate_signals

    mv = _setup_eligible_model(db_session, name="1x2-olm-vs08")
    match, pred = _setup_match_and_prediction(db_session, mv, p_model=0.40)
    # Triple necesario para de-vig + edge positivo en HOME
    _setup_odds_triple(db_session, match, h_odds=5.00, d_odds=3.50, a_odds=2.50)

    generate_signals(db_session, model_version_id=mv.id, match_id=match.id)
    count_after_first = db_session.scalar(select(func.count(ValueSignal.id)))

    # Segunda ejecución
    generate_signals(db_session, model_version_id=mv.id, match_id=match.id)
    count_after_second = db_session.scalar(select(func.count(ValueSignal.id)))

    assert count_after_first == count_after_second
    assert count_after_first >= 1  # La primera corrida sí emitió señal
