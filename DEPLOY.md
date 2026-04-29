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
- [PostgreSQL Migration](#8-postgresql-migration)
- [Reverse Proxy Setup](#9-reverse-proxy-setup)
- [Rate Limiting](#10-rate-limiting)
- [Systemd Service](#11-systemd-service)
- [Monitoring](#12-monitoring)
- [Maintenance](#13-maintenance)
- [Security Checklist](#14-security-checklist)
- [Dependencies](#15-dependencies)

---

## 1. Prerequisites

- Python 3.14+
- pip
- SQLite 3.35+ (for `PRAGMA journal_mode=WAL` and FTS5 support)
- A reverse proxy (nginx, Caddy recommended)
- A domain with SSL certificate

---

## 2. Quick Start

```bash
# Clone and enter the project
git clone <repo-url> /opt/blog
cd /opt/blog

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create config.toml (edit as needed)
cp config.toml config.toml

# Set required environment variables
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export ADMIN_PASSWORD="your-strong-password-here"

# Initialize the database
export FLASK_APP=run:app
flask db upgrade

# Run the development server (NOT for production)
python run.py
```

The app listens on `0.0.0.0:5000` by default.

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
| `SMTP_USER` | — | SMTP auth username for newsletter/email |
| `SMTP_PASSWORD` | — | SMTP auth password |
| `SESSION_COOKIE_SECURE` | `true` | Require HTTPS for session cookies. Set `false` only for local HTTP development |
| `PROXY_COUNT` | `1` | Number of reverse proxies in front of the app. Set `0` to disable `ProxyFix` |
| `API_KEY` | — | REST API authentication key. Generate: `python3 -c 'import secrets; print(secrets.token_hex(32))'` |
| `DATABASE_URL` | — | PostgreSQL connection string (overrides SQLite) |

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
| `BACKUP_ENCRYPTION_KEY` | GPG symmetric encryption passphrase (min 8 chars) |
| `BACKUP_GPG_CIPHER` | Cipher algorithm (default: `AES256`) |

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
confirmation_expiry_hours = 48
max_retry_attempts = 5
```

The app validates `config.toml` on startup and raises `RuntimeError` for invalid values.

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

The app uses in-process APScheduler with file locking (`fcntl`) to prevent duplicate newsletter sends.

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
git clone <repo-url> /opt/blog
cd /opt/blog

# Create .env file
cat > .env << EOF
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
ADMIN_PASSWORD=your-strong-password-here
ADMIN_USERNAME=admin
EOF

# Start the container
docker-compose up -d

# View logs
docker-compose logs -f
```

The blog will be available at `http://localhost:5000`. Admin at `http://localhost:5000/admin/login`.

### Environment Variables in Docker

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session signing key |
| `ADMIN_PASSWORD` | Yes | Admin login password |
| `ADMIN_USERNAME` | No | Admin username (default: `admin`) |
| `SMTP_USER` | No | SMTP username |
| `SMTP_PASSWORD` | No | SMTP password |
| `STORAGE_BACKEND` | No | `local` or `s3` |
| `S3_*` | No | S3 configuration |

### Data Persistence

Docker Compose uses named volumes:

| Volume | Contents |
|---|---|
| `blog_data` | SQLite database (`instance/`) |
| `blog_logs` | Application logs (`logs/`) |
| `blog_uploads` | Uploaded media (`app/static/uploads/`) |

These persist across container restarts and upgrades.

### Updating the Container

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build

# View logs
docker-compose logs -f
```

### Health Check

The container includes a health check verifying the app responds:

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' blog

# Manual health check
curl -f http://localhost:5000/health
```

### Resource Limits

Add limits to `docker-compose.yml` if needed:

```yaml
services:
  blog:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

### Production Docker Considerations

1. **Use a reverse proxy** (nginx, Caddy) with HTTPS in front of Docker
2. **Set `config.toml [site] base_url`** to your public HTTPS URL
3. **Configure rate limiting** at the proxy level (see Section 10)
4. **Back up the named volumes** regularly

**Backup volumes:**
```bash
docker run --rm -v blog_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/blog_data_backup.tar.gz -C /data .
```

### Docker Network

The blog container exposes port 5000. For production:

```yaml
services:
  blog:
    ports:
      - "127.0.0.1:5000:5000"  # Only bind to localhost
```

This prevents direct external access—only the reverse proxy can reach it.

### Environment File

Create `.env` from environment variables:

```bash
cat > .env << 'EOF'
SECRET_KEY=your-secret-key
ADMIN_PASSWORD=your-password
ADMIN_USERNAME=admin
SMTP_USER=
SMTP_PASSWORD=
EOF
```

Never commit `.env` to version control.

---

## 7. Backup and Restore

### Built-in Backup (Admin UI)

1. Go to `/admin/backup`
2. Click **Create Backup**
3. Optionally enable:
   - **Compression** — gzip reduces file size
   - **Encryption** — GPG symmetric encryption (requires `BACKUP_ENCRYPTION_KEY`)
4. Backups appear in the list below

**Restore:**
1. Find your backup in the list
2. Click **Restore**
3. Confirm the action

**Warning:** Restoring overwrites all current data.

**Backup location:** `instance/backups/`

### Built-in Backup (CLI)

```bash
# Create backup
flask backup --create

# Create compressed backup
flask backup --create --compress

# Create encrypted backup
flask backup --create --encrypt

# Create compressed and encrypted
flask backup --create --compress --encrypt

# List backups
flask backup --list

# Restore from backup
flask backup --restore instance/backups/backup-2026-04-29.db
```

### Manual SQLite Backup

```bash
# Live backup (safe during writes with WAL mode)
sqlite3 /opt/blog/instance/blog.db ".backup '/var/backups/blog/backup-$(date +%Y%m%d).db'"

# Portable SQL dump
sqlite3 /opt/blog/instance/blog.db ".dump" | gzip > /var/backups/blog/backup-$(date +%Y%m%d).sql.gz
```

### Off-site Backup Sync

The `scripts/sync_backups.sh` script syncs backups to remote storage.

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

1. **Database:** `instance/blog.db` and `instance/backups/`
2. **Uploads:** `app/static/uploads/`
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
cp /var/backups/blog/backup-20260429.db /opt/blog/instance/blog.db

# Restart
sudo systemctl start blog
```

**From encrypted backup:**
```bash
# Decrypt first
python backup.py --decrypt backup.db.gpg

# Then restore
flask backup --restore backup.db
```

**Cross-version restore:**
If restoring from a different version:
1. Restore to empty database
2. Import data: `flask import-data backup.json`

---

## 8. PostgreSQL Migration

For single-server deployments, SQLite with WAL mode is sufficient. For higher traffic or multi-server deployments, migrate to PostgreSQL.

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
url = "postgresql://blog_user:your_secure_password@localhost/blog"
```

### Step 4: Export SQLite Data

```bash
# Backup SQLite
cp instance/blog.db instance/blog.db.sq3-backup

# Export to CSV
mkdir -p migration_temp
sqlite3 instance/blog.db << 'EOF'
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

Use the SQL script in the migration_temp directory (see full script in the codebase comments).

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

```caddy
blog.example.com {
    reverse_proxy 127.0.0.1:5000

    # Rate limiting
    @login path /admin/login
    handle @login {
        rate_limit 5 1m
        reverse_proxy 127.0.0.1:5000
    }
}
```

---

## 10. Rate Limiting

Rate limiting is configured at the reverse proxy level.

### Recommended Limits

| Endpoint | Limit |
|---|---|
| `/admin/login` | 5 req/min |
| `/admin/*` | 20 req/min |
| `/api/*` | 20 req/min |
| Public routes | 100 req/min |

### Cloudflare WAF

For Cloudflare deployments, use custom rules:

1. **Login protection:** Rate limit `/admin/login` at 5 req/min
2. **Admin protection:** Rate limit `/admin/*` at 20 req/min

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
ReadWritePaths=/opt/blog/instance /opt/blog/logs
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
curl http://127.0.0.1:5000/health
```

Response:
```json
{
  "status": "ok",
  "database": "connected",
  "scheduler": "running",
  "timestamp": "2026-04-29T12:00:00+00:00"
}
```

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
- [Uptime Robot](https://uptimerobot.com/)
- [Healthchecks.io](https://healthchecks.io/)
- [Pingdom](https://pingdom.com/)

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

The newsletter scheduler runs in-process via APScheduler—no external cron needed. It wakes every 5 minutes to check for scheduled posts and newsletters.

---

## 14. Security Checklist

- [ ] `SECRET_KEY` is random 64-character hex string
- [ ] `ADMIN_PASSWORD` is strong (12+ chars, mixed case, numbers, symbols)
- [ ] `config.toml [server] debug = false`
- [ ] `config.toml [site] base_url` uses `https://`
- [ ] HTTPS enforced at reverse proxy (redirect from HTTP, HSTS header)
- [ ] `SESSION_COOKIE_SECURE = True` (automatic when `debug = false`)
- [ ] `PROXY_COUNT` set correctly for proxy setup
- [ ] Static files served by nginx, not proxied
- [ ] Rate limiting configured for `/admin/login` (5 req/min)
- [ ] `instance/blog.db` not in web-accessible directory
- [ ] `static/uploads/` permissions restricted
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

For Python 3.14 compatibility, see `requirements.txt`.
