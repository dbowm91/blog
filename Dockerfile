FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash blog

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt gunicorn

RUN mkdir -p /home/blog/instance /home/blog/logs /home/blog/app/static/uploads
RUN chown -R blog:blog /home/blog

COPY --chown=blog:blog . .

USER blog

ENV PATH="/home/blog/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run:app

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-", "run:app"]
