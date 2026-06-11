"""Modelos SQLAlchemy. Importar todo acá puebla Base.metadata para Alembic."""

from app.models.base import Base
from app.models.betting import BetLeg, BetLog, ValueSignal
from app.models.competition import Competition
from app.models.match import GoalEvent, Match, Shootout
from app.models.model import ModelVersion, Prediction
from app.models.odds import Odds
from app.models.stats import EloRating, MatchTeamStats
from app.models.sync import SyncLog
from app.models.team import Team, TeamAlias
from app.models.tournament import GroupTeam, TournamentGroup

__all__ = [
    "Base",
    "Team",
    "TeamAlias",
    "Competition",
    "Match",
    "GoalEvent",
    "Shootout",
    "EloRating",
    "MatchTeamStats",
    "TournamentGroup",
    "GroupTeam",
    "Odds",
    "ModelVersion",
    "Prediction",
    "ValueSignal",
    "BetLog",
    "BetLeg",
    "SyncLog",
]
