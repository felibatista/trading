# --- build del panel (Vite) ---
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm install --no-audit --no-fund
COPY web/ ./
ENV VITE_API_BASE=""
RUN npm run build

# --- app: API + panel + flota, en un solo proceso ---
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY bot ./bot
COPY api ./api
COPY config.docker.yaml ./config.docker.yaml
COPY --from=web /web/dist ./web_dist
RUN mkdir -p /data
ENV PYTHONUNBUFFERED=1 \
    AMERICO_CONFIG=config.docker.yaml \
    AMERICO_WEB_DIST=/app/web_dist \
    AMERICO_RUN_FLEET=1
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
