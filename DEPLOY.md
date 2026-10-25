# Deployment Guide

Comprehensive guide for deploying DevLog in production.

## Contents

- [Prerequisites](#1-prerequisites)
- [Quick Start](#2-quick-start)
- [Environment Variables](#3-environment-variables)
- [Configuration](#4-configuration)
- [Granian ASGI Server](#5-granian-asgi-server)
- [Docker Deployment](#6-docker-deployment)
- [Backup and Restore](#7-backup-and-restore)
- [PostgreSQL Migration](#8-postgresql-migration-experimental)
- [Reverse Proxy Setup](#9-reverse-proxy-setup)
- [Rate Limiting](#10-rate-limiting)
- [Systemd Service](#11-systemd-service)
- [Monitoring](#12-monitoring)
- [Maintenance](#13-maintenance)
- [Security Checklist](#14-security-checklist)
- [Dependencies](#15-dependencies)
- [Vite for Admins](#16-vite-for-admins)
- [Operator CLI](#17-operator-cli)

---

## 1. Prerequisites

### Docker Production (Recommended)

- [Docker](https://docs.docker.com/get-docker/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/install/) 2.0+
- A reverse proxy (nginx, Caddy, Traefik) for TLS termination and public access

### Local / Non-Docker

- Python 3.12 or later (tested with 3.12 and 3.13)
- pip
- SQLite 3.35+ (for `PRAGMA journal_mode=WAL` and FTS5 support)
- A reverse proxy (nginx, Caddy recommended)
- A domain with SSL certificate

---

## 2. Quick Start

### Docker Production

```bash
git clone https://github.com/dbowm91/blog.git /opt/blog
cd /opt/blog
cp .env.example .env
# Edit .env: set SECRET_KEY and ADMIN_PASSWORD
docker compose --profile production up -d --build
```

The app binds to `127.0.0.1:5000` (localhost only). For public access, terminate TLS with a host-level reverse proxy (Caddy, nginx, Traefik) and proxy to `http://127.0.0.1:5000` — see [Section 9: Reverse Proxy Setup](#9-reverse-proxy-setup).

Admin panel: `http://localhost:5000/admin/login`.

**First-admin bootstrap:** The `ADMIN_PASSWORD` env var is used only when creating the initial admin user. Changing it later does not overwrite the existing admin password — use the password reset flow (`/admin/forgot-password`) instead.

> **Local HTTP testing:** Set `SESSION_COOKIE_SECURE=false` in your `.env` when testing at `http://localhost:5000`, otherwise admin login cookies will not persist. Never use `SESSION_COOKIE_SECURE=false` in production behind HTTPS.

### Local Development (NOT for production)

```bash
git clone https://github.com/dbowm91/blog.git /opt/blog
cd /opt/blog

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export ADMIN_PASSWORD="your-strong-password-here"
export FLASK_APP=run:app
flask db upgrade

python run.py
```

The app listens on `0.0.0.0:5000` by default.

---

## Support Matrix

| Feature | Status | Notes |
|---------|--------|-------|
| SQLite with WAL | Supported | Default single-server database for v1 |
| PostgreSQL | Experimental | Not recommended for v1 production; health checks report unsupported for SQLite-specific features |
| Local filesystem media | Supported | Default media backend |
| S3-compatible media | Experimental | Requires boto3; not CI-tested |
| Redis (cache/rate limiting) | Supported | Used in Docker production profile |
| Celery + Redis (async tasks) | Supported | Newsletter, webhooks, image variants; included in production compose profile |
| External TLS reverse proxy | Supported/recommended | Caddy/nginx/Traefik/cloud proxy to localhost app |
| Included nginx profile | Optional/advanced | Requires `--profile reverse-proxy` and certificate configuration |
| Metrics endpoint | Supported when enabled | Disabled by default; secret required in production |
| Detailed health | Supported when protected | Basic health remains public; detailed health requires secret in production |

---

## 3. Environment Variables

Environment variables override `config.toml` settings. **Required** variables must be set at runtime.

### Required Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Flask session signing key. Generate: `python3 -c 'import secrets; print(secrets.token_hex(32))'` |
| `ADMIN_PASSWORD` | Password for the admin user |

### Optional Variables

| Variable | Default | Description |
|---|---|---|
| `ADMIN_USERNAME` | `admin` | Admin username |
| `SMTP_HOST` | — | SMTP server hostname. Unset disables the daily newsletter job |
| `SMTP_USER` | — | SMTP auth username for newsletter/email |
| `SMTP_PASSWORD` | — | SMTP auth password |
| `SESSION_COOKIE_SECURE` | `true` | Require HTTPS for session cookies. Set `false` only for local HTTP development |
| `PROXY_COUNT` | `1` | Number of reverse proxies in front of the app. Set `0` to disable `ProxyFix` |
| `API_KEY` | — | REST API authentication key. Generate: `python3 -c 'import secrets; print(secrets.token_hex(32))'` |
| `DATABASE_URL` | — | PostgreSQL connection string (fallback for `SQLALCHEMY_DATABASE_URI` — see Section 8) |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker URL (fallback: `REDIS_URL`) |
| `ENABLE_SCHEDULER` | `false` | Enable APScheduler (set `true` on exactly ONE container) |
| `HEALTH_CHECK_SECRET` | — | Secret for detailed `/health?detailed=true` endpoint. When set, detailed health requires `?secret=` param |
| `METRICS_SECRET` | — | Secret for `/metrics` endpoint. Required when `ENABLE_METRICS=true` (no fallback) |
| `ENABLE_METRICS` | `false` | Enable `/metrics` endpoint. Must be `true` with `METRICS_SECRET` in production |

### Storage Variables

| Variable | Default | Description |
|---|---|---|
| `STORAGE_BACKEND` | `local` | Storage type: `local` or `s3` |
| `S3_BUCKET` | — | S3 bucket name (required for S3 backend) |
| `S3_REGION` | `us-east-1` | S3 region |
| `S3_ACCESS_KEY` | — | S3 access key |
| `S3_SECRET_KEY` | — | S3 secret key |
| `S3_ENDPOINT` | — | S3 endpoint URL (for S3-compatible services) |
| `S3_PUBLIC_URL` | — | Public CDN URL for S3 assets |

### Page View Buffer Variables

| Variable | Default | Description |
|---|---|---|
| `PAGE_VIEW_BUFFER_SIZE` | `0` | Buffer size (0 = disabled) |
| `PAGE_VIEW_FLUSH_INTERVAL` | `5` | Flush interval in seconds |

### Backup Encryption Variables

| Variable | Description |
|---|---|
| `BACKUP_ENCRYPTION_KEY` | AES-256-GCM encryption passphrase (min 12 chars) |

### Example Production Environment File

Create `/etc/blog/env` (chmod 600):

```bash
SECRET_KEY=your-64-char-hex-key-here
ADMIN_PASSWORD=your-strong-password
ADMIN_USERNAME=admin
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SESSION_COOKIE_SECURE=true
PROXY_COUNT=1
API_KEY=your-api-key-hex
PAGE_VIEW_BUFFER_SIZE=100
PAGE_VIEW_FLUSH_INTERVAL=10
BACKUP_ENCRYPTION_KEY=your-encryption-passphrase
ENABLE_SCHEDULER=true
HEALTH_CHECK_SECRET=your-health-check-secret
METRICS_SECRET=your-metrics-secret
```

Load with `EnvironmentFile=/etc/blog/env` in systemd unit.

---

## 4. Configuration

### config.toml

Edit `config.toml` in the project root. Key sections:

```toml
[app]
title = "DevLog"
description = "A place for thoughts on code"
posts_per_page = 10
session_lifetime_hours = 24

[server]
host = "0.0.0.0"
port = 5000
debug = false  # MUST be false in production

[site]
base_url = "https://blog.example.com"  # Public URL (no trailing slash)

[email]
smtp_host = "smtp.gmail.com"
smtp_port = 587
smtp_user = ""         # Override with SMTP_USER env var
smtp_password = ""     # Override with SMTP_PASSWORD env var
from_address = "blog@example.com"
smtp_timeout = 30

[newsletter]
send_time = "08:00"               # HH:MM (24h)
confirmation_expiry_hours = 1
max_retry_attempts = 5
```

The app validates `config.toml` on startup and raises `RuntimeError` for invalid values.

Every configuration field is documented by the standalone CLI:

```bash
devlog config explain app.session_lifetime_hours
devlog config check
```

Configuration is resolved from three layers, highest precedence first: environment variables, then `config.toml`, then the built-in defaults. The typed schema lives in `app/config/model.py` (one frozen dataclass per section); `app/config_legacy.py` re-exports the historical flat names for backwards compatibility.

---

## 5. Granian ASGI Server

Granian is a Rust-based ASGI server with superior performance to Python alternatives.

### Installation

```bash
pip install granian
```

### Running

```bash
granian --interface asgi --workers 4 --host 127.0.0.1 --port 5000 run:asgi_app
```

### Worker Tuning

| Workers | CPU Cores | RAM |
|---|---|---|
| 2 | 1-2 | 512 MB+ |
| 4 | 2-4 | 1 GB+ |
| 8 | 4+ | 2 GB+ |

Start with `--workers 4` and adjust based on traffic.

### Timeout Configuration

Always set `--timeout` to prevent hanging requests:

```bash
granian --interface asgi --workers 4 --timeout 60 run:asgi_app
```

**Recommended timeouts:**
- 30 seconds for normal page requests
- 60 seconds for file uploads and newsletter sends
- 120 seconds for backup/restore operations

### Newsletter Scheduler Limitation

The app uses in-process APScheduler with file locking (`fcntl`) to prevent duplicate newsletter sends. The scheduler is gated by the `ENABLE_SCHEDULER` environment variable (default: `false`). Set `ENABLE_SCHEDULER=true` on exactly ONE container to run scheduled jobs.

**Single-server (recommended):**
- Multiple workers work fine—only one wins the file lock
- Use `--workers 1` for absolute simplicity

**Multi-server (not recommended):**
- `fcntl` file locking doesn't work across machines
- Options:
  1. Single worker per server
  2. External scheduler (Celery, cron)
  3. Distributed lock (Redis, etcd)

### Graceful Shutdown

Granian handles graceful shutdown automatically—waiting for in-flight requests to complete.

---

## 6. Docker Deployment

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/install/) 2.0+

### Quick Start

```bash
# Clone the repository
git clone https://github.com/dbowm91/blog.git /opt/blog
cd /opt/blog

# Create .env file
cp .env.example .env
# Edit .env with your values (see Environment Variables below)

# Start with production profile
docker compose --profile production up -d --build

# View logs
docker compose --profile production logs -f
```

The Docker build uses a multi-stage Dockerfile:
1. **Node builder** — runs `npm ci` and `npm run build` to produce frontend assets
2. **Python builder** — installs Python dependencies into a venv
3. **Runtime** — copies the venv, application code, and built frontend assets into a slim image

Frontend assets are built automatically inside the container. No local Node.js installation is required for Docker deployments.

The app binds to `127.0.0.1:5000` (localhost only). It is not directly accessible from other machines. For public access, terminate TLS with a host-level reverse proxy (Caddy, nginx, Traefik) and proxy to `http://127.0.0.1:5000` — see [Section 9: Reverse Proxy Setup](#9-reverse-proxy-setup).

Admin at `http://localhost:5000/admin/login`.

### Compose Profiles

| Profile | Services | Use Case |
|---|---|---|
| `production` | blog, celery, redis | Core production stack (app on `127.0.0.1:5000`) |
| `reverse-proxy` | nginx | Optional nginx reverse proxy — requires certificate configuration |
| `backup` | backup | Standalone backup runner (`backup.py`), writing to `./backups` on the host |

```bash
# Core production stack (blog + celery + redis)
# TLS is NOT terminated — use an external reverse proxy for public access
docker compose --profile production up -d --build

# With included nginx reverse proxy (optional, requires certificate setup)
docker compose --profile production --profile reverse-proxy up -d --build

# Backup service
docker compose --profile backup run --rm backup

# Both production and backup
docker compose --profile production --profile backup up -d
```

The `backup` profile runs `backup.py`, which defaults to a database at
`instance/blog.db`. Pass the container's actual database explicitly when
overriding the entrypoint:

```bash
docker compose --profile backup run --rm backup --db /data/devlog.sqlite3
```

### Environment Variables in Docker

Copy `.env.example` and fill in your values:

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session signing key |
| `ADMIN_PASSWORD` | Yes | Admin login password |
| `ADMIN_USERNAME` | No | Admin username (default: `admin`) |
| `SMTP_HOST` | No | SMTP server. Unset disables the daily newsletter job |
| `SMTP_USER` | No | SMTP username |
| `SMTP_PASSWORD` | No | SMTP password |
| `API_KEY` | No | REST API authentication key |
| `STORAGE_BACKEND` | No | `local` or `s3` |
| `S3_*` | No | S3 configuration |
| `UPLOAD_FOLDER` | No | Media directory. Set to `/data/uploads` to keep uploads in the `blog_data` volume |
| `ENABLE_SCHEDULER` | No | Enable APScheduler (default: `false`, set on ONE container) |
| `HEALTH_CHECK_SECRET` | No | Secret for detailed `/health?detailed=true` endpoint |
| `METRICS_SECRET` | No | Secret for `/metrics` endpoint (required with `ENABLE_METRICS`) |
| `ENABLE_METRICS` | No | Enable `/metrics` endpoint (default: `false`) |

### Data Persistence

Docker Compose uses named volumes:

| Volume | Mount point | Contents |
|---|---|---|
| `blog_data` | `/data` | Runtime data directory (`DEVLOG_DATA_DIR`): the SQLite database and the filesystem-layout subdirectories |
| `blog_config` | `/etc/devlog` | `config.toml` and `.env` (`DEVLOG_CONFIG_FILE`, `DEVLOG_ENV_FILE`) |
| `blog_logs` | `/var/log/devlog` | Log directory (`DEVLOG_LOG_DIR`) |

These persist across container restarts and upgrades.

The database lives at `/data/devlog.sqlite3` in the container. The application
resolves that path from `DEVLOG_DATA_DIR`; outside Docker the same default
resolves to `data/devlog.sqlite3` relative to the working directory. Override
it with `DEVLOG_DATABASE_PATH`, `SQLALCHEMY_DATABASE_URI`, or `DATABASE_URL`.

Two paths sit outside the volumes by default and need attention:

- **Media.** The local storage backend writes to `app/static/uploads/`, which
  is inside the image, not the `blog_data` volume. Set
  `UPLOAD_FOLDER=/data/uploads` on the `blog` and `celery` services to keep
  uploads in the volume, or use the S3 backend.
- **Logs.** The Flask file log handler writes to `logs/blog.log` inside the
  application directory rather than to `DEVLOG_LOG_DIR`. If you rely on the
  `blog_logs` volume for log retention, also collect `/home/blog/logs/` (the
  container's working directory) or forward stdout to your log collector.

### Updating the Container

```bash
# Pull latest code
git pull

# Rebuild and restart (includes frontend asset build)
docker compose --profile production up -d --build

# View logs
docker compose --profile production logs -f
```

### Health Check

The `/health` endpoint is split into two modes:

**Basic (no auth required)** — fast, for Docker healthchecks and uptime monitoring:
```bash
curl -f http://localhost:5000/health
```

Response:
```json
{
  "status": "ok",
  "checks": {
    "database": "ok",
    "scheduler": "running"
  },
  "timestamp": "2026-04-29T12:00:00+00:00"
}
```

**Detailed (requires secret)** — all 8 checks with details:
```bash
curl -H "X-Health-Secret: YOUR_HEALTH_CHECK_SECRET" "http://localhost:5000/health?detailed=true"
```

The secret may also be sent as a `Bearer` token or as `?secret=`. If
`HEALTH_CHECK_SECRET` is unset and the app runs in production mode, detailed
health returns `403`; a wrong secret returns `401`.

Response includes: database, scheduler, search, disk_space, db_integrity, redis, celery, backup_freshness — with status and detail for each. Only critical checks (database, scheduler, search, disk_space, db_integrity) affect overall status.

The container health check uses the basic endpoint:
```bash
docker inspect --format='{{.State.Health.Status}}' blog
```

### Production Scaling Caveats

1. **SQLite is single-writer**: Only one process can write at a time. Do not scale the blog service horizontally without migrating to PostgreSQL first.
2. **APScheduler uses file locking**: The in-process scheduler (`fcntl` lock) only coordinates workers on a single machine. In multi-container deployments, each container runs its own scheduler. Use Celery Beat or an external cron if you need single-scheduled-execution across replicas. Set `ENABLE_SCHEDULER=true` on exactly ONE container.
3. **Async jobs need Redis/Celery**: The `celery` service handles newsletter delivery, webhook delivery, image variant generation, and backups. Without Redis, these jobs block the web process.
4. **Reverse proxy TLS is your responsibility**: The core production profile does not terminate TLS. For public internet deployment, terminate TLS with a host-level reverse proxy such as Caddy, nginx, or Traefik and proxy to `http://127.0.0.1:5000`. The repository also includes an optional nginx Compose profile (`--profile reverse-proxy`) for operators who want to manage nginx inside Compose, but it is not required for the supported single-host path and must be configured with valid certificates before public use.

### Production Docker Considerations

1. **Use a reverse proxy** (Caddy, nginx, Traefik) with HTTPS in front of Docker
2. **Set `config.toml [site] base_url`** to your public HTTPS URL
3. **Configure rate limiting** at the proxy level (see Section 10)
4. **Back up the named volumes** regularly

**Backup volumes:**
```bash
docker run --rm -v blog_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/blog_data_backup.tar.gz -C /data .
```

### Docker Network

The blog container publishes port 5000 bound to `127.0.0.1` (localhost only):

```yaml
services:
  blog:
    ports:
      - "127.0.0.1:5000:5000"  # Only bind to localhost
```

This is the default in `docker-compose.yml`. It prevents direct external access — only the reverse proxy (or local processes) can reach it.

### Environment File

Create `.env` from `.env.example`:

```bash
cp .env.example .env
# Edit with your values
```

Never commit `.env` to version control.

---

## 7. Backup and Restore

### Built-in Backup (Admin UI)

1. Go to `/admin/backup`
2. Click **Create Backup**
3. Optionally enable:
   - **Compression** — gzip reduces file size
   - **Encryption** — AES-256-GCM encryption (requires `BACKUP_ENCRYPTION_KEY`)
4. Backups appear in the list below

**Restore:**
1. Find your backup in the list
2. Click **Restore**
3. Confirm the action

**Warning:** Restoring overwrites all current data.

**Backup location:** `instance/backups/`

**Backup database path:** the **Create Backup** button resolves the database
from the configured URI (`data/devlog.sqlite3` by default). The scheduled
daily backup, the Celery backup task and `devlog backup create` still look
for `instance/blog.db` — see the note in
[Section 13: Maintenance](#13-maintenance).

### Built-in Backup (CLI)

Backups are created via the admin UI (`/admin/backup`), the standalone
`devlog backup create` command, or the scheduled daily job. The following
Flask CLI commands are available for maintenance:

```bash
flask rebuild-search          # Rebuild full-text search index
flask cleanup-orphaned-images # Remove orphaned uploaded images
flask create-admin            # Create a new admin user (prompts for username)
flask promote-admin USERNAME  # Promote a user to admin
flask check-integrity         # Verify database integrity
flask export-data out.json    # Export data to JSON
flask import-data backup.json # Import data from JSON
flask seed                    # Seed database with sample content
```

See [Section 17: Operator CLI](#17-operator-cli) for the equivalent
`devlog` commands.

### Manual SQLite Backup

The SQLite database lives at `data/devlog.sqlite3` by default (override with
`DEVLOG_DATABASE_PATH`, `SQLALCHEMY_DATABASE_URI`, or `DATABASE_URL`).

```bash
# Live backup (safe during writes with WAL mode)
sqlite3 /opt/blog/data/devlog.sqlite3 ".backup '/var/backups/blog/backup-$(date +%Y%m%d).db'"

# Portable SQL dump
sqlite3 /opt/blog/data/devlog.sqlite3 ".dump" | gzip > /var/backups/blog/backup-$(date +%Y%m%d).sql.gz
```

### Off-site Backup Sync

The `scripts/sync_backups.sh` script syncs backups to remote storage.

It reads two environment variables:

| Variable | Default | Description |
|---|---|---|
| `BACKUP_DIR` | `<project>/backups` | Local backup directory to sync |
| `RCLONE_REMOTE` | — | rclone remote, e.g. `s3-backup:my-blog-backups` |

The application writes its own backups to `instance/backups/`, so point
`BACKUP_DIR` at that directory unless you also copy the backups elsewhere.

**Install rclone:**
```bash
curl https://rclone.org/install.sh | sudo bash
```

**Configure rclone:**
```bash
rclone config  # Create remote (e.g., "s3-backup")
```

**Sync backups:**
```bash
# Sync to S3
RCLONE_REMOTE="s3-backup:my-blog-backups" ./scripts/sync_backups.sh

# Dry run
./scripts/sync_backups.sh --dry-run

# Verify
./scripts/sync_backups.sh --verify

# Cleanup local backups older than 14 days
./scripts/sync_backups.sh --cleanup 14
```

**Crontab for daily sync:**
```bash
0 4 * * * /opt/blog/scripts/sync_backups.sh --verify --cleanup 7 >> /opt/blog/logs/backup_sync.log 2>&1
```

### Backup Verification

The `app/backup_integrity.py` module verifies backup integrity:

```python
from app.backup_integrity import verify_backup_integrity, verify_backup_set

# Verify single backup
is_valid, message = verify_backup_integrity('/path/to/backup.db')

# Verify all backups in directory
results = verify_backup_set('/path/to/backups/')
```

**Verification checks:**
- File exists and is readable
- SQLite header is valid
- Required tables exist
- `PRAGMA integrity_check` passes

### Backup Retention

Recommended retention:
- Local: 7 days (with `--cleanup 7`)
- Off-site: 30 days

Adjust based on storage costs and compliance requirements.

### What to Back Up

Include in your backup strategy:

1. **Database:** `data/devlog.sqlite3` (plus its `-wal` / `-shm` sidecars) and `instance/backups/`
2. **Uploads:** `app/static/uploads/` (or the object store, when using S3)
3. **Configuration:** `config.toml` (not secrets)
4. **Environment variables** (document separately)

### Restore Procedures

**From built-in backup:**
1. Go to `/admin/backup`
2. Click **Restore** on the backup
3. Confirm

**From manual backup:**
```bash
# Stop the app
sudo systemctl stop blog

# Restore database
cp /var/backups/blog/backup-20260429.db /opt/blog/data/devlog.sqlite3

# Restart
sudo systemctl start blog
```

**From encrypted backup:**
```bash
# Decrypt first (input: encrypted file path, output: decrypted file path)
python -c "from app.services.backup import decrypt_backup_file; decrypt_backup_file('backup.db.gpg', 'backup.db')"

# Then restore via admin panel: POST /admin/backup/restore/backup.db
# Or copy backup.db to instance/backups/ and use the admin UI
```

**Cross-version restore:**
If restoring from a different version:
1. Restore to empty database
2. Import data: `flask import-data backup.json`

---

## 8. PostgreSQL Migration (Experimental)

> **Warning:** PostgreSQL support is **experimental** and not recommended for v1 production. SQLite WAL is the supported production database for single-server deployments. PostgreSQL is not fully tested in CI, and SQLite-specific features (FTS5 search, PRAGMA integrity checks) report as `unsupported` in health checks when running on PostgreSQL.
>
> This section is provided for operators evaluating future migration paths. Do not use PostgreSQL in production without thorough testing of search, health, backup/restore, and migration behavior.

For single-server deployments, SQLite with WAL mode is sufficient and recommended. PostgreSQL support is planned for a future release when backend-specific search, health checks, and backup/restore are fully implemented.

### Prerequisites

- **PostgreSQL 13+**
- **pg_trgm extension** (recommended for fuzzy matching)
- **psycopg2-binary** package

### Step 1: Install and Configure PostgreSQL

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql
CREATE DATABASE blog;
CREATE USER blog_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE blog TO blog_user;

# Grant schema permissions
\c blog blog_user
GRANT ALL ON SCHEMA public TO blog_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO blog_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO blog_user;

# Enable pg_trgm extension
\c blog
CREATE EXTENSION IF NOT EXISTS pg_trgm;

\q
```

### Step 2: Install Python Dependencies

```bash
pip install psycopg2-binary
```

### Step 3: Configure Database URL

```bash
export DATABASE_URL="postgresql://blog_user:your_secure_password@localhost/blog"
```

Or add to `config.toml`:
```toml
[database]
uri = "postgresql://blog_user:your_secure_password@localhost/blog"
```

### Step 4: Export SQLite Data

```bash
# Backup SQLite
cp data/devlog.sqlite3 data/devlog.sqlite3.sq3-backup

# Export to CSV
mkdir -p migration_temp
sqlite3 data/devlog.sqlite3 << 'EOF'
.mode csv
.headers on
.output migration_temp/users.csv
SELECT * FROM users;
.output migration_temp/posts.csv
SELECT * FROM posts;
-- (export all tables)
EOF
```

### Step 5: Run Migrations

```bash
export SECRET_KEY="your-secret"
export ADMIN_PASSWORD="your-admin"
export DATABASE_URL="postgresql://blog_user:your_secure_password@localhost/blog"
flask db upgrade
```

### Step 6: Import Data

Prefer the built-in export/import tooling over hand-written SQL, because it
carries the column mapping with it:

```bash
# Export from SQLite before the cut-over
flask export-data migration_temp/export.json

# Import into PostgreSQL after the cut-over
flask import-data migration_temp/export.json
```

The standalone CLI offers the same two operations (`devlog data export`,
`devlog data import`); `devlog data import --dry-run` validates a file without
writing to the database.

### Step 7: Configure Search

Replace FTS5 with PostgreSQL `tsvector` (see codebase for implementation details).

### Step 8: Verify Migration

Test:
- [ ] View posts on homepage
- [ ] Search functionality
- [ ] Admin login
- [ ] Create/edit a post
- [ ] Analytics
- [ ] Newsletter send
- [ ] Backup/restore

### PostgreSQL vs SQLite

| Feature | SQLite | PostgreSQL |
|---|---|---|
| Connection | File-based | TCP socket |
| Writes | Serialized | True concurrent |
| Full-text search | FTS5 | tsvector + GIN |
| Backup | Copy file | pg_dump |
| Connection pooling | Not needed | Use pgbouncer |

---

## 9. Reverse Proxy Setup

### nginx

```nginx
server {
    listen 443 ssl http2;
    server_name blog.example.com;

    ssl_certificate     /etc/letsencrypt/live/blog.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/blog.example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    # Serve static files directly
    location /static/ {
        alias /opt/blog/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Proxy to app
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    client_max_body_size 16M;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name blog.example.com;
    return 301 https://$host$request_uri;
}
```

### nginx with Rate Limiting

```nginx
http {
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=admin:10m rate=20r/m;

    server {
        location = /login {
            limit_req zone=login burst=5 nodelay;
            limit_req_status 429;
            proxy_pass http://127.0.0.1:5000;
        }

        location = /admin/login {
            limit_req zone=login burst=5 nodelay;
            limit_req_status 429;
            proxy_pass http://127.0.0.1:5000;
        }

        location /admin/ {
            limit_req zone=admin burst=5 nodelay;
            limit_req_status 429;
            proxy_pass http://127.0.0.1:5000;
        }
    }
}
```

### Caddy

Caddy has no built-in rate limiting. It needs a plugin (for example
`caddy-ratelimit`) or a WAF in front of it.

```caddy
blog.example.com {
    reverse_proxy 127.0.0.1:5000

    # Rate limiting
    @login path /login /admin/login
    handle @login {
        rate_limit 5 1m
        reverse_proxy 127.0.0.1:5000
    }
}
```

---

## 10. Rate Limiting

Rate limiting is configured at the reverse proxy level. The application
deliberately does **not** rate limit the login routes, so the proxy is the
only thing standing between a brute-force attempt and the login handler.
The application keeps the per-account lockout (`MAX_FAILED_ATTEMPTS`,
`LOCKOUT_DURATION_MINUTES`), which is a column on the user row and costs no
extra request.

### Recommended Limits

| Endpoint | Limit |
|---|---|
| `/login` | 5 req/min |
| `/admin/login` | 5 req/min |
| `/admin/*` | 20 req/min |
| `/api/*` | 20 req/min |
| Public routes | 100 req/min |

### Cloudflare WAF

For Cloudflare deployments, use custom rules:

1. **Login protection:** Rate limit `/login` and `/admin/login` at 5 req/min
2. **Admin protection:** Rate limit `/admin/*` at 20 req/min

### Troubleshooting Rate Limiting
- **429 Too Many Requests**: Check if your IP is hitting rate limits, especially for admin routes. Adjust limits in nginx/Caddy config if needed.
- **Rate limits not applying**: Verify `limit_req_zone` is correctly configured for the right keys (e.g., `$binary_remote_addr` for per-IP limits).
- **Cloudflare conflicts**: If using Cloudflare WAF rate limiting, ensure limits align with reverse proxy limits to avoid double-limiting.
- **Behind no proxy at all**: there is no application-layer limit on the login routes, so a bare deployment must put a proxy or WAF in front of it.

---

## 11. Systemd Service

Create `/etc/systemd/system/blog.service`:

```ini
[Unit]
Description=DevLog Blog Application
After=network.target

[Service]
Type=simple
User=blog
Group=blog
WorkingDirectory=/opt/blog
EnvironmentFile=/etc/blog/env
ExecStart=/opt/blog/venv/bin/granian --interface asgi --workers 4 --timeout 60 run:asgi_app
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/blog/data /opt/blog/instance /opt/blog/logs
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable blog
sudo systemctl start blog
sudo journalctl -u blog -f
```

---

## 12. Monitoring

### Health Check

```bash
# Basic health (fast, no auth — use for uptime monitoring)
curl http://127.0.0.1:5000/health

# Detailed health (requires secret when HEALTH_CHECK_SECRET is set)
curl -H "X-Health-Secret: YOUR_HEALTH_CHECK_SECRET" "http://127.0.0.1:5000/health?detailed=true"
```

Basic response:
```json
{
  "status": "ok",
  "checks": {
    "database": "ok",
    "scheduler": "running"
  },
  "timestamp": "2026-04-29T12:00:00+00:00"
}
```

Detailed response includes all checks: database, scheduler, search, disk_space, db_integrity, redis, celery, backup_freshness.

### Metrics

```bash
# Requires METRICS_SECRET when ENABLE_METRICS=true
curl -H "X-Metrics-Secret: YOUR_METRICS_SECRET" http://127.0.0.1:5000/metrics
```

When `ENABLE_METRICS=false` (default), `/metrics` returns 404. Set `ENABLE_METRICS=true` and `METRICS_SECRET` to enable.

### Application Logs

Logs written to `logs/blog.log` (rotated at 10 MB, 10 backups):

```bash
tail -f /opt/blog/logs/blog.log
```

Or via journalctl:
```bash
journalctl -u blog -f
```

### Uptime Monitoring

Use `/health` endpoint with:
- [Uptime Robot](https://uptimerobot.com/) — use the basic `/health` endpoint (no auth)
- [Healthchecks.io](https://healthchecks.io/) — use the basic `/health` endpoint
- [Pingdom](https://pingdom.com/) — use the basic `/health` endpoint

---

## 13. Maintenance

### Cron Jobs

```bash
# Weekly integrity check (Sunday 2 AM)
0 2 * * 0 cd /opt/blog && flask check-integrity >> logs/integrity.log 2>&1

# Weekly search rebuild (Sunday 3 AM)
0 3 * * 0 cd /opt/blog && flask rebuild-search >> logs/search.log 2>&1

# Monthly cleanup (1st of month 4 AM)
0 4 1 * * cd /opt/blog && flask cleanup-orphaned-images >> logs/cleanup.log 2>&1
```

### Newsletter Scheduler

The scheduler runs in-process via APScheduler — no external cron needed. It is gated by the `ENABLE_SCHEDULER` environment variable (default: `false`); set it on exactly ONE container in multi-container deployments.

When enabled it runs four jobs:

| Job | Schedule | Notes |
|---|---|---|
| Scheduled post publishing | Every 5 minutes | Publishes posts whose `scheduled_publish_at` has passed |
| Subscriber cleanup | Every 5 minutes | Deletes unconfirmed subscribers past their confirmation window |
| Daily newsletter | `08:00` (`[newsletter] send_time`) | Only scheduled when `SMTP_HOST` is set |
| Daily backup | `02:00` | Writes to `instance/backups/` — see the note below |

Each job takes a file lock first, so multiple workers on one host do not
duplicate work.

> **Known limitation.** The scheduled daily backup, the Celery
> `run_backup_task` and `devlog backup create` all look for the database at
> `instance/blog.db`. With the default `data/devlog.sqlite3` path they cannot
> find it, and the scheduled job logs
> `Database file not found at .../instance/blog.db, skipping backup`. Only the
> **Create Backup** button in `/admin/backup` resolves the database from the
> configured URI. Until the backup paths are aligned with
> `app/config/loader.py`, either keep the database at `instance/blog.db` or
> create backups from the admin UI.

### Background Jobs: Celery vs APScheduler

DevLog uses two complementary systems for background work:

| System | What it does | Where it runs |
|--------|-------------|---------------|
| **APScheduler** | Triggers scheduled tasks (newsletter sends, post publishing, backups, subscriber cleanup) | In-process, gated by `ENABLE_SCHEDULER=true` on one container |
| **Celery** | Executes async jobs (newsletter delivery, webhook delivery, image variants, backup creation) | Dedicated `celery` service in the production compose profile |

**How they interact:** APScheduler enqueues jobs into Celery when available. Without Celery, newsletter sends block the web process. The production compose profile includes both — APScheduler on the blog container, Celery as a separate worker.

---

## 14. Security Checklist

- [ ] `SECRET_KEY` is random 64-character hex string
- [ ] `ADMIN_PASSWORD` is strong (12+ chars, mixed case, numbers, symbols)
- [ ] `config.toml` is NOT tracked in git (only `config.toml.example` is committed)
- [ ] `config.toml [server] debug = false`
- [ ] `config.toml [site] base_url` uses `https://`
- [ ] HTTPS enforced at reverse proxy (redirect from HTTP, HSTS header)
- [ ] `SESSION_COOKIE_SECURE = True` (must be explicitly set in production)
- [ ] `PROXY_COUNT` set correctly for proxy setup (affects rate limiting and session IP binding via `ProxyFix`)
- [ ] `HEALTH_CHECK_SECRET` set to gate detailed health endpoint
- [ ] `METRICS_SECRET` set and `ENABLE_METRICS=true` to gate `/metrics` endpoint
- [ ] Static files served by nginx, not proxied
- [ ] Rate limiting configured for `/admin/login` (5 req/min)
- [ ] `data/devlog.sqlite3` not in a web-accessible directory
- [ ] `app/static/uploads/` permissions restricted
- [ ] SMTP credentials via environment variables
- [ ] Regular backups configured

---

## 15. Dependencies

| Package | Purpose |
|---|---|
| Flask | Web framework |
| SQLAlchemy | ORM |
| Flask-Login | Session management |
| Flask-Migrate | Database migrations |
| Werkzeug | Password hashing, WSGI/ASGI |
| asgiref | ASGI adapter |
| markdown | Markdown rendering |
| nh3 | HTML sanitization |
| APScheduler | Newsletter scheduling |
| granian | ASGI server |

For Python version requirements, see `pyproject.toml`.

---

## 16. Vite for Admins

Vite is used for frontend asset bundling with content hashing for cache busting.

### How Vite Works
- **Development**: `npm run dev` starts Vite dev server with HMR (Hot Module Replacement)
- **Production**: `npm run build` generates content-hashed assets in `app/static/dist/`
- Flask's `vite_asset()` helper maps unhashed paths to hashed filenames via `manifest.json`

### Docker Builds

Docker builds frontend assets automatically via a multi-stage Dockerfile. The Node builder stage runs `npm ci` and `npm run build`, and the runtime image includes the compiled assets. No manual build step is needed for Docker deployments.

### Manual Builds (Non-Docker)

For non-Docker production deployments, build assets before starting the server:

```bash
npm ci
npm run build
```

Verify the build produced the manifest:

```bash
test -f app/static/dist/.vite/manifest.json && echo "Build OK"
```

### Admin Tasks
- **Rebuild assets**: After changing JS/CSS files, run `npm run build` and restart the app
- **Check manifest**: Verify `app/static/dist/.vite/manifest.json` exists after build
- **Troubleshooting**: If assets return 404, ensure `vite_asset()` is used in templates instead of `url_for('static', ...)`
- **Content hashing**: Hashed filenames (e.g., `main-BVtPp-ke.js`) allow aggressive caching (`Cache-Control: max-age=31536000, immutable`)

---

## 17. Operator CLI

`devlog` is the standalone operator CLI. It is installed with the package
(`pip install -e .` in a checkout, or from a wheel) and is the primary
interface for inspecting and repairing a deployment. The Flask CLI commands
(`flask ...`) remain available as compatibility wrappers over the same
underlying services, and still cover a few things `devlog` does not expose
(`flask seed`, `flask shell`, `flask create-admin`).

```bash
devlog --help
devlog --config /etc/devlog/config.toml --env-file /etc/devlog/.env <command>
```

Global flags: `--config`, `--env-file`, `--json`, `--quiet`, `--verbose`,
`--no-color`.

### Command Groups

| Group | Commands | Purpose |
|---|---|---|
| `config` | `check`, `show`, `explain`, `paths`, `init`, `migrate` | Inspect, validate and scaffold `config.toml` |
| `admin` | `create`, `promote`, `reset-password`, `list` | Manage admin accounts |
| `db` | `check`, `rebuild-search`, `status`, `migrate` | Database integrity, FTS rebuild, migrations |
| `themes` | `list`, `validate`, `inspect`, `refresh`, `paths`, `accessibility` | Manage the Halloy theme catalogue |
| `backup` | `create`, `verify`, `inspect` | Create and verify backups |
| `data` | `export`, `import` | Export/import posts, subscribers, tags and pages |
| `media` | `scan`, `cleanup` | Find and remove orphaned uploads |
| `onboard` | `detect`, `plan`, `run`, `resume` | First-run and reconfiguration onboarding |
| `paths` | `status`, `discover-legacy`, `migrate`, `check` | Inspect and migrate the filesystem layout |
| `deploy` | `render`, `install`, `check` | Render and install systemd/compose/proxy units |
| `doctor` | `doctor` | Run 76 diagnostic checks across 20 categories |
| lifecycle | `start`, `stop`, `restart`, `status`, `logs` | Manage the service |

### Common Operations

```bash
# Validate the effective configuration
devlog config check --production

# Explain a single field, with its source
devlog config explain app.session_lifetime_hours

# Show resolved values and where each came from
devlog config show --effective

# Run every diagnostic check
devlog doctor

# Run one check, or one category, and apply safe fixes
devlog doctor --check db.sqlite_integrity
devlog doctor --category security
devlog doctor --fix-safe

# Create, verify and inspect backups
devlog backup verify instance/backups/blog_20260429.db
devlog backup inspect instance/backups/blog_20260429.db

# Inspect the filesystem layout
devlog paths status
devlog paths check

# Theme catalogue
devlog themes list --warnings
devlog themes validate "themes/Catppuccin Mocha.toml"
devlog themes accessibility --strict
```

`devlog doctor --list-checks` prints the full check registry. Checks are
grouped into 20 categories (`installation`, `configuration`, `secrets`,
`filesystem`, `database`, `search`, `assets`, `themes`, `storage`, `email`,
`redis`, `celery`, `scheduler`, `backup`, `deployment`, `service`, `proxy`,
`health`, `capacity`, `security`).

---

## 18. GitHub Repository Settings

These settings must be configured via the GitHub web UI (not files):

### Repository Topics
Add topics in **Settings > General > Topics**: `flask`, `blog`, `cms`, `sqlite`, `newsletter`, `python`

### Security
- Enable **Security advisories** (Settings > Security)
- Add `SECURITY.md` for vulnerability reporting (if not already present)

### Branch Protection Rules
For the `main` branch, configure in **Settings > Branches > Branch protection rules**:
- Require pull request reviews before merging
- Require status checks to pass (CI workflows)
- Require branches to be up to date before merging
- Optionally require signed commits

### About Section
Set in **Settings > General > About**:
- Description: "Flask-based blog CMS with newsletter, FTS5 search, and 2FA"
- Website: Your deployment URL
- Topics: `flask`, `blog`, `cms`, `python`
