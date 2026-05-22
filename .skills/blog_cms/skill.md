# Blog CMS Skill

## Description
Blog CMS - Flask-based blogging platform with admin dashboard, newsletter scheduling, FTS5 search, multi-admin sessions, custom CSS theming, syntax highlighting themes, post series, Atom feed, 2FA, Comments, Audit Log, Post Revision Diff

Implementation Status: All waves A-N completed. Project in maintenance mode.

Waves A-N implemented features (2FA, Rate Limiting, Search, Frontend, Brotli, Bug Fixes, Code Quality, Documentation). Wave K completed architecture reviews of all 8 modules. Wave L implemented all architecture review findings (1 critical security fix, 2 medium fixes, 8 documentation corrections). Wave M completed full implementation of Wave M plan (4 critical bugs fixed, 36 documentation/improvement items completed). Wave N completed 26 items (2 code fixes, 11 documentation fixes, 10 improvements). Plan has been pruned to summary status.

## Wave N Completion (May 2026)

All Wave N items verified and completed:
- **N-1.1**: Fixed email task retry logic - added `max_retries=3` and `self.retry(exc=e)` to `send_confirmation_task` and `send_password_reset_task`
- **N-1.2**: Fixed mobile-menu.jsx import in main.js
- **N-2.1 through N-2.11**: 11 documentation fixes (ADMIN_RATE_LIMITS, S3 env vars, Webhook encryption, delivery_status, Search config/indexing, routes docs, Docker v2, Permissions-Policy, Python version)
- **N-3.1 through N-3.10**: 10 improvements (email.md, serialization, slug, benchmark fixtures, FTS cleanup, stale line numbers, deprecation notice, backup naming, AGENTS.override.md)

Plan file `plans/plan.md` updated to completed status.

## Wave M Completion (May 2026)

All Wave M items verified and completed:
- 4 Critical bug fixes (M-1.1 through M-1.4)
- 10 High-priority documentation fixes (M-2.1 through M-2.10)
- 12 Medium-priority documentation fixes (M-3.1 through M-3.12)
- 14 Low-priority improvements (M-4.1 through M-4.14)

Plan file `plans/plan.md` pruned to summary status - detailed implementation steps removed.

### Critical Bug Fixes
- **M-1.1**: Fixed `image-review.js` import to `image-preview.js` in `main.js:15,40,51`
- **M-1.2**: Initial email task fix - removed misleading `retry_backoff=True` without max_retries (fully fixed in N-1.1 with `max_retries=3` and `self.retry()`)

### Configuration Fixes
- **docker-compose.yml**: Added `blog_logs` volume to Celery service
- **docker-compose.yml:14**: Added comment explaining `SESSION_COOKIE_SECURE` string handling

### Documentation Updates (36 items)
- API routes, webhook model, search provider, backup implementations
- Health check configuration, APScheduler documentation
- Configuration options, model field documentation
- Various route/method corrections and clarifications

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
`images` (line 31), `newsletter` (line 130), `webhooks` (line 182), `email` (lines 262, 283), `backup` (line 304)

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