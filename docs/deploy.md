# Runbook de Deploy en VPS — Mundial 2026

Guía paso a paso para desplegar el sistema en un droplet de DigitalOcean.
Diseñado para alguien sin experiencia previa en ops: cada comando es copy-paste.
Tiempo estimado: < 30 minutos (más el tiempo de migración de datos).

---

## 1. Bootstrap del VPS

### Crear el droplet (si todavía no lo hiciste)

1. Entrá a [cloud.digitalocean.com](https://cloud.digitalocean.com).
2. Create → Droplet → **Ubuntu 24.04 (LTS) x64**.
3. Tamaño mínimo recomendado: 2 GB RAM / 1 vCPU / 50 GB SSD.
4. Autenticación: **SSH Key** (pegá tu clave pública `~/.ssh/id_ed25519.pub`).
5. Create Droplet. Esperá hasta que aparezca la IP del droplet en el panel.

### Conectarse y configurar Docker

```bash
# Reemplazá VPS_IP con la IP de tu droplet (la que ves en el panel)
ssh root@VPS_IP
```

Una vez dentro del VPS:

```bash
# Docker oficial (instala compose v2 plugin, más reciente que apt docker.io)
curl -fsSL https://get.docker.com | sh

# Verificar
docker version
docker compose version
```

---

## 2. Clonar el repositorio

Necesitás un **Personal Access Token (PAT) de GitHub** con permisos read-only sobre el repo.

### Cómo crear el PAT fine-grained (read-only)

1. En GitHub: **Settings → Developer settings → Personal access tokens → Fine-grained tokens**.
2. Click **Generate new token**.
3. Nombre: `match-predictor-vps` (o lo que quieras).
4. **Repository access → Only select repositories → match-predictor**.
5. **Permissions → Repository permissions → Contents → Read-only**.
6. Generate token. Copiá el token (empieza con `github_pat_...`).

### Clonar en el VPS

```bash
# Reemplazá TU_TOKEN con el PAT que acabás de crear
git clone https://TU_TOKEN@github.com/MiguelP4lacios/match-predictor.git ~/match-predictor
cd ~/match-predictor
```

### Alternativa: deploy key (sin PAT)

Si preferís usar SSH en lugar de HTTPS:

```bash
# En el VPS: generar par de claves (sin passphrase)
ssh-keygen -t ed25519 -C "vps-deploy" -f ~/.ssh/deploy_key -N ""
cat ~/.ssh/deploy_key.pub
```

Copiá la clave pública. En GitHub: **Settings del repo → Deploy keys → Add deploy key**.
Pegá la clave, tildá *Allow read access*, guardá.

```bash
# Clonar con la deploy key
GIT_SSH_COMMAND='ssh -i ~/.ssh/deploy_key -o IdentitiesOnly=yes' \
  git clone git@github.com:MiguelP4lacios/match-predictor.git ~/match-predictor
cd ~/match-predictor
```

---

## 3. Crear el archivo `.env`

> **IMPORTANTE: Nunca commiteés el `.env`. Está en `.gitignore`, pero acordate: jamás
> hagás `git add .env`.**

```bash
cd ~/match-predictor

cat > .env << 'EOF'
# API key de The Odds API (https://the-odds-api.com)
# Free tier: 500 créditos/mes. Registrate y copiá tu clave.
ODDS_API_KEY=<tu_api_key_aqui>
EOF
```

---

## 4. Migración de datos (Mac → VPS)

> Esta etapa transfiere la BD completa del Mac al VPS, preservando los odds capturados
> (son irrecuperables: no hay histórico gratuito de odds de selecciones).
> Se corre **desde el Mac**, no desde el VPS.

### Pre-requisitos en el Mac

- Stack de desarrollo levantado (`docker compose up -d --build`).
- SSH key del Mac agregada al VPS (el script usa `scp` + `ssh`).

### Ejecutar la migración

```bash
# Desde el directorio del proyecto en tu Mac:
bash scripts/migrate_data.sh root@VPS_IP
```

El script hace todo automáticamente:
1. `pg_dump` comprimido de tu BD local.
2. `scp` del dump al VPS.
3. Inicia solo Postgres en el VPS.
4. Restaura el dump (esquema + datos + odds).
5. Verifica counts: `match ≥ 49,443`, `odds_snapshot > 5,800`, `value_signal ≥ 69`.
6. Si los counts pasan, levanta el stack completo con `--build`.

Si el script falla en el paso 5 (counts insuficientes), revisá el restore antes de continuar.

---

## 5. Levantar el stack (primera vez o rebuild)

Si ya corriste `migrate_data.sh`, el stack ya está levantado. Para levantarlo manualmente:

```bash
# Desde ~/match-predictor en el VPS
cd ~/match-predictor
docker compose -f docker-compose.prod.yml up -d --build
```

Verificar que todos los servicios estén corriendo:

```bash
docker compose -f docker-compose.prod.yml ps
```

Deberías ver:
- `db` → Up (healthy)
- `api` → Up (healthy)
- `frontend` → Up

Los servicios one-shot (`migrate`, `ingest`) van a aparecer como `Exited (0)` — es correcto.

---

## 6. Túnel SSH + verificación

> El frontend solo es accesible en `127.0.0.1:8080` del VPS (no hay puerto público).
> El acceso se hace por túnel SSH desde tu Mac.

### Abrir el túnel

```bash
# Desde tu Mac — dejá esta terminal abierta mientras navegás
ssh -L 8080:localhost:8080 root@VPS_IP
```

### Verificar que todo funciona

Abrí otra terminal en tu Mac:

```bash
# API (vía nginx proxy)
curl http://localhost:8080/api/v1/signals
# Debe retornar JSON: {"items": [...], "total": N}

# Dashboard
# Abrí http://localhost:8080 en el navegador
```

---

## 7. Operación diaria

### Loop de actualización del torneo

Corre este script en el VPS cada día (o manualmente antes de ver señales):

```bash
cd ~/match-predictor
bash scripts/tournament_update.sh
```

Pasos que ejecuta:
1. Captura odds actuales (The Odds API).
2. Ingesta histórica desde martj42 (detecta novedades, upsert seguro).
3. Recalcula ratings Elo.
4. Genera predicciones 1X2 para fixtures futuros.
5. Genera señales +EV PAPER.

Si los créditos de odds están agotados:

```bash
bash scripts/tournament_update.sh --skip-odds
```

### Cron automático (backup + update)

```bash
# Editá el crontab del VPS:
crontab -e
```

Agregá estas líneas:

```
# Backup diario a las 2am UTC
0 2 * * * cd /root/match-predictor && bash scripts/backup.sh >> /var/log/backup.log 2>&1

# Update del torneo a las 3am UTC (después del backup)
0 3 * * * cd /root/match-predictor && bash scripts/tournament_update.sh >> /var/log/tournament_update.log 2>&1
```

### Backup manual

```bash
cd ~/match-predictor
bash scripts/backup.sh
# El dump queda en backups/YYYY-MM-DD_HHMMSS.sql.gz
ls -lh backups/
```

---

## 8. Logs y troubleshooting

### Ver logs en tiempo real

```bash
# API (errores, requests)
docker compose -f docker-compose.prod.yml logs -f api

# Base de datos
docker compose -f docker-compose.prod.yml logs -f db

# Frontend (nginx)
docker compose -f docker-compose.prod.yml logs -f frontend

# Todos los servicios a la vez
docker compose -f docker-compose.prod.yml logs -f
```

### Reiniciar un servicio

```bash
docker compose -f docker-compose.prod.yml restart api
docker compose -f docker-compose.prod.yml restart frontend
```

### Rebuild con nuevo código

```bash
cd ~/match-predictor
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

### Ver el estado del stack

```bash
docker compose -f docker-compose.prod.yml ps
```

### La API no responde (503 desde el browser)

```bash
# Verificar que api está healthy
docker compose -f docker-compose.prod.yml ps api

# Ver logs de la api
docker compose -f docker-compose.prod.yml logs --tail=50 api

# Reiniciar si hace falta
docker compose -f docker-compose.prod.yml restart api
```

### Quedarse sin espacio en disco

```bash
# Ver uso
df -h

# Limpiar imágenes y contenedores huérfanos de Docker
docker system prune -f

# Limpiar backups viejos (mantener los últimos 7)
ls -t backups/*.sql.gz | tail -n +8 | xargs rm -f
```

---

## Referencia rápida

| Acción | Comando |
|--------|---------|
| Levantar stack | `docker compose -f docker-compose.prod.yml up -d --build` |
| Bajar stack | `docker compose -f docker-compose.prod.yml down` |
| Ver estado | `docker compose -f docker-compose.prod.yml ps` |
| Loop diario | `bash scripts/tournament_update.sh` |
| Backup | `bash scripts/backup.sh` |
| Logs | `docker compose -f docker-compose.prod.yml logs -f api` |
| Túnel SSH | `ssh -L 8080:localhost:8080 root@VPS_IP` |

> **Nota de seguridad**: `docker compose config` imprime las variables de entorno
> resueltas — incluida `ODDS_API_KEY`. No pegues su salida en issues/chats sin
> redactarla primero.
