"""Señales +EV de futuros: de-vig proporcional sobre N outcomes + ValueSignal PAPER.

INVARIANTE: el LLM NUNCA calcula ni inventa señales. Este módulo es el único
writer de ValueSignal para mercados OUTRIGHT_WINNER (futuros). Todas las señales
son PAPER — sin gate de backtest — porque las probabilidades de Monte Carlo
champion NO están backtestadas como el OLM 1X2 (N=1 WC por año hace imposible
una calibración histórica robusta). Esta decisión es honesta y está documentada.

CAVEAT DE CALIBRACIÓN (obligatorio por diseño):
  Las probabilidades de campeón de Monte Carlo (montecarlo-v1) son señales
  INFORMATIVAS, no señales operacionales validadas. El OLM 1X2 tiene backtest
  (Brier/log-loss vs baselines). Los futuros Monte Carlo NO. Toda señal emitida
  por este módulo usa BetMode.PAPER y nunca debe usarse para apuesta REAL sin
  un backtest histórico adecuado.

Algoritmo:
  1. Cargar todas las predicciones OUTRIGHT_WINNER del model_version.
  2. Para cada equipo con predicción + odds capturada:
     a. Colectar TODAS las odds capturadas del mismo mercado/competición (snapshot
        completo) para calcular el overround global.
     b. De-vig proporcional: p_fair_i = (1/odds_i) / Σ_j(1/odds_j) para todos j.
  3. edge = p_model − p_fair; si edge ≥ edge_min → emitir ValueSignal (PAPER).
  4. Upsert idempotente sobre uq_signal_identity (prediction_id, odds_id).
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.betting import BetLog, ValueSignal
from app.models.enums import BetMode, BetStatus, MarketType
from app.models.model import ModelVersion, Prediction
from app.models.odds import Odds

# Edge mínimo por defecto (configurable por caller)
_DEFAULT_EDGE_MIN = 0.03


# ---------------------------------------------------------------------------
# Función pura: de-vig proporcional sobre N outcomes
# ---------------------------------------------------------------------------


def devig_n_outcomes(odds: list[float]) -> list[float]:
    """Convierte N cuotas decimales a probabilidades justas (método proporcional).

    p_fair_i = (1/odds_i) / Σ_j(1/odds_j)

    La suma de todas las p_fair_i es exactamente 1.0 (dentro de precisión float).

    Args:
        odds: lista de cuotas decimales > 1.0 (una por outcome/equipo).

    Returns:
        Lista de probabilidades justas de la misma longitud que `odds`.
        Suma = 1.0 (±1e-9).
    """
    if not odds:
        return []

    raw_implied = [1.0 / o for o in odds]
    total = sum(raw_implied)

    return [r / total for r in raw_implied]


# ---------------------------------------------------------------------------
# Generador de señales de futuros
# ---------------------------------------------------------------------------


def generate_futures_signals(
    session: Session,
    model_version_id: int,
    edge_min: float = _DEFAULT_EDGE_MIN,
) -> list[int]:
    """Genera señales +EV PAPER sobre odds OUTRIGHT_WINNER para el model dado.

    NO aplica el gate de backtest (BacktestRequiredError/BacktestGateError).
    Todas las señales son BetMode.PAPER — ver CAVEAT DE CALIBRACIÓN en el módulo.

    De-vig proporcional sobre TODAS las odds OUTRIGHT_WINNER capturadas para la
    misma competición (snapshot global) — esto calcula el overround real del libro.

    Idempotente: upsert sobre uq_signal_identity (prediction_id, odds_id).

    Args:
        session:          sesión SQLAlchemy activa.
        model_version_id: ID del ModelVersion (montecarlo-v1).
        edge_min:         umbral mínimo de edge para emitir señal (default 0.03).

    Returns:
        Lista de IDs de ValueSignal nuevas emitidas (vacía si no hay +EV o no hay odds).
    """
    mv: ModelVersion | None = session.get(ModelVersion, model_version_id)
    if mv is None:
        raise ValueError(f"model_version_id={model_version_id} no encontrado")

    # Predicciones OUTRIGHT_WINNER del modelo (futuros champion)
    predictions = session.scalars(
        select(Prediction).where(
            Prediction.model_version_id == model_version_id,
            Prediction.market_type == MarketType.OUTRIGHT_WINNER,
            Prediction.outcome_team_id.is_not(None),
        )
    ).all()

    if not predictions:
        return []

    # Determinar competition_id (puede haber uno solo para futuros WC)
    # Tomar el más común entre las predicciones
    comp_ids = {p.competition_id for p in predictions if p.competition_id is not None}

    if not comp_ids:
        return []

    # Para cada competition_id, cargar TODAS las odds OUTRIGHT_WINNER capturadas
    # (necesitamos el snapshot completo para el overround global)
    comp_id = next(iter(comp_ids))  # WC tiene un solo competition_id

    all_odds_rows = session.scalars(
        select(Odds).where(
            Odds.market_type == MarketType.OUTRIGHT_WINNER,
            Odds.competition_id == comp_id,
            Odds.outcome_team_id.is_not(None),
        )
    ).all()

    if not all_odds_rows:
        return []

    # Calcular de-vig sobre TODAS las odds capturadas (overround global)
    # Usar la cuota más reciente por equipo (última capturada) para el snapshot
    # Agrupar por outcome_team_id: última odds capturada por equipo
    latest_odds_by_team: dict[int, Odds] = {}
    for row in sorted(all_odds_rows, key=lambda r: r.captured_at):
        latest_odds_by_team[row.outcome_team_id] = row  # última = más reciente

    all_team_ids = list(latest_odds_by_team.keys())
    all_decimal_odds = [float(latest_odds_by_team[tid].decimal_odds) for tid in all_team_ids]

    # De-vig proporcional sobre el snapshot completo
    p_fair_list = devig_n_outcomes(all_decimal_odds)
    p_fair_by_team: dict[int, float] = {
        tid: p_fair for tid, p_fair in zip(all_team_ids, p_fair_list, strict=True)
    }

    # Mapear predictions por team_id
    pred_by_team: dict[int, Prediction] = {
        p.outcome_team_id: p for p in predictions
    }

    emitted_ids: list[int] = []

    for team_id, odds_row in latest_odds_by_team.items():
        pred = pred_by_team.get(team_id)
        if pred is None:
            continue  # Sin predicción para este equipo → no hay señal

        p_model = float(pred.probability)
        p_fair = p_fair_by_team[team_id]
        edge = p_model - p_fair

        if edge < edge_min:
            continue

        decimal_odds = float(odds_row.decimal_odds)
        ev = p_model * (decimal_odds - 1.0) - (1.0 - p_model)
        kf = max(0.0, (p_model * decimal_odds - 1.0) / (decimal_odds - 1.0)) * 0.25
        recommended_stake = Decimal(str(round(kf * 1000.0, 2)))  # bankroll default 1000

        # Upsert idempotente sobre uq_signal_identity(prediction_id, odds_id)
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
            # Nueva señal → crear BetLog PAPER (misma lógica que signals.py)
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
