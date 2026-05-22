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

## Health Check Endpoint

The `/health` endpoint provides JSON status for all components:

| Aspect | Details |
|--------|---------|
| Authentication | Optional HMAC authentication when `HEALTH_CHECK_SECRET` is configured |
| Rate Limiting | 60 requests/minute via Flask-Limiter |
| Status Response | Returns 200 even if optional services are degraded |

### Critical Checks

Only these checks affect the overall health status:

- `database` - Database connectivity
- `scheduler` - APScheduler status
- `search` - Search provider status
- `disk_space` - Available disk space
- `db_integrity` - Database integrity

### Optional Checks

These checks are included in detailed output but do not affect the overall health status:

- `backup_freshness` - Backup recency (when backup directory exists)
- `email` - SMTP connectivity
- `redis` - Redis connectivity
- `celery` - Celery worker availability

### Authenticated Detailed Health Check

When `HEALTH_CHECK_SECRET` is configured, detailed health information is available via query parameters:
- `?secret=<value>&detailed=true` - Returns full component status

## Encryption Key Requirements

| Key | Minimum Length | Generation |
|-----|---------------|------------|
| `BACKUP_ENCRYPTION_KEY` | 12 characters | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `WEBHOOK_ENCRYPTION_KEY` | 32 bytes / 64 hex chars | `python -c "import secrets; print(secrets.token_hex(32))"` |

## Resource Limits

Memory limits configured in `docker-compose.yml` under `deploy.resources`:

| Service | Limit | Reservation |
|---------|-------|-------------|
| `blog` | 512M | 256M |
| `celery` | 256M | - |
| `redis` | 128M | - |

## See Also
- [CI/CD](deployment/cicd.md) - Docker in CI pipeline
- [Security](deployment/security.md) - Security configuration
