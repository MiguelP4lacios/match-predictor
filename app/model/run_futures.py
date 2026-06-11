"""Runner del Monte Carlo de futuros: subcomandos simulate | signals.

    docker compose run --rm api python -m app.model.run_futures simulate
    docker compose run --rm api python -m app.model.run_futures signals

simulate:
  1. Carga grupos WC, resultados de fase de grupos, Elo ratings.
  2. Simula el torneo con montecarlo.simulate_tournament().
  3. DELETE predicciones anteriores del model_version 'montecarlo-v1'.
  4. INSERT predicciones nuevas (idempotente).
  5. COMMIT al borde de la operación.

Invariante: NUNCA llama a APIs externas. Todo desde Postgres.
"""

from __future__ import annotations

import argparse
import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.model.montecarlo import simulate_tournament
from app.model.standings import MatchResult
from app.models import (
    Competition,
    EloRating,
    ModelVersion,
    Prediction,
)
from app.models.enums import CompetitionKind, MarketType, MatchStatus
from app.models.match import Match
from app.models.tournament import GroupTeam, TournamentGroup

# ---------------------------------------------------------------------------
# Nombre canónico de la ModelVersion de Monte Carlo
# ---------------------------------------------------------------------------
_MC_MODEL_NAME = "montecarlo-v1"
_MC_N_ITERATIONS = 20_000
_MC_SEED = 42


# ---------------------------------------------------------------------------
# load_sim_inputs
# ---------------------------------------------------------------------------


def load_sim_inputs(
    session: Session,
    competition_id: int | None = None,
) -> tuple[dict[str, list[int]], dict[int, float], dict[str, list[MatchResult]], int | None]:
    """Carga los inputs del simulador desde la BD.

    Args:
        session:        sesión SQLAlchemy activa.
        competition_id: si se provee, usa esa competición específica.
                       Si None, busca la primera WORLD_CUP en la BD.

    Returns:
        groups: {"A": [team_id, ...], ...} — equipos por grupo del WC activo
        elo_ratings: {team_id: float} — rating Elo más reciente por equipo
        completed_results: {"A": [MatchResult(...), ...]} — partidos FINISHED de grupo
        competition_id: ID de la competición WC o None si no existe
    """
    if competition_id is not None:
        wc = session.get(Competition, competition_id)
    else:
        wc = session.scalar(
            select(Competition).where(Competition.kind == CompetitionKind.WORLD_CUP).limit(1)
        )
    if wc is None:
        return {}, {}, {}, None

    comp_id = wc.id

    # Grupos del WC
    grp_stmt = (
        select(TournamentGroup)
        .where(TournamentGroup.competition_id == comp_id)
        .order_by(TournamentGroup.name)
    )
    tournament_groups = list(session.scalars(grp_stmt))
    if not tournament_groups:
        return {}, {}, {}, comp_id

    # Composición: {group_letter: [team_id, ...]}
    groups: dict[str, list[int]] = {}
    all_team_ids: set[int] = set()
    for grp in tournament_groups:
        member_ids = list(
            session.scalars(select(GroupTeam.team_id).where(GroupTeam.group_id == grp.id))
        )
        groups[grp.name] = member_ids
        all_team_ids.update(member_ids)

    if not all_team_ids:
        return groups, {}, {}, comp_id

    # Elo ratings (más reciente por equipo — el correcto a la fecha de hoy)
    today = datetime.date.today()
    elo_ratings: dict[int, float] = {}
    for team_id in all_team_ids:
        rating = session.scalar(
            select(EloRating.rating)
            .where(
                EloRating.team_id == team_id,
                EloRating.rating_date <= today,
            )
            .order_by(EloRating.rating_date.desc())
            .limit(1)
        )
        if rating is not None:
            elo_ratings[team_id] = float(rating)

    # Resultados de grupo FINISHED
    completed_results: dict[str, list[MatchResult]] = {}
    for grp in tournament_groups:
        finished_stmt = (
            select(Match)
            .where(
                Match.group_id == grp.id,
                Match.status == MatchStatus.FINISHED,
                Match.home_score.is_not(None),
                Match.away_score.is_not(None),
            )
        )
        matches = list(session.scalars(finished_stmt))
        if matches:
            completed_results[grp.name] = [
                MatchResult(
                    home_id=m.home_team_id,
                    away_id=m.away_team_id,
                    home_score=m.home_score,
                    away_score=m.away_score,
                )
                for m in matches
            ]

    return groups, elo_ratings, completed_results, comp_id


# ---------------------------------------------------------------------------
# run_futures_simulate
# ---------------------------------------------------------------------------

# Mapeo de claves de resultado Monte Carlo → MarketType
_PROB_MARKET: list[tuple[str, MarketType]] = [
    ("p_champion", MarketType.OUTRIGHT_WINNER),
    ("p_advance_group", MarketType.GROUP_ADVANCE),
    ("p_reach_sf", MarketType.REACH_SEMI_FINAL),
    ("p_reach_final", MarketType.REACH_FINAL),
]


def run_futures_simulate(
    session: Session,
    model_version_id: int,
    n_iterations: int = _MC_N_ITERATIONS,
    seed: int = _MC_SEED,
    competition_id: int | None = None,
) -> int:
    """Simula el torneo y persiste predicciones de futuros en la BD.

    Idempotente: borra las predicciones existentes del model_version antes de insertar.
    COMMIT al borde de la operación: si algo falla, rollback limpio.

    Args:
        session:         sesión SQLAlchemy activa.
        model_version_id: ID del ModelVersion a usar (debe existir previamente).
        n_iterations:    número de iteraciones Monte Carlo.
        seed:            semilla para reproducibilidad.

    Returns:
        Número de filas insertadas.
    """
    # Cargar inputs
    groups, elo_ratings, completed_results, competition_id = load_sim_inputs(
        session, competition_id=competition_id
    )

    if not groups or competition_id is None:
        return 0

    # Cargar parámetros del ModelVersion
    mv = session.get(ModelVersion, model_version_id)
    if mv is None:
        raise ValueError(f"ModelVersion id={model_version_id} no existe")

    model_params = mv.params_json or {}

    # Simular
    sim_results = simulate_tournament(
        groups=groups,
        elo_ratings=elo_ratings,
        model_params=model_params,
        completed_results=completed_results,
        n_iterations=n_iterations,
        seed=seed,
    )

    # DELETE predicciones existentes de este model_version (idempotencia)
    session.execute(
        delete(Prediction).where(Prediction.model_version_id == model_version_id)
    )

    # INSERT nuevas predicciones
    rows_inserted = 0
    for team_id, probs in sim_results.items():
        for prob_key, market in _PROB_MARKET:
            probability = probs.get(prob_key, 0.0)
            pred = Prediction(
                model_version_id=model_version_id,
                match_id=None,  # futuros no tienen partido específico
                competition_id=competition_id,
                outcome_team_id=team_id,
                market_type=market,
                outcome_code=None,
                probability=probability,
                low_confidence=False,
            )
            session.add(pred)
            rows_inserted += 1

    session.flush()
    return rows_inserted


# ---------------------------------------------------------------------------
# Subcomando _simulate (modo runner)
# ---------------------------------------------------------------------------


def _run_simulate() -> None:
    """Subcomando: carga inputs → simula → persiste predicciones de futuros."""
    from app.core.database import SessionLocal

    print(f"Simulando torneo ({_MC_N_ITERATIONS} iteraciones, seed={_MC_SEED})...")

    with SessionLocal() as session:
        # Obtener o crear ModelVersion
        mv = session.scalar(select(ModelVersion).where(ModelVersion.name == _MC_MODEL_NAME))
        if mv is None:
            mv = ModelVersion(
                name=_MC_MODEL_NAME,
                params_json={
                    "seed": _MC_SEED,
                    "n": _MC_N_ITERATIONS,
                    "model": "monte-carlo-poisson-elo",
                },
            )
            session.add(mv)
            session.flush()
            print(f"  ModelVersion '{_MC_MODEL_NAME}' creado (id={mv.id})")
        else:
            print(f"  ModelVersion '{_MC_MODEL_NAME}' encontrado (id={mv.id})")

        rows = run_futures_simulate(session, model_version_id=mv.id)
        session.commit()

    print(f"  Predicciones escritas: {rows}")
    if rows > 0:
        n_teams = rows // len(_PROB_MARKET)
        print(f"  Equipos simulados: ~{n_teams}")


# ---------------------------------------------------------------------------
# Subcomando _signals (placeholder — implementado en Phase 5)
# ---------------------------------------------------------------------------


def _run_signals() -> None:
    """Subcomando: genera señales +EV PAPER sobre odds capturadas vs MC probs.

    Requiere:
      - Haber ejecutado 'simulate' previamente (predicciones montecarlo-v1 en BD).
      - Odds OUTRIGHT_WINNER capturadas (por pipeline automático o manual).

    CAVEAT: señales son PAPER (informativas). Monte Carlo champion probs no están
    backtestadas como el OLM 1X2 — ver app/model/futures_signals.py.
    """
    from app.core.database import SessionLocal
    from app.model.futures_signals import generate_futures_signals

    with SessionLocal() as session:
        mv = session.scalar(select(ModelVersion).where(ModelVersion.name == _MC_MODEL_NAME))
        if mv is None:
            print(f"ERROR: ModelVersion '{_MC_MODEL_NAME}' no existe. Ejecutar 'simulate' primero.")
            return

        print(f"Generando señales +EV PAPER para ModelVersion '{_MC_MODEL_NAME}' (id={mv.id})...")
        signal_ids = generate_futures_signals(session, mv.id)
        session.commit()

    if signal_ids:
        suffix = "..." if len(signal_ids) > 10 else ""
        print(f"  Señales emitidas: {len(signal_ids)} (IDs: {signal_ids[:10]}{suffix})")
    else:
        print("  Sin señales +EV: no hay odds capturadas o ningún equipo tiene edge ≥ 0.03.")
    print("  AVISO: todas las señales son PAPER — Monte Carlo sin backtest histórico.")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI con subcomandos simulate | signals."""
    parser = argparse.ArgumentParser(description="Runner de futuros Monte Carlo WC2026")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("simulate", help="Simular torneo y persistir predicciones de futuros")
    sub.add_parser("signals", help="Generar señales +EV PAPER (requiere odds capturadas)")

    args = parser.parse_args()

    if args.command == "simulate":
        _run_simulate()
    elif args.command == "signals":
        _run_signals()


if __name__ == "__main__":
    main()
