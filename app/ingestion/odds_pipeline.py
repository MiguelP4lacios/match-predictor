"""Pipeline de captura de odds: RawOdds -> tabla `odds` (polimórfica).

Cada captura INSERTA filas nuevas (snapshot con captured_at). El histórico de
snapshots es lo que después permite identificar la closing line (is_closing) y
medir edge contra la probabilidad del modelo.

Linkeo robusto a los fixtures del Mundial:
- por PAR de equipos (frozenset), no por fecha: The Odds API usa hora UTC y un
  partido nocturno cae al día siguiente -> la fecha no es confiable.
- la orientación local/visitante se toma de NUESTRO fixture (en cancha neutral
  del Mundial el "home" de la casa es arbitrario).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.resolver import TeamResolver
from app.ingestion.sources.base import OddsSource
from app.models import Competition, Match, Odds
from app.models.enums import MarketType, MatchStatus

_MARKET_MAP = {
    "h2h": MarketType.MATCH_1X2,
    "totals": MarketType.OVER_UNDER,
    "outrights": MarketType.OUTRIGHT_WINNER,
}
_WORLD_CUP_NAME = "FIFA World Cup"

# Nombres de The Odds API que no coinciden con el canónico (martj42).
_NAME_OVERRIDES = {
    "USA": "United States",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
}


def _canonical(name: str) -> str:
    return _NAME_OVERRIDES.get(name, name)


class OddsCapturePipeline:
    def __init__(self, session: Session, source: OddsSource) -> None:
        self._session = session
        self._source = source
        self._resolver = TeamResolver(session)
        # frozenset({home_id, away_id}) -> (match_id, home_id, away_id)
        self._match_index: dict[frozenset, tuple[int, int, int]] = {}
        self._wc_competition_id: int | None = None
        self._wc_loaded = False

    def capture(self) -> dict[str, object]:
        self._build_match_index()
        inserted = 0
        unlinked: set[tuple[str, str]] = set()
        for ro in self._source.fetch_odds():
            row = self._to_odds(ro)
            if row is None:
                if ro.market_key in ("h2h", "totals"):
                    unlinked.add((ro.home_team, ro.away_team))
                continue
            self._session.add(row)
            inserted += 1
        self._session.commit()
        return {
            "inserted": inserted,
            "unlinked_events": len(unlinked),
            "unlinked_sample": sorted(unlinked)[:15],
        }

    def _resolve(self, name: str):
        return self._resolver.resolve(
            self._source.source, name, canonical_name=_canonical(name), create_missing=False
        )

    def _to_odds(self, ro) -> Odds | None:
        market_type = _MARKET_MAP.get(ro.market_key)
        if market_type is None:
            return None

        if market_type is MarketType.OUTRIGHT_WINNER:
            team = self._resolve(ro.outcome_name)
            comp_id = self._world_cup_id()
            if team is None or comp_id is None:
                return None
            return Odds(
                competition_id=comp_id,
                market_type=market_type,
                outcome_team_id=team.id,
                bookmaker=ro.bookmaker,
                decimal_odds=ro.price,
                captured_at=ro.captured_at,
                is_closing=False,
            )

        # h2h / totals -> enganchar al fixture por par de equipos.
        home = self._resolve(ro.home_team)
        away = self._resolve(ro.away_team)
        if home is None or away is None:
            return None
        entry = self._match_index.get(frozenset((home.id, away.id)))
        if entry is None:
            return None
        match_id, our_home_id, our_away_id = entry

        return Odds(
            match_id=match_id,
            market_type=market_type,
            outcome_code=self._outcome_code(ro, our_home_id, our_away_id),
            line=ro.line,
            bookmaker=ro.bookmaker,
            decimal_odds=ro.price,
            captured_at=ro.captured_at,
            is_closing=False,
        )

    def _outcome_code(self, ro, our_home_id: int, our_away_id: int) -> str | None:
        if ro.market_key == "totals":
            return ro.outcome_name.upper()  # OVER / UNDER
        if ro.market_key == "h2h":
            team = self._resolve(ro.outcome_name)  # None para "Draw"
            if team is None:
                return "DRAW"
            if team.id == our_home_id:
                return "HOME"
            if team.id == our_away_id:
                return "AWAY"
            return "DRAW"
        return None

    def _world_cup_id(self) -> int | None:
        if not self._wc_loaded:
            comp = self._session.scalar(
                select(Competition).where(Competition.name == _WORLD_CUP_NAME)
            )
            self._wc_competition_id = comp.id if comp else None
            self._wc_loaded = True
        return self._wc_competition_id

    def _build_match_index(self) -> None:
        rows = self._session.execute(
            select(Match.id, Match.home_team_id, Match.away_team_id)
            .join(Competition, Competition.id == Match.competition_id)
            .where(
                Match.status == MatchStatus.SCHEDULED,
                Competition.name == _WORLD_CUP_NAME,
            )
        ).all()
        for match_id, home_id, away_id in rows:
            self._match_index[frozenset((home_id, away_id))] = (
                match_id,
                home_id,
                away_id,
            )
