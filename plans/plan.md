# Master Improvement Plan - Consolidated

**Date:** 2026-04-29
**Status:** PLANNED
**Summary:** Consolidated from all plans (plan2-9.md). Items verified against codebase marked ✓. Unverified items marked [REVIEW]. Implementation organized into waves for parallelization.

---

## VERIFICATION STATUS

Items marked ✓ are verified against the codebase. Items marked [REVIEW] need verification before implementation.

---

## WAVE 1: Critical Bug Fixes (Single-threaded, Sequential)

These must be fixed first as other improvements depend on stable code.

### 1.1: Fix sync_fts() Missing Arguments in cli.py [P0 - CRITICAL] ✓

**Issue:** `app/cli.py:255` calls `sync_fts(existing)` with only 1 argument, but function requires 5.
**Impact:** Import data command silently fails to sync FTS index for imported posts.

**File:** `app/cli.py`
**Lines:** 254-256
**Current code:**
```python
if existing and post_data.get("tags"):
    sync_fts(existing)
```

**Fix:**
```python
if existing and post_data.get("tags"):
    sync_fts(existing.id, existing.title, existing.body, existing.summary, existing.published)
```

**Priority:** P0 (Critical)
**Effort:** Low

---

### 1.2: Fix Search Snippet XSS Vulnerability [P0 - CRITICAL] ✓

**Issue:** `app/search.py:310-324` `highlight_query()` wraps user search input in `<mark>` tags without HTML escaping.
**Impact:** XSS vulnerability in search results.

**File:** `app/search.py`
**Lines:** 310-324

**Current code:**
```python
def highlight_query(text: str, query: str) -> str:
    if not text or not query:
        return text
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)
```

**Fix:**
```python
import html

def highlight_query(text: str, query: str) -> str:
    if not text or not query:
        return text
    escaped_text = html.escape(text)
    pattern = re.compile(re.escape(query), re.IGNECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", escaped_text)
```

**Priority:** P0 (Critical)
**Effort:** Low

---

### 1.3: Fix CSRF Token Rotation After Validation [P1 - HIGH] ✓

**Issue:** `app/csrf.py:54-59` removes used token but doesn't generate a new one.
**Impact:** Tokens don't rotate after validation (docs say they should).

**File:** `app/csrf.py`
**Lines:** 54-59

**Current code:**
```python
tokens = session.get("csrf_tokens", [])
for i, t in enumerate(tokens):
    if hmac.compare_digest(token, t):
        tokens.pop(i)
        session["csrf_tokens"] = tokens
        return
```

**Fix:**
```python
for i, t in enumerate(tokens):
    if hmac.compare_digest(token, t):
        tokens.pop(i)
        # Generate new token to maintain window size
        tokens.append(secrets.token_hex(32))
        # Trim to window size
        if len(tokens) > CSRF_TOKEN_WINDOW_SIZE:
            tokens = tokens[-CSRF_TOKEN_WINDOW_SIZE:]
        session["csrf_tokens"] = tokens
        return
```

**Priority:** P1 (High)
**Effort:** Low

---

### 1.4: Fix Cache Key Using id(post) Instead of post.id [P1 - HIGH] ✓

**Issue:** `app/filters.py:41,56` uses Python object `id(post)` which changes per query instance.
**Impact:** Cache misses on every request, defeating caching entirely.

**File:** `app/filters.py`
**Lines:** 41, 56

**Current code:**
```python
post_id = id(post)  # Line 41
cache_key = f"_post_srcset_cache_{id(post)}"  # Line 56
```

**Fix:**
```python
post_id = post.id  # Line 41 - use database primary key
cache_key = f"_post_srcset_cache_{post.id}"  # Line 56 - use database primary key
```

**Priority:** P1 (High)
**Effort:** Low

---

### 1.5: Fix Bare except Exception in storage.py [P2 - MEDIUM] ✓

**Issue:** `app/storage.py:168,175,182,198,325` catches ALL exceptions with bare `except Exception`.
**Impact:** Hides critical errors like KeyboardInterrupt, SystemExit.

**Files:** `app/storage.py`
**Lines:** 168, 175, 182, 198, 325

**Current pattern:**
```python
except Exception:
    return None
```

**Fix:**
```python
from botocore.exceptions import ClientError, BotoCoreError

except (ClientError, BotoCoreError) as e:
    logger.error("S3 operation failed: %s", e)
    return None
except (KeyboardInterrupt, SystemExit):
    raise
except Exception as e:
    logger.error("Unexpected error in S3 operation: %s", e)
    return None
```

**Priority:** P2 (Medium)
**Effort:** Low

---

### 1.6: Verify scheduler.py Exception Handling [P2 - MEDIUM] ✓

**Issue:** `app/scheduler.py:57` uses bare except for getting next run time. The code shows:

**File:** `app/scheduler.py`
**Lines:** 51-58

**Current code:**
```python
try:
    jobs = _scheduler.get_jobs()
    if not jobs:
        return None
    next_job = min(jobs, key=lambda j: j.next_run_time)
    return next_job.next_run_time
except Exception:
    return None
```

**Priority:** P2 (Medium)
**Effort:** Low
**Status:** Plan says to fix with specific exceptions - verify if this is still needed

---

### 1.7: Remove Unused Import [P3 - LOW] ✓

**Issue:** `app/routes/admin/helpers/posts.py:3` imports `flash` but never uses it.

**File:** `app/routes/admin/helpers/posts.py`
**Line:** 3

**Current:**
```python
from flask import current_app, flash
```

**Fix:**
```python
from flask import current_app
```

**Priority:** P3 (Low)
**Effort:** Very Low

---

## WAVE 2: Security Hardening (Can run parallel with Wave 1)

### 2.1: Add Rate Limiting to Sensitive Endpoints [P1 - HIGH] [REVIEW]

**Issue:** `/confirm/<token>`, `/unsubscribe/<token>`, `/forgot-password` not rate-limited.
**Impact:** Token enumeration attacks possible.

**Files to modify:** `app/routes/public.py`, `app/routes/admin/auth.py`

**Implementation:**
```python
# app/routes/public.py - Add decorators
@public.route("/confirm/<token>")
@limiter.limit("5 per minute")
def confirm(token) -> Response:

@public.route("/unsubscribe/<token>")
@limiter.limit("5 per minute")
def unsubscribe(token) -> Response:
```

```python
# app/routes/admin/auth.py
@admin.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def forgot_password() -> Response:
```

**Priority:** P1 (High)
**Effort:** Low

---

### 2.2: Configure Proxy-Aware Rate Limiting [P2 - MEDIUM] [REVIEW]

**Issue:** Flask-Limiter uses `get_remote_address` which doesn't respect X-Forwarded-For.

**File:** `app/__init__.py`

**Implementation:**
```python
def get_client_ip():
    from flask import request
    return request.headers.get('X-Forwarded-For', request.remote_addr) or request.remote_addr

limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["100 per minute"],
)
```

**Priority:** P2 (Medium)
**Effort:** Low

---

### 2.3: Enable Rate Limit Headers [P3 - LOW] [REVIEW]

**Issue:** `RATELIMIT_HEADERS_ENABLED = False` - clients can't see rate limits.

**File:** `app/__init__.py`

**Current:** Line 168 - `app.config["RATELIMIT_HEADERS_ENABLED"] = False`

**Fix:**
```python
app.config["RATELIMIT_HEADERS_ENABLED"] = not app.debug
```

**Priority:** P3 (Low)
**Effort:** Low

---

### 2.4: Add Content-Type Headers for Uploaded Files [P2 - MEDIUM] [REVIEW]

**Issue:** Uploaded images served without explicit Content-Type.

**File:** `app/__init__.py` or new route

**Implementation:**
```python
@public.route("/uploads/<filename>")
def serve_upload(filename):
    from flask import send_from_directory
    import mimetypes

    mimetypes.init()
    mime = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        filename,
        mimetype=mime
    )
```

**Priority:** P2 (Medium)
**Effort:** Medium

---

## WAVE 3: N+1 Query Fixes (Can run parallel after Wave 1 complete)

### 3.1: Verify N+1 Queries in API Routes [P1 - HIGH] [REVIEW]

**Issue:** May be missing `.options(joinedload(Post.tags))` in API routes and some public routes.

**Verified locations (✓ Already has joinedload):**
- `app/routes/public.py:82,104,157,291,339,351` - index, archive, tag, search pages ✓
- `app/routes/admin/posts.py:541` - bulk posts ✓
- `app/routes/admin/helpers/posts.py:14` - base query ✓

**Need verification - may be missing:**
- `app/routes/api.py:111` - `list_posts()` - need to check if tags accessed
- `app/routes/api.py:139` - `get_post()` - need to check if tags accessed
- `app/routes/api.py:231` - `update_post()` - need to check if tags accessed
- `app/routes/api.py:291` - `delete_post()` - need to check if tags accessed
- `app/routes/public.py:242` - `post()` route - no joinedload but template may not use tags
- `app/routes/public.py:449` - `public_preview()` - no joinedload but template doesn't use tags

**Note:** The `_post_to_dict()` helper in API may access post.tags. Need to verify.

**Priority:** P1 (High)
**Effort:** Medium

---

### 3.2: Add Query Parameter Redirect Support [P3 - LOW] [REVIEW]

**Issue:** `_safe_redirect_url()` only uses Referer header, should support explicit `next` parameter.

**File:** `app/routes/public.py`

**Implementation:**
```python
def _safe_redirect_url():
    from urllib.parse import urlparse

    # Check ?next= parameter first
    next_url = request.args.get("next")
    if next_url:
        parsed = urlparse(next_url)
        if parsed.netloc == "" or parsed.netloc == request.host:
            return next_url

    # Fall back to Referer header
    referrer = request.referrer
    if referrer:
        parsed = urlparse(referrer)
        if parsed.netloc == "" or parsed.netloc == request.host:
            return referrer

    return url_for("public.index")
```

**Priority:** P3 (Low)
**Effort:** Low

---

## WAVE 4: Code Quality Refactoring (Can run parallel after Wave 1 complete)

### 4.1: Extract Tag Count Query Helper [P2 - MEDIUM] [REVIEW]

**Issue:** `_get_tag_counts_cached()` and `_get_tag_counts_uncached()` are nearly identical.

**File:** `app/tag_cache.py`
**Lines:** 14-41

**Fix:** Create shared `_build_tag_counts_query()` helper.

**Priority:** P2 (Medium)
**Effort:** Medium

---

### 4.2: Create Cache Invalidation Helper [P2 - MEDIUM] [REVIEW]

**Issue:** Cache invalidation calls repeated 5+ times in posts.py.

**File:** `app/routes/admin/posts.py`
**Lines:** 157-160, 284-287, 434-436, 558-560, 578-579, 595-596, 613-614

**Fix:** Create `_invalidate_all_caches()` helper in `app/routes/admin/__init__.py`.

**Priority:** P2 (Medium)
**Effort:** Medium

---

### 4.3: Add Missing current_app Import [P3 - LOW] [REVIEW]

**Issue:** `app/routes/public.py:440` uses `current_app` without explicit import.

**File:** `app/routes/public.py`

**Fix:** Add `current_app` to imports.

**Priority:** P3 (Low)
**Effort:** Very Low

---

## WAVE 5: Cross-Platform & Thread-Safety (Can run parallel after Wave 1 complete)

### 5.1: Replace fcntl with filelock for Cross-Platform [P2 - MEDIUM] [REVIEW]

**Issue:** `fcntl` is Unix-only. No locking on Windows.

**File:** `app/scheduler.py`

**Fix:** Use `filelock` library for cross-platform compatibility:
```bash
pip install filelock
```

```python
from filelock import FileLock, FileLockException

def send_daily_newsletter(app) -> None:
    lock_path = os.path.join(app.instance_path, "newsletter.lock")
    lock = FileLock(lock_path, timeout=0)
    try:
        lock.acquire()
    except FileLockException:
        return

    try:
        # ... do work ...
    finally:
        lock.release()
```

**Priority:** P2 (Medium)
**Effort:** Medium
**Dependencies:** Add `filelock>=3.13.0` to requirements.txt

---

### 5.2: Fix S3 Client Thread-Safety [P2 - MEDIUM] [REVIEW]

**Issue:** `boto3.client()` is NOT thread-safe. Race condition in lazy property getter.

**File:** `app/storage.py`

**Fix:** Use `boto3.session.Session()` with thread lock:
```python
import threading
from botocore.config import Config

class S3StorageBackend(StorageBackend):
    def __init__(self, ...):
        self._client_lock = threading.Lock()

    @property
    def client(self):
        if self._client is None:
            with self._client_lock:
                if self._client is None:
                    session = boto3.session.Session(
                        aws_access_key_id=self.access_key,
                        aws_secret_access_key=self.secret_key,
                        region_name=self.region
                    )
                    config = Config(
                        retries={
                            'mode': 'standard',
                            'total_max_attempts': 5
                        }
                    )
                    client_kwargs = {'config': config}
                    if self.endpoint:
                        client_kwargs['endpoint_url'] = self.endpoint
                    self._client = session.client('s3', **client_kwargs)
        return self._client
```

**Priority:** P2 (Medium)
**Effort:** Medium

---

### 5.3: Page View Buffer Timezone Fix [P3 - LOW] [REVIEW]

**Issue:** `app/page_view_buffer.py:122` uses `datetime.now(timezone.utc)` instead of `utc_now()`.

**File:** `app/page_view_buffer.py`

**Fix:** Replace with `utc_now()` from utils.

**Priority:** P3 (Low)
**Effort:** Low

---

## WAVE 6: S3 Storage Fixes (Requires Wave 1 complete first)

### 6.1: Fix S3 Storage Read/Delete Operations [CRITICAL] [REVIEW]

**Problem:** Storage abstraction partially implemented but broken for reads/deletes.

**Affected files:**
- `app/filters.py` - Uses `os.path.isfile()` instead of `storage.exists()`
- `app/routes/admin/media.py` - Uses `os.scandir()` instead of `storage.list_files()`
- `app/utils.py` - `safe_delete_file()` uses `os.remove()` instead of `storage.delete()`
- `app/routes/rss.py:136` - Hardcoded `/static/uploads/` path
- `app/templates/` - Hardcoded `/static/uploads/` URLs

**Fix approach:**
1. Update `app/filters.py` to use `storage.exists()` and `storage.url()`
2. Update `app/routes/admin/media.py` to use `storage.list_files()`
3. Update `app/utils.py` to use `storage.delete()` for S3 backend
4. Update `app/routes/rss.py` to use `storage.url()`
5. Create new filter `{{ post.image | file_url }}` using `storage.url()`

**Priority:** CRITICAL
**Effort:** Medium
**Status:** Requires code fixes before documentation

---

### 6.2: Fix Backup Encryption UI [P2 - MEDIUM] [REVIEW]

**Problem:** Admin template missing encrypt checkbox.

**Affected files:**
- `app/templates/admin/backup.html` - Missing encrypt checkbox

**Fix:** Add encrypt checkbox:
```html
<div class="checkbox">
    <label>
        <input type="checkbox" name="encrypt" value="yes">
        Encrypt backup (requires BACKUP_ENCRYPTION_KEY env var)
    </label>
</div>
```

**Priority:** P2 (Medium)
**Effort:** Low

---

## WAVE 7: Frontend UX Improvements (Can run parallel after Wave 1-2 complete)

### 7.1: Search UX Improvements [P1 - HIGH] [REVIEW]

**Files:** `app/templates/base.html`, `app/static/js/public/search.js`, `app/static/css/style.css`

**Changes:**
- Add clear button to search input
- Update CSS for search input wrapper
- Add clear button event handler

**Priority:** P1 (High)

---

### 7.2: Post Card Keyboard Navigation [P2 - MEDIUM] [REVIEW]

**Files:** `app/templates/index.html`, `app/static/js/public/post-list.js` (new)

**Changes:**
- Create new post-list.js module
- Add keyboard navigation (j/k/arrows/Home/End)
- Add tabindex to post cards
- Add focus styles

**Priority:** P2 (Medium)

---

### 7.3: Pagination Enhancements [P1 - HIGH] [REVIEW]

**Files:** `app/templates/macros.html`, `app/templates/index.html`, `app/templates/search.html`, `app/templates/tag.html`

**Changes:**
- Rewrite pagination macro with page numbers, ellipsis, first/last links
- Update templates to use macro

**Priority:** P1 (High)

---

### 7.4: Form Error Accessibility [P1 - HIGH] [REVIEW]

**Files:** `app/templates/macros.html`, `app/templates/admin/page_editor.html`

**Changes:**
- Update field_error macro with ARIA attributes
- Add `aria-invalid` and `aria-describedby` to form inputs

**Priority:** P1 (High)

---

### 7.5: Password Visibility Toggle [P2 - MEDIUM] [REVIEW]

**Files:** `app/templates/admin/login.html`

**Changes:**
- Add password input wrapper
- Add show/hide toggle button (functionality already in utils.js)

**Priority:** P2 (Medium)

---

### 7.6: Tag Cloud Sizing by Post Count [P3 - LOW] [REVIEW]

**Files:** `app/templates/_sidebar.html`, `app/context_processors.py`, `app/static/css/style.css`

**Changes:**
- Add tag_min_count, tag_max_count to context
- Add weight-based CSS classes

**Priority:** P3 (Low)

---

### 7.7: Toast Notification Repositioning [P3 - LOW] [REVIEW]

**Files:** `app/static/js/shared/toast.js`, `app/static/css/style.css`

**Changes:**
- Reposition to top-center on mobile
- Update animation for top position

**Priority:** P3 (Low)

---

### 7.8: Search Suggestions Loading Indicator [P3 - LOW] [REVIEW]

**Files:** `app/static/js/public/search.js`, `app/static/css/style.css`

**Changes:**
- Add loading state during fetch
- Add loading CSS animation

**Priority:** P3 (Low)

---

### 7.9: Color-Scheme Meta Tag [P4 - VERY LOW] [REVIEW]

**Files:** `app/templates/base.html`, `app/templates/admin/base.html`

**Changes:**
- Add `<meta name="color-scheme" content="dark light">`

**Priority:** P4 (Very Low)

---

### 7.10: Mobile Share Button Visibility [P4 - VERY LOW] [REVIEW]

**Files:** `app/templates/_post_content.html`, `app/static/css/style.css`

**Changes:**
- Consider floating share button on mobile

**Priority:** P4 (Very Low)

---

## WAVE 8: Advanced Features (Future work - after Waves 1-7 complete)

### 8.1: Scheduled Post Visibility in Admin [P2 - MEDIUM] [REVIEW]

**Add "Upcoming" tab to posts dashboard to view scheduled posts.**

---

### 8.2: Editor Auto-save Enhancements [P2 - MEDIUM] [REVIEW]

**Add "Save Draft" button and optional server-side autosave.**

---

### 8.3: Webhook System [P3 - MEDIUM] [REVIEW]

**Add Webhook model, delivery service, and admin UI.**

---

### 8.4: API Analytics Endpoints [P3 - MEDIUM] [REVIEW]

**Add /api/stats/views, /api/stats/shares, /api/stats/top-posts.**

---

### 8.5: FTS Query Limits [P3 - LOW] [REVIEW]

**Add max query length and term limits to prevent abuse.**

---

### 8.6: Tag Count Refactor [P3 - LOW] [REVIEW]

**Extract shared tag count query helper.**

---

### 8.7: Redis Rate Limit Storage [P3 - LOW] [REVIEW]

**Configure Redis storage backend for multi-instance deployments.**

---

### 8.8: Admin Rate Limits [P3 - LOW] [REVIEW]

**Add rate limits to additional admin routes.**

---

### 8.9: Public Route Rate Limits [P3 - LOW] [REVIEW]

**Add rate limits to search, sitemap, feeds.**

---

## Wave Implementation Order

| Wave | Items | Can Start | Blocking |
|------|-------|-----------|----------|
| Wave 1 | 1.1-1.7 (Critical Bugs) | Now | Nothing |
| Wave 2 | 2.1-2.4 (Security) | Now | Wave 1 |
| Wave 3 | 3.1-3.2 (N+1 Queries) | After Wave 1 | Wave 1 |
| Wave 4 | 4.1-4.3 (Code Quality) | After Wave 1 | Wave 1 |
| Wave 5 | 5.1-5.3 (Cross-Platform) | After Wave 1 | Wave 1 |
| Wave 6 | 6.1-6.2 (S3 Storage) | After Wave 1 | Wave 1 |
| Wave 7 | 7.1-7.10 (Frontend UX) | After Wave 1-2 | Wave 1, Wave 2 |
| Wave 8 | 8.1-8.9 (Advanced) | After Waves 1-7 | All |

---

## Files to Modify Summary

| File | Wave | Changes |
|------|------|---------|
| `app/cli.py` | 1 | Fix sync_fts arguments |
| `app/csrf.py` | 1 | Add CSRF token rotation |
| `app/search.py` | 1 | Fix highlight_query XSS |
| `app/filters.py` | 1, 6 | Fix cache key, use storage |
| `app/storage.py` | 1, 5 | Fix bare except, thread safety |
| `app/scheduler.py` | 1, 5 | Fix bare except, filelock |
| `app/routes/admin/helpers/posts.py` | 1 | Remove unused import |
| `app/routes/public.py` | 2, 3 | Rate limits, N+1, next param |
| `app/routes/admin/auth.py` | 2 | Rate limits |
| `app/__init__.py` | 2 | Proxy-aware rate limits |
| `app/tag_cache.py` | 4 | Extract helper |
| `app/routes/admin/__init__.py` | 4 | Cache invalidation helper |
| `app/page_view_buffer.py` | 5 | Use utc_now |
| `app/utils.py` | 6 | Use storage.delete |
| `app/routes/admin/media.py` | 6 | Use storage.list_files |
| `app/routes/rss.py` | 6 | Use storage.url |
| `app/templates/admin/backup.html` | 6 | Add encrypt checkbox |
| `app/templates/base.html` | 7 | Search clear, color-scheme |
| `app/templates/macros.html` | 7 | Pagination, field_error |
| `app/templates/admin/login.html` | 7 | Password toggle |
| `app/templates/_sidebar.html` | 7 | Tag weighting |
| `app/static/js/public/search.js` | 7 | Clear button, loading |
| `app/static/js/public/post-list.js` | 7 | NEW - keyboard nav |
| `app/static/css/style.css` | 7 | Multiple CSS additions |

---

## Dependencies to Add

| Library | Wave | Purpose |
|---------|------|---------|
| filelock>=3.13.0 | 5 | Cross-platform file locking |

---

## Testing

After implementing any changes:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

---

## Priority Summary

| Priority | Items |
|----------|-------|
| P0 (Critical) | 1.1, 1.2 |
| P1 (High) | 1.3, 1.4, 2.1, 3.1, 7.1, 7.3, 7.4 |
| P2 (Medium) | 1.5, 1.6, 2.2, 2.4, 4.1, 4.2, 5.1, 5.2, 6.1, 6.2, 7.2, 7.5, 8.1, 8.2 |
| P3 (Low) | 1.7, 2.3, 3.2, 4.3, 5.3, 7.6, 7.7, 7.8, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9 |
| P4 (Very Low) | 7.9, 7.10 |
