"""Tests TDD para app/model/run_futures.py — persistence del Monte Carlo.

Escenarios:
  RF1: load_sim_inputs devuelve vacío cuando no hay grupos WC en DB
  RF2: run_futures_simulate es idempotente (2 llamadas → mismas filas, no duplicados)
  RF3: Los market_type escritos coinciden exactamente con los esperados
  RF4: outcome_team_id es NOT NULL en todas las predicciones de futuros
  RF5: competition_id está seteado y apunta al WC en todas las filas
"""

import datetime

from sqlalchemy import select

from app.models import (
    Competition,
    EloRating,
    ModelVersion,
    Prediction,
    Team,
)
from app.models.enums import CompetitionKind, MarketType
from app.models.tournament import GroupTeam, TournamentGroup

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PARAMS = {
    "cutpoints": {"a1": 0.4, "delta": 0.6},
    "beta_diff": 0.003,
    "beta_neutral": -0.1,
}

_FUTURES_MARKETS = {
    MarketType.OUTRIGHT_WINNER,
    MarketType.GROUP_ADVANCE,
    MarketType.REACH_SEMI_FINAL,
    MarketType.REACH_FINAL,
}


def _make_wc_competition(session):
    c = Competition(name="FIFA World Cup 2026 RF_TEST", kind=CompetitionKind.WORLD_CUP)
    session.add(c)
    session.flush()
    return c


def _make_team(session, name: str, elo: float = 1700.0) -> Team:
    t = Team(name=f"RF_{name}")
    session.add(t)
    session.flush()
    er = EloRating(team_id=t.id, rating_date=datetime.date(2026, 1, 1), rating=elo)
    session.add(er)
    session.flush()
    return t


def _make_group(session, comp, letter: str, teams: list[Team]) -> TournamentGroup:
    grp = TournamentGroup(competition_id=comp.id, season_year=2026, name=letter)
    session.add(grp)
    session.flush()
    for t in teams:
        session.add(GroupTeam(group_id=grp.id, team_id=t.id))
    session.flush()
    return grp


def _make_model_version(session) -> ModelVersion:
    mv = ModelVersion(name="montecarlo-v1-rftest", params_json=_PARAMS)
    session.add(mv)
    session.flush()
    return mv


# ---------------------------------------------------------------------------
# RF1: load_sim_inputs devuelve vacío sin grupos WC
# ---------------------------------------------------------------------------


def test_rf1_load_sim_inputs_empty_without_groups(db_session):
    """RF1: WC con CERO grupos → load_sim_inputs retorna groups={}, elo={}, results={}."""
    from app.model.run_futures import load_sim_inputs

    # Crear una competición WC sin grupos (aislada por el SAVEPOINT del fixture)
    wc = _make_wc_competition(db_session)

    groups, elo_ratings, completed_results, comp_id = load_sim_inputs(
        db_session, competition_id=wc.id
    )

    assert groups == {}, f"Esperado {{}}, obtenido {groups}"
    assert elo_ratings == {}, f"Esperado {{}}, obtenido {elo_ratings}"
    assert completed_results == {}
    assert comp_id == wc.id


# ---------------------------------------------------------------------------
# RF2: idempotencia — 2 llamadas producen las mismas filas
# ---------------------------------------------------------------------------


def test_rf2_run_futures_simulate_is_idempotent(db_session):
    """RF2: llamar simulate dos veces produce el mismo número de filas, sin duplicados."""
    from app.model.run_futures import run_futures_simulate

    wc = _make_wc_competition(db_session)
    teams_a = [_make_team(db_session, f"A{i}", elo=1700.0 if i == 0 else 1500.0) for i in range(4)]
    teams_b = [_make_team(db_session, f"B{i}") for i in range(4)]
    _make_group(db_session, wc, "X", teams_a)
    _make_group(db_session, wc, "Y", teams_b)
    mv = _make_model_version(db_session)

    from sqlalchemy import func
    from sqlalchemy import select as sa_select

    # Primera ejecución
    run_futures_simulate(
        db_session, model_version_id=mv.id, n_iterations=100, seed=99,
        competition_id=wc.id,
    )
    count1 = db_session.scalar(
        sa_select(func.count(Prediction.id)).where(Prediction.model_version_id == mv.id)
    )

    # Segunda ejecución (idempotente)
    run_futures_simulate(
        db_session, model_version_id=mv.id, n_iterations=100, seed=99,
        competition_id=wc.id,
    )
    count2 = db_session.scalar(
        sa_select(func.count(Prediction.id)).where(Prediction.model_version_id == mv.id)
    )

    assert count1 > 0, "Primera ejecución debe escribir predicciones"
    assert count1 == count2, (
        f"Idempotencia fallida: primera ejecución {count1} filas, segunda {count2} filas"
    )


# ---------------------------------------------------------------------------
# RF3: market_types escritos son exactamente los 4 esperados
# ---------------------------------------------------------------------------


def test_rf3_market_types_are_correct(db_session):
    """RF3: Los 4 market_types de futuros están presentes en las predicciones escritas."""

    from app.model.run_futures import run_futures_simulate

    wc = _make_wc_competition(db_session)
    teams_a = [_make_team(db_session, f"C{i}") for i in range(4)]
    teams_b = [_make_team(db_session, f"D{i}") for i in range(4)]
    _make_group(db_session, wc, "M", teams_a)
    _make_group(db_session, wc, "N", teams_b)
    mv = _make_model_version(db_session)

    run_futures_simulate(
        db_session, model_version_id=mv.id, n_iterations=100, seed=7,
        competition_id=wc.id,
    )

    written_markets = set(
        db_session.scalars(
            select(Prediction.market_type).where(Prediction.model_version_id == mv.id).distinct()
        ).all()
    )

    assert written_markets == _FUTURES_MARKETS, (
        f"Market types esperados: {_FUTURES_MARKETS}, obtenidos: {written_markets}"
    )


# ---------------------------------------------------------------------------
# RF4: outcome_team_id es NOT NULL en todas las predicciones de futuros
# ---------------------------------------------------------------------------


def test_rf4_outcome_team_id_not_null(db_session):
    """RF4: Todas las predicciones de futuros tienen outcome_team_id NOT NULL."""
    from sqlalchemy import func

    from app.model.run_futures import run_futures_simulate

    wc = _make_wc_competition(db_session)
    teams_a = [_make_team(db_session, f"E{i}") for i in range(4)]
    teams_b = [_make_team(db_session, f"F{i}") for i in range(4)]
    _make_group(db_session, wc, "P", teams_a)
    _make_group(db_session, wc, "Q", teams_b)
    mv = _make_model_version(db_session)

    run_futures_simulate(
        db_session, model_version_id=mv.id, n_iterations=100, seed=13,
        competition_id=wc.id,
    )

    null_count = db_session.scalar(
        select(func.count(Prediction.id)).where(
            Prediction.model_version_id == mv.id,
            Prediction.outcome_team_id.is_(None),
        )
    )

    assert null_count == 0, f"Se encontraron {null_count} predicciones con outcome_team_id NULL"


# ---------------------------------------------------------------------------
# RF5: competition_id apunta al WC en todas las filas
# ---------------------------------------------------------------------------


def test_rf5_competition_id_is_wc(db_session):
    """RF5: Todas las predicciones de futuros tienen competition_id del WC."""
    from sqlalchemy import func

    from app.model.run_futures import run_futures_simulate

    wc = _make_wc_competition(db_session)
    teams_a = [_make_team(db_session, f"G{i}") for i in range(4)]
    teams_b = [_make_team(db_session, f"H{i}") for i in range(4)]
    _make_group(db_session, wc, "R", teams_a)
    _make_group(db_session, wc, "S", teams_b)
    mv = _make_model_version(db_session)

    run_futures_simulate(
        db_session, model_version_id=mv.id, n_iterations=100, seed=21,
        competition_id=wc.id,
    )

    wrong_comp = db_session.scalar(
        select(func.count(Prediction.id)).where(
            Prediction.model_version_id == mv.id,
            Prediction.competition_id != wc.id,
        )
    )

    assert wrong_comp == 0, (
        f"Se encontraron {wrong_comp} predicciones con competition_id != WC"
    )
