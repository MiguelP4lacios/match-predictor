"""Motor de Elo: recorre los partidos jugados en orden cronológico y puebla
`elo_rating` con el rating de cada equipo DESPUÉS de cada partido.

Determinista: re-ejecutar da el mismo resultado (borra y recalcula). El rating
"actual" de un equipo = su última fila en elo_rating. Para predecir un fixture en
fecha D se usa el último rating de cada equipo con rating_date < D (sin look-ahead).
"""

from collections import defaultdict

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.model.elo import (
    DEFAULT_HOME_ADVANTAGE,
    DEFAULT_INITIAL_RATING,
    K_CONTINENTAL,
    K_FRIENDLY,
    K_OTHER_TOURNAMENT,
    K_QUALIFIER_OR_MAJOR,
    K_WORLD_CUP,
    k_factor,
    update_ratings,
)
from app.models import Competition, EloRating, Match, ModelVersion
from app.models.enums import MatchStatus

_VERSION_PREFIX = "elo-v"
_BATCH = 5000


class EloEngine:
    def __init__(
        self,
        session: Session,
        *,
        initial: float = DEFAULT_INITIAL_RATING,
        home_advantage: float = DEFAULT_HOME_ADVANTAGE,
    ) -> None:
        self._session = session
        self._initial = initial
        self._home_advantage = home_advantage

    def compute(self) -> dict[str, int]:
        self._session.execute(delete(EloRating))  # recálculo limpio

        ratings: dict[int, float] = defaultdict(lambda: self._initial)
        # (team_id, fecha) -> rating final del día (sobreescribe si juega 2 veces)
        points: dict[tuple, float] = {}
        n_matches = 0

        for row in self._iter_finished_matches():
            home, away = row.home_team_id, row.away_team_id
            new_home, new_away = update_ratings(
                ratings[home],
                ratings[away],
                row.home_score,
                row.away_score,
                k_factor(row.kind),
                neutral=row.neutral_site,
                home_advantage=self._home_advantage,
            )
            ratings[home] = new_home
            ratings[away] = new_away
            points[(home, row.match_date)] = new_home
            points[(away, row.match_date)] = new_away
            n_matches += 1

        self._bulk_insert(points)
        self._record_version()
        self._session.commit()
        return {
            "matches": n_matches,
            "teams": len(ratings),
            "elo_points": len(points),
        }

    def _iter_finished_matches(self):
        stmt = (
            select(
                Match.home_team_id,
                Match.away_team_id,
                Match.home_score,
                Match.away_score,
                Match.neutral_site,
                Match.match_date,
                Competition.kind,
            )
            .join(Competition, Competition.id == Match.competition_id)
            .where(
                Match.status == MatchStatus.FINISHED,
                Match.home_score.is_not(None),
                Match.away_score.is_not(None),
            )
            .order_by(Match.match_date, Match.id)
        )
        return self._session.execute(stmt).yield_per(2000)

    def _bulk_insert(self, points: dict[tuple, float]) -> None:
        rows = [
            {"team_id": team_id, "rating_date": rating_date, "rating": rating}
            for (team_id, rating_date), rating in points.items()
        ]
        for i in range(0, len(rows), _BATCH):
            self._session.execute(insert(EloRating), rows[i : i + _BATCH])

    def _record_version(self) -> None:
        """Registra los parámetros del cómputo en model_version (D6 — inmutable).

        - Si NO existe ninguna versión → INSERT "elo-v1".
        - Si la última versión tiene los mismos params → reutilizar (recompute
          idempotente no hace spam de versiones).
        - Si los params cambiaron → INSERT "elo-v{N+1}" sin tocar "elo-vN".
        """
        params = {
            "initial_rating": self._initial,
            "home_advantage": self._home_advantage,
            "k": {
                "world_cup": K_WORLD_CUP,
                "continental": K_CONTINENTAL,
                "qualifier_or_major": K_QUALIFIER_OR_MAJOR,
                "other_tournament": K_OTHER_TOURNAMENT,
                "friendly": K_FRIENDLY,
            },
        }
        # Obtener la versión más reciente (nombre lexicográfico: elo-v1 < elo-v2)
        latest = self._session.scalar(
            select(ModelVersion)
            .where(ModelVersion.name.like(f"{_VERSION_PREFIX}%"))
            .order_by(ModelVersion.name.desc())
            .limit(1)
        )
        if latest is None:
            self._session.add(
                ModelVersion(name=f"{_VERSION_PREFIX}1", params_json=params)
            )
            return

        if latest.params_json == params:
            return  # mismos params → reusar, no generar spam

        # Params cambiados → INSERT nueva versión incrementando el número
        try:
            n = int(latest.name[len(_VERSION_PREFIX):])
        except ValueError:
            n = 1
        self._session.add(
            ModelVersion(name=f"{_VERSION_PREFIX}{n + 1}", params_json=params)
        )
