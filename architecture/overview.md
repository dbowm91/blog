# Architecture Overview

This document provides a high-level overview of the DevLog blogging platform architecture and serves as an index for detailed documentation of each component.

## System Summary

DevLog is a Flask-based blogging platform with:
- SQLAlchemy ORM (SQLite default, PostgreSQL supported)
- FTS5 full-text search
- Multi-admin sessions with 2FA
- Newsletter scheduling with async delivery
- Custom CSS theming and syntax highlighting
- Post revisions with diffs
- Comments system
- Audit logging
- Webhook delivery
- Docker deployment with Celery workers

---

## Component Index

### Core Application
| Component | File(s) | Description |
|-----------|---------|-------------|
| [App Factory](core/app-factory.md) | `app/__init__.py` | Flask app initialization, extensions, middleware |
| [Configuration](core/configuration.md) | `app/config.py`, `config.toml` | Configuration loading and priority |
| [Extensions](core/extensions.md) | `app/extensions.py` | SQLAlchemy, Flask-Login, Migrate, Caching |
| [Models](core/models.md) | `app/models.py` | Database models (User, Post, Tag, etc.) |

### Routes & API
| Component | File(s) | Description |
|-----------|---------|-------------|
| [Public Routes](routes/public-routes.md) | `app/routes/public/` | Blog pages, search, comments, subscription |
| [Admin Routes](routes/admin-routes.md) | `app/routes/admin/` | Dashboard, post editor, settings, analytics |
| [API Routes](routes/api-routes.md) | `app/routes/api/` | REST API for posts, subscribers, stats |
| [RSS/Feeds](routes/rss-feeds.md) | `app/routes/rss.py` | RSS 2.0, Atom, JSON feeds |

### Services Layer
| Component | File(s) | Description |
|-----------|---------|-------------|
| [Backup Service](services/backup.md) | `app/services/backup.py` | Database backup with compression/encryption |
| [Serialization](services/serialization.md) | `app/services/serialization.py` | JSON export/import |
| [Slug Service](services/slug.md) | `app/services/slug.py` | Unique slug generation |
| [Tag Service](services/tag.md) | `app/services/tag.md` | Tag CRUD and count management |

### Task Processing
| Component | File(s) | Description |
|-----------|---------|-------------|
| [Celery Tasks](tasks/celery-tasks.md) | `app/celery_app.py`, `app/tasks.py` | Async task queue workers |
| [APScheduler](tasks/scheduler.md) | `app/scheduler.py` | In-process scheduled jobs |

### Infrastructure
| Component | File(s) | Description |
|-----------|---------|-------------|
| [Search](infrastructure/search.md) | `app/search.py` | FTS5 full-text search |
| [Email](infrastructure/email.md) | `app/email.py` | SMTP email delivery |
| [Storage](infrastructure/storage.md) | `app/storage.py` | Local/S3 storage abstraction |
| [Webhooks](infrastructure/webhooks.md) | `app/webhooks.py` | Webhook delivery with SSRF protection |

### Frontend
| Component | File(s) | Description |
|-----------|---------|-------------|
| [Static Assets](frontend/static-assets.md) | `app/static/` | JS, CSS, uploads, Vite build |
| [Templates](frontend/templates.md) | `app/templates/` | Jinja2 templates |

### Deployment & Operations
| Component | File(s) | Description |
|-----------|---------|-------------|
| [Docker](deployment/docker.md) | `Dockerfile`, `docker-compose.yml` | Container orchestration |
| [CI/CD](deployment/cicd.md) | `.github/workflows/` | Testing and deployment pipelines |
| [Security](deployment/security.md) | Various | Authentication, CSRF, sanitization |

### Testing
| Component | File(s) | Description |
|-----------|---------|-------------|
| [Test Suite](testing/test-suite.md) | `tests/` | Unit, integration, e2e tests |

---

## Directory Structure

```
blog/
├── app/
│   ├── __init__.py          # App factory
│   ├── models.py            # Database models
│   ├── config.py            # Configuration
│   ├── extensions.py        # Flask extensions
│   ├── routes/              # Route blueprints
│   │   ├── api/             # REST API
│   │   ├── admin/           # Admin dashboard
│   │   ├── public/          # Public pages
│   │   └── rss.py           # Feeds
│   ├── services/           # Business logic
│   ├── static/              # Frontend assets
│   └── templates/           # Jinja2 templates
├── tests/                   # Test suite
├── migrations/               # Database migrations
├── architecture/             # This documentation
├── docs/                    # OpenAPI spec
├── nginx/                   # Nginx config
├── scripts/                 # Build scripts
└── plans/                   # Development roadmap
```

## Request Flow

```
Request → Nginx → Granian (ASGI) → Flask → Blueprint → Route Handler
                                                     ↓
                                               Service/Model
                                                     ↓
                                         SQLAlchemy → SQLite/PostgreSQL

Async Operations:
  Route → Celery → Redis Queue → Celery Worker
  APScheduler → Triggered Jobs → Services
```

## Configuration Priority

1. Environment variables (highest)
2. `config.toml` file
3. Default values in `app/config.py`

## Key Technologies

| Component | Technology |
|-----------|------------|
| Web Framework | Flask 3.1+ |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite / PostgreSQL |
| ASGI Server | Granian (Rust) |
| Task Queue | Celery + Redis |
| Cache | Flask-Caching + Redis |
| Scheduler | APScheduler |
| Frontend Build | Vite |
