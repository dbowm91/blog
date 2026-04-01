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

Important: the app uses in-process APScheduler with file locking (`fcntl`) to prevent duplicate newsletter sends across workers. This works on Linux. On Windows, APScheduler runs without file locking.

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

## 6. Systemd Service

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

## 7. Backup

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

## 8. Monitoring

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

## 9. Security Checklist

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
- [ ] Regular backups are configured (see Section 7)
