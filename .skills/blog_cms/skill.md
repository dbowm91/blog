# Blog CMS Skill

## Description
Blog CMS - Flask-based blogging platform with admin dashboard, newsletter scheduling, FTS5 search, multi-admin sessions, custom CSS theming, syntax highlighting themes, post series, Atom feed, 2FA, Comments, Audit Log, Post Revision Diff

Implementation Status: All waves completed. Project in maintenance mode.

## Implementation Summary

All implementation waves (A-F from plan.md) have been verified and completed:
- **Wave A**: Testing documentation (clean_db fixture, test file list with line numbers)
- **Wave B**: Services documentation (search.md source clarification, reset_fts_available(), backup.md line numbers)
- **Wave C**: Tasks documentation (error handling table, deliver_webhook_task non-retry, line numbers fixed)
- **Wave D**: Routes documentation (comment rate limit 10/min, sitemap cache, API pages field, JSON feed authors)
- **Wave E**: Frontend documentation (route-based code splitting, post_image_url filter, lazy-load.js fallback)
- **Wave F**: Infrastructure documentation (WEBHOOK_TIMEOUT, variant cleanup, FLASK_ENV, PYTHONPATH, BACKUP_ENCRYPTION_KEY)

### Deferred Item (Acknowledged)
**Per-Webhook Retry** - Implemented May 28, 2026. `deliver_webhook_task` now dispatches to `deliver_single_webhook_task` for per-webhook retry with exponential backoff (up to 3 retries).

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
- `app/routes/api/` - REST API (posts, subscribers, stats, auth)
- `app/routes/rss.py` - RSS 2.0, Atom, JSON feed endpoints

### Services
- `app/services/backup.py` - `create_backup()` (Celery, encrypted/compressed) and `run_daily_backup()` (APScheduler, both use blog_*.db naming)
- `app/services/slug.py` - Slug generation with 100 try collision limit
- `app/services/serialization.py` - JSON export/import
- `app/services/tag.py` - Tag management with caching
- `app/services/search/` - Search provider abstraction (SQLiteSearchProvider, PostgreSQLSearchProvider stub)
- `app/services/encryption.py` - AES-256-GCM encryption for TOTP

### Tasks
- `app/tasks.py` - Celery tasks (images, newsletter, webhooks, email, backup queues)
- `app/scheduler.py` - APScheduler jobs (cleanup_expired_subscribers every 5 min, run_daily_backup at 02:00)

### Infrastructure
- `app/email.py` - SMTP email delivery
- `app/storage.py` - Local/S3 storage abstraction
- `app/webhooks.py` - Webhook delivery with SSRF protection
- `app/page_view_buffer.py` - Page view buffering

### Testing
- `tests/conftest.py` - Test fixtures (app, client, db, admin_user)
- `tests/shared_fixtures.py` - Shared `ensure_buffer_disabled` autouse fixture (Wave F consolidation)
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
These files previously used broad `except Exception` clauses. All have been replaced with specific exceptions:
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

### Log ID, not Username
When logging user actions, always use `user.id`. Never log raw User objects or usernames.

### Credential Protection
Never log `SECRET_KEY`, `ADMIN_PASSWORD`, or API keys.

## Test Interference Notes

### Page View Buffer
- Buffer started during `create_app()` if `PAGE_VIEW_BUFFER_SIZE > 0`
- In tests: disable via `app.config.PAGE_VIEW_BUFFER_SIZE = 0` and call `shutdown_page_view_buffer()`
- `ensure_buffer_disabled` fixture consolidated in `tests/shared_fixtures.py` (Wave F)

### Test Database Session
`db.session.refresh()` fails if object isn't in current session. Re-query from database instead.

## Implementation Plan

All waves completed: `plans/plan.md`
- Project in maintenance mode
- See `plans/plan.md` for complete reference of all implementation details