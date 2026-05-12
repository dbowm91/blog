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

Located in `nginx/` subdirectory:
- `nginx/nginx.conf` - Main configuration
- `nginx/conf.d/blog.conf` - Blog-specific settings (vhost, routes, etc.)
- Gzip compression (optionally Brotli with custom nginx image)
- Rate limiting (login: 5r/m, admin: 20r/m)
- Static file caching
- SSL termination (external)
- Health check endpoint proxy to `/health`

### Brotli Configuration

Brotli compression is commented out in `nginx/nginx.conf:26-34`:
- Requires custom nginx image with `--with-http_brotli_module`
- Standard `nginx:alpine` does not include Brotli support

## Celery Task Queues

For production deployments with Celery:
- **images**: Image processing
- **newsletter**: Newsletter delivery
- **webhooks**: Webhook delivery
- **email**: Transactional emails
- **backup**: Database backups

Workers can be scaled independently:
```bash
docker-compose up -d --scale celery=3
```

## Multi-Worker Deployment Considerations

**APScheduler Limitation:** APScheduler jobs run in-process and use FileLock for concurrency control. FileLock only works on a single machine, meaning:
- In multi-container deployments, each container runs its own APScheduler
- Without external coordination (Redis, etcd), jobs may run on all replicas simultaneously
- This is acceptable for read-heavy jobs but may cause duplicate newsletter sends or backups

For coordinated multi-worker deployments, consider:
1. Using Celery Beat instead of APScheduler for scheduled tasks
2. Adding Redis-based distributed locking
3. Running APScheduler only on a single designated container

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
