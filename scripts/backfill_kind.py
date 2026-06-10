"""Backfill competition.kind usando el clasificador compartido (D4).

Reclasifica TODAS las filas de la tabla `competition` usando
`classify_competition_kind` — la misma función que usa la ingesta.
Imprime distribución ANTES y DESPUÉS para evidencia de auditoría.

Idempotente: si se ejecuta de nuevo, el resultado es el mismo.

    docker compose run --rm -T api python scripts/backfill_kind.py
"""

from __future__ import annotations

import sys

from sqlalchemy import text

from app.core.database import SessionLocal
from app.ingestion.classification import classify_competition_kind
from app.models.competition import Competition


def get_distribution(session) -> dict[str, int]:
    rows = session.execute(
        text("SELECT kind, count(*) FROM competition GROUP BY kind ORDER BY count(*) DESC")
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def main() -> None:
    with SessionLocal() as session:
        # ── ANTES ────────────────────────────────────────────────────────────
        before = get_distribution(session)
        total = sum(before.values())
        print(f"\n=== ANTES: distribución competition.kind ({total} filas) ===")
        for kind, cnt in before.items():
            print(f"  {kind:<20} {cnt:>6}")

        # ── Reclasificar ─────────────────────────────────────────────────────
        competitions = session.query(Competition).all()
        changed: list[tuple[str, str, str]] = []  # (name, old_kind, new_kind)

        for comp in competitions:
            new_kind = classify_competition_kind(comp.name)
            old_label = comp.kind.name if comp.kind is not None else "NULL"
            new_label = new_kind.name

            if old_label != new_label:
                changed.append((comp.name, old_label, new_label))
                comp.kind = new_kind

        session.commit()
        print(f"\n→ {len(changed)} filas reclasificadas")

        # ── Muestra de cambios ────────────────────────────────────────────────
        if changed:
            print("\n  Muestra de reclasificaciones (primeras 20):")
            for name, old, new in changed[:20]:
                print(f"  [{old} → {new}]  {name}")

        # ── DESPUÉS ──────────────────────────────────────────────────────────
        after = get_distribution(session)
        total_after = sum(after.values())
        print(f"\n=== DESPUÉS: distribución competition.kind ({total_after} filas) ===")
        for kind, cnt in after.items():
            print(f"  {kind:<20} {cnt:>6}")

        # ── Validaciones de corrección ────────────────────────────────────────
        print("\n=== Validaciones ===")

        world_cup_count = after.get("WORLD_CUP", 0)
        print(f"  WORLD_CUP count: {world_cup_count}  (esperado: 1 — solo 'FIFA World Cup' exacto)")

        null_count = session.execute(
            text("SELECT count(*) FROM competition WHERE kind IS NULL")
        ).scalar()
        print(f"  NULL kind: {null_count}  (esperado: 0)")

        # Verificar que CONIFA/Viva/etc. NO están en WORLD_CUP
        bad_wc = session.execute(
            text(
                "SELECT name FROM competition WHERE kind = 'WORLD_CUP' "
                "AND name != 'FIFA World Cup' "
                "ORDER BY name"
            )
        ).fetchall()
        if bad_wc:
            print(f"  ⚠  No-FIFA en WORLD_CUP ({len(bad_wc)} filas):")
            for row in bad_wc:
                print(f"     - {row[0]}")
        else:
            print("  ✓  Sin torneos no-FIFA en WORLD_CUP")

        if null_count > 0:
            print("ERROR: quedan filas con kind NULL", file=sys.stderr)
            sys.exit(1)

        print("\n✓ Backfill completado correctamente\n")


if __name__ == "__main__":
    main()
