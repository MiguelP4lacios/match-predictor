"""Motor de liquidación de apuestas — settle_bets.

Itera sobre bet_log WHERE status=PENDING, resuelve el partido via:
  - Ruta REAL: bet.match_id + bet.outcome_code directamente.
  - Ruta PAPER: bet.value_signal_id → value_signal → prediction → match_id, outcome_code.

Para cada apuesta con partido FINISHED:
  - Deriva resultado 1X2 (HOME/DRAW/AWAY) por marcador.
  - Evalúa WON/LOST.
  - Calcula pnl: WON = stake*(odds-1); LOST = -stake.
  - Fija settled_result, settled_at, status.

Idempotente: filtra solo PENDING, por lo que re-run no toca lo ya liquidado.
COMMITEA al final (frontera de transacción explícita — lección del rollback silencioso).
Retorna dict {settled, won, lost}.
"""

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.betting import BetLog, ValueSignal
from app.models.enums import BetStatus, MatchStatus
from app.models.match import Match
from app.models.model import Prediction


def _derive_result(home_score: int, away_score: int) -> str:
    """Deriva el resultado 1X2 a partir del marcador al 90'+ET."""
    if home_score > away_score:
        return "HOME"
    if away_score > home_score:
        return "AWAY"
    return "DRAW"


def _calc_pnl(stake: Decimal, odds_taken: float, won: bool) -> Decimal:
    """PnL: WON = stake*(odds-1); LOST = -stake. Redondeado a 2 decimales."""
    if won:
        profit = stake * Decimal(str(odds_taken - 1))
        return profit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return (-stake).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def settle_bets(session: Session) -> dict[str, int]:
    """Liquida todas las apuestas PENDING cuyos partidos estén FINISHED.

    Returns:
        dict con claves settled, won, lost.
    """
    # Obtener apuestas PENDING con LEFT JOIN a value_signal → prediction (ruta PAPER)
    stmt = (
        select(
            BetLog,
            Match,
            Prediction.outcome_code.label("pred_outcome_code"),
            Prediction.match_id.label("pred_match_id"),
        )
        .outerjoin(ValueSignal, BetLog.value_signal_id == ValueSignal.id)
        .outerjoin(Prediction, ValueSignal.prediction_id == Prediction.id)
        .outerjoin(
            Match,
            # COALESCE lógico: REAL usa bet.match_id; PAPER usa prediction.match_id
            (BetLog.match_id == Match.id) | (
                (BetLog.match_id.is_(None)) & (Prediction.match_id == Match.id)
            ),
        )
        .where(
            BetLog.status == BetStatus.PENDING,
            Match.status == MatchStatus.FINISHED,
        )
    )

    rows = session.execute(stmt).all()

    settled_count = 0
    won_count = 0
    lost_count = 0

    now = datetime.now(tz=UTC)

    for row in rows:
        bet: BetLog = row.BetLog
        match: Match = row.Match

        # Resolver outcome_code: ruta REAL directa o ruta PAPER via prediction
        outcome_code = bet.outcome_code or row.pred_outcome_code
        if outcome_code is None:
            # Sin outcome no se puede liquidar; skip
            continue

        result = _derive_result(match.home_score, match.away_score)
        is_won = outcome_code == result

        bet.status = BetStatus.WON if is_won else BetStatus.LOST
        bet.settled_result = result
        bet.settled_at = now
        bet.pnl = _calc_pnl(bet.stake, float(bet.odds_taken), is_won)

        settled_count += 1
        if is_won:
            won_count += 1
        else:
            lost_count += 1

    session.commit()

    return {"settled": settled_count, "won": won_count, "lost": lost_count}
