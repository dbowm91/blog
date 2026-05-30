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
| [Services Layer](#4-services-layer) | Business logic (backup, search, slug, tags) | [services/overview.md](services/overview.md), [services/backup.md](services/backup.md), [services/search.md](services/search.md), [services/slug.md](services/slug.md), [services/tag.md](services/tag.md) |
| [Task Processing](#5-task-processing) | Async (Celery) and scheduled (APScheduler) tasks | [tasks/overview.md](tasks/overview.md), [tasks/celery-tasks.md](tasks/celery-tasks.md), [tasks/scheduler.md](tasks/scheduler.md) |
| [Infrastructure](#6-infrastructure) | Search, email, storage, webhooks | [infrastructure/overview.md](infrastructure/overview.md), [infrastructure/search.md](infrastructure/search.md), [infrastructure/email.md](infrastructure/email.md), [infrastructure/storage.md](infrastructure/storage.md), [infrastructure/webhooks.md](infrastructure/webhooks.md) |
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

## 1. Core Application

**Source:** `app/__init__.py`, `app/config.py`, `app/extensions.py`, `app/filters.py`, `app/context_processors.py`

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
| Encryption | `app/services/encryption.py` | AES-256-GCM for TOTP secrets |
| Search | `app/services/search/` | Search provider abstraction (SQLite FTS5, PostgreSQL stub) |
| Slug | `app/services/slug.py` | Slug generation with collision handling |
| Tag | `app/services/tag.py` | Tag CRUD operations |
| Serialization | `app/services/serialization.py` | JSON export/import |

**Deep Dive:** [services/overview.md](services/overview.md), [services/backup.md](services/backup.md), [services/search.md](services/search.md), [services/slug.md](services/slug.md), [services/tag.md](services/tag.md)

---

### Search Provider Abstraction (`app/services/search/`)

The search module provides a provider-based abstraction for full-text search:

| File | Purpose |
|------|---------|
| `__init__.py` | `SearchProvider` ABC defining the interface |
| `sqlite.py` | FTS5 implementation with BM25 ranking |
| `postgresql.py` | PostgreSQL FTS stub (future implementation) |

**Key Functions:**
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

**Deep Dive:** [tasks/overview.md](tasks/overview.md), [tasks/celery-tasks.md](tasks/celery-tasks.md), [tasks/scheduler.md](tasks/scheduler.md)

---

## 6. Infrastructure

**Source:** `app/search.py`, `app/email.py`, `app/storage.py`, `app/webhooks.py`

**Purpose:** Supporting systems for core application operation.

| Component | Source | Purpose |
|-----------|--------|---------|
| Search | `app/search.py` | FTS5 full-text search |
| Email | `app/email.py` | SMTP email delivery |
| Storage | `app/storage.py` | Local/S3 storage abstraction |
| Webhooks | `app/webhooks.py` | Event-driven webhook delivery |
| Health Check | `app/routes/public/meta.py` | System health monitoring |

**Deep Dive:** [infrastructure/overview.md](infrastructure/overview.md), [infrastructure/search.md](infrastructure/search.md), [infrastructure/email.md](infrastructure/email.md), [infrastructure/storage.md](infrastructure/storage.md), [infrastructure/webhooks.md](infrastructure/webhooks.md)

---

## 7. Frontend

**Source:** `app/templates/`, `app/static/`

**Purpose:** User-facing JavaScript, CSS, and templates.

| Component | Source | Purpose |
|-----------|--------|---------|
| Static Assets | `app/static/` | JS modules (Vite-bundled), CSS, fonts, images |
| Templates | `app/templates/` | Jinja2 templates (admin, public, email) |

**Deep Dive:** [frontend/overview.md](frontend/overview.md), [frontend/templates.md](frontend/templates.md), [frontend/static-assets.md](frontend/static-assets.md)

---

## 8. Security Architecture

**Source:** `app/routes/admin/auth.py`, `app/services/encryption.py`, `app/middleware/rate_limit.py`

**Purpose:** Authentication, authorization, and protection against attacks.

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

**Deep Dive:** [deployment/security.md](deployment/security.md)

---

## 9. Deployment

**Source:** `Dockerfile`, `docker-compose.yml`, `nginx/`, `scripts/`

**Purpose:** Container orchestration, web server configuration, CI/CD.

| Component | Purpose |
|-----------|---------|
| Docker | Containerized deployment; health check includes 10s `start_period` before healthy status |
| Docker Compose | Multi-container orchestration |
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