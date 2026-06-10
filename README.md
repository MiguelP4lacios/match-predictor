# Mundial 2026 — Sistema de Predicción +EV (Selecciones)

Sistema de predicción de resultados de fútbol de selecciones nacionales para
apostar con **valor esperado positivo**. El modelo estadístico (determinista)
calcula probabilidades; el LLM solo las narra. Ver `docs/adr/0002-sistema-apuestas-ev.md`.

## Setup (un solo comando)

No necesitás Python ni uv en tu máquina: todo corre en contenedores. El código se
monta por bind-mount, así que editás local y el contenedor recarga solo.

```bash
docker compose up -d --build
```

Eso orquesta todo en orden: `db` → `migrate` (esquema) → `api` + `ingest` (datos).
Cuando termina, la API ya sirve con el esquema y los datos históricos cargados.

- API: http://localhost:8000  (health: `/health`, `/health/db`)
- Postgres: localhost:5432 (datos persistidos en el volumen `pgdata`)

Comandos útiles:

```bash
docker compose logs -f api                          # ver logs de la app
docker compose run --rm api pytest                  # tests dentro del contenedor
docker compose run --rm api python -m app.ingestion.run --force   # re-ingestar
docker compose down                                 # bajar (datos quedan en pgdata)
docker compose down -v                              # bajar y BORRAR datos
```

> **ADVERTENCIA — `docker compose down -v` DESTRUYE todos los datos de Postgres**,
> incluidas las cuotas capturadas en directo (son **irrecuperables**; no hay histórico
> gratuito de odds de selecciones). Antes de cualquier operación destructiva ejecutá:
>
> ```bash
> bash scripts/backup.sh   # pg_dump comprimido → backups/YYYY-MM-DD_HHMMSS.sql.gz
> ```

> **Nota durante el torneo**: el proceso de `docker compose` se ejecuta en segundo
> plano, pero si tu Mac entra en suspensión la BD deja de recibir escrituras. Usá
> `caffeinate -i docker compose up -d --build` o activá "Prevent your Mac from
> automatically sleeping" en las preferencias de energía mientras el Mundial esté
> en curso.


## Estructura

```
app/
├── core/      # config (env) y conexión a la BD
├── models/    # 15 entidades SQLAlchemy (ver docs/adr/0002)
├── api/       # endpoints FastAPI (lectura desde Postgres, nunca API externa)
└── main.py
migrations/    # Alembic
docs/adr/      # decisiones de arquitectura
```

## Deploy

Para desplegar en producción (VPS DigitalOcean, Mundial 2026), ver el runbook completo:

```bash
# Desde el Mac, una sola vez:
bash scripts/migrate_data.sh root@VPS_IP

# Acceso al dashboard vía túnel SSH:
ssh -L 8080:localhost:8080 root@VPS_IP
# → http://localhost:8080
```

Documentación completa en [`docs/deploy.md`](docs/deploy.md).

## Estado

Fase 1: esqueleto + modelos de datos. Próximo: capa `DataSource` + ingesta.
