# futures-montecarlo Specification

## Purpose

Motor Monte Carlo para el Mundial 2026: tabla Annex C, corrección de `StandingRow`, y simulador de torneo completo (72 partidos de grupo → knockout R32→Final) que produce probabilidades por equipo para OUTRIGHT_WINNER, GROUP_ADVANCE, REACH_SEMI_FINAL, REACH_FINAL.

---

## Requirements

### Requirement: Annex C Data Module

`app/model/annex_c.py` MUST export `ANNEX_C: dict[frozenset[str], dict[str, str]]` with exactly 495 entries. Each key MUST be a frozenset of 8 distinct uppercase letters in `{A..L}`. Each value MUST be a dict mapping the 8 column headers `{"1A", "1B", "1D", "1E", "1G", "1I", "1K", "1L"}` to a single group letter (the third-placed team's group assigned to that slot).

All 495 frozenset keys MUST be unique. The module MUST expose `validate_annex_c() -> None` that raises `ValueError` if any row violates these invariants.

#### Scenario: Annex C structural validation

- GIVEN `ANNEX_C` is imported
- WHEN `validate_annex_c()` is called
- THEN no exception is raised; `len(ANNEX_C) == 495`; every key is a frozenset of exactly 8 letters; all keys unique

#### Scenario: Opt 1 lookup

- GIVEN qualifying groups `frozenset({"E","F","G","H","I","J","K","L"})`
- WHEN `ANNEX_C[key]` is accessed (Opt 1)
- THEN returns `{"1A":"E","1B":"J","1D":"I","1E":"F","1G":"H","1I":"G","1K":"L","1L":"K"}`

---

### Requirement: StandingRow team_id Field

`app/model/standings.py` MUST add `team_id: int = 0` to `StandingRow` as an **additive** field (default 0 preserves existing callers). `_accumulate()` MUST populate `team_id` from `TeamRef.team_id`.

(Previously: `StandingRow` had no `team_id` field — cross-group ranking was impossible.)

#### Scenario: team_id populated after accumulation

- GIVEN `members = [TeamRef(team_id=5, name="X"), TeamRef(team_id=9, name="Y")]` and results
- WHEN `compute_standings(members, results)` is called
- THEN each returned `StandingRow` has `.team_id` matching the corresponding team's id

---

### Requirement: Monte Carlo Simulator

`app/model/montecarlo.py` MUST export:

```
simulate_tournament(
    groups: dict[str, list[int]],
    elo_ratings: dict[int, float],
    model_params: dict,
    completed_results: dict[str, list[MatchResult]],
    n_iterations: int = 20_000,
    seed: int | None = None,
) -> dict[int, dict[str, float]]
```

Return value: `{team_id: {"p_champion", "p_advance_group", "p_reach_semi", "p_reach_final"}}` for all 48 teams.

Group stage: sample 1X2 from `predict_proba(params, elo_diff, neutral=True)` using seeded NumPy RNG; add Poisson goal draws (λ_home, λ_away conditioned on outcome) to resolve GD tiebreakers. Top 2 per group advance directly; 8 best thirds ranked by (Pts → GD → GF → Elo) using Annex C for slot assignment. Elo is STATIC (no in-simulation updates). Knockout formula: `P(home_adv) = P(H) + 0.5 × P(D)`, `P(away_adv) = P(A) + 0.5 × P(D)`.

#### Scenario: Probability sums and ordering (toy tournament)

- GIVEN 2 groups of 2 teams; Group X: team_1 (Elo=1800), team_2 (Elo=1500); Group Y: team_3 (Elo=1700), team_4 (Elo=1450); seed=42; n_iterations=5_000
- WHEN `simulate_tournament(...)` is called (2-group format: top 1 per group + final)
- THEN `sum(r["p_champion"] for r in result.values())` ∈ [0.99, 1.01]
- AND `result[team_1]["p_champion"] > result[team_2]["p_champion"]` (stronger team dominates)

#### Scenario: Reproducibility — same seed → identical output

- GIVEN identical inputs and `seed=42`
- WHEN `simulate_tournament(...)` is called twice
- THEN both calls return byte-identical dicts for all team_ids and all probability keys

#### Scenario: Knockout advancement probability formula

- GIVEN a knockout match where `predict_proba` returns `P(H)=0.45, P(D)=0.28, P(A)=0.27`
- WHEN knockout advancement is computed
- THEN `P(home_advances) = 0.45 + 0.5×0.28 = 0.59` and `P(away_advances) = 0.27 + 0.5×0.28 = 0.41`

---
