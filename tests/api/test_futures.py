"""Tests TDD para GET /api/v1/futures/probabilities y GET /api/v1/futures/signals.

Escenarios:
  F1: champions 200 con ítems rankeados por p_champion DESC
  F2: empty case → 200 con champions=[]
  F3: sum(p_champion) razonable (en nuestro fixture 2 equipos, suma = p1 + p2)
  F4: signals 200 con lista vacía cuando no hay ValueSignal de futuros
  F5: numeric edge scenario — p_model=0.18 capturado, fair=0.14 → edge=0.04
"""

from decimal import Decimal

from app.models.competition import Competition
from app.models.enums import CompetitionKind, MarketType
from app.models.model import ModelVersion, Prediction
from app.models.team import Team

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MC_MODEL_NAME = "montecarlo-v1"

# Mercados de futuros (para aislar los tests de datos reales ya committeados en
# la BD de dev por una corrida de `run_futures simulate`).
_FUTURES_MARKETS = [
    MarketType.OUTRIGHT_WINNER,
    MarketType.GROUP_ADVANCE,
    MarketType.REACH_SEMI_FINAL,
    MarketType.REACH_FINAL,
]


def _clear_futures(session) -> None:
    """Borra (dentro del SAVEPOINT) las predicciones de futuros reales para que el
    test controle exactamente qué ve el endpoint. El rollback deja la BD intacta."""
    from sqlalchemy import delete

    from app.models.model import Prediction

    session.execute(delete(Prediction).where(Prediction.market_type.in_(_FUTURES_MARKETS)))
    session.flush()


def _make_wc(session) -> Competition:
    comp = Competition(name="FIFA World Cup 2026", kind=CompetitionKind.WORLD_CUP)
    session.add(comp)
    session.flush()
    return comp


def _make_teams(session) -> tuple[Team, Team]:
    t1 = Team(name="FuturesTeamAlpha")
    t2 = Team(name="FuturesTeamBeta")
    session.add_all([t1, t2])
    session.flush()
    return t1, t2


def _make_mv(session) -> ModelVersion:
    # get-or-create: la BD de dev ya puede tener un montecarlo-v1 real (name unique).
    from sqlalchemy import select

    mv = session.scalar(select(ModelVersion).where(ModelVersion.name == _MC_MODEL_NAME))
    if mv is None:
        mv = ModelVersion(name=_MC_MODEL_NAME, params_json={"seed": 42, "n": 20_000})
        session.add(mv)
        session.flush()
    return mv


def _seed_futures_predictions(
    session, mv: ModelVersion, comp: Competition, teams: list[Team]
) -> None:
    """Inserta predicciones de futuros para cada equipo (4 mercados cada uno)."""
    # Argentina: campeón más probable
    probs = {
        teams[0].id: {
            MarketType.OUTRIGHT_WINNER: 0.25,
            MarketType.GROUP_ADVANCE: 0.80,
            MarketType.REACH_SEMI_FINAL: 0.55,
            MarketType.REACH_FINAL: 0.40,
        },
        teams[1].id: {
            MarketType.OUTRIGHT_WINNER: 0.18,
            MarketType.GROUP_ADVANCE: 0.75,
            MarketType.REACH_SEMI_FINAL: 0.45,
            MarketType.REACH_FINAL: 0.32,
        },
    }
    for team_id, markets in probs.items():
        for market, prob in markets.items():
            session.add(
                Prediction(
                    model_version_id=mv.id,
                    match_id=None,
                    competition_id=comp.id,
                    outcome_team_id=team_id,
                    market_type=market,
                    outcome_code=None,
                    probability=prob,
                    low_confidence=False,
                )
            )
    session.flush()


# ---------------------------------------------------------------------------
# Tests — /futures/probabilities
# ---------------------------------------------------------------------------


class TestFuturesProbabilities:
    """F1-F3: endpoint de probabilidades."""

    def test_200_ranked_desc(self, client, db_session):
        """F1: retorna 200; champions rankeados por p_champion DESC."""
        _clear_futures(db_session)
        comp = _make_wc(db_session)
        t1, t2 = _make_teams(db_session)
        mv = _make_mv(db_session)
        _seed_futures_predictions(db_session, mv, comp, [t1, t2])

        resp = client.get("/api/v1/futures/probabilities")

        assert resp.status_code == 200
        body = resp.json()
        assert "champions" in body
        champions = body["champions"]
        assert len(champions) == 2
        # FuturesTeamAlpha (0.25) debe ir antes que FuturesTeamBeta (0.18)
        assert champions[0]["team"] == "FuturesTeamAlpha"
        assert champions[1]["team"] == "FuturesTeamBeta"
        # Los 4 campos de prob deben estar presentes
        assert "p_champion" in champions[0]
        assert "p_advance_group" in champions[0]
        assert "p_reach_sf" in champions[0]
        assert "p_reach_final" in champions[0]

    def test_p_champion_ranked(self, client, db_session):
        """F1 triangulación: p_champion del primero > p_champion del segundo."""
        _clear_futures(db_session)
        comp = _make_wc(db_session)
        t1, t2 = _make_teams(db_session)
        mv = _make_mv(db_session)
        _seed_futures_predictions(db_session, mv, comp, [t1, t2])

        resp = client.get("/api/v1/futures/probabilities")

        champions = resp.json()["champions"]
        assert champions[0]["p_champion"] > champions[1]["p_champion"]
        # Numeric check
        assert abs(champions[0]["p_champion"] - 0.25) < 0.001
        assert abs(champions[1]["p_champion"] - 0.18) < 0.001

    def test_empty_when_no_predictions(self, client, db_session):
        """F2: sin predicciones → champions vacío (no 404)."""
        _clear_futures(db_session)
        resp = client.get("/api/v1/futures/probabilities")

        assert resp.status_code == 200
        body = resp.json()
        assert body["champions"] == []

    def test_probabilities_in_range(self, client, db_session):
        """F3: todas las probabilidades en [0, 1]."""
        _clear_futures(db_session)
        comp = _make_wc(db_session)
        t1, t2 = _make_teams(db_session)
        mv = _make_mv(db_session)
        _seed_futures_predictions(db_session, mv, comp, [t1, t2])

        resp = client.get("/api/v1/futures/probabilities")

        for item in resp.json()["champions"]:
            assert 0.0 <= item["p_champion"] <= 1.0
            assert 0.0 <= item["p_advance_group"] <= 1.0
            assert 0.0 <= item["p_reach_sf"] <= 1.0
            assert 0.0 <= item["p_reach_final"] <= 1.0


# ---------------------------------------------------------------------------
# Tests — /futures/signals
# ---------------------------------------------------------------------------


class TestFuturesSignals:
    """F4-F5: endpoint de señales EV."""

    def test_200_empty_when_no_signals(self, client, db_session):
        """F4: sin ValueSignal de futuros → items=[] (no 404)."""
        _clear_futures(db_session)
        resp = client.get("/api/v1/futures/signals")

        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["items"] == []

    def test_200_with_futures_signal(self, client, db_session):
        """F5: con ValueSignal de futuros → retorna ítems con edge."""
        _clear_futures(db_session)
        from datetime import UTC, datetime

        from app.models.betting import ValueSignal
        from app.models.odds import Odds

        comp = _make_wc(db_session)
        t1, t2 = _make_teams(db_session)
        mv = _make_mv(db_session)
        _seed_futures_predictions(db_session, mv, comp, [t1, t2])

        # Buscar prediction OUTRIGHT_WINNER para Argentina (t1, p=0.18 → fixture)
        # El escenario numérico: p_model=0.18, fair=0.14 → edge=+0.04
        from sqlalchemy import select

        from app.core.database import get_session  # noqa: F401 - imported for override
        from app.models.model import Prediction as P  # noqa: N817

        pred = db_session.scalar(
            select(P).where(
                P.model_version_id == mv.id,
                P.outcome_team_id == t1.id,
                P.market_type == MarketType.OUTRIGHT_WINNER,
            )
        )
        assert pred is not None

        # Crear Odds para este equipo
        odds = Odds(
            bookmaker="bet365",
            market_type=MarketType.OUTRIGHT_WINNER,
            outcome_team_id=t1.id,
            decimal_odds=Decimal("7.14"),  # 1/7.14 ≈ 0.14 fair
            captured_at=datetime(2026, 6, 9, 12, 0, 0, tzinfo=UTC),
        )
        db_session.add(odds)
        db_session.flush()

        # Crear ValueSignal (edge = 0.25 - 0.14 = 0.11)
        sig = ValueSignal(
            prediction_id=pred.id,
            odds_id=odds.id,
            edge=Decimal("0.11"),
            ev=Decimal("0.11"),
            kelly_fraction=Decimal("0.04"),
            recommended_stake=Decimal("0.00"),
        )
        db_session.add(sig)
        db_session.flush()

        resp = client.get("/api/v1/futures/signals")

        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["team"] == "FuturesTeamAlpha"
        assert abs(items[0]["edge"] - 0.11) < 0.001
        assert abs(items[0]["best_odds"] - 7.14) < 0.01
        assert items[0]["bookmaker"] == "bet365"
