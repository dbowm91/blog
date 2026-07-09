# Deployment

## Docker Compose

### Production Services

| Service | Purpose |
|---------|---------|
| `blog` | Flask web application |
| `celery` | Celery worker for async tasks |
| `redis` | Message broker and cache |
| `nginx` | Reverse proxy and static file serving |
| `backup` | Automated database backups |

### Celery Worker Concurrency

**Important**: The Celery worker runs with `--concurrency=1`:

```yaml
celery:
  command: celery -A app.celery_app worker --loglevel=info --concurrency=1
```

This single-concurrency setting ensures:
- Newsletter emails are sent in order without duplication
- Webhook delivery is serialized
- Database backup operations don't overlap

### Docker Wait for Redis

The `celery` service waits for Redis to be healthy before starting:

```yaml
celery:
  depends_on:
    redis:
      condition: service_healthy
```

Redis uses `redis-cli ping` for health checks. For additional reliability, you can use `docker-compose wait redis` in entrypoint scripts to ensure Redis is ready before the application starts.

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask secret key | Yes |
| `ADMIN_PASSWORD` | Admin login password | Yes |
| `ADMIN_USERNAME` | Admin username (default: admin) | No |
| `DATABASE_URL` | SQLAlchemy database URI | No |
| `SMTP_HOST` | SMTP server hostname | No |
| `SMTP_PASSWORD` | SMTP authentication password | No |
| `SESSION_COOKIE_SECURE` | Secure cookie flag | No |
| `REDIS_URL` | Redis connection URL | No |

### Session Cookie Secure

**Note**: `SESSION_COOKIE_SECURE` passes a string `"true"` not boolean due to docker-compose parsing. This may need to be addressed in future versions.

### Data Volumes

| Volume | Mount Point | Purpose |
|--------|--------------|---------|
| `blog_data` | `/home/blog/instance` | Database and instance files |
| `blog_logs` | `/home/blog/logs` | Application logs |
| `blog_uploads` | `/home/blog/app/static/uploads` | Media files |

### Resource Limits

| Service | Memory Limit | Memory Reservation |
|---------|--------------|---------------------|
| blog | 512MB | 256MB |
| celery | 256MB | - |
| redis | 128MB | - |

## Health Checks

The `blog` service exposes a health check endpoint with two modes:

### Basic Health Check

```
GET /health
```

Returns only `database` and `scheduler` status. Fast, no auth required. Used for Docker healthchecks.

**Location:** `app/routes/public/meta.py:214-365`

### Detailed Health Check

For full health information, authenticate with `HEALTH_CHECK_SECRET`:

```
GET /health?secret=<value>&detailed=true
```

Returns all 8 checks with details. Requires `HEALTH_CHECK_SECRET` environment variable in docker-compose.yml.

### Health Check Status

| Check | Category | Affects Overall Status | Mode |
|-------|----------|------------------------|------|
| database | critical | Yes | Basic + Detailed |
| scheduler | critical | Yes | Basic + Detailed |
| search | critical | Yes | Detailed only |
| disk_space | critical | Yes | Detailed only |
| db_integrity | critical | Yes | Detailed only |
| backup_freshness | optional | No | Detailed only |
| email | optional | No | Detailed only |
| redis | optional | No | Detailed only |
| celery | optional | No | Detailed only |

## Graceful Shutdown

The scheduler runs as a daemon thread and will not prevent process exit. See [Scheduler](../tasks/scheduler.md) for details.