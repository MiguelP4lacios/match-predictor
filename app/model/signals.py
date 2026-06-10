"""Motor de señales +EV: gate de honestidad, de-vig, edge, EV, ¼-Kelly.

Invariante de arquitectura: el LLM NUNCA calcula ni inventa señales.
Este módulo es el ÚNICO writer de value_signal. El gate es lo primero —
no bypasseable: si el modelo no tiene backtest, se lanza excepción.

Gate de honestidad:
  1. BacktestRequiredError: params_json sin clave "backtest"
  2. BacktestGateError:     backtest.beats_baselines != True

Upsert idempotente sobre uq_signal_identity (prediction_id, odds_id).
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.model.odds_queries import best_odds_per_outcome
from app.model.probabilities import (
    BacktestGateError,
    BacktestRequiredError,
    compute_ev,
    devig_proportional,
    kelly_quarter,
)
from app.models import BetLog, ModelVersion, Prediction, ValueSignal
from app.models.enums import BetMode, BetStatus, MarketType


def _check_gate(mv: ModelVersion) -> dict:
    """Valida que el modelo tenga backtest aprobado.

    Returns:
        El dict ``params_json["backtest"]`` si pasa el gate.

    Raises:
        BacktestRequiredError: si no hay clave "backtest" en params_json.
        BacktestGateError:     si beats_baselines != True.
    """
    params = mv.params_json or {}
    if "backtest" not in params:
        raise BacktestRequiredError(
            f"ModelVersion '{mv.name}' no tiene reporte de backtest en params_json. "
            "Ejecutar `run_1x2 backtest` antes de generar señales."
        )
    bt = params["backtest"]
    if not bt.get("beats_baselines", False):
        brier = bt.get("brier", "N/A")
        logloss = bt.get("logloss", "N/A")
        raise BacktestGateError(
            f"ModelVersion '{mv.name}' no supera los baselines: "
            f"brier={brier}, logloss={logloss}. "
            "Señales bloqueadas hasta que el modelo supere ambas métricas."
        )
    return bt


def _get_thresholds(mv: ModelVersion) -> dict:
    """Devuelve thresholds del modelo (con defaults seguros)."""
    params = mv.params_json or {}
    thresholds = params.get("thresholds", {})
    return {
        "edge_min": thresholds.get("edge_min", 0.03),
        "kelly_fraction": thresholds.get("kelly_fraction", 0.25),
        "min_bucket_support": thresholds.get("min_bucket_support", 300),
        "bankroll": thresholds.get("bankroll", 1000.0),
    }


def generate_signals(
    session: Session,
    model_version_id: int,
    match_id: int | None = None,
) -> list[int]:
    """Genera señales +EV para las predicciones del modelo dado.

    Args:
        session: sesión SQLAlchemy.
        model_version_id: ID del ModelVersion activo.
        match_id: si se especifica, limita las predicciones a ese partido.

    Returns:
        Lista de IDs de ValueSignal emitidas.

    Raises:
        BacktestRequiredError: si params_json no contiene "backtest".
        BacktestGateError:     si beats_baselines != True.
    """
    mv: ModelVersion = session.get(ModelVersion, model_version_id)
    if mv is None:
        raise ValueError(f"model_version_id={model_version_id} no encontrado")

    # Gate de honestidad — lo primero, no bypasseable
    _check_gate(mv)
    thresholds = _get_thresholds(mv)
    edge_min: float = thresholds["edge_min"]
    bankroll: float = thresholds["bankroll"]

    # Obtener predicciones del modelo
    pred_stmt = select(Prediction).where(
        Prediction.model_version_id == model_version_id,
        Prediction.market_type == MarketType.MATCH_1X2,
    )
    if match_id is not None:
        pred_stmt = pred_stmt.where(Prediction.match_id == match_id)

    predictions = session.scalars(pred_stmt).all()
    if not predictions:
        return []

    # Agrupar predicciones por (match_id) → dict outcome_code → Prediction
    matches: dict[int, dict[str, Prediction]] = {}
    for pred in predictions:
        mid = pred.match_id
        if mid not in matches:
            matches[mid] = {}
        matches[mid][pred.outcome_code] = pred

    emitted_ids: list[int] = []

    for mid, preds_by_outcome in matches.items():
        # Mejor cuota por outcome_code (extraído a odds_queries para reutilización)
        best_odds = best_odds_per_outcome(mid, session)
        if not best_odds:
            continue  # Sin odds, no hay señal

        h_odds_row = best_odds.get("HOME")
        d_odds_row = best_odds.get("DRAW")
        a_odds_row = best_odds.get("AWAY")

        if not (h_odds_row and d_odds_row and a_odds_row):
            continue  # Triple incompleto

        fair = devig_proportional(
            h_odds=float(h_odds_row.decimal_odds),
            d_odds=float(d_odds_row.decimal_odds),
            a_odds=float(a_odds_row.decimal_odds),
        )

        outcome_odds_map = {
            "HOME": (h_odds_row, fair["home"]),
            "DRAW": (d_odds_row, fair["draw"]),
            "AWAY": (a_odds_row, fair["away"]),
        }

        for outcome_code, (odds_row, fair_p) in outcome_odds_map.items():
            pred = preds_by_outcome.get(outcome_code)
            if pred is None:
                continue

            p_model = float(pred.probability)
            decimal_odds = float(odds_row.decimal_odds)
            edge = p_model - fair_p

            if edge < edge_min:
                continue  # Sin valor esperado suficiente

            ev = compute_ev(p_model, decimal_odds)
            kf = kelly_quarter(p_model, decimal_odds)
            recommended_stake = Decimal(str(round(kf * bankroll, 2)))

            # Upsert idempotente
            vs_stmt = (
                pg_insert(ValueSignal)
                .values(
                    prediction_id=pred.id,
                    odds_id=odds_row.id,
                    edge=round(edge, 5),
                    ev=round(ev, 5),
                    kelly_fraction=round(kf, 5),
                    recommended_stake=recommended_stake,
                )
                .on_conflict_do_nothing(constraint="uq_signal_identity")
                .returning(ValueSignal.id)
            )
            result = session.execute(vs_stmt).scalar()

            if result is not None:
                # Nueva señal emitida — crear BetLog PAPER
                bet = BetLog(
                    value_signal_id=result,
                    mode=BetMode.PAPER,
                    stake=recommended_stake,
                    odds_taken=decimal_odds,
                    status=BetStatus.PENDING,
                )
                session.add(bet)
                emitted_ids.append(result)

    session.flush()
    return emitted_ids
