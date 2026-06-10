#!/usr/bin/env bash
# Loop diario de actualización del torneo (corre en el VPS).
# Encadena: [odds] → ingest → elo → predict → signals.
# Usar set -e para abortar al primer error: si elo falla, predict y signals NO corren.
#
# Uso (desde ~/match-predictor en el VPS):
#   bash scripts/tournament_update.sh              # incluye captura de odds
#   bash scripts/tournament_update.sh --skip-odds  # salta paso 1 (cuota agotada)
#
# Cron sugerido (3am UTC, todos los días):
#   0 3 * * * cd /root/match-predictor && bash scripts/tournament_update.sh >> /var/log/tournament_update.log 2>&1

set -euo pipefail

# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------
SKIP_ODDS=false

for arg in "$@"; do
  case "$arg" in
    --skip-odds) SKIP_ODDS=true ;;
    *) echo "ERROR: Argumento desconocido: $arg" >&2; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Compose command (standalone prod)
# ---------------------------------------------------------------------------
COMPOSE="docker compose -f docker-compose.prod.yml"

echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') — Iniciando tournament_update..."

# ---------------------------------------------------------------------------
# Paso 1: Captura de odds (skippable)
# ---------------------------------------------------------------------------
if [[ "$SKIP_ODDS" == "true" ]]; then
  echo "[1/5] Captura de odds — SALTADA (--skip-odds activo)."
else
  echo "[1/5] Capturando odds actuales..."
  # scheduler está en profiles:[manual]; usamos COMPOSE_PROFILES para que compose lo encuentre.
  COMPOSE_PROFILES=manual $COMPOSE run --rm scheduler python -m app.scheduler.run --once
fi

# ---------------------------------------------------------------------------
# Paso 2: Ingesta histórica (--force: upsert ON CONFLICT, seguro idempotente)
# ---------------------------------------------------------------------------
echo "[2/5] Ingesta histórica (--force)..."
$COMPOSE run --rm ingest python -m app.ingestion.run --force

# ---------------------------------------------------------------------------
# Paso 3: Recalcular Elo
# ---------------------------------------------------------------------------
echo "[3/5] Recalculando ratings Elo..."
$COMPOSE run --rm api python -m app.model.run_elo

# ---------------------------------------------------------------------------
# Paso 4: Generar predicciones 1X2
# ---------------------------------------------------------------------------
echo "[4/5] Generando predicciones 1X2..."
$COMPOSE run --rm api python -m app.model.run_1x2 predict

# ---------------------------------------------------------------------------
# Paso 5: Generar señales +EV
# ---------------------------------------------------------------------------
echo "[5/5] Generando señales +EV PAPER..."
$COMPOSE run --rm api python -m app.model.run_1x2 signals

# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------
echo ""
echo "[OK] tournament_update complete — $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
