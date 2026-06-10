#!/usr/bin/env bash
# Migración Mac→VPS: backup local → scp → restore en Postgres → assert counts → stack up.
# Corre en el Mac. Requiere SSH key configurada para el VPS.
#
# Uso:
#   bash scripts/migrate_data.sh user@host
#   bash scripts/migrate_data.sh root@123.45.67.89
#
# Pre-requisitos:
#   - Stack de desarrollo levantado localmente (para hacer el backup).
#   - SSH key configurada: ssh-copy-id user@host (o ~/.ssh/config).
#   - Proyecto clonado en el VPS bajo /root/match-predictor (o ajustar REMOTE_DIR).
#
# Variable de entorno opcional:
#   REMOTE_DIR  — ruta del proyecto en el VPS (default: /root/match-predictor)

set -euo pipefail

# ---------------------------------------------------------------------------
# Parámetros
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
  echo "Uso: $0 user@host" >&2
  echo "Ejemplo: $0 root@123.45.67.89" >&2
  exit 1
fi

TARGET="$1"
REMOTE_DIR="${REMOTE_DIR:-/root/match-predictor}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="$PROJECT_DIR/backups"

# ---------------------------------------------------------------------------
# Paso 1: Backup local
# ---------------------------------------------------------------------------
echo "==> [1/6] Creando backup local de la BD..."
bash "$SCRIPT_DIR/backup.sh"

# shellcheck disable=SC2012
DUMP_FILE="$(ls -t "$BACKUP_DIR"/*.sql.gz 2>/dev/null | head -1)"
if [[ -z "$DUMP_FILE" ]]; then
  echo "ERROR: No se encontró ningún dump en $BACKUP_DIR" >&2
  exit 1
fi
DUMP_NAME="$(basename "$DUMP_FILE")"
echo "    Dump: $DUMP_FILE"

# ---------------------------------------------------------------------------
# Paso 2: Copiar dump al VPS
# ---------------------------------------------------------------------------
echo "==> [2/6] Copiando dump al VPS ($TARGET)..."
ssh "$TARGET" "mkdir -p ~/backups"
scp "$DUMP_FILE" "$TARGET:~/backups/$DUMP_NAME"
echo "    Dump copiado → ~/backups/$DUMP_NAME"

# ---------------------------------------------------------------------------
# Paso 3: Iniciar solo la BD en el VPS
# ---------------------------------------------------------------------------
echo "==> [3/6] Iniciando Postgres en VPS..."
# shellcheck disable=SC2029
ssh "$TARGET" "cd $REMOTE_DIR && docker compose -f docker-compose.prod.yml up -d db"

echo "    Esperando que Postgres esté listo (hasta 60s)..."
# Las variables $REMOTE_DIR y $DUMP_NAME se expanden en el cliente (intencional: los
# valores locales se pasan al script remoto). Las variables \$ELAPSED y \$TIMEOUT se
# escapan para que se expandan en el shell REMOTO.
# shellcheck disable=SC2029
ssh "$TARGET" "
  TIMEOUT=60
  ELAPSED=0
  until docker compose -f $REMOTE_DIR/docker-compose.prod.yml exec -T db \
      pg_isready -U postgres -d match_predictor -q; do
    sleep 2
    ELAPSED=\$((ELAPSED + 2))
    if [[ \$ELAPSED -ge \$TIMEOUT ]]; then
      echo 'ERROR: Timeout esperando Postgres' >&2
      exit 1
    fi
  done
  echo '    Postgres listo.'
"

# ---------------------------------------------------------------------------
# Paso 4: Restaurar dump
# ---------------------------------------------------------------------------
echo "==> [4/6] Restaurando dump en Postgres..."
# gunzip + psql en pipeline: el dump incluye esquema + datos + alembic_version.
# shellcheck disable=SC2029
ssh "$TARGET" "
  gunzip -c ~/backups/$DUMP_NAME | \
    docker compose -f $REMOTE_DIR/docker-compose.prod.yml exec -T db \
      psql -U postgres match_predictor
"
echo "    Restore completado."

# ---------------------------------------------------------------------------
# Paso 5: Verificar counts
# ---------------------------------------------------------------------------
echo "==> [5/6] Verificando counts..."

# psql -t: solo filas (sin encabezado ni pie); tr elimina espacios y saltos de línea.
# shellcheck disable=SC2029
MATCH_COUNT="$(ssh "$TARGET" "
  docker compose -f $REMOTE_DIR/docker-compose.prod.yml exec -T db \
    psql -U postgres match_predictor -t -c 'SELECT COUNT(*) FROM match'
" | tr -d ' \r\n')"

# shellcheck disable=SC2029
ODDS_COUNT="$(ssh "$TARGET" "
  docker compose -f $REMOTE_DIR/docker-compose.prod.yml exec -T db \
    psql -U postgres match_predictor -t -c 'SELECT COUNT(*) FROM odds'
" | tr -d ' \r\n')"

# shellcheck disable=SC2029
SIGNAL_COUNT="$(ssh "$TARGET" "
  docker compose -f $REMOTE_DIR/docker-compose.prod.yml exec -T db \
    psql -U postgres match_predictor -t -c 'SELECT COUNT(*) FROM value_signal'
" | tr -d ' \r\n')"

echo "    match:         $MATCH_COUNT  (requerido: ≥49,443)"
echo "    odds:             (requerido: >5,800)"
echo "    value_signal:  $SIGNAL_COUNT (requerido: ≥69)"

FAIL=0

if [[ "$MATCH_COUNT" -lt 49443 ]]; then
  echo "ERROR: match insuficiente — $MATCH_COUNT < 49443. Restauración incompleta." >&2
  FAIL=1
fi

if [[ "$ODDS_COUNT" -le 5800 ]]; then
  echo "ERROR: odds insuficiente — $ODDS_COUNT ≤ 5800. Las odds no se recuperaron." >&2
  FAIL=1
fi

if [[ "$SIGNAL_COUNT" -lt 69 ]]; then
  echo "ERROR: value_signal insuficiente — $SIGNAL_COUNT < 69. Las señales no se recuperaron." >&2
  FAIL=1
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo "Abortando — corregí el restore antes de levantar el stack." >&2
  exit 1
fi

echo "    Counts OK ✓"

# ---------------------------------------------------------------------------
# Paso 6: Levantar stack completo
# ---------------------------------------------------------------------------
echo "==> [6/6] Levantando stack completo en VPS..."
# shellcheck disable=SC2029
ssh "$TARGET" "cd $REMOTE_DIR && docker compose -f docker-compose.prod.yml up -d --build"

echo ""
echo "=========================================="
echo "  Migración completada exitosamente."
echo "=========================================="
echo ""
echo "Próximos pasos:"
echo "  1. Desde tu Mac, abrí un túnel SSH:"
echo "       ssh -L 8080:localhost:8080 $TARGET"
echo "  2. Visitá http://localhost:8080 en el navegador."
echo "  3. Para la operación diaria, en el VPS:"
echo "       cd /root/match-predictor"
echo "       bash scripts/tournament_update.sh"
