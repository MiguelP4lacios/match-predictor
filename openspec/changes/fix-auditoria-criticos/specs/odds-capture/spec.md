# Odds Capture Specification

## Purpose

Captura confiable de snapshots de cuotas desde The Odds API: persistencia siempre (match_id nullable), trazabilidad por `source_event_id`/`commence_time`, re-linkeo posterior al cargar fixtures, y desambiguación robusta de outcome para evitar odds corruptas.

## Requirements

### Requirement: Always-Persist Odds

`OddsCapturePipeline.capture()` in `app/ingestion/odds_pipeline.py` MUST persist every `Odds` row received from the source, regardless of whether a matching `Match` can be found in the database.

The `odds` table MUST have two new columns:
- `source_event_id VARCHAR(80)` — ID opaco de The Odds API para re-linkeo posterior.
- `commence_time TIMESTAMP` — hora UTC de inicio del evento según la fuente.

The `match` table MUST have a new column:
- `kickoff_at TIMESTAMP` — hora UTC del partido (from `commence_time` when fixture is loaded).

When no match is found, the `Odds` row MUST be inserted with `match_id = NULL`.

A separate job/script `relink_odds` MUST exist that attempts to match unlinked odds (`match_id IS NULL`) to their `Match` using `source_event_id` or the `commence_time ± 1 day` + team-pair strategy, and updates `match_id` in place.

#### Scenario: Odds without fixture are persisted

- GIVEN The Odds API returns a h2h event for teams not yet in the `match` table
- WHEN `capture()` is called
- THEN an `Odds` row is inserted with `match_id = NULL`, `source_event_id` set, `commence_time` set
- AND the return dict `"unlinked_events"` count is > 0

#### Scenario: Odds with fixture get match_id on capture

- GIVEN the `match` table has a scheduled match for `(TeamA, TeamB)` with `kickoff_at` within 1 day of `commence_time`
- WHEN `capture()` is called for that event
- THEN the `Odds` row is inserted with `match_id` set (NOT NULL)

#### Scenario: relink_odds links previously unlinked odds

- GIVEN `odds` table has rows with `match_id = NULL` and valid `source_event_id`
- AND the corresponding `match` row now exists
- WHEN `relink_odds` job runs
- THEN those rows have `match_id` updated to the correct match id
- AND rows that still have no match remain `match_id = NULL`

---

### Requirement: Reliable Outcome Code Resolution

`OddsCapturePipeline._outcome_code()` MUST assign `"DRAW"` ONLY when `ro.outcome_name == "Draw"` (exact string, case-insensitive comparison).

When `self._resolve(ro.outcome_name)` returns `None` for a non-"Draw" outcome name (unresolved team), the pipeline MUST discard the `Odds` row and log a warning containing the unresolved name. It MUST NOT assign `"DRAW"` to an unresolved team name.

Match linking for h2h/totals MUST compare `ro.commence_time` against `Match.kickoff_at` within ±1 day in addition to the team-pair frozenset. If both a team-pair match AND a time constraint are required, time takes precedence for disambiguation when multiple matches exist for the same pair.

#### Scenario: "Draw" outcome code assigned correctly

- GIVEN a h2h market row with `outcome_name = "Draw"`
- WHEN `_outcome_code()` is called
- THEN it returns `"DRAW"`

#### Scenario: Unresolved team name is not treated as DRAW

- GIVEN a h2h market row with `outcome_name = "Côte d'Ivoire"` and the resolver returns `None`
- WHEN `_outcome_code()` is called
- THEN the `Odds` row is discarded (not inserted)
- AND a warning is logged containing `"Côte d'Ivoire"`

#### Scenario: Disambiguation by commence_time when two fixtures share same pair

- GIVEN `match` table has two rows for `(TeamA, TeamB)`: one on 2026-06-14 and one on 2026-06-15
- AND `ro.commence_time` falls within ±1 day of 2026-06-15
- WHEN `_build_match_index()` resolves the match
- THEN the `Odds` row links to the 2026-06-15 match (not the 2026-06-14 one)
