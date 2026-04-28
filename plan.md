# Improvement Plan

**Date:** 2026-04-28
**Status:** Active - Work not yet started
**Source:** Consolidated from plans/plan2.md through plan10.md

---

## Verification Status

- 487 tests pass (1 known flaky media upload test)
- All items below are unverified unless marked as already present in codebase

---

## Wave Organization

Items are organized into waves that can be executed in parallel within each wave. Waves must be completed sequentially (Wave 1 before Wave 2, etc.) unless marked as independently parallel.

---

## Wave 1: Critical Security & Deployment Fixes

*Execute these first - they address security vulnerabilities and unblock deployment*

### 1.1 API Key Timing Attack Fix
**Priority:** CRITICAL
**Files:** `app/routes/api.py`
**Effort:** 5 minutes

**Problem:** Line 32 uses `provided != API_KEY` which is vulnerable to timing attack. Python's `!=` short-circuits on first mismatched character.

**Fix:**
```python
# Line 32: Replace:
if not provided or provided != API_KEY:
# With:
import hmac
if not hmac.compare_digest(provided, API_KEY):
```

**Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k "api"`

---

### 1.2 Granian Not Used in Docker Deployment
**Priority:** CRITICAL
**Files:** `requirements.txt`, `Dockerfile`
**Effort:** 15 minutes

**Changes:**
1. Add `granian>=2.7.0,<3.0` to `requirements.txt`
2. Update `Dockerfile` line 12: Remove explicit `gunicorn` install
3. Update `Dockerfile` line 27: Replace gunicorn CMD with granian:
   ```dockerfile
   CMD ["granian", "--interface", "asgi", "--workers", "2", "--host", "0.0.0.0", "--port", "5000", "run:asgi_app"]
   ```

---

### 1.3 Docker-Compose Circular Dependency
**Priority:** CRITICAL
**Files:** `docker-compose.yml`
**Effort:** 5 minutes

**Problem:** `blog` depends on `nginx` waiting for healthy, and `nginx` depends on `blog` → deadlock.

**Fix:** Remove `depends_on: nginx` from `blog` service. Keep `nginx` depends_on `blog`.

---

### 1.4 Health Endpoint Documentation Mismatch
**Priority:** CRITICAL
**Files:** `DEPLOY.md`, `docker-compose.yml`
**Effort:** 15 minutes

**Problem:** DEPLOY.md shows incorrect JSON structure for `/health` endpoint.

**Current (incorrect) in DEPLOY.md:**
```json
{"status": "ok", "database": "connected", ...}
```

**Actual structure:**
```json
{"status": "ok" | "degraded", "checks": {"database": "ok", "scheduler": "running", "search": "ok"}, "timestamp": "..."}
```

**Changes:**
1. Update `DEPLOY.md` around lines 946-952 to match actual structure
2. Update docker-compose healthcheck to detect degraded status:
   ```yaml
   test: ["CMD", "bash", "-c", "curl -sf http://localhost:5000/health | grep -q '\"status\": \"ok\"'"]
   ```

---

## Wave 2: High Priority Bug Fixes

*Can be executed in parallel within this wave*

### 2.1 Fix Empty `footer_tag_counts`
**Priority:** HIGH
**Files:** `app/context_processors.py`
**Effort:** 10 minutes

**Problem:** Line 100 sets `footer_tag_counts: {}` instead of calling `_get_tag_counts()`.

**Fix:** Change line 100 from `{}` to `_get_tag_counts()`

**Optional:** Update `app/templates/base.html` to display tag counts with:
```jinja2
{{ tag.name }}{% if footer_tag_counts.get(tag.id) %} ({{ footer_tag_counts.get(tag.id) }}){% endif %}
```

---

### 2.2 Fix N+1 Query in Revisions Route
**Priority:** HIGH
**Files:** `app/routes/admin/posts.py`
**Effort:** 10 minutes

**Note:** Code already has `joinedload(PostRevision.author)` at line 688. Verify this is working correctly by running:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k "revision"
```

If tests pass, this item is complete.

---

### 2.3 Fix SMTP Connection Handling
**Priority:** HIGH
**Files:** `app/email.py`
**Effort:** 15 minutes

**Problem:** Line 36 uses `with smtplib.SMTP() as server:` pattern. AGENTS.md warns this is problematic because reassigning `server` inside the block creates a new local variable while `__exit__` still calls the original.

**Fix:** Replace with manual `try/finally` pattern:
```python
server = None
try:
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT)
    server.ehlo()
    context = ssl.create_default_context()
    server.starttls(context=context)
    server.ehlo()
    if SMTP_USER:
        server.login(SMTP_USER, SMTP_PASSWORD)
    server.sendmail(FROM_ADDRESS, to, msg.as_string())
finally:
    if server:
        try:
            server.quit()
        except OSError:
            pass
```

---

### 2.4 Password Reset Token Hashing
**Priority:** HIGH
**Files:** `app/routes/admin/auth.py`
**Effort:** 30 minutes

**Problem:** Reset tokens stored in plaintext in database.

**Changes:**
- In `forgot_password()`: Store `SHA-256(token)` instead of plaintext
- In `reset_password()`: Hash incoming token before lookup

**Note:** No migration needed - tokens expire after 1 hour.

---

### 2.5 Backup Integrity Verification
**Priority:** HIGH
**Files:** `app/backup_integrity.py` (NEW), `backup.py`, `app/routes/admin/backup.py`
**Effort:** 2-3 hours

**Implementation:**
1. Create `app/backup_integrity.py` with:
   - `calculate_sha256()` - Calculate file hash
   - `verify_sha256()` - Timing-safe hash verification
   - `write_checksum_file()` - Create `.sha256` sidecar file
   - `check_sqlite_integrity()` - Run `PRAGMA integrity_check`
   - `verify_backup_integrity()` - Comprehensive verification

2. Update `backup.py` - Generate checksum + run integrity check after backup

3. Update `app/routes/admin/backup.py` - Verify integrity before restore

**No new dependencies** - Uses Python standard library (hashlib, gzip, sqlite3)

---

## Wave 3: Syndication & Feed Improvements

*Can be executed in parallel within this wave*

### 3.1 JSON Feed Implementation
**Priority:** HIGH
**Files:** `app/routes/rss.py`, `app/templates/base.html`
**Effort:** 2 hours

**Implementation:**
- Add `/feed.json` endpoint implementing JSON Feed 1.1 spec
- Item fields: `id` (URL), `url`, `title`, `content_html`, `summary`, `image`, `date_published`, `tags`, `attachments`
- Add autodiscovery link in `base.html`

---

### 3.2 RSS Feed Enhancements
**Priority:** HIGH
**Files:** `app/routes/rss.py`
**Effort:** 1 hour

**Add to RSS 2.0:**
- `content:encoded` with CDATA wrapping
- Author info (`dc:creator`)
- Categories/tags
- Image enclosures

---

### 3.3 Conditional GET Support
**Priority:** HIGH
**Files:** `app/routes/rss.py`
**Effort:** 1 hour

**Implementation:**
- Use `func.max(Post.updated_at)` for strong ETag
- Return `304 Not Modified` when If-Modified-Since/ETag matches

---

### 3.4 Cache Headers for Feeds
**Priority:** HIGH
**Files:** `app/routes/rss.py`
**Effort:** 30 minutes

**Add headers:**
```
Cache-Control: public, max-age=86400, s-maxage=604800, stale-while-revalidate=3600
Last-Modified: <timestamp>
ETag: <hash>
```

---

### 3.5 Atom Feed (Optional)
**Priority:** MEDIUM
**Effort:** 1 hour

---

### 3.6 Tag-Specific RSS Feeds (Optional)
**Priority:** MEDIUM
**Effort:** 1 hour
**Depends on:** 3.1-3.4 complete

---

## Wave 4: Frontend Usability

*Can be executed in parallel within this wave (except H1 which depends on FTS5 prefix)*

### 4.1 Search Experience Enhancements
**Priority:** HIGH
**Files:** `app/search.py`, `app/routes/public.py`, `app/static/js/public/search.js` (NEW)
**Effort:** 2 hours

**Requires FTS5 prefix index first (see Wave 5 Item 5.4)**

**Implementation:**
- Add FTS5 prefix index: `prefix=2 3 4` to `posts_fts` virtual table
- New endpoint `/api/search/suggestions` returns JSON array of matching post titles
- Frontend autocomplete with recent searches via localStorage

---

### 4.2 Client-Side Form Validation
**Priority:** HIGH
**Files:** `app/static/js/lib/formageddon.js` (NEW), forms
**Effort:** 1 hour

**Implementation:**
- Self-host `formageddon` library (4.2KB)
- Add HTML5 validation attributes
- Integrate with `showToast()` for error display

---

### 4.3 Editor Preview Latency Reduction
**Priority:** HIGH
**Files:** `app/static/js/lib/minigfm.min.js` (NEW), `app/static/js/admin/editor.js`
**Effort:** 1 hour

**Implementation:**
- Self-host MiniGFM (~3KB) for client-side markdown parsing
- Reduces debounce from 300ms to 150ms

---

### 4.4 Bulk Operation Feedback Enhancement
**Priority:** HIGH
**Files:** `app/static/js/admin/bulk.js`
**Effort:** 30 minutes

**Implementation:**
- Action-specific overlay text: "Publishing 3 post(s)..."
- Progress indication

---

### 4.5 Public Toast Notifications
**Priority:** MEDIUM
**Files:** `app/static/js/public/share.js`
**Effort:** 15 minutes

**Change:** Add `showToast()` call after successful share

---

### 4.6 SVG Icon Accessibility
**Priority:** MEDIUM
**Files:** Multiple templates
**Effort:** 30 minutes

**Changes:**
```html
<svg aria-hidden="true" role="img" aria-label="Description">
```

---

### 4.7 Color Contrast Fixes
**Priority:** MEDIUM
**Files:** `app/static/css/style.css`
**Effort:** 15 minutes

**Changes:**
- `--border` darken to `#b0b8c2`
- Badge alpha 0.15 → 0.25

---

### 4.8 Keyboard Shortcut Discoverability
**Priority:** MEDIUM
**Files:** Templates, `app/static/js/shared/toast.js`
**Effort:** 30 minutes

**Implementation:**
- Add `title` attribute to shortcut elements
- First-visit toast hint

---

### 4.9 Low Priority Frontend Items
**Priority:** LOW
**Effort:** ~2 hours total

| Item | Files | Effort |
|------|-------|--------|
| Remove stat card hover effects | `style.css` | 10 min |
| Reading progress bar toggle | `reading-progress-toggle.js` (NEW) | 30 min |
| Flash message flicker fix | `style.css` | 10 min |
| Mobile share button "More" menu | `share.js` | 45 min |

---

## Wave 5: Admin Panel Usability

*Can be executed in parallel within this wave*

### 5.1 Pages Link in Admin Navigation
**Priority:** HIGH
**Files:** `app/templates/admin/base.html`
**Effort:** 5 minutes

**Change:** Add Pages link to "More" dropdown after Tags using `url_for('admin.pages_list')`

---

### 5.2 Restore Button Distinct Styling
**Priority:** HIGH
**Files:** `app/templates/admin/backup.html`, `style.css`
**Effort:** 10 minutes

**Change:** Add `.btn-restore` class with red background, white text, warning icon

---

### 5.3 Active State Highlighting for Nested Nav
**Priority:** MEDIUM
**Files:** `app/templates/admin/base.html`
**Effort:** 15 minutes

**Change:** Use `request.endpoint.startswith('admin.settings')` for nested routes

---

### 5.4 Confirm Modal Replacement
**Priority:** MEDIUM
**Files:** `app/static/js/shared/modal.js`
**Effort:** 1 hour

**Implementation:**
- Replace `confirm()` with `showConfirmModal()` promise-based
- Store `previousActiveElement` for focus restoration
- Add `aria-describedby` for dynamic labels

---

### 5.5 Focus Trapping for Modals
**Priority:** MEDIUM
**Files:** `app/static/js/shared/modal.js`
**Effort:** 45 minutes
**Depends on:** 5.4

**Implementation:**
- Use focusableSelectors list
- Tab/Shift+Tab cycling within modal
- Escape closes modal

---

### 5.6 Users Page Refactor
**Priority:** MEDIUM
**Files:** `app/templates/admin/users.html`
**Effort:** 1 hour

**Change:** Use modal-based actions instead of inline forms

---

### 5.7 Mobile Editor Preview Toggle Bug
**Priority:** MEDIUM
**Files:** `app/static/js/admin/editor.js`, `style.css`
**Effort:** 15 minutes

**Problem:** Class name mismatch between JS and CSS

---

### 5.8 Bulk Action Loading State
**Priority:** MEDIUM
**Files:** `app/static/js/admin/bulk.js`
**Effort:** 30 minutes

**Implementation:**
- Disable buttons during processing
- Set "Processing..." text
- 30s timeout handling
- Error handling

---

### 5.9 Low Priority Admin Items
**Priority:** LOW
**Effort:** ~45 min total

| Item | Files | Effort |
|------|-------|--------|
| Dropdown grouping | base.html | 15 min |
| Tag rename UX | tags.html | 20 min |
| Dead CSS removal | style.css | 10 min |

---

## Wave 6: Code Quality & Testing

*Can be executed in parallel within this wave*

### 6.1 Missing Admin Tests
**Priority:** HIGH
**Files:** `tests/` (new files)
**Effort:** 5-7 hours

**New test files needed:**
- `tests/test_pages.py` - Static Pages CRUD
- `tests/test_settings.py` - Site Settings/Theme
- `tests/test_revisions.py` - Post Revisions
- `tests/test_sessions.py` - Session Management
- `tests/test_scheduler.py` - Scheduler Status

**Add to existing:**
- `tests/test_auth.py` - Password Reset Flow

---

### 6.2 Session Fixation Prevention Test
**Priority:** HIGH
**Files:** `tests/test_auth.py`
**Effort:** 30 minutes

**Verification:** Use `client.session_transaction()` to verify `session.clear()` before `login_user()`

---

### 6.3 Fix Flaky Media Upload Test
**Priority:** MEDIUM
**Files:** `tests/test_media.py`
**Effort:** 30 minutes

**Change:** Replace `time.sleep(0.5)` with `expect(page.locator()).to_be_visible(timeout=5000)`

---

### 6.4 pytest-cov Configuration
**Priority:** MEDIUM
**Files:** `pytest.ini`
**Effort:** 15 minutes

**Add to `addopts`:**
```
--cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=75
```

---

### 6.5 Consolidate Duplicate Fixtures
**Priority:** MEDIUM
**Files:** `tests/conftest.py`
**Effort:** 1 hour

---

## Wave 7: Database & Search Optimizations

*Must be executed sequentially*

### 7.1 Combine Redundant COUNT Queries
**Priority:** MEDIUM
**Files:** `app/routes/admin/helpers/dashboard.py`
**Effort:** 20 minutes

**Problem:** Four separate `SELECT COUNT(*)` queries (lines 79-94).

**Fix:** Combine using `scalar_subquery()`:
```python
stmt = select(
    select(func.count(PageView.id)).scalar_subquery().label('total_views'),
    select(func.count(Post.id)).where(Post.published == True).scalar_subquery().label('total_posts'),
    select(func.count(ShareEvent.id)).scalar_subquery().label('total_shares'),
    select(func.count(Subscriber.id)).where(Subscriber.confirmed == True).scalar_subquery().label('total_subscribers')
)
result = db.session.execute(stmt).one()
```

---

### 7.2 Fix Regex Recompilation in Loop
**Priority:** MEDIUM
**Files:** `app/search.py`
**Effort:** 15 minutes

**Problem:** `highlight_query()` recompiles regex on each call.

**Fix:** Precompile in `get_search_snippets()` and pass pattern:
```python
def get_search_snippets(posts: list, query: str) -> dict[int, str]:
    pattern = re.compile(re.escape(query), re.IGNORECASE) if query else None
    for post in posts:
        snippet_text = post.summary if post.summary else post.body
        raw_snippet = extract_snippet(snippet_text, query)
        snippets[post.id] = highlight_query(raw_snippet, pattern=pattern)
    return snippets
```

---

### 7.3 Add post_tags.tag_id Index
**Priority:** MEDIUM
**Files:** `app/models.py`
**Effort:** 30 minutes + migration

**Fix:** Add explicit index:
```python
post_tags = db.Table(
    "post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("posts.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
    db.Index("ix_post_tags_tag_id", "tag_id"),
)
```

**Run:**
```bash
flask db migrate -m "add index on post_tags.tag_id"
flask db upgrade
```

---

### 7.4 Fix FTS5 Initialization
**Priority:** MEDIUM
**Files:** `app/search.py`
**Effort:** 30 minutes

**Problem:** `init_fts()` uses DROP TABLE → CREATE (not atomic).

**Fix:** Use `CREATE VIRTUAL TABLE IF NOT EXISTS` and proper error handling.

---

### 7.5 Add FTS5 Prefix Index
**Priority:** MEDIUM
**Files:** `app/search.py`
**Effort:** 30 minutes

**Change:** Add `prefix=2 3 4` to posts_fts virtual table creation.

---

## Wave 8: Code Organization

*Can be executed in parallel within this wave*

### 8.1 Move THEME_PRESETS to Dedicated Module
**Priority:** MEDIUM
**Files:** `app/themes.py` (NEW), `app/models.py`, `app/context_processors.py`, `app/routes/admin/settings.py`
**Effort:** 1-2 hours

**Steps:**
1. Create `app/themes.py` with `THEME_PRESETS` dictionary (92 lines)
2. Update imports in `context_processors.py` and `settings.py`
3. Remove from `models.py`

---

### 8.2 Add Flask-Caching for Scalability
**Priority:** MEDIUM
**Files:** `requirements.txt`, `app/extensions.py`, `app/__init__.py`, `app/cache.py`, `config.toml`
**Effort:** 2-3 hours

**Steps:**
1. Add `Flask-Caching>=2.0.0` and `cachelib>=0.12.0` to requirements
2. Initialize cache in extensions and app factory
3. Replace custom locking with cache primitives
4. Add config: `[cache] type = "simple"`

---

### 8.3 Create Centralized Error Handlers
**Priority:** MEDIUM
**Files:** `app/error_handlers.py` (NEW), multiple route files
**Effort:** 2-3 hours

**Steps:**
1. Create `app/error_handlers.py` with `db_transaction()` and `safe_commit()` helpers
2. Refactor simple try/except blocks
3. Keep complex IntegrityError handling inline

---

### 8.4 Split public.py into Package
**Priority:** LOW
**Files:** `app/routes/public/` (NEW package)
**Effort:** 4-5 hours

**Structure:**
```
app/routes/public/
    __init__.py
    blog.py      # post, tag, archive routes
    search.py    # search routes
    subscribe.py # subscription routes
    share.py     # share routes
    sitemap.py   # sitemap
    health.py    # health check
    helpers.py   # shared helpers
```

---

## Wave 9: PostgreSQL Migration Preparation

*Can be executed in parallel with other waves (future-ready)*

### 9.1 Alembic SQLite Batch Mode
**Priority:** LOW
**Files:** `migrations/env.py`
**Effort:** 1 hour

**Add:** `render_as_batch=True` for SQLite compatibility

---

### 9.2 Database Dialect Detection Utility
**Priority:** LOW
**Files:** `app/utils.py`
**Effort:** 1 hour

**Add:** `get_db_dialect()` function

---

### 9.3 Health Check PostgreSQL Compatibility
**Priority:** LOW
**Files:** `app/routes/public.py`
**Effort:** 1 hour

**Change:** Replace `sqlite_master` query with dialect-agnostic approach

---

### 9.4 PostgreSQL Search Module
**Priority:** LOW
**Files:** `app/search_postgres.py` (NEW)
**Effort:** 3-4 hours

---

## Wave 10: Documentation

*Can be executed in parallel with other waves*

### 10.1 README.md Restructuring
**Priority:** HIGH
**Files:** `README.md`
**Effort:** 3-4 hours

**New Structure:**
1. Quick Start (keep existing lines 21-38)
2. How to Use DevLog (new) - For Readers and Admins
3. Features (With Context) - feature lists with usage context
4. Configuration - env vars + config.toml options
5. REST API - endpoints + curl examples
6. CLI Commands - table with examples
7. Routes - public + admin tables (30+ routes)
8. Installation (keep existing lines 19-65)
9. Project Structure (keep existing lines 162-208)

**Do NOT modify:** DEPLOY.md, docs/openapi.yaml

---

### 10.2 AGENTS.md Updates
**Priority:** LOW
**Files:** `AGENTS.md`
**Effort:** 30 minutes

**Changes:**
- Add note at top clarifying file purpose
- Add "Features Agents Should Know About" section
- Add cross-references to README.md

---

## Items to Skip

The following items were considered but should be skipped:

| Item | Reason |
|------|--------|
| WebSub/PubSubHubbub | Low adoption |
| Ping Services | Obsolete protocol |
| Scheduler health check enhancement | Current approach sufficient |
| Storage abstraction layer | Local storage optimal at current scale |
| Rate limiting | Reverse proxy approach correct |
| `time.sleep()` alternatives | Low risk for blog traffic |
| tinycss2 for CSS sanitization | Current regex is "good enough" |
| Large file refactoring (18-26h) | Too expensive for benefit |

---

## Files Summary by Wave

| File | Wave(s) | Items |
|------|---------|-------|
| `app/routes/api.py` | 1 | 1.1 |
| `app/email.py` | 2 | 2.3 |
| `app/routes/admin/auth.py` | 2 | 2.4 |
| `app/context_processors.py` | 2, 8 | 2.1, 8.1 |
| `app/routes/admin/backup.py` | 2, 5 | 2.5, 5.2 |
| `app/backup_integrity.py` | 2 | 2.5 (NEW) |
| `requirements.txt` | 1, 8 | 1.2, 8.2 |
| `Dockerfile` | 1 | 1.2 |
| `docker-compose.yml` | 1 | 1.3, 1.4 |
| `DEPLOY.md` | 1 | 1.4 |
| `app/routes/rss.py` | 3 | 3.1-3.6 |
| `app/routes/public.py` | 4, 5, 9 | 4.1, 5.7, 9.3 |
| `app/search.py` | 4, 5, 7 | 4.1, 5.4, 7.2, 7.4, 7.5 |
| `app/routes/admin/posts.py` | 2 | 2.2 |
| `app/routes/admin/helpers/dashboard.py` | 7 | 7.1 |
| `app/models.py` | 7, 8 | 7.3, 8.1 |
| `app/themes.py` | 8 | 8.1 (NEW) |
| `app/error_handlers.py` | 8 | 8.3 (NEW) |
| `app/extensions.py` | 8 | 8.2 |
| `migrations/env.py` | 9 | 9.1 |
| `app/static/js/public/search.js` | 4 | 4.1 (NEW) |
| `app/static/js/lib/formageddon.js` | 4 | 4.2 (NEW) |
| `app/static/js/lib/minigfm.min.js` | 4 | 4.3 (NEW) |
| `app/static/js/admin/bulk.js` | 4, 5 | 4.4, 5.8 |
| `app/static/js/shared/modal.js` | 5 | 5.4, 5.5 |
| `app/static/css/style.css` | 4, 5 | 4.7, 4.9, 5.9 |
| `app/templates/admin/base.html` | 5 | 5.1, 5.3 |
| `tests/test_pages.py` | 6 | 6.1 (NEW) |
| `tests/test_settings.py` | 6 | 6.1 (NEW) |
| `tests/test_revisions.py` | 6 | 6.1 (NEW) |
| `tests/test_sessions.py` | 6 | 6.1 (NEW) |
| `tests/test_scheduler.py` | 6 | 6.1 (NEW) |
| `pytest.ini` | 6 | 6.4 |
| `README.md` | 10 | 10.1 |
| `AGENTS.md` | 10 | 10.2 |

---

## Dependencies Summary

**New Dependencies:**
- `granian>=2.7.0,<3.0` (Wave 1)
- `Flask-Caching>=2.0.0` (Wave 8)
- `cachelib>=0.12.0` (Wave 8)

**Migrations Required:**
- Wave 7: `flask db migrate -m "add index on post_tags.tag_id"`

**Verification Command:**
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

---

## End of Plan
