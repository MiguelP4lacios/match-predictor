"""TeamResolver — el corazón de la capa DataSource provider-agnostic.

Traduce (source, external_id) -> Team canónico vía la tabla team_alias. Cuando una
fuente backbone (martj42) menciona un equipo por primera vez, crea el Team canónico
y registra el alias. Fuentes posteriores (eloratings, statsbomb) se enganchan al
mismo Team por nombre o por su propio alias. Cachea en memoria para no golpear la
BD en cada una de las ~49k filas.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Team, TeamAlias
from app.models.enums import DataSource


class TeamResolver:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._alias_cache: dict[tuple[DataSource, str], int] = {}
        self._name_cache: dict[str, int] = {}

    def resolve(
        self,
        source: DataSource,
        external_id: str,
        canonical_name: str | None = None,
        create_missing: bool = True,
    ) -> Team | None:
        """Resuelve el Team canónico. Con create_missing=False (p.ej. odds) NO crea
        equipos nuevos: si el nombre no matchea uno existente, devuelve None y la
        cotización se ignora — evita duplicar 'USA' vs 'United States'."""
        canonical_name = canonical_name or external_id
        cache_key = (source, external_id)

        if cache_key in self._alias_cache:
            return self._session.get(Team, self._alias_cache[cache_key])

        alias = self._session.scalar(
            select(TeamAlias).where(
                TeamAlias.source == source,
                TeamAlias.external_id == external_id,
            )
        )
        if alias is not None:
            self._alias_cache[cache_key] = alias.team_id
            return self._session.get(Team, alias.team_id)

        team = self._get_or_create_team(canonical_name, create_missing)
        if team is None:
            return None
        self._session.add(
            TeamAlias(team_id=team.id, source=source, external_id=external_id)
        )
        self._alias_cache[cache_key] = team.id
        return team

    def _get_or_create_team(
        self, canonical_name: str, create_missing: bool = True
    ) -> Team | None:
        norm = canonical_name.strip()
        key = norm.lower()

        if key in self._name_cache:
            return self._session.get(Team, self._name_cache[key])

        # Case-insensitive lookup usando el índice funcional uq_team_name_lower (D7).
        # Evita duplicar "Argentina" y "argentina" como dos equipos distintos.
        team = self._session.scalar(
            select(Team).where(func.lower(Team.name) == norm.lower())
        )
        if team is None:
            if not create_missing:
                return None
            team = Team(name=norm)
            self._session.add(team)
            self._session.flush()  # asigna team.id

        self._name_cache[key] = team.id
        return team
