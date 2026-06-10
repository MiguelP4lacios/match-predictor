"""Router de grupos WC2026 — solo lectura.

GET /api/v1/groups        — todos los grupos con standings al vuelo.
GET /api/v1/groups/{name} — detalle: standings + fixtures con predicciones.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import FixtureItem, GroupDetail, GroupItem, StandingRowSchema
from app.core.database import get_session
from app.model.standings import MatchResult, TeamRef, compute_standings
from app.models.enums import MarketType, MatchStatus
from app.models.match import Match
from app.models.model import Prediction
from app.models.tournament import GroupTeam, TournamentGroup

router = APIRouter(tags=["groups"])


def _build_standing_rows(group: TournamentGroup, session: Session) -> list[StandingRowSchema]:
    """Calcula standings al vuelo desde matches FINISHED del grupo."""
    members = [TeamRef(team_id=gt.team_id, name=gt.team.name) for gt in group.members]

    finished_matches = [m for m in group.matches if m.status == MatchStatus.FINISHED]
    results = [
        MatchResult(
            home_id=m.home_team_id,
            away_id=m.away_team_id,
            home_score=m.home_score or 0,
            away_score=m.away_score or 0,
        )
        for m in finished_matches
        if m.home_score is not None and m.away_score is not None
    ]

    rows = compute_standings(members, results)
    return [
        StandingRowSchema(
            team_name=r.team_name,
            pj=r.pj,
            g=r.g,
            e=r.e,
            p=r.p,
            gf=r.gf,
            gc=r.gc,
            dg=r.dg,
            pts=r.pts,
        )
        for r in rows
    ]


def _load_groups(session: Session) -> list[TournamentGroup]:
    """Carga todos los grupos con miembros (team.name) y matches del grupo."""
    stmt = (
        select(TournamentGroup)
        .options(
            selectinload(TournamentGroup.members).selectinload(GroupTeam.team),
            selectinload(TournamentGroup.matches),
        )
        .order_by(TournamentGroup.name)
    )
    return list(session.scalars(stmt).all())


@router.get("/groups", response_model=list[GroupItem])
def list_groups(
    session: Session = Depends(get_session),  # noqa: B008
) -> list[GroupItem]:
    """Todos los grupos con equipos y tabla de posiciones actual.

    Standings calculados al vuelo desde FINISHED matches (sin tabla persistida).
    Zero llamadas externas.
    """
    groups = _load_groups(session)

    return [
        GroupItem(
            name=g.name,
            teams=[gt.team.name for gt in g.members],
            standings=_build_standing_rows(g, session),
        )
        for g in groups
    ]


@router.get("/groups/{name}", response_model=GroupDetail)
def group_detail(
    name: str,
    session: Session = Depends(get_session),  # noqa: B008
) -> GroupDetail:
    """Detalle de un grupo: standings + fixtures con predicciones 1X2.

    Normaliza la letra a mayúscula. Devuelve 404 si el grupo no existe.
    """
    name_upper = name.upper()

    stmt = (
        select(TournamentGroup)
        .options(
            selectinload(TournamentGroup.members).selectinload(GroupTeam.team),
            selectinload(TournamentGroup.matches).selectinload(Match.home_team),
            selectinload(TournamentGroup.matches).selectinload(Match.away_team),
        )
        .where(TournamentGroup.name == name_upper)
    )
    group = session.scalars(stmt).first()

    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    standings = _build_standing_rows(group, session)
    teams = [gt.team.name for gt in group.members]

    # Predicciones 1X2 para los fixtures del grupo — anti-N+1
    match_ids = [m.id for m in group.matches]
    pred_index: dict[int, dict[str, Prediction]] = {}
    if match_ids:
        preds_stmt = select(Prediction).where(
            Prediction.match_id.in_(match_ids),
            Prediction.market_type == MarketType.MATCH_1X2,
        )
        for p in session.scalars(preds_stmt).all():
            pred_index.setdefault(p.match_id, {})[p.outcome_code or ""] = p

    fixtures = []
    for m in sorted(group.matches, key=lambda x: (x.match_date, x.id)):
        preds = pred_index.get(m.id, {})
        p_home = preds.get("HOME")
        p_draw = preds.get("DRAW")
        p_away = preds.get("AWAY")
        fixtures.append(
            FixtureItem(
                id=m.id,
                match_date=m.match_date,
                kickoff_at=m.kickoff_at,
                home_team=m.home_team.name,
                away_team=m.away_team.name,
                status=str(m.status),
                home_score=m.home_score,
                away_score=m.away_score,
                p_home=float(p_home.probability) if p_home else None,
                p_draw=float(p_draw.probability) if p_draw else None,
                p_away=float(p_away.probability) if p_away else None,
            )
        )

    return GroupDetail(
        name=group.name,
        teams=teams,
        standings=standings,
        fixtures=fixtures,
    )
