# Agent Guidelines

Quick reference for AI agents working on this codebase.

See `plan.md` for the consolidated improvement plan.

## Running Tests

```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

Both `ADMIN_PASSWORD` and `SECRET_KEY` environment variables are **required**—the app raises `RuntimeError` when `create_app()` is called without them.

## Project Structure

```
run.py                  # Entry point—exports `app` (WSGI) and `asgi_app` (ASGI)
app/__init__.py         # App factory (`create_app()`), middleware, logging setup
app/config.py           # All config loaded from `config.toml` + env vars (+ validation)
app/models.py           # SQLAlchemy models (User, Post, Tag, Subscriber, PageView, ShareEvent, AdminSession, SiteSettings)
app/extensions.py       # Flask extensions (db, login_manager, migrate)
app/routes/public.py    # Public-facing routes
app/routes/admin/       # Admin routes package (requires login)
app/routes/admin/__init__.py  # Blueprint registration, shared helpers, admin_required
app/routes/admin/auth.py      # login, logout
app/routes/admin/posts.py     # dashboard, post CRUD, bulk operations
app/routes/admin/subscribers.py  # subscriber management
app/routes/admin/tags.py      # tag management
app/routes/admin/users.py     # user management
app/routes/admin/sessions.py  # session management
app/routes/admin/media.py     # media library
app/routes/admin/backup.py    # backup/restore
app/routes/admin/analytics.py # analytics page
app/routes/admin/newsletter.py # newsletter test
app/routes/admin/settings.py  # theme settings (presets, custom CSS, logo)
app/routes/rss.py       # RSS feed
app/csrf.py             # CSRF token handling
app/cache.py            # Tag count cache (double-checked locking)
app/search.py           # FTS5 full-text search with LIKE fallback
app/utils.py            # Slug generation, email validation, XML escaping, UTCDateTime type
app/base62.py           # Short URL encoding (base62)
app/scheduler.py        # APScheduler newsletter job (with file locking)
app/email.py            # SMTP email sending (with TLS via ssl.create_default_context)
app/markdown_config.py  # Shared nh3 allowed tags/attributes for markdown rendering
app/csv_utils.py        # Subscriber CSV export with formula injection prevention
DEPLOY.md               # Deployment guide
```

## Key Patterns

### Database
- SQLite stored in `instance/blog.db` (auto-created)
- Uses Flask-SQLAlchemy + Flask-Migrate (Alembic)
- Uses SQLAlchemy 2.0 patterns exclusively — `db.session.execute(select(Model).filter(...))` instead of `Model.query.filter(...)`
- Use `db.session.get(Model, id)` instead of `Model.query.get(id)` (avoids LegacyAPIWarning)
- Use `db.paginate(select(...), page=..., per_page=..., error_out=False)` for pagination

### Models
- `Post.slug` must be unique—use `_generate_unique_slug()` in `app/routes/admin/posts.py`
- `Post.updated_at` has automatic `onupdate` trigger in the model
- Tags use a many-to-many relationship via `post_tags` table
- `Post.short_code()` encodes the post ID to base62 for short URLs (`/s/<code>`)
- `Post.scheduled_publish_at` — optional datetime for scheduled auto-publish (scheduler checks every minute)
- `Subscriber.token` is a UUID hex used for confirm/unsubscribe links
- `Subscriber.expires_at` has no model default; the subscribe route sets it explicitly from config (`confirmation_expiry_hours`)
- All models have `__repr__` methods for debugging
- Database indexes: `ix_posts_published_created` on `(published, created_at)`, `ix_posts_published_at` on `published_at`, `ix_posts_newsletter_sent_at` on `newsletter_sent_at`, `ix_posts_published_updated` on `(published, updated_at)`, `ix_posts_published_slug` on `(published, slug)`
- `PageView` has composite index `ix_page_views_post_created` on `(post_id, created_at)`; `ShareEvent` has `ix_share_events_post_created` on `(post_id, created_at)`
- `Subscriber` has composite index `ix_subscribers_confirmed_unsubscribed` on `(confirmed, unsubscribed_at)`
- `AdminSession` tracks active admin sessions with `session_id`, `ip_address`, `user_agent`, `created_at`, `last_activity`; has index `ix_admin_sessions_user_id` on `user_id`
- `User.is_admin` — boolean, default False; first user auto-promoted to admin
- All DateTime columns use `UTCDateTime` TypeDecorator (stores naive UTC in SQLite, returns timezone-aware UTC on read)
- `utc_now()` returns timezone-aware UTC datetime

### Slugs
- `generate_slug()` in `app/utils.py` handles unicode normalization, lowercasing, and special char removal
- Both `Post.generate_slug()` and `Tag.generate_slug()` delegate to this utility
- `_generate_unique_slug()` in `app/routes/admin/helpers.py` handles collisions by appending counter suffixes (`slug-2`, `slug-3`, etc.)
- In `edit_post()`, slug is only regenerated when `title != post.title`

### Session
- `session["viewed_posts"]` tracks viewed post IDs to avoid double-counting page views—capped at `MAX_VIEWED_POSTS` entries from config (default 100, keeps most recent)
- Admin session expires after `SESSION_LIFETIME_HOURS` hours of inactivity (configurable in `config.toml`, default 24)
- `SESSION_COOKIE_SECURE` is set to `not app.debug` (HTTPS only in production)
- `SESSION_COOKIE_SAMESITE` is set to `"Lax"`
- Login creates an `AdminSession` record (tracks `session_id`, `ip_address`, `user_agent`); logout deletes it
- Session timeout also cleans up `AdminSession` record on expiry
- Sessions management UI at `/admin/sessions` (view, revoke)

### CSRF
- All POST routes require CSRF token
- Tests disable CSRF via `CSRF_ENABLED=False` + `TESTING=True` in config
- Token injected into templates via `context_processor`
- The `validate_csrf_token()` in `app/csrf.py` checks both form data (`csrf_token`) and HTTP header (`X-CSRF-Token`). No `_csrf_exempt` bypass exists.
- `main.js` sends `X-CSRF-Token` header for the `/api/track-share` JSON endpoint (reads from `<meta name="csrf-token">`)
- The `before_request` handler in `__init__.py` handles both CSRF validation and session timeout

### Configuration
- `config.toml` for site settings (title, author, email, etc.)
- Config validation is deferred to `create_app()` (not import time), so `config.py` can be imported without env vars set
- `SECRET_KEY` falls back to empty string; `ADMIN_PASSWORD` falls back to empty string; `RuntimeError` in `create_app()` catches the missing case
- Environment variables override config values:
  - `SECRET_KEY` (required)
  - `ADMIN_PASSWORD` (required)
  - `ADMIN_USERNAME` (optional, default: admin)
  - `SMTP_USER`, `SMTP_PASSWORD` (optional)
- Pagination and limits loaded from `config.toml [app]`: `max_viewed_posts`, `session_lifetime_hours`, `tag_cache_ttl_seconds`, `dashboard_per_page`, `subscribers_per_page`, `media_per_page`, `media_max_files`

### Authorization
- `admin_required` decorator in `app/routes/admin/__init__.py` combines `@login_required` with `is_admin` check
- Non-admin users get 403 on all admin routes (except login/logout)
- Login route rejects non-admin users with same "Invalid credentials" message as bad passwords
- `logout()` uses `@login_required` alone so non-admin authenticated users can still log out

### Theming
- `SiteSettings` model stores theme preferences in the database (single row, id=1)
- `THEME_PRESETS` dict in `models.py` defines available themes with CSS variable values
- Theme CSS variables injected via `<style>` tag in `base.html` and `admin/base.html`
- `inject_theme` context processor loads settings from DB on every request
- Settings page at `/admin/settings` allows preset selection, logo text, and custom CSS
- Custom CSS enabled via checkbox; rules injected after theme variables for override capability

## Common Tasks

### Add a new route
1. Add handler to `app/routes/public.py` or `app/routes/admin/`
2. Create template in `app/templates/`
3. Admin routes need `@admin_required` decorator (not `@login_required`)

### Add a new model
1. Define in `app/models.py`
2. Run `flask db migrate -m "description"`
3. Run `flask db upgrade`

### Modify templates
- Base template: `app/templates/base.html`
- Sidebar: `app/templates/_sidebar.html`
- Admin templates: `app/templates/admin/`

## Known Limitations

- **SQLite only**—no PostgreSQL/MySQL support configured
- **File uploads**—stored locally in `static/uploads/`, no S3 support
- **Newsletter scheduler**—runs in-process via APScheduler with `fcntl` file locking to prevent duplicate sends across workers (Unix only). `HAS_FCNTL` flag guards against `ImportError` on Windows. `_scheduler_running` is a `threading.Event` (set on init, cleared on shutdown via atexit, checked via `.is_set()`).
- **Newsletter dedup**—uses `newsletter_sent_at == None` filter to avoid resending
- **Subscriber.expires_at**—timezone-naive datetime used consistently throughout
- **ProxyFix configurable** via `PROXY_COUNT` env var (defaults to 1) in `app/__init__.py`
- **Email templates** use light-friendly colors (`#f6f8fa`, `#ffffff`, `#24292f`, `#0969da`)

## Rate Limiting

This codebase intentionally **does not include application-level rate limiting**. Rate limiting is expected to be handled by the reverse proxy, WAF, or CDN sitting in front of this application. Reasons:

- **Already handled upstream** — A properly configured reverse proxy (nginx, Caddy, traefik) or cloud provider (Cloudflare, AWS WAF, etc.) provides mature, tested rate limiting
- **Simplicity** — Application-level rate limiting adds complexity and overhead (in-memory state not shared across workers, memory growth concerns)
- **Single responsibility** — The app focuses on its core function (blogging); infrastructure concerns like rate limiting belong at the infrastructure layer

**Do not add rate limiting code to this project.** If you need per-IP or per-user rate limiting, configure it at the proxy/WAF level.

### Recommended Proxy Rules for Login Protection

The `/admin/login` endpoint is the primary attack surface. Configure your reverse proxy with these minimum rules:

```nginx
# nginx example
location /admin/login {
    limit_req zone=login burst=5 nodelay;
    limit_req_status 429;
}
```

Suggested thresholds:
- **5 requests per minute** per IP for `/admin/login`
- **20 requests per minute** per IP for other `/admin/*` routes
- **100 requests per minute** per IP for public routes

For Cloudflare, use a WAF custom rule matching `http.request.uri.path eq "/admin/login"` with managed challenge action.

## Lessons Learned

### SMTP Context Manager Gotcha
`with smtplib.SMTP() as server:` binds `server` at `__enter__` time. Reassigning `server` inside the block (e.g., for reconnection) creates a new local variable—the `with` statement's `__exit__` still calls the **original** object. For reconnectable connections, use manual `try/finally` instead.

### Cross-Blueprint Imports
Both `admin` routes and `public.py` import `invalidate_tag_cache` and `_get_tag_counts` from `app.cache` (extracted from `public.py` to avoid coupling). No cross-blueprint imports remain.

### Admin Routes Use `@admin_required`
All admin routes (except `login()` and `logout()`) use `@admin_required`, which combines `@login_required` with an `is_admin` check. Non-admin users get 403. The login route rejects non-admin users with "Invalid credentials" (same message as bad password to avoid username enumeration). `logout()` uses `@login_required` alone so non-admin authenticated users can still log out.

### `generate_slug` Edge Cases
Empty string and whitespace-only input both fall back to `"untitled"`. The initial `if not name` check catches `""`, and the final `return slug if slug else "untitled"` catches whitespace that becomes empty after processing.

### Edit Tool Matching
The `edit` tool matches `oldString` literally. Be careful with edits that insert code at a boundary—match enough surrounding context to avoid hitting unintended locations (e.g., `return redirect(...)` appears in multiple functions).

### `nh3` Config
The `nh3.clean()` allowed tags/attributes are defined in `app/markdown_config.py` and shared by `app/__init__.py` (markdown_safe filter) and `app/routes/admin.py` (preview endpoint). Modify allowed tags/attributes in the shared config only.

### Subscribe Exception Handling
The `subscribe()` route in `public.py` catches specific SMTP/connection exceptions from `send_confirmation()` to mask email failures from users (they're already subscribed in the DB). Programming errors are no longer swallowed.

### Subscribe Race Condition
Two concurrent subscribe requests with the same email can both pass the `scalar_one_or_none()` check, then both try to insert. The unique constraint causes an unhandled `IntegrityError` → 500. Fixed by wrapping insert + commit in `try/except IntegrityError` and re-querying on collision.

### IntegrityError Rollback Gotcha
In `edit_post()`, `db.session.rollback()` reverts ALL session changes, not just the failing commit. After rollback, SQLAlchemy marks all attributes as expired and will re-read from DB on next access. If you only re-set one field (e.g., slug) and commit, all other edits are silently lost. Always reapply all field changes after rollback.

### Newsletter Send Success Tracking
`send_newsletter()` returns `True` (all sent) or `False` (some failures). The scheduler checks this before marking posts as `newsletter_sent_at`. SMTP failures mid-batch trigger reconnection with retry; posts are only marked sent if all subscribers received the email.

### File Deletion Timing in edit_post() and bulk_operations()
Old image files are deleted *after* `db.session.commit()` to prevent dangling file references on rollback. In `edit_post()`, the old image filename is stored before mutation, then deleted only after a successful commit. In `bulk_operations()`, image paths are collected, the batch is committed, then files are removed in a separate loop. In `delete_post()`, the image is stored, the post record is deleted and committed, then the file is removed.

### `safe_delete_file` Utility
`safe_delete_file(filepath)` in `app/utils.py` wraps `os.remove()` with `FileNotFoundError` handling (returns `True`) and `OSError` logging (returns `False`). Use this instead of inline try/except blocks.

### LIKE Wildcard Escaping
Search input containing `%` or `_` causes unexpected pattern matching. Escape them before interpolating into LIKE patterns:
```python
escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
search_term = f"%{escaped}%"
Post.title.ilike(search_term, escape="\\")
```

### Image Upload Extension
`_save_image()` uses the detected magic byte type for the file extension, not the user-provided extension. This prevents Content-Type mismatches (e.g., JPEG saved as `.webp`).

### Token Enumeration Prevention
/confirm/<token> uses `scalar_one_or_none()` + `time.sleep(0.1)` to prevent token enumeration
- Invalid tokens return success (not 404) to avoid revealing valid tokens
- Already-confirmed subscribers get "Already confirmed." flash and redirect
- Same pattern as unsubscribe endpoint

### Double-Checked Locking for Caches
`_get_tag_counts()` in `app/cache.py` uses double-checked locking — the lock is held only for cache reads/writes, and the DB query runs outside the lock. This prevents slow queries from blocking all concurrent requests.

### FTS5 Search
- `app/search.py` — `init_fts()` creates FTS5 virtual table `posts_fts` (title, body, summary)
- FTS index synced via `sync_fts()` on post create/edit/publish/unpublish/delete
- `rebuild_fts()` does full index rebuild (`posts_fts rebuild`)
- `search(query)` in `app/search.py` returns matching post IDs from FTS5
- Search route (`app/routes/public.py`) imports `search` from `app/search.py`, falls back to LIKE on any error
- LIKE fallback filters by `Post.published == True` (FTS doesn't have a published column)
- FTS table check via `sqlite_master` query before attempting MATCH (avoids error spam)
- FTS MATCH query has `LIMIT 100` to prevent unbounded results
- `sync_fts()` is called BEFORE `db.session.commit()` in `new_post()`, `edit_post()`, and `bulk_operations()` publish/unpublish branches — if sync fails, the transaction rolls back cleanly. For delete routes, `remove_fts()` stays AFTER commit — stale FTS entries are handled gracefully by LIKE fallback.
- In `edit_post()`, `sync_fts()` is only called when searchable fields (title, body, summary, published) change

### Multi-Admin
- `flask create-admin` CLI command creates or promotes admin users (prompts for username/password)
- User management UI at `/admin/users` (list, create, delete, change password)
- Safety guards: cannot delete own account, cannot delete last admin, min 8-char password
- First user auto-promoted to admin in `create_app()` (deterministic: `order_by(User.id)`)
- **Password complexity:** Requires at least 3 of 4 character classes (lowercase, uppercase, digit, special). Minimum 8 characters. Existing tests use passwords like `Password123!` to meet requirements.

### UTCDateTime TypeDecorator
`UTCDateTime` in `app/utils.py` stores naive UTC in SQLite but always returns timezone-aware UTC. On bind, it strips timezone info (`.replace(tzinfo=None)`). On result, it adds UTC timezone to naive values. Existing naive rows are interpreted as UTC on read. This ensures all comparisons are timezone-aware while SQLite compatibility is maintained.

### FTS5 Empty Table Edge Case
`init_fts()` runs `CREATE VIRTUAL TABLE IF NOT EXISTS` then `INSERT OR IGNORE`. If the INSERT fails (e.g., `posts` table doesn't exist yet), the FTS table still exists but is empty. The search route checks `sqlite_master` for table existence before MATCH, but an empty FTS table returns no results. `_fts_search()` returns `[]` (not `None`) in this case, so the LIKE fallback kicks in via the `if post_ids:` check.

### SQLAlchemy 2.0 Query Patterns
All database queries use SQLAlchemy 2.0 style:
- `db.session.execute(select(Model).filter(...)).scalar_one_or_none()` for single results
- `db.session.execute(select(Model).filter_by(...)).scalars().all()` for multiple results
- `db.session.execute(select(func.count(...))).scalar_one()` for counts
- `db.session.execute(delete(Model).where(...))` for deletes
- `db.paginate(select(...), page=..., per_page=..., error_out=False)` for pagination

### Standalone Utility Scripts
`backup.py` is a standalone utility script (not part of the Flask app). It should not import from `app.*` modules since it needs to work independently. Use hardcoded defaults or CLI args rather than config imports.

### Dependencies
`pygments` was previously listed in `requirements.txt` but is no longer installed — Prism.js handles all syntax highlighting.

### `assert` Statements Under `python -O`
`assert` is stripped when Python runs with `-O` (optimize flag). Never use `assert` for runtime safety checks — use `if not ... :` with proper error handling instead. The search route previously used `assert` to validate FTS5 results, which would silently fail in optimized deployments.

### `db.session.close_all()` Deprecation
`db.session.close_all()` is deprecated since SQLAlchemy 1.3 and will be removed. Use `db.engine.dispose()` instead — it closes all connections in the pool, making `close_all()` redundant.

### FTS5 Special Character Escaping
`search()` in `app/search.py` uses `_escape_fts_term()` to handle FTS5 special characters. The helper strips leading/trailing hyphens (negation), replaces colons (column specifier), and escapes double quotes by doubling. Empty terms are filtered out. The `except Exception` fallback to LIKE handles any remaining edge cases.

### WAL Mode
SQLite uses WAL (Write-Ahead Logging) mode by default, enabling concurrent reads during writes and improving performance. Enabled via `PRAGMA journal_mode=WAL` on database connection.

### Flask Rebuild Search CLI
`flask rebuild-search` command rebuilds the FTS5 search index from scratch. Useful after importing data or recovering from index corruption.

### Analytics Caching
Dashboard analytics queries are cached in-memory with a 5-minute TTL (`_analytics_cache` in `app/routes/admin/helpers.py`) to prevent slow page loads. Cache key is the `days` parameter. Cache is invalidated via `invalidate_analytics_cache()` on post CRUD operations and bulk operations (publish, unpublish, delete). The cache has a max size of 16 entries (LRU eviction). In tests, clear the cache with `admin_module._analytics_cache.clear()` if a prior test populated it for the same cache key. Dashboard metrics have a separate 2-minute TTL cache (`_dashboard_metrics_cache` in `app/routes/admin/posts.py`).

### Subscriber CSV Export
`/admin/subscribers/export` streams a CSV of all confirmed subscribers (columns: email, subscribed_at, confirmed_at). Uses `StreamingHTTPResponse` for memory efficiency with large lists.

### Subscriber Bulk Operations
- `POST /admin/subscribers/bulk` — handles `delete` and `export` actions for selected subscribers
- Checkbox selection on subscribers page with "Select All" toggle

### Admin Keyboard Shortcuts
- `Ctrl+S` / `Cmd+S` — save draft (admin pages only — must be scoped with `admin-body` check)
- `Ctrl+Shift+P` / `Cmd+Shift+P` — toggle preview pane
- `Ctrl+Enter` / `Cmd+Enter` — publish post
- `?` — show keyboard shortcuts modal
- `Esc` — close modal
- `g` then `d/p/s/t` — vim-style navigation (Dashboard, Posts, Subscribers, Tags). 500ms timeout between keys. (admin pages only — must be scoped)
- Modal defined in `app/templates/admin/base.html` (`#keyboard-help` with `.modal-overlay` class)
- JS handlers in `app/static/js/main.js` use `(e.ctrlKey || e.metaKey)` for cross-platform support
- `e.preventDefault()` scoped inside each `if (target)` block — only prevents default when target element exists
- Close button and click-outside-to-close bound once on page load (not on each `?` press)
- Modal CSS in `style.css` under "Keyboard Shortcuts Modal" section (CSP-compliant, no inline styles)
- **All admin keyboard shortcuts must be guarded with `document.body.classList.contains('admin-body')` to prevent firing on public pages**

### Test Fixture Organization
- `tests/conftest.py` defines fixtures
- Use `@pytest.fixture` with descriptive names
- Fixtures should be scoped appropriately (`function`, `session`)
- Avoid importing app fixtures in unit test files that don't need them

### Security Headers (Additional)
- `X-Download-Options: noopen` — prevents file execution in download context
- `X-Permitted-Cross-Domain-Policies: none` — prevents Adobe Flash cross-domain requests

### Upload File Size Validation
All image uploads validated against 10MB limit. Magic byte detection rejects files that exceed this limit before processing. Configurable via `max_upload_size` in `config.toml [app]`.

### Session Timeout
Admin sessions expire after inactivity (default 24 hours, configurable via `session_lifetime_hours`). Timeout checked on every request in `before_request` handler. Session extended on activity.

### CSS Variable Deduplication
The codebase had duplicate CSS variables (`--bg-primary` = `--bg`, `--text-secondary` = `text-muted`). When consolidating, check which variable is the "canonical" one by seeing which is used more broadly, then replace all uses of the duplicate with the canonical name before removing it.

### CSV Export
CSV generation is handled by `generate_subscribers_csv()` in `app/csv_utils.py`. Both `export_subscribers()` and `subscribers_bulk()` use this shared utility. Cells starting with `=`, `+`, `-`, `@` are prefixed with `'` to prevent CSV formula injection.

### Magic Numbers in Config
The following magic numbers are configurable via `config.toml`:
- `max_upload_size` (default 10MB) — maximum uploaded file size
- `smtp_timeout` (default 30s) — SMTP connection timeout
- `export_batch_size` (default 500) — subscriber export batch size for streaming
- `fts_result_limit` (default 100) — FTS5 search result limit
- `token_enumeration_delay` (default 0.1s) — constant-time delay for confirm/unsubscribe routes

### Mobile Nav Class
CSS animation is defined on `.nav-links.open` (matches JS toggle). The `::before` backdrop overlay is gated on `.nav-links.open::before`.

### Nested Forms in Dashboard
The dashboard bulk form (`<form id="bulk-form">`) previously wrapped the entire post list, with per-post "Reset NL" and "Delete" as nested `<form>` elements inside it. HTML spec forbids nested forms — browsers implicitly close the outer form when encountering the inner one, breaking bulk operations. The fix uses `form="bulk-form"` attribute on checkboxes to associate them with the bulk form without nesting, while per-post forms remain outside the bulk form entirely.

### CSS Duplicate Rule Blocks
The codebase had two separate `.flash` CSS rule blocks in `style.css` — one with visual properties (padding, border-radius) and one with layout properties (position, overflow). While CSS merges them correctly, this is confusing and error-prone. When editing CSS, check for duplicate selectors that may have been split across sections.

### Dead CSS from Class Name Mismatches
The codebase had hover rules for `.share-btn.twitter:hover` etc. but the actual HTML uses `.share-btn.share-twitter`. The CSS selectors with a space (descendant combinator) vs dot (compound selector) behave differently. When CSS rules don't seem to work, verify the actual class names in the HTML match the CSS selectors exactly.

### Lazy Image Progressive Enhancement
Lazy images use `opacity: 0` by default and JS adds `.loaded` class. Without a `.js` class gate on `<html>`, images remain invisible when JS fails. The pattern is: add `document.documentElement.classList.add('js')` as the first JS line, then prefix CSS rules with `.js` so they only apply when JS is available.

### Admin Page Detection in JS
The `<body>` in `admin/base.html` has `class="admin-body"`. Use `document.body.classList.contains('admin-body')` to scope JS handlers that should only run on admin pages (keyboard shortcuts, vim navigation, modal handlers). Public pages should not have admin-specific behavior.

### Mobile Menu Toggle
The mobile hamburger menu button is **created dynamically in JavaScript** (`main.js` lines 162-205), not in HTML templates. It toggles `.open` class on `.nav-links`, swaps icons, and closes on outside click and Escape key. The CSS class `.mobile-menu-toggle` exists in `style.css` but the button element is injected by JS.

### `ConnectionError` is Subclass of `OSError`
`ConnectionError` inherits from `OSError`. Do not catch both in the same except clause — `ConnectionError` is redundant when `OSError` is already caught.

### Reading Progress Bar
The `.reading-progress` div exists in `post.html` (scoped to article pages only) with CSS transition. JS driver is in `main.js:92-97` — calculates scroll percentage and updates width on scroll.

## Assets

- **No external assets**—all fonts (Inter, JetBrains Mono) are self-hosted in `app/static/fonts/`
- **Prism.js** is self-hosted (`app/static/js/prism.min.js` and `app/static/js/prism-languages.js`) with extended language definitions (Python, Bash, JSON, Markdown, SQL, TypeScript, Go, Rust, C/C++, YAML, TOML, Docker, PHP, Ruby, Swift)
- Do not add external CDN links (Google Fonts, CDNs, etc.)

## Dependencies (Python 3.14 compatible)

See `requirements.txt`. Key packages:
- Flask 3.1+
- SQLAlchemy 2.0+ (via Flask-SQLAlchemy)
- Werkzeug 3.1+ (password hashing, security)
- asgiref 3.8+ (ASGI adapter for Granian)
- nh3 0.2+ (HTML sanitization—**not** `bleach`, which is deprecated since 2023)

## Email

- Uses `smtplib` directly (no Celery/Redis dependency)
- SMTP connection uses `starttls()` with `ssl.create_default_context()` for TLS certificate verification
- Individual emails (`_send_email()`) open a fresh SMTP connection per call
- Newsletter batch (`send_newsletter()`) reuses a single SMTP connection via `_connect_smtp()` helper in `email.py`
- Per-subscriber exception handling; failures are logged but don't stop the batch
- On `SMTPServerDisconnected`, reconnects and retries the failed send; aborts if reconnection fails
- **Do not use `with smtplib.SMTP() as server:` for newsletter batch** — reassigning `server` inside the `with` block doesn't affect the context manager's exit handler. Use manual `try/finally` instead (see `send_newsletter()`).
- Progress logged every 50 subscribers for operational visibility

## Admin Routes

- Tag names validated against `^[a-zA-Z0-9\s\-]+$` regex (ASCII only); invalid names flash a warning to the user
- Image uploads validated via magic byte detection (`_detect_image_type` in `app/routes/admin/__init__.py`) — no Pillow dependency required
- `_save_image()` returns `(filename, error_message)` tuple; callers flash the error if present
- Allowed extensions: `png, jpg, jpeg, gif, webp`

## Newsletter Reset

- Route: `POST /admin/newsletter-reset/<post_id>` (login required)
- Resets `newsletter_sent_at` to `None` and `newsletter_attempts` to `0` so the post is picked up by the next newsletter run
- Dashboard shows "Reset NL" button on posts that have already been sent
- Tooltip shows attempt count when > 0

## Backup/Restore

- Route: `GET /admin/backup` (login required) — lists all backups
- `POST /admin/backup/create` — creates backup (optional `compress` checkbox for gzip)
- `GET /admin/backup/download/<filename>` — downloads backup file
- `POST /admin/backup/restore/<filename>` — restores database from backup (requires app restart)
- `POST /admin/backup/delete/<filename>` — deletes a backup file
- Backups stored in `instance/backups/` directory
- Filename validation via `^blog_\d{8}_\d{6}\.db(\.gz)?$` regex (prevents path traversal)
- Compressed backup restore: detects `.gz` suffix and decompresses via `gzip` to temp file before copying

## Templates

- `{{ post.body | markdown_safe | safe }}` renders markdown with HTML sanitization via `nh3`
- The `markdown_safe` filter allows: `p, br, strong, em, u, s, code, pre, blockquote, h1-h6, ul, ol, li, a, img, table, thead, tbody, tr, th, td, hr, span, div`
- Allowed attributes: `a[href,title]`, `img[src,alt,title,width,height]`, `span/div[*][class]`
- **nh3 note**: The `rel` attribute for `<a>` tags is managed automatically by nh3—do not include it in allowed attributes (causes a panic)
- OG image meta tag is already implemented in `post.html:8`
- CSP header: `default-src 'self'` with `style-src 'self' 'nonce-<random>'`, `style-src-attr 'unsafe-inline'`, `font-src 'self'`, `img-src 'self' data:`, `script-src 'self' 'nonce-<random>'`, `connect-src 'self'`, `frame-src 'none'`, `frame-ancestors 'none'`
- **No inline event handlers** — delete confirmation uses `data-confirm` attribute handled by `main.js` (CSP compliance). All inline `onchange` handlers have been migrated to `main.js`.
- Nonce generated per-request in `before_request` handler via `g.csp_nonce`, injected into templates via `context_processor` as `csp_nonce`
- `<style>` and `<script>` tags in templates use `nonce="{{ csp_nonce }}"` attribute
- Inline `style=""` attributes allowed via `style-src-attr 'unsafe-inline'` for data-driven styles (chart heights)

## Security Headers

The `set_security_headers` after-request handler sets:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-Download-Options: noopen`
- `X-Permitted-Cross-Domain-Policies: none`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy` (self-only sources, `style-src` uses nonces, `style-src-attr 'unsafe-inline'` for data-driven styles, `frame-src 'none'` blocks all iframe embedding)
- `Cache-Control: public, max-age=31536000, immutable` (static assets only)

## Dark/Light Mode

- Theme toggle uses `[data-theme="light"]` on `<html>` element
- Light mode CSS variables override dark defaults in `style.css`
- Default dark mode: no `data-theme` attribute (uses `:root` variables)
- Preference stored in `localStorage` key `theme`; defaults to `prefers-color-scheme`
- Toggle button injected into navbar via JS (both public and admin)
- SVG sun/moon icons swap on toggle

## Navbar Scroll Behavior

- CSS class toggle `.navbar-shrunk` replaces inline style manipulation
- `transition: padding 0.2s ease` on `.navbar` (disabled via `prefers-reduced-motion`)
- `navbar.classList.toggle('navbar-shrunk', window.scrollY > 60)` in scroll handler

## Post Enhancements

- **Table of Contents:** Generated from `.prose h2/h3` headings, sticky sidebar on desktop, IntersectionObserver highlights current section. Appears when article has 3+ headings.
- **Last Updated Indicator:** Shows "Updated: {date}" when `post.updated_at > post.created_at`.
- **Image Lightbox:** Click `.prose img` opens full-size overlay. Escape/click-outside to close.
- **Breadcrumbs:** Home > Tag > Post Title trail on post and tag pages.

## Draft Autosave

- Saved to `localStorage` with key `draft-<post_id>` or `draft-new`
- Throttled to every 5 seconds on any editor input
- On load: if draft exists and textarea is empty, prompts to restore
- Cleared on successful form submit
- Shows "Saving..." / "Draft saved" indicator via `#autosave-status` element

## Live Markdown Preview

- Split editor layout: textarea left, preview right (CSS grid `1fr 1fr`)
- Debounced 300ms rendering via `POST /admin/preview-markdown`
- Reuses the same `nh3.clean()` config as `markdown_safe_filter`
- Preview pane uses `.prose` class for consistent styling

## File Upload Cleanup

- `edit_post()`: when replacing an image, old file is removed *after* successful commit
- `delete_post()`: removes image file *after* successful post deletion commit
- `bulk_operations()`: collects image paths, commits deletions, then removes files
- All file deletions use `safe_delete_file()` from `app/utils.py`

## Orphan Tag Cleanup

- `_cleanup_orphan_tags()` in `app/routes/admin/__init__.py` removes tags with zero associated posts
- Does NOT call `db.session.commit()` — callers are responsible for committing
- Called BEFORE `db.session.commit()` in `edit_post`, `delete_post`, and `bulk_operations` (delete branch)
- Called after `invalidate_tag_cache()` in `delete_post()`, `edit_post()`, and `bulk_operations()` delete branch

## Dashboard Search/Filter

- Search query param `?q=` filters posts by title using `ilike`
- Status param `?status=published|draft|all` filters by publication state
- Pagination preserves both `q` and `status` params in links
- LIKE wildcards (`%`, `_`) are escaped in dashboard search input

## Preview Mode

- Route: `GET /admin/preview/<post_id>` (login required)
- Renders `_post_content.html` partial via `{% include %}`
- Shows yellow `.preview-banner` above content
- Works for both drafts and published posts

## Template Partials

- `_post_content.html` contains the article markup shared between `post.html` and `admin/preview.html`
- Uses `{% include %}` (not `{% extends %}`) so it doesn't conflict with base template blocks
- Relies on `author_name`, `author_avatar`, `author_role` from context processor

## Bulk Operations

- Dashboard has checkboxes on each post row + "Select All" toggle
- Form uses `form="bulk-form"` attribute on checkboxes to associate without nesting (never nest `<form>` elements)
- Three submit buttons: Publish, Unpublish, Delete — each sends `action` value
- Destructive actions use `data-confirm-bulk` attribute (not inline `onclick`)
- Bulk action buttons hidden by default; shown via JS when checkboxes are checked
- Image cleanup included for bulk delete

## Button Conventions

Use button classes consistently across admin templates:

| Class | Usage |
|-------|-------|
| `btn btn-primary` | Primary submit action (Create Post, Save Changes) |
| `btn btn-small` | Default for actions in lists and tables |
| `btn btn-small btn-ghost` | Secondary actions (Edit, Export, Back) |
| `btn btn-small btn-danger` | Destructive actions (Delete) in lists |

Examples:
```html
<!-- Primary action in forms -->
<button type="submit" class="btn btn-primary">Save Changes</button>

<!-- Secondary action in lists/tables -->
<a href="..." class="btn btn-small btn-ghost">Edit</a>

<!-- Destructive action in lists/tables -->
<button type="submit" class="btn btn-small btn-danger">Delete</button>

<!-- Inline forms in header -->
<a href="..." class="btn btn-small btn-ghost">Back</a>
```

## Tag Caching

- `_get_tag_counts()` in `app/cache.py` uses an in-memory cache with configurable TTL (default 60s, via `tag_cache_ttl_seconds` in `config.toml [app]`)
- Cache uses double-checked locking for thread-safe operations
- `invalidate_tag_cache()` called on tag create/rename/delete and post CRUD operations
- Cache returns a copy to prevent external mutation

## Post Scheduling

- `Post.scheduled_publish_at` — optional datetime for scheduled auto-publish
- Scheduler checks every minute (`publish_scheduled_posts` in `scheduler.py`)
- Auto-publishes posts where `published == False` and `scheduled_publish_at <= now`
- Sets `published = True`, `published_at = now`, clears `scheduled_publish_at`, syncs FTS
- Editor has `datetime-local` input for scheduling; leave empty for immediate publishing
- Both `new_post()` and `edit_post()` handle `scheduled_publish_at` from form data

## Request ID Logging

- Each request gets a unique 8-char hex ID (`g.request_id`)
- Log format includes `[%(request_id)s]` for correlating log entries per request
- `RequestIdFilter` in `configure_logging()` safely handles missing request context

## Session Learnings

### Test Env Var Setup
Environment variables (`SECRET_KEY`, `ADMIN_PASSWORD`) must be set **before** importing `app` modules in test files. `config.py` reads `os.environ` at module import time and caches the values as module-level constants. Setting `os.environ` inside a pytest fixture does NOT retroactively update already-imported constants. Always set env vars at the top of `conftest.py` before any `from app import ...` statements.

### `@event.listens_for` Inside `app_context()`
Registering `@event.listens_for(Engine, "connect")` inside `with app.app_context():` is correct — the listener is registered once during app creation and fires for every new connection from the pool. The PRAGMA executed inside the listener applies per-connection.

### Modal Focus Trap Scope
When adding event listeners inside a `forEach` loop, ensure the listener is defined **inside** the callback so the variable is correctly scoped. A listener defined outside the loop will capture the last iteration's value due to JavaScript closure behavior.

### `e.key === 'ShiftTab'` is Dead Code
There is no `'ShiftTab'` key event. Shift+Tab fires `e.key === 'Tab'` with `e.shiftKey === true`. Check `e.shiftKey` instead of checking for a non-existent key value.

### Empty State SVG Icons
The codebase already uses SVG data URI `background-image` for empty state icons (not emoji `content`). When editing `.empty-state::before`, preserve the SVG background pattern.

### Admin Routes Already Split
The admin routes are already organized as a package (`app/routes/admin/`) with separate modules for auth, posts, subscribers, tags, users, sessions, media, backup, analytics, and newsletter. Do not attempt to split them further.

### Plan Consolidation
The improvement plan is in `plan.md` organized into parallelizable waves. Items within each wave can be worked on simultaneously by sub-agents unless dependency notes say otherwise. The `plans/` directory has been removed.

### File Reference Verification
Line numbers in plans and documentation can drift. Always verify file references against the actual codebase before making edits. Use `grep` or `read` to confirm locations.

### `_generate_unique_slug` Location
`_generate_unique_slug()` is in `app/routes/admin/helpers.py` at line 226 (not 230). It is called by `new_post()` and `edit_post()` in `app/routes/admin/posts.py`.

### `_get_posts_query` `order_by` Parameter Is Used
The `order_by` parameter in `_get_posts_query()` (`app/routes/admin/helpers.py:84`) is NOT dead code — it has a default fallback (`Post.updated_at.desc()`) and is actively applied to the query. Do not remove it.

### Plan Consolidation Process
When consolidating multiple plan files, verify each item against the actual codebase before including it. Many items from earlier plan iterations may have already been implemented. Use a "Already Completed" section in the consolidated plan to track what was done.

### Share Tracking Implementation
Share tracking in `main.js` uses `navigator.sendBeacon()` as the primary method with `fetch(keepalive: true)` as fallback. The handler is attached to `.share-btn[data-platform]` elements.

### Media File Listing Optimization
`app/routes/admin/media.py` uses `heapq.nlargest()` for efficient file listing instead of loading all files into memory and sorting. This is the recommended pattern for file-based pagination.

### Error Page Partial Pattern
`app/templates/_error.html` is used by 404.html but 500.html has its own inline markup. When consolidating error pages, enhance the partial with optional flags (`show_search`, `show_suggestions`) rather than duplicating markup.
