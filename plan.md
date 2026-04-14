# Improvement Plan

Consolidated from plans 2-9 (code quality, security, performance, developer experience, and feature enhancements). All items from the original plan.md (waves 1-7, items 1-29) were completed in previous sessions.

---

## Summary of Remaining Items

| Wave | Category | Items | Priority |
|------|----------|-------|----------|
| 1 | Critical Bugs | 9 | Critical |
| 2 | Security Fixes | 12 | High |
| 3 | Exception Handling | 6 | Medium |
| 4 | Performance | 15 | Medium |
| 5 | Code Quality | 6 | Medium |
| 6 | Documentation | 7 | Low |
| 7 | New Features | 18 | Medium |
| 8 | Developer Experience | 9 | Low |
| 9 | Module Refactoring | 2 | Low |

---

## Wave 1: Critical Bugs

**These items fix broken functionality or security vulnerabilities. Do first.**

### 1.1 Fix nested forms in subscribers.html

**Severity**: High — Breaks bulk operations

**Problem**: The bulk form (`<form id="bulk-form">`) contains nested per-subscriber delete forms. HTML forbids nested forms; browsers implicitly close the outer form when encountering inner ones.

**Location**: `app/templates/admin/subscribers.html:48-52`

**Fix**: Move delete forms outside the bulk form. Use `form="bulk-form"` attribute on checkboxes to associate them with the bulk form without nesting.

### 1.2 Fix nested forms in dashboard.html

**Severity**: High — Same issue, breaks bulk operations

**Problem**: The dashboard bulk form contains nested per-post forms ("Reset NL" and "Delete" buttons).

**Location**: `app/templates/admin/dashboard.html:114-122`

**Fix**: Apply the same pattern — use `form="bulk-form"` attribute on checkboxes, move delete/reset forms outside the bulk form.

### 1.3 Fix path traversal in media.py delete_media

**Severity**: Medium-High — Potential file deletion beyond upload directory

**Problem**: If `secure_filename()` returns empty string, `filepath` becomes just the upload directory path, which passes the traversal check.

**Location**: `app/routes/admin/media.py:95`

**Fix**: Add empty filename check after `secure_filename()`:
```python
filename = secure_filename(filename)
if not filename:
    abort(400)
```

### 1.4 Fix session fixation vulnerability

**Severity**: High — Session hijacking risk

**Problem**: After calling `login_user(user)`, the Flask session ID is not regenerated. An attacker who obtains a user's session ID before login could fixate that session.

**Location**: `app/routes/admin/auth.py:26`

**Fix**: Add `session.regenerate()` before `login_user()`:
```python
session.regenerate()  # Add before login_user()
login_user(user)
```

### 1.5 Add OperationalError handler in subscribe()

**Severity**: Medium — Database failures cause 500 errors

**Problem**: The `subscribe()` route only catches `IntegrityError` but not `OperationalError`. Database issues will raise 500 errors.

**Location**: `app/routes/public.py:373-399`

**Fix**: Change `except IntegrityError:` to `except (IntegrityError, OperationalError):`

### 1.6 Escape search query in templates

**Severity**: Medium — XSS risk

**Problem**: `{{ query }}` rendered without escaping in search.html. Searching `<script>alert(1)</script>` triggers XSS.

**Location**: `app/templates/search.html:16,18`

**Fix**: Use `{{ query | escape }}` in meta description block.

### 1.7 Escape search query in FTS5

**Severity**: Medium — FTS query manipulation

**Problem**: `_escape_fts_term()` only handles `:` and `"` but FTS5 has many special operators (`AND`, `OR`, `NOT`, `NEAR`, `*`, `()`, etc.).

**Location**: `app/search.py:75-80`

**Fix**: Improve escaping to handle all FTS5 special characters:
```python
def _escape_fts_term(term: str) -> str:
    term = term.strip()
    term = re.sub(r'[()*:+\-"<>]', ' ', term)
    term = re.sub(r'\s+', ' ', term)
    term = term.replace('"', '""')
    return term if term else ""
```

### 1.8 Sanitize analytics dropdown in JavaScript

**Severity**: Low — Admin-only self-XSS

**Problem**: `select.value` is directly interpolated into a URL without validation.

**Location**: `app/static/js/main.js:683`

**Fix**: Validate against allowed values:
```javascript
const allowedDays = ['7', '14', '30', '90', '180', '365'];
if (allowedDays.includes(select.value)) {
    window.location.href = '/admin/analytics?days=' + select.value;
}
```

### 1.9 Move timing delay before database query

**Severity**: Medium — Token enumeration timing leak

**Problem**: `time.sleep(TOKEN_ENUMERATION_DELAY)` happens AFTER the database query. An attacker can measure response times to distinguish valid from invalid tokens.

**Location**: `app/routes/public.py:413-422`, `app/routes/public.py:453-462`

**Fix**: Move `time.sleep()` BEFORE the database query to normalize timing.

---

## Wave 2: Security Hardening

**Security improvements that don't break existing functionality.**

### 2.1 Sanitize custom CSS before rendering

**Severity**: Medium — Potential data exfiltration via CSS

**Problem**: `{{ custom_css | safe }}` bypasses auto-escaping. Malicious CSS can exfiltrate data via `background-image` URLs.

**Location**: `app/templates/base.html:30`, `app/templates/admin/base.html:20`

**Fix**: Add CSS sanitization to strip dangerous properties (`url()`, `expression()`, `content`, etc.):
```python
import re

def sanitize_css(css_text: str) -> str:
    css_text = re.sub(r'url\s*\([^)]*\)', '', css_text)
    css_text = re.sub(r'expression\s*\([^)]*\)', '', css_text)
    css_text = re.sub(r'content\s*:', '/* blocked */:', css_text)
    # Parse and validate remaining CSS
    return css_text
```

### 2.2 Add login rate limiting (defense-in-depth)

**Severity**: Medium — Brute-force protection

**Problem**: No rate limiting on `/admin/login`. While proxy-level is recommended, application-level provides defense-in-depth.

**Location**: `app/routes/admin/auth.py`

**Fix**: Add simple in-memory rate limiting:
```python
_login_attempts: dict[str, list[float]] = {}
MAX_ATTEMPTS = 5
LOCKOUT_WINDOW = 300

def rate_limit_login(f):
    # Track attempts, clear on success
```

Note: Document that proxy-level rate limiting is required for production.

### 2.3 Add rate limiting to token endpoints

**Severity**: Medium — Enumeration protection

**Problem**: `/confirm/<token>` and `/unsubscribe/<token>` have no rate limiting.

**Location**: `app/routes/public.py:402-439`, `app/routes/public.py:442-480`

**Fix**: Apply similar rate limiting with higher limits (20 attempts per minute).

### 2.4 Validate SESSION_COOKIE_SECURE independently of debug

**Severity**: Medium — Cookie security tied to debug mode

**Problem**: `SESSION_COOKIE_SECURE = not app.debug` makes cookie security dependent on debug setting.

**Location**: `app/__init__.py:90`

**Fix**: Use explicit environment variable control:
```python
app.config["SESSION_COOKIE_SECURE"] = _env("SESSION_COOKIE_SECURE", "true").lower() in ("true", "1", "yes")
```

### 2.5 Add SECRET_KEY strength validation

**Severity**: Medium — Weak secret fallback

**Problem**: `SECRET_KEY` falls back to empty string silently.

**Location**: `app/config.py:72`

**Fix**: Validate minimum length (32 chars) in `_validate_config()`:
```python
if len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY must be at least 32 characters...")
```

### 2.6 Validate redirect URLs against allowlist

**Severity**: Medium — Open redirect prevention

**Problem**: `_safe_redirect_url()` relies on `request.host` which can be spoofed via Host header.

**Location**: `app/routes/public.py:45-52`

**Fix**: Compare against `BASE_URL` configuration when available.

### 2.7 Add CSRF enforcement warning

**Severity**: Low — Defense-in-depth

**Problem**: No warning if CSRF is disabled in production mode.

**Location**: `app/config.py` or `app/csrf.py`

**Fix**: Add production check that warns if CSRF disabled in non-debug mode.

### 2.8 Add COOP security header

**Severity**: Low — Standard security header

**Problem**: No `Cross-Origin-Opener-Policy` header set.

**Location**: `app/__init__.py` (set_security_headers)

**Fix**: Add `response.headers["Cross-Origin-Opener-Policy"] = "same-origin"`

### 2.9 Remove sensitive info from health endpoint

**Severity**: Low — Information disclosure

**Problem**: `/health` exposes Python version and pool stats.

**Location**: `app/routes/public.py:529-590`

**Fix**: Remove version and pool stats from response, or restrict endpoint to localhost only.

### 2.10 Add subscriber cascade delete

**Severity**: Low-Medium — Orphaned sessions

**Problem**: Deleting a user doesn't cascade-delete their `AdminSession` records.

**Location**: `app/models.py` (User.admin_sessions relationship)

**Fix**: Add `cascade="all,delete"` to the relationship or explicitly delete sessions before deleting user.

### 2.11 Fix FakeSubscriber missing attributes

**Severity**: Low — Errors masked by bare except

**Problem**: `FakeSubscriber` dataclass is missing `confirmed`, `created_at`, `expires_at`, `unsubscribed_at` attributes that `send_newsletter` may access.

**Location**: `app/routes/admin/newsletter.py:15-19`

**Fix**: Add all missing attributes with sensible defaults.

### 2.12 Add cascade to AdminSession relationship

**Severity**: Low — Orphaned sessions

**Problem**: When a user is deleted, their AdminSession records remain.

**Location**: `app/models.py`

**Fix**: Ensure cascade delete is configured properly.

---

## Wave 3: Exception Handling

**Replace bare `except Exception` blocks with specific exceptions.**

### 3.1 Replace bare except in search.py

**Locations**: `app/search.py:30, 43, 61, 71, 106`

**Fix**: Use `sqlalchemy.exc.OperationalError, ProgrammingError` for database operations.

### 3.2 Replace bare except in email.py

**Locations**: `app/email.py:76, 144`

**Fix**: Use `smtplib.SMTPException, OSError`.

### 3.3 Replace bare except in public.py

**Locations**: `app/routes/public.py:548, 566`

**Fix**: Use `OperationalError, ProgrammingError`.

### 3.4 Replace bare except in newsletter.py

**Location**: `app/routes/admin/newsletter.py:58`

**Fix**: Use `smtplib.SMTPException, OSError`.

### 3.5 Replace bare except in backup.py

**Locations**: `backup.py:73, 85`

**Fix**: Use `OSError` for gzip, `sqlite3.Error, OSError` for backup creation.

### 3.6 Add documentation comments for intentional catches

**Locations**: `app/routes/admin/helpers.py:49` (URL parsing returns "Other"), `app/routes/errors.py:30` (graceful degradation)

**Fix**: Add comments documenting these are intentional catch-all handlers with known behavior.

---

## Wave 4: Performance

**Query optimization and caching improvements.**

### 4.1 Consolidate analytics queries

**Problem**: `_get_analytics_data()` runs ~10 separate DB queries per call.

**Location**: `app/routes/admin/helpers.py:99-196`

**Fix**: Consolidate into 3-4 queries using subqueries and CTEs.

### 4.2 Enforce related posts LIMIT cap

**Problem**: `RELATED_POSTS_COUNT` config could be set too high.

**Location**: `app/routes/public.py:69`

**Fix**: Add `HARD_RELATED_POST_LIMIT = 20` regardless of config.

### 4.3 Pre-render newsletter template

**Problem**: Template rendered individually for each subscriber.

**Location**: `app/email.py:92-113`

**Fix**: Pre-render once with placeholder token, replace per-subscriber.

### 4.4 Add request-level tag list caching

**Problem**: Tag list fetched on every public page request.

**Location**: `app/routes/public.py:91,165,196`

**Fix**: Use Flask `g` object for request-level caching.

### 4.5 Cache SiteSettings application-wide

**Problem**: `inject_theme()` queries SiteSettings on every request.

**Location**: `app/context_processors.py`

**Fix**: Add TTL-based caching with invalidation on settings update.

### 4.6 Optimize footer context processor

**Problem**: Footer runs 3 queries on every non-admin request.

**Location**: `app/context_processors.py:90-130`

**Fix**: Cache recent posts and tags with short TTL (30-60 seconds).

### 4.7 Optimize dashboard view/share count queries

**Problem**: Dashboard uses two separate subqueries for view_counts and share_counts.

**Location**: `app/routes/admin/posts.py:59-82`

**Fix**: Consider combining into single query with proper indexes.

### 4.8 Optimize tags list query

**Problem**: Tags list runs two queries instead of one.

**Location**: `app/routes/admin/tags.py`

**Fix**: Use single query with LEFT JOIN and GROUP BY.

### 4.9 Optimize analytics page queries

**Problem**: Analytics page runs 7 separate queries.

**Location**: `app/routes/admin/helpers.py`

**Fix**: Combine some queries (total_views is sum of daily_views).

### 4.10 Add query result caching for expensive operations

**Problem**: Repeated expensive queries aren't cached.

**Location**: `app/routes/admin/analytics.py`

**Fix**: Add `Flask-Caching` decorators with query string caching.

### 4.11 Verify and add missing database indexes

**Problem**: Some query patterns may lack optimal indexes.

**Location**: `app/models.py`

**Fix**: Review and add indexes for `PageView.referrer` if referrer aggregation is slow.

### 4.12 Clear prefetch timer on page unload

**Problem**: Prefetch timer not cleared on page leave.

**Location**: `app/static/js/main.js:950`

**Fix**: Add `beforeunload` event handler to clear timer.

### 4.13 Optimize session-based view tracking

**Problem**: Session list grows to 100 entries, causes serialization overhead.

**Location**: `app/routes/public.py`

**Fix**: Use set instead of list for `viewed_posts`, or use cache.

### 4.14 Add scheduler health monitoring

**Problem**: No visibility into scheduler health.

**Location**: `app/scheduler.py`

**Fix**: Add health endpoint showing scheduler status and last newsletter time.

### 4.15 Async newsletter sending (optional)

**Problem**: Newsletter sends sequentially, blocking scheduler.

**Location**: `app/email.py`

**Fix**: Use `ThreadPoolExecutor` for parallel sending with thread-safe connection management.

---

## Wave 5: Code Quality

**Type annotations, cleanup, and maintainability.**

### 5.1 Add type annotations to _get_posts_query

**Location**: `app/routes/admin/helpers.py:84`

**Fix**: Add `-> select` return type.

### 5.2 Add type annotations to _get_tag_counts

**Location**: `app/cache.py:33`

**Fix**: Add `-> dict[int, int]` return type.

### 5.3 Add type annotations to template filters

**Location**: `app/__init__.py:124, 131`

**Fix**: Add `-> str` return types to `markdown_safe_filter` and `reading_time_filter`.

### 5.4 Add type annotations to model methods

**Location**: `app/models.py`

**Fix**: Add `-> str` to `Post.generate_slug()` and `Post.short_code()`.

### 5.5 Add type annotations to helper functions

**Location**: `app/routes/admin/helpers.py`

**Fix**: Add types to `_detect_image_type`, `_allowed_file`, `_save_image`, `validate_tag_name`, `_generate_unique_slug`, `_cleanup_orphan_tags`, `_get_or_create_tags`, `_apply_post_updates`.

### 5.6 Add type annotations to search functions

**Location**: `app/search.py`

**Fix**: Add return types to `init_fts`, `rebuild_fts`, `sync_fts`, `remove_fts`, `search`.

### 5.7 Remove unused variables

**Problem**: Some queries may not be used by templates.

**Location**: `app/routes/public.py:91, 134`

**Fix**: Verify template usage and remove unused queries.

### 5.8 Fix imprecise type annotation in cache.py

**Problem**: `_TAG_COUNTS_CACHE` typed as `dict[str, object]` instead of actual types.

**Location**: `app/cache.py:18`

**Fix**: Use proper types: `dict[str, Optional[dict[int, int]] | float]`.

### 5.9 Handle SQLAlchemy pool methods compatibility

**Problem**: Pool introspection methods may not exist in all SQLAlchemy versions.

**Location**: `app/__init__.py:575-581`

**Fix**: Wrap in try/except to gracefully handle missing methods.

### 5.10 Extract handle_db_error utility

**Problem**: Duplicate error handling in multiple places.

**Location**: `app/utils.py`

**Fix**: Create shared utility:
```python
def handle_db_error(e: Exception, operation: str) -> bool:
    from sqlalchemy.exc import IntegrityError, OperationalError
    if isinstance(e, (IntegrityError, OperationalError)):
        logger.error("Database error during %s: %s", operation, e)
        db.session.rollback()
        return True
    return False
```

---

## Wave 6: Documentation

**Documentation improvements.**

### 6.1 Document SMTP timeout configuration

**Location**: DEPLOY.md

**Fix**: Add `smtp_timeout` to configuration section.

### 6.2 Document proxy-level rate limiting

**Problem**: Login rate limiting recommendation needs clarification.

**Location**: DEPLOY.md

**Fix**: Ensure the rate limiting section clearly documents nginx/Cloudflare configuration.

### 6.3 Document response compression

**Problem**: Response compression recommendation not documented.

**Location**: DEPLOY.md

**Fix**: Add nginx gzip configuration example.

### 6.4 Document PostgreSQL for production

**Problem**: SQLite limitations not documented.

**Location**: DEPLOY.md

**Fix**: Add section on PostgreSQL migration path for production.

### 6.5 Add API documentation docstrings

**Problem**: No API documentation for routes.

**Location**: Route handlers

**Fix**: Add docstrings to public and admin routes.

### 6.6 Document environment variables

**Problem**: No comprehensive env var list.

**Location**: DEPLOY.md

**Fix**: Add environment variable reference table.

### 6.7 Document third-party libraries

**Problem**: Dependencies listed but not their purposes.

**Location**: DEPLOY.md or README.md

**Fix**: Add library purpose table.

---

## Wave 7: New Features

**Content management, SEO, and API enhancements.**

### 7.1 Static pages

**Problem**: No way to create static content pages (About, Contact).

**Effort**: 3-4 hours

**Fix**: Add `Page` model, routes, and admin CRUD.

### 7.2 Post archive page

**Problem**: No chronological browsing of all posts.

**Effort**: 1-2 hours

**Fix**: Add `/archive` route with posts grouped by year/month.

### 7.3 Search result highlighting

**Problem**: Search results show matching posts but don't highlight terms.

**Effort**: 2 hours

**Fix**: Extract snippets around matches and pass to template.

### 7.4 Schema.org JSON-LD markup

**Problem**: Posts lack structured data for SEO.

**Effort**: 1 hour

**Fix**: Add JSON-LD Article schema to post templates.

### 7.5 Twitter card enhancements

**Problem**: Base Twitter Card tag exists but per-post title/description/image missing.

**Effort**: 30 minutes

**Fix**: Add per-post Twitter meta tags.

### 7.6 Enhanced sitemap

**Problem**: Sitemap could include static pages and proper lastmod.

**Effort**: 30 minutes

**Fix**: Update sitemap generator for static pages (after 7.1).

### 7.7 Canonical URLs

**Problem**: No canonical URL meta tags.

**Effort**: 30 minutes

**Fix**: Add canonical URL to base template and context processors.

### 7.8 Robots.txt enhancements

**Problem**: Basic robots.txt, AI crawler blocking missing.

**Effort**: 15 minutes

**Fix**: Add sitemap location and block AI crawlers.

### 7.9 REST API for posts

**Problem**: No programmatic access to blog content.

**Effort**: 4-5 hours

**Fix**: Create read-only API at `/api/v1/` with posts, tags endpoints.

### 7.10 Webhook system

**Problem**: No way to notify external services on publish.

**Effort**: 4-5 hours

**Fix**: Add `Webhook` model and delivery system.

### 7.11 Import/Export tool

**Problem**: No migration or backup tool for full blog data.

**Effort**: 3-4 hours

**Fix**: Add JSON export/import with CLI commands.

### 7.12 Scheduled posts calendar view

**Problem**: No visual overview of scheduled posts.

**Effort**: 2-3 hours

**Fix**: Add calendar view to admin dashboard.

### 7.13 Post list columns toggle

**Problem**: Fixed columns in post list.

**Effort**: 1-2 hours

**Fix**: Add column visibility toggle with localStorage persistence.

### 7.14 Bulk subscriber resend confirmation

**Problem**: Bulk actions limited to delete/export.

**Effort**: 1 hour

**Fix**: Add resend confirmation email action.

### 7.15 Newsletter inline styles

**Problem**: Newsletter HTML uses CSS classes email clients may ignore.

**Effort**: 2 hours

**Fix**: Convert to inline styles using premailer or manual styling.

### 7.16 Unsubscribe preference center

**Problem**: Users can only unsubscribe entirely.

**Effort**: 3-4 hours

**Fix**: Add preference form for frequency/topics.

### 7.17 API key management UI

**Problem**: API keys require server config changes.

**Effort**: 2-3 hours

**Fix**: Add admin UI for generating/revoking API keys.

### 7.18 Session IP binding

**Problem**: Sessions can be used from different IPs.

**Effort**: 1 hour

**Fix**: Store initial IP, warn on change (don't break mobile users).

---

## Wave 8: Developer Experience

**Tests, polish, and accessibility.**

### 8.1 Add Flask shell context

**Problem**: No interactive shell context for debugging.

**Effort**: 15 minutes

**Fix**: Add shell context processor for models.

### 8.2 Add Post.short_code test

**Problem**: `short_code()` method not tested.

**Effort**: 15 minutes

**Fix**: Add test to `tests/test_models.py`.

### 8.3 Add FTS tests (optional)

**Problem**: FTS module functions not tested directly.

**Effort**: 45 minutes

**Fix**: Add direct tests for `sync_fts`, `rebuild_fts`.

### 8.4 Add context processor tests

**Problem**: Context processors not tested.

**Effort**: 30 minutes

**Fix**: Add tests for footer data skipping admin routes.

### 8.5 Add CLI command tests

**Problem**: CLI commands not tested.

**Effort**: 1 hour

**Fix**: Add tests for `rebuild-search` and `create-admin`.

### 8.6 Handle missing image file

**Problem**: Post has image path but file missing.

**Effort**: 30 minutes

**Fix**: Check image existence, clear invalid reference.

### 8.7 Add database integrity check

**Problem**: No graceful handling of corrupted database.

**Effort**: 1 hour

**Fix**: Add integrity check on startup.

### 8.8 Add loading spinner to admin forms

**Problem**: Forms feel slow on save.

**Effort**: 30 minutes

**Fix**: Add subtle spinner on submit buttons.

### 8.9 Add confirmation for bulk delete

**Problem**: Bulk delete could be clearer.

**Effort**: 20 minutes

**Fix**: Add count comparison before delete.

### 8.10 Improve upload progress

**Problem**: Large uploads show no progress.

**Effort**: 1 hour

**Fix**: Add XHR progress listener for uploads.

### 8.11 Add prefers-reduced-motion support

**Problem**: Animations don't respect user preference.

**Effort**: 15 minutes

**Fix**: Add media query guards for nav menu and shimmer.

### 8.12 Fix lightbox close focus behavior

**Problem**: Inconsistent focus management on close.

**Effort**: 20 minutes

**Fix**: Track keyboard vs mouse open, restore focus appropriately.

---

## Wave 9: Module Refactoring

**Larger refactors that should be done carefully.**

### 9.1 Split admin/helpers.py

**Problem**: 432-line file with multiple responsibilities.

**Effort**: 3-4 hours

**Fix**: Split into `analytics.py`, `tags.py`, `images.py`, `posts.py`, `dashboard.py`, `backup.py` in `app/routes/admin/helpers/` package.

### 9.2 Split main.js

**Problem**: 1120-line file with many features.

**Effort**: 2-3 hours

**Fix**: Extract to `js/shared/modal.js`, `js/shared/dark-mode.js`, `js/admin/editor.js`, `js/admin/bulk.js`, `js/public/lightbox.js`, `js/public/toc.js`.

---

## Implementation Notes

### Testing

Run tests after each wave:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

### Parallelization

Items within each wave can be worked on in parallel by sub-agents with these dependencies:

**Wave 1**: All items independent — can parallelize fully
**Wave 2**: All items independent — can parallelize fully
**Wave 3**: All items independent — can parallelize fully
**Wave 4**: Items 4.1-4.9 (query/cache) independent of 4.10-4.15 (scheduler/async)
**Wave 5**: All items independent
**Wave 6**: All items independent (documentation only)
**Wave 7**: 7.6 depends on 7.1; 7.9-7.10 independent; 7.11-7.18 mostly independent
**Wave 8**: All items independent
**Wave 9**: Items 9.1 and 9.2 independent of each other

### Dependencies

- **Redis** (optional): Needed for Wave 4 items 4.10 and 7.3.3 if multi-worker deployment
- **cssutils**: Needed for item 2.1 (CSS sanitization)
- **premailer**: Optional for item 7.15 (newsletter inline styles)

### Already Completed

The following items from the plans were found to already be implemented:

- ✅ Scheduler already running check — `scheduler.py` has file locking
- ✅ 'c' key shortcut admin guard — share bar doesn't exist on admin pages, so not needed
- ✅ Code block copy button — implemented in `main.js:208-237`
- ✅ Twitter Card tag — exists in `base.html:13`
- ✅ Sitemap posts — posts and tags included in sitemap
- ✅ Robots.txt — basic version exists
- ✅ FTS ordering uses `case()` — implemented
- ✅ Dashboard metrics cache — consolidated
- ✅ Newsletter template pre-render check — already optimized
- ✅ Tag count caching — double-checked locking in `cache.py`
- ✅ Analytics caching — 5-min TTL with LRU eviction
- ✅ Connection pool stats in /health — implemented

---

## Related Files

- `plan.md` - Original consolidated plan (items 1-29 completed)
- `AGENTS.md` - Project structure and patterns
- `DEPLOY.md` - Deployment guide
- `app/models.py` - Model definitions
- `app/routes/` - Route handlers
- `app/templates/` - Jinja2 templates
- `app/static/js/main.js` - JavaScript

---

## Notes

- Items marked "Low" effort are 1-2 hours; "Medium" is 2-4 hours; "High" is 4+ hours
- All changes should maintain backward compatibility
- Run tests after each wave to verify nothing breaks
- Documentation items (Wave 6) can be done alongside any other wave
