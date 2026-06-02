# Architecture Overview

DevLog is a Flask-based blog CMS with SQLAlchemy ORM, full-text search, async task processing, and Vue/Vite frontend.

This document provides a **birds-eye view** of all system components and serves as an **index** to detailed architecture documents for focused review.

---

## Discrete Modules

The codebase is organized into these discrete modules, each with dedicated deep-dive documentation:

| Module | Description | Deep Dive |
|--------|-------------|-----------|
| [Core Application](#1-core-application) | Flask app factory, configuration, extensions | [core/app-factory.md](core/app-factory.md), [core/configuration.md](core/configuration.md) |
| [Data Models](#2-data-models) | SQLAlchemy ORM models (17 models) | [core/models.md](core/models.md) |
| [Routes Layer](#3-routes-layer) | HTTP request handlers (admin, public, API, feeds) | [routes/admin-routes.md](routes/admin-routes.md), [routes/public-routes.md](routes/public-routes.md), [routes/api-routes.md](routes/api-routes.md), [routes/rss-feeds.md](routes/rss-feeds.md) |
| [Services Layer](#4-services-layer) | Business logic (backup, search, slug, tags, encryption) | [services/overview.md](services/overview.md), [services/backup.md](services/backup.md), [services/search.md](services/search.md), [services/slug.md](services/slug.md), [services/tag.md](services/tag.md), [services/encryption.md](services/encryption.md), [services/serialization.md](services/serialization.md), [services/tag_cache.md](services/tag_cache.md) |
| [Task Processing](#5-task-processing) | Async (Celery) and scheduled (APScheduler) tasks | [tasks/overview.md](tasks/overview.md), [tasks/celery-tasks.md](tasks/celery-tasks.md), [tasks/scheduler.md](tasks/scheduler.md) |
| [Infrastructure](#6-infrastructure) | Search, email, storage, webhooks | [infrastructure/search.md](infrastructure/search.md), [infrastructure/email.md](infrastructure/email.md), [infrastructure/storage.md](infrastructure/storage.md), [infrastructure/webhooks.md](infrastructure/webhooks.md) |
| [Frontend](#7-frontend) | Jinja2 templates, CSS, JavaScript (Vite) | [frontend/overview.md](frontend/overview.md), [frontend/templates.md](frontend/templates.md), [frontend/static-assets.md](frontend/static-assets.md) |
| [Security](#8-security-architecture) | Authentication, 2FA, CSRF, rate limiting | [deployment/security.md](deployment/security.md) |
| [Deployment](#9-deployment) | Docker, nginx, CI/CD | [deployment/overview.md](deployment/overview.md), [deployment/docker.md](deployment/docker.md) |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               Clients                                        │
│                    (Browser, API Clients, RSS Readers)                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Nginx (TLS Termination)                            │
│                    Static Files, Load Balancing, Brotli                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Granian ASGI Server (Rust)                            │
│                     Flask App + APScheduler (in-process)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
             ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
              ▼                         ▼                         ▼
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│   Celery Worker │     │       Redis         │     │                 │
│   (Redis Queue) │◄────│  (Broker + Cache   │────►│  (Rate Limits)  │
│                 │     │   + Rate Limits)    │     │                 │
│  • images       │     │                     │     │                 │
│  • newsletter   │     │  Queues:           │     │                 │
│  • webhooks     │     │  • images          │     │                 │
│  • email        │     │  • newsletter      │     │                 │
│  • backup       │     │  • webhooks        │     │                 │
│                 │     │  • email           │     │                 │
│                 │     │  • backup          │     │                 │
│                 │     │                     │     │                 │
│                 │     │  Single REDIS_URL  │     │                 │
│                 │     │  (multiple uses)   │     │                 │
└─────────────────┘     └─────────────────────┘     └─────────────────┘
             │                         │
             └─────────────────────────┼─────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SQLite (WAL) / PostgreSQL                             │
│                                                                              │
│  Tables: users, posts, tags, subscribers, page_views, share_events,           │
│          admin_sessions, site_settings, pages, post_revisions,                │
│          webhooks, webhook_events, series, post_series, comments,             │
│          admin_audit_logs, api_tokens                                         │
│                                                                              │
│  FTS5: posts_fts (full-text search virtual table)                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Core Application

**Source:** `app/__init__.py`, `app/config.py`, `app/extensions.py`, `app/filters.py`, `app/context_processors.py`, `app/tag_cache.py`, `app/cli.py`, `app/validators.py`

**Purpose:** Initialize Flask app, configure extensions, register blueprints, set up middleware.

| Component | File | Purpose |
|-----------|------|---------|
| App Factory | `app/__init__.py` | `create_app()` - Flask app factory |
| Configuration | `app/config.py` | TOML loading, env overrides, validation |
| Extensions | `app/extensions.py` | SQLAlchemy, LoginManager, Migrate |
| Filters | `app/filters.py` | Jinja2 template filters |
| Context Processors | `app/context_processors.py` | Template global variables |
| CLI Commands | `app/cli.py` | Flask CLI commands (rebuild-search, seed, etc.) |
| Validators | `app/validators.py` | API input validation |
| Tag Cache | `app/tag_cache.py` | Tag count caching with Flask-Caching TTL |

**Deep Dive:** [core/app-factory.md](core/app-factory.md), [core/configuration.md](core/configuration.md)

---

## 2. Data Models

**Source:** `app/models.py` (17 models)

**Purpose:** Database schema and relationships.

| Model | Purpose |
|-------|---------|
| `User` | Admin users with TOTP 2FA, backup codes, account lockout |
| `Post` | Blog posts with revisions, tags, series |
| `Tag` | Post categorization |
| `Subscriber` | Newsletter subscribers with confirmation tokens |
| `Page` | Static pages |
| `PageView` | Analytics page views |
| `ShareEvent` | Social sharing tracking |
| `AdminSession` | Admin login session tracking with IP binding |
| `SiteSettings` | Singleton site configuration |
| `Webhook` | Webhook endpoints with encrypted secrets |
| `WebhookEvent` | Webhook delivery events with status tracking |
| `Series` | Post series groupings |
| `PostSeries` | Series-post junction with ordering |
| `Comment` | Threaded comments with parent-child relationships |
| `PostRevision` | Post edit history |
| `AdminAuditLog` | Security audit trail |
| `ApiToken` | API authentication tokens with scoped access |

**Deep Dive:** [core/models.md](core/models.md)

---

## 3. Routes Layer

**Source:** `app/routes/`

**Purpose:** Handle HTTP requests and responses for public, admin, and API access.

| Module | Source | Purpose |
|--------|--------|---------|
| Public Routes | `app/routes/public/` | Blog pages, posts, subscriptions |
| Admin Routes | `app/routes/admin/` | Dashboard, CRUD operations |
| API Routes | `app/routes/api/` | REST API for programmatic access |
| RSS/Feeds | `app/routes/rss.py` | Atom, RSS, JSON feeds |
| Error Handlers | `app/routes/errors.py` | 404, 500, 413 responses |

**Deep Dive:** [routes/admin-routes.md](routes/admin-routes.md), [routes/public-routes.md](routes/public-routes.md), [routes/api-routes.md](routes/api-routes.md), [routes/rss-feeds.md](routes/rss-feeds.md)

---

### API Routes Detail (`app/routes/api/`)

| Endpoint | File | Purpose |
|----------|------|---------|
| `/api/posts` | `posts.py` | Post CRUD with pagination, search, filtering |
| `/api/subscribers` | `subscribers.py` | Subscriber management |
| `/api/stats` | `stats.py` | Dashboard statistics |
| `/api/pages` | `pages.py` | Static page management |
| `/api/series` | `series.py` | Post series management |
| `/api/tags` | `tags.py` | Tag management |
| API Auth | `auth.py` | `require_api_key` decorator |

---

## 4. Services Layer

**Source:** `app/services/`

**Purpose:** Business logic encapsulation, abstraction layer for reusable functionality.

| Service | Source | Purpose |
|---------|--------|---------|
| Backup | `app/services/backup.py` | Database backup with compression/encryption |
| Backup Encryption | `app/backup_encryption.py` | AES-256-GCM backup file encryption |
| Encryption | `app/services/encryption.py` | AES-256-GCM for TOTP secrets |
| Search | `app/services/search/` | Search provider abstraction (SQLite FTS5, PostgreSQL stub) |
| Slug | `app/services/slug.py` | Slug generation with collision handling |
| Tag | `app/services/tag.py` | Tag CRUD operations |
| Serialization | `app/services/serialization.py` | JSON export/import |
| Webhook Encryption | `app/webhook_encryption.py` | AES-256-GCM webhook secret encryption |

**Deep Dive:** [services/overview.md](services/overview.md), [services/backup.md](services/backup.md), [services/search.md](services/search.md), [services/slug.md](services/slug.md), [services/tag.md](services/tag.md), [services/encryption.md](services/encryption.md), [services/serialization.md](services/serialization.md), [services/tag_cache.md](services/tag_cache.md)

---

### Search Provider Abstraction (`app/services/search/`)

The `app/services/search/` module wraps the low-level `app/search.py` FTS5 implementation with a provider-based abstraction for future flexibility:

| File | Purpose |
|------|---------|
| `__init__.py` | `SearchProvider` ABC defining the interface |
| `sqlite.py` | FTS5 implementation delegating to `app/search.py` |
| `postgresql.py` | PostgreSQL FTS stub (future implementation) |

**Key Functions (from `app/search.py`):**
- `init_fts()` - Create FTS5 virtual table
- `sync_fts()` / `sync_fts_batch()` - Index posts
- `search()` - Query with BM25 ranking
- `get_search_snippets()` - Generate highlighted snippets
- `get_did_you_mean()` - Fuzzy matching suggestions

---

## 5. Task Processing

**Source:** `app/tasks.py`, `app/scheduler.py`, `app/celery_app.py`

**Purpose:** Handle asynchronous and scheduled background work.

| System | Source | Purpose |
|--------|--------|---------|
| Celery | `app/tasks.py` | Async task queue with Redis broker |
| APScheduler | `app/scheduler.py` | In-process scheduled jobs |

**Celery Queues:**
| Queue | Tasks |
|-------|-------|
| `images` | Image variant generation |
| `newsletter` | Newsletter delivery (Celery task — no attempt check) |
| `webhooks` | Webhook delivery |
| `email` | Transactional emails |
| `backup` | Database backups |

**APScheduler Jobs:**
| Job | Schedule | Purpose |
|-----|----------|---------|
| `send_daily_newsletter` | Daily at configured time | Auto-send newsletter |
| `cleanup_expired_subscribers` | Every 5 minutes | Remove unconfirmed expired |
| `publish_scheduled_posts` | Every 5 minutes | Auto-publish scheduled posts |
| `run_daily_backup` | Daily at 02:00 | Daily database backup |

**Newsletter Delivery Paths:** Two paths terminate at `email.send_newsletter()`:
1. **Daily scheduled:** `scheduler.send_daily_newsletter()` (APScheduler) → `email.send_newsletter()` — checks `NEWSLETTER_MAX_RETRY_ATTEMPTS`, filters posts by `newsletter_attempts`
2. **Manual/ad-hoc:** `send_newsletter_task` (Celery) → `email.send_newsletter()` — no attempt count check, sends for all requested post IDs

**Newsletter Retry:** Scheduler path respects `NEWSLETTER_MAX_RETRY_ATTEMPTS` (`app/scheduler.py:118`). Celery task does not check attempt counts — it sends for all posts in `post_ids` regardless of prior failures. Retry count is 5.

**APScheduler Multi-Container Warning:** APScheduler uses `FileLock` with `timeout=0` which only works on a single machine. In multi-container deployments, each container runs its own scheduler and jobs may execute simultaneously.

**Deep Dive:** [tasks/overview.md](tasks/overview.md), [tasks/celery-tasks.md](tasks/celery-tasks.md), [tasks/scheduler.md](tasks/scheduler.md)

---

## 6. Infrastructure

**Source:** `app/search.py`, `app/email.py`, `app/storage.py`, `app/webhooks.py`, `app/utils.py`

**Purpose:** Supporting systems for core application operation.

| Component | Source | Purpose |
|-----------|--------|---------|
| Search | `app/search.py` | FTS5 full-text search (low-level implementation) |
| Email | `app/email.py` | SMTP email delivery |
| Storage | `app/storage.py` | Local/S3 storage abstraction |
| Webhooks | `app/webhooks.py` | Event-driven webhook delivery |
| Utilities | `app/utils.py` | SSRF protection, logging helpers |
| Health Check | `app/routes/public/meta.py` | System health monitoring |

**Note on FTS Initialization:** FTS5 init failures are caught and rolled back silently (`app/__init__.py:430-433`). The user is never informed if full-text search will not function. Consider failing loudly or surfacing a user-visible error when FTS init fails.

### Health Check (`GET /health`)

**Source:** `app/routes/public/meta.py:188-321`

Health endpoint for monitoring with rate limit of 60/min per IP.

#### Authentication

- **Basic call**: `GET /health` — returns summary status without sensitive details
- **Detailed call**: `GET /health?detailed=true&secret=<HEALTH_CHECK_SECRET>` — returns extra detail fields (database latency, scheduler next run, last newsletter send)
- The `detailed` param alone is not enough; `secret` must match `HEALTH_CHECK_SECRET` env var via constant-time HMAC comparison

#### Critical Checks

These checks determine the overall `status` field:

| Check | Validation | Status Values |
|-------|-----------|---------------|
| `database` | Executes `SELECT 1` against the database, measures latency | `ok`, `error` |
| `scheduler` | Calls `get_scheduler_health()` if `SMTP_HOST` is set | `running`, `disabled`, `error` |
| `search` | Queries `sqlite_master` for `posts_fts` table existence | `ok`, `unavailable`, `error` |
| `disk_space` | Checks `shutil.disk_usage()` on instance path; threshold is 10% free | `ok`, `low`, `error` |
| `db_integrity` | Runs `PRAGMA integrity_check` | `ok`, `error` |

#### Optional Checks

These checks are included in the response but do **not** affect overall status:

| Check | Validation | Status Values |
|-------|-----------|---------------|
| `redis` | Redis `PING` with 2s connect/timeout | `ok`, `error` |
| `celery` | `celery_app.control.inspect().ping()` with 3s timeout | `ok`, `unavailable`, `disabled` |
| `backup_freshness` | Finds most recent backup file by mtime; checks age < 24 hours | `ok`, `stale`, `no_backups`, `error` |

#### Overall Status Logic

- **`ok`**: All critical checks have status in `("ok", "running", "disabled")`
- **`degraded`**: Any critical check has status `"error"` or `"low"`
- The HTTP status code is `200` when overall is `ok`, `503` when `degraded`

#### Detailed Response

When authenticated with `?detailed=true&secret=<key>`, the response includes a `details` object:

| Field | Source |
|-------|--------|
| `database_latency_ms` | Time for `SELECT 1` in milliseconds |
| `scheduler_next_run` | Next scheduled job run time (if scheduler enabled) |
| `scheduler_last_newsletter_send` | Timestamp of last newsletter send (if scheduler enabled) |

#### Response Format

```json
{
  "status": "ok|degraded",
  "checks": {
    "database": "ok",
    "scheduler": "running",
    "search": "ok",
    "disk_space": "ok",
    "db_integrity": "ok",
    "redis": "ok",
    "celery": "ok",
    "backup_freshness": "ok"
  },
  "timestamp": "2026-06-02T12:00:00+00:00",
  "details": {
    "database_latency_ms": 0.42,
    "scheduler_next_run": "2026-06-03T08:00:00+00:00",
    "scheduler_last_newsletter_send": "2026-06-02T08:00:00+00:00"
  }
}
```

### Storage (`app/storage.py`)

Storage abstraction layer for media files with local and S3 backends.

| Class | Purpose |
|-------|---------|
| `StorageBackend` | Abstract base class defining the interface |
| `LocalStorageBackend` | Local filesystem storage |
| `S3StorageBackend` | S3-compatible storage via boto3 |

Configured via `STORAGE_BACKEND` env var: `"local"` (default) or `"s3"`. `get_storage()` returns a module-level singleton. Lazy client initialization for S3 uses `threading.Lock`. `save()` raises exceptions on failure (with logging). Other S3 methods return `False` or empty lists on failure.

### SSRF Protection (`app/utils.py`)

Webhook delivery includes Server-Side Request Forgery (SSRF) protection to prevent requests to internal/private networks.

- **URL Validation**: Before sending webhook requests, URLs are validated against private IP ranges
- **Blocked Ranges**: `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `::1/128`, `fc00::/7`
- **DNS Rebinding Protection**: Resolves hostname and checks resolved IP before sending
- **Redirect Prevention**: `allow_redirects=False` prevents redirect-based SSRF bypass
- **Implementation**: `app/utils.py:383-485` (~100 lines). Returns `tuple[bool, str]`.

**Deep Dive:** [infrastructure/search.md](infrastructure/search.md), [infrastructure/email.md](infrastructure/email.md), [infrastructure/storage.md](infrastructure/storage.md), [infrastructure/webhooks.md](infrastructure/webhooks.md)

---

## 7. Frontend

**Source:** `app/templates/`, `app/static/`

**Purpose:** User-facing JavaScript, CSS, and templates.

| Component | Source | Purpose |
|-----------|--------|---------|
| Static Assets | `app/static/` | JS modules (Vite-bundled), CSS, fonts, images |
| Templates | `app/templates/` | Jinja2 templates (admin, public, email) |

**Deep Dive:** [frontend/overview.md](frontend/overview.md), [frontend/templates.md](frontend/templates.md), [frontend/static-assets.md](frontend/static-assets.md)

> **⚠️ Production Deployment Requirement:** The Vite build (`npm run build`) must be run before production deployment. The `manifest.json` file (generated at `app/static/dist/.vite/manifest.json`) must be present. If Vite build has not run, JavaScript assets will return hashed paths that do not exist, resulting in broken functionality.

---

## 8. Security Architecture

**Source:** `app/routes/admin/auth.py`, `app/services/encryption.py`, `app/middleware/rate_limit.py`, `app/csrf.py`

**Purpose:** Authentication, authorization, and protection against attacks.

| Feature | Implementation |
|---------|---------------|
| **Authentication** | Session-based with optional TOTP 2FA |
| **2FA** | TOTP secrets encrypted with AES-256-GCM |
| **Backup Codes** | SHA-256 hashed, single-use (8 codes) |
| **CSRF** | Sliding window tokens (5 valid) via `app/csrf.py`; globally enforced via `before_request_handler()` (`app/__init__.py:296-298`) |
| **API Auth** | Two-tier: legacy `API_KEY` env var with HMAC comparison + scoped `ApiToken` model with `require_scope()` decorator |

> **CSRF Scope for API Clients:** CSRF validation is enforced globally for **all POST requests** (`app/__init__.py:297-298`), including API endpoints. API clients authenticating with Bearer tokens (`ApiToken`) do not have Flask sessions containing CSRF tokens, so POST requests to API endpoints will return 403. API clients should either use the legacy `API_KEY` header (which bypasses CSRF via HMAC comparison) or provide a valid CSRF token in the request. This is a known design interaction documented in `plans/plan.md` (Wave 2 item 2.12).
| **Account Lockout** | 5 failed attempts → 15-minute lockout |
| **SSRF Protection** | URL validation against private IP ranges |
| **Webhook Signing** | HMAC-SHA256 with `X-Webhook-Signature` header |
| **XSS** | `nh3` HTML sanitizer, CSP headers |
| **Audit Logging** | `AdminAuditLog` for all admin actions |
| **Rate Limiting** | Flask-Limiter with Redis/memory backend via `app/middleware/rate_limit.py` |
| **Session Fixation** | `session.clear()` before `login_user()` |

**Deep Dive:** [deployment/security.md](deployment/security.md)

---

## 9. Deployment

**Source:** `Dockerfile`, `docker-compose.yml`, `nginx/`, `scripts/`

**Purpose:** Container orchestration, web server configuration, CI/CD.

| Component | Purpose |
|-----------|---------|
| Docker | Containerized deployment; health check includes 10s `start_period` before healthy status |
| Docker Compose | Multi-container orchestration; requires explicit profiles (`--profile production`, `--profile backup`) — no default profile |
| Nginx | TLS termination, static files, load balancing |
| CI/CD | Automated testing and deployment |

**Deep Dive:** [deployment/overview.md](deployment/overview.md), [deployment/docker.md](deployment/docker.md), [deployment/cicd.md](deployment/cicd.md)

---

## Directory Structure

```
blog/
├── app/                              # Main application package
│   ├── __init__.py                   # create_app() - Flask app factory
│   ├── config.py                     # Configuration loading from TOML + env
│   ├── models.py                     # SQLAlchemy ORM models (17 models)
│   ├── extensions.py                 # Flask extensions (db, login_manager, migrate)
│   ├── utils.py                      # Utilities (slug, UTCDateTime, SSRF)
│   ├── validators.py                # API input validation
│   ├── filters.py                   # Jinja2 template filters
│   ├── context_processors.py         # Template context injectors
│   ├── email.py                     # SMTP email sending
│   ├── webhooks.py                  # Webhook event creation/delivery
│   ├── storage.py                    # Local/S3 storage abstraction
│   ├── search.py                    # FTS5 full-text search
│   ├── tasks.py                     # Celery async tasks
│   ├── scheduler.py                 # APScheduler jobs
│   ├── celery_app.py                # Celery configuration
│   ├── csrf.py                      # CSRF token validation
│   ├── page_view_buffer.py          # Buffered page view writes
│   ├── tag_cache.py                 # Tag count caching
│   ├── backup_integrity.py          # Backup verification
│   ├── webhook_encryption.py        # Webhook secret encryption
│   ├── backup_encryption.py         # Backup file encryption
│   ├── markdown_config.py           # Markdown processing config
│   ├── transaction.py              # Transaction helpers
│   ├── csv_utils.py                 # CSV export utilities
│   ├── base62.py                    # Post ID encoding
│   ├── cli.py                       # CLI commands (flask cli)
│   │
│   ├── routes/                      # Route blueprints
│   │   ├── __init__.py
│   │   ├── admin/                   # Admin blueprint
│   │   │   ├── __init__.py         # Blueprint + auth decorators
│   │   │   ├── auth.py             # Login, logout, 2FA, password reset
│   │   │   ├── posts/              # Post management
│   │   │   │   ├── __init__.py     # Registers routes
│   │   │   │   ├── manage.py       # CRUD operations
│   │   │   │   ├── editor.py       # Post editor
│   │   │   │   └── revisions.py   # Post revisions
│   │   │   ├── subscribers.py      # Subscriber management
│   │   │   ├── tags.py             # Tag management
│   │   │   ├── users.py            # User management
│   │   │   ├── sessions.py         # Admin session management
│   │   │   ├── media.py            # Media library
│   │   │   ├── backup.py           # Backup/restore
│   │   │   ├── analytics.py        # Analytics dashboard
│   │   │   ├── newsletter.py      # Newsletter sending
│   │   │   ├── settings.py         # Site settings
│   │   │   ├── pages.py            # Static pages
│   │   │   ├── series.py           # Post series
│   │   │   ├── audit.py           # Audit log viewer
│   │   │   ├── comments.py         # Comment moderation
│   │   │   └── helpers/            # Shared admin utilities
│   │   │       ├── __init__.py
│   │   │       ├── analytics.py
│   │   │       ├── dashboard.py
│   │   │       ├── posts.py
│   │   │       ├── images.py
│   │   │       ├── slug.py
│   │   │       ├── tags.py
│   │   │       └── shared.py
│   │   ├── api/                     # REST API blueprint
│   │   │   ├── __init__.py
│   │   │   ├── auth.py            # require_api_key decorator
│   │   │   ├── posts.py           # Post CRUD
│   │   │   ├── subscribers.py     # Subscriber endpoints
│   │   │   └── stats.py           # Analytics stats
│   │   ├── public/                 # Public-facing blueprint
│   │   │   ├── __init__.py
│   │   │   ├── browse.py          # Home, archive, tag pages
│   │   │   ├── posts.py           # Post view, preview, share
│   │   │   ├── subscribe.py       # Newsletter subscription
│   │   │   ├── comments.py        # Comment submission
│   │   │   └── meta.py            # Sitemap, robots.txt, health
│   │   ├── rss.py                  # Atom, RSS, JSON feeds
│   │   └── errors.py               # 404, 500, 413 handlers
│   │
│   ├── services/                    # Business logic services
│   │   ├── backup.py              # Backup with compression/encryption
│   │   ├── encryption.py          # AES-256-GCM for TOTP secrets
│   │   ├── serialization.py       # JSON export/import
│   │   ├── slug.py                # Slug generation
│   │   ├── tag.py                 # Tag CRUD
│   │   └── search/                # Search abstraction
│   │       ├── __init__.py       # SearchProvider ABC
│   │       ├── sqlite.py         # FTS5 implementation
│   │       └── postgresql.py     # PostgreSQL FTS (stub)
│   │
│   ├── middleware/                 # WSGI middleware
│   │   └── rate_limit.py         # Admin rate limiting
│   │
│   └── static/                    # Frontend assets
│       ├── css/                   # Stylesheets
│       ├── js/                    # JavaScript (Vite-bundled)
│       ├── img/                   # Static images
│       ├── fonts/                 # Web fonts
│       └── uploads/              # User media uploads
│
├── tests/                           # Test suite
│   ├── conftest.py                 # Pytest configuration
│   ├── shared_fixtures.py          # Shared fixtures
│   ├── test_*.py                  # Unit/integration tests
│   └── e2e/                       # Playwright E2E tests
│
├── migrations/                      # Flask-Migrate database migrations
├── architecture/                    # This directory
│   ├── overview.md                 # This file
│   ├── core/                      # Core application docs
│   ├── routes/                    # Route layer docs
│   ├── services/                  # Services layer docs
│   ├── tasks/                     # Task processing docs
│   ├── infrastructure/           # Infrastructure docs
│   ├── frontend/                  # Frontend docs
│   └── testing/                  # Testing docs
│
├── scripts/                        # DevOps scripts
├── plans/                          # Review plans (indexed from plans/)
├── nginx/                         # Nginx configuration
├── docs/                          # OpenAPI spec
├── run.py                         # Entry point
├── config.toml                    # Configuration file
├── docker-compose.yml             # Container orchestration
├── Dockerfile                     # Container image
├── requirements.txt              # Python dependencies
├── package.json                  # Node dependencies
└── vite.config.js               # Vite bundler config
```

---

## Database Schema

```
┌─────────────────┐     ┌─────────────────┐
│      User       │────►│  AdminSession   │
└────────┬────────┘     └─────────────────┘
         │
         ├──────────────────────────────┐
         │                              │
         ▼                              ▼
┌─────────────────┐           ┌─────────────────┐
│  AdminAuditLog  │           │  PostRevision    │
└─────────────────┘           └─────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│      Post        │────►│      Tag        │◄────│    post_tags    │
└────────┬────────┘     └─────────────────┘     └─────────────────┘
         │
         ├──────────────┬───────────────┬───────────────┬───────────────┐
         │              │               │               │               │
         ▼              ▼               ▼               ▼               ▼
┌─────────────────┐ ┌─────────┐ ┌─────────────┐ ┌───────────┐ ┌─────────────┐
│   PageView      │ │ShareEvent│ │  Comment    │ │PostSeries │ │PostRevision │
└─────────────────┘ └─────────┘ └──────┬──────┘ └───────────┘ └─────────────┘
                                       │ (self-referential)
                                       ▼
                                   ┌─────────────┐
                                   │   Comment   │
                                   │  (parent_id)│
                                   └─────────────┘

┌─────────────────┐     ┌─────────────────┐
│   Subscriber     │     │     Series       │
└─────────────────┘     └────────┬────────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │  PostSeries │
                           └─────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Webhook     │────►│  WebhookEvent   │     │   SiteSettings  │
└─────────────────┘     └─────────────────┘     └─────────────────┘

┌─────────────────┐
│    ApiToken     │
│ (scoped access) │
└─────────────────┘
```

---

## Key Technologies

| Component | Technology |
|-----------|------------|
| Web Framework | Flask 3.1+ |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite (WAL) / PostgreSQL |
| ASGI Server | Granian (Rust) |
| Task Queue | Celery 5.x + Redis |
| Scheduler | APScheduler |
| Cache | Flask-Caching + Redis |
| Frontend Build | Vite 6.x |
| CSS | Vanilla CSS (no framework) |
| JavaScript | Vanilla JS (ES modules) |
| Templates | Jinja2 |
| Migration | Flask-Migrate |
| HTML Sanitizer | nh3 |
| 2FA | pyotp (TOTP) |
| QR Codes | qrcode |
| Image Processing | Pillow |
| S3 Client | boto3 |
| HTTP Client | requests |
| Monitoring | Prometheus (optional) |

---

## Related Documents

- [Implementation Plan](../plans/plan.md) - Consolidated implementation plan
- [AGENTS.md](../AGENTS.md) - Agent guidelines and conventions
- [DEPLOY.md](../DEPLOY.md) - Deployment documentation
- [USAGE.md](../USAGE.md) - Usage documentation