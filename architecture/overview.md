# Architecture Overview

This document provides a high-level overview of the DevLog blogging platform and serves as an index for detailed documentation of each component.

## System Summary

DevLog is a Flask-based blogging platform with:
- SQLAlchemy ORM (SQLite default, PostgreSQL supported)
- FTS5 full-text search with bm25 ranking
- Multi-admin sessions with 2FA authentication
- Newsletter scheduling with async delivery via Celery
- Custom CSS theming and syntax highlighting themes
- Post revisions with diff tracking
- Threaded comments system
- Audit logging for admin actions
- Webhook delivery with SSRF protection
- Responsive image variants (WebP at 400w, 800w, 1200w)
- Docker deployment with Granian ASGI server

---

## Component Index

### [Core Application](core/)
| Component | File | Description |
|-----------|------|-------------|
| [App Factory](core/app-factory.md) | `app/__init__.py` | Flask app initialization, extensions, middleware, security headers |
| [Configuration](core/configuration.md) | `app/config.py`, `config.toml` | Configuration loading with env var override priority |
| [Models](core/models.md) | `app/models.py` | SQLAlchemy models for all database entities |
| Extensions | `app/extensions.py` | SQLAlchemy, Flask-Login, Migrate initialization |

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
| [Tag Service](services/tag.md) | `app/services/tag.py` | Tag CRUD and count management |
| [Encryption](services/encryption.md) | `app/services/encryption.py` | AES-256-GCM encryption for TOTP secrets |
| [Search Abstraction](services/search/) | `app/services/search/` | SearchProvider ABC with SQLite FTS5 implementation |

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

### [Review Plans](plans/)
| Component | File | Description |
|-----------|------|-------------|
| Review Plans | `plans/review/*.md` | Detailed review outputs for each module |

---

## Directory Structure

```
blog/
├── app/
│   ├── __init__.py              # App factory (create_app)
│   ├── config.py                # Configuration loader
│   ├── models.py                # SQLAlchemy ORM models
│   ├── extensions.py            # Flask extension initialization
│   ├── utils.py                 # Utility functions (slug, email validation, SSRF)
│   ├── validators.py            # API input validation
│   ├── filters.py               # Jinja2 template filters
│   ├── context_processors.py    # Template context injectors
│   ├── csrf.py                  # CSRF token generation/validation
│   ├── email.py                 # Email sending
│   ├── webhooks.py              # Webhook event creation/delivery
│   ├── tasks.py                 # Celery async tasks
│   ├── scheduler.py             # APScheduler jobs
│   ├── storage.py               # Storage abstraction
│   ├── search.py                # FTS5 full-text search
│   ├── page_view_buffer.py      # High-traffic page view buffering
│   │
│   ├── routes/
│   │   ├── admin/               # Admin dashboard blueprint
│   │   │   ├── auth.py          # Login, logout, 2FA
│   │   │   ├── posts/           # Post editor, list, revisions
│   │   │   ├── subscribers.py   # Subscriber management
│   │   │   ├── tags.py          # Tag CRUD
│   │   │   ├── users.py         # User management
│   │   │   ├── sessions.py      # Session monitoring
│   │   │   ├── media.py         # Media upload
│   │   │   ├── backup.py        # Backup/restore
│   │   │   ├── analytics.py     # Dashboard analytics
│   │   │   ├── newsletter.py    # Newsletter preview/send
│   │   │   ├── settings.py      # Theme, custom CSS
│   │   │   ├── pages.py         # Static page editor
│   │   │   ├── series.py        # Series management
│   │   │   ├── audit.py         # Audit log viewer
│   │   │   └── comments.py      # Comment moderation
│   │   ├── api/                 # REST API blueprint
│   │   │   ├── auth.py          # API key authentication
│   │   │   ├── posts.py         # Post CRUD
│   │   │   ├── subscribers.py   # Subscriber management
│   │   │   └── stats.py         # Analytics stats
│   │   ├── public/              # Public-facing blueprint
│   │   │   ├── browse.py        # Home, archive, tag pages, search
│   │   │   ├── posts.py          # Post view, preview, share tracking
│   │   │   ├── subscribe.py     # Subscribe/confirm/unsubscribe
│   │   │   ├── comments.py      # Public comment submission
│   │   │   └── meta.py          # Sitemap, robots.txt
│   │   ├── rss.py               # Atom, RSS, JSON feeds
│   │   └── errors.py            # 404, 500, 413 handlers
│   │
│   ├── services/
│   │   ├── backup.py            # Backup service
│   │   ├── encryption.py        # AES-256-GCM encryption
│   │   ├── serialization.py      # JSON export/import
│   │   ├── slug.py              # Slug generation
│   │   ├── tag.py               # Tag service
│   │   └── search/              # Search abstraction
│   │       ├── __init__.py      # SearchProvider ABC
│   │       ├── sqlite.py        # SQLite FTS5 provider
│   │       └── postgresql.py    # PostgreSQL stub
│   │
│   ├── middleware/
│   │   └── rate_limit.py        # Per-admin rate limiting
│   │
│   ├── static/
│   │   ├── css/                 # Stylesheets
│   │   ├── js/                  # JavaScript (Vite-bundled)
│   │   │   ├── main.js         # Core public JS
│   │   │   ├── admin/          # Admin-specific JS
│   │   │   ├── public/         # Public-facing JS
│   │   │   └── lib/             # Third-party libraries
│   │   ├── img/                 # Static images
│   │   ├── fonts/               # Font files
│   │   └── uploads/             # User-uploaded media
│   │
│   └── templates/               # Jinja2 HTML templates
│       ├── base.html            # Base template
│       ├── index.html           # Homepage
│       ├── post.html            # Single post
│       ├── admin/               # Admin templates
│       ├── email/                # Email templates
│       └── public/               # Public preview templates
│
├── tests/                       # Test suite
│   ├── conftest.py             # Pytest fixtures
│   ├── shared_fixtures.py      # Shared test utilities
│   ├── test_*.py               # Unit/integration tests
│   ├── e2e/                    # Playwright E2E tests
│   └── benchmarks/             # Performance benchmarks
│
├── migrations/                  # Flask-Migrate database migrations
├── architecture/               # Architecture documentation (this directory)
├── docs/                        # OpenAPI specification
├── scripts/                     # DevOps scripts
├── plans/                       # Development roadmap and review plans
├── instance/                    # Instance-specific files (database, backups)
├── backups/                     # Backup storage
├── nginx/                       # Nginx configuration
├── run.py                      # Application entry point
├── backup.py                   # Root-level backup script
├── config.toml.example         # Configuration template
├── docker-compose.yml          # Docker services
├── Dockerfile                  # Container image
├── requirements.txt            # Python dependencies
├── package.json                 # npm dependencies
└── vite.config.js              # Vite bundler configuration
```

---

## Request Flow

```
                    ┌─────────────────────────────────────────┐
                    │                  Nginx                   │
                    │         (TLS termination, static)        │
                    └──────────────────┬──────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │           Granian (ASGI)                 │
                    │         Python/Rust server                │
                    └──────────────────┬──────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                              Flask Application                                │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         Before Request Hooks                            │ │
│  │  • Request ID generation (g.request_id)                                  │ │
│  │  • CSP nonce generation (g.csp_nonce)                                   │ │
│  │  • CSRF validation for POST/PUT/DELETE                                   │ │
│  │  • Session timeout check (sliding expiration)                           │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                       │                                       │
│  ┌────────────────────────────────────▼────────────────────────────────────┐ │
│  │                          Blueprint Routing                              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │ │
│  │  │  admin   │  │   api    │  │  public  │  │   rss    │  │  errors  │  │ │
│  │  │  /admin  │  │   /api   │  │    /     │  │  /feed   │  │ handlers │  │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                       │                                       │
│  ┌────────────────────────────────────▼────────────────────────────────────┐ │
│  │                         Route Handler                                    │ │
│  │                                    │                                     │ │
│  │                      ┌─────────────▼─────────────┐                       │ │
│  │                      │      Service Layer        │                       │ │
│  │                      │  backup, slug, search,    │                       │ │
│  │                      │  tag, email, webhooks     │                       │ │
│  │                      └─────────────┬─────────────┘                       │ │
│  │                                    │                                     │ │
│  │                      ┌─────────────▼─────────────┐                       │ │
│  │                      │    SQLAlchemy ORM         │                       │ │
│  │                      └─────────────┬─────────────┘                       │ │
│  └────────────────────────────────────┼────────────────────────────────────┘ │
│                                       │                                       │
└───────────────────────────────────────┼───────────────────────────────────────┘
                                        │
                    ┌───────────────────▼───────────────────┐
                    │          SQLite / PostgreSQL            │
                    │           (WAL mode enabled)           │
                    └────────────────────────────────────────┘
```

### Async Operations

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              Celery Workers                                  │
│                                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                │
│  │  images queue  │  │ newsletter     │  │   webhooks     │                │
│  │  (Pillow)      │  │ queue         │  │   queue        │                │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘                │
│          │                   │                    │                          │
│  ┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐                │
│  │ Image variant  │  │ Newsletter    │  │ Webhook       │                │
│  │ generation     │  │ delivery      │  │ delivery      │                │
│  └────────────────┘  └────────────────┘  └────────────────┘                │
│                                                                              │
│  ┌────────────────┐  ┌────────────────┐                                     │
│  │  email queue   │  │  backup queue  │                                     │
│  │  (SMTP)        │  │  (sqlite3)      │                                     │
│  └───────┬────────┘  └───────┬────────┘                                     │
│          │                   │                                               │
│  ┌───────▼────────┐  ┌───────▼────────┐                                     │
│  │ Confirmation, │  │ Encrypted      │                                     │
│  │ password reset │  │ backup storage │                                     │
│  └────────────────┘  └────────────────┘                                     │
└──────────────────────────────────────────────────────────────────────────────┘
                              │
                              │ Redis (Broker)
                              │
┌─────────────────────────────▼─────────────────────────────────────────────┐
│                             APScheduler                                      │
│                                                                             │
│  • daily_newsletter (configurable time)                                     │
│  • cleanup_expired_subscribers (every 5 minutes)                            │
│  • publish_scheduled_posts (every 5 minutes)                                 │
│  • run_daily_backup (02:00 daily)                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Configuration Priority

Configuration values are resolved in the following order (highest to lowest):

1. **Environment variables** - For production and sensitive values
2. **`config.toml` file** - For environment-specific configuration
3. **Default values in `app/config.py`** - For all other settings

Example `config.toml`:

```toml
[app]
title = "DevLog"
posts_per_page = 10
session_lifetime_hours = 24

[admin]
username = "admin"

[email]
smtp_host = "smtp.example.com"
smtp_port = 587
from_address = "noreply@example.com"

[newsletter]
send_time = "08:00"
confirmation_expiry_hours = 48
```

---

## Database Models

```
User
├── admin_sessions (1:N)
└── (reverse lookups: user.posts, user.audit_logs NOT defined on User)

Post
├── tags (N:N via post_tags)
├── page_views (1:N)
├── share_events (1:N)
├── revisions (1:N via PostRevision)
├── comments (1:N, threaded via parent_id)
├── series_entries (1:N via PostSeries)
└── user (Post.user_id -> User.id)

Tag
Post
Subscriber
Page
Series
SiteSettings (singleton at id=1)
Webhook
WebhookEvent
AdminAuditLog
└── actor (AdminAuditLog.actor_id -> User.id)

Comment
├── parent (self-referential, remote_side=[id])
└── replies (back_populates="parent")
```

### Key Indexes

| Table | Index | Columns |
|-------|-------|---------|
| posts | ix_posts_published_created | (published, created_at) |
| posts | ix_posts_published_at | (published_at) |
| posts | ix_posts_newsletter_sent_at | (newsletter_sent_at) |
| posts | ix_posts_scheduled_publish_at | (scheduled_publish_at) |
| comments | ix_comments_post_approved | (post_id, approved) |
| subscribers | ix_subscribers_confirmed_unsubscribed | (confirmed, unsubscribed_at) |

---

## Security Architecture

| Feature | Implementation |
|---------|----------------|
| **Authentication** | Session-based with optional TOTP 2FA |
| **2FA** | TOTP secrets encrypted with AES-256-GCM |
| **Backup Codes** | SHA-256 hashed, single-use |
| **CSRF** | Sliding window tokens (5 valid) |
| **API Auth** | X-API-Key header with HMAC timing-safe comparison |
| **Session Fixation** | `session.clear()` before `login_user()` |
| **Account Lockout** | 5 failed attempts → 15-minute lockout |
| **IP Binding** | Optional `SESSION_IP_BINDING = "enforce"` |
| **SSRF Protection** | URL validation against private IP ranges |
| **Webhook Signing** | HMAC-SHA256 with `X-Webhook-Signature` header |
| **XSS** | `nh3` HTML sanitizer, CSP headers |
| **Audit Logging** | `AdminAuditLog` for all admin actions |
| **Rate Limiting** | Flask-Limiter with Redis/memory backend |
| **Password Hashing** | `werkzeug.security.generate_password_hash` |

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
| WSGI | Gunicorn/Whitenoise (fallback) |

---

## API Reference

### Authentication

**Admin Session:**
- `POST /admin/login` - Username/password login
- `POST /admin/logout` - End session
- `GET /admin/2fa/setup` - Initiate TOTP setup
- `POST /admin/2fa/verify` - Verify TOTP code
- `GET /admin/2fa/backup-codes` - Generate backup codes
- `POST /admin/2fa/disable` - Disable 2FA

**API Key:**
- All `/api/*` routes require `X-API-Key` header

### REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/posts` | List posts with pagination |
| GET | `/api/posts/<id>` | Get single post |
| POST | `/api/posts` | Create post |
| PUT | `/api/posts/<id>` | Update post (triggers webhook on publish state change) |
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
| `/subscribe` | POST only - subscribe to newsletter |
| `/confirm/<token>` | Confirm subscription |
| `/unsubscribe/<token>` | Unsubscribe |
| `/preview/<id>` | Admin preview (requires session + HMAC) |
| `/atom`, `/rss`, `/json` | Feed endpoints |

---

## See Also

- [Review Plan](review_plan.md) - Module-by-module review assignments
- [Plans Directory](../plans/) - Development roadmap
- [Core Application](core/) - App factory, configuration, models
- [Routes & API](routes/) - All route blueprints
- [Services](services/) - Business logic layer
- [Tasks](tasks/) - Celery and APScheduler
- [Infrastructure](infrastructure/) - Search, email, storage, webhooks
- [Frontend](frontend/) - Static assets and templates
- [Deployment](deployment/) - Docker, CI/CD, security
- [Testing](testing/) - Test suite documentation
