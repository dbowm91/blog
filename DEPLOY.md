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

For higher traffic or multi-server deployments, migrate to **PostgreSQL**. The process below provides step-by-step instructions including full-text search migration.

---

#### H4: PostgreSQL Migration Guide

##### Prerequisites

- **PostgreSQL 13+** — Required for `GENERATED ALWAYS AS` columns
- **pg_trgm extension** — Enables trigram-based fuzzy matching (optional but recommended for "Did you mean?" suggestions)
- **Python driver** — `psycopg2-binary` package

##### Step 1: Install and Configure PostgreSQL

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Switch to postgres user for admin tasks
sudo -u postgres psql

# Create database and user
CREATE DATABASE blog;
CREATE USER blog_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE blog TO blog_user;

# Grant schema permissions (required for Flask-Migrate)
\c blog blog_user
GRANT ALL ON SCHEMA public TO blog_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO blog_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO blog_user;

# Enable pg_trgm extension (for fuzzy matching in "Did you mean?" feature)
\c blog
CREATE EXTENSION IF NOT EXISTS pg_trgm;

# Exit psql
\q
```

##### Step 2: Install Python Dependencies

```bash
# Install PostgreSQL driver
pip install psycopg2-binary

# Or for production with greenlet support
pip install psycopg2-binary --no-binary psycopg2
```

##### Step 3: Update Configuration

Add the database URL to `config.toml`:

```toml
[database]
url = "postgresql://blog_user:your_secure_password@localhost/blog"
```

**Alternative: Use environment variable** (recommended for production):

```bash
export DATABASE_URL="postgresql://blog_user:your_secure_password@localhost/blog"
```

The app detects PostgreSQL automatically when the URL starts with `postgresql://` or `postgres://`.

##### Step 4: Export Data from SQLite

Before migrating, create a backup of your SQLite database:

```bash
# Backup the SQLite database
cp instance/blog.db instance/blog.db.sq3-backup

# Export data to CSV for migration
# Note: SQLite's .dump is not directly compatible with PostgreSQL
# We'll use a two-step process: CSV export, then import

mkdir -p migration_temp
cd migration_temp

# Export each table to CSV
sqlite3 ../instance/blog.db << 'EOF'
.mode csv
.headers on
.output users.csv
SELECT * FROM users;
.output posts.csv
SELECT * FROM posts;
.output tags.csv
SELECT * FROM tags;
.output post_tags.csv
SELECT * FROM post_tags;
.output subscribers.csv
SELECT * FROM subscribers;
.output page_views.csv
SELECT * FROM page_views;
.output share_events.csv
SELECT * FROM share_events;
.output admin_sessions.csv
SELECT * FROM admin_sessions;
.output site_settings.csv
SELECT * FROM site_settings;
.output post_revisions.csv
SELECT * FROM post_revisions;
.output pages.csv
SELECT * FROM pages;
.output
EOF

ls -la
```

##### Step 5: Run Flask-Migrate

Flask-Migrate (Alembic) will create the schema in PostgreSQL:

```bash
# Set environment variables
export SECRET_KEY="your-secret-key"
export ADMIN_PASSWORD="your-admin-password"
export DATABASE_URL="postgresql://blog_user:your_secure_password@localhost/blog"

# Run migrations (creates all tables)
flask db upgrade
```

##### Step 6: Import Data into PostgreSQL

Create the `import_postgresql.sql` script:

```sql
-- migration_temp/import_postgresql.sql
-- Run with: psql -U blog_user -d blog -f import_postgresql.sql

-- Disable triggers for initial import (we'll re-enable and rebuild FTS at the end)
SET session_replication_role = replica;

-- Users (import first - other tables reference this)
\COPY users(id, username, password_hash, is_admin, created_at) FROM 'users.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users)) FROM users;

-- Posts (import before tags - post_tags references both)
\COPY posts(id, title, slug, body, summary, image, created_at, updated_at, published, published_at, scheduled_publish_at, newsletter_sent_at, newsletter_attempts) FROM 'posts.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('posts_id_seq', (SELECT MAX(id) FROM posts)) FROM posts;

-- Tags
\COPY tags(id, name, slug, created_at) FROM 'tags.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('tags_id_seq', (SELECT MAX(id) FROM tags)) FROM tags;

-- Post-Tags relationship
\COPY post_tags(post_id, tag_id) FROM 'post_tags.csv' WITH (FORMAT csv, NULL 'NULL');

-- Subscribers
\COPY subscribers(id, email, token, confirmed, created_at, expires_at, unsubscribed_at) FROM 'subscribers.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('subscribers_id_seq', (SELECT MAX(id) FROM subscribers)) FROM subscribers;

-- Page Views
\COPY page_views(id, post_id, referrer, created_at) FROM 'page_views.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('page_views_id_seq', (SELECT MAX(id) FROM page_views)) FROM page_views;

-- Share Events
\COPY share_events(id, post_id, platform, created_at) FROM 'share_events.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('share_events_id_seq', (SELECT MAX(id) FROM share_events)) FROM share_events;

-- Admin Sessions
\COPY admin_sessions(id, user_id, session_id, ip_address, user_agent, created_at, last_activity) FROM 'admin_sessions.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('admin_sessions_id_seq', (SELECT MAX(id) FROM admin_sessions)) FROM admin_sessions;

-- Site Settings
\COPY site_settings(id, theme_preset, custom_css_enabled, custom_css, logo_text, updated_at) FROM 'site_settings.csv' WITH (FORMAT csv, NULL 'NULL');

-- Post Revisions
\COPY post_revisions(id, post_id, title, slug, body, summary, created_at, author_id) FROM 'post_revisions.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('post_revisions_id_seq', (SELECT MAX(id) FROM post_revisions)) FROM post_revisions;

-- Pages (static pages)
\COPY pages(id, title, slug, body, published, created_at, updated_at) FROM 'pages.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('pages_id_seq', (SELECT MAX(id) FROM pages)) FROM pages;

-- Re-enable triggers
RESET session_replication_role;

-- Create PostgreSQL full-text search index (replaces FTS5)
-- This is the key step for FTS migration

-- Add tsvector generated column for full-text search
ALTER TABLE posts ADD COLUMN search_vector tsvector
GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(summary, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(body, '')), 'C')
) STORED;

-- Create GIN index for fast full-text search
CREATE INDEX ix_posts_search_vector ON posts USING gin(search_vector);

-- Create trigger to keep search_vector updated on INSERT/UPDATE
CREATE OR REPLACE FUNCTION posts_search_trigger() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.summary, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(NEW.body, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER posts_search_update
    BEFORE INSERT OR UPDATE OF title, summary, body ON posts
    FOR EACH ROW EXECUTE FUNCTION posts_search_trigger();

-- Vacuum to update statistics
VACUUM ANALYZE posts;

-- Verify the migration
SELECT 'Posts with search_vector:' AS info, count(*) FROM posts WHERE search_vector IS NOT NULL;
SELECT 'Posts with NULL search_vector:' AS info, count(*) FROM posts WHERE search_vector IS NULL;
```

Run the import:

```bash
cd migration_temp
psql -U blog_user -d blog -f import_postgresql.sql
cd ..
```

##### Step 7: Configure Search Module

The search module (`app/search.py`) uses SQLite FTS5, which is not compatible with PostgreSQL. After migration:

**Option A: Use PostgreSQL Full-Text Search (Recommended)**

Replace `app/search.py` with PostgreSQL-specific implementation. The key changes:

```python
# Replace FTS5 queries with PostgreSQL tsvector queries

def _check_fts_enabled() -> bool:
    """Check if PostgreSQL tsvector column exists."""
    from sqlalchemy import text
    result = db.session.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'posts' AND column_name = 'search_vector'
        )
    """))
    return result.scalar() is True

def search(query: str) -> list[tuple[int, int]]:
    """Search using PostgreSQL tsvector."""
    # Convert query to tsquery format
    tsquery = " & ".join(query.split())  # Simple AND for multi-word
    result = db.session.execute(text("""
        SELECT id, ts_rank(search_vector, to_tsquery('english', :q)) AS rank
        FROM posts
        WHERE published = TRUE
          AND search_vector @@ to_tsquery('english', :q)
        ORDER BY rank DESC
        LIMIT :limit
    """), {"q": tsquery, "limit": FTS_RESULT_LIMIT})
    return [(row[0], row[1]) for row in result.fetchall()]
```

**Option B: Use Search-as-a-Service (Elasticsearch, Typesense)**

For large-scale deployments, consider:
- **Typesense** — Lightweight, PostgreSQL-like API, supports similarity search
- **Elasticsearch** — Industry standard for full-text search
- **Meilisearch** — Modern, fast, great developer experience

These require separate infrastructure but offer superior search quality and scalability.

##### Step 8: Update Application for PostgreSQL

Key differences to handle in code:

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| Connection | File-based | TCP socket |
| WAL mode | Enabled by default | Not applicable (PostgreSQL uses MVCC) |
| FTS | FTS5 virtual table | `tsvector` generated column + GIN index |
| Locking | Busy timeout | Row-level locking |
| Backup | `.backup` command | `pg_dump` / `pg_restore` |
| Concurrency | Serialized writes | True concurrent reads/writes |

No code changes are required for most SQLAlchemy operations—the ORM handles database differences. The main exception is the FTS search module.

##### Step 9: Verify the Migration

```bash
# Start the application with PostgreSQL
export SECRET_KEY="your-secret-key"
export ADMIN_PASSWORD="your-admin-password"
export DATABASE_URL="postgresql://blog_user:your_secure_password@localhost/blog"
python run.py
```

Test these operations:
- [ ] View posts on homepage
- [ ] Search functionality (`/?q=test`)
- [ ] Admin login
- [ ] Create/edit a post
- [ ] Check analytics (page views)
- [ ] Newsletter send (test mode)
- [ ] Backup/restore functionality

##### Step 10: Switch to Production Server

Once verified, update your production configuration:

```bash
# Set environment variables
export DATABASE_URL="postgresql://blog_user:your_secure_password@localhost/blog"
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export ADMIN_PASSWORD="your-new-strong-password"

# Run with Granian
granian --interface asgi --workers 4 --host 127.0.0.1 --port 5000 run:asgi_app
```

---

##### Known Limitations and Differences from SQLite

| Issue | SQLite Behavior | PostgreSQL Behavior |
|-------|-----------------|---------------------|
| **File-based storage** | Single file `instance/blog.db` | Server process required |
| **Backup** | `.backup` command or copy file | `pg_dump` / `pg_restore` |
| **Concurrent writes** | Serialized with busy timeout | True concurrent writes |
| **Full-text search** | FTS5 virtual table | `tsvector` + GIN index |
| **WAL mode** | Enabled for concurrent reads | Not applicable |
| **Connection pooling** | Not needed | Recommended (`pgbouncer` for high traffic) |
| **Connection string** | File path | `postgresql://user:pass@host/db` |
| **Schema migrations** | Flask-Migrate | Flask-Migrate (Alembic) |

**PostgreSQL-specific considerations:**

1. **Connection pooling** — For high-traffic sites, use `pgbouncer`:
   ```bash
   # Install pgbouncer
   sudo apt install pgbouncer
   
   # Configure /etc/pgbouncer/pgbouncer.ini
   [databases]
   blog = host=127.0.0.1 port=5432 dbname=blog
   
   [pgbouncer]
   pool_mode = transaction
   max_client_conn = 100
   default_pool_size = 20
   ```
   Then connect via: `postgresql://blog_user:pass@localhost:6432/blog`

2. **Character encoding** — Ensure UTF-8 encoding is configured:
   ```sql
   ALTER DATABASE blog SET client_encoding TO 'UTF8';
   ```

3. **Timezone handling** — PostgreSQL handles timezones natively. The app's `UTCDateTime` TypeDecorator works correctly, but naive/aware datetime handling may differ.

4. **Case sensitivity** — SQLite's `LIKE` is case-insensitive for ASCII; PostgreSQL requires `ILIKE` for case-insensitive matching. The search module already uses `ILIKE` in the LIKE fallback.

5. **Index differences** — SQLite and PostgreSQL have different index structures. PostgreSQL query planner may produce different execution plans. Use `EXPLAIN ANALYZE` to debug performance issues.

6. **Newsletter file locking** — The APScheduler newsletter uses `fcntl` file locking, which is Unix-only and designed for single-machine multi-worker setups. With PostgreSQL, the advisory lock pattern can be used for distributed locking if needed.

7. **SQLite dump incompatibility** — SQLite `.dump` output uses SQLite-specific SQL syntax that PostgreSQL cannot parse. Always use CSV export or `sqlite3 -csv` mode for data migration.

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
    limit_req_zone $binary_remote_addr zone=api:10m rate=20r/m;
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

        # Rate limit API routes
        location /api/ {
            limit_req zone=api burst=10 nodelay;
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

### Off-site Backup Sync

The `scripts/sync_backups.sh` script syncs local backups to remote storage (S3, Google Drive, etc.) using rclone or native AWS CLI.

**Prerequisites:**

```bash
# Install rclone (recommended)
curl https://rclone.org/install.sh | sudo bash

# Or install AWS CLI for S3
pip install awscli
```

**Configuration:**

```bash
# For rclone (supports S3, Google Drive, Azure Blob, SFTP, etc.)
export RCLONE_REMOTE="s3:my-backups/blog"
export RETENTION_DAYS=7

# For native S3
export REMOTE_TYPE="s3"
export AWS_S3_BUCKET="my-backups"
export AWS_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
```

**Usage:**

```bash
# Sync backups (with rclone)
./scripts/sync_backups.sh

# Preview changes without syncing
./scripts/sync_backups.sh --dry-run

# Verify backups after sync
./scripts/sync_backups.sh --verify

# Sync and cleanup local backups older than 14 days
./scripts/sync_backups.sh --cleanup 14
```

**Automated Sync with Cron:**

```bash
# Add to crontab: sync backups daily at 4 AM
crontab -e

# 0 4 * * * /opt/blog/scripts/sync_backups.sh --verify --cleanup 7 >> /opt/blog/logs/backup_sync.log 2>&1
```

**Backup Verification:**

The `app/backup_integrity.py` module provides integrity verification:

```python
from app.backup_integrity import verify_backup_integrity, verify_backup_set

# Verify a single backup
is_valid, message = verify_backup_integrity(backup_path)

# Verify all backups in a directory
results = verify_backup_set(backup_dir)
```

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

## 10. Maintenance Cron Jobs

Schedule these maintenance tasks with cron to keep the blog running smoothly:

```bash
# Edit crontab
crontab -e

# Database integrity check (weekly)
0 2 * * 0 cd /opt/blog && ADMIN_PASSWORD=yourpass SECRET_KEY=yourkey flask check-integrity >> logs/integrity.log 2>&1

# Rebuild search index (weekly, after integrity check)
0 3 * * 0 cd /opt/blog && ADMIN_PASSWORD=yourpass SECRET_KEY=yourkey flask rebuild-search >> logs/search.log 2>&1

# Clean up orphaned images (monthly)
0 4 1 * * cd /opt/blog && ADMIN_PASSWORD=yourpass SECRET_KEY=yourkey flask cleanup-orphaned-images >> logs/cleanup.log 2>&1

# Sync backups to off-site storage (daily at 4 AM)
0 4 * * * /opt/blog/scripts/sync_backups.sh --verify --cleanup 7 >> /opt/blog/logs/backup_sync.log 2>&1
```

**Newsletter:** The newsletter scheduler runs in-process via APScheduler and requires no external cron setup. The scheduler wakes every 5 minutes to check for scheduled posts and newsletters.

## 11. Security Checklist

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

## 12. Dependencies

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
