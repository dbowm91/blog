# Docker

Multi-container Docker setup for production deployment.

## Services

| Service | Image | Purpose |
|---------|-------|---------|
| `blog` | Custom | Main Flask app (Granian ASGI) |
| `celery` | Custom | Celery worker |
| `redis` | `redis:7-alpine` | Cache and message broker |
| `nginx` | `nginx:alpine` | Reverse proxy (optional, `reverse-proxy` profile) |
| `backup` | Custom | Scheduled database backups |

## Installation

The installer (`scripts/install.sh`) supports Docker mode with `--docker`:

```bash
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --docker
```

For native (non-Docker) installation, the installer uses a versioned release layout with atomic symlinks. Use `--system` (default, installs to `/opt/devlog`) or `--user` (installs to `~/.local/share/devlog`):

```bash
# System-wide
curl -fsSL ... | bash -s -- --native --system

# Per-user (XDG-compliant)
curl -fsSL ... | bash -s -- --native --user
```

The installer handles code artifacts only (download, checksum verification, virtualenv creation, activation). Configuration, database setup, and admin creation are delegated to `devlog onboard` (see [installation.md](installation.md) for the full responsibility boundary).

## Docker Compose Profiles

| Profile | Services | Purpose |
|---------|----------|---------|
| `production` | `blog`, `celery`, `redis` | Core production stack (app on `127.0.0.1:5000`); does not terminate TLS |
| `reverse-proxy` | `nginx` | Optional nginx reverse proxy — requires certificate configuration before use |
| `backup` | `backup` | Scheduled backups |

## Dockerfile

Three-stage build:
1. **Frontend builder stage** (`node:20-alpine`): Runs `npm ci` + `npm run build` to produce Vite-bundled assets in `app/static/dist/`
2. **Python builder stage** (`python:3.12-slim`): Installs Python dependencies into a virtualenv
3. **Runtime stage** (`python:3.12-slim`): Copies the virtualenv from the Python builder and built frontend assets from the frontend builder; sets up non-root user and Granian CMD

The frontend assets are copied into the runtime image via:
```dockerfile
COPY --from=frontend-builder /home/blog/app/static/dist /home/blog/app/static/dist
```

This means `npm ci && npm run build` does **not** need to run separately for Docker builds — it happens automatically in the first stage. The CI `docker-build` job verifies this by checking that `app/static/dist/.vite/manifest.json` exists in the built image.

### Key Features
- Non-root user (`blog`)
- Three-stage build for minimal image size (no Node.js in runtime image)
- Health checks

Resource limits (memory, CPU) are configured in `docker-compose.yml` under each service's `deploy.resources` section, not in the Dockerfile itself.

## Backup Service

The `backup` service in `docker-compose.yml:119-137` runs `backup.py` with `working_dir: /home/blog`. The backup script uses a relative path (`instance/blog.db` at `backup.py:23`) which resolves from the working directory. The `blog_data` volume is mounted at `/home/blog/instance:ro` (read-only) to provide database access. The `BACKUP_DIR` environment variable (`/backups`) directs output to the `./backups` host mount.

## Nginx Configuration

Located in `nginx/` subdirectory:
- `nginx/nginx.conf` - Main configuration
- `nginx/conf.d/blog.conf` - Blog-specific settings (vhost, routes, etc.)
- Gzip compression (optionally Brotli with custom nginx image)
- Rate limiting (login: 5r/m, admin: 20r/m)
- Static file caching
- SSL termination (requires external certificates — not automatic)
- Health check endpoint proxy to `/health`

The nginx service is **optional** and part of the `reverse-proxy` profile. The core production profile does not include nginx. For public deployment, TLS must be handled by an external reverse proxy (Caddy, nginx, Traefik, cloud load balancer) proxying to `http://127.0.0.1:5000`.

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

### Celery Configuration

Configured in `app/celery_app.py:20-31`:

| Setting | Value | Purpose |
|---------|-------|---------|
| `task_time_limit` | 300s | Hard time limit per task (kills worker) |
| `task_soft_time_limit` | 240s | Soft time limit (raises `SoftTimeLimitExceeded`) |
| `worker_prefetch_multiplier` | 1 | Worker fetches one task at a time |
| `worker_max_tasks_per_child` | 100 | Recycle worker after 100 tasks (prevents memory leaks) |

Additional config when Flask app context is available (`app/celery_app.py:33-37`):
- `task_acks_late=True` — Acknowledge tasks after execution (not before)
- `task_reject_on_worker_lost=True` — Re-queue task if worker crashes

**Important**: The Celery worker runs with `--concurrency=1` (see `docker-compose.yml:66`). This single-concurrency setting ensures:
- Newsletter emails are sent in order without duplication
- Webhook delivery is serialized

Workers can be scaled independently:
```bash
docker-compose up -d --scale celery=3
```

**Warning:** The `--concurrency=1` setting is per-container, not total. Scaling to 3 containers (`--scale celery=3`) results in 3x parallelism (3 concurrent workers). This can cause duplicate newsletter sends or webhook deliveries unless task routing or queue partitioning is implemented.

## Multi-Worker Deployment Considerations

**APScheduler Limitation:** APScheduler jobs run in-process and use FileLock for concurrency control. FileLock only works on a single machine, meaning:
- In multi-container deployments, each container runs its own APScheduler
- Without external coordination (Redis, etcd), jobs may run on all replicas simultaneously
- This is acceptable for read-heavy jobs but may cause duplicate newsletter sends or backups

For coordinated multi-worker deployments, consider:
1. Using Celery Beat instead of APScheduler for scheduled tasks
2. Adding Redis-based distributed locking
3. Running APScheduler only on a single designated container

## APScheduler Multi-Container Limitations

APScheduler uses `filelock.FileLock` with `timeout=0` (see `app/scheduler.py:76`). This lock mechanism only works on a single machine and does not provide cross-machine coordination.

**Problem:** When running multiple container replicas:
- Each container runs its own APScheduler instance
- FileLock cannot coordinate across container boundaries
- Scheduled jobs (newsletter, backups, post publishing) execute on all replicas simultaneously
- This causes duplicate newsletter sends, duplicate backups, and duplicate post publishes

**Impact:**
| Job | Consequence |
|-----|-------------|
| `send_daily_newsletter` | Duplicate emails to subscribers |
| `run_daily_backup` | Multiple concurrent backup processes |
| `publish_scheduled_posts` | Duplicate published posts |
| `cleanup_expired_subscribers` | No data corruption, but wasted cycles |

**Mitigation Options:**
1. **Run APScheduler on single container only** - Use container labels/constraints to ensure only one replica runs scheduler jobs
2. **Use Celery Beat** - Replace APScheduler with Celery Beat for distributed job scheduling
3. **External distributed lock** - Implement Redis or etcd-based locking (future enhancement)

### Detection and Alerting

To detect APScheduler race conditions in multi-container deployments:

**Log-based detection:** Monitor logs for multiple instances of the same job firing simultaneously:
```
grep "Starting job" app.log | grep "send_daily_newsletter" | wc -l
```
If more than 1 instance starts within a short window, a race condition occurred.

**FileLock skip detection:** When FileLock fails to acquire (lock held by another container), the job logs a warning:
```
WARNING - Job "send_daily_newsletter" was not executed because the lock file ... is already acquired
```
Multiple skip warnings across different containers indicate no actual job execution is happening.

**Newsletter count anomaly:** Track `newsletter_sent_at` timestamps on posts. If posts show multiple newsletter send events with very close timestamps (within seconds), this indicates duplicate sends.

**Alerting configuration:**
1. Set up log aggregation (e.g., ELK, Loki, CloudWatch) to detect concurrent job execution
2. Alert when `send_daily_newsletter` runs more than once per scheduled interval
3. Alert when `run_daily_backup` creates multiple backups within a short window
4. Monitor `publish_scheduled_posts` for duplicate execution within 5-minute window

**Scaling warning:** Running more than 1 `blog` container with APScheduler enabled will cause duplicate job execution. FileLock with `timeout=0` cannot coordinate across containers. Always ensure only 1 replica has the scheduler active, or disable APScheduler on additional replicas via environment variables or deployment constraints.

The `celery` service in `docker-compose.yml` runs with `--concurrency=1` and does not run APScheduler. APScheduler runs within the `blog` service (via `app/__init__.py` initialization).

## Environment Variables

| Variable | Description |
|----------|-------------|
| `FLASK_ENV` | `development` or `production` (affects Redis caching) |
| `SECRET_KEY` | Flask secret key |
| `ADMIN_PASSWORD` | Admin password |
| `ADMIN_USERNAME` | Admin username (optional, defaults to `admin`) |
| `SQLALCHEMY_DATABASE_URI` | SQLAlchemy connection string (optional, defaults to SQLite `blog.db`) |
| `API_KEY` | API key for REST API authentication |
| `SESSION_COOKIE_SECURE` | Set to `true` for HTTPS-only cookies (default: `true`) |
| `DATABASE_URL` | PostgreSQL connection string (optional, defaults to SQLite `blog.db`) |
| `REDIS_URL` | Redis connection |
| `SMTP_HOST` | SMTP server for newsletter/email (optional) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |
| `CACHE_REDIS_URL` | Redis URL for Flask-Caching (optional, defaults to REDIS_URL) |
| `CELERY_BROKER_URL` | Celery broker URL (optional, defaults to REDIS_URL) |
| `HEALTH_CHECK_SECRET` | Secret for detailed health check access |
| `METRICS_SECRET` | Secret for `/metrics` endpoint (required with `ENABLE_METRICS=true`) |
| `ENABLE_METRICS` | Enable `/metrics` endpoint (default: `false`; requires `METRICS_SECRET` in production) |
| `PROXY_COUNT` | Number of proxies for ProxyFix middleware (default: 1) |
| `PYTHONPATH` | Python path for Celery/backup services (set to `/home/blog`) |

## Health Check Endpoint

The `/health` endpoint provides JSON status for all components:

| Aspect | Details |
|--------|---------|
| Authentication | Optional HMAC authentication when `HEALTH_CHECK_SECRET` is configured |
| Rate Limiting | 60 requests/minute via Flask-Limiter |
| Status Response | Returns 200 even if optional services are degraded |

### Docker Health Check Configuration

The `blog` service uses a Docker health check with `start_period: 10s`:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `start_period` | 10s | Grace period before first health check evaluation; container reports `starting` status during this time |
| `interval` | 30s | Time between checks |
| `timeout` | 10s | Max time for check to complete |
| `retries` | 3 | Consecutive failures before unhealthy |

**Note:** The Dockerfile `HEALTHCHECK` instruction uses `--timeout=3s` while docker-compose overrides it to `timeout: 10s`. The docker-compose value takes precedence at runtime. The shorter Dockerfile timeout is a fallback for non-compose builds.

**Note:** During the 10-second `start_period`, the container is in `starting` state and will not be marked unhealthy even if the health check fails. The container is only evaluated as healthy or unhealthy after `start_period` elapses.

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
| `BACKUP_ENCRYPTION_KEY` | 12 characters | `python -c "import secrets; print(secrets.token_urlsafe(12))"` |
| `WEBHOOK_ENCRYPTION_KEY` | 32 bytes / 64 hex chars | `python -c "import secrets; print(secrets.token_hex(32))"` |

## Resource Limits

Memory limits configured in `docker-compose.yml` under `deploy.resources`:

| Service | Limit | Reservation |
|---------|-------|-------------|
| `blog` | 512M | 256M |
| `celery` | 256M | - |
| `redis` | 128M | - |

## Scripts Directory

Operational scripts in `scripts/` for development and deployment tasks:

| Script | Language | Purpose |
|--------|----------|---------|
| `build_assets.py` | Python | Basic CSS/JS minification (removes whitespace and comments). Creates `.orig` backups of modified files. |
| `dev.sh` | Bash | Local development setup: checks Python ≥ 3.12, creates venv, installs deps, runs migrations, prints env var instructions. |
| `update-assets.sh` | Bash | Downloads latest CDN assets (marked.js, Prism.js) into `app/static/js/lib/`. |
| `sync_backups.sh` | Bash | Syncs local backups to off-site storage via rclone or native AWS S3 CLI. Supports `--dry-run`, `--verify`, and `--cleanup` flags. |

### `build_assets.py`

Minifies CSS and JS files in `app/static/css/` and `app/static/js/`. Use `--dry-run` to preview, `--force` to overwrite. Not intended for production use (see Vite bundler for production builds).

### `dev.sh`

Full local development bootstrap. Verifies Python ≥ 3.12, creates virtualenv, installs requirements, runs `flask db upgrade`, and prints startup instructions including required environment variables (`SECRET_KEY`, `ADMIN_PASSWORD`).

### `update-assets.sh`

Fetches marked.js and Prism.js from jsDelivr CDN into `app/static/js/lib/`. Run after dependency updates to refresh vendored libraries.

### `sync_backups.sh`

Off-site backup synchronization. Requires `REMOTE_TYPE` (`s3` or `rclone`) and corresponding credentials. Options: `--dry-run` (preview), `--verify` (post-sync check), `--cleanup DAYS` (prune old local backups). Default retention: 7 days.

## Granian Configuration

The blog service runs via Granian ASGI server, configured in the Dockerfile `CMD`:

```
granian --interface asgi --workers 4 --timeout 60 --host 0.0.0.0 --port 5000 run:asgi_app
```

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `--workers` | 4 | Worker processes (matches typical CPU core count) |
| `--timeout` | 60 | Request timeout in seconds |
| `--interface` | asgi | ASGI interface (Flask via `run:asgi_app`) |
| `--host` | 0.0.0.0 | Listen on all interfaces |
| `--port` | 5000 | Application port |

**Note:** Celery runs with `--concurrency=1` (single worker) to prevent duplicate newsletter sends and webhook deliveries. The Granian worker count (4) is independent of Celery concurrency.

## Nginx Proxy Networking

The nginx configuration uses `proxy_pass http://blog:5000` to reach the blog service. In Docker Compose, containers on the same user-defined network share a network namespace for inter-container communication. The `blog` service exposes port 5000 via the `expose` directive, and nginx resolves `blog` to the blog service through the shared Docker network.

The nginx `client_max_body_size` is set to `16M` to accommodate file uploads proxied to the Flask app.

### Nginx Security Headers

The nginx configuration (`nginx/conf.d/blog.conf:25-32`) sets security headers including `X-XSS-Protection "1; mode=block"`. These headers are only present when traffic is proxied through nginx — Flask does not set them. Direct access to the Flask app (port 5000) will not include these headers.

## Backup Service Encryption Key Loading

The backup container (`docker-compose.yml:105-120`) runs `backup.py` with `PYTHONPATH=/home/blog` to import `app.services.backup`. Encryption keys are not mounted as files — they are loaded via the application's config module (`app/config.py`) which reads from `config.toml` and environment variables.

The backup service mounts:
- `blog_data:/home/blog/instance:ro` — read-only database access
- `./backups:/backups` — writeable backup output directory

The `BACKUP_ENCRYPTION_KEY` can be provided via:
- Environment variable `BACKUP_ENCRYPTION_KEY` (set in host environment or `.env` file)
- `config.toml` under `[backup]` section as `encryption_key`

If the key is set in both places, the environment variable takes precedence.

**Fallback behavior:** If `BACKUP_ENCRYPTION_KEY` is set but cannot be loaded (e.g., cryptography library unavailable), backup proceeds unencrypted. A `WARNING: Backup encryption failed, proceeding without encryption` is logged (`backup.py:69-70`).

## Production Checklist

Before deploying to production, verify all items:

### Secrets & Credentials
- [ ] `SECRET_KEY` set to a random 64-character hex string (`python3 -c 'import secrets; print(secrets.token_hex(32))'`)
- [ ] `ADMIN_PASSWORD` set to a strong password (12+ chars, mixed case, numbers, symbols)
- [ ] `BACKUP_ENCRYPTION_KEY` set (via environment or `config.toml [backup] encryption_key`) if using encrypted backups (12+ characters)
- [ ] `WEBHOOK_ENCRYPTION_KEY` set if using encrypted webhooks (64-char hex string)
- [ ] `HEALTH_CHECK_SECRET` set for authenticated health check endpoint
- [ ] All secrets stored in `.env` file or environment, **not** in `config.toml` or source code

### Application Configuration
- [ ] `config.toml [server] debug = false`
- [ ] `config.toml [site] base_url` set to `https://` URL
- [ ] `SESSION_COOKIE_SECURE = true` (enforced automatically in production)
- [ ] `PROXY_COUNT` set correctly for reverse proxy setup (default: 1)
- [ ] `FLASK_ENV=production` set to enable Redis caching

### SMTP / Newsletter
- [ ] `SMTP_USER` and `SMTP_PASSWORD` configured for newsletter delivery
- [ ] `config.toml [email] smtp_host` set (e.g., `smtp.gmail.com`)
- [ ] `config.toml [email] from_address` set to valid sender address
- [ ] Test email delivery before enabling newsletter scheduler

### Database & Backups
- [ ] Database initialized (`flask db upgrade`)
- [ ] `instance/blog.db` not in web-accessible directory
- [ ] Backup service tested (`docker-compose --profile backup up`)
- [ ] Off-site backup sync configured (see `scripts/sync_backups.sh`)

### Networking & TLS
- [ ] HTTPS enforced at reverse proxy (HTTP-to-HTTPS redirect)
- [ ] HSTS header configured at reverse proxy
- [ ] Static files served by nginx/Caddy (not proxied to Flask)
- [ ] `client_max_body_size` set in nginx for file uploads

### Security
- [ ] Rate limiting configured for `/admin/login` (5 req/min)
- [ ] `CSRF_ENABLED` not disabled in production
- [ ] Admin dashboard not exposed on public interfaces without authentication
- [ ] Redis not exposed to untrusted networks

### Monitoring
- [ ] Health check endpoint accessible (`/health`)
- [ ] `HEALTH_CHECK_SECRET` set for detailed health status
- [ ] Log monitoring configured for error tracking
- [ ] Disk space monitoring for database and backups

## See Also
- [CI/CD](cicd.md) - Docker in CI pipeline
- [Security](security.md) - Security configuration
