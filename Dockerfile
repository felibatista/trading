# Imagen Python compartida por los servicios `bot` y `api`.
FROM python:3.11-slim

WORKDIR /app

# Dependencias (ccxt/pandas/anthropic/fastapi se instalan desde wheels: sin compilador).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Código + config de producción.
COPY bot ./bot
COPY api ./api
COPY config.docker.yaml ./config.docker.yaml

# Directorio de datos (SQLite) — montado como volumen en docker-compose.
RUN mkdir -p /data

ENV PYTHONUNBUFFERED=1

# Comando por defecto (cada servicio lo sobrescribe en docker-compose.yml).
CMD ["python", "-m", "bot", "run", "BTC/USDT", "--loop", "--config", "config.docker.yaml"]
