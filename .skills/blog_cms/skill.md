# Blog CMS Skill

## Description
Blog CMS - Flask-based blogging platform with admin dashboard, newsletter scheduling, FTS5 search, multi-admin sessions, custom CSS theming, syntax highlighting themes, post series, Atom feed, 2FA, Comments, Audit Log, Post Revision Diff

## Status

Maintenance mode. All implementation waves completed.

## Triggers

Flask app, SQLAlchemy, session management, CSRF, newsletter, APScheduler, FTS5, REST API, password reset, post revisions, preview links, toasts, dashboard charts, graceful shutdown, Docker deployment, Vite bundler, 2FA, Comments, Audit Log

## Key Files

### Core Application
- `app/__init__.py` - Flask app factory with extensions, blueprints, middleware, security headers
- `app/config.py` - Configuration loading (env > config.toml > defaults)
- `app/models.py` - SQLAlchemy models (User, Post, Tag, Comment, Subscriber, etc.)
- `app/extensions.py` - Flask extensions initialization
- `app/filters.py` - Jinja2 template filters (markdown_safe, reading_time, post_image_url, etc.)
- `app/context_processors.py` - Template context processors (inject_csrf, inject_config, inject_theme, etc.)

### Routes
- `app/routes/public/` - Public pages, search, comments, subscribe
- `app/routes/admin/` - Admin dashboard, post editor, settings
- `app/routes/api/` - REST API (posts, pages, series, tags, subscribers, stats, auth)
- `app/routes/rss.py` - RSS 2.0, Atom, JSON feed endpoints

### Services
- `app/services/backup.py` - `create_backup()` (Celery, encrypted/compressed) and `run_daily_backup()` (APScheduler, both use blog_*.db naming)
- `app/services/slug.py` - Slug generation with 100 try collision limit
- `app/services/serialization.py` - JSON export/import
- `app/services/tag.py` - Tag management with caching
- `app/services/search/` - Search provider abstraction (SQLiteSearchProvider, PostgreSQLSearchProvider stub)
- `app/services/encryption.py` - AES-256-GCM encryption for TOTP secrets

### Tasks
- `app/tasks.py` - Celery tasks (images, newsletter, webhooks, email, backup queues)
- `app/scheduler.py` - APScheduler jobs (cleanup_expired_subscribers every 5 min, publish_scheduled_posts every 5 min, run_daily_backup at 02:00)

### Infrastructure
- `app/email.py` - SMTP email delivery
- `app/storage.py` - Local/S3 storage abstraction (thread-safe singleton via double-checked locking)
- `app/webhooks.py` - Webhook delivery with SSRF protection
- `app/page_view_buffer.py` - Page view buffering

### Testing
- `tests/conftest.py` - Test fixtures (app, client, db, admin_user)
- `tests/shared_fixtures.py` - Shared `ensure_buffer_disabled` autouse fixture
- `tests/test_*.py` - Unit tests
- `tests/benchmarks/` - Benchmark tests
- `tests/e2e/` - E2E tests with Playwright

## Verified Routes

| Route | Path | Method |
|-------|------|--------|
| New post | `/admin/new` | GET/POST |
| Edit post | `/admin/edit/<id>` | GET/POST |
| Tag delete | `/admin/tags/delete/<id>` | POST |
| Comment submission | `/POST /post/<slug>/comment` | POST |
| Subscribe | `/subscribe` | POST only |
| API post publish | `PUT /api/posts/<id>` | PUT with `{"published": true}` |

## Verified Behavior

### Configuration Priority
env vars > config.toml > defaults

### Newsletter Retry Count
Default is 5 (not 3)

### APScheduler Schedules
- `cleanup_expired_subscribers`: `minute="*/5"` (NOT hourly)
- `run_daily_backup`: `hour=2, minute=0` (NOT midnight)

### Celery Queue Names
`images`, `newsletter`, `webhooks`, `email`, `backup` (see `app/tasks.py`)

### Comment Model Relationships
```python
parent = db.relationship("Comment", remote_side=[id], back_populates="replies")
replies = db.relationship("Comment", back_populates="parent", lazy="select")
```

### Health Check Critical Checks
```python
critical_checks = {
    k: v for k, v in checks.items()
    if k in ("database", "scheduler", "search", "disk_space", "db_integrity")
}
```

### Snippet Batching (SQLite)
```python
chunk_size = 500
for i in range(0, len(post_ids), chunk_size):
    chunk = post_ids[i:i + chunk_size]
```

## Security Notes

### High-Risk Files (Error Handling)
These files use specific exception handling:
- `app/routes/public/meta.py`
- `app/email.py`
- `app/backup_integrity.py`
- `app/webhooks.py`
- `app/tasks.py`
- `app/page_view_buffer.py`

### 2FA Implementation
- TOTP secrets encrypted at rest using AES-256-GCM
- `User.totp_secret` is a property that decrypts on access
- Backup codes SHA-256 hashed and single-use

### LOGIN_FAILURE_DELAY
Minimum enforced at 0.1s in `app/config.py` to prevent brute force.

### Thread-Safe Storage
`app/storage.py:get_storage()` uses double-checked locking with `threading.Lock()`.

## Template Filters

Actual filters in `app/filters.py`:
- `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`
- `post_image_avif_url_stub` — DEPRECATED: stub, always returns None

## Test Interference Notes

### Page View Buffer
- Buffer started during `create_app()` if `PAGE_VIEW_BUFFER_SIZE > 0`
- In tests: disable via `app.config.PAGE_VIEW_BUFFER_SIZE = 0` and call `shutdown_page_view_buffer()`
- `ensure_buffer_disabled` fixture in `tests/shared_fixtures.py`

### Test Database Session
`db.session.refresh()` fails if object isn't in current session. Re-query from database instead.

## Maintenance

Project is in maintenance mode. No active implementation plans.
- See `docs/internals/agent-maintainer-notes.md` for detailed implementation history