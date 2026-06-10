# ── Stage build ─────────────────────────────────────────────────────────────
FROM node:22-alpine AS build

WORKDIR /app

# Instalar dependencias primero (cache de capas)
COPY package*.json ./
RUN npm ci

# Copiar fuentes y compilar
COPY . .
RUN npm run build

# ── Stage prod ───────────────────────────────────────────────────────────────
FROM nginx:alpine AS prod

# Copiar artefactos de build
COPY --from=build /app/dist /usr/share/nginx/html

# Configuración nginx: sirve dist/ + proxy /api → api:8000
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
