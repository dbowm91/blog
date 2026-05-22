# Architecture Overview

DevLog is a Flask-based blog CMS with SQLAlchemy ORM, full-text search, async task processing, and Vue/Vite frontend.

This document provides a **birds-eye view** of all system components and serves as an **index** to detailed architecture documents for focused review.

---

## Quick Reference

| Layer | Component | Source | Deep Dive |
|-------|-----------|--------|-----------|
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
│                    (Browser, API Clients, RSS Readers)                        │
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
│          admin_audit_logs                                                    │
│                                                                              │
│  FTS5: posts_fts (full-text search virtual table)                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

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
│   │   ├── tag_cache.py           # Tag count caching with TTL
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
│       └── uploads/               # User media uploads
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
│   ├── deployment/               # Deployment docs
│   ├── plans/                     # Review plans
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

## Discrete Modules

### 1. Core Application

**Purpose:** Initialize Flask app, configure extensions, register blueprints, set up middleware.

| Component | File | Purpose |
|-----------|------|---------|
| App Factory | `app/__init__.py` | `create_app()` - Flask app factory |
| Configuration | `app/config.py` | TOML loading, env overrides, validation |
| Models | `app/models.py` | 17 SQLAlchemy models |
| Extensions | `app/extensions.py` | SQLAlchemy, LoginManager, Migrate |
| Filters | `app/filters.py` | Jinja2 template filters |
| Context Processors | `app/context_processors.py` | Template global variables |

**Key Files:**
- [core/app-factory.md](core/app-factory.md) - Full app initialization flow
- [core/configuration.md](core/configuration.md) - Configuration system
- [core/models.md](core/models.md) - Model relationships and details

---

### 2. Routes Layer

**Purpose:** Handle HTTP requests and responses for public, admin, and API access.

| Module | Source | Purpose |
|--------|--------|---------|
| Public Routes | `app/routes/public/` | Blog pages, posts, subscriptions |
| Admin Routes | `app/routes/admin/` | Dashboard, CRUD operations |
| API Routes | `app/routes/api/` | REST API for programmatic access |
| RSS/Feeds | `app/routes/rss.py` | Atom, RSS, JSON feeds |
| Error Handlers | `app/routes/errors.py` | 404, 500, 413 responses |

**Key Files:**
- [routes/public-routes.md](routes/public-routes.md) - Public route details
- [routes/admin-routes.md](routes/admin-routes.md) - Admin route details
- [routes/api-routes.md](routes/api-routes.md) - API route details
- [routes/rss-feeds.md](routes/rss-feeds.md) - Feed implementation details

---

### 3. Services Layer

**Purpose:** Business logic封装，abstraction层 for reusable functionality.

| Service | Source | Purpose |
|---------|--------|---------|
| Backup | `app/services/backup.py` | Database backup with compression/encryption |
| Encryption | `app/services/encryption.py` | AES-256-GCM for TOTP secrets |
| Search | `app/services/search/` | Search provider abstraction (SQLite FTS5, PostgreSQL stub) |
| Slug | `app/services/slug.py` | Slug generation with collision handling |
| Tag | `app/services/tag.py` | Tag CRUD with caching |
| Tag Cache | `app/tag_cache.py` | Tag count caching with TTL |
| Serialization | `app/services/serialization.py` | JSON export/import |

**Key Files:**
- [services/backup.md](services/backup.md) - Backup service details
- [services/overview.md](services/overview.md) - Search architecture
- [services/slug.md](services/slug.md) - Slug generation details
- [services/tag.md](services/tag.md) - Tag service details
- [services/serialization.md](services/serialization.md) - Serialization details

---

### 4. Task Processing

**Purpose:** Handle asynchronous and scheduled background work.

| System | Source | Purpose |
|--------|--------|---------|
| Celery | `app/tasks.py` | Async task queue with Redis broker |
| APScheduler | `app/scheduler.py` | In-process scheduled jobs |

**Celery Queues:**
| Queue | Tasks |
|-------|-------|
| `images` | Image variant generation |
| `newsletter` | Newsletter delivery |
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

**Key Files:**
- [tasks/celery-tasks.md](tasks/celery-tasks.md) - Celery task details
- [tasks/scheduler.md](tasks/scheduler.md) - APScheduler details

---

### 5. Infrastructure

**Purpose:** Supporting systems for core application operation.

| Component | Source | Purpose |
|-----------|--------|---------|
| Search | `app/search.py` | FTS5 full-text search |
| Email | `app/email.py` | SMTP email delivery |
| Storage | `app/storage.py` | Local/S3 storage abstraction |
| Webhooks | `app/webhooks.py` | Event-driven webhook delivery |

**Key Files:**
- [infrastructure/search.md](infrastructure/search.md) - Search details
- [infrastructure/email.md](infrastructure/email.md) - Email system details
- [infrastructure/storage.md](infrastructure/storage.md) - Storage details
- [infrastructure/webhooks.md](infrastructure/webhooks.md) - Webhook details

---

### 6. Frontend

**Purpose:** User-facing JavaScript, CSS, and templates.

| Component | Source | Purpose |
|-----------|--------|---------|
| Static Assets | `app/static/` | JS modules, CSS, fonts, images |
| Templates | `app/templates/` | Jinja2 templates (admin, public, email) |

**Key Files:**
- [frontend/static-assets.md](frontend/static-assets.md) - Frontend asset details
- [frontend/templates.md](frontend/templates.md) - Template details

---

### 7. Data Models

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

**Model Relationships:**
- `User` → `AdminSession` (1:N)
- `Post` → `Tag` (N:N via `post_tags`)
- `Post` → `PostRevision` (1:N)
- `Post` → `Series` (N:N via `post_series`)
- `Post` → `PageView`, `ShareEvent`, `Comment` (1:N)
- `Comment` → `Comment` (self-referential via `parent_id`)

---

### 8. Security Architecture

| Feature | Implementation |
|---------|---------------|
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
| Core | [plans/core_review.md](plans/core_review.md) |
| Services | [plans/services_review.md](plans/services_review.md) |
| Routes | [plans/routes_review.md](plans/routes_review.md) |
| Tasks | [plans/tasks_review.md](plans/tasks_review.md) |
| Infrastructure | [plans/infrastructure_review.md](plans/infrastructure_review.md) |
| Frontend | [plans/frontend_review.md](plans/frontend_review.md) |
| Deployment | [plans/deployment_review.md](plans/deployment_review.md) |
| Testing | [plans/testing_review.md](plans/testing_review.md) |

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

(End of file - total 745 lines)