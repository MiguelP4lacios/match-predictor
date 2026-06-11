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

from app.models.betting import BetLeg, BetLog, ValueSignal
from app.models.enums import BetKind, BetStatus, MatchStatus
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
            (BetLog.match_id == Match.id)
            | ((BetLog.match_id.is_(None)) & (Prediction.match_id == Match.id)),
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


def settle_parlays(session: Session) -> dict[str, int]:
    """Liquida todos los parlays PENDING cuyos legs estén resolubles.

    Lógica:
    - Si ALGÚN leg LOST (partido FINISHED, outcome distinto) → parlay LOST, pnl=-stake.
    - Si TODOS los legs WON (partido FINISHED, outcome correcto) → parlay WON,
      pnl = stake × (combined_odds - 1).
    - Si algún partido no está FINISHED → parlay sigue PENDING.

    Idempotente: filtra solo bet_kind=PARLAY y status=PENDING.
    COMMITEA al final (frontera de transacción explícita).

    Returns:
        dict con claves settled, won, lost.
    """
    # Obtener parlays PENDING
    stmt = select(BetLog).where(
        BetLog.bet_kind == BetKind.PARLAY,
        BetLog.status == BetStatus.PENDING,
    )
    parlays = session.scalars(stmt).all()

    settled_count = 0
    won_count = 0
    lost_count = 0
    now = datetime.now(tz=UTC)

    for parlay in parlays:
        # Cargar legs con sus partidos
        legs_stmt = (
            select(BetLeg, Match)
            .join(Match, BetLeg.match_id == Match.id)
            .where(BetLeg.bet_log_id == parlay.id)
        )
        leg_rows = session.execute(legs_stmt).all()

        if not leg_rows:
            continue

        # Determinar estado de cada leg
        any_lost = False
        all_finished_and_won = True

        for leg, match in leg_rows:
            if match.status != MatchStatus.FINISHED:
                # Partido sin jugar → parlay sigue PENDING
                all_finished_and_won = False
                break

            if match.home_score is None or match.away_score is None:
                all_finished_and_won = False
                break

            result = _derive_result(match.home_score, match.away_score)
            if leg.outcome_code != result:
                any_lost = True
                all_finished_and_won = False
                break
        else:
            # Loop completed without break → all legs checked and FINISHED
            pass

        if any_lost:
            parlay.status = BetStatus.LOST
            parlay.settled_result = "LOST"
            parlay.pnl = (-parlay.stake).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            parlay.settled_at = now
            settled_count += 1
            lost_count += 1
        elif all_finished_and_won:
            combined_odds = Decimal(str(parlay.odds_taken))
            profit = parlay.stake * (combined_odds - Decimal("1"))
            parlay.pnl = profit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            parlay.status = BetStatus.WON
            parlay.settled_result = "WON_ALL"
            parlay.settled_at = now
            settled_count += 1
            won_count += 1
        # else: still PENDING (some leg not played yet)

    session.commit()

    return {"settled": settled_count, "won": won_count, "lost": lost_count}
