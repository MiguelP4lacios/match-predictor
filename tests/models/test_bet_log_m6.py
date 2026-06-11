"""Round-trip tests para m6: BetLog con campos de apuesta REAL.

Escenarios:
  - BetLog con match_id+outcome_code (sin signal) → persiste OK
  - BetLog sin match_id ni value_signal_id → ck_bet_resolvable dispara IntegrityError
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.betting import BetLog
from app.models.competition import Competition
from app.models.enums import BetMode, BetStatus, CompetitionKind, MatchStatus
from app.models.match import Match
from app.models.team import Team


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scheduled_match(session) -> Match:
    """Crea un partido SCHEDULED mínimo para FK de BetLog."""
    comp = Competition(name="M6 Test Comp", kind=CompetitionKind.FRIENDLY)
    session.add(comp)
    session.flush()

    home = Team(name="M6 Home")
    away = Team(name="M6 Away")
    session.add_all([home, away])
    session.flush()

    match = Match(
        competition_id=comp.id,
        match_date=__import__("datetime").date(2026, 7, 1),
        home_team_id=home.id,
        away_team_id=away.id,
        status=MatchStatus.SCHEDULED,
    )
    session.add(match)
    session.flush()
    return match


# ---------------------------------------------------------------------------
# Test 1: BetLog con match_id + outcome_code (sin signal) → OK
# ---------------------------------------------------------------------------


def test_bet_log_real_without_signal_persists(db_session):
    """BetLog mode=REAL con match_id+outcome_code sin value_signal_id persiste."""
    from decimal import Decimal

    match = _make_scheduled_match(db_session)

    bet = BetLog(
        value_signal_id=None,
        match_id=match.id,
        outcome_code="HOME",
        mode=BetMode.REAL,
        stake=Decimal("12000.00"),
        odds_taken=1.40,
        status=BetStatus.PENDING,
    )
    db_session.add(bet)
    db_session.flush()  # debe persistir sin error

    assert bet.id is not None
    assert bet.match_id == match.id
    assert bet.outcome_code == "HOME"
    assert bet.value_signal_id is None


# ---------------------------------------------------------------------------
# Test 2: BetLog sin match_id ni value_signal_id → ck_bet_resolvable
# ---------------------------------------------------------------------------


def test_bet_log_without_resolvable_identity_raises(db_session):
    """INSERT sin value_signal_id ni (match_id, outcome_code) → IntegrityError (CHECK)."""
    from decimal import Decimal

    bet = BetLog(
        value_signal_id=None,
        match_id=None,
        outcome_code=None,
        mode=BetMode.REAL,
        stake=Decimal("1000.00"),
        odds_taken=1.50,
        status=BetStatus.PENDING,
    )
    db_session.add(bet)

    with pytest.raises(IntegrityError):
        db_session.flush()
