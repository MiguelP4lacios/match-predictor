# Delta for Prod Deploy

## MODIFIED Requirements

### Requirement: Tournament Update Script

A script `scripts/tournament_update.sh` MUST chain the following steps using `set -e`
(abort on first non-zero exit). The compose invocation MUST use
`-f docker-compose.prod.yml`. Step 1 MUST be skipped if `--skip-odds` flag is passed.

(Previously: 5 steps — [odds] → ingest → elo → predict → signals. Settlement step
not present.)

| Step | Command |
|------|---------|
| 1 (optional) | `docker compose ... run --rm scheduler python -m app.scheduler.run --once` |
| 2 | `docker compose ... run --rm ingest python -m app.ingestion.run --force` |
| 3 | `docker compose ... run --rm api python -m app.betting.settle` |
| 4 | `docker compose ... run --rm api python -m app.model.run_elo` |
| 5 | `docker compose ... run --rm api python -m app.model.run_1x2 predict` |
| 6 | `docker compose ... run --rm api python -m app.model.run_1x2 signals` |

Settlement (step 3) MUST run immediately after ingest (step 2) and before elo (step 4),
because it only needs `match.home_score`/`away_score` populated by ingest.

The script MUST print a `[OK] tournament_update complete` summary on success.
Step numbering in log messages MUST reflect the updated 6-step chain.

#### Scenario: Settle corre tras ingest exitoso

- GIVEN ingest (step 2) completa con exit 0
- WHEN `tournament_update.sh` avanza
- THEN step 3 (`python -m app.betting.settle`) corre, imprime `"Settled: N bets"`,
  y el script continúa a step 4 (elo)

#### Scenario: Settle liquida apuestas del día

- GIVEN 2 partidos FINISHED tras el ingest con apuestas PENDING
- WHEN step 3 corre
- THEN imprime `"Settled: 2 bets"`; elo y predicciones corren con datos frescos

#### Scenario: Abort on step failure

- GIVEN `python -m app.model.run_elo` (step 4) exits non-zero
- WHEN `tournament_update.sh` is running
- THEN steps 5 and 6 are NOT executed and the script exits non-zero

#### Scenario: Skip odds step

- GIVEN odds API credits are exhausted
- WHEN `bash scripts/tournament_update.sh --skip-odds` is run
- THEN step 1 is omitted; steps 2–6 run normally; script exits 0

#### Scenario: Settle idempotente en re-run

- GIVEN el script corre dos veces el mismo día
- WHEN step 3 corre en la segunda ejecución
- THEN imprime `"Settled: 0 bets"` (apuestas ya liquidadas); script continúa normal
