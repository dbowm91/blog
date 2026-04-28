# Consolidated Improvement Plans Summary (Batch 1)

**Date:** April 28, 2026  
**Source Plans:** plan2.md (Security), plan3.md (Performance), plan4.md (Code Quality), plan5.md (Tech Stack/Deployment)

---

## Overview

| Plan | Focus Area | Items | Priority Distribution | Est. Total Effort |
|------|-----------|-------|----------------------|-------------------|
| plan2.md | Security Improvements | 7 | 1 Critical, 2 High, 2 Medium, 2 Low | 4-5 hours |
| plan3.md | Performance Improvements | 10 | 3 High, 4 Medium, 2 Low | 4-6 hours |
| plan4.md | Code Quality | 10 | 1 High, 5 Medium, 4 Low | ~44-69 hours |
| plan5.md | Tech Stack/Deployment | 6 | 3 Critical, 3 Medium | ~50 minutes |

---

## PHASE 1: CRITICAL (Fix Immediately)

### 1.1 API Key Timing Attack Fix
**Plan:** plan2.md - Task 1  
**File:** `app/routes/api.py:32`  
**Effort:** 5 minutes  
**Severity:** HIGH - Allows full API key extraction via side-channel

**Problem:** Python `!=` operator uses short-circuit evaluation. Attackers can extract API key character-by-character by measuring response time differences.

**Fix:**
```python
import hmac
# Replace: if not provided or provided != API_KEY:
if not hmac.compare_digest(provided, API_KEY):
```

**Verification:** Code review test checking for `hmac.compare_digest` usage.

---

### 1.2 Granian Not Used in Docker Deployment
**Plan:** plan5.md - Issue 1  
**Files:** `requirements.txt`, `Dockerfile`  
**Effort:** 15 minutes  
**Severity:** HIGH - Documentation promotes Granian but Gunicorn is used

**Changes Required:**
1. Add `granian>=2.7.0,<3.0` to `requirements.txt`
2. Update `Dockerfile` line 12: Remove explicit `gunicorn` install
3. Update `Dockerfile` line 27: Replace gunicorn CMD with granian:
   ```dockerfile
   CMD ["granian", "--interface", "asgi", "--workers", "2", "--host", "0.0.0.0", "--port", "5000", "run:asgi_app"]
   ```

---

### 1.3 Docker-Compose Circular Dependency
**Plan:** plan5.md - Issue 2  
**File:** `docker-compose.yml:24-26, 41-43`  
**Effort:** 5 minutes  
**Severity:** HIGH - Services cannot start due to circular `depends_on`

**Problem:** `blog` depends on `nginx` waiting for healthy, and `nginx` depends on `blog` waiting for healthy → deadlock.

**Fix:** Remove `depends_on: nginx` from `blog` service. Keep `nginx` depends_on `blog`.

---

### 1.4 Health Endpoint Documentation Mismatch
**Plan:** plan5.md - Issue 3  
**Files:** `DEPLOY.md`, `docker-compose.yml`  
**Effort:** 15 minutes  
**Severity:** HIGH - Documentation shows incorrect JSON structure

**Current State (DEPLOY.md):**
```json
{"status": "ok", "database": "connected", ...}  // WRONG
```

**Actual Implementation:**
```json
{"status": "ok" | "degraded", "checks": {"database": "ok", "scheduler": "running", "search": "ok"}, "timestamp": "..."}
```

**Changes:**
1. Update `DEPLOY.md` lines 946-952 to match actual structure
2. Update docker-compose healthcheck to detect degraded status:
   ```yaml
   test: ["CMD", "bash", "-c", "curl -sf http://localhost:5000/health | grep -q '\"status\": \"ok\"'"]
   ```

---

## PHASE 2: HIGH PRIORITY

### 2.1 Backup Integrity Verification
**Plan:** plan2.md - Task 2  
**Files:** `app/backup_integrity.py` (NEW), `backup.py`, `app/routes/admin/backup.py`  
**Effort:** 2-3 hours  
**Severity:** MEDIUM-HIGH

**Implementation Steps:**
1. Create `app/backup_integrity.py` module with functions:
   - `calculate_sha256()` - Calculate file hash
   - `verify_sha256()` - Timing-safe hash verification
   - `write_checksum_file()` - Create `.sha256` sidecar file
   - `check_sqlite_integrity()` - Run `PRAGMA integrity_check`
   - `verify_backup_integrity()` - Comprehensive verification

2. Update `backup.py` - Generate checksum + run integrity check after backup creation

3. Update `app/routes/admin/backup.py` - Verify integrity before restore

**No new dependencies** - Uses Python standard library (hashlib, gzip, sqlite3)

---

### 2.2 Password Reset Token Hashing
**Plan:** plan2.md - Task 3  
**File:** `app/routes/admin/auth.py:140-142, 168-170`  
**Effort:** 30 minutes  
**Severity:** MEDIUM

**Changes:**
- In `forgot_password()`: Store `SHA-256(token)` instead of plaintext
- In `reset_password()`: Hash incoming token before lookup
- No migration needed - tokens expire after 1 hour

**Why SHA-256:** Reset tokens have 256 bits entropy; no key stretching needed.

---

### 2.3 Fix `yield_per()` Defeated by `.all()`
**Plan:** plan3.md - Item 1  
**File:** `app/scheduler.py:112`  
**Effort:** 5 minutes  
**Severity:** HIGH (Bug)

**Problem:** `yield_per(100)` followed by `.all()` loads all rows into memory.

**Fix:** Remove `yield_per()` since dataset is typically small:
```python
posts = list(
    db.session.execute(
        select(Post).filter(...).order_by(Post.published_at.desc())
    ).scalars()
)
```

---

### 2.4 Fix Empty `footer_tag_counts`
**Plan:** plan3.md - Item 2  
**File:** `app/context_processors.py:100`  
**Effort:** 10 minutes  
**Severity:** HIGH (Bug)

**Problem:** `footer_tag_counts` is always `{}` - import exists but function is never called.

**Fix:** Change line 88 from `{}` to `_get_tag_counts()`

**Optional:** Update `app/templates/base.html:109` to display tag counts.

---

### 2.5 Fix N+1 Query in Revisions Route
**Plan:** plan3.md - Item 3  
**File:** `app/routes/admin/posts.py:683-691`  
**Effort:** 10 minutes  
**Severity:** HIGH (N+1 Query)

**Fix:** Add `joinedload(PostRevision.author)` to query:
```python
from sqlalchemy.orm import joinedload
revisions = db.session.execute(
    select(PostRevision).filter(...).options(joinedload(PostRevision.author))
).scalars().all()
```

---

### 2.6 Fix SMTP Connection Handling
**Plan:** plan4.md - Task 1.1  
**File:** `app/email.py:24-43`  
**Effort:** 15 minutes  
**Severity:** HIGH

**Problem:** Uses `with smtplib.SMTP() as server:` pattern (AGENTS.md warns against this for newsletter batch).

**Fix:** Replace with manual `try/finally` pattern (matching newsletter code):
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

## PHASE 3: MEDIUM PRIORITY

### 3.1 Combine Redundant COUNT Queries
**Plan:** plan3.md - Item 4  
**File:** `app/routes/admin/helpers/dashboard.py:79-94`  
**Effort:** 20 minutes  

**Problem:** Four separate `SELECT COUNT(*)` queries.

**Fix:** Combine into single query using `scalar_subquery()`:
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

### 3.2 Fix Regex Recompilation in Loop
**Plan:** plan3.md - Item 5  
**File:** `app/search.py:306`  
**Effort:** 15 minutes  

**Problem:** `highlight_query()` called in loop, `re.compile()` runs N times.

**Fix:** Precompile regex once in `get_search_snippets()` and pass pattern:
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

### 3.3 Add Reverse Index on `post_tags.tag_id`
**Plan:** plan3.md - Item 6  
**File:** `app/models.py:265-270`  
**Effort:** 30 minutes + migration  

**Fix:** Add explicit index on `tag_id`:
```python
post_tags = db.Table(
    "post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("posts.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
    db.Index("ix_post_tags_tag_id", "tag_id"),
)
```

**Then run:** `flask db migrate -m "add index on post_tags.tag_id"` and `flask db upgrade`

---

### 3.4 Fix FTS5 Initialization
**Plan:** plan4.md - Task 2.1  
**File:** `app/search.py:52-80`  
**Effort:** 30 minutes  

**Problem:** `init_fts()` uses DROP TABLE → CREATE (not atomic).

**Fix:** Use `CREATE VIRTUAL TABLE IF NOT EXISTS` and proper error handling.

---

### 3.5 Move THEME_PRESETS to Dedicated Module
**Plan:** plan4.md - Task 2.2  
**Files:** `app/models.py`, `app/themes.py` (NEW), `app/context_processors.py`, `app/routes/admin/settings.py`  
**Effort:** 1-2 hours  

**Steps:**
1. Create `app/themes.py` with `THEME_PRESETS` dictionary
2. Update imports in `context_processors.py` and `settings.py`
3. Remove from `models.py`

---

### 3.6 Add Flask-Caching for Scalability
**Plan:** plan4.md - Task 2.3  
**Files:** `requirements.txt`, `app/extensions.py`, `app/__init__.py`, `app/cache.py`, `app/context_processors.py`, `config.toml`  
**Effort:** 2-3 hours  

**Steps:**
1. Add `Flask-Caching>=2.0.0` and `cachelib>=0.12.0` to requirements
2. Initialize cache in extensions and app factory
3. Replace custom locking with cache primitives
4. Add config: `[cache] type = "simple"`

---

### 3.7 Create Centralized Error Handlers
**Plan:** plan4.md - Task 2.4  
**Files:** `app/error_handlers.py` (NEW), multiple route files  
**Effort:** 2-3 hours  

**Steps:**
1. Create `app/error_handlers.py` with `db_transaction()` and `safe_commit()` helpers
2. Refactor simple try/except blocks
3. Keep complex IntegrityError handling inline

---

### 3.8 Minor Documentation/Configuration Fixes

| Issue | Plan | Files | Effort |
|-------|------|-------|--------|
| README logout route (GET→POST) | plan5.md | `README.md` | 5 min |
| Missing routes in README | plan5.md | `README.md` | 15 min |
| Backup service entrypoint | plan5.md | `docker-compose.yml` | 5 min |

---

## PHASE 4: OPTIONAL / LOW PRIORITY

### Task Group A: Performance Optimizations (plan3.md)

| Item | File | Effort | Notes |
|------|------|--------|-------|
| Simplify `get_indexed_terms()` | `app/search.py:201-219` | 10 min | Query posts_fts only, include all columns |
| Add Asset Minification | `scripts/build_assets.py` (NEW) | 1-2h | Use csscompressor, rjsmin |
| Evaluate time.sleep() alternatives | `app/routes/public.py:620,660`, `app/routes/admin/auth.py:54,152` | 1-2h | Option B: CPU burn instead of sleep |

---

### Task Group B: Code Quality Improvements (plan4.md)

| Task | Files | Effort | Notes |
|------|-------|--------|-------|
| Extract CSP Headers to Helper | `app/__init__.py` | 1h | Extract `_build_csp_policy()` |
| Consider tinycss2 for CSS Sanitization | `app/utils.py` | 3-4h | Current regex is "good enough" |
| Consider Lazy-Loading Config | `app/config.py` | 2-3h | Use PEP 562 `__getattr__` |
| Fix `__all__` Ordering | `app/utils.py` | 0 | No action needed |

---

### Task Group C: Refactoring (plan4.md)

| Task | Files | Effort | Notes |
|------|-------|--------|-------|
| Refactor Large Files | `app/routes/public.py`, `app/routes/admin/posts.py`, `app/__init__.py` | 18-26h | Split into packages; 3 separate developers possible |

---

## Implementation Priority Order

Recommended execution sequence based on impact/effort ratio:

1. **Immediate (Phase 1 Critical):**
   - API Key Timing Attack Fix (5 min) - security
   - Docker Compose Circular Dependency (5 min) - unblocks deployment
   - Granian in Docker (15 min) - performance
   - Health Endpoint Docs (15 min) - accuracy

2. **This Week (Phase 2 High):**
   - SMTP Connection Handling (15 min) - consistency
   - Backup Integrity Verification (2-3h) - data safety
   - Password Reset Token Hashing (30 min) - security
   - Fix `yield_per().all()` (5 min) - bug fix
   - Fix empty `footer_tag_counts` (10 min) - bug fix
   - Fix N+1 in Revisions (10 min) - performance

3. **Next Sprint (Phase 3 Medium):**
   - Combine COUNT queries (20 min) - performance
   - Fix regex recompilation (15 min) - performance
   - Add post_tags.tag_id index (30 min) - database optimization
   - Fix FTS5 initialization (30 min) - correctness
   - Move THEME_PRESETS (1-2h) - code organization
   - Add Flask-Caching (2-3h) - scalability
   - Create Error Handlers (2-3h) - code quality
   - Documentation fixes (25 min) - accuracy

4. **Future / Optional (Phase 4 Low):**
   - Asset minification (1-2h)
   - time.sleep() alternatives (1-2h)
   - CSP helper extraction (1h)
   - tinycss2 consideration (3-4h)
   - Lazy config loading (2-3h)
   - Large file refactoring (18-26h)

---

## Dependencies & Notes

- **No new external dependencies** except: `Flask-Caching>=2.0.0`, `cachelib>=0.12.0` (for task 3.6), and `granian>=2.7.0,<3.0` (for task 1.2)
- **Database migrations** required for: post_tags.tag_id index (task 3.3)
- **Testing after each task:** `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v`
- **AGENTS.md patterns to follow:** Use `db.paginate()`, `db.session.get()`, SQLAlchemy 2.0 patterns

---

## Files Summary

| File | Tasks |
|------|-------|
| `app/routes/api.py` | 1.1, 2.5 (optional) |
| `app/routes/admin/auth.py` | 2.2, 2.6 |
| `app/email.py` | 2.6 |
| `app/scheduler.py` | 2.3 |
| `app/context_processors.py` | 2.4 |
| `app/routes/admin/posts.py` | 2.5 |
| `app/routes/admin/helpers/dashboard.py` | 3.1 |
| `app/search.py` | 3.2, 3.4, 3.A |
| `app/models.py` | 3.3 |
| `app/routes/admin/backup.py` | 2.1 |
| `backup.py` | 2.1 |
| `app/backup_integrity.py` | 2.1 (NEW) |
| `app/error_handlers.py` | 3.7 (NEW) |
| `app/themes.py` | 3.5 (NEW) |
| `requirements.txt` | 1.2, 3.6 |
| `Dockerfile` | 1.2 |
| `docker-compose.yml` | 1.3, 1.4, 3.8 |
| `DEPLOY.md` | 1.4 |
| `README.md` | 3.8 |
| `scripts/build_assets.py` | 3.A (NEW) |

---

*Generated from Batch 1 consolidation: plan2.md, plan3.md, plan4.md, plan5.md*
