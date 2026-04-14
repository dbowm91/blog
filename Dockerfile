FROM python:3.14-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt granian

FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash blog

COPY --from=builder /root/.local /home/blog/.local
COPY --chown=blog:blog . .

RUN mkdir -p /home/blog/instance /home/blog/logs /home/blog/app/static/uploads
RUN chown -R blog:blog /home/blog

USER blog

ENV PATH="/home/blog/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run:app

EXPOSE 5000

CMD ["granian", "--interface", "asgi", "--host", "0.0.0.0", "--port", "5000", "--workers", "2", "run:asgi_app"]
