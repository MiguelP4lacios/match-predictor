# Match Ingestion Specification

## Purpose

Ingesta idempotente de resultados e fixtures de selecciones nacionales con clasificación correcta de competencias para K-factor de Elo. Cubre `infer_competition_kind` (F1) y upsert sin duplicados (F2).

## Requirements

### Requirement: K-factor Classification

`infer_competition_kind(tournament)` in `app/ingestion/pipeline.py` MUST map every tournament string to one of: `WORLD_CUP`, `CONTINENTAL`, `QUALIFIER`, `NATIONS_LEAGUE`, `FRIENDLY`, or `OTHER`.

The function MUST apply classification in this priority order:
1. Qualification/qualifier keywords → `QUALIFIER`
2. Nations League → `NATIONS_LEAGUE`
3. "world cup" AND tournament is FIFA-official (whitelist) → `WORLD_CUP`
4. "world cup" but NOT FIFA-official (CONIFA, Viva, Beach Soccer WC, etc.) → `OTHER`
5. Continental tournaments (whitelist: Copa América, African Cup, Euro, Gold Cup, AFC Asian Cup, OFC Nations Cup, CONCACAF Nations League) → `CONTINENTAL`
6. Friendly → `FRIENDLY`
7. Fallback → `OTHER`

`CompetitionKind.OTHER` MUST be added to `app/models/enums.py`.

The K-factor lookup `k_factor(kind)` in `app/model/elo.py` MUST map `CompetitionKind.OTHER` → `K_OTHER_TOURNAMENT` (30). The existing default already returns 30 for unknown kinds, but `OTHER` MUST be explicit in `_K_BY_KIND`.

A backfill migration MUST re-classify existing `competition.kind` rows using the updated logic.

#### Scenario: FIFA World Cup gets K=60

- GIVEN tournament name is `"FIFA World Cup"`
- WHEN `infer_competition_kind` is called
- THEN it returns `CompetitionKind.WORLD_CUP`
- AND `k_factor(CompetitionKind.WORLD_CUP)` returns `60`

#### Scenario: CONIFA World Cup excluded from WORLD_CUP

- GIVEN tournament name is `"CONIFA World Football Cup"` or `"Viva World Cup"`
- WHEN `infer_competition_kind` is called
- THEN it returns `CompetitionKind.OTHER`
- AND `k_factor(CompetitionKind.OTHER)` returns `30` (NOT `60`)

#### Scenario: CECAFA Cup classified as OTHER

- GIVEN tournament name is `"CECAFA Cup"`
- WHEN `infer_competition_kind` is called
- THEN it returns `CompetitionKind.OTHER`
- AND `k_factor(CompetitionKind.OTHER)` returns `30`

#### Scenario: Copa América classified as CONTINENTAL

- GIVEN tournament name is `"Copa América"`
- WHEN `infer_competition_kind` is called
- THEN it returns `CompetitionKind.CONTINENTAL`
- AND `k_factor(CompetitionKind.CONTINENTAL)` returns `50`

#### Scenario: Qualification overrides world cup keyword

- GIVEN tournament name is `"FIFA World Cup qualification"`
- WHEN `infer_competition_kind` is called
- THEN it returns `CompetitionKind.QUALIFIER`
- AND `k_factor(CompetitionKind.QUALIFIER)` returns `40`

---

### Requirement: Idempotent Match Ingestion

The `match` table MUST have a unique constraint on `(match_date, home_team_id, away_team_id)` — WITHOUT `competition_id`, per design D1: the goal/shootout linker already treats that tuple as identity, and including `competition_id` would re-admit duplicates on reclassification.

`ResultsIngestionPipeline._load_matches()` MUST use `INSERT … ON CONFLICT (match_date, home_team_id, away_team_id) DO UPDATE SET home_score, away_score, status` instead of plain `session.add()`.

Running `ResultsIngestionPipeline.run(force=True)` on an already-loaded dataset MUST leave the total `match` count unchanged.

#### Scenario: Re-ingestion does not duplicate matches

- GIVEN the database contains 49,443 matches after initial ingestion (49,445 raw minus 2 source duplicates removed by the pre-flight dedup)
- WHEN `run(force=True)` is called a second time with the same source data
- THEN `SELECT COUNT(*) FROM match` still returns `49,443`
- AND the return dict key `"matches"` reflects rows processed (not inserted)

#### Scenario: Updated score is applied on re-ingestion

- GIVEN match `(competition_id=1, match_date=2022-12-18, home_team_id=X, away_team_id=Y)` exists with `home_score=3, away_score=3`
- WHEN source data has `home_score=3, away_score=3` (same) and `run(force=True)` is called
- THEN the row is upserted without error and count remains unchanged

#### Scenario: Incremental re-ingest without force stays skipped

- GIVEN `sync_log` has a row for the resource with `last_fetched_at` set
- WHEN `run(force=False)` is called
- THEN the pipeline returns `{"skipped": True, ...}` without touching the `match` table
