#!/usr/bin/env bash
# Backup de PostgreSQL vía docker compose exec.
# Uso: bash scripts/backup.sh
# El archivo resultante: backups/YYYY-MM-DD_HHMMSS.sql.gz

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="$PROJECT_DIR/backups"

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date -u +"%Y-%m-%d_%H%M%S")
OUTFILE="$BACKUP_DIR/${TIMESTAMP}.sql.gz"

echo "Iniciando backup de match_predictor → $OUTFILE"

docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T db \
    pg_dump -U postgres match_predictor | gzip > "$OUTFILE"

SIZE=$(du -sh "$OUTFILE" | cut -f1)
echo "Backup completado: $OUTFILE ($SIZE)"
