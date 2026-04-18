# Improvement Plan

Consolidated from all plan files. Items organized into waves for parallel implementation.

---

## Summary

This document consolidates improvement items from plans 2-6 into a unified plan with wave-based organization for parallel execution. Items marked **[VERIFIED UNFIXED]** have been confirmed against the current codebase as still needing attention.

---

## Wave 1: Critical Bugs (Sequential - Blocks Other Work)

These items are functional bugs that break existing behavior and must be fixed first.

### 1. SMTP Connection Closed Before Use **[VERIFIED UNFIXED]**
**File:** `app/email.py:65-85`
**Severity:** Critical
**Impact:** Newsletter emails fail to send; every `sendmail()` raises `SMTPServerDisconnected`

**Root Cause:**
The `finally` block executes `server.quit()` **before** the `return` statement completes. Python's `finally` always runs before the return value is captured by the caller.

```python
def _connect_smtp() -> Optional[smtplib.SMTP]:
    server = None
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT)
        # ... setup ...
        return server  # finally runs BEFORE this completes
    finally:
        if server:
            server.quit()  # Closes connection before caller can use it!
```

**Fix:**
Remove the `finally` block entirely. Let `send_newsletter()` manage connection lifecycle via its own `try/finally` (already present at lines 192-196).

```python
def _connect_smtp() -> Optional[smtplib.SMTP]:
    server = None
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT)
        server.ehlo()
        context = ssl.create_default_context()
        server.starttls(context=context)
        server.ehlo()
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASSWORD)
        return server
    except (smtplib.SMTPException, OSError):
        logger.exception("Failed to connect to SMTP server")
        return None
    # No finally - caller manages cleanup
```

**Verification:**
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -c "
from app import create_app
from app.email import send_newsletter
app = create_app()
with app.app_context():
    result = send_newsletter(1)
    print('Newsletter result:', result)
"
```

---

### 2. Footer Cache Never Serves Cached Data **[VERIFIED UNFIXED]**
**File:** `app/context_processors.py:65-104`
**Severity:** Critical
**Impact:** Every request executes 2 DB queries despite cache; cache is populated but never served. Additionally, DB queries hold the lock for the entire query duration.

**Root Cause:**
When cache is stale, the function re-queries the database, stores results in cache, then returns the fresh results instead of the cached data. The DB queries also run while holding the lock.

```python
def _get_footer_data() -> dict:
    with _FOOTER_CACHE_LOCK:  # Lock held during entire query!
        now = _time.monotonic()
        if (_FOOTER_CACHE["data"] is not None
            and (now - _FOOTER_CACHE["timestamp"]) < _FOOTER_TTL):
            return _FOOTER_CACHE["data"].copy()  # Returns here correctly

        # DB queries run INSIDE the lock (lines 80-92)
        recent_posts = db.session.execute(...)
        footer_tags = db.session.execute(...)

        _FOOTER_CACHE["data"] = {...}  # Cache populated

    return {  # Returns FRESH data, not cached!
        "recent_posts_footer": recent_posts,
        ...
    }
```

**Fix:**
1. Use double-checked locking: check cache validity inside lock, but query DB outside lock, then re-check and update cache inside lock
2. After populating the cache, return `_FOOTER_CACHE["data"].copy()` instead of the fresh variables

**Verification:** Add logging to confirm cache hits; measure DB query count per request.

---

### 3. Missing `func` Import Causes Scheduler Crash **[VERIFIED UNFIXED]**
**File:** `app/scheduler.py:16,95`
**Severity:** Critical
**Impact:** `send_daily_newsletter()` crashes with `NameError` when run by scheduler

**Root Cause:**
```python
from sqlalchemy import select  # Line 16 - func NOT imported

# Line 95 - uses func.count() without import:
subscriber_count = db.session.execute(
    select(func.count(Subscriber.id))
    ...
).scalar()
```

**Fix:**
Add `func` to the import:
```python
from sqlalchemy import func, select
```

**Verification:**
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -c "
from app import create_app
from app.scheduler import send_daily_newsletter
app = create_app()
with app.app_context():
    send_daily_newsletter()
"
```

---

### 4. Undefined CSS Variable `--bg-primary` **[VERIFIED UNFIXED]**
**File:** `app/static/css/style.css:1299`
**Severity:** Critical (Broken CSS)
**Impact:** `.btn-danger-primed` uses `var(--bg-primary)` which is never defined in `:root`. Users may see invisible or incorrectly colored text.

**Current State (style.css lines 1297-1302):**
```css
.btn-danger-primed {
    background: var(--red);
    color: var(--bg-primary);  /* NEVER DEFINED - should be --bg or #fff */
    font-weight: bold;
    animation: pulse-danger 1s ease-in-out infinite;
}
```

**Fix:**
Replace `var(--bg-primary)` with `var(--bg)`:
```css
.btn-danger-primed {
    background: var(--red);
    color: var(--bg);
    font-weight: bold;
    animation: pulse-danger 1s ease-in-out infinite;
}
```

**Verification:**
1. Navigate to dashboard, select posts for bulk delete
2. Click delete, verify confirmation button has legible text on red background
3. Verify button pulse animation is visible

---

### 5. Admin Preview Extends Wrong Base Template **[VERIFIED UNFIXED]**
**File:** `app/templates/admin/preview.html:1`
**Severity:** Critical (Template Bug)
**Impact:** Preview page breaks admin context and navigation.

**Current State (preview.html lines 1-10):**
```jinja
{% extends "base.html" %}  {# Should be "admin/base.html" #}

{% block title %}[Preview] {{ post.title }} | {{ site_title }}{% endblock %}

{% block content %}
<div class="preview-banner">
    Preview Mode {% if not post.published %}(Draft){% endif %} &mdash; only visible to you
</div>
{% include "_post_content.html" %}
{% endblock %}
```

**Fix:**
Change the extends directive:
```jinja
{% extends "admin/base.html" %}
```

**Verification:**
1. Navigate to `/admin/preview/<post_id>` for a draft post
2. Verify admin navbar is visible at top
3. Verify keyboard shortcuts work (press `?`)
4. Verify no JavaScript errors in console

---

## Wave 2: Security & Session Fixes (Can Run in Parallel)

### 6. Logout Endpoint Missing CSRF Validation **[VERIFIED UNFIXED]**
**File:** `app/routes/admin/auth.py:54`
**Severity:** High (Security)
**Impact:** Session fixation possible if attacker can trigger logout via CSRF

**Current State:**
```python
@admin.route("/logout", methods=["POST"])
@login_required  # Has @login_required but no CSRF check
def logout():
    session.clear()
    ...
```

**Fix:**
Add CSRF validation to the logout route, similar to other POST routes in the codebase.

**Verification:** Verify logout POST without valid CSRF token is rejected.

---

### 7. DB Query on Every Admin Request **[VERIFIED UNFIXED]**
**File:** `app/routes/admin/__init__.py:25-38`
**Severity:** High (Performance)
**Impact:** `admin_required` queries `AdminSession` table on every admin page view just to check IP address

**Root Cause:**
```python
@admin_required
def some_admin_route():
    # This decorator runs on EVERY admin request:
    sid = session.get("admin_session_id")
    if sid:
        admin_session = db.session.execute(
            select(AdminSession).filter_by(session_id=sid)
        ).scalar_one_or_none()
        if admin_session and admin_session.ip_address:
            # Only logs a warning if IP changed - doesn't actually invalidate
            ...
```

**Fix:**
Store admin session metadata in the encrypted Flask session instead of querying the database. The IP address check is a soft warning — it doesn't invalidate sessions, just logs.

```python
# In admin_required decorator:
sid = session.get("admin_session_id")
if sid:
    stored_ip = session.get("admin_session_ip")
    current_ip = request.remote_addr
    if stored_ip and current_ip and stored_ip != current_ip:
        logger.warning("IP address changed for admin session", ...)
        # Optionally: could require re-login here
```

Only query the DB when explicitly revoking a session or checking validity.

**Verification:**
Profile admin dashboard with multiple page loads and verify query count decreases.

---

### 8. ShareEvent Platform Should Use Allowlist Validation **[VERIFIED UNFIXED]**
**File:** `app/routes/public.py:431`
**Severity:** Low (Security)
**Impact:** Arbitrary strings up to 32 characters accepted as platform identifier

**Current State:**
```python
platform = str(data["platform"])[:32]
```

**Fix:**
```python
ALLOWED_SHARE_PLATFORMS = {"twitter", "facebook", "linkedin", "reddit", "hackernews", "link"}

platform = str(data["platform"])[:32]
if platform not in ALLOWED_SHARE_PLATFORMS:
    return jsonify({"error": "invalid platform"}), 400
```

**Verification:**
```bash
curl -X POST /api/track-share \
  -H "Content-Type: application/json" \
  -d '{"post_id": 1, "platform": "<script>alert(1)</script>"}'
# Should return 400
```

---

### 9. Add List-Unsubscribe Header to Newsletter Emails **[VERIFIED UNFIXED]**
**File:** `app/email.py`
**Severity:** Low (Email Deliverability)
**Impact:** Missing RFC 8058 compliant List-Unsubscribe header; some email clients cannot offer one-click unsubscribe

**Current State:**
Newsletter emails are sent with unsubscribe URLs in the body but lack the `List-Unsubscribe` and `List-Unsubscribe-Post` headers.

**Fix:**
For newsletters (in `send_newsletter()` around line 164), add headers before sending:
```python
msg["List-Unsubscribe"] = f"<{unsub_url}>"
msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
```

For confirmation emails (`send_confirmation()` at line 46), modify to not use `_send_email()` and build the message inline with headers, or add an optional `extra_headers` parameter to `_send_email()`.

**Verification:**
Send a test newsletter and confirmation email; inspect raw headers for `List-Unsubscribe`.

---

## Wave 3: Performance Improvements (Can Run in Parallel)

### 10. N+1 Query Problem on Admin Dashboard **[VERIFIED UNFIXED]**
**File:** `app/routes/admin/helpers/posts.py` (`_get_posts_query`)
**Severity:** High (Performance)
**Impact:** Each post on the dashboard triggers a separate query to load its tags

**Root Cause:**
`_get_posts_query()` does not use eager loading:
```python
def _get_posts_query(status: str, search: str, order_by=None) -> select:
    base_q = select(Post)  # No joinedload(Post.tags)
```

But `dashboard.html:95` accesses tags:
```html
{% for tag in post.tags %}
```

**Fix:**
Add `joinedload(Post.tags)` to the base query:
```python
from sqlalchemy.orm import joinedload

def _get_posts_query(status: str, search: str, order_by=None) -> select:
    base_q = select(Post).options(joinedload(Post.tags))
    ...
```

**Also fix:** `app/routes/admin/helpers/analytics.py:65-69` — top posts query also missing eager loading.

**Verification:**
Enable SQLAlchemy echo logging to verify query count.

---

### 11. LIKE Fallback Causes Full Table Scans **[VERIFIED UNFIXED]**
**File:** `app/routes/public.py:350-368`
**Severity:** High (Performance)
**Impact:** Search without FTS5 runs 3 full table scans with leading wildcards

**Root Cause:**
```python
escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
search_term = f"%{escaped}%"  # Leading wildcard - can't use index
```

**Fix:**
Prefer FTS5 more aggressively — return no results from FTS if it has no matches, rather than falling back to LIKE:
```python
post_ids = _fts_search(query)  # FTS search
if post_ids:
    pagination = db.paginate(
        select(Post)
        .options(joinedload(Post.tags))
        .filter(Post.published == True, Post.id.in_(post_ids))
        ...
    )
else:
    # Only fallback to LIKE if FTS returns nothing AND FTS table exists
    pagination = db.paginate(
        select(Post)
        .options(joinedload(Post.tags))
        .filter(
            Post.published == True,
            Post.summary.ilike(search_term, escape="\\"),  # Only summary
        )
        ...
    )
```

**Verification:**
```bash
ADMIN_PASSWORD=test SECRET_KEY=test sqlite3 instance/blog.db "DROP TABLE IF EXISTS posts_fts;"
```

---

### 12. String Replace Per Subscriber in Newsletter **[VERIFIED UNFIXED]**
**File:** `app/email.py:148-163`
**Severity:** Medium (Performance)
**Impact:** 20K string allocations for 10K subscribers; GC pressure

**Current:**
```python
for i, sub in enumerate(subscribers, 1):
    unsub_url = unsub_url_base + sub.token
    html = pre_rendered_html.replace(unsub_url_base + "TOKEN", unsub_url)  # New string
    text = pre_rendered_text.replace(unsub_url_base + "TOKEN", unsub_url)  # New string
    ...
```

**Fix:**
Split template by TOKEN marker and join with personalized URLs:
```python
# Pre-split template once
html_parts = pre_rendered_html.split("TOKEN")
text_parts = pre_rendered_text.split("TOKEN")

for i, sub in enumerate(subscribers, 1):
    unsub_url = unsub_url_base + sub.token
    html = html_parts[0] + unsub_url + html_parts[1]  # Join instead of replace
    text = text_parts[0] + unsub_url + text_parts[1]
    ...
```

**Verification:**
Memory profile newsletter sending with large subscriber list.

---

### 13. Bulk Operations N Separate FTS Syncs **[VERIFIED UNFIXED]**
**File:** `app/routes/admin/posts.py:460-475`, `app/scheduler.py:237-243`
**Severity:** Medium (Performance)
**Impact:** Bulk publish/delete runs N DELETE + N INSERT statements

**Fix:**
Batch FTS updates using `INSERT OR REPLACE` with executemany:
```python
# In app/search.py, add:
def sync_fts_batch(items: list[tuple]):
    """Batch sync multiple posts to FTS index."""
    if not items:
        return
    try:
        db.session.execute(
            text("DELETE FROM posts_fts WHERE rowid = :id"),
            [{"id": item[0]} for item in items]
        )
        published_items = [item for item in items if item[4]]
        if published_items:
            db.session.execute(
                text("INSERT INTO posts_fts(rowid, title, body, summary) VALUES(:id, :title, :body, :summary)"),
                [{"id": i[0], "title": i[1], "body": i[2], "summary": i[3]} for i in published_items]
            )
    except Exception:
        logger.exception("FTS batch sync failed")
```

**Verification:**
Time bulk operations with many posts; compare before/after.

---

### 14. Media Page Full Directory Scan **[VERIFIED UNFIXED]**
**File:** `app/routes/admin/media.py:38-50`
**Severity:** Medium (Performance)
**Impact:** Every media page load scans entire upload directory

**Fix:**
Add file listing cache with invalidation on upload/delete:
```python
_MEDIA_CACHE = {"files": None, "timestamp": 0}
_MEDIA_CACHE_LOCK = threading.Lock()
_MEDIA_CACHE_TTL = 30  # seconds

def _get_cached_media_list(search: str = None):
    global _MEDIA_CACHE
    with _MEDIA_CACHE_LOCK:
        now = _time.monotonic()
        if (_MEDIA_CACHE["files"] is not None
            and (now - _MEDIA_CACHE["timestamp"]) < _MEDIA_CACHE_TTL):
            files = _MEDIA_CACHE["files"]
        else:
            files = _scan_media_directory()
            _MEDIA_CACHE["files"] = files
            _MEDIA_CACHE["timestamp"] = now

    if search:
        files = [(mtime, name, size) for mtime, name, size in files
                 if search.lower() in name.lower()]
    return files
```

Invalidate `_MEDIA_CACHE["files"] = None` in `delete_media()` and after successful upload.

**Verification:**
Load media page multiple times; second load should be faster.

---

### 15. Footer Cache Not Invalidated on Post Changes **[VERIFIED UNFIXED]**
**File:** `app/context_processors.py:65-104`
**Severity:** Medium (Correctness)
**Impact:** "Recent Posts" in footer shows stale data for up to 45 seconds after post changes

**Fix:**
Add `invalidate_footer_cache()` called from:
- `app/routes/admin/posts.py`: `new_post()` (after `db.session.commit()`)
- `app/routes/admin/posts.py`: `edit_post()` (after `db.session.commit()`)
- `app/routes/admin/posts.py`: `delete_post()` (after `db.session.commit()`)
- `app/routes/admin/posts.py`: `bulk_operations()` delete branch (after `db.session.commit()`)
- `app/routes/admin/posts.py`: `bulk_operations()` publish/unpublish branches (after `db.session.commit()`)

```python
# In context_processors.py:
def invalidate_footer_cache():
    with _FOOTER_CACHE_LOCK:
        _FOOTER_CACHE["data"] = None
```

**Verification:**
Create a post, check footer shows it immediately after creation.

---

### 16. SiteSettings Cache Not Invalidated on Save **[VERIFIED UNFIXED]**
**File:** `app/context_processors.py:30-62`
**Severity:** Medium (Correctness)
**Impact:** Theme changes (logo, colors, custom CSS) take up to 5 minutes to appear

**Fix:**
In `app/routes/admin/settings.py`, call `invalidate_settings_cache()` after successful settings save.

**Also:** Add invalidation for custom CSS changes if there's a separate preview/save flow.

---

## Wave 4: Code Quality Fixes (Can Run in Parallel)

### 17. Slug Regeneration Return Value Ignored **[VERIFIED UNFIXED]**
**File:** `app/routes/admin/posts.py:223-233`
**Severity:** High
**Impact:** When slug collision occurs, caller doesn't know slug was regenerated; subsequent operations may fail or use wrong slug

**Fix:**
Check the return value of `_commit_post_with_rollback()` and use the returned slug for any subsequent operations (e.g., redirect URL).

**Verification:** Create post with duplicate slug, verify correct redirect and flash message.

---

### 18. Error Recovery Block Duplicates Main Logic **[VERIFIED UNFIXED]**
**File:** `app/routes/admin/posts.py:320-351`
**Severity:** High (Maintainability)
**Impact:** 30+ lines of duplicated code; changes to post creation must be made in two places

**Fix:**
Extract shared logic into a helper function used by both the normal path and the IntegrityError handler.

**Verification:** Verify error recovery path produces identical results to normal path.

---

### 19. Regex Character Class Range Operator Bug **[VERIFIED UNFIXED]**
**File:** `app/search.py:90`
**Severity:** Medium
**Impact:** The `-` in `[()*:+\-"<>]` is interpreted as range from `+` (43) to `"` (34), potentially matching unintended characters

**Current:**
```python
term = re.sub(r'[()*:+\-"<>]', " ", term)
```

**Fix:**
```python
term = re.sub(r'[()*:+"<>\-]', " ", term)  # Hyphen at end
# or
term = re.sub(r'[()*:\+"<>"\-]', " ", term)  # Hyphen escaped
```

**Verification:** Run FTS search with hyphenated terms; verify no unintended character removal.

---

### 20. Missing Database Index **[VERIFIED UNFIXED]**
**File:** `app/models.py` (Post model)
**Severity:** Medium (Performance)
**Impact:** Slug lookups may be slow for large post tables

**Issue:**
AGENTS.md documents `ix_posts_published_slug` but it's not defined in the Post model.

**Fix:**
Add to Post's `__table_args__`:
```python
db.Index("ix_posts_published_slug", "published", "slug"),
```

**Verification:** Run `EXPLAIN QUERY PLAN` for slug-based lookups.

---

### 21. TOCTOU Race Condition in Admin Deletion **[VERIFIED UNFIXED]**
**File:** `app/routes/admin/users.py:104-108`
**Severity:** Medium (Security)
**Impact:** Between checking admin count and deleting, another admin could be deleted

**Fix:**
Use `SELECT ... FOR UPDATE` or wrap in a transaction with appropriate isolation level. Alternatively, catch the database constraint violation and handle it gracefully.

**Verification:** Create test with concurrent admin deletion requests.

---

### 22. `FakeSubscriber` Dataclass in Route File **[VERIFIED UNFIXED]**
**File:** `app/routes/admin/newsletter.py:17-24`
**Severity:** Medium (Code Organization)
**Impact:** Test utilities in production code; violates separation of concerns

**Fix:**
Move `FakeSubscriber` to `tests/conftest.py` or a dedicated test fixtures module.

**Verification:** Ensure newsletter test still passes after move.

---

### 23. Media File Truncation Off-by-One **[VERIFIED UNFIXED]**
**File:** `app/routes/admin/media.py:66`
**Severity:** Medium
**Impact:** May display one fewer file than intended per page

**Current:**
```python
if len(all_files) >= media_per_page:
    truncated = True
```

**Fix:**
```python
if len(all_files) > media_per_page:
    truncated = True
    all_files = all_files[:media_per_page]
```

**Verification:** Upload more than `media_per_page` files and verify correct pagination.

---

### 24. Newsletter Retry Logic Not Implemented **[VERIFIED UNFIXED]**
**Severity:** High (Operational Gap)
**Files:** `app/email.py`, `app/scheduler.py`, `config.toml`

**Issue:**
`NEWSLETTER_MAX_RETRY_ATTEMPTS` is defined but newsletter send does not implement retry logic.

**Fix:**
1. Add retry logic with configurable `NEWSLETTER_MAX_RETRY_ATTEMPTS` for transient SMTP errors
2. Implement exponential backoff between retries
3. Track `newsletter_attempts` on Post model (already exists but unused)
4. Only mark `newsletter_sent_at` if all subscribers succeed (or max retries reached)

**Verification:**
1. Send newsletter with simulated transient failure
2. Verify retry happens up to `max_retry_attempts`
3. Verify `newsletter_attempts` incremented correctly

---

## Wave 5: Multi-Admin & User Management (Can Run in Parallel)

### 25. Cannot Promote/Demote Users to Admin **[VERIFIED UNFIXED]**
**Severity:** High (User Management Gap)
**Files:** `app/routes/admin/users.py`, `app/templates/admin/users.html`

**Issue:**
Users can be created but cannot be promoted to admin or demoted from admin.

**Fix:**
1. Add `POST /admin/users/<user_id>/promote` route that sets `user.is_admin = True`
2. Add `POST /admin/users/<user_id>/demote` route that sets `user.is_admin = False`
3. Add guard: cannot demote if `user.id == current_user.id` (self-demotion)
4. Add guard: cannot demote if `admin_count <= 1` after operation
5. Add Promote/Demote button to user list with confirmation for demotion

**Verification:**
1. Create non-admin user, verify Promote button appears
2. Click Promote, verify user gains admin access
3. Attempt to demote self, verify rejection
4. Attempt to demote last admin, verify rejection

---

### 26. Cannot Transfer Admin Ownership **[VERIFIED UNFIXED]**
**Severity:** Medium (User Management Gap)
**Files:** `app/routes/admin/users.py`, `app/templates/admin/users.html`

**Fix:**
1. Add `POST /admin/users/<user_id>/make-owner` route
2. Add "Transfer Ownership" button visible only to current owner
3. Require password confirmation for ownership transfer

---

### 27. Add Type Hints to Model Methods **[VERIFIED UNFIXED]**
**Files:** `app/models.py`

**Methods lacking return type hints:**
- `Tag.generate_slug()` → should return `str`
- `Page.generate_slug()` → should return `str`
- `Post.generate_slug()` → should return `str`
- `Post.short_code()` → should return `str`

---

## Wave 6: UI/Template Fixes (Can Run in Parallel)

### 28. Login Page Loads Full Admin Base **[VERIFIED UNFIXED]**
**File:** `app/templates/admin/login.html:1`
**Severity:** Medium (UI Inconsistency)
**Impact:** Login page shows admin navigation that shouldn't be there.

**Fix:**
1. Create a minimal base template `admin/login_base.html` with just a login wrapper and no admin nav
2. Or simpler: make `login.html` extend the public `base.html`
3. Strip unnecessary elements (admin nav, shortcuts modal, confirm modal)

**Verification:**
1. Navigate to `/admin/login` when already logged in
2. Verify no admin navbar appears
3. Verify page has clean, centered login form

---

### 29. Templates Don't Verify Image File Existence **[VERIFIED UNFIXED]**
**Severity:** Medium (Robustness)
**Files:** `app/templates/` (multiple)

**Issue:**
Templates check `{% if post.image %}` which only verifies the filename exists in the database, not whether the file exists on disk.

**Affected Templates:**
- `index.html`, `tag.html`, `search.html`, `_post_content.html`, `post.html`, `email/newsletter.html`

**Fix:**
Refactor templates to use the `post_image_url` filter:
```html
{% set img = post|post_image_url %}
{% if img %}
    <img src="{{ url_for('static', filename='uploads/' + img) }}">
```

**Verification:**
1. Upload image for post
2. Delete image file from filesystem (keep DB record)
3. View post via various routes, verify no broken images rendered

---

### 30. Duplicate Badge and Status Badge Styles **[VERIFIED UNFIXED]**
**File:** `app/static/css/style.css:2407-2443`
**Severity:** Medium (Maintenance)
**Impact:** `.badge` and `.status-badge` have identical styles; confusion and maintenance burden

**Fix:**
1. Search codebase to determine which class name has more usage
2. Consolidate to single naming convention (use `.badge-*` naming)
3. Remove `.status-*` rules from CSS
4. Update `pages.html` to use `.badge-*` classes instead of `.status-*`

**Verification:**
After consolidation, verify all badges render correctly across admin pages.

---

### 31. Missing Visible Form Labels for Change Password **[VERIFIED UNFIXED]**
**File:** `app/templates/admin/users.html:31`
**Severity:** Low (Accessibility)
**Impact:** Password field lacks visible label.

**Fix:**
Add visible label (visually hidden for screen reader access):
```html
<label for="password-{{ user.id }}" class="visually-hidden">New password for {{ user.username }}</label>
<input type="password" id="password-{{ user.id }}" name="password" ...>
```

---

### 32. No Password Visibility Toggle **[VERIFIED UNFIXED]**
**File:** `app/templates/admin/users.html:14-15, 64`
**Severity:** Low (UX)

**Fix:**
Add show/hide toggle button next to password inputs.

---

### 33. Backup Restore Button Not Visually Dangerous **[VERIFIED UNFIXED]**
**File:** `app/templates/admin/backup.html:37`
**Severity:** Low (UX)
**Impact:** Restore button doesn't look destructive.

**Fix:**
Use `.btn-danger` for restore button:
```html
<button type="submit" class="btn btn-danger">Restore</button>
```

---

### 34. No Admin Breadcrumb Navigation **[VERIFIED UNFIXED]**
**File:** `app/templates/admin/base.html`, admin templates
**Severity:** Medium (Navigation)

**Fix:**
1. Add breadcrumb partial `admin/_breadcrumbs.html`
2. Add CSS for `.admin-breadcrumb`
3. Include breadcrumbs in admin templates

**Verification:**
Navigate through admin sections, verify breadcrumbs appear.

---

### 35. Breadcrumb Truncation Accessibility Issue **[VERIFIED UNFIXED]**
**File:** `app/static/css/style.css:926-932`
**Severity:** High (Accessibility)
**Impact:** `.breadcrumb-current` has `max-width: 200px` with ellipsis truncation.

**Fix:**
```css
.breadcrumb-current {
    max-width: 400px;  /* Allow more room for long titles */
}
```

**Verification:**
Create post with very long title, verify full title visible in breadcrumb.

---

### 36. Archive Grid Layout Breaks on Mobile **[VERIFIED UNFIXED]**
**File:** `app/static/css/style.css:513-520`
**Severity:** High (Layout)
**Impact:** Archive page grid doesn't adapt to mobile.

**Fix:**
Add mobile override:
```css
@media (max-width: 768px) {
    .archive-post {
        grid-template-columns: 1fr;
    }
}
```

---

### 37. Share Bar Cluttered on Mobile **[VERIFIED UNFIXED]**
**File:** `app/templates/_post_content.html:20-43`, `app/static/css/style.css`
**Severity:** Medium (UX)
**Impact:** 8 share buttons wrap on mobile, disrupting reading flow.

**Fix:**
Use CSS to hide less-used buttons on small screens:
```css
@media (max-width: 480px) {
    .share-btn-linkedin, .share-btn-hn, .share-btn-reddit, .share-btn-pinterest {
        display: none;
    }
}
```

---

### 38. Author Info Missing from Post Cards **[VERIFIED UNFIXED]**
**Files:** `app/templates/index.html`, `app/templates/tag.html`, `app/templates/search.html`
**Severity:** Medium (UX)

**Fix:**
Add author line to post cards in each template.

---

### 39. No Scheduled Post Indicator **[VERIFIED UNFIXED]**
**File:** `app/templates/admin/dashboard.html`
**Severity:** Medium (UX)
**Impact:** Scheduled posts look identical to drafts.

**Fix:**
Add "Scheduled" badge with datetime in admin dashboard.

---

## Wave 7: JavaScript & Dead Code Cleanup (Can Run in Parallel)

### 40. Missing Error Handling on Dynamic Imports **[VERIFIED UNFIXED]**
**File:** `app/static/js/main.js:2-22`
**Severity:** Medium (Robustness)
**Impact:** All 19 dynamic imports lack `.catch()` handlers.

**Fix:**
Wrap each import with error handling:
```javascript
const loadModule = (path, initFn) => {
    import(path).then(module => {
        if (initFn) initFn(module);
    }).catch(err => {
        console.error(`Failed to load module: ${path}`, err);
    });
};
```

---

### 41. Duplicate Focus Trap Logic in Shortcuts Module **[VERIFIED UNFIXED]**
**File:** `app/static/js/admin/shortcuts.js:92-126`
**Severity:** Low (Dead Code)

**Fix:**
Remove the duplicate focus trap from `shortcuts.js`. The `modal.js` version already handles the keyboard shortcuts modal.

---

### 42. Share Tracking Silently Swallows Errors **[VERIFIED UNFIXED]**
**File:** `app/static/js/public/share.js:57-70`
**Severity:** Low (Observability)
**Impact:** `.catch(() => {})` silently ignores all errors.

**Fix:**
```javascript
.catch(err => {
    console.warn('Share tracking failed:', err);
});
```

---

### 43. Unused CSS Variable `--text-dim-strong` **[VERIFIED UNFIXED]**
**File:** `app/static/css/style.css:77, 1383`
**Severity:** Low (Dead Code)

**Fix:**
Remove the `--text-dim-strong` variable from both `:root` and `[data-theme="light"]`.

---

### 44. Unused CSS Class `.post-card-snippet` **[VERIFIED UNFIXED]**
**File:** `app/static/css/style.css:468-474`
**Severity:** Low (Dead Code)

**Fix:**
Remove the `.post-card-snippet` CSS rules.

---

### 45. `_build_newsletter_message` Appears Unused **[VERIFIED UNFIXED]**
**File:** `app/email.py:88-111`
**Severity:** Low (Dead Code)

**Fix:**
Remove if truly unused, or refactor `send_newsletter()` to use it.

---

### 46. Related Posts Only Use First Tag **[VERIFIED UNFIXED]**
**File:** `app/templates/post.html:39`
**Severity:** Low (Content Quality)

**Fix:**
Use all tags for related posts query instead of just the first.

---

### 47. No Jinja Macros for Reusable Patterns **[VERIFIED UNFIXED]**
**Files:** `app/templates/` (multiple)
**Severity:** Low (Maintainability)

**Fix:**
Create `app/templates/macros.html` with reusable macros for pagination, badges, and field errors.

---

### 48. Email Templates Not Using Base **[VERIFIED UNFIXED]**
**Files:** `app/templates/email/newsletter.html`, `app/templates/email/confirm.html`
**Severity:** Low (Maintainability)

**Fix:**
Create `app/templates/email/base_email.html` and update newsletter/confirm to extend it.

---

## Wave 8: Minor Improvements (Can Run in Parallel)

### 49. SiteSettings Singleton Not Enforced **[VERIFIED UNFIXED]**
**File:** `app/models.py:218-229`
**Severity:** Low

**Fix Options:**
1. Add a check constraint at DB level
2. Use `INSERT OR IGNORE` and always access via `SiteSettings.query.get(1)`
3. Create a `SiteSettings.get_instance()` class method

---

### 50. Inconsistent Relationship Patterns **[VERIFIED UNFIXED]**
**File:** `app/models.py`
**Severity:** Low (Maintainability)
**Impact:** Mix of `backref` (string) and `back_populates` (explicit).

**Fix:**
Standardize on `back_populates` with explicit `lazy` parameters throughout.

---

### 51. Missing Type Hints on Model Methods **[VERIFIED UNFIXED]**
**File:** `app/models.py`
**Severity:** Low

*See Wave 4 item 27 for methods needing type hints.*

---

### 52. Referrer Index May Be Ineffective **[VERIFIED UNFIXED]**
**File:** `app/models.py:176`
**Severity:** Low (Performance)
**Impact:** Indexing 512-char VARCHAR is largely ineffective in SQLite.

**Fix Options:**
1. Remove the index if referrer analytics aren't used
2. Hash referrers to a fixed length for indexing
3. Normalize to domain-only and index that

---

### 53. SELECT Before DELETE on Session Expiry **[VERIFIED UNFIXED]**
**File:** `app/__init__.py:204-206`
**Severity:** Low (Performance)
**Impact:** One extra query when cleaning expired sessions.

**Fix:**
```python
db.session.execute(
    delete(AdminSession).where(AdminSession.session_id == sid)
)
```

---

### 54. Individual Loop Deletes for Expired Subscribers **[VERIFIED UNFIXED]**
**File:** `app/scheduler.py:179-181`
**Severity:** Low (Performance)
**Impact:** N ORM DELETE operations instead of 1 bulk DELETE.

**Fix:**
```python
if expired:
    db.session.execute(
        delete(Subscriber).where(Subscriber.id.in_([sub.id for sub in expired]))
    )
    db.session.commit()
```

---

### 55. File Read Twice on Upload Rejection **[VERIFIED UNFIXED]**
**File:** `app/routes/admin/helpers/images.py:37-44`
**Severity:** Low (I/O)

**Fix:**
Read header first, then seek to end for size:
```python
header = file.read(32)  # Read once
file.seek(0, 2)        # Then check size
size = file.tell()
file.seek(0)
```

---

### 56. Sequential File Deletes in Bulk Operations **[VERIFIED UNFIXED]**
**File:** `app/routes/admin/posts.py:504-505`
**Severity:** Low (Performance)

**Note:** This is fine for typical use; consider async only if needed.

---

### 57. Error Page Inconsistency **[VERIFIED UNFIXED]**
**File:** `app/templates/_error.html`, `app/templates/500.html`
**Severity:** Low (UI Inconsistency)

**Fix:**
Update 500.html to use the `_error.html` partial.

---

### 58. Health Endpoint Missing from AGENTS.md **[VERIFIED UNFIXED]**
**File:** `AGENTS.md`
**Severity:** Low (Documentation)

**Fix:**
Add documentation for `GET /health` endpoint.

---

### 59. Archive Page Not Documented **[VERIFIED UNFIXED]**
**File:** `AGENTS.md`
**Severity:** Low (Documentation)

**Fix:**
Add to AGENTS.md: `- **Archive Page:** `/archive` lists all published posts grouped by year`

---

### 60. Static Pages Feature Documentation Incomplete **[VERIFIED UNFIXED]**
**File:** `AGENTS.md`
**Severity:** Low (Documentation)

**Fix:**
Add: `- **Static Pages:** `/page/<slug>` renders custom pages`

---

### 61. N+1 Query Risk with Dynamic Relationships **[VERIFIED UNFIXED]**
**File:** `app/models.py:112,114-118`
**Severity:** Medium (Performance)

**Affected Relationships:**
- `Tag.posts` (line 112): `backref=db.backref("posts", lazy="dynamic")`
- `Post.page_views` (line 114-116): `lazy="dynamic"`
- `Post.share_events` (line 117-118): `lazy="dynamic")`

**Fix:**
Change `lazy="dynamic"` to `lazy="select"` or `lazy="selectin"` if not intentionally used with `.filter()` chaining.

---

### 62. `scalar()` Returns None on Empty Result **[VERIFIED UNFIXED]**
**File:** `app/scheduler.py:98`
**Severity:** Medium (Correctness)
**Impact:** Newsletter skips sending when no subscribers despite check.

**Fix:**
Use `scalar_one_or_none()` with explicit zero check:
```python
result = db.session.execute(...).scalar_one_or_none()
if not result:  # Catches both None and 0
    return
```

---

## Implementation Order Summary

| Wave | Items | Description | Parallelization |
|------|-------|-------------|-----------------|
| **Wave 1** | 1-5 | Critical bugs (Sequential) | Blocks all other waves |
| **Wave 2** | 6-9 | Security & Session Fixes | Can run in parallel after Wave 1 |
| **Wave 3** | 10-16 | Performance Improvements | Can run in parallel after Wave 1 |
| **Wave 4** | 17-24 | Code Quality Fixes | Can run in parallel after Wave 2/3 |
| **Wave 5** | 25-27 | Multi-Admin & User Management | Can run in parallel |
| **Wave 6** | 28-39 | UI/Template Fixes | Can run in parallel |
| **Wave 7** | 40-48 | JavaScript & Dead Code Cleanup | Can run in parallel |
| **Wave 8** | 49-62 | Minor Improvements | Can run in parallel |

---

## Additional Items (Not Scheduled)

Low priority items identified but not scheduled for implementation:

| Issue | Location | Description |
|-------|----------|-------------|
| Regex-based CSS sanitization | `app/utils.py:sanitize_css()` | Uses regex instead of proper CSS parser. Potential bypass with complex selectors. |
| Newsletter scheduler single-machine lock | `app/scheduler.py` | File-based locking only; multi-worker needs Redis. |
| FTS sync errors swallowed | `app/search.py:sync_fts()` | Errors don't prevent DB commit, leaving FTS out of sync. |
| No orphaned image cleanup | `app/routes/admin/media.py` | Images uploaded but never associated with a post are never cleaned up. |

---

## Related Documentation

- `AGENTS.md` — Project structure and patterns
- `DEPLOY.md` — Deployment guide
- `.opencode/skills/` — Specialized skills for security, performance, and feature documentation
