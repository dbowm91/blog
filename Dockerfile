FROM node:20-alpine AS frontend-builder

WORKDIR /home/blog

COPY package.json package-lock.json ./
RUN npm ci

COPY app/static ./app/static
COPY vite.config.js ./
RUN npm run build

FROM python:3.12-slim AS builder

WORKDIR /home/blog

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

WORKDIR /home/blog

LABEL org.opencontainers.image.source="https://github.com/dbowm91/blog"
LABEL org.opencontainers.image.description="DevLog - Self-hosted Flask blog CMS"
LABEL org.opencontainers.image.licenses="MIT"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash blog

COPY --from=builder /opt/venv /opt/venv
COPY --chown=blog:blog . .
COPY --from=frontend-builder /home/blog/app/static/dist /home/blog/app/static/dist

RUN mkdir -p /data /data/uploads /data/themes /data/backups /data/exports \
    && mkdir -p /etc/devlog \
    && mkdir -p /var/log/devlog \
    && mkdir -p /run/devlog \
    && chown -R blog:blog /data /etc/devlog /var/log/devlog /run/devlog

USER blog

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run:app \
    REDIS_URL="redis://redis:6379/0" \
    DEVLOG_CONFIG_FILE="/etc/devlog/config.toml" \
    DEVLOG_ENV_FILE="/etc/devlog/.env" \
    DEVLOG_DATA_DIR="/data" \
    DEVLOG_LOG_DIR="/var/log/devlog" \
    DEVLOG_RUNTIME_DIR="/run/devlog"

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s CMD curl -f http://localhost:5000/health || exit 1

# Granian with 4 workers for request handling. Set ENABLE_SCHEDULER=true on only
# one container if running multiple replicas to avoid duplicate scheduled jobs.
CMD ["granian", "--interface", "asgi", "--workers", "4", "--timeout", "60", "--host", "0.0.0.0", "--port", "5000", "run:asgi_app"]
