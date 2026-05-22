# CI/CD

## Docker Compose Wait

For reliable service startup in CI/CD pipelines, ensure dependent services are ready before running application code.

### Redis Readiness

Use `docker-compose wait redis` to block until Redis is healthy:

```yaml
# In your entrypoint script
docker-compose wait redis

# Then start your application
python -m gunicorn -b 0.0.0.0:5000 "app:create_app()"
```

This is particularly useful in:
- CI/CD pipelines where service startup may be delayed
- Container orchestration where dependencies may start in any order
- Environments without native health check support

### Health Check Configuration

The `redis` service in docker-compose.yml includes a health check:

```yaml
redis:
  image: redis:7-alpine
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 3s
    retries: 3
```

The `celery` service depends on this health check:

```yaml
celery:
  depends_on:
    redis:
      condition: service_healthy
```