# Deployment Guide

## 1. Prerequisites

- Python 3.14+
- pip
- SQLite 3.35+ (for `PRAGMA journal_mode=WAL` and FTS5 support)
- A reverse proxy (nginx recommended)
- A domain with SSL certificate

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

# Create config.toml from example (if provided) or edit config.toml directly
cp config.toml config.toml  # edit as needed

# Set required environment variables
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export ADMIN_PASSWORD="your-strong-password-here"

# Initialize the database
export FLASK_APP=run:app
flask db upgrade

# Run the development server (not for production)
python run.py
```

The app listens on `0.0.0.0:5000` by default.

## 3. Configuration

### Environment Variables

These are **required** at runtime. The app will not start without them.

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session signing key. Generate with `python3 -c 'import secrets; print(secrets.token_hex(32))'` |
| `ADMIN_PASSWORD` | Yes | Password for the admin user |
| `ADMIN_USERNAME` | No | Admin username (default: `admin`) |
| `SMTP_USER` | No | SMTP auth username for newsletter/email |
| `SMTP_PASSWORD` | No | SMTP auth password |
| `SESSION_COOKIE_SECURE` | No | Require HTTPS for session cookies (default: `true`). Set to `false` only for local HTTP development |
| `PROXY_COUNT` | No | Number of reverse proxies in front of the app (default: `1`). Set to `0` to disable `ProxyFix` |

### config.toml

Edit `config.toml` in the project root. Key sections:

```toml
[app]
title = "DevLog"
description = "A place for thoughts on code, systems, and the craft of building software."
posts_per_page = 10
session_lifetime_hours = 24       # Admin session inactivity timeout

[server]
host = "0.0.0.0"
port = 5000
debug = false                     # MUST be false in production

[site]
base_url = "https://blog.example.com"  # Your public URL (no trailing slash)

[email]
smtp_host = "smtp.gmail.com"
smtp_port = 587
smtp_user = ""                    # Override with SMTP_USER env var
smtp_password = ""                # Override with SMTP_PASSWORD env var
from_address = "blog@example.com"
smtp_timeout = 30                 # SMTP connection timeout in seconds

[newsletter]
send_time = "08:00"               # HH:MM (24h) for scheduled newsletter
confirmation_expiry_hours = 1
max_retry_attempts = 5
```

The app validates `config.toml` on startup and raises `RuntimeError` for invalid values.

## 4. Production Deployment with Granian

Granian is an ASGI server that serves the `asgi_app` object exported from `run.py`.

```bash
# Install granian
pip install granian

# Run with granian (4 workers, bind to localhost:5000)
granian --interface asgi --workers 4 --host 127.0.0.1 --port 5000 run:asgi_app
```

Worker tuning recommendations:

| Workers | CPU Cores | RAM |
|---|---|---|
| 2 | 1-2 | 512 MB+ |
| 4 | 2-4 | 1 GB+ |
| 8 | 4+ | 2 GB+ |

Use `--workers 4` as a starting point. SQLite WAL mode allows concurrent reads; writes are serialized with a 5-second busy timeout.

**Newsletter Scheduler Limitation:** The app uses in-process APScheduler with file locking (`fcntl`) to prevent duplicate newsletter sends. This works on a single machine with multiple workers—only one worker will win the lock and send the newsletter. However, this does **not** protect against duplicate sends **across multiple machines** (e.g., multiple container instances). For multi-machine deployments, either:

1. Run a single worker only (no multi-worker setup), or
2. Use an external scheduler (cron, Celery Beat) instead of APScheduler, or
3. Use a distributed lock mechanism (Redis, etcd) instead of `fcntl`

For most single-server deployments, running with `--workers 1` for the newsletter scheduler is the simplest and safest approach.

### Database Scaling

The default configuration uses **SQLite with WAL mode**, which is sufficient for single-server deployments with up to ~10,000 posts and moderate traffic. SQLite advantages include simple backup (single file), no separate server process, and excellent performance for read-heavy workloads.

For higher traffic or multi-server deployments, migrate to **PostgreSQL**:

1. **Install PostgreSQL** and create a database:
   ```bash
   sudo apt install postgresql
   sudo -u postgres psql
   CREATE DATABASE blog;
   CREATE USER blog_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE blog TO blog_user;
   ```

2. **Update `config.toml`** to use PostgreSQL:
   ```toml
   [database]
   url = "postgresql://blog_user:your_password@localhost/blog"
   ```

3. **Install required packages**:
   ```bash
   pip install psycopg2-binary
   ```

4. **Use Flask-Migrate** to transfer data:
   ```bash
   # Export data from SQLite
   sqlite3 instance/blog.db ".dump" > backup.sql

   # Import to PostgreSQL (adjust types as needed)
   psql -U blog_user -d blog -f backup.sql
   ```

5. **Restart the application** to use the new database.

**Note:** The codebase is developed and tested with SQLite. PostgreSQL compatibility is available via SQLAlchemy's database-agnostic patterns, but some edge cases (especially around FTS5) may behave differently. The FTS5 full-text search is SQLite-specific and has no direct PostgreSQL equivalent—consider using PostgreSQL's `tsvector` or a dedicated search service like Elasticsearch if you migrate.

## 5. Reverse Proxy Setup (nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name blog.example.com;

    ssl_certificate     /etc/letsencrypt/live/blog.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/blog.example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;

    # Rate limit zone for login
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    # Serve static files directly
    location /static/ {
        alias /opt/blog/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Rate-limit the login endpoint
    location = /admin/login {
        limit_req zone=login burst=3 nodelay;
        limit_req_status 429;

        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
    }

    # Everything else proxied to the app
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }

    # Upload size limit (matches app MAX_CONTENT_LENGTH of 16 MB)
    client_max_body_size 16M;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name blog.example.com;
    return 301 https://$host$request_uri;
}
```

The app sets `SESSION_COOKIE_SECURE = True` when `debug = False`, so HTTPS is mandatory in production.

The `ProxyFix` middleware (controlled by `PROXY_COUNT` env var, default 1) trusts `X-Forwarded-For`, `X-Forwarded-Proto`, and `X-Forwarded-Host` headers. Set `PROXY_COUNT=0` if running without a reverse proxy.

## 5b. Request Timeouts

This codebase intentionally **does not include application-level request timeout middleware**. Request timeouts should be configured at the reverse proxy or WSGI/ASGI server level:

### Granian (ASGI)
```bash
granian --workers 4 --timeout 60 run:asgi_app
```

### Gunicorn (WSGI)
```bash
gunicorn --workers 4 --timeout 60 --graceful-timeout 30 run:app
```

### nginx
The nginx config already includes `proxy_read_timeout 60s` and `proxy_connect_timeout 10s`. Adjust these to match your server timeout settings.

### Recommended thresholds
- **30 seconds** for normal page requests
- **60 seconds** for file uploads and newsletter sends
- **120 seconds** for backup/restore operations

### Response Compression

Enable gzip compression in nginx to reduce bandwidth and improve response times:

```nginx
http {
    # Enable gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/rss+xml application/atom+xml image/svg+xml;
    gzip_min_length 256;

    # Bypass compression for already-compressed formats
    gzip_disable "msie6";
}
```

**Note:** The app itself does not perform compression—delegating to the reverse proxy is more efficient. Static assets (`/static/`) should already be cached and served by nginx with `expires 1y`.

## 6. Rate Limiting

This codebase intentionally **does not include application-level rate limiting**. Rate limiting is expected to be handled by the reverse proxy, WAF, or CDN sitting in front of this application.

### Recommended nginx Configuration

Add rate limiting zones and apply them to specific endpoints:

```nginx
http {
    # Rate limiting zones (10MB stores up to ~160k IPs)
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=admin:10m rate=20r/m;
    limit_req_zone $binary_remote_addr zone=public:10m rate=100r/m;

    server {
        # ... existing SSL config ...

        # Rate limit login endpoint (most sensitive)
        location = /admin/login {
            limit_req zone=login burst=5 nodelay;
            limit_req_status 429;

            proxy_pass http://127.0.0.1:5000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }

        # Rate limit all other admin routes
        location /admin/ {
            limit_req zone=admin burst=5 nodelay;
            limit_req_status 429;

            proxy_pass http://127.0.0.1:5000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }

        # Rate limit public routes (less restrictive)
        location / {
            limit_req zone=public burst=20 nodelay;
            limit_req_status 429;

            proxy_pass http://127.0.0.1:5000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }
    }
}
```

### Caddy Configuration

```caddy
# Global rate limiting
{
    rate_limit {
        zone login {
            key {remote_host}
            events 5
            window 1m
        }
        zone admin {
            key {remote_host}
            events 20
            window 1m
        }
        zone public {
            key {remote_host}
            events 100
            window 1m
        }
    }
}

blog.example.com {
    reverse_proxy 127.0.0.1:5000

    # Login endpoint - most restrictive
    @login_path path /admin/login
    route @login_path {
        rate_limit login
    }

    # Admin routes
    @admin_path path /admin/*
    route @admin_path {
        rate_limit admin
    }

    # Public routes
    route {
        rate_limit public
    }
}
```

### Cloudflare WAF Configuration

For Cloudflare, use a WAF custom rule to rate limit the login endpoint:

1. Go to your Cloudflare dashboard → Security → WAF → Custom Rules
2. Create a new rule with these settings:
   - **Rule Name:** Rate Limit Login
   - **Field:** URI Path
   - **Operator:** equals
   - **Value:** `/admin/login`
   - **Then:** Choose rate limiting action (e.g., Managed Challenge)
   - **Rate:** 5 requests per minute

3. For broader admin protection, create another rule:
   - **Rule Name:** Rate Limit Admin
   - **Field:** URI Path
   - **Operator:** starts with
   - **Value:** `/admin/`
   - **Then:** Managed Challenge or Rate Limit
   - **Rate:** 20 requests per minute

4. For public routes:
   - **Rule Name:** Rate Limit Public
   - **Field:** (none - applies to all requests)
   - **Then:** Rate Limit
   - **Rate:** 100 requests per minute

### Why Application-Level Rate Limiting Is Not Included

- **Already handled upstream:** A properly configured reverse proxy (nginx, Caddy, traefik) or cloud provider (Cloudflare, AWS WAF) provides mature, tested rate limiting
- **Simplicity:** Application-level rate limiting adds complexity and overhead (in-memory state not shared across workers, memory growth concerns)
- **Single responsibility:** The app focuses on its core function (blogging); infrastructure concerns like rate limiting belong at the infrastructure layer

### Monitoring Rate Limits

When rate limiting is configured at the proxy level, monitor these metrics:

- **429 responses:** Count of HTTP 429 responses indicates users are hitting limits
- **Rejected requests:** Most proxies log rejected requests (nginx logs show `limiting requests`)
- **Abnormal patterns:** Sudden spikes in 429 responses may indicate abuse attacks



## 7. Systemd Service

Create `/etc/systemd/system/blog.service`:

```ini
[Unit]
Description=Blog Application
After=network.target

[Service]
Type=simple
User=blog
Group=blog
WorkingDirectory=/opt/blog
Environment="SECRET_KEY=your-secret-key-here"
Environment="ADMIN_PASSWORD=your-admin-password-here"
ExecStart=/opt/blog/venv/bin/granian --interface asgi --workers 4 --host 127.0.0.1 --port 5000 run:asgi_app
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/blog/instance /opt/blog/logs
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable blog
sudo systemctl start blog
sudo journalctl -u blog -f   # Follow logs
```

For better security, store the environment variables in a separate file:

```bash
# /etc/systemd/system/blog.env (chmod 600, owned by root)
SECRET_KEY=...
ADMIN_PASSWORD=...
```

Then use `EnvironmentFile=/etc/systemd/system/blog.env` in the unit file instead of individual `Environment=` lines.

## 7. Docker Deployment

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

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session signing key |
| `ADMIN_PASSWORD` | Yes | Admin login password |
| `ADMIN_USERNAME` | No | Admin username (default: `admin`) |
| `SMTP_USER` | No | SMTP username for newsletter |
| `SMTP_PASSWORD` | No | SMTP password |

### Data Persistence

Docker uses named volumes to persist data:

- `blog_data` — SQLite database (`instance/`)
- `blog_logs` — Application logs (`logs/`)
- `blog_uploads` — Uploaded media (`app/static/uploads/`)

These volumes persist across container restarts and upgrades.

### Updating

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build

# View logs
docker-compose logs -f
```

### Health Check

The container includes a health check that verifies the app responds:

```bash
# Check health
docker inspect --format='{{.State.Health.Status}}' blog

# Manual health check
curl -f http://localhost:5000/health
```

### Production Considerations

For production deployments:

1. **Use a reverse proxy** (nginx, Caddy) with HTTPS in front of the Docker container
2. **Set `config.toml [site] base_url`** to your public HTTPS URL
3. **Configure rate limiting** at the proxy level (see Section 5)
4. **Back up the named volumes** regularly:
   ```bash
   docker run --rm -v blog_data:/data -v $(pwd):/backup alpine \
     tar czf /backup/blog_data_backup.tar.gz -C /data .
   ```
5. **Monitor container logs**: `docker-compose logs -f`

### Resource Limits

Add resource limits to `docker-compose.yml` if needed:

```yaml
services:
  blog:
    # ... existing config ...
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

## 8. Backup

### Built-in Backup

The admin panel provides backup/restore at `/admin/backup`:

- Creates timestamped copies of `instance/blog.db` in `instance/backups/`
- Optional gzip compression
- Restore from any backup via the UI

### Manual SQLite Backup

```bash
# Live backup (safe during writes with WAL mode)
sqlite3 /opt/blog/instance/blog.db ".backup '/var/backups/blog/backup-$(date +%Y%m%d).db'"

# Or use the .dump method for a portable SQL file
sqlite3 /opt/blog/instance/blog.db ".dump" | gzip > /var/backups/blog/backup-$(date +%Y%m%d).sql.gz

# Crontab example: daily backup at 3 AM, retain 30 days
# 0 3 * * * sqlite3 /opt/blog/instance/blog.db ".backup '/var/backups/blog/backup-$(date +\%Y\%m\%d).db'" && find /var/backups/blog -name "backup-*.db" -mtime +30 -delete
```

Include `instance/backups/` and `static/uploads/` in your backup strategy.

## 9. Monitoring

### Health Check

The app exposes a health endpoint at `GET /health`:

```json
{
  "status": "ok",
  "database": "connected",
  "scheduler": "running",
  "timestamp": "2026-04-01T12:00:00+00:00"
}
```

`status` is `"ok"` when the database responds, `"error"` otherwise.

Use this with uptime monitoring (Uptime Robot, Healthchecks.io, etc.) or as a container health check:

```bash
curl -sf http://127.0.0.1:5000/health | grep -q '"status": "ok"'
```

### Application Logs

Logs are written to `logs/blog.log` (rotated at 10 MB, 10 backups) when not in debug mode. View with:

```bash
tail -f /opt/blog/logs/blog.log
```

Or use `journalctl -u blog` for systemd-managed deployments.

## 10. Security Checklist

- [ ] `SECRET_KEY` is a random 64-character hex string and is not committed to version control
- [ ] `ADMIN_PASSWORD` is strong (12+ characters, mixed case, numbers, symbols)
- [ ] `config.toml [server] debug = false`
- [ ] `config.toml [site] base_url` uses `https://`
- [ ] HTTPS is enforced (nginx redirect from HTTP, HSTS header set by app)
- [ ] `SESSION_COOKIE_SECURE` is `True` (automatic when `debug = false`)
- [ ] `PROXY_COUNT` is set correctly for your proxy setup (default `1`)
- [ ] Static files served by nginx, not proxied through the app
- [ ] Rate limiting configured for `/admin/login` at the proxy level (5 req/min recommended)
- [ ] SQLite database file (`instance/blog.db`) is not in a web-accessible directory
- [ ] `static/uploads/` is not directly writable by the web server user
- [ ] `instance/` directory permissions are restricted (the systemd `ProtectSystem=strict` directive helps)
- [ ] SMTP credentials are set via environment variables, not in `config.toml`
- [ ] Regular backups are configured (see Section 8)

## 11. Dependencies

The application uses these key packages:

| Package | Purpose |
|---|---|
| Flask | Web framework |
| SQLAlchemy | ORM (with Flask-SQLAlchemy integration) |
| Flask-Login | User session management |
| Flask-Migrate | Database migrations (Alembic) |
| Werkzeug | Password hashing, security utilities, WSGI/ASGI adapters |
| asgiref | ASGI adapter for Granian |
| markdown | Markdown to HTML conversion for posts |
| nh3 | HTML sanitization (replaces deprecated `bleach`) |
| APScheduler | In-process newsletter scheduling |

For Python 3.14 compatibility, see `requirements.txt` for version constraints.
