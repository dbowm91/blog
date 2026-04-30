# Master Improvement Plan - Phase 2

**Date:** 2026-04-30
**Status:** PENDING
**Summary:** Consolidation of plans 2-8 identifying actionable improvements for security, performance, and features.

---

## Overview

This plan consolidates improvements from 7 separate plan documents into a unified implementation roadmap. Items are organized into waves based on dependencies and parallelization potential.

**Total Actionable Items:** ~50
**Estimated Total Effort:** 40-55 hours

---

## Wave 1: Critical Bug Fixes (Parallelize: 4 items)

These fixes address data integrity and security issues. Execute in parallel.

### 1.1 CSRF Token Reuse Optimization
- **Priority:** CRITICAL
- **File:** `app/context_processors.py:130`
- **Issue:** `inject_csrf()` context processor calls `generate_csrf_token()` on EVERY request, generating new tokens unnecessarily and flooding the sliding window
- **Fix:** Reuse existing token from `session.get("csrf_tokens", [])` if available, only generate if no tokens exist
- **Proposed change:**
```python
@ app.context_processor
def inject_csrf():
    try:
        from flask import g
        nonce = getattr(g, "csp_nonce", "")
    except RuntimeError:
        nonce = ""
    tokens = session.get("csrf_tokens", [])
    csrf_token = tokens[-1] if tokens else generate_csrf_token()
    return {"csrf_token": csrf_token, "csp_nonce": nonce}
```
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/test_security.py -v -k csrf`

### 1.2 Archive Route Memory Optimization
- **Priority:** CRITICAL
- **File:** `app/routes/public.py:155-184`
- **Issue:** Archive route loads full `Post.body` into memory for all posts
- **Fix:** Add `defer(Post.body)` to archive query
- **Proposed change:** In the posts_query at line ~155, add:
```python
from sqlalchemy.orm import defer
posts_query = (
    select(Post)
    .options(joinedload(Post.tags), defer(Post.body))
    .filter(Post.published == True)
)
```
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k archive`

### 1.3 AdminSession DB Cleanup on IP Enforcement
- **Priority:** CRITICAL
- **File:** `app/routes/admin/__init__.py:26-41`
- **Issue:** When IP binding fails, the AdminSession DB record is not deleted before `session.clear()`
- **Fix:** Delete AdminSession DB record BEFORE calling `session.clear()`
- **Proposed change:** Move the session deletion before `session.clear()`:
```python
admin_session_id = session.get("admin_session_id")
if admin_session_id and request.remote_addr != session.get("ip_address"):
    # Delete the session record FIRST
    db.session.execute(
        delete(AdminSession).where(AdminSession.id == admin_session_id)
    )
    db.session.commit()
    # THEN clear session
    session.clear()
```
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k session`

### 1.4 pages.py IntegrityError Retry Logic
- **Priority:** CRITICAL
- **Files:** `app/routes/admin/pages.py:78-91` (new_page)
- **Issue:** After rollback on IntegrityError, only one slug attempt is made. If that slug also exists, the operation fails silently or loses data.
- **Fix:** Add retry loop similar to `posts.py` pattern with slug regeneration and multiple retry attempts (up to 100 counter)
- **Reference:** See `posts.py:177-202` helper function `_attempt_post_commit()` which handles this correctly with while loop
- **Implementation:** Consider creating helper `_attempt_page_commit()` that follows same pattern:
```python
def _attempt_page_commit(page, title):
    """Retry page commit with slug regeneration on collision."""
    max_attempts = 100
    for attempt in range(max_attempts):
        try:
            db.session.flush()
            db.session.commit()
            return page.slug, True
        except IntegrityError:
            db.session.rollback()
            if attempt == max_attempts - 1:
                raise
            page.slug = _generate_unique_slug(Page, title, exclude_id=page.id if page.id else None)
            db.session.add(page)
```
- **Note:** `edit_page()` at lines 156-161 already correctly re-fetches page after rollback and re-applies fields - verify this pattern is also correct in `new_page()`
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k pages`

---

## Wave 2: Security Hardening (Parallelize: 2 items)

### 2.1 Login Failure Delay Standardization
- **Priority:** HIGH
- **File:** `app/routes/admin/auth.py:70`
- **Issue:** Login failure uses hardcoded `time.sleep(0.05)` instead of configurable delay
- **Note:** This is separate from `TOKEN_ENUMERATION_DELAY` which is for token-based flows (confirm/unsubscribe) at 0.1s
- **Fix:** Create new config `LOGIN_FAILURE_DELAY` or reuse existing `_FAILED_LOGIN_DELAY` if available:
```python
from app.config import LOGIN_FAILURE_DELAY
time.sleep(LOGIN_FAILURE_DELAY)  # instead of hardcoded 0.05
```
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/test_security.py -v -k login`

### 2.2 SESSION_COOKIE_SECURE Runtime Enforcement
- **Priority:** HIGH
- **File:** `app/__init__.py` (around line 160)
- **Issue:** No runtime check that prevents disabling cookie security in production
- **Fix:** Add runtime enforcement:
```python
if not app.debug and not app.testing:
    if not app.config.get("SESSION_COOKIE_SECURE", True):
        raise RuntimeError(
            "SESSION_COOKIE_SECURE must be True in production. "
            "This is a security requirement."
        )
```
- **Verification:** Set `SESSION_COOKIE_SECURE=false` in config and verify app fails to start

---

## Wave 3: Async Infrastructure (Parallelize: All Celery items)

### 3.1 Wire Celery Tasks
- **Priority:** HIGH
- **Files:** `app/tasks.py`, `app/webhooks.py:81`, `app/scheduler.py:125`
- **Issue:** Tasks defined but `@shared_task` decorator not applied
- **Fix:** Add `@shared_task` decorators:
```python
# In app/tasks.py
@shared_task
def generate_image_variants(image_path):
    ...

@shared_task
def send_newsletter_task(subject, html_body, recipient_ids):
    ...

@shared_task
def deliver_webhook(url, payload, headers):
    ...
```
- **Update callers:**
  - `app/webhooks.py:81` - change `deliver_webhook()` to `deliver_webhook.delay()`
  - `app/scheduler.py:125` - change to dispatch via Celery instead of direct call
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k celery`

### 3.2 Async Email Tasks
- **Priority:** HIGH
- **Files:** `app/tasks.py`, `app/routes/public.py:514`, `app/routes/admin/auth.py:162`, `app/routes/admin/subscribers.py:202`
- **Issue:** Email sending is synchronous, blocks requests
- **Fix:** Create async email tasks:
```python
# In app/tasks.py
@shared_task
def send_confirmation_task(email, token):
    from app.email import send_email
    from app.models import Subscriber
    # Send confirmation email...

@shared_task
def send_password_reset_task(email, token):
    from app.email import send_email
    # Send password reset email...
```
- **Update callers to use `.delay()`:**
  - Subscribe endpoint: `send_confirmation_task.delay(email, token)`
  - Forgot password: `send_password_reset_task.delay(email, token)`
  - Bulk resend: Loop with `send_confirmation_task.delay(subscriber.email, subscriber.token)`
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k email`

### 3.3 Async Image Variant Generation
- **Priority:** HIGH
- **Files:** `app/storage.py:297-298`, `app/filters.py`
- **Issue:** Image variants generated synchronously on upload
- **Fix:** Queue `generate_image_variants.delay(filename)` instead of blocking call
- **Add on-demand fallback in filters.py** if variant is missing:
```python
# Check if variant exists, if not trigger async generation
if not os.path.exists(variant_path):
    from app.tasks import generate_image_variants
    generate_image_variants.delay(filename)
```
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k image`

---

## Wave 4: Performance Optimizations (Parallelize: All items)

### 4.1 RSS Feed Caching
- **Priority:** MEDIUM
- **File:** `app/routes/rss.py:38-47, 138-142`
- **Fix:** Add `@flask_cache.cached(timeout=300)` to feed generation
- **Implementation:**
```python
from flask importFlask-Caching
cache = Flask-Caching()

@public.route("/rss")
@flask_cache.cached(timeout=300)
def feed():
    ...
```
- **Add cache invalidation** on post publish/unpublish/delete
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k rss`

### 4.2 Archive Years Caching
- **Priority:** MEDIUM
- **File:** `app/routes/public.py:137-143`
- **Fix:** Add `@flask_cache.cached(timeout=3600)` to `_get_available_years()`
- **Implementation:**
```python
@flask_cache.cached(timeout=3600)
def _get_available_years():
    years_query = (
        select(func.extract("year", Post.created_at).label("year"))
        .filter(Post.published == True)
        .distinct()
        .order_by(func.extract("year", Post.created_at).desc())
    )
    return [int(row.year) for row in db.session.execute(years_query).fetchall()]
```
- **Add cache invalidation** when posts are published/unpublished
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k archive`

### 4.3 Remove Duplicate Filter Definition
- **Priority:** LOW
- **File:** `app/filters.py:95-116`
- **Fix:** DELETE the second `post_image_srcset_filter` definition (lines 95-116)
- **Verification:** `grep -n "def post_image_srcset_filter" app/filters.py` should show only 1 match

### 4.4 Remove Dead Code in file_url_filter
- **Priority:** LOW
- **File:** `app/filters.py:75-93`
- **Issue:** Lines 82-93 are unreachable - code after `return storage.url(filename)` at line 81 can never execute
- **Fix:** DELETE lines 82-93 (the redundant cache lookup code that was likely copy-pasted)
- **Verification:** Code review - ensure function only has the storage.url() return

### 4.5 Rate Limiting on /api/track-share
- **Priority:** MEDIUM
- **File:** `app/routes/public.py:467`
- **Fix:** Add `@limiter.limit("20 per minute")` to share tracking endpoint
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k share`

### 4.6 Public Route Rate Limiting
- **Priority:** HIGH
- **File:** `app/routes/public.py`
- **Missing rate limits on:**
  - `/search` - add `@limiter.limit("20 per minute")`
  - `/post/<slug>` - add `@limiter.limit("60 per minute")`
  - `/archive` - add `@limiter.limit("30 per minute")`
  - `/page/<slug>` - add `@limiter.limit("60 per minute")`
  - `/tag/<slug>` - add `@limiter.limit("60 per minute")`
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k "rate or limit"`

---

## Wave 5: API Improvements (Parallelize: 2 items)

### 5.1 API Input Validation
- **Priority:** HIGH
- **File:** `app/routes/api.py:167-178`
- **Issue:** Missing input validation on API endpoints
- **Fix:** Create `app/validators.py` with validation functions:
```python
# app/validators.py
from wtforms import Form, StringField, validators

def validate_post_data(data):
    errors = []
    if "title" in data and len(data["title"]) > 500:
        errors.append("Title too long")
    # Add more validation...
    return errors if errors else None
```
- **Apply to API endpoints** in `app/routes/api.py`
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k api`

### 5.2 API IntegrityError Handling
- **Priority:** HIGH
- **File:** `app/routes/api.py:387-390` (create_subscriber endpoint)
- **Issue:** `create_subscriber` endpoint does direct `db.session.commit()` without try/except - concurrent requests can cause IntegrityError and return 500
- **Fix:** Add try/except around commit, handle collision by re-querying (similar to `public.py:subscribe`):
```python
db.session.add(subscriber)
try:
    db.session.commit()
except (IntegrityError, OperationalError):
    db.session.rollback()
    # Re-query on collision - subscriber may have been created by concurrent request
    existing = db.session.execute(
        select(Subscriber).filter_by(email=email)
    ).scalar_one_or_none()
    if existing:
        return jsonify(_subscriber_to_dict(existing)), 200
    raise  # Something else went wrong
```
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k api`

---

## Wave 6: Infrastructure (Parallelize: All items)

### 6.1 Redis Cache for Production
- **Priority:** HIGH
- **File:** `app/__init__.py:176-179`
- **Issue:** SimpleCache not suitable for multi-worker deployments
- **Fix:** Use Redis cache backend:
```python
if os.environ.get("FLASK_ENV") == "production":
    cache_config = {
        "CACHE_TYPE": "RedisCache",
        "CACHE_REDIS_URL": os.environ.get("CACHE_REDIS_URL", "redis://localhost:6379/0"),
        "CACHE_DEFAULT_TIMEOUT": 300,
        "CACHE_KEY_PREFIX": "blog_",
    }
```
- **Verification:** Set `FLASK_ENV=production` with Redis running, verify caching works

### 6.2 Redis Rate Limiting Storage
- **Priority:** HIGH
- **File:** `app/config.py:121`
- **Issue:** `RATE_LIMIT_STORAGE_URI` defaults to `memory://`
- **Fix:** Default to Redis for production:
```python
RATE_LIMIT_STORAGE_URI = os.environ.get(
    "RATE_LIMIT_STORAGE_URI",
    "redis://localhost:6379/1" if os.environ.get("FLASK_ENV") == "production" else "memory://"
)
```
- **Verification:** `FLASK_ENV=production` with Redis, verify rate limits persist across restarts

### 6.3 Database Connection Pooling
- **Priority:** MEDIUM
- **File:** `app/__init__.py`
- **Fix:** Add production pool settings:
```python
if not app.debug and not app.testing:
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
        "pool_timeout": 30,
    }
```
- **Verification:** Load testing with multiple workers

### 6.4 Fix Redundant Inline Import
- **Priority:** LOW
- **File:** `app/__init__.py lines 7-17, 400`
- **Issue:** `from flask import request` imported at module level AND inline in `get_client_ip()`
- **Fix:** Remove redundant inline import, use module-level import
- **Verification:** Code review

---

## Wave 7: Frontend Improvements (Parallelize with Vite setup)

### 7.1 Add Vite Bundler
- **Priority:** HIGH
- **Files:** `app/static/js/main.js`, `app/static/js/shared/*`, `app/static/js/admin/*`, `app/static/js/public/*`
- **Issue:** Too many HTTP requests (10-15 files per page)
- **Solution:** Vite with flask-vite integration
- **Implementation:**
  1. Add `flask-vite` and `vite` to requirements.txt
  2. Create `vite.config.js`:
```javascript
import { defineConfig } from 'vite'
import flask from 'vite-plugin-flask'

export default defineConfig({
  plugins: [flask()],
  build: {
    outDir: 'app/static/bundled',
    rollupOptions: {
      input: {
        main: './app/static/js/main.js'
      }
    }
  }
})
```
  3. Update templates to use bundled output in production
  4. Auto-injects `<script src="/static/bundled/main.js">` into templates
- **Effort:** 2-4 hours
- **Verification:** Load admin page, check network tab for reduced requests

### 7.2 CSS Architecture Split
- **Priority:** HIGH
- **File:** `app/static/css/style.css` (4,175 lines)
- **Solution:** Split into multiple files:
  - `app/static/css/base.css` - Reset, fonts, variables
  - `app/static/css/layout.css` - Container, navbar, sidebar
  - `app/static/css/forms.css` - Form styles
  - `app/static/css/admin.css` - Admin-specific
  - `app/static/css/public.css` - Public-specific
  - `app/static/css/utilities.css` - Utility classes
- **Effort:** 1-3 hours
- **Verification:** Manual testing of all page types

### 7.3 Remove Unused Import
- **Priority:** MEDIUM
- **File:** `app/static/js/admin/shortcuts.js:1`
- **Fix:** Remove unused `focusableSelectors` import
- **Verification:** `grep -n "focusableSelectors" app/static/js/admin/shortcuts.js`

### 7.4 Hardcoded Routes Fix
- **Priority:** MEDIUM
- **File:** `app/static/js/admin/shortcuts.js:30-34`
- **Fix:** Inject routes via data attribute in `admin/base.html`
- **Implementation:**
```html
<script>
  window.ADMIN_ROUTES = {
    posts: "{{ url_for('admin.dashboard') }}",
    pages: "{{ url_for('admin.list_pages') }}",
    // ...
  };
</script>
```
- **Verification:** Vim keyboard shortcuts work correctly

### 7.5 Editor Preview Race Conditions
- **Priority:** MEDIUM
- **File:** `app/static/js/admin/editor.js:35-80`
- **Fix:**
  1. Add debounce (300ms) like search.js
  2. Add request ordering to ignore stale responses
- **Implementation:**
```javascript
// Add debounce
let previewTimeout = null;
const debouncedPreview = () => {
  clearTimeout(previewTimeout);
  previewTimeout = setTimeout(fetchPreview, 300);
};

// Add request ID ordering
let latestRequestId = 0;
const fetchPreview = async () => {
  const requestId = ++latestRequestId;
  const response = await fetchPreviewEndpoint();
  if (requestId === latestRequestId) {
    updatePreview(response);
  }
};
```
- **Verification:** Type in editor, preview updates without race conditions

---

## Wave 8: Feature Enhancements (Parallelize where possible)

### Phase 1: Quick Wins (Can parallelize with above)

#### 8.1 OpenAPI/Swagger UI Integration
- **Priority:** HIGH
- **Effort:** 1-2 hours
- **Files:** `requirements.txt`, `app/__init__.py`, `docs/openapi.yaml`
- **Implementation:**
  1. Add `flask-swagger-ui>=4.0.0` to requirements.txt
  2. Register blueprint in `app/__init__.py`:
```python
from flask_swagger_ui import get_swaggerui_blueprint
SWAGGER_URL = '/api/docs'
API_URL = '/openapi.yaml'
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
```
  3. Add route to serve `/openapi.yaml`
- **Verification:** Visit `/api/docs`, see Swagger UI

#### 8.2 Sitemap Enhancement
- **Priority:** HIGH
- **Effort:** 15-30 minutes
- **File:** `app/routes/public.py`
- **Fix:** Add `/archive` to sitemap
- **Verification:** Check `/sitemap.xml` includes archive URL

#### 8.3 Open Graph Image Resolution
- **Priority:** MEDIUM
- **Effort:** 1 hour
- **Files:** `app/templates/post.html`, `app/templates/page.html`, `app/templates/index.html`
- **Fix:** Add `og:image` meta tags with proper 1200x630 resolution
- **Verification:** Test with Facebook debugger

### Phase 2: Content Improvements

#### 8.4 Markdown Footnotes Support
- **Priority:** MEDIUM
- **Effort:** 30 minutes
- **File:** `app/filters.py`, `app/markdown_config.py`
- **Fix:** Add `"footnotes"` to markdown extensions
- **Verification:** Create post with `[^1]` footnote syntax

#### 8.5 Related Posts Tag Intersection Scoring
- **Priority:** MEDIUM
- **Effort:** 2-3 hours
- **File:** `app/routes/public.py:74-95`
- **Fix:** Modify `_get_related_posts()` to order by shared tag count
- **Implementation:**
```python
def _get_related_posts(post, limit=5):
    post_tag_ids = {tag.id for tag in post.tags}
    if not post_tag_ids:
        return []

    # Score by number of shared tags
    from sqlalchemy import func
    query = (
        select(Post, func.count(Post.tags).label('shared_count'))
        .join(Post.tags)
        .filter(Post.id != post.id, Post.published == True)
        .filter(Post.tags.any(Tag.id.in_(post_tag_ids)))
        .group_by(Post.id)
        .order_by('shared_count DESC', Post.created_at.desc())
        .limit(limit)
    )
    # ...
```
- **Verification:** Create posts with overlapping tags, verify ordering

#### 8.6 Atom Feed Support
- **Priority:** MEDIUM
- **Effort:** 2-3 hours
- **File:** `app/routes/rss.py`
- **Fix:** Add `/atom` route with Atom 1.0 format
- **Verification:** Visit `/atom`, validate against Atom spec

#### 8.7 Reading Time in Admin Dashboard
- **Priority:** LOW
- **Effort:** 30 minutes
- **File:** `app/templates/admin/dashboard.html`
- **Fix:** Add `{{ post.body | reading_time }}` display
- **Verification:** Check dashboard shows reading time

### Phase 3: Advanced Features

#### 8.8 Syntax Highlighting Theme Selector
- **Priority:** MEDIUM
- **Effort:** 4-6 hours
- **Files:** `app/models.py`, `app/routes/admin/settings.py`, `app/templates/admin/settings.html`, `app/static/js/main.js`
- **Requires:** Database migration for `SiteSettings.syntax_theme`
- **Implementation:**
  1. Add `syntax_theme` field to SiteSettings
  2. Define `SYNTAX_THEMES` constant
  3. Add selector in admin settings
  4. Update main.js to load theme dynamically
  5. Add additional Prism theme CSS files
- **Verification:** Change theme in settings, verify code blocks change

#### 8.9 Post Series/Collections Feature
- **Priority:** MEDIUM
- **Effort:** 6-8 hours
- **Files:** `app/models.py`, new `app/routes/admin/series.py`, `app/routes/public.py`
- **Requires:** Database migration
- **Implementation:**
  1. Create `Series` and `PostSeries` models
  2. Add admin routes: `/admin/series`, `/admin/series/new`, `/admin/series/<id>/edit`
  3. Add public routes: `/series/<slug>`
  4. Update post page to show "Part X of Series Name"
  5. Add templates
- **Verification:** Create series, add posts, verify display

#### 8.10 Newsletter Email Preview
- **Priority:** LOW
- **Effort:** 3-4 hours
- **Files:** `app/routes/admin/newsletter.py`, `app/templates/admin/newsletter.html`
- **Fix:** Add `/admin/newsletter/preview` route
- **Verification:** Click preview, see newsletter email

#### 8.11 Scheduled Post Notifications
- **Priority:** LOW
- **Effort:** 2-3 hours
- **Files:** `app/routes/admin/dashboard.py`, `app/templates/admin/dashboard.html`
- **Fix:** Add "scheduled_posts_count" to dashboard stats
- **Implementation:**
```python
# In dashboard route
scheduled_count = db.session.execute(
    select(func.count(Post.id)).filter(
        Post.scheduled_publish_at != None,
        Post.scheduled_publish_at <= utc_now(),
        Post.published == False
    )
).scalar()
```
- **Verification:** Schedule a post, check dashboard badge

---

## Already Correct (No Action Needed)

| Item | Plan | Reason |
|------|------|--------|
| Exception handling | 7 | All `except Exception` clauses justified |
| Admin session cleanup | 7 | Already optimized |
| API input validation | 7 | Current validation adequate |
| Dashboard metrics | 7 | Current implementation adequate |
| Multi-machine scheduler | 7 | Already documented in DEPLOY.md |
| Token enumeration prevention | 2 | Already implemented with timing delay |
| Security headers | 2 | Full coverage already |
| Settings cache invalidation | 3 | Already fixed |

---

## Dependencies Summary

### External Services Required
- **Redis** - For production caching and rate limiting
- **Celery worker/beat** - For async task processing

### Database Migrations Required
- `Series`/`PostSeries` models (Wave 8, item 8.9)
- `SiteSettings.syntax_theme` field (Wave 8, item 8.8)

### Python Package Additions
- `flask-swagger-ui>=4.0.0` (Wave 8, item 8.1)
- `vite` + `vite-plugin-flask` (Wave 7, item 7.1)

---

## Verification Commands

```bash
# Run full test suite
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v

# Run without E2E
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ --ignore=tests/e2e

# Specific test files
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/test_security.py -v
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/test_api.py -v
```

---

## Parallelization Strategy

### Wave 1 (Critical) - Execute sequentially due to data integrity concerns
### Wave 2 (Security) - Can parallelize with Wave 1
### Wave 3 (Async) - Can parallelize internally, depends on Wave 2 for some items
### Wave 4 (Performance) - Can parallelize internally
### Wave 5 (API) - Can parallelize with Wave 4
### Wave 6 (Infrastructure) - Can parallelize internally
### Wave 7 (Frontend) - Can parallelize with Wave 3-6, Vite is prerequisite for CSS split
### Wave 8 (Features) - Can parallelize within phases, some depend on Wave 6-7

### Recommended Implementation Order
1. Wave 1 (Critical) - First due to data integrity
2. Wave 2 (Security) - Parallel with Wave 1
3. Wave 3 (Async) - After Wave 2, but Celery items can start parallel
4. Wave 4 (Performance) - Parallel with Wave 3
5. Wave 5 (API) - Parallel with Wave 4
6. Wave 6 (Infrastructure) - Parallel with Wave 5
7. Wave 7 (Frontend) - After Wave 3 complete (for Vite)
8. Wave 8 (Features) - Parallel with Wave 7, phase 3 after Wave 6-7

---

## Notes

- All database changes require `flask db migrate` and `flask db upgrade`
- Redis and Celery services must be running for async features
- Some items may be combined or split based on implementation findings
- Verification tests should be run after each wave
