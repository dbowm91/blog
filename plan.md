# DevLog Blog Platform — Consolidated Improvement Plan

Consolidated from plan2/plan3/plan4/plan5. All rate limiting items have been removed — rate limiting is handled by the reverse proxy.

---

## Phase 1: Security Fixes (Priority: HIGH)

### 1.1 CSRF constant-time comparison

**File:** `app/csrf.py:20`

**Problem:** `token != session.get("csrf_token")` uses Python's short-circuit comparison, enabling timing side-channel attacks.

**Fix:** Use `hmac.compare_digest()` (add `import hmac` at top of file).

```python
if not token or not hmac.compare_digest(token, session.get("csrf_token", "")):
    abort(403)
```

**Tests:** Existing CSRF tests pass — behavior identical, just timing-safe.

---

### 1.2 HSTS conditional on debug mode

**File:** `app/__init__.py:153`

**Problem:** `Strict-Transport-Security` is sent unconditionally. In local HTTP dev, browsers cache HSTS and block future HTTP access.

**Fix:** Only set when not in debug mode.

```python
if not current_app.debug:
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
```

**Tests:** Verify header absent when `app.debug=True`, present when `False`.

---

### 1.3 RSS link/guid XML escaping

**File:** `app/routes/rss.py:28,35-36,45,49`

**Problem:** `<link>` and `<guid>` values are inserted raw without `xml_escape()`. Inconsistent with `title` and `description` which are escaped. `BASE_URL` comes from config and could contain characters needing escaping.

**Fix:** Apply `xml_escape()` to link values in both item-level and channel-level elements.

**Tests:** Add test with a URL containing `&` to verify escaping.

---

### 1.4 confirm() — accurate message for expired tokens

**File:** `app/routes/public.py:276-282`

**Problem:** Expired confirmation deletes the subscriber but shows "Subscription confirmed!" — misleading.

**Fix:** Show accurate message:

```python
flash("This confirmation link has expired. Please subscribe again.", "warning")
```

**Tests:** Verify expired token shows warning instead of success.

---

## Phase 2: Bug Fixes (Priority: HIGH)

### 2.1 edit_post() IntegrityError rollback loses user edits

**File:** `app/routes/admin.py:291-296`

**Problem:** On slug collision `IntegrityError`, `db.session.rollback()` reverts ALL changes (title, body, summary, tags, image, published state). The retry only sets a new slug and commits — the user's edits are silently lost because SQLAlchemy expires attributes after rollback and re-reads from DB.

**Fix:** After rollback, re-query the post and reapply all field changes before committing:

```python
except IntegrityError:
    db.session.rollback()
    post = db.session.get(Post, post_id)
    post.title = title
    post.body = body
    post.summary = summary
    post.slug = _generate_unique_slug(title, exclude_id=post.id)
    post.published = published
    if published and not was_published:
        post.published_at = utc_now()
    post.tags = _get_or_create_tags(tag_names)
    if image:
        post.image = image
    db.session.commit()
```

**Tests:** Edit a post triggering slug collision; verify body/summary/tags preserved.

---

### 2.2 new_post() IntegrityError — orphaned image cleanup

**File:** `app/routes/admin.py:224-234`

**Problem:** If the first commit fails, the uploaded image file exists on disk. If the retry also fails or the code is refactored, the orphaned image stays.

**Fix:** After rollback, delete the uploaded image before retrying with a fresh `_save_image()` call:

```python
except IntegrityError:
    db.session.rollback()
    if image:
        try:
            os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], image))
        except FileNotFoundError:
            pass
    slug = _generate_unique_slug(title + "-post")
    image, error = _save_image(request.files.get("image"))
    # ... recreate post ...
```

**Tests:** Test that new_post handles IntegrityError and creates the post with correct image.

---

### 2.3 Subscriber model default expires_at

**File:** `app/models.py:103`

**Problem:** Model default is `timedelta(hours=1)`. The subscribe route always overrides this from config, so the default is misleading dead code.

**Fix:** Change to 365 days to serve as a sensible fallback:

```python
default=lambda: utc_now() + timedelta(days=365)
```

**Tests:** Existing subscriber tests pass — default is overridden in all code paths.

---

### 2.4 Remove unused datetime import

**File:** `app/routes/public.py:1`

**Problem:** Line 1 imports `datetime` class but it is never used in the file. Only `timedelta` (line 4) is used.

**Fix:** Remove `from datetime import datetime` on line 1.

---

## Phase 3: Performance Improvements (Priority: HIGH)

### 3.1 Add composite indexes on PageView and ShareEvent

**File:** `app/models.py`

**Current state:** `PageView` has separate indexes on `post_id` and `created_at`. `ShareEvent` has an index on `post_id` only. Analytics queries that filter by both columns would benefit from composite indexes.

**Action:**
- Replace individual indexes with composite: `db.Index("ix_page_views_post_created", "post_id", "created_at")`
- Add composite: `db.Index("ix_share_events_post_created", "post_id", "created_at")`

**Migration:** `flask db migrate -m "Add composite indexes on PageView and ShareEvent" && flask db upgrade`

---

### 3.2 Add index on Post.published_at

**File:** `app/models.py`

**Problem:** Newsletter and analytics queries filter on `published_at` without an index.

**Action:** Add `db.Index("ix_posts_published_at", "published_at")` to `Post.__table_args__`.

**Migration:** `flask db migrate -m "Add index on Post.published_at" && flask db upgrade`

---

### 3.3 Tag count query — double-checked locking

**File:** `app/routes/public.py:37-51`

**Problem:** The DB query runs inside `_TAG_CACHE_LOCK`. If the query is slow, all concurrent requests block waiting for the lock.

**Fix:** Use double-checked locking — only hold the lock for cache reads/writes, run the query outside:

```python
def _get_tag_counts():
    with _TAG_CACHE_LOCK:
        now = _time.monotonic()
        if _TAG_COUNTS_CACHE["data"] is not None and (now - _TAG_COUNTS_CACHE["timestamp"]) < _TAG_COUNTS_TTL:
            return _TAG_COUNTS_CACHE["data"].copy()

    counts = (...)  # DB query outside lock
    result = {row[0]: row[1] for row in counts}

    with _TAG_CACHE_LOCK:
        now = _time.monotonic()
        if _TAG_COUNTS_CACHE["data"] is None or (now - _TAG_COUNTS_CACHE["timestamp"]) >= _TAG_COUNTS_TTL:
            _TAG_COUNTS_CACHE["data"] = result
            _TAG_COUNTS_CACHE["timestamp"] = now
            return result.copy()
        return _TAG_COUNTS_CACHE["data"].copy()
```

**Tests:** Existing cache tests pass.

---

### 3.4 Optimize media gallery — cap file count

**File:** `app/routes/admin.py:537`

**Problem:** All files are loaded and sorted into memory. With thousands of uploads this is slow and unbounded.

**Fix:** Cap at 1000 files. Use `os.scandir()` instead of `glob.glob()` for better performance. Show notice in template when truncated.

**Tests:** Existing media page test continues to pass.

---

### 3.5 Optimize search query

**File:** `app/routes/public.py:145-173`

**Problem:** Searching on `body` column via `ILIKE` is slow with large content.

**Options:**
- **Option A:** Add SQLite FTS (Full-Text Search) — no breaking changes
- **Option B:** Remove body from search, limit to title and summary

---

### 3.6 Add database connection pooling config

**File:** `app/__init__.py`

**Action:**

```python
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}
```

---

### 3.7 Add ProxyFix middleware

**File:** `app/__init__.py`

**Problem:** `request.remote_addr` returns the proxy IP, not the client IP, behind reverse proxies.

**Fix:**

```python
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
```

---

## Phase 4: Newsletter Reliability (Priority: HIGH)

### 4.1 send_newsletter() — return success/failure

**File:** `app/email.py:70-127`

**Problem:** `send_newsletter()` returns `None`. No signal to the caller about success.

**Fix:** Return `True` (all sent) or `False` (some failures). Track per-subscriber success.

---

### 4.2 Scheduler — only mark sent on success

**File:** `app/scheduler.py:48-53`

**Problem:** Scheduler unconditionally marks posts as sent after calling `send_newsletter()`, regardless of whether emails were actually delivered.

**Fix:**

```python
success = send_newsletter(posts, subscribers)
if success:
    now = utc_now()
    for post in posts:
        post.newsletter_sent_at = now
    db.session.commit()
else:
    logger.warning("Newsletter had failures; posts will be retried on next run")
```

**Tests:** Test that send_newsletter returns False on SMTP failure; posts not marked as sent.

---

## Phase 5: Code Quality (Priority: MEDIUM)

### 5.1 Extract tag cache to separate module

**File:** Create `app/cache.py`, modify `app/routes/public.py`, `app/routes/admin.py`

**Problem:** Cross-blueprint import (`admin.py` imports `invalidate_tag_cache` from `public.py`) creates coupling.

**Action:** Extract `_TAG_COUNTS_CACHE`, `_TAG_COUNTS_TTL`, `_TAG_CACHE_LOCK`, `invalidate_tag_cache()`, and `_get_tag_counts()` into `app/cache.py`. Update imports in both route modules.

---

### 5.2 Add ProxyFix (see 3.7)

Already covered above.

---

### 5.3 config.toml base_url — use http for localhost

**File:** `config.toml:25`

**Problem:** `base_url = "https://localhost:5000"` with no TLS configured. Combined with HSTS, this breaks browsers.

**Fix:** Change to `http://localhost:5000`. Users set real HTTPS URL in production.

---

### 5.4 Improve admin user creation error handling

**File:** `app/__init__.py:186-203`

**Problem:** Ambiguous behavior when `ADMIN_PASSWORD` env var doesn't match stored password.

**Fix:** Add explicit logging when password mismatch detected. Make error handling more explicit.

---

### 5.5 Add type hints to utility functions

**Files:** `app/utils.py`, `app/base62.py`, `app/email.py`

**Action:** Add complete type hints for better IDE support and documentation.

---

## Phase 6: Observability (Priority: MEDIUM)

### 6.1 Add request ID tracking

**File:** `app/__init__.py`

**Action:** Add middleware that generates a unique ID per request (`X-Request-ID` header), includes it in log output.

---

### 6.2 Add request timing middleware

**File:** `app/__init__.py`

**Action:** Log requests that take >1s with method, path, and duration.

---

### 6.3 Enhance logging

**Files:** `app/__init__.py`, various modules

**Actions:**
- Add structured logging (JSON format option)
- Add performance logging for slow queries

---

## Phase 7: Testing (Priority: HIGH)

### 7.1 Add newsletter scheduler tests

**File:** Create `tests/test_newsletter.py`

**Tests:**
- `test_scheduler_sends_to_confirmed_only()` — only confirmed, unsubscribed=None receive
- `test_scheduler_excludes_expired_subscribers()` — expired expires_at excluded
- `test_newsletter_sent_at_prevents_duplicates()` — flag set after sending
- `test_newsletter_test_endpoint()` — POST /admin/newsletter-test works
- `test_newsletter_reset_endpoint()` — POST /admin/newsletter-reset/<id> clears flag
- `test_newsletter_returns_false_on_smtp_failure()` — send_newsletter returns False

---

### 7.2 Add security header tests

**File:** Create `tests/test_security.py`

**Tests:**
- `test_csp_header()` — CSP header present and correct
- `test_hsts_conditional()` — HSTS absent in debug, present in production
- `test_csrf_protection()` — POST without token fails
- `test_x_frame_options()` — X-Frame-Options is DENY
- `test_referrer_policy()` — Referrer-Policy header present

---

### 7.3 Add page view deduplication tests

**File:** Add to `tests/test_public.py`

**Tests:**
- `test_page_view_deduplication()` — same session, same post = 1 view only
- `test_max_viewed_posts_cap()` — session capped at MAX_VIEWED_POSTS

---

## Phase 8: Robustness (Priority: LOW)

### 8.1 Orphan tag cleanup

**File:** `app/routes/admin.py` (delete_post, edit_post, bulk_operations)

**Problem:** When posts are deleted or tags removed, tag records with zero posts remain in DB.

**Fix:** Add `_cleanup_orphan_tags()` helper. Call after `invalidate_tag_cache()` in delete_post, edit_post, and bulk_operations delete branch.

**Tests:** Create post with tags, delete post, verify orphaned tags removed.

---

### 8.2 Validate image dimensions

**File:** `app/routes/admin.py`

**Action:** Add optional dimension checking in `_save_image()`.

---

### 8.3 Scheduler graceful shutdown

**File:** `app/scheduler.py`

**Action:** Verify scheduler shuts down on app teardown.

---

## Phase 9: User Experience (Priority: LOW)

### 9.1 Add search result count

**File:** `app/templates/search.html`

**Action:** Display "Found X result(s)" before pagination.

---

### 9.2 Add auto-save indicator

**File:** `app/templates/admin/editor.html`

**Action:** Show "Saving..." / "Saved" indicator during draft autosave.

---

## Phase 10: Features (Priority: LOW)

### 10.1 Add password change endpoint

**File:** `app/routes/admin.py`, `app/templates/admin/password.html`

**Action:** Add `GET/POST /admin/password` route with current password verification.

---

### 10.2 Add post scheduling

**File:** `app/models.py`, `app/routes/admin.py`, `app/scheduler.py`

**Action:** Add `scheduled_at` column, scheduler job, and UI for scheduling.

---

### 10.3 Add export functionality

**File:** `app/routes/admin.py`

**Action:** Export posts as Markdown or JSON for backup.

---

## Execution Order

### Sprint 1: Security & Bug Fixes (1-2 days)
1. CSRF constant-time comparison (1.1)
2. HSTS conditional on debug (1.2)
3. config.toml base_url fix (5.3)
4. Remove unused import (2.4)
5. RSS XML escaping (1.3)
6. confirm() expired message (1.4)
7. Subscriber default expires_at (2.3)
8. edit_post IntegrityError fix (2.1)
9. new_post IntegrityError image cleanup (2.2)

### Sprint 2: Performance (1-2 days)
10. Composite indexes on PageView/ShareEvent (3.1)
11. Index on Post.published_at (3.2)
12. Tag count query double-checked locking (3.3)
13. Media gallery file cap (3.4)
14. ProxyFix middleware (3.7)
15. DB connection pooling (3.6)

### Sprint 3: Newsletter & Testing (2-3 days)
16. send_newsletter return value (4.1)
17. Scheduler success check (4.2)
18. Newsletter scheduler tests (7.1)
19. Security header tests (7.2)
20. Page view dedup tests (7.3)

### Sprint 4: Code Quality & UX (1-2 days)
21. Extract tag cache (5.1)
22. Admin user error handling (5.4)
23. Request ID tracking (6.1)
24. Request timing (6.2)
25. Search result count (9.1)
26. Auto-save indicator (9.2)

---

After each change: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v`
