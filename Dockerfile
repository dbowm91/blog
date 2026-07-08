FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

LABEL org.opencontainers.image.source="https://github.com/dbowm91/blog"
LABEL org.opencontainers.image.description="DevLog - Self-hosted Flask blog CMS"
LABEL org.opencontainers.image.licenses="MIT"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash blog

COPY --from=builder /opt/venv /opt/venv
COPY --chown=blog:blog . .

RUN mkdir -p /home/blog/instance /home/blog/logs /home/blog/app/static/uploads

USER blog

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run:app \
    REDIS_URL="redis://redis:6379/0"

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s CMD curl -f http://localhost:5000/health || exit 1

# Granian with 4 workers for request handling. Set ENABLE_SCHEDULER=true on only
# one container if running multiple replicas to avoid duplicate scheduled jobs.
CMD ["granian", "--interface", "asgi", "--workers", "4", "--timeout", "60", "--host", "0.0.0.0", "--port", "5000", "run:asgi_app"]
