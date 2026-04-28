# Agent Guidelines

Quick reference for AI agents working on this codebase.

## Running Tests

```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

To run without E2E tests (which require Playwright):
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ --ignore=tests/e2e
```

Both `ADMIN_PASSWORD` and `SECRET_KEY` environment variables are **required**—the app raises `RuntimeError` when `create_app()` is called without them.

## Project Structure

```
run.py                  # Entry point—exports `app` (WSGI) and `asgi_app` (ASGI)
app/__init__.py         # App factory (`create_app()`), middleware, logging setup
app/config.py           # All config loaded from `config.toml` + env vars (+ validation)
app/models.py           # SQLAlchemy models (User, Post, Tag, Subscriber, PageView, ShareEvent, AdminSession, SiteSettings, Page, PostRevision)
app/extensions.py       # Flask extensions (db, login_manager, migrate)
app/routes/public.py    # Public-facing routes
app/routes/admin/       # Admin routes package (requires login)
app/routes/admin/__init__.py  # Blueprint registration, shared helpers, admin_required
app/routes/admin/auth.py      # login, logout, password reset
app/routes/admin/posts.py     # dashboard, post CRUD, bulk operations, revisions
app/routes/admin/subscribers.py  # subscriber management (incl. bulk resend)
app/routes/admin/tags.py      # tag management
app/routes/admin/users.py     # user management
app/routes/admin/sessions.py  # session management
app/routes/admin/media.py     # media library
app/routes/admin/backup.py    # backup/restore
app/routes/admin/analytics.py # analytics page
app/routes/admin/newsletter.py # newsletter test
app/routes/admin/settings.py  # theme settings (presets, custom CSS, logo)
app/routes/admin/pages.py     # static pages CRUD
app/routes/admin/helpers/     # Admin helpers package
app/routes/admin/helpers/slug.py  # Slug generation helper
app/routes/api.py       # REST API (Post/Subscriber endpoints)
app/routes/rss.py       # RSS feed
app/csrf.py             # CSRF token handling (sliding window)
app/cache.py            # Tag count cache (double-checked locking)
app/search.py           # FTS5 full-text search with LIKE fallback + snippet extraction
app/utils.py            # Slug generation, email validation, XML escaping, UTCDateTime type
app/base62.py           # Short URL encoding (base62)
app/scheduler.py        # APScheduler newsletter job (with file locking)
app/email.py            # SMTP email sending (with TLS via ssl.create_default_context)
app/markdown_config.py  # Shared nh3 allowed tags/attributes for markdown rendering
app/csv_utils.py        # Subscriber CSV export with formula injection prevention
app/context_processors.py  # Template context (theme, footer, canonical_url)
app/cli.py              # CLI commands (export-data, import-data, seed, etc.)
app/backup_integrity.py # Backup integrity verification
app/static/js/          # JavaScript modules (ES6 with dynamic imports)
app/static/js/lib/     # Third-party JS libraries (marked.js for markdown preview)
app/static/js/shared/   # Shared JS modules (utils, dark-mode, modal, mobile-menu, toast, etc.)
app/static/js/public/   # Public-facing JS modules (share, lightbox, toc, search, etc.)
app/static/js/admin/    # Admin JS modules (editor, bulk, shortcuts)
DEPLOY.md               # Deployment guide (SQLite/PostgreSQL)
docs/openapi.yaml       # API documentation
scripts/dev.sh          # Development environment setup script
scripts/sync_backups.sh  # Off-site backup sync script (rclone/S3)
```

## Key Patterns

### Database
- SQLite stored in `instance/blog.db` (auto-created, WAL mode)
- Uses Flask-SQLAlchemy + Flask-Migrate (Alembic)
- Uses SQLAlchemy 2.0 patterns exclusively — `db.session.execute(select(Model).filter(...))` instead of `Model.query.filter(...)`
- Use `db.session.get(Model, id)` instead of `Model.query.get(id)` (avoids LegacyAPIWarning)
- Use `db.paginate(select(...), page=..., per_page=..., error_out=False)` for pagination

### Models
- `Post.slug` must be unique—use `_generate_unique_slug()` in `app/routes/admin/posts.py`
- `Page.slug` must be unique—use `_generate_unique_page_slug()` in `app/routes/admin/pages.py`
- `Post.updated_at` has automatic `onupdate` trigger in the model
- Tags use a many-to-many relationship via `post_tags` table
- `Post.short_code()` encodes the post ID to base62 for short URLs (`/s/<code>`)
- `Post.scheduled_publish_at` — optional datetime for scheduled auto-publish (scheduler checks every 5 minutes)
- `PostRevision` model tracks revision history on each publish
- `Subscriber.token` is a UUID hex used for confirm/unsubscribe links
- `Subscriber.expires_at` has no model default; the subscribe route sets it explicitly from config (`confirmation_expiry_hours`)
- All models have `__repr__` methods for debugging
- Database indexes on frequently queried columns (see models.py for full list)
- `User.reset_token` and `User.reset_token_expires_at` for password reset flow (tokens hashed with SHA-256 before storage)
- `AdminSession` tracks active admin sessions with IP binding warning
- All DateTime columns use `UTCDateTime` TypeDecorator (stores naive UTC in SQLite, returns timezone-aware UTC on read)
- `utc_now()` returns timezone-aware UTC datetime

### Session
- `session["viewed_posts"]` tracks viewed post IDs to avoid double-counting page views—capped at `MAX_VIEWED_POSTS` entries from config (default 100)
- Admin session expires after `SESSION_LIFETIME_HOURS` hours of inactivity (default 24)
- `SESSION_COOKIE_SECURE` defaults to "true" (set "false" to disable HTTPS-only cookie)
- `SESSION_COOKIE_SAMESITE` is set to `"Lax"`
- Login creates an `AdminSession` record (tracks `session_id`, `ip_address`, `user_agent`); logout deletes it
- Session IP binding logs warning on address change (detects potential hijacking, does not invalidate)
- **Cascade delete**: Deleting a User automatically deletes their AdminSession records

### CSRF (Sliding Window)
- CSRF token uses sliding window of 5 valid tokens per session
- `generate_csrf_token()` creates new token, maintains window
- `validate_csrf_token()` checks token is in valid set, removes after use
- Token rotates on privilege changes (promote/demote/make_owner)
- All POST routes require CSRF token
- Tests disable CSRF via `CSRF_ENABLED=False` + `TESTING=True` in config

### API Authentication
- REST API uses `X-API-Key` header (env var `API_KEY`)
- Admin routes use session-based authentication via `@admin_required` decorator
- Password reset flow: forgot-password → email with reset link → reset form → new password

### Configuration
- `config.toml` for site settings (title, author, email, etc.)
- Config validation deferred to `create_app()` (not import time)
- `SECRET_KEY` must be at least 32 characters
- `ADMIN_PASSWORD` required; `RuntimeError` in `create_app()` if missing
- Environment variables override config values
- Pagination and limits loaded from `config.toml [app]` section
- **Custom CSS sanitization**: `sanitize_css()` strips dangerous properties (`url()`, `expression()`, `content`, etc.)

## Common Tasks

### Add a new route
1. Add handler to `app/routes/public.py` or `app/routes/admin/`
2. Create template in `app/templates/`
3. Admin routes need `@admin_required` decorator

### Add a new model
1. Define in `app/models.py`
2. Run `flask db migrate -m "description"`
3. Run `flask db upgrade`

### Modify templates
- Base template: `app/templates/base.html`
- Sidebar: `app/templates/_sidebar.html`
- Admin templates: `app/templates/admin/`
- Error pages: `app/templates/404.html`, `app/templates/500.html`, `app/templates/_error.html` partial

## Known Limitations

- **SQLite with PostgreSQL migration path**—default uses SQLite (WAL mode); PostgreSQL migration documented in DEPLOY.md
- **File uploads**—stored locally in `static/uploads/`, no S3 support
- **Newsletter scheduler**—runs in-process via APScheduler with `fcntl` file locking (Unix only)
- **E2E tests** require Playwright installation to run

## Rate Limiting

This codebase intentionally **does not include application-level rate limiting**. Configure at reverse proxy/WAF level.

```nginx
# nginx example for /admin/login
limit_req zone=login burst=5 nodelay;
limit_req_status 429;
```

Suggested: 5 req/min for `/admin/login`, 20 req/min for `/admin/*`, 100 req/min for public routes.

## Lessons Learned

### SMTP Context Manager Gotcha
`with smtplib.SMTP() as server:` binds `server` at `__enter__` time. Reassigning `server` inside the block creates a new local variable—the `with` statement's `__exit__` still calls the **original** object. Use manual `try/finally` instead.

### Cross-Blueprint Imports
Both `admin` routes and `public.py` import `invalidate_tag_cache` and `_get_tag_counts` from `app.cache`. No other cross-blueprint imports.

### Admin Routes Use `@admin_required`
All admin routes (except `login()` and `logout()`) use `@admin_required`, which combines `@login_required` with `is_admin` check.

### `generate_slug` Edge Cases
Empty string and whitespace-only input both fall back to `"untitled"`.

### `nh3` Config
The `nh3.clean()` allowed tags/attributes are defined in `app/markdown_config.py` and shared by `app/__init__.py` (markdown_safe filter) and `app/routes/admin.py` (preview endpoint).

### Subscribe Race Condition
Two concurrent subscribe requests with same email can both pass `scalar_one_or_none()` check, then both try to insert. The unique constraint causes `IntegrityError` → 500. Fixed by wrapping insert + commit in `try/except IntegrityError` and re-querying on collision.

### IntegrityError Rollback Gotcha
In `edit_post()`, `db.session.rollback()` reverts ALL session changes. After rollback, SQLAlchemy marks all attributes as expired. If you only re-set one field and commit, all other edits are silently lost. Always reapply all field changes after rollback.

### File Deletion Timing
Old image files are deleted *after* `db.session.commit()` to prevent dangling file references on rollback. Use `safe_delete_file()` from `app/utils.py`.

### LIKE Wildcard Escaping
Search input containing `%` or `_` causes unexpected pattern matching. Escape them before interpolating:
```python
escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
search_term = f"%{escaped}%"
Post.title.ilike(search_term, escape="\\")
```

### Image Upload Extension
`_save_image()` uses the detected magic byte type for the file extension, not the user-provided extension.

### Token Enumeration Prevention
/confirm/<token> uses `scalar_one_or_none()` + `time.sleep(0.1)` to prevent token enumeration. Invalid tokens return success (not 404).

### Double-Checked Locking for Caches
`_get_tag_counts()` in `app/cache.py` uses double-checked locking — DB query runs outside the lock.

### FTS5 Search
- `app/search.py` — FTS5 virtual table `posts_fts` (title, body, summary)
- FTS index synced via `sync_fts()` on post create/edit/publish/unpublish/delete
- `sync_fts()` called BEFORE `db.session.commit()` for create/edit/publish; `remove_fts()` called AFTER for delete
- FTS table existence cached with 5-minute TTL
- LIKE fallback filters by `Post.published == True`
- "Did you mean?" suggestions via `difflib.get_close_matches()`
- Query term highlighting with `<mark>` tags

### Route-Based JavaScript Code Splitting
`app/static/js/main.js` uses route-based dynamic imports. Admin pages get utils, modal, shortcuts, bulk. Public pages get utils, dark-mode, mobile-menu, lazy-load, share, lightbox, toc.

### Multi-Admin
- `flask create-admin <username>` CLI command
- User management UI at `/admin/users`
- Password complexity: 3 of 4 character classes, min 8 chars
- Promote/Demote via `POST /admin/users/<id>/promote` or `POST /admin/users/<id>/demote`
- Ownership transfer via `POST /admin/users/<id>/make-owner`

### SQLAlchemy 2.0 Query Patterns
```python
db.session.execute(select(Model).filter(...)).scalar_one_or_none()  # single result
db.session.execute(select(Model).filter_by(...)).scalars().all()    # multiple results
db.session.execute(select(func.count(...))).scalar_one()           # counts
db.session.execute(delete(Model).where(...))                        # deletes
db.paginate(select(...), page=..., per_page=..., error_out=False)    # pagination
```

### `assert` Statements Under `python -O`
`assert` is stripped when Python runs with `-O`. Never use `assert` for runtime safety checks.

### `db.session.close_all()` Deprecation
Use `db.engine.dispose()` instead — it closes all connections in the pool.

### Mobile Menu Toggle
The mobile hamburger menu button is **created dynamically in JavaScript** (`shared/mobile-menu.js`), not in HTML templates.

### Nested Forms in Dashboard
Bulk form uses `form="bulk-form"` attribute on checkboxes to associate without nesting. Never nest `<form>` elements.

### Template Value Caching
To avoid redundant computations, cache filter results in template loops:
```jinja2
{% set rt = post.body | reading_time %}
{% set img = post|post_image_url %}
{% set truncated_desc = post.body | truncate(160) %}
{% set tc = tag_counts.get(tag.id, 0) %}
```
This is especially important for filters with file I/O or string processing.

### Request-Level Image Caching
The `post_image_url` filter uses Flask `g` object for request-level caching to avoid repeated file I/O:
```python
# In app/__init__.py - filter implementation
if not hasattr(g, "_post_image_cache"):
    g._post_image_cache = {}
if post_id in g._post_image_cache:
    return g._post_image_cache[post_id]
result = compute_image_url(post_id)
g._post_image_cache[post_id] = result
return result
```

### Tag Count Caching
Tag counts use double-checked locking in `app/cache.py` with a cached function.

### GPU Acceleration for Blur Effects
For `backdrop-filter: blur()`, use `will-change: backdrop-filter` in CSS to enable GPU compositing:
```css
.navbar, .nav-links, .modal-overlay {
    will-change: backdrop-filter;
}
```

### Lazy Image Progressive Enhancement
Images use `opacity: 0` by default and JS adds `.loaded` class. Pattern: add `document.documentElement.classList.add('js')` first, prefix CSS rules with `.js`.

### Admin Page Detection in JS
Use `document.body.classList.contains('admin-body')` to scope admin-only JS handlers.

### `yield_per()` Usage
Calling `.all()` after `.yield_per()` defeats streaming by materializing all rows into a list. In `app/scheduler.py`, the subscriber query uses `.yield_per(500).scalars()` without `.all()` to stream results.

### Docker-Compose Circular Dependency
Avoid circular `depends_on` with `condition: service_healthy`. The blog service previously depended on nginx; nginx depended on blog being healthy → deadlock.

### Granian ASGI Integration
Granian (Rust-based ASGI server) is significantly faster than Gunicorn. Use `granian --interface asgi ...` to run the `asgi_app` from `run.py`.

### PostRevision Eager Loading
Always use `.options(joinedload(PostRevision.author))` when querying revisions to avoid N+1 queries in templates that display the author.

## Assets

- **No external assets**—all fonts (Inter, JetBrains Mono) are self-hosted in `app/static/fonts/`
- **Prism.js** is self-hosted with extended language definitions
- Do not add external CDN links (Google Fonts, CDNs, etc.)

## New Features Added

### JSON Feed
- `/json` endpoint provides JSON Feed 1.1 format
- Includes title, summary, url, tags, image, author
- Conditional GET with ETag support
- Cache-Control headers for feeds

### Backup Integrity Verification
- `app/backup_integrity.py` module provides verification functions
- Verifies SQLite backup integrity (header, tables, PRAGMA integrity_check)
- Detects corruption using file size and structure heuristics

### Off-site Backup Sync
- `scripts/sync_backups.sh` supports rclone and AWS S3
- Dry-run mode, verification, and local cleanup options
- Cron automation examples in DEPLOY.md

### Granian ASGI Server
- Granian is the recommended ASGI server (faster than Gunicorn)
- Dockerfile updated to use `granian --interface asgi`
- `requirements.txt` includes granian>=1.0.0

### Admin Enhancements
- Pages link added to admin navigation dropdown
- Restore button uses distinct amber/warning color
- Escape key closes modals
- Media cache invalidation on post create/edit

### Search Enhancements
- Live search suggestions via `/api/posts` endpoint
- Debounced input with keyboard navigation
- Search suggestions CSS styling

### Editor Preview Latency
- Client-side markdown rendering via marked.js in `app/static/js/lib/marked.min.js`
- Instant preview feedback as user types
- Server-side `/admin/preview-markdown` still called for nh3 sanitization
- Abortable fetch requests prevent race conditions

### CI/CD Workflow
- GitHub Actions workflow at `.github/workflows/test.yml`
- Runs on push and pull request events
- Python 3.12 with pip caching
- Full test suite: `pytest tests/ --ignore=tests/e2e`

### FTS5 Atomic Sync
- `sync_fts()` uses `INSERT OR REPLACE` for atomic upsert
- `sync_fts_batch()` separates published/unpublished for correct batch handling
- `reset_fts_available()` properly resets FTS cache for testing/cache invalidation

### Alembic SQLite Batch Mode
- `migrations/env.py` configured with `render_as_batch=True` for safe SQLite migrations
- Enables `DROP COLUMN` and `ALTER COLUMN` operations via table recreation
- Required for proper handling of destructive migrations in SQLite

## Dependencies (Python 3.14 compatible)

See `requirements.txt`. Key packages:
- Flask 3.1+
- SQLAlchemy 2.0+ (via Flask-SQLAlchemy)
- Werkzeug 3.1+ (password hashing, security)
- asgiref 3.8+ (ASGI adapter for Granian)
- nh3 0.2+ (HTML sanitization—**not** `bleach`, which is deprecated since 2023)

## Email

- Uses `smtplib` directly (no Celery/Redis)
- SMTP connection uses `starttls()` with `ssl.create_default_context()`
- Individual emails open a fresh SMTP connection per call
- Newsletter batch reuses a single SMTP connection via `_connect_smtp()` helper
- **Do not use `with smtplib.SMTP() as server:` for newsletter batch** — use manual `try/finally`
- Per-subscriber exception handling; failures are logged but don't stop the batch
- On `SMTPServerDisconnected`, reconnects and retries

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

## Security Posture

The codebase implements robust security controls:
- Session fixation prevention (`session.clear()` before `login_user()`)
- CSRF protection with sliding window (timing-safe comparison via `hmac.compare_digest`)
- API key comparison using `hmac.compare_digest()` (timing-safe)
- Password hashing via `werkzeug.security` (pbkdf2:sha256)
- Token enumeration prevention with constant-time delay
- SQLAlchemy 2.0 parameterized queries throughout
- Magic byte detection for file uploads
- CSS sanitization blocking `url()`, `expression()`, `content`, etc.
- CSV formula injection prevention
- Comprehensive security headers (CSP with nonces, HSTS, X-Frame-Options)

## Database Indexes

Key indexes for query optimization:
- `ix_posts_published_created` — post listings
- `ix_posts_published_updated` — dashboard
- `ix_page_views_post_created` — view counts
- `ix_share_events_post_created` — share counts
- `ix_subscribers_confirmed_unsubscribed` — subscriber queries

## Testing Notes

- 510 unit tests pass (excluding E2E)
- New tests added for: password reset flow, settings routes, pages routes
- E2E tests require Playwright: `pip install playwright && playwright install`