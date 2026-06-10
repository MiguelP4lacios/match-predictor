"""Runner del modelo 1X2: subcomandos fit | backtest | predict | signals.

    docker compose run --rm api python -m app.model.run_1x2 fit
    docker compose run --rm api python -m app.model.run_1x2 backtest
    docker compose run --rm api python -m app.model.run_1x2 predict
    docker compose run --rm api python -m app.model.run_1x2 signals

Refleja el patrón de run_elo.py: docker-only entrypoint, sin dependencias
de FastAPI, sin LLM, sin llamadas a APIs externas durante el request.
"""

import argparse
import datetime
import sys

# ---------------------------------------------------------------------------
# Subcomandos
# ---------------------------------------------------------------------------


def _run_fit() -> None:
    """Ajusta el OLM sobre partidos con match_date < 2018-06-01."""
    import pandas as pd
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.model.fit_1x2 import build_binned_table, fit_olm, to_params
    from app.models import EloRating, Match, ModelVersion
    from app.models.enums import MatchStatus

    cutoff = datetime.date(2018, 6, 1)
    home_adv = 100.0

    cutoff_str = cutoff.isoformat()
    print(f"Ajustando OLM sobre partidos con match_date < {cutoff_str}...")
    with SessionLocal() as session:
        stmt = (
            select(
                Match.id.label("match_id"),
                Match.match_date,
                Match.home_team_id,
                Match.away_team_id,
                Match.neutral_site,
                Match.home_score,
                Match.away_score,
            )
            .where(
                Match.status == MatchStatus.FINISHED,
                Match.match_date < cutoff,
                Match.home_score.is_not(None),
                Match.away_score.is_not(None),
            )
            .order_by(Match.match_date)
        )
        rows = session.execute(stmt).fetchall()

    if not rows:
        print("ERROR: No hay partidos finalizados antes de la fecha de corte.")
        sys.exit(1)

    # Construir DataFrame con elo_diff point-in-time
    records = []
    with SessionLocal() as session:
        for row in rows:
            # Lookup point-in-time de Elo para cada equipo
            home_r = (
                session.scalar(
                    select(EloRating.rating)
                    .where(
                        EloRating.team_id == row.home_team_id,
                        EloRating.rating_date < row.match_date,
                    )
                    .order_by(EloRating.rating_date.desc())
                    .limit(1)
                )
                or 1500.0
            )

            away_r = (
                session.scalar(
                    select(EloRating.rating)
                    .where(
                        EloRating.team_id == row.away_team_id,
                        EloRating.rating_date < row.match_date,
                    )
                    .order_by(EloRating.rating_date.desc())
                    .limit(1)
                )
                or 1500.0
            )

            adv = 0.0 if row.neutral_site else home_adv
            elo_diff = (home_r + adv) - away_r

            if row.home_score > row.away_score:
                outcome = 2  # home
            elif row.home_score == row.away_score:
                outcome = 1  # draw
            else:
                outcome = 0  # away

            records.append(
                {
                    "match_id": row.match_id,
                    "match_date": row.match_date,
                    "elo_diff": elo_diff,
                    "neutral": int(row.neutral_site),
                    "outcome": outcome,
                }
            )

    df = pd.DataFrame(records)
    print(f"  Partidos de entrenamiento: {len(df)}")

    params = fit_olm(df)
    binned = build_binned_table(df)
    full_params = to_params(params, binned)

    print(
        f"  Coeficientes: a1={params['cutpoints']['a1']:.4f}, "
        f"delta={params['cutpoints']['delta']:.4f}, "
        f"beta_diff={params['beta_diff']:.6f}, "
        f"beta_neutral={params['beta_neutral']:.4f}"
    )
    print(f"  Buckets binados con soporte: {len(binned)}")

    # Persistir en model_version
    with SessionLocal() as session:
        mv_name = "1x2-olm-v1"
        existing = session.scalar(select(ModelVersion).where(ModelVersion.name == mv_name))
        if existing is None:
            mv = ModelVersion(name=mv_name, params_json=full_params)
            session.add(mv)
        else:
            existing.params_json = full_params
        session.commit()

    print(f"  ModelVersion '{mv_name}' guardado correctamente.")


def _run_backtest() -> None:
    """Evalúa el OLM sobre partidos con match_date >= 2018-06-01."""
    import pandas as pd
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.model.backtest_1x2 import BacktestGateError, run_backtest
    from app.models import EloRating, Match, ModelVersion
    from app.models.enums import MatchStatus

    cutoff = datetime.date(2018, 6, 1)
    cutoff_str = cutoff.isoformat()
    home_adv = 100.0

    print(f"Backtest OLM (eval >= {cutoff_str})...")

    with SessionLocal() as session:
        mv_name = "1x2-olm-v1"
        mv = session.scalar(select(ModelVersion).where(ModelVersion.name == mv_name))
        if mv is None:
            print(f"ERROR: ModelVersion '{mv_name}' no encontrada. Ejecutar 'fit' primero.")
            sys.exit(1)

        params = mv.params_json

        # Cargar TODOS los partidos finalizados para el backtest
        stmt = (
            select(
                Match.id.label("match_id"),
                Match.match_date,
                Match.home_team_id,
                Match.away_team_id,
                Match.neutral_site,
                Match.home_score,
                Match.away_score,
            )
            .where(
                Match.status == MatchStatus.FINISHED,
                Match.home_score.is_not(None),
                Match.away_score.is_not(None),
            )
            .order_by(Match.match_date)
        )
        rows = session.execute(stmt).fetchall()

        records = []
        for row in rows:
            home_r = (
                session.scalar(
                    select(EloRating.rating)
                    .where(
                        EloRating.team_id == row.home_team_id,
                        EloRating.rating_date < row.match_date,
                    )
                    .order_by(EloRating.rating_date.desc())
                    .limit(1)
                )
                or 1500.0
            )

            away_r = (
                session.scalar(
                    select(EloRating.rating)
                    .where(
                        EloRating.team_id == row.away_team_id,
                        EloRating.rating_date < row.match_date,
                    )
                    .order_by(EloRating.rating_date.desc())
                    .limit(1)
                )
                or 1500.0
            )

            adv = 0.0 if row.neutral_site else home_adv
            elo_diff = (home_r + adv) - away_r

            if row.home_score > row.away_score:
                outcome = 2
            elif row.home_score == row.away_score:
                outcome = 1
            else:
                outcome = 0

            records.append(
                {
                    "match_date": str(row.match_date),
                    "elo_diff": elo_diff,
                    "neutral": int(row.neutral_site),
                    "outcome": outcome,
                }
            )

        df = pd.DataFrame(records)
        binned_table = params.get("binned_table", [])

    try:
        metrics = run_backtest(df, params, binned_table, cutoff=cutoff_str)
        print("  Backtest APROBADO — el modelo supera ambos baselines.")
        print(
            f"  Brier OLM: {metrics['brier']:.4f} "
            f"(uniform={metrics['baselines']['uniform_brier']:.4f}, "
            f"binned={metrics['baselines']['binned_brier']:.4f})"
        )
        print(
            f"  Log-loss OLM: {metrics['logloss']:.4f} "
            f"(uniform={metrics['baselines']['uniform_logloss']:.4f}, "
            f"binned={metrics['baselines']['binned_logloss']:.4f})"
        )
        print(f"  Partidos evaluados: {metrics['eval_n']}")

        # Actualizar params_json con el reporte de backtest
        with SessionLocal() as session:
            mv = session.scalar(select(ModelVersion).where(ModelVersion.name == mv_name))
            updated = dict(mv.params_json)
            updated["backtest"] = {
                "brier": metrics["brier"],
                "logloss": metrics["logloss"],
                "baselines": metrics["baselines"],
                "beats_baselines": True,
                "calibration_table": metrics["calibration_table"],
                "eval_n": metrics["eval_n"],
                "eval_window": metrics["eval_window"],
                "split": cutoff_str,
            }
            mv.params_json = updated
            session.commit()
        print(f"  Backtest persistido en ModelVersion '{mv_name}'.")

    except BacktestGateError as exc:
        print(f"  Backtest FALLIDO: {exc}")
        print("  Señales bloqueadas. El modelo NO está autorizado para apostar.")
        sys.exit(1)


def _run_predict() -> None:
    """Genera predicciones 1X2 para fixtures SCHEDULED de WC2026."""
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.model.predict_1x2 import predict_match
    from app.models import Competition, Match, ModelVersion
    from app.models.enums import CompetitionKind, MatchStatus

    print("Generando predicciones 1X2 para fixtures SCHEDULED...")
    today = datetime.date.today()

    with SessionLocal() as session:
        mv_name = "1x2-olm-v1"
        mv = session.scalar(select(ModelVersion).where(ModelVersion.name == mv_name))
        if mv is None:
            print(f"ERROR: ModelVersion '{mv_name}' no encontrada. Ejecutar 'fit' primero.")
            sys.exit(1)

        stmt = (
            select(Match.id)
            .join(Competition, Competition.id == Match.competition_id)
            .where(
                Match.status == MatchStatus.SCHEDULED,
                Competition.kind == CompetitionKind.WORLD_CUP,
                Match.match_date >= today,
            )
            .order_by(Match.match_date)
        )
        match_ids = list(session.scalars(stmt))

    if not match_ids:
        print("  No hay fixtures SCHEDULED de WC2026 hacia adelante.")
        return

    print(f"  Fixtures encontrados: {len(match_ids)}")
    total = 0
    with SessionLocal() as session:
        for mid in match_ids:
            ids = predict_match(session, match_id=mid, model_version_id=mv.id)
            total += len(ids)
        session.commit()

    print(f"  Predicciones escritas: {total} (3 por fixture = {total // 3} partidos)")


def _run_signals() -> None:
    """Genera señales +EV PAPER para fixtures con predicciones y odds."""
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.model.signals import generate_signals
    from app.models import ModelVersion

    print("Generando señales +EV PAPER...")
    with SessionLocal() as session:
        mv_name = "1x2-olm-v1"
        mv = session.scalar(select(ModelVersion).where(ModelVersion.name == mv_name))
        if mv is None:
            print(f"ERROR: ModelVersion '{mv_name}' no encontrada.")
            sys.exit(1)

        emitted = generate_signals(session, model_version_id=mv.id)
        session.commit()

    print(f"  Señales emitidas: {len(emitted)}")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI con subcomandos fit | backtest | predict | signals."""
    parser = argparse.ArgumentParser(description="Runner del modelo 1X2 (OLM + señales +EV)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("fit", help="Ajustar OLM sobre datos históricos")
    sub.add_parser("backtest", help="Evaluar OLM y actualizar gate de honestidad")
    sub.add_parser("predict", help="Generar predicciones para fixtures SCHEDULED")
    sub.add_parser("signals", help="Generar señales +EV PAPER")

    args = parser.parse_args()

    if args.command == "fit":
        _run_fit()
    elif args.command == "backtest":
        _run_backtest()
    elif args.command == "predict":
        _run_predict()
    elif args.command == "signals":
        _run_signals()


if __name__ == "__main__":
    main()
