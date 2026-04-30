# Master Improvement Plan - Phase 2

**Date:** 2026-04-30
**Status:** PENDING
**Summary:** Consolidation of all improvement plans into a unified implementation roadmap. ~50 actionable items across security, performance, features, and infrastructure.

---

## Wave 1: Critical Bug Fixes (Do First - Sequential within wave for data integrity)

These fixes address data integrity and security issues. Execute in sequence due to data integrity concerns.

### 1.1 CSRF Token Reuse Optimization
- **Priority:** CRITICAL
- **File:** `app/context_processors.py:130`
- **Issue:** `inject_csrf()` context processor calls `generate_csrf_token()` on EVERY request, generating new tokens unnecessarily and flooding the sliding window
- **Fix:** Modify the context processor to reuse existing token if available:
```python
# Change line 130 from:
return {"csrf_token": generate_csrf_token(), "csp_nonce": nonce}
# To:
tokens = session.get("csrf_tokens", [])
csrf_token = tokens[-1] if tokens else generate_csrf_token()
return {"csrf_token": csrf_token, "csp_nonce": nonce}
```
- **Note:** The `generate_csrf_token()` function in `app/csrf.py:23-36` always creates new tokens. The context processor should be modified to check for existing tokens first before calling `generate_csrf_token()`.
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k csrf`

### 1.2 Archive Route Memory Optimization
- **Priority:** CRITICAL
- **File:** `app/routes/public.py:155-184`
- **Issue:** Archive route loads full `Post.body` into memory for all posts (body can be 10KB+ per post)
- **Fix:** Add `defer(Post.body)` to archive query:
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
- **Issue:** When IP binding fails with `SESSION_IP_BINDING="enforce"`, the AdminSession DB record is NOT deleted before `session.clear()`. The `logout_user()` function only clears the Flask session, not the database record.
- **Fix:** Delete AdminSession DB record BEFORE calling `session.clear()`:
```python
if SESSION_IP_BINDING == "enforce":
    sid = session.get("admin_session_id")
    if sid:
        admin_session = db.session.execute(
            select(AdminSession).filter_by(session_id=sid)
        ).scalar_one_or_none()
        if admin_session:
            try:
                db.session.delete(admin_session)
                db.session.commit()
            except (IntegrityError, OperationalError):
                db.session.rollback()
    logout_user()
    session.clear()
    flash("Session invalidated due to IP address change.", "error")
    return redirect(url_for("admin.login"))
```
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k session`

### 1.4 pages.py IntegrityError Retry Logic
- **Priority:** CRITICAL
- **File:** `app/routes/admin/pages.py:78-91` (new_page function)
- **Issue:** After rollback on IntegrityError, only one slug attempt is made. If that slug also exists (edge case), the operation fails. The `edit_page()` function at lines 156-161 correctly re-fetches after rollback but `new_page()` does not.
- **Fix:** Create a retry loop similar to posts.py `_attempt_post_commit()` helper. The new_page function needs proper retry logic that regenerates slug on each attempt:
```python
def _attempt_page_commit(page, title, body, published, scheduled_publish_at=None):
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
- **Note:** The retry loop must be WITHIN the new_page function, not just a helper, to preserve all other field assignments.
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k pages`

---

## Wave 2: Security Hardening (Can parallelize with Wave 1)

### 2.1 Login Failure Delay Standardization
- **Priority:** HIGH
- **File:** `app/routes/admin/auth.py:70`
- **Issue:** Login failure uses hardcoded `time.sleep(0.05)` instead of configurable delay. The config `TOKEN_ENUMERATION_DELAY` (0.1s) is for token-based flows only (confirm/unsubscribe).
- **Fix:** Add new config `LOGIN_FAILURE_DELAY` in `app/config.py`:
```python
LOGIN_FAILURE_DELAY = float(os.environ.get("LOGIN_FAILURE_DELAY", "0.05"))
```
Then use it in auth.py:
```python
from app.config import LOGIN_FAILURE_DELAY
# ... at line 70:
time.sleep(LOGIN_FAILURE_DELAY)
```
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/test_security.py -v -k login`

### 2.2 SESSION_COOKIE_SECURE Runtime Enforcement
- **Priority:** HIGH
- **File:** `app/__init__.py` (around line 160, after the CSRF_ENABLED warning)
- **Issue:** No runtime check prevents disabling cookie security in production
- **Fix:** Add runtime enforcement after the existing CSRF_ENABLED warning:
```python
if not app.debug and not app.testing:
    if not app.config.get("SESSION_COOKIE_SECURE", True):
        raise RuntimeError(
            "SESSION_COOKIE_SECURE must be True in production. "
            "This is a security requirement."
        )
```
- **Verification:** Set `SESSION_COOKIE_SECURE=false` in config and verify app fails to start with RuntimeError

---

## Wave 3: Async Infrastructure (Can parallelize internally - depends on Celery setup)

### 3.1 Wire Celery Tasks
- **Priority:** HIGH
- **Files:** `app/tasks.py`, `app/webhooks.py:81`, `app/scheduler.py:125`
- **Issue:** Tasks in `app/tasks.py` are defined as plain Python functions, NOT as Celery tasks (no `@shared_task` decorator). The `.delay()` method would fail with AttributeError.
- **Fix:** Add `@shared_task` decorator to all task functions in `app/tasks.py`:
```python
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def generate_image_variants(self, image_path: str) -> bool:
    """Generate responsive image variants for an uploaded image."""
    # existing implementation
    ...

@shared_task(bind=True, max_retries=3, time_limit=600, soft_time_limit=540)
def send_newsletter_task(self, post_ids: List[int]) -> dict:
    """Send newsletter for specified posts (async via Celery)."""
    # existing implementation
    ...

@shared_task(bind=True, max_retries=3)
def deliver_webhook(self, webhook_event_id: int) -> bool:
    """Deliver a webhook event to registered endpoints."""
    # existing implementation
    ...
```
- **Update callers:**
  - `app/webhooks.py:81` - already calls `.delay()`, verify it works after adding decorator
  - `app/scheduler.py:125` - change from `send_newsletter()` direct call to `send_newsletter_task.delay(post_ids)`
- **Note:** The scheduler's `send_daily_newsletter()` should dispatch to Celery instead of running synchronously
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k celery`

### 3.2 Async Email Tasks
- **Priority:** HIGH
- **Files:** `app/tasks.py`, `app/routes/public.py:514`, `app/routes/admin/auth.py:162`, `app/routes/admin/subscribers.py:202`
- **Issue:** Email sending is synchronous, blocks requests for 2-5 seconds
- **Fix:** Create async email tasks in `app/tasks.py`:
```python
@shared_task
def send_confirmation_task(subscriber_id: int) -> bool:
    """Send confirmation email asynchronously."""
    from app.models import Subscriber
    sub = db.session.get(Subscriber, subscriber_id)
    if sub:
        from app.email import send_confirmation
        send_confirmation(sub)
        return True
    return False

@shared_task
def send_password_reset_task(user_id: int, token: str) -> bool:
    """Send password reset email asynchronously."""
    from app.models import User
    user = db.session.get(User, user_id)
    if user:
        from app.email import send_password_reset
        send_password_reset(user, token)
        return True
    return False
```
- **Update callers to use `.delay()`:**
  - `app/routes/public.py:514` - `_try_send_confirmation()`: change `send_confirmation(subscriber)` to `send_confirmation_task.delay(subscriber.id)`
  - `app/routes/admin/auth.py:162` - `forgot_password()`: change `send_password_reset(user, token)` to `send_password_reset_task.delay(user.id, token)`
  - `app/routes/admin/subscribers.py:202` - `bulk_resend()` loop: change `send_confirmation(sub)` to `send_confirmation_task.delay(sub.id)`
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k email`

### 3.3 Async Image Variant Generation
- **Priority:** HIGH
- **Files:** `app/storage.py:297-298`, `app/filters.py`
- **Issue:** Image variants generated synchronously on upload, blocking admin users
- **Fix:** Modify `upload_with_processing()` in `app/storage.py` to queue async generation:
```python
def upload_with_processing(filename: str, file_content: bytes, generate_variants: bool = True):
    # ... save file first (original) ...

    if generate_variants:
        # Queue async generation instead of blocking
        from app.tasks import generate_image_variants
        generate_image_variants.delay(filename)

    return filename, None
```
- **Add on-demand fallback in filters.py** if variant is missing:
```python
# In post_image_srcset_filter, check if variants exist
# If not, trigger generation and return base image only or None
```
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k image`

---

## Wave 4: Performance Optimizations (Can parallelize internally)

### 4.1 RSS Feed Caching
- **Priority:** MEDIUM
- **File:** `app/routes/rss.py:38-47, 138-142`
- **Fix:** Add `@flask_cache.cached(timeout=300)` to feed generation:
```python
from app import cache as flask_cache

@flask_cache.cached(timeout=300, key_prefix="rss_feed_")
def _get_cached_feed_posts(limit: int = 20):
    posts = db.session.execute(
        select(Post).filter_by(published=True)
        .order_by(Post.published_at.desc().nullslast(), Post.created_at.desc())
        .limit(limit)
    ).scalars().all()
    return posts
```
- **Add cache invalidation** on post publish/unpublish/delete (invalidate "rss_feed_" key)
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k rss`

### 4.2 Archive Years Caching
- **Priority:** MEDIUM
- **File:** `app/routes/public.py:137-143`
- **Fix:** Add `@flask_cache.cached(timeout=3600)` to `_get_available_years()`:
```python
@flask_cache.cached(timeout=3600, key_prefix="archive_years_")
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
- **Issue:** `post_image_srcset_filter` is defined twice. First definition (lines 52-73) uses `storage.exists()`, second (lines 95-116) uses `os.path.isfile()` which bypasses S3.
- **Fix:** DELETE lines 95-116 (the duplicate second definition)
- **Verification:** `grep -n "def post_image_srcset_filter" app/filters.py` should show only 1 match

### 4.4 Remove Dead Code in file_url_filter
- **Priority:** LOW
- **File:** `app/filters.py:75-93`
- **Issue:** Lines 82-93 are unreachable - code after `return storage.url(filename)` at line 81 can never execute
- **Fix:** DELETE lines 82-93 (redundant cache lookup code after return statement)
- **Verification:** Code review - ensure function only has the storage.url() return

### 4.5 Rate Limiting on /api/track-share
- **Priority:** MEDIUM
- **File:** `app/routes/public.py:467`
- **Fix:** Add `@limiter.limit("20 per minute")` to share tracking endpoint:
```python
@public.route("/api/track-share", methods=["POST"])
@limiter.limit("20 per minute")
def track_share() -> Response:
    ...
```
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k share`

### 4.6 Public Route Rate Limiting
- **Priority:** HIGH
- **File:** `app/routes/public.py`
- **Issue:** Most public routes lack rate limiting
- **Fix:** Add `@limiter.limit()` decorators:
  - `/search` - add `@limiter.limit("20 per minute")`
  - `/post/<slug>` - add `@limiter.limit("60 per minute")`
  - `/archive` - add `@limiter.limit("30 per minute")`
  - `/page/<slug>` - add `@limiter.limit("60 per minute")`
  - `/tag/<slug>` - add `@limiter.limit("60 per minute")`
- **Note:** Check existing limits in the file first to avoid duplicates
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k "rate or limit"`

---

## Wave 5: API Improvements (Can parallelize with Wave 4)

### 5.1 API Input Validation
- **Priority:** HIGH
- **File:** `app/routes/api.py:167-178`
- **Issue:** Missing input validation on API endpoints (title length, slug format, summary length, published type validation)
- **Fix:** Create `app/validators.py` with validation functions:
```python
# app/validators.py
from wtforms import Form, StringField, validators

def validate_string(value, max_length: int, field_name: str) -> tuple:
    """Validate a string field. Returns (value, error_message)."""
    if not isinstance(value, str):
        return "", f"{field_name} must be a string"
    if len(value) > max_length:
        return "", f"{field_name} exceeds {max_length} chars"
    return value, None

def validate_email(value: str, max_length: int = 256) -> tuple:
    """Validate email format and length."""
    if not isinstance(value, str):
        return "", "email must be a string"
    if len(value) > max_length:
        return "", "email exceeds {max_length} chars"
    if not is_valid_email(value):
        return "", "Invalid email format"
    return value, None

def validate_boolean(value, field_name: str) -> tuple:
    """Validate a boolean field."""
    if isinstance(value, bool):
        return value, None
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true", None
    return False, f"{field_name} must be a boolean"
```
- **Apply to API endpoints** in `app/routes/api.py` - `create_post()`, `update_post()`, `create_subscriber()`
- **Return 400** with field-specific error messages on validation failure
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
    existing = db.session.execute(
        select(Subscriber).filter_by(email=email)
    ).scalar_one_or_none()
    if existing:
        return jsonify(_subscriber_to_dict(existing)), 200
    raise

return jsonify(_subscriber_to_dict(subscriber)), 201
```
- **Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k api`

---

## Wave 6: Infrastructure (Can parallelize internally)

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
else:
    cache_config = {
        "CACHE_TYPE": "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 300,
    }
cache.init_app(app, config=cache_config)
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
- **Fix:** Add production pool settings (after db.init_app):
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
- **Issue:** `from flask import request` imported at module level (as `req`) AND inline in `get_client_ip()` function
- **Fix:** Remove redundant inline import, use module-level `req`:
```python
def get_client_ip():
    return req.headers.get('X-Forwarded-For', req.remote_addr) or req.remote_addr
```
- **Verification:** Code review

---

## Wave 7: Frontend Improvements (Can parallelize with Waves 3-6, Vite prerequisite for CSS split)

### 7.1 Add Vite Bundler
- **Priority:** HIGH
- **Files:** `app/static/js/main.js`, `vite.config.js`, base templates
- **Issue:** Too many HTTP requests (10-15 files per page) - no build step exists
- **Solution:** Vite with flask-vite integration
- **Implementation Steps:**
  1. Add to requirements.txt: `vite>=5.0.0`, `vite-plugin-flask>=0.1.0` (or similar)
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
  },
  server: {
    origin: 'http://127.0.0.1:5173',
    proxy: {
      '/': 'http://127.0.0.1:5000',
    },
  },
})
```
  3. Update `app/templates/base.html` to use bundled output in production:
```html
{% if config.DEBUG %}
<script type="module" src="http://127.0.0.1:5173/@vite.js"></script>
{% else %}
<script src="{{ url_for('static', filename='bundled/main.js') }}"></script>
{% endif %}
```
  4. Add `npm` scripts for development and build:
```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }
}
```
- **Effort:** 2-4 hours
- **Verification:** Load admin page, check network tab for reduced requests

### 7.2 CSS Architecture Split
- **Priority:** HIGH
- **File:** `app/static/css/style.css` (4,175 lines)
- **Solution:** Split into multiple files (can be done after Vite setup for CSS extraction):
```
app/static/css/
├── base.css       # Reset, fonts, variables
├── layout.css     # Container, navbar, sidebar
├── forms.css      # Form styles
├── admin.css      # Admin-specific
├── public.css     # Public-specific
└── utilities.css  # Utility classes
```
- **Effort:** 1-3 hours
- **Verification:** Manual testing of all page types

### 7.3 Remove Unused Import
- **Priority:** MEDIUM
- **File:** `app/static/js/admin/shortcuts.js:1`
- **Fix:** Remove unused `focusableSelectors` import:
```javascript
// DELETE this line:
import { focusableSelectors } from '../shared/utils.js';
```
- **Verification:** `grep -n "focusableSelectors" app/static/js/admin/shortcuts.js` should return nothing

### 7.4 Hardcoded Routes Fix
- **Priority:** MEDIUM
- **File:** `app/static/js/admin/shortcuts.js:30-34`, `app/templates/admin/base.html`
- **Fix:** Inject routes via data attribute in `admin/base.html`:
```html
<script>
  window.ADMIN_ROUTES = {
    posts: "{{ url_for('admin.dashboard') }}",
    pages: "{{ url_for('admin.list_pages') }}",
    subscribers: "{{ url_for('admin.subscribers') }}",
    tags: "{{ url_for('admin.tags') }}",
    dashboard: "{{ url_for('admin.index') }}",
  };
</script>
```
Then update shortcuts.js to use window.ADMIN_ROUTES:
```javascript
const routes = window.ADMIN_ROUTES || { d: '/admin/', p: '/admin/posts', s: '/admin/subscribers', t: '/admin/tags' };
```
- **Verification:** Vim keyboard shortcuts work correctly

### 7.5 Editor Preview Race Conditions
- **Priority:** MEDIUM
- **File:** `app/static/js/admin/editor.js:35-80`
- **Issue:** No debouncing on preview server requests - every keystroke triggers a request
- **Fix:**
  1. Add debounce (300ms) like search.js:
```javascript
let previewTimeout = null;
const debouncedFetchServerPreview = () => {
  clearTimeout(previewTimeout);
  previewTimeout = setTimeout(fetchServerPreview, 300);
};
```
  2. Update input listener:
```javascript
bodyTextarea.addEventListener('input', () => {
  renderClientPreview(text);
  debouncedFetchServerPreview();
});
```
- **Note:** Request abort logic already exists (lines 50-54), but no debouncing to limit request frequency
- **Verification:** Type in editor, preview updates without excessive requests

---

## Wave 8: Feature Enhancements (Can parallelize within phases, phase 3 depends on Waves 6-7)

### Phase 1: Quick Wins

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
  3. Add route to serve `/openapi.yaml`:
```python
@app.route('/openapi.yaml')
def openapi_spec():
    return send_from_directory(app.root_path, '../docs/openapi.yaml')
```
- **Verification:** Visit `/api/docs`, see Swagger UI

#### 8.2 Sitemap Enhancement - Add Archive Page
- **Priority:** HIGH
- **Effort:** 15-30 minutes
- **File:** `app/routes/public.py` (sitemap generator at lines 764-812)
- **Fix:** Add `/archive` URL to `_generate_sitemap()`:
```python
# Add after homepage entry:
urls.append({
    "loc": url_for("public.archive", _external=True),
    "changefreq": "weekly",
    "priority": "0.5"
})
```
- **Verification:** Check `/sitemap.xml` includes archive URL

#### 8.3 Open Graph Image Resolution
- **Priority:** MEDIUM
- **Effort:** 1 hour
- **Files:** `app/templates/page.html`, `app/templates/index.html`
- **Fix:** Add `og:image` meta tags with proper 1200x630 resolution:
  - `page.html` - add og_image block if page has image
  - `index.html` - add og_image block with site default
- **Verification:** Debug tool shows og:image on all page types

### Phase 2: Content Improvements

#### 8.4 Markdown Footnotes Support
- **Priority:** MEDIUM
- **Effort:** 30 minutes
- **File:** `app/filters.py:13`
- **Fix:** Add `"footnotes"` to markdown extensions:
```python
html = markdown.markdown(text, extensions=["fenced_code", "tables", "footnotes"])
```
- **Verification:** Create post with `[^1]` footnote syntax, verify renders

#### 8.5 Related Posts Tag Intersection Scoring
- **Priority:** MEDIUM
- **Effort:** 2-3 hours
- **File:** `app/routes/public.py:74-95` (`_get_related_posts()`)
- **Issue:** Orders by `created_at.desc()` (newest first), not by shared tag count
- **Fix:** Modify to score by number of shared tags:
```python
def _get_related_posts(post, limit=5):
    post_tag_ids = {tag.id for tag in post.tags}
    if not post_tag_ids:
        return []

    # Score by number of shared tags
    from sqlalchemy import func, label
    tag_count_subquery = (
        select(func.count(post_tags.c.tag_id))
        .where(post_tags.c.post_id == Post.id)
        .where(post_tags.c.tag_id.in_(post_tag_ids))
        .correlate(Post)
        .label('shared_tag_count')
    )

    query = (
        select(Post, tag_count_subquery)
        .options(joinedload(Post.tags))
        .filter(
            Post.published == True,
            Post.id != post.id,
            Post.tags.any(Tag.id.in_(post_tag_ids)),
        )
        .order_by(tag_count_subquery.desc(), Post.created_at.desc())
        .limit(limit)
    )
    results = db.session.execute(query).unique().scalars().all()
    return [r[0] for r in results]  # Extract Post objects
```
- **Verification:** Create posts with overlapping tags, verify ordering by tag count

#### 8.6 Atom Feed Support
- **Priority:** MEDIUM
- **Effort:** 2-3 hours
- **File:** `app/routes/rss.py`
- **Fix:** Add `/atom` route with Atom 1.0 format (parallel to RSS route):
```python
@rss.route("/atom")
def atom_feed():
    """Atom 1.0 feed."""
    posts = _get_feed_posts(limit=20)
    # Build Atom XML response
    # Use appropriate Atom schema elements: feed, entry, id, title, updated, link, content
```
- **Verification:** Visit `/atom`, validate against Atom spec

#### 8.7 Reading Time in Admin Dashboard
- **Priority:** LOW
- **Effort:** 30 minutes
- **File:** `app/templates/admin/dashboard.html`
- **Fix:** Add `{{ post.body | reading_time }}` display in post list items:
```html
<span class="reading-time">{{ post.body | reading_time }}</span>
```
- **Verification:** Dashboard shows reading time for each post

### Phase 3: Advanced Features (Require more work, some depend on Wave 6-7)

#### 8.8 Syntax Highlighting Theme Selector
- **Priority:** MEDIUM
- **Effort:** 4-6 hours
- **Files:** `app/models.py`, `app/routes/admin/settings.py`, `app/templates/admin/settings.html`, `app/static/js/main.js`
- **Requires:** Database migration for `SiteSettings.syntax_theme`
- **Implementation:**
  1. Add `syntax_theme` field to SiteSettings model
  2. Define `SYNTAX_THEMES` constant:
```python
SYNTAX_THEMES = {
    "okaidia": {"name": "Okaidia (Default)", "css": "prism-okaidia.css"},
    "github": {"name": "GitHub", "css": "prism-github.css"},
    "solarized-light": {"name": "Solarized Light", "css": "prism-solarized-light.css"},
    "dracula": {"name": "Dracula", "css": "prism-dracula.css"},
    "tomorrow-night": {"name": "Tomorrow Night", "css": "prism-tomorrow-night.css"},
}
```
  3. Add selector in admin settings
  4. Update main.js to load theme dynamically via data attribute on body
  5. Add additional Prism theme CSS files
- **Verification:** Change theme in settings, verify code blocks change

#### 8.9 Post Series/Collections Feature
- **Priority:** MEDIUM
- **Effort:** 6-8 hours
- **Files:** `app/models.py`, new `app/routes/admin/series.py`, `app/routes/public.py`
- **Requires:** Database migration
- **Implementation:**
  1. Create `Series` and `PostSeries` models:
```python
class Series(db.Model):
    __tablename__ = "series"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(500), default="")
    image = db.Column(db.String(256))
    created_at = db.Column(UTCDateTime, default=utc_now)
    posts = db.relationship("PostSeries", back_populates="series", order_by="PostSeries.order_index")

class PostSeries(db.Model):
    __tablename__ = "post_series"
    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(db.Integer, db.ForeignKey("series.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    order_index = db.Column(db.Integer, nullable=False)
    series = db.relationship("Series", back_populates="posts")
    post = db.relationship("Post")
```
  2. Add admin routes: `/admin/series`, `/admin/series/new`, `/admin/series/<id>/edit`
  3. Add public routes: `/series/<slug>`
  4. Update post page to show "Part X of Series Name"
  5. Add templates
- **Verification:** Create series, add posts, verify display

#### 8.10 Newsletter Email Preview
- **Priority:** LOW
- **Effort:** 3-4 hours
- **Files:** `app/routes/admin/newsletter.py`, `app/templates/admin/newsletter.html`
- **Fix:** Add `/admin/newsletter/preview` route:
```python
@admin.route("/newsletter/preview")
@admin_required
def newsletter_preview():
    # Get recent posts for preview
    # Render email template
    # Return HTML response
```
- **Verification:** Click preview, see newsletter email

#### 8.11 Scheduled Post Notifications
- **Priority:** LOW
- **Effort:** 2-3 hours
- **Files:** `app/routes/admin/dashboard.py`, `app/templates/admin/dashboard.html`
- **Fix:** Add "scheduled_posts_count" to dashboard metrics:
```python
# In dashboard metrics function:
scheduled_count = db.session.execute(
    select(func.count(Post.id)).filter(
        Post.scheduled_publish_at != None,
        Post.scheduled_publish_at <= utc_now(),
        Post.published == False
    )
).scalar()
# Add to returned dict: "scheduled_posts_count": scheduled_count
```
- **Add display in dashboard template** (badge or count indicator)
- **Verification:** Schedule a post, check dashboard shows count

---

## Already Correct (No Action Needed)

| Item | Source Plan | Reason |
|------|-------------|--------|
| Exception handling | 7 | All `except Exception` clauses justified |
| Admin session cleanup | 7 | Already optimized |
| API input validation | 7 | Current validation adequate for scale |
| Dashboard metrics | 7 | Current implementation adequate |
| Multi-machine scheduler | 7 | Already documented in DEPLOY.md |
| Token enumeration prevention | 2 | Already implemented with timing delay |
| Security headers | 2 | Full coverage already |
| Settings cache invalidation | 3 | Already fixed |
| Post tags index coverage | 4 | Already optimized |
| Synchronous webhooks | 4 | 10s timeout is reasonable |
| Newsletter transaction handling | 4 | Rollback reverts newsletter_sent_at |

---

## Dependencies Summary

### External Services Required
- **Redis** - For production caching and rate limiting (already in docker-compose.yml)
- **Celery worker/beat** - For async task processing (already configured)

### Database Migrations Required
- `Series`/`PostSeries` models (Wave 8, item 8.9)
- `SiteSettings.syntax_theme` field (Wave 8, item 8.8)

### Python Package Additions
- `flask-swagger-ui>=4.0.0` (Wave 8, item 8.1)
- `vite` + `vite-plugin-flask` (Wave 7, item 7.1) - verify exact package names

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

### Wave 1 (Critical) - Execute SEQUENTIALLY due to data integrity concerns
### Wave 2 (Security) - Can parallelize WITH Wave 1
### Wave 3 (Async) - Can parallelize internally, some depends on Wave 2
### Wave 4 (Performance) - Can parallelize internally
### Wave 5 (API) - Can parallelize WITH Wave 4
### Wave 6 (Infrastructure) - Can parallelize WITH Wave 5
### Wave 7 (Frontend) - Can parallelize WITH Waves 3-6, Vite is prerequisite for CSS split
### Wave 8 (Features) - Can parallelize within phases, phase 3 after Waves 6-7

### Recommended Implementation Order (Waves)
1. **Wave 1** (Critical fixes) - FIRST due to data integrity
2. **Wave 2** (Security) - PARALLEL with Wave 1
3. **Wave 3** (Async/Celery) - PARALLEL internally, after Wave 2 for some items
4. **Wave 4** (Performance) - PARALLEL with Wave 3
5. **Wave 5** (API) - PARALLEL with Wave 4
6. **Wave 6** (Infrastructure) - PARALLEL with Wave 5
7. **Wave 7** (Frontend) - AFTER Wave 3 complete (for Vite), PARALLEL with Waves 4-6
8. **Wave 8** (Features) - PARALLEL with Wave 7, Phase 3 after Waves 6-7 complete

### Sub-agent Task Groups
For parallel execution with sub-agents:

**Group A (Critical - Do First):**
- Wave 1 items 1.1, 1.2, 1.3, 1.4 (sequential)

**Group B (Security - Can parallelize with A):**
- Wave 2 items 2.1, 2.2

**Group C (Async Infrastructure):**
- Wave 3 items 3.1, 3.2, 3.3 (can parallelize after Group B)

**Group D (Performance):**
- Wave 4 items 4.1, 4.2, 4.3, 4.4, 4.5, 4.6 (can parallelize with Group C)

**Group E (API):**
- Wave 5 items 5.1, 5.2 (can parallelize with Group D)

**Group F (Infrastructure):**
- Wave 6 items 6.1, 6.2, 6.3, 6.4 (can parallelize with Group E)

**Group G (Frontend):**
- Wave 7 items 7.1, 7.2, 7.3, 7.4, 7.5 (7.1 is prerequisite for 7.2)

**Group H (Features):**
- Wave 8 items 8.1-8.11 (can parallelize within phases)

---

## Notes

- All database changes require `flask db migrate -m "description"` and `flask db upgrade`
- Redis and Celery services must be running for async features
- Some items may be combined or split based on implementation findings
- Verification tests should be run after each wave
- Vite setup (7.1) must precede CSS split (7.2) for optimal CSS extraction

---

## Wave Summary

| Wave | Items | Priority | Est. Effort |
|------|-------|----------|-------------|
| Wave 1: Critical Bug Fixes | 4 | CRITICAL | 1-2 hours |
| Wave 2: Security Hardening | 2 | HIGH | 30 min |
| Wave 3: Async Infrastructure | 3 | HIGH | 2-4 hours |
| Wave 4: Performance Optimizations | 6 | MEDIUM-LOW | 2-4 hours |
| Wave 5: API Improvements | 2 | HIGH | 1-2 hours |
| Wave 6: Infrastructure | 4 | MEDIUM | 1-2 hours |
| Wave 7: Frontend Improvements | 5 | HIGH | 4-8 hours |
| Wave 8: Feature Enhancements | 11 | MEDIUM-LOW | 23-33 hours |
| **TOTAL** | **~37 actionable** | - | **35-50 hours** |

(End of file - 682 lines)