# App Core Agent Override

Specialized handling for the Flask application core.

## Key Files

- `__init__.py` - App factory (`create_app()`), middleware, logging setup
- `config.py` - All config loaded from `config.toml` + env vars + validation
- `models.py` - SQLAlchemy models (User, Post, Tag, Subscriber, PageView, ShareEvent, AdminSession, SiteSettings, Page, PostRevision)
- `extensions.py` - Flask extensions (db, login_manager, migrate)
- `utils.py` - Slug generation, email validation, XML escaping, UTCDateTime type
- `base62.py` - Short URL encoding (base62)
- `csrf.py` - CSRF token handling (sliding window)
- `tag_cache.py` - Tag count cache (flask-cache memoization)
- `search.py` - FTS5 full-text search with LIKE fallback + snippet extraction
- `markdown_config.py` - Shared nh3 allowed tags/attributes for markdown rendering
- `csv_utils.py` - Subscriber CSV export with formula injection prevention
- `context_processors.py` - Template context (theme, footer, canonical_url)
- `filters.py` - Template filters (reading_time, post_image_url, truncate, etc.)
- `vite.py` - Vite integration for content-hashed assets
- `storage.py` - Storage abstraction layer (local/S3)
- `page_view_buffer.py` - Page view buffering for high-traffic sites
- `backup_encryption.py` - GPG symmetric encryption for backups
- `backup_integrity.py` - Backup integrity verification
- `validators.py` - Input validation utilities
- `webhooks.py` - Webhook delivery with retry
- `tasks.py` - Celery tasks
- `celery_app.py` - Celery configuration

## Configuration

- `config.toml` for site settings (title, author, email, etc.)
- Config validation deferred to `create_app()` (not import time)
- `SECRET_KEY` must be at least 32 characters
- `ADMIN_PASSWORD` required; `RuntimeError` in `create_app()` if missing
- Environment variables override config values
- Pagination and limits loaded from `config.toml [app]` section
- **Custom CSS sanitization**: `sanitize_css()` strips dangerous properties (`url()`, `expression()`, `content`, etc.)
- **Redis Cache**: In production, uses Redis backend (`CACHE_TYPE: RedisCache`)
- **Redis Rate Limiting**: Production uses Redis for rate limit storage (`RATE_LIMIT_STORAGE_URI`)
- **DB Connection Pool**: Production uses pooled connections (`SQLALCHEMY_ENGINE_OPTIONS`)

## Models

- `Post.slug` must be unique—use `_generate_unique_slug()` in `app/routes/admin/helpers/slug.py`
- `Page.slug` must be unique—use `_generate_unique_slug()` in `app/routes/admin/helpers/slug.py`
- `Post.updated_at` has automatic `onupdate` trigger in the model
- Tags use a many-to-many relationship via `post_tags` table
- `Post.short_code()` encodes the post ID to base62 for short URLs (`/s/<code>`)
- `Post.scheduled_publish_at` — optional datetime for scheduled auto-publish
- `PostRevision` model tracks revision history on each publish
- `Series` and `PostSeries` models for post series/collections
- `Subscriber.token` is a UUID hex used for confirm/unsubscribe links
- `Subscriber.expires_at` has no model default; the subscribe route sets it explicitly
- `User.reset_token` and `User.reset_token_expires_at` for password reset flow (tokens hashed with SHA-256)
- `AdminSession` tracks active admin sessions with IP binding warning
- All DateTime columns use `UTCDateTime` TypeDecorator (stores naive UTC in SQLite, returns timezone-aware UTC on read)
- `utc_now()` returns timezone-aware UTC datetime

## Database

- SQLite stored in `instance/blog.db` (auto-created, WAL mode)
- **WAL-Compatible Backups**: When WAL mode is enabled, `shutil.copy2` is insufficient as it misses the `.wal` and `.shm` files. ALWAYS use the `sqlite3.backup()` API for consistent database snapshots.
- Uses Flask-SQLAlchemy + Flask-Migrate (Alembic)
- SQLAlchemy 2.0 patterns exclusively — `db.session.execute(select(Model).filter(...))`
- Use `db.session.get(Model, id)` instead of `Model.query.get(id)`
- Use `db.paginate(select(...), page=..., per_page=..., error_out=False)` for pagination

## Database Indexes

- `ix_posts_published_created` — post listings
- `ix_posts_published_updated` — dashboard
- `ix_page_views_post_created` — view counts
- `ix_share_events_post_created` — share counts
- `ix_subscribers_confirmed_unsubscribed` — subscriber queries

## Error Logging

Structured error handling utilities in `app/utils.py`:
- `ErrorLogContext` - Context manager for event categorization
- `log_storage_error()`, `log_security_event()`, `log_scheduler_error()` - Specialized loggers
- `handle_error()` - Unified error handler
- `unified_error_handler()` - Decorator for route error handling

## Security

- Session fixation prevention (`session.clear()` before `login_user()`)
- CSRF protection with sliding window (timing-safe comparison via `hmac.compare_digest`)
- Password hashing via `werkzeug.security` (pbkdf2:sha256)
- Token enumeration prevention with constant-time delay
- SQLAlchemy 2.0 parameterized queries throughout
- Magic byte detection for file uploads
- **Custom CSS sanitization**: `sanitize_css()` currently uses regex (Pending Wave 1 upgrade to `tinycss2`)
- **Webhook Encryption**: Pending Wave 1 (implement AES-256-GCM in `webhook_encryption.py`)
- **FTS Security**: `app/search.py` needs refactor to avoid string concatenation (Pending Wave 1)
- Comprehensive security headers (CSP with nonces, HSTS, X-Frame-Options)

## Security Headers

The `set_security_headers` after-request handler sets:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-Download-Options: noopen`
- `X-Permitted-Cross-Domain-Policies: none`
- `Cross-Origin-Opener-Policy: same-origin`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy` (self-only sources, nonces for scripts/styles, `frame-src 'none'`)

## CLI Commands

Available via `flask`:
- `flask rebuild-search` — Rebuild FTS5 index
- `flask cleanup-orphaned-images` — Clean up unused uploaded images
- `flask create-admin <username>` — Create or promote admin user
- `flask promote-admin <username>` — Promote existing user to admin
- `flask check-integrity` — Run database integrity check
- `flask export-data <output_file>` — Export posts/subscribers/tags as JSON
- `flask import-data <input_file>` — Import from JSON
- `flask seed` — Generate sample data for testing

## Shell Context

`flask shell` provides: `db`, `User`, `Post`, `Tag`, `Subscriber`, `Page`, `PageView`, `ShareEvent`, `AdminSession`, `SiteSettings`, `PostRevision`