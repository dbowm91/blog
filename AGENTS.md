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
app/models.py           # SQLAlchemy models (User, Post, Tag, Subscriber, PageView, ShareEvent)
app/extensions.py       # Flask extensions (db, login_manager, migrate)
app/routes/public.py    # Public-facing routes
app/routes/admin.py     # Admin routes (requires login)
app/routes/rss.py       # RSS feed
app/csrf.py             # CSRF token handling
app/cache.py            # Tag count cache (double-checked locking)
app/search.py           # FTS5 full-text search with LIKE fallback
app/utils.py            # Slug generation, email validation, XML escaping, UTCDateTime type
app/base62.py           # Short URL encoding (base62)
app/scheduler.py        # APScheduler newsletter job (with file locking)
app/email.py            # SMTP email sending (with TLS via ssl.create_default_context)
app/markdown_config.py  # Shared nh3 allowed tags/attributes for markdown rendering
```

## Key Patterns

### Database
- SQLite stored in `instance/blog.db` (auto-created)
- Uses Flask-SQLAlchemy + Flask-Migrate (Alembic)
- Uses SQLAlchemy 2.0 patterns exclusively — `db.session.execute(select(Model).filter(...))` instead of `Model.query.filter(...)`
- Use `db.session.get(Model, id)` instead of `Model.query.get(id)` (avoids LegacyAPIWarning)
- Use `db.paginate(select(...), page=..., per_page=..., error_out=False)` for pagination

### Models
- `Post.slug` must be unique—use `_generate_unique_slug()` in admin.py
- `Post.updated_at` has automatic `onupdate` trigger in the model
- Tags use a many-to-many relationship via `post_tags` table
- `Post.short_code()` encodes the post ID to base62 for short URLs (`/s/<code>`)
- `Subscriber.token` is a UUID hex used for confirm/unsubscribe links
- `Subscriber.expires_at` has no model default; the subscribe route sets it explicitly from config (`confirmation_expiry_hours`)
- All models have `__repr__` methods for debugging
- Database indexes: `ix_posts_published_created` on `(published, created_at)`, `ix_posts_published_at` on `published_at`, `ix_posts_newsletter_sent_at` on `newsletter_sent_at`, `ix_posts_published_updated` on `(published, updated_at)`
- `PageView` has composite index `ix_page_views_post_created` on `(post_id, created_at)`; `ShareEvent` has `ix_share_events_post_created` on `(post_id, created_at)`
- `Subscriber` has composite index `ix_subscribers_confirmed_unsubscribed` on `(confirmed, unsubscribed_at)`
- `User.is_admin` — boolean, default False; first user auto-promoted to admin
- All DateTime columns use `UTCDateTime` TypeDecorator (stores naive UTC in SQLite, returns timezone-aware UTC on read)
- `utc_now()` returns timezone-aware UTC datetime

### Slugs
- `generate_slug()` in `app/utils.py` handles unicode normalization, lowercasing, and special char removal
- Both `Post.generate_slug()` and `Tag.generate_slug()` delegate to this utility
- `_generate_unique_slug()` in `app/routes/admin.py` handles collisions by appending counter suffixes (`slug-2`, `slug-3`, etc.)
- In `edit_post()`, slug is only regenerated when `title != post.title`

### Session
- `session["viewed_posts"]` tracks viewed post IDs to avoid double-counting page views—capped at `MAX_VIEWED_POSTS` entries from config (default 100, keeps most recent)
- Admin session expires after `SESSION_LIFETIME_HOURS` hours of inactivity (configurable in `config.toml`, default 24)
- `SESSION_COOKIE_SECURE` is set to `not app.debug` (HTTPS only in production)
- `SESSION_COOKIE_SAMESITE` is set to `"Lax"`

### CSRF
- All POST routes require CSRF token
- Tests disable CSRF via `CSRF_ENABLED=False` + `TESTING=True` in config
- Token injected into templates via `context_processor`
- The `validate_csrf_token()` in `__init__.py` checks both form data (`csrf_token`) and HTTP header (`X-CSRF-Token`)
- `main.js` sends `X-CSRF-Token` header for the `/api/track-share` JSON endpoint (reads from `<meta name="csrf-token">`)
- The `before_request` handler in `__init__.py` handles both CSRF validation and session timeout
- The handler checks for `_csrf_exempt` attribute on view functions (currently unused by any route)

### Configuration
- `config.toml` for site settings (title, author, email, etc.)
- Config validation is deferred to `create_app()` (not import time), so `config.py` can be imported without env vars set
- `SECRET_KEY` falls back to empty string; `RuntimeError` in `create_app()` catches the missing case
- Environment variables override config values:
  - `SECRET_KEY` (required)
  - `ADMIN_PASSWORD` (required)
  - `ADMIN_USERNAME` (optional, default: admin)
  - `SMTP_USER`, `SMTP_PASSWORD` (optional)
- Pagination and limits loaded from `config.toml [app]`: `max_viewed_posts`, `session_lifetime_hours`, `tag_cache_ttl_seconds`, `dashboard_per_page`, `subscribers_per_page`, `media_per_page`, `media_max_files`

### Authorization
- `admin_required` decorator in `app/routes/admin.py` combines `@login_required` with `is_admin` check
- Non-admin users get 403 on all admin routes (except login/logout)
- Login route rejects non-admin users with same "Invalid credentials" message as bad passwords
- `logout()` uses `@login_required` alone so non-admin authenticated users can still log out

## Common Tasks

### Add a new route
1. Add handler to `app/routes/public.py` or `app/routes/admin.py`
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
- **Newsletter scheduler**—runs in-process via APScheduler with `fcntl` file locking to prevent duplicate sends across workers (Unix only). `HAS_FCNTL` flag guards against `ImportError` on Windows.
- **Newsletter dedup**—uses `newsletter_sent_at == None` filter to avoid resending
- **Subscriber.expires_at**—timezone-naive datetime used consistently throughout
- **No upper version bounds** in `requirements.txt`—all dependencies use `>=` only
- **ProxyFix hardcoded** to `x_for=1, x_proto=1, x_host=1` in `app/__init__.py`
- **Dashboard N+1**—`Post.tags` relationship is lazy-loaded in dashboard query (no `joinedload`)
- **`_cleanup_orphan_tags()`** calls its own `db.session.commit()`—callers should be aware
- **`confirm` endpoint** does not check if subscriber is already confirmed before writing
- **`restore_backup`** does not close DB connections before overwriting the database file
- **Email templates** use hardcoded GitHub-dark colors (`#0d1117`, `#161b22`, `#e6edf3`)—not suitable for light-mode email clients

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
Both `admin.py` and `public.py` import `invalidate_tag_cache` and `_get_tag_counts` from `app.cache` (extracted from `public.py` to avoid coupling). No cross-blueprint imports remain.

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
/confirm/<token> now uses `first()` + `time.sleep(0.1)` to prevent token enumeration
- Invalid tokens return success (not 404) to avoid revealing valid tokens
- Same pattern as unsubscribe endpoint

### Double-Checked Locking for Caches
`_get_tag_counts()` in `app/cache.py` uses double-checked locking — the lock is held only for cache reads/writes, and the DB query runs outside the lock. This prevents slow queries from blocking all concurrent requests.

### FTS5 Search
- `app/search.py` — `init_fts()` creates FTS5 virtual table `posts_fts` (title, body, summary)
- FTS index synced via `sync_fts()` on post create/edit/publish/unpublish/delete
- `rebuild_fts()` does full index rebuild (`posts_fts rebuild`)
- Search route (`app/routes/public.py`) tries FTS5 MATCH first, falls back to LIKE on any error
- LIKE fallback filters by `Post.published == True` (FTS doesn't have a published column)
- FTS table check via `sqlite_master` query before attempting MATCH (avoids error spam)
- FTS MATCH query has `LIMIT 100` to prevent unbounded results
- `sync_fts()` is called BEFORE `db.session.commit()` in `new_post()`, `edit_post()`, and `bulk_operations()` publish/unpublish branches — if sync fails, the transaction rolls back cleanly. For delete routes, `remove_fts()` stays AFTER commit — stale FTS entries are handled gracefully by LIKE fallback.
- In `edit_post()`, `sync_fts()` is only called when searchable fields (title, body, summary, published) change

### Multi-Admin
- `flask create-admin` CLI command creates or promotes admin users (prompts for username/password)
- User management UI at `/admin/users` (list, create, delete, change password)
- Safety guards: cannot delete own account, cannot delete last admin, min 8-char password
- First user auto-promoted to admin in `create_app()`

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

- Tag names validated against `^[\w\s-]+$` regex; invalid names flash a warning to the user
- Image uploads validated via magic byte detection (`_detect_image_type` in `admin.py`) — no Pillow dependency required
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

## Templates

- `{{ post.body | markdown_safe | safe }}` renders markdown with HTML sanitization via `nh3`
- The `markdown_safe` filter allows: `p, br, strong, em, u, s, code, pre, blockquote, h1-h6, ul, ol, li, a, img, table, thead, tbody, tr, th, td, hr, span, div`
- Allowed attributes: `a[href,title]`, `img[src,alt,title,width,height]`, `span/div[*][class]`
- **nh3 note**: The `rel` attribute for `<a>` tags is managed automatically by nh3—do not include it in allowed attributes (causes a panic)
- OG image meta tag is already implemented in `post.html:8`
- CSP header: `default-src 'self'` with `style-src 'self' 'unsafe-inline'`, `font-src 'self'`, `img-src 'self' data:`, `script-src 'self'`, `connect-src 'self'`, `frame-src 'none'`, `frame-ancestors 'none'`
- **No inline event handlers** — delete confirmation uses `data-confirm` attribute handled by `main.js` (CSP compliance)

## Security Headers

The `set_security_headers` after-request handler sets:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy` (self-only sources, `style-src` includes `'unsafe-inline'` for CSS custom properties used in animation delays, `frame-src 'none'` blocks all iframe embedding)
- `Cache-Control: public, max-age=31536000, immutable` (static assets only)

## Dark/Light Mode

- Theme toggle uses `[data-theme="light"]` on `<html>` element
- Light mode CSS variables override dark defaults in `style.css`
- Default dark mode: no `data-theme` attribute (uses `:root` variables)
- Preference stored in `localStorage` key `theme`; defaults to `prefers-color-scheme`
- Toggle button injected into navbar via JS (both public and admin)
- SVG sun/moon icons swap on toggle

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

- `_cleanup_orphan_tags()` in `admin.py` removes tags with zero associated posts
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
- Form wraps the entire post list with `action="/admin/bulk"`
- Three submit buttons: Publish, Unpublish, Delete — each sends `action` value
- Destructive actions use `data-confirm-bulk` attribute (not inline `onclick`)
- Image cleanup included for bulk delete

## Tag Caching

- `_get_tag_counts()` in `app/cache.py` uses an in-memory cache with configurable TTL (default 60s, via `tag_cache_ttl_seconds` in `config.toml [app]`)
- Cache uses double-checked locking for thread-safe operations
- `invalidate_tag_cache()` called on tag create/rename/delete and post CRUD operations
- Cache returns a copy to prevent external mutation

## Remaining Plan Items

All items from `plan.md` have been completed:
- **Wave 1**: 7 trivial cleanup items (dead code, dependency removal, minor fixes) ✅
- **Wave 2**: 2 security/robustness items (X-XSS-Protection header, FTS5 assertion) ✅
- **Wave 3**: SQLAlchemy 2.0 migration (~51 occurrences across 6 files) ✅
- **Wave 4**: Page view optimization (deferred/monitoring only)

Previously completed from earlier plan iterations:
- IntegrityError retry paths in `new_post()`/`edit_post()` — done
- Security headers, bug fixes, performance improvements — done
- Timezone-aware datetimes, FTS5 search, multi-admin, backup/restore UI — done
- Sitemap streaming, eager loading, centralized pagination, SMTP validation — done
