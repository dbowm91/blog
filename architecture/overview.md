# Architecture Overview

DevLog is a Flask-based blog CMS with SQLAlchemy ORM, full-text search, async task processing, and a Vue/Vite frontend.

This document provides a **birds-eye view** of all system components and serves as an **index** to detailed architecture documents for each module. Each section links to deep-dive documentation for focused review.

---

## Quick Reference

| Layer | Component | File(s) | Deep Dive |
|-------|-----------|---------|-----------|
| **Core** | App Factory | `app/__init__.py` | [core/app-factory.md](core/app-factory.md) |
| | Configuration | `app/config.py` | [core/configuration.md](core/configuration.md) |
| | Models | `app/models.py` | [core/models.md](core/models.md) |
| **Routes** | Public | `app/routes/public/` | [routes/public-routes.md](routes/public-routes.md) |
| | Admin | `app/routes/admin/` | [routes/admin-routes.md](routes/admin-routes.md) |
| | API | `app/routes/api/` | [routes/api-routes.md](routes/api-routes.md) |
| | Feeds | `app/routes/rss.py` | [routes/rss-feeds.md](routes/rss-feeds.md) |
| **Services** | Backup | `app/services/backup.py` | [services/backup.md](services/backup.md) |
| | Search | `app/services/search/` | [services/overview.md](services/overview.md) |
| | Slug | `app/services/slug.py` | [services/slug.md](services/slug.md) |
| | Tag | `app/services/tag.py` | [services/tag.md](services/tag.md) |
| | Serialization | `app/services/serialization.py` | [services/serialization.md](services/serialization.md) |
| **Tasks** | Celery | `app/tasks.py` | [tasks/celery-tasks.md](tasks/celery-tasks.md) |
| | APScheduler | `app/scheduler.py` | [tasks/scheduler.md](tasks/scheduler.md) |
| **Infrastructure** | Search | `app/search.py` | [infrastructure/search.md](infrastructure/search.md) |
| | Email | `app/email.py` | [infrastructure/email.md](infrastructure/email.md) |
| | Storage | `app/storage.py` | [infrastructure/storage.md](infrastructure/storage.md) |
| | Webhooks | `app/webhooks.py` | [infrastructure/webhooks.md](infrastructure/webhooks.md) |
| **Frontend** | Static Assets | `app/static/` | [frontend/static-assets.md](frontend/static-assets.md) |
| | Templates | `app/templates/` | [frontend/templates.md](frontend/templates.md) |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               Clients                                        │
│                    (Browser, API Clients, RSS Readers)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Nginx (TLS Termination)                            │
│                    Static Files, Load Balancing, Brotli                     │
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
│   Celery Worker │     │       Redis         │     │      Redis       │
│   (Redis Queue) │◄────│  (Broker + Cache)  │────►│  (Rate Limits)   │
│                 │     │                     │     │                  │
│  • images       │     │  Queues:           │     │                  │
│  • newsletter   │     │  • images          │     │                  │
│  • webhooks     │     │  • newsletter      │     │                  │
│  • email        │     │  • webhooks        │     │                  │
│  • backup       │     │  • email           │     │                  │
│                 │     │  • backup          │     │                  │
└─────────────────┘     └─────────────────────┘     └─────────────────┘
          │                         │                         │
          └─────────────────────────┼─────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SQLite (WAL) / PostgreSQL                             │
│                                                                              │
│  Tables: users, posts, tags, subscribers, page_views, share_events,           │
│          admin_sessions, site_settings, pages, post_revisions,                │
│          webhooks, webhook_events, series, post_series, comments,             │
│          admin_audit_logs                                                    │
│                                                                              │
│  FTS5: posts_fts (full-text search virtual table)                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
blog/
├── app/                              # Main application package
│   ├── __init__.py                   # create_app() - Flask app factory
│   ├── config.py                     # Configuration loading from TOML + env
│   ├── models.py                     # SQLAlchemy ORM models (15 models)
│   ├── extensions.py                 # Flask extensions (db, login_manager, migrate)
│   ├── utils.py                      # Utilities (slug, UTCDateTime, SSRF)
│   ├── validators.py                 # API input validation
│   ├── filters.py                    # Jinja2 template filters
│   ├── context_processors.py          # Template context injectors
│   ├── email.py                      # SMTP email sending
│   ├── webhooks.py                   # Webhook event creation/delivery
│   ├── storage.py                    # Local/S3 storage abstraction
│   ├── search.py                     # FTS5 full-text search
│   ├── tasks.py                      # Celery async tasks
│   ├── scheduler.py                  # APScheduler jobs
│   ├── celery_app.py                 # Celery configuration
│   ├── csrf.py                       # CSRF token validation
│   ├── page_view_buffer.py           # Buffered page view writes
│   ├── tag_cache.py                  # Tag count caching
│   ├── backup_integrity.py           # Backup verification
│   ├── webhook_encryption.py         # Webhook secret encryption
│   ├── backup_encryption.py          # Backup file encryption
│   ├── markdown_config.py            # Markdown processing config
│   ├── transaction.py                # Transaction helpers
│   ├── csv_utils.py                  # CSV export utilities
│   ├── base62.py                     # Post ID encoding
│   │
│   ├── routes/                       # Route blueprints
│   │   ├── __init__.py
│   │   ├── admin/                    # Admin blueprint
│   │   │   ├── __init__.py          # Blueprint + auth decorators
│   │   │   ├── auth.py              # Login, logout, 2FA, password reset
│   │   │   ├── posts/               # Post management
│   │   │   │   ├── __init__.py      # Registers routes
│   │   │   │   ├── manage.py        # CRUD operations
│   │   │   │   ├── editor.py        # Post editor
│   │   │   │   └── revisions.py     # Post revisions
│   │   │   ├── subscribers.py       # Subscriber management
│   │   │   ├── tags.py              # Tag management
│   │   │   ├── users.py             # User management
│   │   │   ├── sessions.py          # Admin session management
│   │   │   ├── media.py             # Media library
│   │   │   ├── backup.py            # Backup/restore
│   │   │   ├── analytics.py          # Analytics dashboard
│   │   │   ├── newsletter.py         # Newsletter sending
│   │   │   ├── settings.py          # Site settings
│   │   │   ├── pages.py             # Static pages
│   │   │   ├── series.py             # Post series
│   │   │   ├── audit.py             # Audit log viewer
│   │   │   ├── comments.py          # Comment moderation
│   │   │   └── helpers/             # Shared admin utilities
│   │   │       ├── __init__.py
│   │   │       ├── analytics.py
│   │   │       ├── dashboard.py
│   │   │       ├── posts.py
│   │   │       ├── images.py
│   │   │       ├── slug.py
│   │   │       ├── tags.py
│   │   │       └── shared.py
│   │   ├── api/                      # REST API blueprint
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # require_api_key decorator
│   │   │   ├── posts.py             # Post CRUD
│   │   │   ├── subscribers.py       # Subscriber endpoints
│   │   │   └── stats.py             # Analytics stats
│   │   ├── public/                  # Public-facing blueprint
│   │   │   ├── __init__.py
│   │   │   ├── browse.py            # Home, archive, tag pages
│   │   │   ├── posts.py             # Post view, preview, share
│   │   │   ├── subscribe.py         # Newsletter subscription
│   │   │   ├── comments.py           # Comment submission
│   │   │   └── meta.py              # Sitemap, robots.txt, health
│   │   ├── rss.py                   # Atom, RSS, JSON feeds
│   │   └── errors.py                # 404, 500, 413 handlers
│   │
│   ├── services/                     # Business logic services
│   │   ├── backup.py                # Backup with compression/encryption
│   │   ├── encryption.py            # AES-256-GCM for TOTP secrets
│   │   ├── serialization.py         # JSON export/import
│   │   ├── slug.py                  # Slug generation
│   │   ├── tag.py                   # Tag CRUD
│   │   └── search/                  # Search abstraction
│   │       ├── __init__.py         # SearchProvider ABC
│   │       ├── sqlite.py           # FTS5 implementation
│   │       └── postgresql.py       # PostgreSQL FTS (stub)
│   │
│   ├── middleware/                   # WSGI middleware
│   │   └── rate_limit.py           # Admin rate limiting
│   │
│   └── static/                       # Frontend assets
│       ├── css/                     # Stylesheets
│       ├── js/                     # JavaScript (Vite-bundled)
│       ├── img/                    # Static images
│       ├── fonts/                   # Web fonts
│       └── uploads/                # User media uploads
│
├── tests/                            # Test suite
│   ├── conftest.py                  # Pytest configuration
│   ├── shared_fixtures.py            # Shared fixtures
│   ├── test_*.py                    # Unit/integration tests
│   └── e2e/                        # Playwright E2E tests
│
├── migrations/                       # Flask-Migrate database migrations
├── architecture/                     # This directory
│   ├── overview.md                  # This file
│   ├── core/                        # Core application docs
│   ├── routes/                      # Route layer docs
│   ├── services/                    # Services layer docs
│   ├── tasks/                       # Task processing docs
│   ├── infrastructure/              # Infrastructure docs
│   ├── frontend/                    # Frontend docs
│   ├── deployment/                  # Deployment docs
│   ├── plans/                       # Review plans
│   └── testing/                     # Testing docs
│
├── scripts/                         # DevOps scripts
├── plans/                          # Review plans (indexed from plans/)
├── nginx/                          # Nginx configuration
├── docs/                           # OpenAPI spec
├── run.py                          # Entry point
├── config.toml                     # Configuration file
├── docker-compose.yml              # Container orchestration
├── Dockerfile                      # Container image
├── requirements.txt                # Python dependencies
├── package.json                    # Node dependencies
└── vite.config.js                  # Vite bundler config
```

---

## Core Application

### App Factory (`app/__init__.py`)

The `create_app()` function initializes the Flask application:

1. **Configuration Loading**: Loads `config.toml`, validates env vars, sets up SQLAlchemy URI
2. **Extension Initialization**: db, login_manager, migrate, limiter, cache, compress
3. **Database Setup**: WAL mode, busy timeout, connection pool (non-SQLite)
4. **Blueprint Registration**: public, admin, rss, errors, api
5. **Middleware**: ProxyFix, CSP headers, Prometheus metrics
6. **Before/After Request**: CSRF validation, session timeout, security headers
7. **Scheduler Initialization**: APScheduler for background jobs
8. **Page View Buffer**: Buffered analytics writes

**Key Files:**
- [core/app-factory.md](core/app-factory.md) - Full app initialization flow
- [core/configuration.md](core/configuration.md) - Configuration system

### Models (`app/models.py`)

| Model | Purpose |
|-------|---------|
| `User` | Admin users with TOTP 2FA, backup codes |
| `Post` | Blog posts with revisions, tags, series |
| `Tag` | Post categorization |
| `Subscriber` | Newsletter subscribers |
| `Page` | Static pages |
| `PageView` | Analytics page views |
| `ShareEvent` | Social sharing tracking |
| `AdminSession` | Admin login sessions |
| `SiteSettings` | Singleton site configuration |
| `Webhook` | Webhook endpoints |
| `WebhookEvent` | Webhook delivery events |
| `Series` | Post series groupings |
| `PostSeries` | Series-post junction |
| `Comment` | Threaded comments |
| `AdminAuditLog` | Security audit trail |

**Relationships:**
- `User` → `AdminSession` (1:N)
- `Post` → `Tag` (N:N via `post_tags`)
- `Post` → `PostRevision` (1:N)
- `Post` → `Series` (N:N via `post_series`)
- `Post` → `PageView`, `ShareEvent`, `Comment` (1:N)
- `Comment` → `Comment` (self-referential via `parent_id`)

**Key Files:**
- [core/models.md](core/models.md) - Model relationships and details

---

## Routes Layer

### Public Routes (`app/routes/public/`)

Handles all public-facing pages:

| Route | File | Purpose |
|-------|------|---------|
| `/` | browse.py | Homepage with recent posts |
| `/post/<slug>` | posts.py | Single post view |
| `/page/<slug>` | browse.py | Static pages |
| `/tag/<name>` | browse.py | Posts by tag |
| `/archive` | browse.py | Full archive |
| `/search` | browse.py | Search results |
| `/series/<slug>` | browse.py | Series page |
| `/subscribe` | subscribe.py | POST only - subscription |
| `/confirm/<token>` | subscribe.py | Confirm subscription |
| `/unsubscribe/<token>` | subscribe.py | Unsubscribe |
| `/preview/<id>` | posts.py | Admin preview (HMAC + session) |
| `/sitemap.xml` | meta.py | SEO sitemap |
| `/robots.txt` | meta.py | Robots directive |
| `/health` | meta.py | Health check |

**Key Files:**
- [routes/public-routes.md](routes/public-routes.md) - Public route details

### Admin Routes (`app/routes/admin/`)

Authentication-gated admin panel:

| Section | File | Purpose |
|---------|------|---------|
| Dashboard | helpers/dashboard.py | Overview stats |
| Auth | auth.py | Login, logout, 2FA, password reset |
| Posts | posts/* | Post CRUD, editor, revisions |
| Tags | tags.py | Tag management |
| Subscribers | subscribers.py | Subscriber list, export |
| Users | users.py | User management, promotion |
| Sessions | sessions.py | Admin session tracking |
| Media | media.py | Image upload, library |
| Backup | backup.py | Backup, restore |
| Analytics | analytics.py | Traffic analytics |
| Newsletter | newsletter.py | Send newsletters |
| Settings | settings.py | Site settings, themes |
| Pages | pages.py | Static pages |
| Series | series.py | Post series |
| Audit | audit.py | Audit log viewer |
| Comments | comments.py | Comment moderation |

**Key Files:**
- [routes/admin-routes.md](routes/admin-routes.md) - Admin route details

### API Routes (`app/routes/api/`)

REST API for programmatic access:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/posts` | GET | List posts (pagination, search) |
| `/api/posts/<id>` | GET | Single post |
| `/api/posts` | POST | Create post |
| `/api/posts/<id>` | PUT | Update post |
| `/api/posts/<id>` | DELETE | Delete post |
| `/api/subscribers` | GET | List subscribers |
| `/api/subscribers` | POST | Add subscriber |
| `/api/stats` | GET | Analytics stats |

**Authentication:** X-API-Key header with HMAC timing-safe comparison

**Key Files:**
- [routes/api-routes.md](routes/api-routes.md) - API route details

### RSS/Feeds (`app/routes/rss.py`)

| Endpoint | Format | Purpose |
|----------|--------|---------|
| `/atom` | Atom 1.0 | Full-content Atom feed |
| `/rss` | RSS 2.0 | RSS feed |
| `/json` | JSON Feed 1.1 | JSON feed |

**Key Files:**
- [routes/rss-feeds.md](routes/rss-feeds.md) - Feed implementation details

---

## Services Layer

### Backup Service (`app/services/backup.py`)

Centralized backup logic supporting:
- Raw SQLite backup via `sqlite3.backup()` API
- Optional gzip compression
- Optional AES-256-GCM encryption (via `app/backup_encryption.py`)
- Retention policy (keeps N most recent)

**Note:** There are two backup implementations:
1. `create_backup()` - Celery task, supports encryption/compression
2. `run_daily_backup()` in scheduler - No encryption/compression

**Key Files:**
- [services/backup.md](services/backup.md) - Backup service details

### Search Abstraction (`app/services/search/`)

Abstract `SearchProvider` base class with implementations:

| Provider | File | Status |
|----------|------|--------|
| SQLite FTS5 | sqlite.py | Implemented |
| PostgreSQL FTS | postgresql.py | Stub |

Factory function `get_search_provider()` selects based on `SEARCH_PROVIDER` config.

**Key Files:**
- [services/overview.md](services/overview.md) - Search architecture

### Slug Service (`app/services/slug.py`)

Unique slug generation with collision handling:
- Max 100 collision attempts before falling back to UUID suffix
- Uses `app/utils.generate_slug()` for base slugify

**Key Files:**
- [services/slug.md](services/slug.md) - Slug generation details

### Tag Service (`app/services/tag.py`)

Tag CRUD operations with count management.

**Key Files:**
- [services/tag.md](services/tag.md) - Tag service details

### Serialization (`app/services/serialization.py`)

JSON export/import for data portability.

**Key Files:**
- [services/serialization.md](services/serialization.md) - Serialization details

---

## Task Processing

### Celery Tasks (`app/tasks.py`)

Async task queue with Redis broker:

| Task | Queue | Purpose |
|------|-------|---------|
| `generate_image_variants` | images | Generate 400w/800w/1200w WebP variants |
| `send_newsletter_task` | newsletter | Send newsletter to subscribers |
| `deliver_webhook_task` | webhooks | Deliver webhook events |
| `send_confirmation_task` | email | Send confirmation emails |
| `send_password_reset_task` | email | Send password reset emails |
| `run_backup_task` | backup | Async database backup |

**Retry Policy:** max_retries=3 with exponential backoff

**Key Files:**
- [tasks/celery-tasks.md](tasks/celery-tasks.md) - Celery task details

### APScheduler (`app/scheduler.py`)

In-process scheduled jobs with file locking:

| Job | Schedule | Purpose |
|-----|----------|---------|
| `send_daily_newsletter` | Daily at `NEWSLETTER_SEND_TIME` | Auto-send newsletter |
| `cleanup_expired_subscribers` | Every 5 minutes | Remove unconfirmed expired |
| `publish_scheduled_posts` | Every 5 minutes | Auto-publish scheduled posts |
| `run_daily_backup` | Daily at 02:00 | Daily database backup |

**Multi-Worker Limitation:** FileLock only works on single machine. See [tasks/scheduler.md](tasks/scheduler.md).

**Key Files:**
- [tasks/scheduler.md](tasks/scheduler.md) - APScheduler details

---

## Infrastructure

### Full-Text Search (`app/search.py`)

SQLite FTS5 implementation with:
- BM25 ranking
- "Did you mean?" suggestions via difflib
- Search snippet highlighting
- Automatic LIKE fallback if FTS unavailable

**Tables:**
- `posts_fts` - FTS5 virtual table
- `posts_fts_vocab` - FTS5 vocabulary table

**Key Files:**
- [infrastructure/search.md](infrastructure/search.md) - Search details

### Email (`app/email.py`)

SMTP email delivery with:
- Confirmation emails for new subscribers
- Password reset emails
- Newsletter delivery with retry logic
- Exponential backoff on failures

**Key Files:**
- [infrastructure/email.md](infrastructure/email.md) - Email system details

### Storage (`app/storage.py`)

Storage abstraction with backends:

| Backend | Class | Configuration |
|---------|-------|---------------|
| Local | `LocalStorageBackend` | `STORAGE_BACKEND=local` (default) |
| S3 | `S3StorageBackend` | `STORAGE_BACKEND=s3` |

S3 requires: `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`

**Key Files:**
- [infrastructure/storage.md](infrastructure/storage.md) - Storage details

### Webhooks (`app/webhooks.py`)

Event-driven webhook delivery:
- `create_webhook_event()` - Queue webhook event
- `deliver_webhook_task` - Celery task for delivery
- HMAC-SHA256 signing with `X-Webhook-Signature` header
- SSRF protection via `is_safe_webhook_url()`
- Secret encryption at rest (AES-256-GCM)

**Key Files:**
- [infrastructure/webhooks.md](infrastructure/webhooks.md) - Webhook details

---

## Frontend

### Static Assets (`app/static/`)

| Directory | Purpose |
|-----------|---------|
| css/ | Stylesheets (vanilla CSS, no framework) |
| js/ | JavaScript ES modules (Vite-bundled) |
| img/ | Static images |
| fonts/ | Web fonts |
| uploads/ | User-uploaded media |

**Build:** Vite 6.x with code splitting and `manualChunks`

**Key Files:**
- [frontend/static-assets.md](frontend/static-assets.md) - Frontend asset details

### Templates (`app/templates/`)

Jinja2 templates with:
- Admin templates (login, dashboard, editor)
- Public templates (base, post, page, archive)
- Email templates (confirm, newsletter, password_reset)
- Context processors for global template variables
- Custom filters for formatting

**Key Files:**
- [frontend/templates.md](frontend/templates.md) - Template details

---

## Security Architecture

| Feature | Implementation |
|---------|----------------|
| **Authentication** | Session-based with optional TOTP 2FA |
| **2FA** | TOTP secrets encrypted with AES-256-GCM |
| **Backup Codes** | SHA-256 hashed, single-use (8 codes) |
| **CSRF** | Sliding window tokens (5 valid) |
| **API Auth** | X-API-Key header with HMAC timing-safe comparison |
| **Account Lockout** | 5 failed attempts → 15-minute lockout |
| **SSRF Protection** | URL validation against private IP ranges |
| **Webhook Signing** | HMAC-SHA256 with `X-Webhook-Signature` header |
| **XSS** | `nh3` HTML sanitizer, CSP headers |
| **Audit Logging** | `AdminAuditLog` for all admin actions |
| **Rate Limiting** | Flask-Limiter with Redis/memory backend |
| **Session Fixation** | `session.clear()` before `login_user()` |

**Key Files:**
- [deployment/security.md](deployment/security.md) - Security details

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
```

---

## Review Plans

For focused deep-dives into specific modules, see the review plans:

| Module | Review Document |
|--------|-----------------|
| Core | [plans/core_review.md](../plans/core_review.md) |
| Services | [plans/services_review.md](../plans/services_review.md) |
| Routes | [plans/routes_review.md](../plans/routes_review.md) |
| Tasks | [plans/tasks_review.md](../plans/tasks_review.md) |
| Infrastructure | [plans/infrastructure_review.md](../plans/infrastructure_review.md) |
| Frontend | [plans/frontend_review.md](../plans/frontend_review.md) |
| Deployment | [plans/deployment_review.md](../plans/deployment_review.md) |
| Testing | [plans/testing_review.md](../plans/testing_review.md) |

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
