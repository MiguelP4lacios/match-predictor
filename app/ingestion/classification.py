"""Clasificador puro de torneos → CompetitionKind (D4).

`classify_competition_kind(name) -> CompetitionKind` + `CONTINENTAL_CHAMPIONSHIPS`.

Compartido por `pipeline.py` (ingesta) y `scripts/backfill_kind.py` —
UNA sola implementación, sin lógica duplicada. Función PURA: sin estado,
sin BD, sin LLM.

Orden de prioridad (el orden importa):
  1. qualification/qualifier → QUALIFIER   (precede a "world cup")
  2. nations league          → NATIONS_LEAGUE
  3. "FIFA World Cup" EXACTO → WORLD_CUP   (excluye CONIFA, Viva, Beach Soccer, etc.)
  4. friendly                → FRIENDLY
  5. nombre en whitelist     → CONTINENTAL  (nombres reales del dataset martj42)
  6. fallback                → OTHER         (K=30; ~10 k torneos CONIFA/Viva/regionales)
"""

from app.models.enums import CompetitionKind

# Whitelist de nombres reales en el dataset martj42/international-football-results.
# Comparación exacta (case-sensitive) para evitar falsos positivos.
CONTINENTAL_CHAMPIONSHIPS: frozenset[str] = frozenset(
    {
        "UEFA Euro",
        "Copa América",
        "African Cup of Nations",
        "AFC Asian Cup",
        "Gold Cup",
        "CONCACAF Championship",
        "Oceania Nations Cup",
        "Confederations Cup",
    }
)

_FIFA_WORLD_CUP = "FIFA World Cup"


def classify_competition_kind(name: str) -> CompetitionKind:
    """Mapea el nombre libre de un torneo a un `CompetitionKind`.

    Usa comparación case-insensitive para keywords, comparación exacta para
    la whitelist y para `"FIFA World Cup"` (evita clasificar "CONIFA World
    Football Cup" como WORLD_CUP).

    Args:
        name: Nombre del torneo tal como aparece en la fuente (p.ej. martj42).

    Returns:
        `CompetitionKind` correspondiente.
    """
    t = name.lower()

    # 1. Qualifier — DEBE ir antes de world_cup: "FIFA World Cup qualification"
    if "qualification" in t or "qualifier" in t:
        return CompetitionKind.QUALIFIER

    # 2. Nations League
    if "nations league" in t:
        return CompetitionKind.NATIONS_LEAGUE

    # 3. FIFA World Cup exacto (case-sensitive) — excluye CONIFA/Viva/etc.
    if name == _FIFA_WORLD_CUP:
        return CompetitionKind.WORLD_CUP

    # 4. Friendly
    if "friendly" in t:
        return CompetitionKind.FRIENDLY

    # 5. Whitelist de campeonatos continentales (nombres canónicos del dataset)
    if name in CONTINENTAL_CHAMPIONSHIPS:
        return CompetitionKind.CONTINENTAL

    # 6. Todo lo demás → OTHER (torneos CONIFA, Viva, regionales, etc.)
    return CompetitionKind.OTHER
