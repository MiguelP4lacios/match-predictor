"""Tests unitarios TDD para app/model/explain.py.

Cubre tres escenarios del spec signal-explanation:
  (a) Propiedad de reconciliación: cada raw canónico == columna persistida verbatim.
      p_fair == p_model − edge exactamente.
  (b) Escenario numérico: signal id=10 (datos reales de BD).
  (c) Fixture sintético triple incompleto → note presente, no excepción.

Todos los tests usan db_session (SAVEPOINT isolation) definido en conftest.py.
"""

import datetime
import decimal

import pytest
from sqlalchemy.orm import Session

# RED: fallan porque app/model/explain.py no existe todavía
from app.model.explain import Explanation, ExplainSection, ExplainStep, build_explanation
from app.models.betting import ValueSignal
from app.models.competition import Competition
from app.models.enums import CompetitionKind, MarketType, MatchStatus
from app.models.match import Match
from app.models.model import ModelVersion, Prediction
from app.models.odds import Odds
from app.models.team import Team


# ---------------------------------------------------------------------------
# Helpers de fixture sintéticos
# ---------------------------------------------------------------------------


def _make_competition(session: Session) -> Competition:
    c = Competition(name="Explain Test WC", kind=CompetitionKind.WORLD_CUP)
    session.add(c)
    session.flush()
    return c


def _make_teams(session: Session) -> tuple[Team, Team]:
    home = Team(name="EX_Home")
    away = Team(name="EX_Away")
    session.add_all([home, away])
    session.flush()
    return home, away


def _make_match(session: Session, comp: Competition, home: Team, away: Team) -> Match:
    m = Match(
        competition_id=comp.id,
        match_date=datetime.date(2025, 1, 15),
        home_team_id=home.id,
        away_team_id=away.id,
        neutral_site=False,
        status=MatchStatus.SCHEDULED,
        went_to_extra_time=False,
        went_to_penalties=False,
    )
    session.add(m)
    session.flush()
    return m


def _make_model_version(session: Session) -> ModelVersion:
    mv = ModelVersion(
        name="ex-test-v1",
        params_json={
            "backtest": {
                "brier": 0.1703,
                "eval_n": 1000,
                "logloss": 0.8699,
                "baselines": {
                    "uniform_brier": 0.2222,
                    "binned_brier": 0.1887,
                    "uniform_logloss": 1.0986,
                    "binned_logloss": 0.9614,
                },
                "beats_baselines": True,
            },
            "thresholds": {
                "bankroll": 1000,
                "kelly_fraction": 0.25,
            },
        },
    )
    session.add(mv)
    session.flush()
    return mv


def _make_prediction(
    session: Session, match: Match, mv: ModelVersion, probability: float = 0.65
) -> Prediction:
    p = Prediction(
        match_id=match.id,
        model_version_id=mv.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code="HOME",
        probability=probability,
        low_confidence=False,
        competition_id=match.competition_id,
    )
    session.add(p)
    session.flush()
    return p


def _make_odds_row(
    session: Session,
    match: Match,
    outcome_code: str,
    bookmaker: str,
    decimal_odds: float,
    captured_at: datetime.datetime,
) -> Odds:
    o = Odds(
        match_id=match.id,
        market_type=MarketType.MATCH_1X2,
        outcome_code=outcome_code,
        bookmaker=bookmaker,
        decimal_odds=decimal_odds,
        captured_at=captured_at,
        is_closing=False,
    )
    session.add(o)
    session.flush()
    return o


def _make_signal(
    session: Session,
    prediction: Prediction,
    odds: Odds,
    edge: float = 0.10,
    ev: float = 0.08,
    kelly_fraction: float = 0.05,
    recommended_stake: str = "50.00",
) -> ValueSignal:
    sig = ValueSignal(
        prediction_id=prediction.id,
        odds_id=odds.id,
        edge=decimal.Decimal(str(edge)),
        ev=decimal.Decimal(str(ev)),
        kelly_fraction=decimal.Decimal(str(kelly_fraction)),
        recommended_stake=decimal.Decimal(recommended_stake),
    )
    session.add(sig)
    session.flush()
    return sig


# ---------------------------------------------------------------------------
# Helpers de inspección de la explicación
# ---------------------------------------------------------------------------


def _find_section(explanation: Explanation, key: str) -> ExplainSection:
    """Busca sección por key o falla con mensaje claro."""
    s = next((s for s in explanation.sections if s.key == key), None)
    assert s is not None, f"Sección '{key}' no encontrada en {[s.key for s in explanation.sections]}"
    return s


def _find_step(section: ExplainSection, key: str) -> ExplainStep:
    """Busca step por key o falla con mensaje claro."""
    st = next((s for s in section.steps if s.key == key), None)
    assert st is not None, f"Step '{key}' no encontrado en {[s.key for s in section.steps]}"
    return st


# ---------------------------------------------------------------------------
# (a) Propiedad de reconciliación con datos sintéticos
# ---------------------------------------------------------------------------


def test_reconciliation_canonical_raws_match_persisted_columns(db_session):
    """Propiedad: cada raw canónico == columna persistida verbatim."""
    comp = _make_competition(db_session)
    home, away = _make_teams(db_session)
    match = _make_match(db_session, comp, home, away)
    mv = _make_model_version(db_session)
    pred = _make_prediction(db_session, match, mv, probability=0.72)
    captured_at = datetime.datetime(2025, 1, 14, 10, 0, 0)
    home_odds = _make_odds_row(db_session, match, "HOME", "BookTest", 1.90, captured_at)
    _make_odds_row(db_session, match, "DRAW", "BookTest", 3.50, captured_at)
    _make_odds_row(db_session, match, "AWAY", "BookTest", 4.20, captured_at)
    sig = _make_signal(
        db_session,
        pred,
        home_odds,
        edge=0.08500,
        ev=0.07000,
        kelly_fraction=0.04500,
        recommended_stake="45.00",
    )
    db_session.flush()

    explanation = build_explanation(db_session, sig.id)

    assert explanation is not None

    edge_section = _find_section(explanation, "edge")

    # p_model raw == prediction.probability verbatim
    p_model_step = _find_step(edge_section, "p_model")
    assert abs(float(p_model_step.raw) - float(pred.probability)) < 1e-6

    # edge raw == value_signal.edge verbatim
    edge_step = _find_step(edge_section, "edge")
    assert abs(float(edge_step.raw) - float(sig.edge)) < 1e-6

    # p_fair == p_model − edge EXACTAMENTE (derivado, no recalculado)
    p_fair_step = _find_step(edge_section, "p_fair_derived")
    expected_p_fair = float(pred.probability) - float(sig.edge)
    assert abs(float(p_fair_step.raw) - expected_p_fair) < 1e-9

    # stake: kelly_fraction raw == value_signal.kelly_fraction verbatim
    stake_section = _find_section(explanation, "stake")
    kf_step = _find_step(stake_section, "kelly_fraction")
    assert abs(float(kf_step.raw) - float(sig.kelly_fraction)) < 1e-6

    # recommended_stake raw == str(value_signal.recommended_stake)
    rs_step = _find_step(stake_section, "recommended_stake")
    assert rs_step.raw == str(sig.recommended_stake)


def test_reconciliation_p_fair_equals_p_model_minus_edge(db_session):
    """p_fair derivado = p_model − edge exactamente (segunda triangulación con valores distintos)."""
    comp = _make_competition(db_session)
    home, away = _make_teams(db_session)
    match = _make_match(db_session, comp, home, away)
    mv = _make_model_version(db_session)
    pred = _make_prediction(db_session, match, mv, probability=0.55)
    captured_at = datetime.datetime(2025, 1, 14, 10, 0, 0)
    home_odds = _make_odds_row(db_session, match, "HOME", "BookTest2", 2.10, captured_at)
    _make_odds_row(db_session, match, "DRAW", "BookTest2", 3.20, captured_at)
    _make_odds_row(db_session, match, "AWAY", "BookTest2", 3.80, captured_at)
    sig = _make_signal(
        db_session,
        pred,
        home_odds,
        edge=0.06000,
        ev=0.04000,
        kelly_fraction=0.02000,
        recommended_stake="20.00",
    )
    db_session.flush()

    explanation = build_explanation(db_session, sig.id)

    edge_section = _find_section(explanation, "edge")
    p_model_step = _find_step(edge_section, "p_model")
    edge_step = _find_step(edge_section, "edge")
    p_fair_step = _find_step(edge_section, "p_fair_derived")

    derived = float(p_model_step.raw) - float(edge_step.raw)
    assert abs(float(p_fair_step.raw) - derived) < 1e-9


# ---------------------------------------------------------------------------
# (b) Escenario numérico signal id=10 — datos reales de BD
# ---------------------------------------------------------------------------


def test_explain_signal_10_numerical_scenario(db_session):
    """Signal id=10: verifica valores numéricos verbatim del spec.

    p_model=0.83394, edge=0.14724, p_fair_derived=0.68670
    overround=0.99064, triple H=1.470 D=4.800 A=9.800
    |p_fair_reconstructed − p_fair_derived| ≤ 0.0001
    """
    explanation = build_explanation(db_session, 10)

    assert explanation is not None

    edge_section = _find_section(explanation, "edge")

    # p_model verbatim
    p_model_step = _find_step(edge_section, "p_model")
    assert abs(float(p_model_step.raw) - 0.83394) < 1e-5
    assert p_model_step.formatted is None  # front formatea

    # edge verbatim
    edge_step = _find_step(edge_section, "edge")
    assert abs(float(edge_step.raw) - 0.14724) < 1e-5
    assert edge_step.formatted is None  # front formatea

    # p_fair_derived = 0.83394 − 0.14724 = 0.68670
    p_fair_step = _find_step(edge_section, "p_fair_derived")
    assert abs(float(p_fair_step.raw) - 0.68670) < 1e-4
    assert p_fair_step.formatted is None  # front formatea

    # overround ilustrativo: 1/1.470 + 1/4.800 + 1/9.800 ≈ 0.99064
    overround_step = _find_step(edge_section, "overround")
    assert abs(float(overround_step.raw) - 0.99064) < 1e-4
    assert overround_step.formatted is not None  # intermedios → formatted

    # p_fair_reconstructed para HOME (ilustrativo): ≈ 0.68671
    pfr_step = _find_step(edge_section, "p_fair_reconstructed")
    assert abs(float(pfr_step.raw) - 0.68671) < 1e-4
    assert pfr_step.formatted is not None  # ilustrativo

    # Tolerancia de reconciliación: |reconstructed − derived| ≤ 0.0001
    recon_diff = abs(float(pfr_step.raw) - float(p_fair_step.raw))
    assert recon_diff <= 0.0001, f"Reconciliación fuera de tolerancia: {recon_diff}"

    # origen_p_model: elo_home y elo_away
    origen_section = _find_section(explanation, "origen_p_model")
    elo_home_step = _find_step(origen_section, "elo_home")
    assert abs(float(elo_home_step.raw) - 1980.33) < 0.1

    elo_away_step = _find_step(origen_section, "elo_away")
    assert abs(float(elo_away_step.raw) - 1662.98) < 0.1

    # stake
    stake_section = _find_section(explanation, "stake")
    kf_step = _find_step(stake_section, "kelly_fraction")
    assert abs(float(kf_step.raw) - 0.12016) < 1e-5

    rs_step = _find_step(stake_section, "recommended_stake")
    assert rs_step.raw == "120.16"

    # metadata
    meta_section = _find_section(explanation, "metadata")
    signal_id_step = _find_step(meta_section, "signal_id")
    assert signal_id_step.raw == 10


def test_explain_returns_none_for_unknown_signal(db_session):
    """signal_id inexistente → build_explanation retorna None (router responde 404)."""
    result = build_explanation(db_session, 99999)
    assert result is None


# ---------------------------------------------------------------------------
# (c) Triple incompleto → note presente, no excepción
# ---------------------------------------------------------------------------


def test_incomplete_triple_returns_note_not_exception(db_session):
    """Triple de-vig incompleto (solo HOME, sin DRAW ni AWAY) → note en sección edge, no falla."""
    comp = _make_competition(db_session)
    home, away = _make_teams(db_session)
    match = _make_match(db_session, comp, home, away)
    mv = _make_model_version(db_session)
    pred = _make_prediction(db_session, match, mv, probability=0.60)
    captured_at = datetime.datetime(2025, 1, 14, 10, 0, 0)
    # Solo HOME odds — DRAW y AWAY ausentes
    home_odds = _make_odds_row(db_session, match, "HOME", "PartialBook", 1.80, captured_at)
    sig = _make_signal(
        db_session,
        pred,
        home_odds,
        edge=0.05,
        ev=0.03,
        kelly_fraction=0.02,
        recommended_stake="20.00",
    )
    db_session.flush()

    # No debe lanzar excepción
    explanation = build_explanation(db_session, sig.id)

    assert explanation is not None
    edge_section = _find_section(explanation, "edge")
    # La sección de edge debe tener un note sobre la imposibilidad de reconstruir
    assert edge_section.note is not None
    assert len(edge_section.note) > 0
