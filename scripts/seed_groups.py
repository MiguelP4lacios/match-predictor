"""Seed de grupos del Mundial 2026 — sorteo FIFA del 2025-12-05.

Ejecutar:
    docker compose run --rm api python scripts/seed_groups.py

Algoritmo:
  1. Selecciona fixtures WC2026 SCHEDULED (stage IS NULL OR stage=GROUP).
  2. Deriva componentes conexas via union-find (app.model.group_utils).
  3. Aserción dura: exactamente 12 componentes × 4 equipos.
  4. Mapea cada componente a la letra oficial via `_OFFICIAL_GROUPS`.
  5. Upsert transaccional: TournamentGroup (12) + GroupTeam (48).
  6. Backfill match.stage=GROUP + match.group_id (72 partidos).
  7. Imprime tabla letra → equipos para verificación del usuario.

Idempotente: re-ejecutar produce el mismo resultado sin errores.

Nombres canónicos verificados contra `SELECT DISTINCT name FROM team WHERE id IN
(SELECT home_team_id ... UNION SELECT away_team_id ...)` para fixtures WC2026.
Correcciones respecto al sorteo original:
  - Czechia     → Czech Republic  (nombre canónico en la BD)
  - Türkiye     → Turkey          (nombre canónico en la BD)
  - Curaçao     → Curaçao         (con acento, coincide con la BD)
  - Ivory Coast → Ivory Coast     ✓ (coincide)
  - DR Congo    → DR Congo        ✓ (coincide)
"""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.model.group_utils import derive_components
from app.models import GroupTeam, Match, Team, TournamentGroup
from app.models.enums import MatchStage, MatchStatus

# ID de "FIFA World Cup" en la BD (martj42 histórico).
_WC_COMPETITION_ID = 23
_WC_SEASON_YEAR = 2026

# Sorteo oficial FIFA 2025-12-05 — letras A–L con nombres canónicos BD.
# Keyed por frozenset para matching insensible al orden.
_OFFICIAL_GROUPS: dict[frozenset[str], str] = {
    frozenset({"Mexico", "South Africa", "South Korea", "Czech Republic"}): "A",
    frozenset({"Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"}): "B",
    frozenset({"Brazil", "Morocco", "Haiti", "Scotland"}): "C",
    frozenset({"United States", "Paraguay", "Australia", "Turkey"}): "D",
    frozenset({"Germany", "Curaçao", "Ivory Coast", "Ecuador"}): "E",
    frozenset({"Netherlands", "Japan", "Sweden", "Tunisia"}): "F",
    frozenset({"Belgium", "Egypt", "Iran", "New Zealand"}): "G",
    frozenset({"Spain", "Cape Verde", "Saudi Arabia", "Uruguay"}): "H",
    frozenset({"France", "Senegal", "Iraq", "Norway"}): "I",
    frozenset({"Argentina", "Algeria", "Austria", "Jordan"}): "J",
    frozenset({"Portugal", "DR Congo", "Uzbekistan", "Colombia"}): "K",
    frozenset({"England", "Croatia", "Ghana", "Panama"}): "L",
}


def seed_groups(
    session: Session,
    *,
    competition_id: int = _WC_COMPETITION_ID,
    season_year: int = _WC_SEASON_YEAR,
    official_groups: dict[frozenset[str], str] | None = None,
) -> None:
    """Inserta grupos y backfills stage=GROUP para los fixtures del torneo.

    Args:
        session:        sesión SQLAlchemy (se hace flush/commit desde el caller).
        competition_id: ID de la competición en la BD.
        season_year:    Año del torneo (para `tournament_group.season_year`).
        official_groups: Mapping frozenset(nombres) → letra. Por defecto usa
                         el sorteo oficial WC2026. Inyectable en tests.

    Raises:
        AssertionError: si el grafo no produce exactamente 12 componentes × 4.
        KeyError:       si una componente no está en el mapping oficial.
    """
    if official_groups is None:
        official_groups = _OFFICIAL_GROUPS

    # 1. Seleccionar fixtures SCHEDULED (idempotente: acepta también stage=GROUP)
    from sqlalchemy import or_, select

    fixtures = session.execute(
        select(Match).where(
            Match.competition_id == competition_id,
            Match.status == MatchStatus.SCHEDULED,
            or_(Match.stage.is_(None), Match.stage == MatchStage.GROUP),
        )
    ).scalars().all()

    if not fixtures:
        raise ValueError(
            f"No se encontraron fixtures SCHEDULED para competition_id={competition_id}. "
            "Verificar que los datos estén cargados."
        )

    # 2. Recopilar nombres de equipos (via FK team_id → name)
    team_ids = set()
    for m in fixtures:
        team_ids.add(m.home_team_id)
        team_ids.add(m.away_team_id)

    teams_by_id: dict[int, str] = {
        t.id: t.name
        for t in session.execute(
            select(Team).where(Team.id.in_(team_ids))
        ).scalars().all()
    }

    # 3. Construir aristas (nombre_local, nombre_visitante)
    edges = [
        (teams_by_id[m.home_team_id], teams_by_id[m.away_team_id])
        for m in fixtures
        if m.home_team_id in teams_by_id and m.away_team_id in teams_by_id
    ]

    # 4. Union-find → 12 componentes × 4 (aserción dura en derive_components)
    components = derive_components(edges)

    # 5. Mapear componentes a letras
    letter_to_teams: dict[str, frozenset[str]] = {}
    for comp in components:
        key = frozenset(comp)
        if key not in official_groups:
            sorted_names = sorted(comp)
            raise KeyError(
                f"Componente sin mapping oficial: {sorted_names}. "
                "Verificar nombres canónicos en _OFFICIAL_GROUPS."
            )
        letter = official_groups[key]
        letter_to_teams[letter] = key

    # 6. Nombre → team_id (invertido)
    team_id_by_name: dict[str, int] = {v: k for k, v in teams_by_id.items()}

    # 7. Upsert transaccional: TournamentGroup + GroupTeam + backfill match
    for letter, team_names in sorted(letter_to_teams.items()):
        # Upsert TournamentGroup
        grp_stmt = (
            pg_insert(TournamentGroup)
            .values(
                competition_id=competition_id,
                season_year=season_year,
                name=letter,
            )
            .on_conflict_do_nothing(constraint="uq_group_comp_season_name")
            .returning(TournamentGroup.id)
        )
        grp_id = session.execute(grp_stmt).scalar()

        if grp_id is None:
            # Ya existía — recuperar el id
            from sqlalchemy import select as _select

            grp_id = session.execute(
                _select(TournamentGroup.id).where(
                    TournamentGroup.competition_id == competition_id,
                    TournamentGroup.season_year == season_year,
                    TournamentGroup.name == letter,
                )
            ).scalar_one()

        # Upsert GroupTeam para cada equipo del grupo
        for tname in team_names:
            tid = team_id_by_name[tname]
            session.execute(
                pg_insert(GroupTeam)
                .values(group_id=grp_id, team_id=tid)
                .on_conflict_do_nothing(constraint="uq_group_team")
            )

        # Backfill match.stage + match.group_id
        for m in fixtures:
            if (
                teams_by_id[m.home_team_id] in team_names
                and teams_by_id[m.away_team_id] in team_names
            ):
                m.stage = MatchStage.GROUP
                m.group_id = grp_id

    session.flush()

    # 8. Imprimir tabla para verificación del usuario
    print(f"\n{'='*60}")
    print(f"Seed grupos WC{season_year} — competition_id={competition_id}")
    print(f"{'='*60}")
    for letter in sorted(letter_to_teams):
        teams_sorted = sorted(letter_to_teams[letter])
        print(f"  Grupo {letter}: {', '.join(teams_sorted)}")
    print(f"{'='*60}")
    print(f"Total: {len(letter_to_teams)} grupos × 4 equipos\n")


def main() -> None:
    """Punto de entrada para ejecución directa."""
    from app.core.database import SessionLocal

    with SessionLocal() as session:
        seed_groups(session)
        session.commit()
        print("Seed completado y commiteado.")


if __name__ == "__main__":
    main()
