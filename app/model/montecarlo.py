"""Motor Monte Carlo — WC2026 champion & advance probabilities.

Función pura: sin BD, sin LLM. Semilla determinista con numpy PCG64.

Arquitectura de la simulación:
  1. Fase de grupos vectorizada: muestreo de 1X2 para todos los partidos
     no jugados × todas las iteraciones de una vez (numpy, fast).
  2. Clasificados: top-2 por grupo. Con 12 grupos: + 8 mejores 3eros via
     Annex C. Con < 12 grupos: solo top-2.
  3. Eliminatorias por ronda: muestreo vectorizado de ganadores por bloque.
  4. Contadores acumulados → proporciones al final.

Caveat documentado: en eliminatoria, los empates se resuelven con P(adv) =
P(H) + 0.5·P(D) (absorción 50/50), lo que sobre-estima levemente al favorito
porque los empates ocurren más en partidos parejos.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.random import PCG64, Generator

from app.model.annex_c import ANNEX_C
from app.model.probabilities import predict_proba
from app.model.standings import MatchResult, TeamRef, compute_standings

# ---------------------------------------------------------------------------
# Funciones puras auxiliares
# ---------------------------------------------------------------------------

# Lambdas de Poisson para goles por resultado (home_gf_lambda, away_gf_lambda)
_GOAL_LAMBDAS: dict[int, tuple[float, float]] = {
    2: (1.5, 0.8),  # victoria local
    1: (1.1, 1.1),  # empate
    0: (0.8, 1.5),  # victoria visitante
}


def knockout_prob(p_home: float, p_draw: float, p_away: float) -> float:  # noqa: ARG001 (p_away documentado)
    """Probabilidad de avance del equipo local en una eliminatoria (neutral).

    P(home_advances) = P(H) + 0.5 × P(D)

    Caveat: las prórrogas y penales se modelan como 50/50 tras empate.

    Args:
        p_home: probabilidad de victoria local.
        p_draw: probabilidad de empate.
        p_away: probabilidad de victoria visitante (no usada directamente).

    Returns:
        Probabilidad de avance del equipo local (float en [0, 1]).
    """
    return p_home + 0.5 * p_draw


def _group_match_pairs(team_ids: list[int]) -> list[tuple[int, int]]:
    """Genera los 6 pares (home_id, away_id) de un round-robin de 4 equipos."""
    pairs: list[tuple[int, int]] = []
    for i in range(len(team_ids)):
        for j in range(i + 1, len(team_ids)):
            pairs.append((team_ids[i], team_ids[j]))
    return pairs


def _precompute_ko_prob_matrix(
    team_idx: dict[int, int],
    elo: dict[int, float],
    params: dict,
) -> np.ndarray:
    """Matriz n×n de P(equipo_i avanza) vs equipo_j en eliminatoria (neutral).

    ko_matrix[i, j] = knockout_prob(predict_proba(elo[i] - elo[j], neutral=True))
    """
    n = len(team_idx)
    mat = np.zeros((n, n), dtype=np.float64)
    team_ids = sorted(team_idx.keys(), key=lambda t: team_idx[t])
    for i, tid_i in enumerate(team_ids):
        for j, tid_j in enumerate(team_ids):
            if i == j:
                continue
            elo_diff = elo.get(tid_i, 1500.0) - elo.get(tid_j, 1500.0)
            probs = predict_proba(params, elo_diff, neutral=True)
            mat[i, j] = knockout_prob(probs["home"], probs["draw"], probs["away"])
    return mat


# ---------------------------------------------------------------------------
# Simulación principal
# ---------------------------------------------------------------------------


def simulate_tournament(
    groups: dict[str, list[int]],
    elo_ratings: dict[int, float],
    model_params: dict,
    completed_results: dict[str, list[MatchResult]],
    n_iterations: int = 20_000,
    seed: int | None = 42,
) -> dict[int, dict[str, float]]:
    """Simula el torneo n_iterations veces con RNG semillado.

    Args:
        groups: {"A": [team_id, ...], ...}
        elo_ratings: {team_id: 1820.0}
        model_params: parámetros OLM de ModelVersion.params_json
        completed_results: partidos FINISHED de grupo por letra de grupo
        n_iterations: número de iteraciones MC (default 20_000)
        seed: semilla para PCG64 (None = no determinista)

    Returns:
        {team_id: {"p_champion": float, "p_reach_final": float,
                   "p_reach_sf": float, "p_advance_group": float}}
    """
    rng: Generator = Generator(PCG64(seed))
    group_letters = sorted(groups.keys())
    n_groups = len(group_letters)

    # Índice de todos los equipos
    all_team_ids: list[int] = [tid for gl in group_letters for tid in groups[gl]]
    team_idx: dict[int, int] = {tid: i for i, tid in enumerate(all_team_ids)}
    n_teams = len(all_team_ids)

    # -----------------------------------------------------------------------
    # Precomputar partidos no jugados + probabilidades de fase de grupos
    # -----------------------------------------------------------------------
    completed_pairs: dict[str, set[tuple[int, int]]] = {
        gl: {(r.home_id, r.away_id) for r in completed_results.get(gl, [])}
        for gl in group_letters
    }

    # Información aplanada de todos los partidos de grupo no jugados
    unplayed_letter: list[str] = []
    unplayed_home: list[int] = []
    unplayed_away: list[int] = []
    unplayed_probs: list[tuple[float, float, float]] = []

    for gl in group_letters:
        for home_id, away_id in _group_match_pairs(groups[gl]):
            if (home_id, away_id) in completed_pairs[gl]:
                continue
            elo_diff = elo_ratings.get(home_id, 1500.0) - elo_ratings.get(away_id, 1500.0)
            p = predict_proba(model_params, elo_diff, neutral=True)
            unplayed_letter.append(gl)
            unplayed_home.append(home_id)
            unplayed_away.append(away_id)
            unplayed_probs.append((p["home"], p["draw"], p["away"]))

    n_unplayed = len(unplayed_probs)

    # -----------------------------------------------------------------------
    # Vectorizar muestreo de resultados de grupo (todas las iteraciones a la vez)
    # -----------------------------------------------------------------------
    if n_unplayed > 0:
        prob_arr = np.array(unplayed_probs, dtype=np.float64)  # (n_unplayed, 3)
        cum_p = np.cumsum(prob_arr, axis=1)  # (n_unplayed, 3)

        u_group = rng.random((n_iterations, n_unplayed))  # (n_iters, n_unplayed)
        # outcomes: 2=home win, 1=draw, 0=away win
        outcomes = (
            (u_group > cum_p[None, :, 0]).astype(np.int8)
            + (u_group > cum_p[None, :, 1]).astype(np.int8)
        )  # (n_iters, n_unplayed)

        # Goles (para cálculo de GD en desempate de grupo)
        # outcomes: 0=home win, 1=draw, 2=away win (cumsum desde P(home) primero)
        lam_h = np.where(outcomes == 0, 1.5, np.where(outcomes == 1, 1.1, 0.8))
        lam_a = np.where(outcomes == 0, 0.8, np.where(outcomes == 1, 1.1, 1.5))
        hg = rng.poisson(lam_h).astype(np.int16)  # (n_iters, n_unplayed)
        ag = rng.poisson(lam_a).astype(np.int16)

        # Consistencia entre resultado y marcador
        # Home win (outcome=0): asegurar hg > ag
        hw_mask = (outcomes == 0) & (hg <= ag)
        hg = np.where(hw_mask, ag + 1, hg)
        # Empate (outcome=1): asegurar hg == ag
        d_mask = outcomes == 1
        ag = np.where(d_mask, hg, ag)
        # Away win (outcome=2): asegurar ag > hg
        aw_mask = (outcomes == 2) & (ag <= hg)
        ag = np.where(aw_mask, hg + 1, ag)
    else:
        outcomes = np.empty((n_iterations, 0), dtype=np.int8)
        hg = np.empty((n_iterations, 0), dtype=np.int16)
        ag = np.empty((n_iterations, 0), dtype=np.int16)

    # Índice rápido: (group_letter, home_id, away_id) → columna en outcomes
    unplayed_idx: dict[tuple[str, int, int], int] = {}
    for col, (gl, hid, aid) in enumerate(
        zip(unplayed_letter, unplayed_home, unplayed_away, strict=True)
    ):
        unplayed_idx[(gl, hid, aid)] = col

    # -----------------------------------------------------------------------
    # Precomputar matriz KO
    # -----------------------------------------------------------------------
    ko_matrix = _precompute_ko_prob_matrix(team_idx, elo_ratings, model_params)

    # -----------------------------------------------------------------------
    # Contadores de clasificación
    # -----------------------------------------------------------------------
    cnt_advance = np.zeros(n_teams, dtype=np.int32)
    cnt_sf = np.zeros(n_teams, dtype=np.int32)
    cnt_final = np.zeros(n_teams, dtype=np.int32)
    cnt_champion = np.zeros(n_teams, dtype=np.int32)

    # -----------------------------------------------------------------------
    # Bucle por iteración (fase de grupos→clasificados→eliminatorias)
    # -----------------------------------------------------------------------
    for it in range(n_iterations):
        it_hg = hg[it]
        it_ag = ag[it]

        # Calcular clasificados por grupo
        group_winners: list[int] = []
        group_runners: list[int] = []
        group_thirds: list[tuple[str, int, int, int, int]] = []  # (letter, tid, pts, gd, gf)

        for gl in group_letters:
            team_ids = groups[gl]
            # Resultados completados ya cerrados
            results: list[MatchResult] = list(completed_results.get(gl, []))

            # Añadir partidos simulados de este grupo
            for home_id, away_id in _group_match_pairs(team_ids):
                if (home_id, away_id) in completed_pairs[gl]:
                    continue
                col = unplayed_idx[(gl, home_id, away_id)]
                h_goals = int(it_hg[col])
                a_goals = int(it_ag[col])
                results.append(
                    MatchResult(
                        home_id=home_id,
                        away_id=away_id,
                        home_score=h_goals,
                        away_score=a_goals,
                    )
                )

            # Calcular tabla
            members = [TeamRef(team_id=tid, name=str(tid)) for tid in team_ids]
            table = compute_standings(members, results)

            # Top-2 avanzan
            w_tid = table[0].team_id
            r_tid = table[1].team_id
            group_winners.append(w_tid)
            group_runners.append(r_tid)
            cnt_advance[team_idx[w_tid]] += 1
            cnt_advance[team_idx[r_tid]] += 1

            # Tercer lugar para ranking cross-grupos
            if n_groups >= 8 and len(table) >= 3:
                t3 = table[2]
                group_thirds.append((gl, t3.team_id, t3.pts, t3.dg, t3.gf))

        # Bracket de eliminatorias
        qualifiers = _build_bracket(
            group_letters,
            group_winners,
            group_runners,
            group_thirds,
            n_groups,
        )  # list[int] de team_ids en orden de bracket

        # Simulación eliminatorias por ronda
        n_qual = len(qualifiers)
        teams = qualifiers  # índices locales en ko_matrix via team_idx

        # Determinar profundidad de competición por equipo
        # según cuántas rondas hay: log2(n_qual) rondas totales
        n_rounds = math.floor(math.log2(n_qual)) if n_qual >= 2 else 0

        # Llenar hasta potencia de 2 si no es exacta (BYE al equipo 0)
        # En WC2026: siempre 32 → 5 rondas
        round_teams = teams

        for _rnd in range(n_rounds):
            next_round: list[int] = []
            u_ko = rng.random(len(round_teams) // 2)
            for m, (t1, t2) in enumerate(zip(round_teams[::2], round_teams[1::2], strict=True)):
                i1 = team_idx[t1]
                i2 = team_idx[t2]
                p_t1_wins = ko_matrix[i1, i2]
                winner = t1 if u_ko[m] < p_t1_wins else t2
                next_round.append(winner)

            # Contadores por TAMAÑO de la ronda resultante (robusto sin importar
            # cuántas rondas haya). next_round = ganadores que avanzan:
            #   4 ganadores  -> jugarán las SEMIS  (llegaron a semifinal)
            #   2 ganadores  -> jugarán la FINAL   (llegaron a la final)
            #   1 ganador    -> CAMPEÓN (se cuenta abajo)
            if len(next_round) == 4:
                for tid in next_round:
                    cnt_sf[team_idx[tid]] += 1
            elif len(next_round) == 2:
                for tid in next_round:
                    cnt_final[team_idx[tid]] += 1

            round_teams = next_round

        # Campeón (único equipo que queda)
        if round_teams:
            cnt_champion[team_idx[round_teams[0]]] += 1

    # -----------------------------------------------------------------------
    # Promediar sobre las iteraciones
    # -----------------------------------------------------------------------
    result: dict[int, dict[str, float]] = {}
    for i, tid in enumerate(all_team_ids):
        result[tid] = {
            "p_champion": cnt_champion[i] / n_iterations,
            "p_reach_final": cnt_final[i] / n_iterations,
            "p_reach_sf": cnt_sf[i] / n_iterations,
            "p_advance_group": cnt_advance[i] / n_iterations,
        }

    return result


# ---------------------------------------------------------------------------
# Construcción del bracket de eliminatorias
# ---------------------------------------------------------------------------


def _build_bracket(
    group_letters: list[str],
    group_winners: list[int],  # [winner_of_A, winner_of_B, ...]
    group_runners: list[int],  # [runner_of_A, runner_of_B, ...]
    group_thirds: list[tuple[str, int, int, int, int]],  # (letter, tid, pts, gd, gf)
    n_groups: int,
) -> list[int]:
    """Construye el bracket de eliminatorias.

    Para WC2026 (n_groups==12):
      - top-2 de cada grupo (24 equipos) + 8 mejores 3eros via Annex C (8 equipos)
      - = exactamente 32 equipos en bracket oficial de 16 partidos de R32.
      - Orden del bracket reproduce el árbol oficial FIFA (R16→QF→SF→Final).

    Para torneos menores: solo top-2 de cada grupo con emparejamiento cruzado simple.

    Returns:
        lista de team_ids en orden de bracket (pares consecutivos se enfrentan).
        WC2026 (n_groups==12): exactamente 32 equipos.
        Otros: n_groups × 2 equipos.
    """
    winner_by_letter = dict(zip(group_letters, group_winners, strict=True))
    runner_by_letter = dict(zip(group_letters, group_runners, strict=True))

    if n_groups == 12 and len(group_thirds) >= 8:
        # -----------------------------------------------------------------------
        # WC2026: 32-team bracket
        #   12 winners + 12 runners + 8 best-thirds = 32 qualifiers
        # -----------------------------------------------------------------------

        # Seleccionar los 8 mejores 3eros: Pts desc, GD desc, GF desc
        thirds_sorted = sorted(
            group_thirds,
            key=lambda x: (-x[2], -x[3], -x[4]),
        )[:8]
        third_letters = frozenset(t[0] for t in thirds_sorted)
        third_by_letter = {t[0]: t[1] for t in thirds_sorted}

        # Annex C: frozenset({8 group letters}) → {"1A": "X", ...}
        slot_map = ANNEX_C.get(third_letters, {})

        if slot_map:
            # slot_map[slot] = letra del grupo cuyo 3er clasificado ocupa ese slot.
            # _SLOTS = ("1A","1B","1D","1E","1G","1I","1K","1L")
            # 8 de los 12 ganadores de grupo juegan vs un 3er clasificado en R32.
            # Los otros 4 ganadores (C, F, H, J) juegan vs subcampeones cruzados.
            #
            # Bracket en orden de árbol single-elimination (pares consecutivos
            # se enfrentan en R32; la estructura garantiza R16/QF/SF/F correctos).
            #
            # Árbol de R16 (fuente: FIFA reglamentos Art. 12.7 Annex):
            #   M89: W74 vs W77 → QF1   M90: W73 vs W75 → QF1
            #   M93: W83 vs W84 → QF2   M94: W81 vs W82 → QF2
            #   M91: W76 vs W78 → QF3   M92: W79 vs W80 → QF3
            #   M95: W86 vs W88 → QF4   M96: W85 vs W87 → QF4

            def _third(slot: str) -> int:
                """team_id del 3er clasificado asignado al slot dado."""
                return third_by_letter[slot_map[slot]]

            return [
                # --- SF1 → QF1 (M97: W89 vs W90) ---
                # R16 M89 (W74 vs W77)
                winner_by_letter["E"], _third("1E"),           # R32 M74: 1E vs 3rd(1E)
                winner_by_letter["I"], _third("1I"),           # R32 M77: 1I vs 3rd(1I)
                # R16 M90 (W73 vs W75)
                runner_by_letter["A"], runner_by_letter["B"],  # R32 M73: 2A vs 2B
                winner_by_letter["F"], runner_by_letter["C"],  # R32 M75: 1F vs 2C
                # --- SF1 → QF2 (M98: W93 vs W94) ---
                # R16 M93 (W83 vs W84)
                runner_by_letter["K"], runner_by_letter["L"],  # R32 M83: 2K vs 2L
                winner_by_letter["H"], runner_by_letter["J"],  # R32 M84: 1H vs 2J
                # R16 M94 (W81 vs W82)
                winner_by_letter["D"], _third("1D"),           # R32 M81: 1D vs 3rd(1D)
                winner_by_letter["G"], _third("1G"),           # R32 M82: 1G vs 3rd(1G)
                # --- SF2 → QF3 (M99: W91 vs W92) ---
                # R16 M91 (W76 vs W78)
                winner_by_letter["C"], runner_by_letter["F"],  # R32 M76: 1C vs 2F
                runner_by_letter["E"], runner_by_letter["I"],  # R32 M78: 2E vs 2I
                # R16 M92 (W79 vs W80)
                winner_by_letter["A"], _third("1A"),           # R32 M79: 1A vs 3rd(1A)
                winner_by_letter["L"], _third("1L"),           # R32 M80: 1L vs 3rd(1L)
                # --- SF2 → QF4 (M100: W95 vs W96) ---
                # R16 M95 (W86 vs W88)
                winner_by_letter["J"], runner_by_letter["H"],  # R32 M86: 1J vs 2H
                runner_by_letter["D"], runner_by_letter["G"],  # R32 M88: 2D vs 2G
                # R16 M96 (W85 vs W87)
                winner_by_letter["B"], _third("1B"),           # R32 M85: 1B vs 3rd(1B)
                winner_by_letter["K"], _third("1K"),           # R32 M87: 1K vs 3rd(1K)
            ]

        # Fallback: miss de Annex C (no debe ocurrir si ANNEX_C tiene las 495 entradas).
        # Bracket simplificado pero válido de 32 equipos:
        #   - 8 partidos ganador+3ero (grupos con tercero clasificado)
        #   - 4 partidos ganador+subcampeón (grupos sin tercero)
        #   - 4 partidos subcampeón+subcampeón (subcampeones de grupos con 3ero)
        # NOTE: orden no refleja el árbol oficial FIFA.
        third_groups = sorted(third_letters)
        non_third_groups = sorted(set(group_letters) - third_letters)
        bracket: list[int] = []
        for gl in third_groups:
            bracket.append(winner_by_letter[gl])
            bracket.append(third_by_letter[gl])
        for gl in non_third_groups:
            bracket.append(winner_by_letter[gl])
            bracket.append(runner_by_letter[gl])
        third_runners = [runner_by_letter[gl] for gl in third_groups]
        for i in range(0, len(third_runners), 2):
            bracket.append(third_runners[i])
            bracket.append(third_runners[i + 1])
        return bracket  # 8×2 + 4×2 + 4×2 = 32 equipos

    # -----------------------------------------------------------------------
    # Bracket genérico: solo top-2, emparejamiento cruzado simple
    # Válido para 2, 4, 8 grupos (todos potencias de 2 → n×2 equipos).
    # -----------------------------------------------------------------------
    bracket = []
    n = n_groups
    for i in range(0, n, 2):
        if i + 1 < n:
            bracket.append(group_winners[i])
            bracket.append(group_runners[i + 1])
        else:
            # Número impar de grupos (raro): solo el ganador avanza
            bracket.append(group_winners[i])
    for i in range(1, n, 2):
        bracket.append(group_winners[i])
        bracket.append(group_runners[i - 1] if i > 0 else group_runners[0])

    return bracket
