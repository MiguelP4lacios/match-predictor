"""Pipeline de ingesta de resultados (Extract -> Transform -> Load).

Transform = resolver identidad de equipos (TeamResolver) y mapear el texto libre
`tournament` a una Competition con su `kind`. Load = upsert en la BD + registro en
sync_log para idempotencia (no re-cargar lo ya cargado).
"""

from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.ingestion.resolver import TeamResolver
from app.ingestion.sources.base import GoalSource, ResultsSource, ShootoutSource
from app.models import Competition, GoalEvent, Match, Shootout, SyncLog
from app.models.enums import CompetitionKind, MatchStage, MatchStatus

_BATCH = 1000


def infer_competition_kind(tournament: str) -> CompetitionKind:
    """Mapea el texto libre de martj42 a un kind. El orden importa:
    'FIFA World Cup qualification' contiene 'world cup' pero es QUALIFIER."""
    t = tournament.lower()
    if "qualification" in t or "qualifier" in t:
        return CompetitionKind.QUALIFIER
    if "nations league" in t:
        return CompetitionKind.NATIONS_LEAGUE
    if "world cup" in t:
        return CompetitionKind.WORLD_CUP
    if "friendly" in t:
        return CompetitionKind.FRIENDLY
    return CompetitionKind.CONTINENTAL


def infer_stage(tournament: str) -> MatchStage | None:
    """Stage grueso a partir del torneo (martj42 no trae ronda)."""
    t = tournament.lower()
    if "friendly" in t:
        return MatchStage.FRIENDLY
    if "qualification" in t or "qualifier" in t:
        return MatchStage.QUALIFIER
    return None


class ResultsIngestionPipeline:
    def __init__(self, session: Session, source: ResultsSource) -> None:
        self._session = session
        self._source = source
        self._resolver = TeamResolver(session)
        self._competitions: dict[str, int] = {}
        self._match_index: dict[tuple, int] = {}

    def run(self, *, force: bool = False) -> dict[str, object]:
        resource = f"{self._source.source.value}:results"
        if not force and self._already_synced(resource):
            return {"skipped": True, "reason": "ya sincronizado (usar force=True)"}

        n_matches = self._load_matches()
        self._build_match_index()
        n_goals = self._load_goals()
        n_shootouts = self._load_shootouts()
        self._mark_synced(resource)
        self._session.commit()

        return {
            "skipped": False,
            "teams": len(self._resolver._name_cache),
            "competitions": len(self._competitions),
            "matches": n_matches,
            "goals": n_goals,
            "shootouts": n_shootouts,
        }

    # --- Load steps ---

    def _load_matches(self) -> int:
        count = 0
        for rm in self._source.fetch_matches():
            home = self._resolver.resolve(rm.source, rm.home_team)
            away = self._resolver.resolve(rm.source, rm.away_team)
            status = (
                MatchStatus.FINISHED
                if rm.home_score is not None
                else MatchStatus.SCHEDULED
            )
            self._session.add(
                Match(
                    competition_id=self._competition_id(rm.tournament),
                    match_date=rm.match_date,
                    home_team_id=home.id,
                    away_team_id=away.id,
                    neutral_site=rm.neutral,
                    stage=infer_stage(rm.tournament),
                    status=status,
                    home_score=rm.home_score,
                    away_score=rm.away_score,
                    city=rm.city,
                    country=rm.country,
                )
            )
            count += 1
            if count % _BATCH == 0:
                self._session.flush()
        self._session.flush()
        return count

    def _load_goals(self) -> int:
        if not isinstance(self._source, GoalSource):
            return 0
        count = skipped = 0
        for rg in self._source.fetch_goals():
            home = self._resolver.resolve(rg.source, rg.home_team)
            away = self._resolver.resolve(rg.source, rg.away_team)
            scoring = self._resolver.resolve(rg.source, rg.scoring_team)
            match_id = self._match_index.get((rg.match_date, home.id, away.id))
            if match_id is None:
                skipped += 1
                continue
            self._session.add(
                GoalEvent(
                    match_id=match_id,
                    team_id=scoring.id,
                    scorer_name=rg.scorer,
                    minute=rg.minute,
                    own_goal=rg.own_goal,
                    penalty=rg.penalty,
                )
            )
            count += 1
            if count % _BATCH == 0:
                self._session.flush()
        self._session.flush()
        return count

    def _load_shootouts(self) -> int:
        if not isinstance(self._source, ShootoutSource):
            return 0
        count = 0
        for rs in self._source.fetch_shootouts():
            home = self._resolver.resolve(rs.source, rs.home_team)
            away = self._resolver.resolve(rs.source, rs.away_team)
            match_id = self._match_index.get((rs.match_date, home.id, away.id))
            if match_id is None:
                continue
            winner = self._resolver.resolve(rs.source, rs.winner)
            self._session.add(Shootout(match_id=match_id, winner_team_id=winner.id))
            count += 1
            if count % _BATCH == 0:
                self._session.flush()
        self._session.flush()

        # El flag went_to_penalties no viene en results.csv: se deriva de la
        # presencia de un shootout. Un solo UPDATE lo deja consistente.
        self._session.execute(
            update(Match)
            .where(Match.id.in_(select(Shootout.match_id)))
            .values(went_to_penalties=True)
        )
        return count

    # --- Helpers ---

    def _competition_id(self, tournament: str) -> int:
        if tournament in self._competitions:
            return self._competitions[tournament]
        comp = self._session.scalar(
            select(Competition).where(Competition.name == tournament)
        )
        if comp is None:
            comp = Competition(name=tournament, kind=infer_competition_kind(tournament))
            self._session.add(comp)
            self._session.flush()
        self._competitions[tournament] = comp.id
        return comp.id

    def _build_match_index(self) -> None:
        rows = self._session.execute(
            select(
                Match.match_date,
                Match.home_team_id,
                Match.away_team_id,
                Match.id,
            )
        ).all()
        for match_date, home_id, away_id, match_id in rows:
            self._match_index[(match_date, home_id, away_id)] = match_id

    def _already_synced(self, resource: str) -> bool:
        existing = self._session.scalar(
            select(SyncLog).where(
                SyncLog.resource == resource,
                SyncLog.source == self._source.source,
            )
        )
        return existing is not None and existing.last_fetched_at is not None

    def _mark_synced(self, resource: str) -> None:
        existing = self._session.scalar(
            select(SyncLog).where(
                SyncLog.resource == resource,
                SyncLog.source == self._source.source,
            )
        )
        now = datetime.now(UTC).replace(tzinfo=None)
        if existing is None:
            self._session.add(
                SyncLog(
                    resource=resource,
                    source=self._source.source,
                    last_fetched_at=now,
                    status="ok",
                )
            )
        else:
            existing.last_fetched_at = now
            existing.status = "ok"
