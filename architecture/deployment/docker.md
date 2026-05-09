# Docker

Multi-container Docker setup for production deployment.

## Services

| Service | Image | Purpose |
|---------|-------|---------|
| `blog` | Custom | Main Flask app (Granian ASGI) |
| `celery` | Custom | Celery worker |
| `redis` | `redis:7-alpine` | Cache and message broker |
| `nginx` | `nginx:alpine` | Reverse proxy |

## Docker Compose Profiles

| Profile | Services | Purpose |
|---------|----------|---------|
| (default) | `blog`, `redis` | Development |
| `production` | `blog`, `celery`, `redis`, `nginx` | Production |
| `backup` | `blog` (backup only) | Scheduled backups |

## Dockerfile

Multi-stage build:
1. **Builder stage**: Python dependencies
2. **Runtime stage**: Final image with non-root user

### Key Features
- Non-root user (`blog`)
- Multi-stage for minimal image size
- Health checks

Resource limits (memory, CPU) are configured in `docker-compose.yml` under each service's `deploy.resources` section, not in the Dockerfile itself.

## Nginx Configuration

Located in `nginx/`:
- Gzip compression
- Rate limiting
- Static file caching
- SSL termination (external)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Flask secret key |
| `ADMIN_PASSWORD` | Admin password |
| `DATABASE_URL` | PostgreSQL connection string (optional, defaults to SQLite `blog.db`) |
| `REDIS_URL` | Redis connection |
| `STORAGE_BACKEND` | `local` or `s3` |

## See Also
- [CI/CD](deployment/cicd.md) - Docker in CI pipeline
- [Security](deployment/security.md) - Security configuration
