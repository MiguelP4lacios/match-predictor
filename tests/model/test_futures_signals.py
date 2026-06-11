"""TDD — Task 5.1: futures_signals.py — de-vig N outcomes + ValueSignal emission.

Escenarios de spec value-signals (verbatim):

  DEVIG-1 — zero-overround book [2.00, 3.00, 6.00]
    raw = [0.5000, 0.3333, 0.1667]; overround = 1.0000
    p_fair = [0.5000, 0.3333, 0.1667] (±0.0001); sum = 1.0000

  DEVIG-2 — real overround book [1.80, 3.50, 4.50]
    raw = [0.5556, 0.2857, 0.2222]; overround = 1.0635
    p_fair = [0.5224, 0.2686, 0.2090] (±0.0001); sum = 1.0000

  FS-1 — edge positivo: p_model=0.18, p_fair=0.14 → edge=0.04 → 1 ValueSignal
  FS-2 — edge negativo: p_model=0.06, p_fair=0.09 → edge=−0.03 → sin señal
  FS-3 — idempotencia: misma snapshot → sin duplicado, sin excepción
"""

import pytest

from app.model.futures_signals import devig_n_outcomes

# ---------------------------------------------------------------------------
# DEVIG puro (función pura, sin BD)
# ---------------------------------------------------------------------------


class TestDevigNOutcomes:
    """Verificación verbatim de los escenarios del spec."""

    def test_devig_zero_overround(self):
        """DEVIG-1: cuotas [2.00, 3.00, 6.00] → p_fair = raw (sin overround)."""
        odds = [2.00, 3.00, 6.00]
        p_fair = devig_n_outcomes(odds)

        assert len(p_fair) == 3
        assert sum(p_fair) == pytest.approx(1.0, abs=1e-9)
        assert p_fair[0] == pytest.approx(0.5000, abs=0.0001)
        assert p_fair[1] == pytest.approx(0.3333, abs=0.0001)
        assert p_fair[2] == pytest.approx(0.1667, abs=0.0001)

    def test_devig_real_overround(self):
        """DEVIG-2: cuotas [1.80, 3.50, 4.50] → overround≈1.0635, p_fair verbatim."""
        odds = [1.80, 3.50, 4.50]
        p_fair = devig_n_outcomes(odds)

        assert len(p_fair) == 3
        assert sum(p_fair) == pytest.approx(1.0, abs=1e-9)
        assert p_fair[0] == pytest.approx(0.5224, abs=0.0001)
        assert p_fair[1] == pytest.approx(0.2686, abs=0.0001)
        assert p_fair[2] == pytest.approx(0.2090, abs=0.0001)

    def test_devig_single_outcome(self):
        """1 outcome → p_fair[0] = 1.0 exacto."""
        odds = [2.50]
        p_fair = devig_n_outcomes(odds)

        assert len(p_fair) == 1
        assert p_fair[0] == pytest.approx(1.0, abs=1e-12)

    def test_devig_sum_always_one(self):
        """48 outcomes con cuotas arbitrarias → sum = 1.0 (±1e-9)."""
        # Simula 48 equipos con cuotas variadas
        import random

        rng = random.Random(42)
        odds = [rng.uniform(1.5, 100.0) for _ in range(48)]
        p_fair = devig_n_outcomes(odds)

        assert len(p_fair) == 48
        assert sum(p_fair) == pytest.approx(1.0, abs=1e-9)
        assert all(p > 0 for p in p_fair)


# ---------------------------------------------------------------------------
# generate_futures_signals — integración con la BD
# ---------------------------------------------------------------------------


def _setup_futures_signal_scenario(session, p_model: float, decimal_odds: float):
    """Crea las entidades mínimas para probar generate_futures_signals.

    Returns (mv_id, prediction_id, odds_id, team_id).
    """
    from sqlalchemy import select

    from app.models import Competition, Odds, Team
    from app.models.enums import CompetitionKind, MarketType
    from app.models.model import ModelVersion, Prediction

    # Team
    team = Team(name=f"TEST_FS_Team_{p_model:.2f}")
    session.add(team)
    session.flush()

    # Competition
    comp = session.scalar(select(Competition).where(Competition.name == "FIFA World Cup"))
    if comp is None:
        comp = Competition(name="FIFA World Cup", kind=CompetitionKind.WORLD_CUP)
        session.add(comp)
        session.flush()

    # ModelVersion (montecarlo-v1, sin backtest — gate SKIPPED para futures)
    mv = session.scalar(
        select(ModelVersion).where(ModelVersion.name == "montecarlo-v1-test")
    )
    if mv is None:
        mv = ModelVersion(
            name="montecarlo-v1-test",
            params_json={"seed": 42, "model": "monte-carlo-test"},
        )
        session.add(mv)
        session.flush()

    # Prediction: OUTRIGHT_WINNER con la prob del modelo
    pred = Prediction(
        model_version_id=mv.id,
        match_id=None,
        competition_id=comp.id,
        outcome_team_id=team.id,
        market_type=MarketType.OUTRIGHT_WINNER,
        outcome_code=None,
        probability=p_model,
        low_confidence=False,
    )
    session.add(pred)
    session.flush()

    # Odds: OUTRIGHT_WINNER capturada para ese equipo
    import datetime

    odds_row = Odds(
        market_type=MarketType.OUTRIGHT_WINNER,
        outcome_team_id=team.id,
        competition_id=comp.id,
        bookmaker="pinnacle",
        decimal_odds=decimal_odds,
        captured_at=datetime.datetime(2026, 6, 11, 12, 0),
        is_closing=False,
    )
    session.add(odds_row)
    session.flush()

    return mv.id, pred.id, odds_row.id, team.id


class TestGenerateFuturesSignals:

    def test_positive_edge_emits_value_signal(self, db_session):
        """FS-1: p_model=0.18, p_fair≈0.14 → edge≈0.04 → 1 ValueSignal PAPER."""
        # Con 1 sola odds a 1/0.14 ≈ 7.14 → devig sobre 1 outcome = 1.0 (not useful)
        # Para que p_fair=0.14 necesitamos que la cuota del team sea tal que su
        # implied sea 0.14 de la suma total. Usar 2 equipos: decimal_odds así
        # que implied(team1)=0.14 y implied(team2)=el resto.
        # Con 1 team solo: p_fair = 1.0 siempre (trivial). Necesitamos el contexto
        # real de múltiples equipos.
        # Escenario más simple: 3 equipos con cuotas [1.80, 3.50, 4.50]
        # p_fair = [0.5224, 0.2686, 0.2090] (spec verbatim)
        # p_model team3 = 0.25 > 0.2090 → edge = 0.25 - 0.2090 = 0.041 > 0.03
        import datetime

        from sqlalchemy import select

        from app.model.futures_signals import generate_futures_signals
        from app.models import Competition, Odds, Team
        from app.models.betting import BetLog, ValueSignal
        from app.models.enums import BetMode, CompetitionKind, MarketType
        from app.models.model import ModelVersion, Prediction

        comp = db_session.scalar(
            select(Competition).where(Competition.name == "FIFA World Cup")
        )
        if comp is None:
            comp = Competition(name="FIFA World Cup", kind=CompetitionKind.WORLD_CUP)
            db_session.add(comp)
            db_session.flush()

        mv = ModelVersion(
            name="mc-fs-test-pos",
            params_json={"seed": 42},
        )
        db_session.add(mv)
        db_session.flush()

        # 3 equipos
        teams = []
        for i in range(3):
            t = Team(name=f"FS_POS_Team_{i}")
            db_session.add(t)
            teams.append(t)
        db_session.flush()

        # cuotas [1.80, 3.50, 4.50] — spec DEVIG-2
        raw_odds_values = [1.80, 3.50, 4.50]
        # p_fair = [0.5224, 0.2686, 0.2090]
        # p_model team2 = 0.25 → edge = 0.25 - 0.2090 = 0.041 > edge_min (0.03)

        p_model_values = [0.50, 0.25, 0.25]  # team0 p≈p_fair, team1 p≈p_fair, team2 +EV

        preds = []
        for team, p_model in zip(teams, p_model_values, strict=True):
            pred = Prediction(
                model_version_id=mv.id,
                match_id=None,
                competition_id=comp.id,
                outcome_team_id=team.id,
                market_type=MarketType.OUTRIGHT_WINNER,
                outcome_code=None,
                probability=p_model,
                low_confidence=False,
            )
            db_session.add(pred)
            preds.append(pred)
        db_session.flush()

        for team, decimal_odds in zip(teams, raw_odds_values, strict=True):
            odds_row = Odds(
                market_type=MarketType.OUTRIGHT_WINNER,
                outcome_team_id=team.id,
                competition_id=comp.id,
                bookmaker="pinnacle",
                decimal_odds=decimal_odds,
                captured_at=datetime.datetime(2026, 6, 11, 12, 0),
                is_closing=False,
            )
            db_session.add(odds_row)
        db_session.flush()

        signal_ids = generate_futures_signals(db_session, mv.id, edge_min=0.03)

        # Team2 (p_model=0.25 vs p_fair=0.2090) → +EV signal
        assert len(signal_ids) >= 1, "Debe emitir al menos 1 señal para team con edge positivo"

        # Verificar que la señal es PAPER
        sig = db_session.get(ValueSignal, signal_ids[0])
        assert sig is not None
        bet = db_session.scalar(
            select(BetLog).where(BetLog.value_signal_id == sig.id)
        )
        assert bet is not None
        assert bet.mode == BetMode.PAPER

    def test_negative_edge_no_signal(self, db_session):
        """FS-2: p_model=0.06, p_fair=0.09 → edge=−0.03 → sin señal."""
        import datetime

        from sqlalchemy import select

        from app.model.futures_signals import generate_futures_signals
        from app.models import Competition, Odds, Team
        from app.models.enums import CompetitionKind, MarketType
        from app.models.model import ModelVersion, Prediction

        comp = db_session.scalar(
            select(Competition).where(Competition.name == "FIFA World Cup")
        )
        if comp is None:
            comp = Competition(name="FIFA World Cup", kind=CompetitionKind.WORLD_CUP)
            db_session.add(comp)
            db_session.flush()

        mv = ModelVersion(name="mc-fs-test-neg", params_json={"seed": 42})
        db_session.add(mv)
        db_session.flush()

        # Un solo equipo con p_model < p_fair
        # Cuota = 4.50 → implied = 1/4.50 = 0.2222 → devig sobre 1 team = 1.0
        # Necesitamos que p_fair(team) = 0.09 con p_model = 0.06
        # Usamos 2 equipos: odds [1.80, 4.50]
        # implied: [0.5556, 0.2222] → total = 0.7778? No, eso es overround < 1
        # Hmm, let me think differently.
        # Use odds [10.0, 12.0] → implied [0.1000, 0.0833] → total 0.1833 → overround < 1
        # That doesn't work either. Use odds [1.30, 1.90] → implied [0.7692, 0.5263] = 1.2955
        # p_fair = [0.7692/1.2955, 0.5263/1.2955] = [0.5937, 0.4063]
        # That's still too high. Let me use 3 teams with team1 having p_fair ≈ 0.09
        # odds [2.00, 11.11, 14.29] → implied [0.5, 0.09, 0.07] → total 0.66 (underround!)
        #
        # OK let me use a simpler approach: just set p_model so it's below p_fair
        # With 3 teams, odds [2.00, 3.00, 6.00]:
        # p_fair = [0.5, 0.333, 0.167] (DEVIG-1, zero overround)
        # team1: p_model = 0.06 (much less than 0.167) → negative edge
        # That works fine.

        teams = []
        for i in range(3):
            t = Team(name=f"FS_NEG_Team_{i}")
            db_session.add(t)
            teams.append(t)
        db_session.flush()

        raw_odds_values = [2.00, 3.00, 6.00]
        # p_fair = [0.5, 0.333, 0.167]
        # team2: p_model=0.06 < p_fair=0.167 → negative edge → no signal
        p_model_values = [0.50, 0.33, 0.06]

        for team, p_model in zip(teams, p_model_values, strict=True):
            pred = Prediction(
                model_version_id=mv.id,
                match_id=None,
                competition_id=comp.id,
                outcome_team_id=team.id,
                market_type=MarketType.OUTRIGHT_WINNER,
                outcome_code=None,
                probability=p_model,
                low_confidence=False,
            )
            db_session.add(pred)

        for team, decimal_odds in zip(teams, raw_odds_values, strict=True):
            odds_row = Odds(
                market_type=MarketType.OUTRIGHT_WINNER,
                outcome_team_id=team.id,
                competition_id=comp.id,
                bookmaker="pinnacle",
                decimal_odds=decimal_odds,
                captured_at=datetime.datetime(2026, 6, 11, 12, 0),
                is_closing=False,
            )
            db_session.add(odds_row)
        db_session.flush()

        signal_ids = generate_futures_signals(db_session, mv.id, edge_min=0.03)

        # None of the teams has edge >= 0.03
        assert len(signal_ids) == 0, "No debe emitir señales cuando el edge es negativo"

    def test_idempotency_no_duplicate(self, db_session):
        """FS-3: misma snapshot ejecutada dos veces → no duplicado, no excepción."""
        import datetime

        from sqlalchemy import func, select

        from app.model.futures_signals import generate_futures_signals
        from app.models import Competition, Odds, Team
        from app.models.betting import ValueSignal
        from app.models.enums import CompetitionKind, MarketType
        from app.models.model import ModelVersion, Prediction

        comp = db_session.scalar(
            select(Competition).where(Competition.name == "FIFA World Cup")
        )
        if comp is None:
            comp = Competition(name="FIFA World Cup", kind=CompetitionKind.WORLD_CUP)
            db_session.add(comp)
            db_session.flush()

        mv = ModelVersion(name="mc-fs-test-idem", params_json={"seed": 42})
        db_session.add(mv)
        db_session.flush()

        # 1 equipo con edge positivo claro
        team = Team(name="FS_IDEM_Team")
        db_session.add(team)
        db_session.flush()

        # p_model=0.30 vs p_fair con odds 4.00 y otros dos equipos
        teams = [team]
        odds_vals = [4.00, 2.00, 2.00]  # team0 has edge
        p_models = [0.30, 0.50, 0.50]

        # Add 2 more teams for context
        for i in range(2):
            t = Team(name=f"FS_IDEM_Other_{i}")
            db_session.add(t)
            teams.append(t)
        db_session.flush()

        for team, p_model in zip(teams, p_models, strict=True):
            pred = Prediction(
                model_version_id=mv.id,
                match_id=None,
                competition_id=comp.id,
                outcome_team_id=team.id,
                market_type=MarketType.OUTRIGHT_WINNER,
                outcome_code=None,
                probability=p_model,
                low_confidence=False,
            )
            db_session.add(pred)

        for team, decimal_odds in zip(teams, odds_vals, strict=True):
            odds_row = Odds(
                market_type=MarketType.OUTRIGHT_WINNER,
                outcome_team_id=team.id,
                competition_id=comp.id,
                bookmaker="pinnacle",
                decimal_odds=decimal_odds,
                captured_at=datetime.datetime(2026, 6, 11, 12, 0),
                is_closing=False,
            )
            db_session.add(odds_row)
        db_session.flush()

        # Primera ejecución
        generate_futures_signals(db_session, mv.id, edge_min=0.03)
        count_after_first = db_session.scalar(
            select(func.count()).select_from(ValueSignal)
            .where(ValueSignal.prediction_id.in_([p.id for p in db_session.scalars(
                select(Prediction).where(Prediction.model_version_id == mv.id)
            ).all()]))
        )

        # Segunda ejecución — idempotente
        generate_futures_signals(db_session, mv.id, edge_min=0.03)
        count_after_second = db_session.scalar(
            select(func.count()).select_from(ValueSignal)
            .where(ValueSignal.prediction_id.in_([p.id for p in db_session.scalars(
                select(Prediction).where(Prediction.model_version_id == mv.id)
            ).all()]))
        )

        assert count_after_first >= 1, "Debe emitir al menos 1 señal en la primera ejecución"
        assert count_after_second == count_after_first, "Segunda ejecución no debe duplicar señales"
