# Architecture Documentation

## System Overview

DevLog is a Flask-based blogging platform with SQLAlchemy ORM, SQLite (default) or PostgreSQL migration path, FTS5 full-text search, and a Vue.js-inspired admin interface.

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Framework | Flask 3.1+ | Request handling, routing, templating |
| ORM | SQLAlchemy 2.0 | Database abstraction |
| Database | SQLite (stable) / PostgreSQL (experimental) | Data persistence |
| ASGI Server | Granian (Rust-based) | High-performance ASGI server |
| Task Queue | Celery + Redis | Async task processing |
| Cache | Flask-Caching + Redis | Response and data caching |
| Scheduler | APScheduler | In-process scheduled tasks |
| Frontend | Vite + Vanilla JS | Asset bundling and build |

## Directory Structure

```
blog/
├── app/
│   ├── __init__.py          # App factory, extensions, middleware
│   ├── models.py            # SQLAlchemy models (User, Post, Tag, etc.)
│   ├── config.py           # Configuration loading from env/toml
│   ├── extensions.py       # Flask extensions (db, login_manager, etc.)
│   ├── utils.py            # Utilities (slug generation, CSS sanitization, etc.)
│   ├── validators.py       # Input validation
│   ├── filters.py         # Jinja2 template filters
│   ├── celery_app.py      # Celery application setup
│   ├── tasks.py           # Celery task definitions
│   ├── scheduler.py       # APScheduler configuration
│   ├── email.py           # Email sending (SMTP)
│   ├── webhooks.py        # Webhook delivery
│   ├── storage.py         # Storage abstraction (local/S3)
│   ├── search.py          # FTS5 full-text search
│   ├── backup_encryption.py  # AES-256-GCM encryption for backups
│   ├── backup_integrity.py   # Backup verification
│   ├── webhook_encryption.py # AES-256-GCM for webhook secrets
│   ├── page_view_buffer.py  # High-traffic page view batching
│   ├── csv_utils.py       # CSV export/import utilities
│   ├── tag_cache.py       # Tag count caching
│   ├── context_processors.py # Template context providers
│   ├── vite.py            # Vite asset helper
│   ├── base62.py          # Short ID encoding
│   ├── markdown_config.py # Allowed HTML tags/attributes
│   ├── transaction.py     # Transaction utilities
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── api/           # REST API (posts, subscribers, stats, auth)
│   │   ├── admin/         # Admin dashboard routes
│   │   │   ├── helpers/   # Admin helpers (slug, analytics, posts, etc.)
│   │   │   └── posts/     # Post management sub-package
│   │   ├── public/        # Public blog routes
│   │   ├── rss.py         # RSS/Atom/JSON feeds
│   │   └── errors.py      # Error handlers
│   │
│   ├── services/
│   │   ├── backup.py      # Backup operations
│   │   ├── serialization.py # JSON export/import
│   │   ├── slug.py        # Slug generation
│   │   └── tag.py         # Tag management
│   │
│   ├── static/
│   │   ├── dist/         # Built assets (Vite output)
│   │   ├── uploads/       # User-uploaded images
│   │   ├── js/            # JavaScript source
│   │   └── css/           # Stylesheets
│   │
│   └── templates/         # Jinja2 templates
│
├── tests/                 # Test suite
├── migrations/           # Flask-Migrate database migrations
├── architecture/         # Detailed architecture documentation
├── docs/                 # OpenAPI specification
├── nginx/                # Nginx configuration
├── plans/                # Development roadmap
├── requirements.txt     # Python dependencies
├── run.py               # Development entry point
├── backup.py            # CLI backup utility
├── DEPLOY.md            # Production deployment guide
└── docker-compose.yml   # Docker Compose configuration
```

## Core Components

### App Factory (`app/__init__.py`)

The `create_app()` function initializes:
1. Flask app with configuration
2. Extensions (SQLAlchemy, Flask-Login, Flask-Migrate, Flask-Caching, Flask-Limiter, Flask-Compress)
3. Blueprints registration
4. Security headers middleware
5. Error handlers
6. Database integrity check
7. Scheduler initialization
8. Page view buffer initialization

### Database Models (`app/models.py`)

```
User
├── AdminSession (1:N)
├── Post (1:N)
├── AdminAuditLog (1:N)
└── totp_secret (2FA)

Post
├── Tag (N:N via post_tags)
├── PostRevision (1:N)
├── PostSeries (1:N via post_series)
├── PageView (1:N)
├── ShareEvent (1:N)
└── Comment (1:N)

Subscriber
Tag
Page
Series
AdminSession
SiteSettings
Webhook
├── WebhookEvent (1:N)
ApiToken
```

### Route Blueprints

| Blueprint | Prefix | Purpose |
|----------|---------|---------|
| `api` | `/api` | REST API for posts, subscribers, stats |
| `admin` | `/admin` | Admin dashboard and management |
| `public` | `/` | Public blog pages (home, post, archive, search) |
| `rss` | `/rss`, `/atom`, `/json` | RSS/Atom/JSON feeds |
| `errors` | - | Error handlers |

### API Routes (`app/routes/api/`)

- `posts.py`: Post CRUD with pagination, search, filtering
- `subscribers.py`: Subscriber management
- `stats.py`: Dashboard statistics
- `auth.py`: API key authentication

### Services (`app/services/`)

- `backup.py`: Unified backup service for CLI/scheduler/cron
- `serialization.py`: Data export/import to JSON
- `slug.py`: Slug generation and uniqueness
- `tag.py`: Tag CRUD operations

### Task Processing

**Celery Tasks (`app/tasks.py`):**
- `generate_image_variants`: Create responsive image variants
- `send_newsletter_task`: Send newsletter emails
- `deliver_webhook_task`: Deliver webhooks with SSRF protection
- `send_confirmation_task`: Send confirmation emails
- `send_password_reset_task`: Send password reset emails

**APScheduler (`app/scheduler.py`):**
- `publish_scheduled_posts`: Publish posts at scheduled time (every 5 minutes)
- `send_daily_newsletter`: Send daily newsletter (configurable time)
- `cleanup_expired_subscribers`: Remove unconfirmed subscribers (every 5 minutes)
- `run_daily_backup`: Daily database backup (02:00)

## Data Flow

### Request Lifecycle

```
Request → Nginx → Granian → Flask → Blueprint → Route Handler
                                                    ↓
                                              Service/Model
                                                    ↓
                                              SQLAlchemy → SQLite/PostgreSQL
```

### Newsletter Flow

```
1. Admin triggers newsletter at /admin/newsletter
2. APScheduler fires send_daily_newsletter at configured time
3. Query all confirmed subscribers
4. For each subscriber, call send_newsletter()
5. Celery task send_newsletter_task offloads to worker queue
6. Email sent via SMTP
```

### Search Flow

```
1. User submits search at /search?q=query
2. Check FTS5 availability via _fts_check()
3. If FTS5 enabled:
   - Query posts_fts table with bm25() ranking
   - Get snippets via snippet() function
4. If FTS5 disabled:
   - Fallback to SQL LIKE query
```

## Security Architecture

### Authentication & Sessions

- **Password Hashing**: `werkzeug.security` (pbkdf2:sha256)
- **Session Fixation Prevention**: `session.clear()` before `login_user()`
- **Session Lifetime**: 24 hours (configurable)
- **Admin Session Tracking**: `AdminSession` table with IP binding
- **2FA**: TOTP-based via `pyotp`

### CSRF Protection

- Sliding window of 5 valid tokens per session
- Token rotation on every successful validation
- Timing-safe comparison via `hmac.compare_digest`

### Input Sanitization

| Input | Method |
|-------|--------|
| HTML | `nh3` allowlist sanitization |
| CSS | `tinycss2` property allowlist |
| SQL | SQLAlchemy 2.0 parameterized queries |
| URLs | SSRF protection with IP range checking |

### Security Headers

```python
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-...'
```

## Caching Strategy

| Data | Cache Method | TTL |
|------|--------------|-----|
| Tag counts | `flask_cache.memoize()` | Until invalidated |
| Site settings | `flask_cache.cached()` | Until invalidated |
| Footer data | `flask_cache.cached()` | Until invalidated |
| Media listing | `flask_cache.cached()` | 30 seconds |
| FTS table check | `flask_cache.cached()` | 5 minutes |
| Dashboard analytics | `flask_cache.cached()` | 2 minutes |
| RSS feed | `flask_cache.cached()` | 5 minutes |

## Database Indexes

```python
# Posts
ix_posts_published_created    # Post listings
ix_posts_published_at          # Published posts
ix_posts_published_updated     # Dashboard
ix_posts_published_slug       # Slug lookups
ix_posts_newsletter_sent_at   # Newsletter tracking
ix_posts_scheduled_publish_at  # Scheduled posts

# Tags
ix_post_tags_tag_id           # Tag lookups

# Subscribers
ix_subscribers_confirmed_unsubscribed  # Subscriber queries

# Share Events
ix_share_events_post_created  # Share counts
ix_share_events_platform      # Platform filtering

# Comments
ix_comments_post_approved      # Comment queries
ix_comments_created_at
ix_comments_parent_id

# Post Series
ix_post_series_series_id
ix_post_series_post_id
```

## Storage Abstraction

`app/storage.py` provides a unified interface:

```python
# Local storage (default)
STORAGE_BACKEND=local

# S3 storage
STORAGE_BACKEND=s3
S3_BUCKET=my-bucket
S3_REGION=us-east-1
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_ENDPOINT=https://s3.amazonaws.com  # optional
S3_PUBLIC_URL=https://cdn.example.com  # optional
```

> **Note:** Local filesystem storage is the stable default. S3 support is experimental -- the backend code exists but is not CI-tested. The `STORAGE_BACKEND` env var defaults to `local`.

## Deployment Options

### Development
```bash
python run.py
```

### Production (Docker)
```bash
docker-compose --profile production up
```

### Production (Manual)
```bash
granian --interface asgi --workers 4 --timeout 60 run:asgi_app
```

## Configuration Priority

1. Environment variables (highest priority)
2. `config.toml` file
3. Default values in `app/config.py`

## Logging

JSON structured logging format:
```json
{"timestamp": "2026-05-05T10:30:00Z", "level": "INFO", "request_id": "abc123", "message": "Post published"}
```

Log files:
- `logs/blog.log` - Application logs
- `logs/nginx/` - Nginx access/error logs

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | - | Flask session signing key |
| `ADMIN_PASSWORD` | Yes | - | Admin login password |
| `ADMIN_USERNAME` | No | `admin` | Admin username |
| `DATABASE_URL` | No | SQLite | PostgreSQL connection string |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection |
| `SMTP_HOST` | No | - | SMTP server hostname |
| `SMTP_USER` | No | - | SMTP username |
| `SMTP_PASSWORD` | No | - | SMTP password |
| `API_KEY` | No | - | REST API key |
| `BACKUP_ENCRYPTION_KEY` | No | - | Backup encryption passphrase |
| `WEBHOOK_ENCRYPTION_KEY` | No | - | Webhook secret encryption |
| `STORAGE_BACKEND` | No | `local` | `local` or `s3` |
| `ENABLE_SCHEDULER` | No | `false` | Enable APScheduler (set on ONE container only) |
| `HEALTH_CHECK_SECRET` | No | - | Secret for detailed `/health` endpoint |
| `METRICS_SECRET` | No | - | Secret for `/metrics` endpoint |