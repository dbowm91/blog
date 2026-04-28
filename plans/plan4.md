# Code Quality Improvement Plan

**Date**: 2026-04-28  
**Status**: Planning phase - implementation not started  
**Investigation**: Deep dive by 10 subagents completed

---

## Executive Summary

Comprehensive code quality review identified 10 issues across the codebase. This plan prioritizes by urgency and provides detailed implementation steps.

**Key Findings**:
- 1 HIGH priority item (SMTP inconsistency with documented practices)
- 5 MEDIUM priority items (refactoring, caching, duplication)
- 4 LOW priority items (cosmetic, optional hardening)

---

## Phase 1: Critical Fixes (HIGH Priority)

### Task 1.1: Fix SMTP Connection Handling
**File**: `app/email.py` (lines 24-43)  
**Priority**: HIGH | **Effort**: 15 min | **Risk**: Low

**Problem**: 
- `_send_email()` uses `with smtplib.SMTP() as server:` pattern
- AGENTS.md explicitly warns: *"Do not use `with smtplib.SMTP() as server:` for newsletter batch"*
- Newsletter code correctly uses manual `try/finally`
- Current code works (no reassignment inside `with` block), but violates documented best practices

**Investigation Findings**:
- The `with` statement gotcha only triggers if `server` is reassigned inside the block
- Python's `smtplib.SMTP.__exit__()` calls `quit()` on the original object
- Current code has no reassignment, so no current bug exists
- Risk is to future maintenance if someone adds reassignment

**Implementation**:
```python
# Edit app/email.py function _send_email() (replace lines 24-43)

# BEFORE (current - uses with statement):
def _send_email(to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> None:
    msg = MIMEMultipart("alternative")
    msg["From"] = FROM_ADDRESS
    msg["To"] = to
    msg["Subject"] = subject
    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
        server.ehlo()
        context = ssl.create_default_context()
        server.starttls(context=context)
        server.ehlo()
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(FROM_ADDRESS, to, msg.as_string())

# AFTER (corrected - matches send_newsletter() pattern):
def _send_email(to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> None:
    msg = MIMEMultipart("alternative")
    msg["From"] = FROM_ADDRESS
    msg["To"] = to
    msg["Subject"] = subject
    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    
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

**Verification**:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k "email"
```

---

## Phase 2: Correctness Improvements (MEDIUM Priority)

### Task 2.1: Fix FTS5 Initialization
**File**: `app/search.py` (lines 52-80)  
**Priority**: MEDIUM | **Effort**: 30 min | **Risk**: Low

**Problem**: `init_fts()` uses DROP TABLE → CREATE VIRTUAL TABLE → INSERT (not atomic).

**Implementation**:
```python
# Edit app/search.py function init_fts() (lines 52-80)

# AFTER (improved - remove unnecessary DROP, cleaner initialization):
def init_fts() -> None:
    """Create FTS5 virtual table. Called once at startup."""
    try:
        # Use IF NOT EXISTS to handle concurrent create attempts
        db.session.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5("
            "title, body, summary)"
        ))
        # Sync FTS index with current posts
        db.session.execute(text("DELETE FROM posts_fts"))
        db.session.execute(text(
            "INSERT INTO posts_fts(rowid, title, body, summary) "
            "SELECT id, title, body, summary FROM posts WHERE published = 1"
        ))
        db.session.commit()
    except (OperationalError, ProgrammingError, DatabaseError) as e:
        db.session.rollback()
        try:
            db.session.execute(text("DROP TABLE IF EXISTS posts_fts"))
            db.session.commit()
        except (OperationalError, ProgrammingError, DatabaseError):
            db.session.rollback()
        logger.warning("FTS5 initialization failed: %s", e)
```

**Verification**:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k "search"
```

---

### Task 2.2: Move THEME_PRESETS to Dedicated Module
**Files**: `app/models.py`, `app/themes.py` (new), `app/context_processors.py`, `app/routes/admin/settings.py`  
**Priority**: MEDIUM | **Effort**: 1-2h | **Risk**: Low

**Implementation Steps**:
1. Create new file `app/themes.py` with `THEME_PRESETS` dictionary (copy from `models.py` lines 275-366)
2. Update `app/context_processors.py` line 138: `from app.themes import THEME_PRESETS`
3. Update `app/routes/admin/settings.py` line 6: `from app.themes import THEME_PRESETS`
4. Remove `THEME_PRESETS` from `app/models.py` (lines 275-366)

**Verification**: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v`

---

### Task 2.3: Add Flask-Caching for Scalability
**Files**: `requirements.txt`, `app/extensions.py`, `app/__init__.py`, `app/cache.py`, `app/context_processors.py`, `config.toml`  
**Priority**: MEDIUM | **Effort**: 2-3h | **Risk**: Low

**Implementation Steps**:
1. Add to `requirements.txt`: `Flask-Caching>=2.0.0` and `cachelib>=0.12.0`
2. Add to `app/extensions.py`: `from flask_caching import Cache; cache = Cache()`
3. In `app/__init__.py` `create_app()`: `from app.extensions import cache; cache.init_app(app)`
4. Update `app/cache.py`: Replace custom locking with `cache.get()`/`cache.add()`/`cache.delete()`
5. Update `app/context_processors.py`: Replace in-memory caches with Flask-Caching
6. Add to `config.toml`: `[cache] type = "simple"`

**Verification**: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v`

---

### Task 2.4: Create Centralized Error Handlers
**Files**: `app/error_handlers.py` (new), multiple route files  
**Priority**: MEDIUM | **Effort**: 2-3h | **Risk**: Low-Medium

**Implementation**:
1. Create `app/error_handlers.py` with `db_transaction()` context manager and `safe_commit()` helper
2. Refactor simple cases: replace try/except blocks with `safe_commit()`
3. Keep complex IntegrityError handling inline (e.g., `app/routes/admin/posts.py`)

**Verification**: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v`

---

### Task 2.5: Refactor Large Files (Optional, High Effort)
**Files**: `app/routes/public.py` (914 lines), `app/routes/admin/posts.py` (744 lines), `app/__init__.py` (420 lines)  
**Priority**: MEDIUM | **Effort**: 18-26h | **Risk**: Low-Medium

**Implementation** (do in order):
1. **public.py** → Create `app/routes/public/` package
2. **admin/posts.py** → Create `app/routes/admin/posts/` package
3. **__init__.py** → Extract to: `app/factory.py`, `app/logging_config.py`, `app/middleware.py`, `app/initialization.py`

**Verification** after each step: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v`

---

## Phase 3: Optional Improvements (LOW Priority)

### Task 3.1: Extract CSP Headers to Helper
**File**: `app/__init__.py`  
**Priority**: LOW | **Effort**: 1h | **Risk**: Low

Extract helper function `_build_csp_policy(nonce, report_uri=None)` and refactor `set_security_headers()`.

---

### Task 3.2: Consider tinycss2 for CSS Sanitization
**File**: `app/utils.py`  
**Priority**: LOW | **Effort**: 3-4h | **Risk**: Low

**Recommendation**: Optional. Current regex is "good enough" for admin-provided CSS.

---

### Task 3.3: Consider Lazy-Loading Config
**File**: `app/config.py`  
**Priority**: LOW | **Effort**: 2-3h | **Risk**: Low

**Recommendation**: Optional. Use PEP 562 `__getattr__` for lazy loading.

---

### Task 3.4: Fix `__all__` Ordering (Cosmetic)
**File**: `app/utils.py`  
**Priority**: LOW | **Effort**: 0 | **Risk**: None

**Recommendation**: No action needed.

---

## Testing Strategy

After each task:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ --ignore=tests/e2e
python3 -c "from app import create_app; app = create_app(); print('OK')"
```

---

## Summary Table

| Task | Priority | Effort | Risk | Phase |
|------|----------|--------|------|-------|
| 1.1 Fix SMTP handling | HIGH | 15 min | Low | 1 |
| 2.1 Fix FTS5 init | MEDIUM | 30 min | Low | 2 |
| 2.2 Move THEME_PRESETS | MEDIUM | 1-2h | Low | 2 |
| 2.3 Add Flask-Caching | MEDIUM | 2-3h | Low | 2 |
| 2.4 Error handlers | MEDIUM | 2-3h | Low-Med | 2 |
| 2.5 Refactor large files | MEDIUM | 18-26h | Low-Med | 2 |
| 3.1 Extract CSP helper | LOW | 1h | Low | 3 |
| 3.2 Consider tinycss2 | LOW | 3-4h | Low | 3 |
| 3.3 Consider lazy config | LOW | 2-3h | Low | 3 |
| 3.4 `__all__` ordering | LOW | 0 | None | 3 |

**Total effort**: Phase 1: 15 min | Phase 2: 23-35h | Phase 3: 6-8h (optional)

---

## Recommendations

1. **Start with Task 1.1** - quick win, aligns with documented practices
2. **Phase 2 tasks 2.1-2.4** can be done in parallel by different developers
3. **Phase 3 is optional** - implement only if you have specific needs
4. **Test after each task** - don't batch multiple tasks without testing
5. **Use feature branches** - each task should be its own branch/PR
