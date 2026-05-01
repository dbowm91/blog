FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash blog

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

RUN mkdir -p /home/blog/instance /home/blog/logs /home/blog/app/static/uploads
RUN chown -R blog:blog /home/blog

COPY --chown=blog:blog . .

USER blog

ENV PATH="/home/blog/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run:app \
    REDIS_URL="redis://redis:6379/0"

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:5000/health || exit 1

CMD granian --interface asgi --workers 2 --host 0.0.0.0 --port 5000 run:asgi_app
