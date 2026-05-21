# Architecture Overview

DevLog is a Flask-based blog CMS with SQLAlchemy ORM, full-text search, async task processing, and a Vue/Vite frontend.

This document provides a **birds-eye view** of all system components. Each section links to detailed documentation for deeper review.

---

## Component Index

### [Core Application](core/)
| Component | File | Description |
|-----------|------|-------------|
| [App Factory](core/app-factory.md) | `app/__init__.py` | Flask app initialization, extensions, middleware, security headers |
| [Configuration](core/configuration.md) | `app/config.py` | Configuration loading with env var override priority |
| [Models](core/models.md) | `app/models.py` | SQLAlchemy models for all database entities |

### [Routes & API](routes/)
| Component | File | Description |
|-----------|------|-------------|
| [Public Routes](routes/public-routes.md) | `app/routes/public/` | Blog pages, search, comments, subscription |
| [Admin Routes](routes/admin-routes.md) | `app/routes/admin/` | Dashboard, post editor, settings, analytics, 2FA |
| [API Routes](routes/api-routes.md) | `app/routes/api/` | REST API for posts, subscribers, stats (requires API key) |
| [RSS/Feeds](routes/rss-feeds.md) | `app/routes/rss.py` | RSS 2.0, Atom 1.0, JSON Feed 1.1 |

### [Services Layer](services/)
| Component | File | Description |
|-----------|------|-------------|
| [Backup Service](services/backup.md) | `app/services/backup.py` | Database backup with compression/encryption |
| [Serialization](services/serialization.md) | `app/services/serialization.py` | JSON export/import |
| [Slug Service](services/slug.md) | `app/services/slug.py` | Unique slug generation with collision handling |
| [Tag Service](services/tag.md) | `app/services/tag.md` | Tag CRUD and count management |
| [Search Abstraction](services/overview.md) | `app/services/search/` | SearchProvider ABC with SQLite FTS5 implementation |

### [Task Processing](tasks/)
| Component | File | Description |
|-----------|------|-------------|
| [Celery Tasks](tasks/celery-tasks.md) | `app/tasks.py` | Async tasks via Celery + Redis (images, newsletter, webhooks, email, backup) |
| [APScheduler](tasks/scheduler.md) | `app/scheduler.py` | In-process scheduled jobs (daily newsletter, cleanup, backup) |

### [Infrastructure](infrastructure/)
| Component | File | Description |
|-----------|------|-------------|
| [Search](infrastructure/search.md) | `app/search.py` | FTS5 full-text search with "Did you mean?" suggestions |
| [Email](infrastructure/email.md) | `app/email.py` | SMTP delivery with retry and exponential backoff |
| [Storage](infrastructure/storage.md) | `app/storage.py` | Local/S3 storage abstraction with responsive image variants |
| [Webhooks](infrastructure/webhooks.md) | `app/webhooks.py` | Webhook delivery with HMAC signing and SSRF protection |

### [Frontend](frontend/)
| Component | File | Description |
|-----------|------|-------------|
| [Static Assets](frontend/static-assets.md) | `app/static/` | CSS, JavaScript (Vite-bundled), uploads, fonts |
| [Templates](frontend/templates.md) | `app/templates/` | Jinja2 templates with context processors and filters |

### [Deployment & Operations](deployment/)
| Component | File | Description |
|-----------|------|-------------|
| [Docker](deployment/docker.md) | `Dockerfile`, `docker-compose.yml` | Container orchestration with Granian ASGI |
| [CI/CD](deployment/cicd.md) | `.github/workflows/` | GitHub Actions pipelines |
| [Security](deployment/security.md) | Various | Authentication, CSRF, sanitization, rate limiting |

### [Testing](testing/)
| Component | File | Description |
|-----------|------|-------------|
| [Test Suite](testing/test-suite.md) | `tests/` | Unit, integration, and Playwright E2E tests |

---

## System Architecture

```
                         ┌─────────────────┐
                         │      Nginx      │  TLS termination, static files
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │    Granian       │  ASGI server (Rust)
                         │  (Gunicorn/WSGI) │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
     ┌────────▼────────┐ ┌───────▼───────┐ ┌───────▼───────┐
     │  Celery Worker  │ │  APScheduler  │ │  Flask App    │
     │  (Redis)       │ │  (in-process)  │ │               │
     │                │ │               │ │  Blueprints:  │
     │  • images      │ │  • newsletter │ │  • admin      │
     │  • newsletter  │ │  • cleanup    │ │  • api        │
     │  • webhooks    │ │  • backup    │ │  • public     │
     │  • email       │ │               │ │  • rss        │
     │  • backup      │ │               │ │               │
     └────────────────┘ └───────────────┘ └───────────────┘
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  │
                         ┌────────▼────────┐
                         │  SQLite (WAL)    │  or PostgreSQL
                         │  / PostgreSQL    │
                         └─────────────────┘
```

---

## Directory Structure

```
blog/
├── app/
│   ├── __init__.py           # create_app() - app factory
│   ├── config.py             # Configuration loader
│   ├── models.py             # SQLAlchemy ORM models
│   ├── extensions.py         # Flask extension initialization
│   ├── utils.py              # Utilities (slug, email, SSRF)
│   ├── validators.py         # API input validation
│   ├── filters.py            # Jinja2 template filters
│   ├── context_processors.py # Template context injectors
│   ├── email.py              # SMTP email sending
│   ├── webhooks.py           # Webhook event creation/delivery
│   ├── storage.py            # Local/S3 storage abstraction
│   ├── search.py             # FTS5 full-text search
│   ├── tasks.py              # Celery async tasks
│   ├── scheduler.py          # APScheduler jobs
│   ├── celery_app.py         # Celery application config
│   │
│   ├── routes/
│   │   ├── admin/           # Admin blueprint
│   │   │   ├── auth.py      # Login, logout, 2FA, password reset
│   │   │   ├── posts/       # Post editor, list, revisions
│   │   │   ├── subscribers.py
│   │   │   ├── tags.py
│   │   │   ├── users.py
│   │   │   ├── sessions.py
│   │   │   ├── media.py
│   │   │   ├── backup.py
│   │   │   ├── analytics.py
│   │   │   ├── newsletter.py
│   │   │   ├── settings.py
│   │   │   ├── pages.py
│   │   │   ├── series.py
│   │   │   ├── audit.py
│   │   │   └── comments.py
│   │   ├── api/             # REST API blueprint
│   │   │   ├── auth.py      # require_api_key decorator
│   │   │   ├── posts.py     # Post CRUD
│   │   │   ├── subscribers.py
│   │   │   └── stats.py
│   │   ├── public/          # Public blueprint
│   │   │   ├── browse.py   # Home, archive, tag, search
│   │   │   ├── posts.py    # Post view, preview, share
│   │   │   ├── subscribe.py
│   │   │   ├── comments.py
│   │   │   └── meta.py     # Sitemap, robots.txt, health
│   │   ├── rss.py          # Atom, RSS, JSON feeds
│   │   └── errors.py       # 404, 500, 413 handlers
│   │
│   ├── services/
│   │   ├── backup.py        # Backup with encryption
│   │   ├── encryption.py    # AES-256-GCM for TOTP
│   │   ├── serialization.py # JSON export/import
│   │   ├── slug.py          # Slug generation
│   │   ├── tag.py           # Tag CRUD
│   │   └── search/          # Search abstraction
│   │       ├── __init__.py  # SearchProvider ABC
│   │       ├── sqlite.py   # FTS5 implementation
│   │       └── postgresql.py
│   │
│   ├── middleware/
│   │   └── rate_limit.py   # Per-admin rate limiting
│   │
│   └── static/
│       ├── css/            # Vanilla CSS
│       ├── js/             # ES modules (Vite-bundled)
│       ├── img/            # Static images
│       ├── fonts/           # Web fonts
│       └── uploads/        # User media
│
├── tests/                   # Pytest suite
│   ├── conftest.py
│   ├── shared_fixtures.py
│   ├── test_*.py           # Unit tests
│   └── e2e/                # Playwright E2E
│
├── migrations/               # Flask-Migrate
├── architecture/            # This directory
├── scripts/                 # DevOps scripts
├── plans/                   # Review plans
├── nginx/                   # Nginx config
├── run.py                   # Entry point
├── config.toml.example
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── package.json
└── vite.config.js
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

---

## Database Models

```
User
├── AdminSession (1:N)
├── PostRevision (1:N)
└── AdminAuditLog (1:N via actor_id)

Post
├── Tag (N:N via post_tags)
├── PostRevision (1:N)
├── PostSeries (1:N via post_series)
├── PageView (1:N)
├── ShareEvent (1:N)
├── Comment (1:N, threaded via parent_id)
└── User (user_id -> User.id)

Subscriber
Tag
Page
Series
SiteSettings (singleton)
Webhook
WebhookEvent
AdminAuditLog
Series
PostSeries (junction table)
Comment (self-referential via parent_id)
```

---

## Security Architecture

| Feature | Implementation |
|---------|----------------|
| **Authentication** | Session-based with optional TOTP 2FA |
| **2FA** | TOTP secrets encrypted with AES-256-GCM |
| **Backup Codes** | SHA-256 hashed, single-use |
| **CSRF** | Sliding window tokens (5 valid) |
| **API Auth** | X-API-Key header with HMAC timing-safe comparison |
| **Account Lockout** | 5 failed attempts → 15-minute lockout |
| **SSRF Protection** | URL validation against private IP ranges |
| **Webhook Signing** | HMAC-SHA256 with `X-Webhook-Signature` header |
| **XSS** | `nh3` HTML sanitizer, CSP headers |
| **Audit Logging** | `AdminAuditLog` for all admin actions |
| **Rate Limiting** | Flask-Limiter with Redis/memory backend |

---

## API Reference

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/posts` | List posts with pagination |
| GET | `/api/posts/<id>` | Get single post |
| POST | `/api/posts` | Create post |
| PUT | `/api/posts/<id>` | Update post |
| DELETE | `/api/posts/<id>` | Delete post |
| GET | `/api/subscribers` | List subscribers |
| GET | `/api/stats` | Analytics stats |

### Public Endpoints

| Route | Purpose |
|-------|---------|
| `/` | Homepage with recent posts |
| `/post/<slug>` | Single post view |
| `/page/<slug>` | Static page |
| `/tag/<name>` | Posts by tag |
| `/archive` | Full archive |
| `/search` | Search results |
| `/series/<slug>` | Series page |
| `/subscribe` | POST only - newsletter subscription |
| `/confirm/<token>` | Confirm subscription |
| `/unsubscribe/<token>` | Unsubscribe |
| `/preview/<id>` | Admin preview (requires session + HMAC) |
| `/atom`, `/rss`, `/json` | Feed endpoints |
| `/health` | Health check |

---

## Review Plans

Detailed review outputs for each module are stored in `plans/`:

| Module | Review Document |
|--------|-----------------|
| Core | `plans/core_review.md` |
| Services | `plans/services_review.md` |
| Routes | `plans/routes_review.md` |
| Tasks | `plans/tasks_review.md` |
| Infrastructure | `plans/infrastructure_review.md` |
| Frontend | `plans/frontend_review.md` |
| Deployment | `plans/deployment_review.md` |
| Testing | `plans/testing_review.md` |