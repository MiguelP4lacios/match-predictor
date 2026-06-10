# Group Standings Specification

## Purpose

Define the behavior for seeding WC2026 groups from existing fixtures,
computing standings with FIFA tiebreakers, and serving group data via two endpoints.

---

## Requirements

### Requirement: R1 — Group Derivation from Fixture Graph

The seed script MUST derive exactly 12 groups by computing connected components
over the 72 SCHEDULED WC2026 group fixtures in the `match` table.
Each component MUST contain exactly 4 teams (any other count → fail loudly with a clear error message before writing any rows).
Group letters A–L MUST be assigned via an explicit, editable mapping inside the script
(letters are NOT derivable from the graph — user MUST verify the printed composition).
Seed MUST be idempotent: re-running produces no duplicate rows (upsert/ignore on
`uq_group_comp_season_name` and `uq_group_team`).
During seed, all 72 group-fixture rows MUST receive `match.stage = MatchStage.GROUP`
and `match.group_id` linked to their `TournamentGroup.id`.

#### Scenario: Valid graph — 12 × 4

- GIVEN 72 SCHEDULED WC2026 group fixtures in `match` with exactly 48 distinct teams
- WHEN `scripts/seed_groups.py` runs
- THEN 12 `TournamentGroup` rows inserted (A–L), 48 `GroupTeam` rows,
  72 `match` rows updated with `stage=GROUP` and `group_id` set;
  script prints the letter→team composition for user verification

#### Scenario: Graph integrity failure

- GIVEN a group fixture is missing and one component contains only 3 teams
- WHEN `scripts/seed_groups.py` runs
- THEN script MUST raise an error (e.g. `AssertionError: expected 12 components of 4 teams,
  got component of 3`) and write ZERO rows (no partial seed)

#### Scenario: Idempotent re-run

- GIVEN seed was already run successfully
- WHEN `scripts/seed_groups.py` runs again
- THEN row counts remain identical; no IntegrityError raised

---

### Requirement: R2 — Standings Pure Function (FIFA Tiebreakers)

`app/model/standings.py` MUST expose a pure function
`compute_standings(matches: list[Match]) -> list[StandingRow]`
that accepts the FINISHED matches of a single group and returns a ranked table.

Columns per row: `team_name`, `PJ` (played), `G` (won), `E` (drawn), `P` (lost),
`GF` (goals for), `GC` (goals against), `DG` (goal diff = GF − GC), `Pts`.

Tiebreaker order (applied iteratively to tied sub-groups):
1. Points (Pts)
2. Goal difference (DG)
3. Goals for (GF)
4. Head-to-head points among tied teams
5. Head-to-head GD among tied teams
6. Head-to-head GF among tied teams
7. Team name alphabetical (deterministic fallback — always produces a stable order)

Fair-play (yellow/red cards) is explicitly OUT OF SCOPE (cards not ingested).
The tiebreaker order MUST be documented in the function's docstring.

#### Scenario S1: Full standings — no tie (numeric verification)

Matches (all FINISHED, Group X):
- A 3–0 B, C 1–1 D, A 1–0 C, B 2–1 D, A 0–0 D, B 1–2 C

Expected table (verified):

| # | Team | PJ | G | E | P | GF | GC | DG | Pts |
|---|------|----|---|---|---|----|----|----|-----|
| 1 | A    | 3  | 2 | 1 | 0 | 4  | 0  | +4 | 7   |
| 2 | C    | 3  | 1 | 1 | 1 | 3  | 3  | 0  | 4   |
| 3 | B    | 3  | 1 | 0 | 2 | 3  | 6  | −3 | 3   |
| 4 | D    | 3  | 0 | 2 | 1 | 2  | 3  | −1 | 2   |

- GIVEN the 6 matches above inserted as FINISHED
- WHEN `compute_standings(group_matches)`
- THEN the function returns rows in the exact order and values shown above

#### Scenario S2: Tie on points broken by goal difference (numeric verification)

Matches (all FINISHED, Group Y):
- A 2–0 B, A 0–0 C, A 0–0 D, B 0–1 C, B 0–0 D, C 0–0 D

Expected (verified):

| # | Team | Pts | DG | GF | Note |
|---|------|-----|----|----|------|
| 1 | A    | 5   | +2 | 2  | DG wins |
| 2 | C    | 5   | +1 | 1  | |
| 3 | D    | 3   | 0  | 0  | |
| 4 | B    | 1   | −3 | 0  | |

- GIVEN the 6 matches above
- WHEN `compute_standings(group_matches)`
- THEN A ranks 1st over C because DG +2 > +1 (same 5 Pts); exact row order as above

#### Scenario S3: Tie broken by head-to-head after Pts + DG + GF equal (numeric verification)

Matches (all FINISHED, Group Z):
- A 1–0 B, A 1–1 C, A 0–0 D, B 1–0 C, B 1–1 D, C 1–0 D

Expected (verified):

| # | Team | Pts | DG | GF | H2H pts (vs tied) | Note |
|---|------|-----|----|----|-------------------|------|
| 1 | A    | 5   | +1 | 2  | — (not tied)      | |
| 2 | B    | 4   | 0  | 2  | H2H B>C: 3 vs 0   | B 1–0 C |
| 3 | C    | 4   | 0  | 2  | |                  | |
| 4 | D    | 2   | −1 | 1  | — (not tied)      | |

- GIVEN B and C both have Pts=4, DG=0, GF=2 (overall equal)
- WHEN head-to-head applied: B 1–0 C → B earns 3 H2H pts, C earns 0
- THEN B ranks 2nd, C ranks 3rd

#### Scenario S4: Zero FINISHED matches

- GIVEN a group with 0 FINISHED matches (all SCHEDULED)
- WHEN `compute_standings([])`
- THEN all 4 teams returned with PJ=G=E=P=GF=GC=DG=Pts=0,
  ordered alphabetically by team name

---

### Requirement: R3 — GET /api/v1/groups

Returns all 12 groups with members and current standings (computed at request time
from FINISHED matches — no persisted standings table).

Response per group item:
- `name` (letter A–L)
- `teams` (list of team names)
- `standings` (list of StandingRow as per R2)

#### Scenario: All groups present after seed

- GIVEN seed was run and ≥ 0 matches are FINISHED
- WHEN `GET /api/v1/groups`
- THEN HTTP 200, exactly 12 group objects, each with 4 teams and a standings list

#### Scenario: No groups seeded

- GIVEN `tournament_group` table is empty
- WHEN `GET /api/v1/groups`
- THEN HTTP 200, `[]` (empty collection, not 404)

---

### Requirement: R4 — GET /api/v1/groups/{name}

Returns a single group by its letter (case-insensitive, normalized to uppercase).
Response: `name`, `teams`, `standings` (as R2), `fixtures` (all group matches for
this group with predictions if present).
Returns HTTP 404 if the letter is unknown (not in A–L or group not seeded).

#### Scenario: Valid group

- GIVEN group "B" is seeded with 4 teams and 6 group fixtures
- WHEN `GET /api/v1/groups/B` or `GET /api/v1/groups/b`
- THEN HTTP 200 with standings + fixtures + predictions (null if not yet generated)

#### Scenario: Unknown group letter

- GIVEN no group "M" exists
- WHEN `GET /api/v1/groups/M`
- THEN HTTP 404, `{"detail": "Group not found"}`

#### Scenario: Lowercase letter normalised

- GIVEN group "A" is seeded
- WHEN `GET /api/v1/groups/a`
- THEN HTTP 200 (same as `/groups/A`)
