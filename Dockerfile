# Imagen de la app. Sirve para dev (con bind-mount) y para prod/CI (autosuficiente).
FROM python:3.12-slim

# uv: gestor de deps rápido (binario oficial de Astral).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Clave del bind-mount: el venv vive FUERA de /app (/opt/uv-venv), así montar el
# código sobre /app no tapa las dependencias. PYTHONPATH=/app para que `uvicorn`,
# `alembic` y `python -m` importen el paquete `app` sin instalarlo como wheel.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/uv-venv \
    PATH="/opt/uv-venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Capa de deps cacheable: solo se reconstruye si cambian pyproject/lockfile.
# --frozen: falla si uv.lock no está en sync con pyproject.toml (detecta drift).
# Incluye el extra `dev` (pytest, ruff): la misma imagen sirve dev + tests.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra dev --no-install-project

# En dev el código llega por bind-mount y pisa esto; en prod/CI la imagen ya lo trae.
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
