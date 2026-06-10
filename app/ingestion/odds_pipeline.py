"""Pipeline de captura de odds: RawOdds -> tabla `odds` (polimórfica).

Cada captura INSERTA filas nuevas (snapshot con captured_at). El histórico de
snapshots es lo que después permite identificar la closing line (is_closing) y
medir edge contra la probabilidad del modelo.

Cambios vs versión original (D3/D8):
- **Persistir siempre**: si no se encuentra el fixture, se inserta con
  match_id=NULL + source_event_id + commence_time → re-linkeable después.
- **DRAW estricto**: DRAW solo si outcome_name.lower() == "draw". Si el resolver
  devuelve None para un nombre que NO es "Draw" → descartar + log warning.
- **Relink posterior**: `relink_orphan_odds(session)` vincula orphans al fixture
  por par de equipos + ventana commence_time ±1 día.
- **Desambiguación temporal**: cuando dos fixtures comparten el mismo par, se
  elige el más cercano al commence_time del evento.
"""

import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.resolver import TeamResolver
from app.ingestion.sources.base import OddsSource
from app.models import Competition, Match, Odds
from app.models.enums import MarketType, MatchStatus

logger = logging.getLogger(__name__)

_MARKET_MAP = {
    "h2h": MarketType.MATCH_1X2,
    "totals": MarketType.OVER_UNDER,
    "outrights": MarketType.OUTRIGHT_WINNER,
}
_WORLD_CUP_NAME = "FIFA World Cup"

# Ventana temporal para linkear odds a fixture (compensar timezone y calendarios).
_RELINK_WINDOW = timedelta(days=1)

# Nombres de The Odds API que no coinciden con el canónico (martj42).
_NAME_OVERRIDES = {
    "USA": "United States",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
}


def _canonical(name: str) -> str:
    return _NAME_OVERRIDES.get(name, name)


def relink_orphan_odds(session: Session) -> dict[str, int]:
    """Vincula filas de odds con match_id=NULL al fixture correspondiente.

    Estrategia:
      1. Agrupar orphans por source_event_id.
      2. Extraer el par de equipos de los outcomes HOME/AWAY (outcome_team_id).
      3. Buscar partidos SCHEDULED con ese par cuyo kickoff_at esté dentro de
         ±1 día del commence_time.
      4. Si hay exactamente 1 candidato → actualizar match_id (y match.kickoff_at
         si NULL).
      5. Si hay 0 o >1 → omitir + log.

    Returns:
        {"linked": N, "skipped": M}
    """
    orphan_rows = session.scalars(
        select(Odds).where(
            Odds.match_id.is_(None),
            Odds.source_event_id.is_not(None),
            Odds.market_type.in_([MarketType.MATCH_1X2, MarketType.OVER_UNDER]),
        )
    ).all()

    if not orphan_rows:
        return {"linked": 0, "skipped": 0}

    # Agrupar por source_event_id
    events: dict[str, list[Odds]] = {}
    for row in orphan_rows:
        events.setdefault(row.source_event_id, []).append(row)

    linked = 0
    skipped = 0

    for event_id, rows in events.items():
        commence_time = rows[0].commence_time
        if commence_time is None:
            skipped += len(rows)
            continue

        # Extraer par de equipos de HOME/AWAY outcomes
        home_team_id: int | None = None
        away_team_id: int | None = None
        for row in rows:
            if row.outcome_code == "HOME" and row.outcome_team_id is not None:
                home_team_id = row.outcome_team_id
            elif row.outcome_code == "AWAY" and row.outcome_team_id is not None:
                away_team_id = row.outcome_team_id

        if home_team_id is None or away_team_id is None:
            logger.warning("relink: no team pair for event %s, skipping", event_id)
            skipped += len(rows)
            continue

        # Buscar fixtures candidatos: mismo par (ambas orientaciones) + ventana ±1d
        candidates = session.scalars(
            select(Match).where(
                Match.status == MatchStatus.SCHEDULED,
                Match.kickoff_at.is_not(None),
                Match.home_team_id.in_([home_team_id, away_team_id]),
                Match.away_team_id.in_([home_team_id, away_team_id]),
            )
        ).all()

        # Filtrar por ventana temporal (±1 día)
        window_secs = _RELINK_WINDOW.total_seconds()
        in_window = [
            m for m in candidates
            if m.kickoff_at is not None
            and abs((commence_time - m.kickoff_at).total_seconds()) <= window_secs
        ]

        if len(in_window) == 0:
            logger.warning(
                "relink: no match found for event %s (teams %s vs %s, commence %s)",
                event_id,
                home_team_id,
                away_team_id,
                commence_time,
            )
            skipped += len(rows)
            continue

        # Desambiguación: elegir el más cercano en tiempo (D3 spec R2 S3)
        match = min(
            in_window,
            key=lambda m: abs((commence_time - m.kickoff_at).total_seconds()),
        )

        if len(in_window) > 1:
            logger.info(
                "relink: %d candidates for event %s, chose match %d (closest)",
                len(in_window),
                event_id,
                match.id,
            )

        for row in rows:
            row.match_id = match.id

        # Poblar kickoff_at del match desde commence_time si no está seteado
        if match.kickoff_at is None:
            match.kickoff_at = commence_time

        linked += len(rows)

    session.flush()
    return {"linked": linked, "skipped": skipped}


class OddsCapturePipeline:
    def __init__(self, session: Session, source: OddsSource) -> None:
        self._session = session
        self._source = source
        self._resolver = TeamResolver(session)
        # frozenset({home_id, away_id}) -> list[(match_id, home_id, away_id, kickoff_at)]
        self._match_index: dict[frozenset, list[tuple[int, int, int]]] = {}
        self._wc_competition_id: int | None = None
        self._wc_loaded = False

    def capture(self) -> dict[str, object]:
        self._build_match_index()
        inserted = 0
        unlinked: set[str] = set()  # source_event_ids sin fixture

        for ro in self._source.fetch_odds():
            row = self._to_odds(ro)
            if row is None:
                continue
            self._session.add(row)
            inserted += 1
            if row.match_id is None and ro.market_key in ("h2h", "totals"):
                unlinked.add(ro.event_id)

        self._session.flush()
        return {
            "inserted": inserted,
            "unlinked_events": len(unlinked),
        }

    def _resolve(self, name: str):
        return self._resolver.resolve(
            self._source.source,
            name,
            canonical_name=_canonical(name),
            create_missing=False,
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
                source_event_id=ro.event_id,
                commence_time=ro.commence_time,
                is_closing=False,
            )

        # h2h / totals: intentar linkear al fixture; si no hay → persistir con match_id=NULL
        home = self._resolve(ro.home_team)
        away = self._resolve(ro.away_team)

        match_id: int | None = None
        our_home_id: int | None = None
        our_away_id: int | None = None

        if home is not None and away is not None:
            entry = self._match_index.get(frozenset((home.id, away.id)))
            if entry is not None:
                match_id, our_home_id, our_away_id = entry

        # Cuando no hay fixture, usar los equipos del evento para determinar HOME/AWAY
        effective_home_id = our_home_id if our_home_id is not None else (home.id if home else None)
        effective_away_id = our_away_id if our_away_id is not None else (away.id if away else None)

        outcome_code = self._outcome_code(ro, effective_home_id, effective_away_id)

        # outcome_code=None → equipo no resuelto (no-Draw) → descartar
        if outcome_code is None:
            return None

        # Para h2h → guardar outcome_team_id para que relink pueda reconstruir el par.
        outcome_team_id: int | None = None
        if market_type is MarketType.MATCH_1X2 and outcome_code in ("HOME", "AWAY"):
            if outcome_code == "HOME" and home is not None:
                outcome_team_id = home.id
            elif outcome_code == "AWAY" and away is not None:
                outcome_team_id = away.id

        return Odds(
            match_id=match_id,
            market_type=market_type,
            outcome_code=outcome_code,
            outcome_team_id=outcome_team_id,
            line=ro.line,
            bookmaker=ro.bookmaker,
            decimal_odds=ro.price,
            captured_at=ro.captured_at,
            source_event_id=ro.event_id,
            commence_time=ro.commence_time,
            is_closing=False,
        )

    def _outcome_code(self, ro, our_home_id: int | None, our_away_id: int | None) -> str | None:
        """Retorna 'HOME', 'AWAY', 'DRAW', 'OVER', 'UNDER', o None (descartar).

        DRAW SOLO cuando outcome_name.lower() == 'draw' (D3 estricto).
        Si el equipo no se resuelve y NO es 'Draw' → None + log warning.
        """
        if ro.market_key == "totals":
            return ro.outcome_name.upper()  # OVER / UNDER

        if ro.market_key == "h2h":
            if ro.outcome_name.lower() == "draw":
                return "DRAW"

            team = self._resolve(ro.outcome_name)
            if team is None:
                logger.warning(
                    "odds_pipeline: outcome_name '%s' (event %s) no pudo resolverse "
                    "a un equipo conocido — odds descartadas",
                    ro.outcome_name,
                    ro.event_id,
                )
                return None  # NO asignar DRAW a un nombre irresoluto

            if our_home_id is not None and team.id == our_home_id:
                return "HOME"
            if our_away_id is not None and team.id == our_away_id:
                return "AWAY"

            # El equipo se resolvió pero no es ninguno de los dos lados del fixture
            logger.warning(
                "odds_pipeline: outcome team %d ('%s') no corresponde a ningún "
                "lado del fixture (home=%s, away=%s) — odds descartadas",
                team.id,
                ro.outcome_name,
                our_home_id,
                our_away_id,
            )
            return None

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
            select(
                Match.id,
                Match.home_team_id,
                Match.away_team_id,
                Match.kickoff_at,
            )
            .join(Competition, Competition.id == Match.competition_id)
            .where(
                Match.status == MatchStatus.SCHEDULED,
                Competition.name == _WORLD_CUP_NAME,
            )
        ).all()
        for match_id, home_id, away_id, _kickoff_at in rows:
            key = frozenset((home_id, away_id))
            # Si hay varios fixtures del mismo par, guardar el más reciente
            # (disambiguation real la hace relink_orphan_odds con ventana ±1d)
            self._match_index[key] = (match_id, home_id, away_id)
