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
app/tag_cache.py      # Tag count cache (flask-cache memoization)
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
app/vite.py            # Vite integration for content-hashed assets
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
- `Post.slug` must be unique—use `_generate_unique_slug()` in `app/routes/admin/helpers/slug.py`
- `Page.slug` must be unique—use `_generate_unique_slug()` in `app/routes/admin/helpers/slug.py` (same function used for both posts and pages)
- `Post.updated_at` has automatic `onupdate` trigger in the model
- Tags use a many-to-many relationship via `post_tags` table
- `Post.short_code()` encodes the post ID to base62 for short URLs (`/s/<code>`)
- `Post.scheduled_publish_at` — optional datetime for scheduled auto-publish (scheduler checks every 5 minutes)
- `PostRevision` model tracks revision history on each publish
- `Series` and `PostSeries` models for post series/collections
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
- **Custom CSS sanitization**: `sanitize_css()` strips dangerous properties (`url()`, `expression()`, `content`, etc.) — must be applied BEFORE saving custom_css in settings.py.
- **Redis Cache**: In production, uses Redis backend (`CACHE_TYPE: RedisCache`)
- **Redis Rate Limiting**: Production uses Redis for rate limit storage (`RATE_LIMIT_STORAGE_URI`)
- **DB Connection Pool**: Production uses pooled connections (`SQLALCHEMY_ENGINE_OPTIONS`)

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
- **File uploads**—stored locally in `static/uploads/`. **CRITICAL:** Clean this directory before production deployment.
- **Newsletter scheduler**—runs in-process via APScheduler with `filelock` for cross-platform file locking. Persistence via `SQLAlchemyJobStore` is planned.
- **E2E tests** require Playwright installation to run.

## Rate Limiting
This codebase uses **application-level rate limiting** via `flask-limiter`.

```nginx
# nginx example for /admin/login
limit_req zone=login burst=5 nodelay;
limit_req_status 429;
```

Suggested: 5 req/min for `/admin/login`, 20 req/min for `/admin/*`, 60 req/min for public routes (index, post, page, tag, series), 30 req/min for archive and preview, 20 req/min for search and share tracking, 10 req/min for subscribe, 5 req/min for confirm/unsubscribe.

## Lessons Learned

### Critical: JS Module Initialization
All JavaScript modules must export a default function for initialization. When adding new modules to `app/static/js/shared/` or `app/static/js/public/`, you **must** add `export default initXxx;` where `initXxx` is the initialization function. The main.js loader calls `module.default()` to invoke the exported function. Modules without this export will not be called on page load.

### Critical: Share Platform Names
The share buttons template (`_post_content.html`) and API (`ALLOWED_SHARE_PLATFORMS` in `public.py`) must use the same platform identifiers. The API expects `"hackernews"` not `"hn"`. Always check that template `data-platform` attributes match the API constants.

### Critical: JSON Feed content_html
When updating the JSON Feed in `app/routes/rss.py`, ensure `content_html` field is included per JSON Feed 1.1 spec. Either `content_html` or `content_text` is required.

### SMTP Context Manager Gotcha
`with smtplib.SMTP() as server:` binds `server` at `__enter__` time. Reassigning `server` inside the block creates a new local variable—the `with` statement's `__exit__` still calls the **original** object. Use manual `try/finally` instead.

### Cross-Blueprint Imports
Both `admin` routes and `public.py` import `invalidate_tag_cache` and `_get_tag_counts` from `app.cache`. No other cross-blueprint imports.

### Admin Routes Use `@admin_required`
All admin routes (except `login()` and `logout()`) use `@admin_required`, which combines `@login_required` with `is_admin` check.

### Admin Routes (`app/routes/admin/`)
- `/admin/` - Dashboard with widgets (traffic chart, top shares, trending, scheduled posts count)
- `/admin/posts` - Post CRUD with bulk operations
- `/admin/posts/<id>/revisions` - Post revision history
- `/admin/subscribers` - Subscriber management with bulk resend
- `/admin/users` - User management with promote/demote/make-owner
- `/admin/sessions` - Active session viewing/revocation
- `/admin/media` - Media library with upload/delete
- `/admin/backup` - Database backup/restore with encryption support
- `/admin/settings` - Theme presets, custom CSS, logo, syntax highlighting theme
- `/admin/pages` - Static pages CRUD
- `/admin/series` - Post series/collections management
- `/admin/newsletter` - Newsletter with preview feature

### `generate_slug` Edge Cases
Empty string and whitespace-only input both fall back to `"untitled"`.

### `nh3` Config
The `nh3.clean()` allowed tags/attributes are defined in `app/markdown_config.py` and shared by `app/__init__.py` (markdown_safe filter) and `app/routes/admin.py` (preview endpoint).

### Subscribe Race Condition
Two concurrent subscribe requests with same email can both pass `scalar_one_or_none()` check, then both try to insert. The unique constraint causes `IntegrityError` → 500. Fixed by wrapping insert + commit in `try/except IntegrityError` and re-querying on collision.

### IntegrityError Rollback Gotcha
In `edit_post()`, `db.session.rollback()` reverts ALL session changes. After rollback, SQLAlchemy marks all attributes as expired. If you only re-set one field and commit, all other edits are silently lost. Always reapply all field changes after rollback.

### IntegrityError Rollback in pages.py
The `new_page()` function in `app/routes/admin/pages.py` implements a retry loop with `max_attempts=100`. On `IntegrityError`, it rolls back, regenerates the slug, and retries the commit.

### CSRF Token Rotation on Privilege Change
When promoting/demoting users or making an owner, the code sets `session["csrf_token"]` (singular) but the sliding window uses `session["csrf_tokens"]` (list). Must reset the list `session["csrf_tokens"]` = `[generate_csrf_token()]` not the singular token.

### make_owner() Race Condition
In `app/routes/admin/users.py`, the `make_owner()` function demotes ALL admins first, then promotes the target. If commit fails between these operations, there would be zero admins. Fix: promote target first (so at least one admin always exists), then demote others. Use `db.session.flush()` after promoting.

### File Deletion Timing
Old image files are deleted *after* `db.session.commit()` to prevent dangling file references on rollback. Use `safe_delete_file()` from `app/utils.py`.

### Search highlight_query XSS Risk (FIXED)
`app/search.py:highlight_query()` was fixed to use `html.escape()` before wrapping in `<mark>` tags.

### Rate Limiting Already Present
The codebase already has `@limiter.limit` decorators on most API routes and `/admin/login`. Adding more requires checking existing limits first.

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

### Tag Count Caching
Tag counts use `flask_cache.memoize` decorator in `app/tag_cache.py`. The `_get_tag_counts_cached()` function is memoized with TTL from config. `_get_tag_counts()` checks `has_request_context()` to use cached or uncached version. Invalidate with `invalidate_tag_cache()`.

### FTS5 Search
- `app/search.py` — FTS5 virtual table `posts_fts` (title, body, summary) with `prefix='2 3 4'` for prefix matching
- Prefix search enabled: searching "Py" matches "Python" (automatically appends `*` to terms)
- FTS index synced via `sync_fts()` on post create/edit/publish/unpublish/delete
- `sync_fts()` called BEFORE `db.session.commit()` for create/edit/publish; `remove_fts()` called AFTER for delete
- FTS table existence cached with 5-minute TTL
- LIKE fallback filters by `Post.published == True`
- "Did you mean?" suggestions via `difflib.get_close_matches()`
- Query term highlighting with `<mark>` tags

### RSS/Atom Feed Caching
- RSS feed (`/rss`) cached with `@flask_cache.cached(timeout=300)`
- Atom feed (`/atom`) available with Atom 1.0 format
- Cache invalidation on post publish/unpublish/delete
- JSON Feed (`/json`) with content_html field (1.1 spec)

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

### API Error Handling
All `db.session.commit()` calls in API endpoints must be wrapped in try/except for `IntegrityError` and `OperationalError`. Return 409 Conflict on duplicate slug, 500 Internal Server Error on operational errors. Import from `sqlalchemy.exc`.

### API Input Validation
Input validation via `app/validators.py`:
- `validate_string(value, max_length, field_name)` - validates string fields
- `validate_email(value, max_length)` - validates email format and length
- `validate_boolean(value, field_name)` - validates boolean fields
- Returns `(value, error_message)` tuple

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
The `post_image_url` filter in `app/filters.py` uses Flask `g` object for request-level caching to avoid repeated file I/O:
```python
if not hasattr(g, "_post_image_cache"):
    g._post_image_cache = {}
post_id = id(post)
if post_id in g._post_image_cache:
    return g._post_image_cache[post_id]
path = os.path.join(app.config["UPLOAD_FOLDER"], post.image)
result = post.image if os.path.isfile(path) else None
g._post_image_cache[post_id] = result
return result
```

### Responsive Images
Post images support responsive srcset via the `post_image_srcset` filter. Variants are generated at 400w, 800w, and 1200w widths on upload. Templates use `srcset` with `sizes` attribute for proper responsive behavior.

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

### Related Posts Scoring
`_get_related_posts()` in `app/routes/public.py` uses tag intersection scoring:
- Subquery counts shared tags per post via `post_tags` table
- Orders by `shared_count DESC, created_at DESC`
- Uses `.unique()` after `.options(joinedload(Post.tags))` to avoid SQLAlchemy "unique() required" error
- Configurable via `RELATED_POSTS_COUNT` in `config.toml` (default: 3, hard limit: 6)

### Docker-Compose Circular Dependency
Avoid circular `depends_on` with `condition: service_healthy`. The blog service previously depended on nginx; nginx depended on blog being healthy → deadlock.

### Granian ASGI Integration
Granian (Rust-based ASGI server) is significantly faster than Gunicorn. Use `granian --interface asgi ...` to run the `asgi_app` from `run.py`.

### PostRevision Eager Loading
Always use `.options(joinedload(PostRevision.author))` when querying revisions to avoid N+1 queries in templates that display the author.

### Media Cache Invalidation
When uploading images via post create/edit, the media cache must be invalidated:
```python
from app.routes.admin.media import _invalidate_media_cache
_invalidate_media_cache()
```
The cache is in `app/routes/admin/media.py` and uses 30-second TTL. This is called automatically in `posts.py` after image save.

### Granian Timeout Flags
When running with Granian, set `--timeout` for request timeouts:
```bash
granian --interface asgi --workers 4 --timeout 60 run:asgi_app
```
Without explicit timeout, long-running requests (backup/restore, newsletter) may hang indefinitely.

### Graceful Shutdown
The shutdown handler in `run.py` sets a shutdown event and waits for in-flight requests to complete. Scheduler jobs finish before DB connections close via `db.engine.dispose()`. Never call `db.session.close_all()` — use `db.engine.dispose()` instead.

### JSON Feed content_html Requirement
The JSON Feed 1.1 spec requires either `content_html` or `content_text`. The `/json` endpoint must include `content_html`. See `app/routes/rss.py`.

## Assets

- **No external assets**—all fonts (Inter, JetBrains Mono) are self-hosted in `app/static/fonts/`
- **Prism.js** is self-hosted with extended language definitions
- Do not add external CDN links (Google Fonts, CDNs, etc.)

## Dependencies (Python 3.14 compatible)

See `requirements.txt`. Key packages:
- Flask 3.1+
- SQLAlchemy 2.0+ (via Flask-SQLAlchemy)
- Werkzeug 3.1+ (password hashing, security)
- asgiref 3.8+ (ASGI adapter for Granian)
- nh3 0.2+ (HTML sanitization—**not** `bleach`, which is deprecated since 2023)

## Email

- Uses `smtplib` directly OR Celery tasks for async newsletter sending (configure via `REDIS_URL`)
- SMTP connection uses `starttls()` with `ssl.create_default_context()`
- Individual emails open a fresh SMTP connection per call
- Newsletter batch reuses a single SMTP connection via `_connect_smtp()` helper
- **Do not use `with smtplib.SMTP() as server:` for newsletter batch** — use manual `try/finally`
- Per-subscriber exception handling; failures are logged but don't stop the batch
- On `SMTPServerDisconnected`, reconnects and retries

## Celery Integration

For async task processing (image variant generation, newsletter sending, webhook delivery):

```bash
# Start worker
celery -A app.celery_app worker --loglevel=info

# Start beat scheduler (for periodic tasks like daily backup)
celery -A app.celery_app beat --loglevel=info
```

Tasks in `app/tasks.py`:
- `generate_image_variants` - Background image processing
- `send_newsletter_task` - Async newsletter delivery
- `send_confirmation_task` - Async email confirmation
- `send_password_reset_task` - Async password reset email
- `deliver_webhook` - Async webhook delivery with retry

## Error Logging

Structured error handling utilities in `app/utils.py`:
- `ErrorLogContext` - Context manager for event categorization
- `log_storage_error()`, `log_security_event()`, `log_scheduler_error()` - Specialized loggers
- `handle_error()` - Unified error handler
- `unified_error_handler()` - Decorator for route error handling

## Cache Helpers

- `_build_tag_counts_query()` in `app/tag_cache.py` - Encapsulates tag count query pattern
- `_invalidate_all_caches()` in `app/routes/admin/__init__.py` - Invalidates tag, FTS, analytics, dashboard, and footer caches

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

- 524 tests pass (514 unit + 10 E2E)
- New tests added for: password reset flow, settings routes, pages routes, content hashing
- E2E tests require Playwright: `pip install playwright && playwright install`
- Run all tests: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v`
- Run without E2E: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ --ignore=tests/e2e`

## Frontend Build System
Uses **Vite** for modern JavaScript/CSS bundling (properly configured and installed):

```bash
# Install dependencies (if not already installed)
npm install --registry https://registry.npmjs.org/

# Development with HMR
npm run dev

# Build for production (with content hashing)
npm run build
```

Configuration: `vite.config.js` with Flask integration via `vite-plugin-flask`.
Dependencies are installed in `node_modules/` (gitignored).

### Content Hashing (Item 5A.5 - COMPLETED 2026-05-01)
- Vite generates content-hashed filenames (e.g., `main-BVtPp-ke.js`)
- Manifest file generated at `app/static/dist/.vite/manifest.json`
- Flask helper `vite_asset()` in `app/vite.py`:
  - JS files: Looks up hashed filename from manifest
  - CSS/other: Appends MD5 content hash as query string (e.g., `base.css?v=3544ab62`)
- Templates use `{{ vite_asset('path/to/file') }}` instead of `{{ url_for('static', ...) }}`
- Enables aggressive caching with `Cache-Control: max-age=31536000, immutable` for static assets

## CSS Architecture
Styles are split into modular files (processed by Vite for production):
- `base.css` — CSS variables, reset, typography
- `layout.css` — Grid layout, navbar, sidebar, footer
- `forms.css` — Form elements, buttons, validation
- `admin.css` — Admin-specific styles
- `public.css` — Public-facing page styles
- `utilities.css` — Helper classes
- `prism.css`, `prism-coy.css`, `prism-dark.css`, `prism-funky.css`, `prism-okaidia.css`, `prism-tomorrow.css` — Syntax highlighting themes

Import via `app/static/css/style.css` which aggregates all files.
- Self-hosted fonts (Inter, JetBrains Mono) via `@font-face`
- Responsive design with CSS grid and flexbox
- Dark mode is default; light theme toggled via `data-theme` attribute

## OpenAPI/Swagger UI
API documentation available at `/api/docs` via Flask-SwaggerUI:
- OpenAPI spec: `docs/openapi.yaml`
- Interactive testing interface at `/api/docs`
- All API endpoints documented with request/response schemas

## Feed Formats
Multiple feed formats supported:
- **RSS 2.0**: `/rss` (cached 5 min)
- **Atom 1.0**: `/atom`
- **JSON Feed 1.1**: `/json` (includes `content_html`)

Cache invalidation on post publish/unpublish/delete.

## Sitemap
Dynamic sitemap.xml generation at `/sitemap.xml`:
- Includes homepage, archive page, static pages, posts, and tags
- Archive page at `/archive`
- Uses streaming XML generation to handle large sites
- Respects `BASE_URL` from config

## Open Graph / Social Meta
Templates include Open Graph and Twitter Card meta tags:
- `og:image` and `twitter:image` in `post.html`, `page.html`, `index.html`
- Defaults to `/static/img/default-post.svg` when no image set
- Override in templates via `{% block og_image %}` and `{% block twitter_image %}`

## Scheduled Post Notifications
Dashboard widgets show scheduled posts count:
- `scheduled_posts_count` added to dashboard metrics
- View in admin dashboard at `/admin/`
- Displays number of posts scheduled for future publication

## Syntax Highlighting Themes
Configurable syntax highlighting for code blocks:
- `SiteSettings.syntax_theme` field stores selected theme
- Admin: `/admin/settings` has theme selector with 6 Prism themes
- Themes loaded dynamically based on `syntax_theme` setting
- Default theme: `prism` (standard)

## Newsletter Preview
Newsletter email preview feature:
- Admin: `/admin/newsletter/preview` route
- Preview button added to newsletter page
- Shows exactly what subscribers receive
- Uses existing newsletter template rendering

## Storage Abstraction Layer (`app/storage.py`)

Supports local filesystem and S3-compatible storage backends:

```bash
# Local storage (default)
export STORAGE_BACKEND=local

# S3 storage
export STORAGE_BACKEND=s3
export S3_BUCKET=my-bucket
export S3_REGION=us-east-1
export S3_ACCESS_KEY=...
export S3_SECRET_KEY=...
export S3_ENDPOINT=https://s3.amazonaws.com  # optional, for S3-compatible services
export S3_PUBLIC_URL=https://cdn.example.com   # optional, for custom CDN URLs
```

**Key classes:**
- `StorageBackend` — Abstract base class defining the interface
- `LocalStorageBackend` — Local filesystem storage
- `S3StorageBackend` — S3-compatible storage via boto3

**Key functions:**
- `get_storage()` — Returns the singleton storage instance
- `upload_with_processing()` — Saves an image with responsive variant generation

**Note:** Image processing (responsive variants) requires local file access. For S3, files are saved to a temp directory, processed locally, then uploaded to S3.

## Page View Buffer (`app/page_view_buffer.py`)

For high-traffic sites, page views can be buffered and batch-written to reduce database load:

```bash
# Enable buffer (flush when buffer reaches 100 views)
export PAGE_VIEW_BUFFER_SIZE=100

# Flush interval in seconds (default: 5)
export PAGE_VIEW_FLUSH_INTERVAL=10
```

**Key classes:**
- `PageViewBuffer` — Thread-safe buffer with background flush thread

**Key functions:**
- `record_page_view(post_id, referrer)` — Record a page view (uses buffer if enabled, else immediate)
- `shutdown_page_view_buffer()` — Graceful shutdown with buffer flush

**Note:** Buffer is disabled by default (`PAGE_VIEW_BUFFER_SIZE=0`). Enable for high-traffic deployments.

## Backup Encryption (`app/backup_encryption.py`)

GPG symmetric encryption for database backups:

```bash
# Set encryption passphrase (min 8 characters)
export BACKUP_ENCRYPTION_KEY=your-secure-passphrase

# Optional: specify cipher (default: AES256)
export BACKUP_GPG_CIPHER=AES256
```

**Key functions:**
- `encrypt_backup(data)` — Encrypt bytes using GPG symmetric encryption
- `decrypt_backup(data)` — Decrypt GPG-encrypted bytes
- `encrypt_backup_file(input_path, output_path)` — Encrypt a file
- `decrypt_backup_file(input_path, output_path)` — Decrypt a file
- `is_encryption_available()` — Check if GPG and key are configured

**CLI support via `backup.py`:**
```bash
python backup.py --encrypt              # Create encrypted backup
python backup.py --compress --encrypt   # Compressed and encrypted
python backup.py --decrypt backup.db.gpg  # Decrypt a backup file
```

**Admin UI:** The backup/restore route handles `.gpg` encrypted files transparently.
