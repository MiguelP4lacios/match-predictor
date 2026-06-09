"""Dedup script — prerequisito de M3.

Detecta y elimina duplicados en `match(match_date, home_team_id, away_team_id)`
y equipos con nombre case-duplicado antes de crear los UNIQUE constraints de M3.

Regla (D7): conservar MIN(id), re-apuntar FKs hijas a ese id, borrar perdedores.

Uso:
    docker compose run --rm api python scripts/dedup.py [--dry-run]

--dry-run: solo reporta, NO modifica la BD.
"""

import logging
import sys
from textwrap import dedent

from sqlalchemy import text

from app.core.database import engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

DRY_RUN = "--dry-run" in sys.argv


def _dry(label: str) -> str:
    return f"[DRY-RUN] {label}" if DRY_RUN else label


def dedup_matches(conn) -> int:
    """Elimina filas duplicadas de `match` conservando MIN(id) por grupo.

    Retorna el número de filas eliminadas (0 en dry-run).
    """
    rows = conn.execute(text(dedent("""
        SELECT
            match_date,
            home_team_id,
            away_team_id,
            array_agg(id ORDER BY id) AS ids,
            array_agg(home_score ORDER BY id) AS home_scores,
            array_agg(away_score ORDER BY id) AS away_scores,
            array_agg(status ORDER BY id) AS statuses
        FROM match
        GROUP BY match_date, home_team_id, away_team_id
        HAVING count(*) > 1
        ORDER BY match_date, home_team_id
    """))).fetchall()

    if not rows:
        log.info("match: sin duplicados — OK")
        return 0

    surplus_ids = []
    for r in rows:
        keep_id = r.ids[0]
        remove_ids = r.ids[1:]
        surplus_ids.extend(remove_ids)
        log.warning(
            "Duplicado en match: date=%s home_id=%s away_id=%s | "
            "keep=%d (score %s-%s %s) | remove=%s (scores %s-%s %s)",
            r.match_date, r.home_team_id, r.away_team_id,
            keep_id, r.home_scores[0], r.away_scores[0], r.statuses[0],
            remove_ids,
            r.home_scores[1:], r.away_scores[1:], r.statuses[1:],
        )

        # Re-apuntar FKs hijas antes de borrar
        for tbl, col in [
            ("goal_event", "match_id"),
            ("shootout", "match_id"),
            ("prediction", "match_id"),
            ("odds", "match_id"),
            ("match_team_stats", "match_id"),
        ]:
            n = conn.execute(text(
                f"SELECT count(*) FROM {tbl} WHERE {col} = ANY(:ids)"
            ), {"ids": remove_ids}).scalar()
            if n > 0:
                log.info("  Re-apuntando %d filas en %s.%s → %d", n, tbl, col, keep_id)
                if not DRY_RUN:
                    conn.execute(text(
                        f"UPDATE {tbl} SET {col} = :keep WHERE {col} = ANY(:ids)"
                    ), {"keep": keep_id, "ids": remove_ids})

    log.info(
        "%s %d filas duplicadas en match (ids: %s)",
        _dry("Eliminando"), len(surplus_ids), surplus_ids,
    )
    if not DRY_RUN:
        conn.execute(
            text("DELETE FROM match WHERE id = ANY(:ids)"),
            {"ids": surplus_ids},
        )
    return len(surplus_ids)


def dedup_teams_lower(conn) -> int:
    """Detecta equipos con nombre case-duplicado. NO los elimina automáticamente.

    La eliminación de equipos es peligrosa (FKs en match, elo_rating, etc.).
    Si hay case-duplicados, el script aborta con instrucciones manuales.
    """
    rows = conn.execute(text(dedent("""
        SELECT lower(name) AS lower_name, array_agg(id ORDER BY id) AS ids,
               array_agg(name ORDER BY id) AS names
        FROM team
        GROUP BY lower(name)
        HAVING count(*) > 1
        ORDER BY lower(name)
    """))).fetchall()

    if not rows:
        log.info("team: sin duplicados de nombre (case-insensitive) — OK")
        return 0

    log.error(
        "BLOQUEANTE: %d grupos de equipos con nombre case-duplicado encontrados:",
        len(rows),
    )
    for r in rows:
        log.error("  '%s' → ids=%s names=%s", r.lower_name, r.ids, r.names)
    log.error(
        "Eliminar equipos duplicados requiere revisión manual (FKs en match, elo_rating, etc.)."
    )
    log.error(
        "Pasos: (1) unificar team_alias, (2) re-apuntar match.home/away_team_id, "
        "(3) borrar el equipo extra, (4) volver a correr este script."
    )
    raise SystemExit(1)


def main() -> None:
    if DRY_RUN:
        log.info("=== MODO DRY-RUN: no se realizarán cambios en la BD ===")
    else:
        log.info("=== Ejecutando dedup — los cambios serán permanentes ===")

    with engine.begin() as conn:
        n_match = dedup_matches(conn)
        dedup_teams_lower(conn)

    log.info(
        "Dedup completado: %d filas eliminadas de match. "
        "Listo para M3 (UNIQUE constraints).",
        n_match,
    )


if __name__ == "__main__":
    main()
