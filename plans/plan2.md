# Code Quality Improvement Plan

**Date**: 2026-04-28  
**Based on**: Deep-dive code review with subagent investigations
**Total Estimated Effort**: 8-10 hours

---

## Executive Summary

This plan addresses code quality issues identified in the codebase review. The codebase is **high-quality** with excellent security practices (514 tests passing). The improvements focus on:
- **Consistency** (error handling, coding patterns)
- **Preventing future bugs** (SMTP context manager, missing error handling)
- **Maintainability** (large file refactoring, testability)

**No security vulnerabilities** were found. No breaking changes required.

---

## Table of Contents

- [Task 1.1: Fix Inconsistent Error Handling in pages.py](#task-11-fix-inconsistent-error-handling-in-pagespy)
- [Task 1.2: Add Missing Error Handling in API Endpoints](#task-12-add-missing-error-handling-in-api-endpoints)
- [Task 1.3: Refactor _send_email() for Consistency](#task-13-refactor-_send_email-for-consistency)
- [Task 2.1: Extract Template Filters to Separate Module](#task-21-extract-template-filters-to-separate-module)
- [Task 2.2: Add Warning for Missing File Locking](#task-22-add-warning-for-missing-file-locking)
- [Task 2.3: Create Reusable Transaction Helper](#task-23-create-reusable-transaction-helper)
- [Task 3.1: Extract SQL Constants in search.py](#task-31-extract-sql-constants-in-searchpy)
- [Task 3.2: Lazy-Load Config (Optional)](#task-32-lazy-load-config-optional)
- [Implementation Order](#implementation-order)
- [Testing Strategy](#testing-strategy)
- [Risk Assessment](#risk-assessment)

---

## Priority 1: HIGH (Fix Soon - 3-4 hours)

### Task 1.1: Fix Inconsistent Error Handling in pages.py

**Problem**: `pages.py` rollback doesn't reapply changes after `IntegrityError`, causing data loss on slug collisions. The `posts.py` file correctly handles this, but `pages.py` doesn't follow the same pattern.

**Locations**:
- `/home/sugarwookie/projects/blog/app/routes/admin/pages.py` lines 77-82 (`new_page()`)
- `/home/sugarwookie/projects/blog/app/routes/admin/pages.py` lines 143-148 (`edit_page()`)

**Current Code (Broken)**:
```python
try:
    db.session.commit()
except (IntegrityError, OperationalError):
    db.session.rollback()
    flash("Database error occurred. Please try again.", "error")
    return redirect(url_for("admin.pages_list"))  # User loses all input!
```

**Note**: The current code loses all form input on any database error. The fix below follows the pattern from `posts.py` which properly handles slug collisions.

**Fix**: Follow `posts.py` pattern with slug regeneration and retry:

```python
try:
    db.session.commit()
except IntegrityError as e:
    db.session.rollback()
    if "slug" in str(e).lower():
        page = db.session.get(Page, page.id)
        page.slug = _generate_unique_slug(Page, title)
        # Reapply all changes
        page.title = title
        page.body = body
        page.published = published
        db.session.commit()
        return render_template("admin/editor.html", page=page, ...)
    else:
        flash("Database error occurred.", "error")
        return redirect(url_for("admin.pages_list"))
except OperationalError:
    db.session.rollback()
    flash("Database error occurred.", "error")
    return redirect(url_for("admin.pages_list"))
```

**Important**: The fix must reapply ALL field changes after rollback (as documented in AGENTS.md "IntegrityError Rollback Gotcha"). SQLAlchemy expires all attributes after rollback.

**Steps**:
1. Read current `pages.py` to understand full context
2. Add `_generate_unique_slug` import from helpers
3. Modify `new_page()` error handling (lines 77-82)
4. Modify `edit_page()` error handling (lines 143-148)
5. Add helper function `_apply_page_updates(page, title, body, ...)` similar to `posts.py`
6. Run tests: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v`

**Estimated Effort**: 1 hour

---

### Task 1.2: Add Missing Error Handling in API Endpoints

**Problem**: `api.py` create/update endpoints don't handle `IntegrityError` on `db.session.commit()`, which can cause 500 errors on slug collisions.

**Locations**:
- `/home/sugarwookie/projects/blog/app/routes/api.py` lines 192-201 (`create_post()`)
- `/home/sugarwookie/projects/blog/app/routes/api.py` lines 257-261 (`update_post()`)

**Current Code (Missing try/except on commit)**:
```python
db.session.add(post)
db.session.flush()
if not sync_fts(post.id, post.title, post.body, post.summary, post.published):
    db.session.rollback()
    return jsonify({"error": "Search index unavailable"}), 503
db.session.commit()  # No try/except! IntegrityError will propagate
```

**Note**: The `sync_fts()` call has error handling, but `db.session.commit()` does not.

**Fix**:
```python
db.session.add(post)
db.session.flush()
if not sync_fts(post.id, post.title, post.body, post.summary, post.published):
    db.session.rollback()
    return jsonify({"error": "Search index unavailable"}), 503
try:
    db.session.commit()
except IntegrityError:
    db.session.rollback()
    return jsonify({"error": "Duplicate slug or database error"}), 409
except OperationalError:
    db.session.rollback()
    return jsonify({"error": "Database error occurred"}), 500
```

**Steps**:
1. Read `api.py` to understand context
2. Add `from sqlalchemy.exc import IntegrityError` import
3. Wrap `db.session.commit()` in try/except in `create_post()`
4. Wrap `db.session.commit()` in try/except in `update_post()`
5. Run tests: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/test_api.py -v`

**Estimated Effort**: 30 minutes

---

### Task 1.3: Refactor _send_email() for Consistency

**Problem**: Uses `with smtplib.SMTP() as server:` while AGENTS.md explicitly warns "Do not use `with`". The gotcha doesn't currently apply (no reassignment), but consistency prevents future bugs.

**Location**: `/home/sugarwookie/projects/blog/app/email.py` lines 24-43

**Current Code**:
```python
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
```

**Fixed Code** (match newsletter pattern):
```python
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
        if server is not None:
            try:
                server.quit()
            except OSError:
                pass
```

**Note**: While the AGENTS.md "SMTP Context Manager Gotcha" doesn't apply here (no reassignment of `server` inside the block), this change ensures consistency with the `send_newsletter()` pattern and prevents future bugs if someone modifies the code.

**Steps**:
1. Modify `_send_email()` function in `app/email.py`
2. Verify `send_confirmation()` and `send_password_reset()` still work (they call `_send_email()`)
3. Run tests: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/test_admin.py -v -k "password or reset"`

**Estimated Effort**: 30 minutes

---

## Priority 2: MEDIUM (Fix When Convenient - 4-5 hours)

### Task 2.1: Extract Template Filters to Separate Module

**Problem**: Filters defined inside `create_app()` cannot be unit tested in isolation. Inconsistent with `context_processors.py` pattern already in use.

**Location**: `/home/sugarwookie/projects/blog/app/__init__.py` lines 184-220

**Current Code** (inside `create_app()`):
```python
@app.template_filter("markdown_safe")
def markdown_safe_filter(text: str) -> str:
    html = markdown.markdown(text, extensions=["fenced_code", "tables"])
    return nh3.clean(html, tags=MARKDOWN_ALLOWED_TAGS, attributes=MARKDOWN_ALLOWED_ATTRIBUTES)

@app.template_filter("reading_time")
def reading_time_filter(text: str) -> str:
    if not text:
        return "1 min read"
    words = len(text.split())
    minutes = max(1, round(words / 200))
    return f"{minutes} min read"
# ... etc
```

**Fix**: Create `/home/sugarwookie/projects/blog/app/filters.py`:

```python
"""Template filters for Jinja2."""
import os
import markdown
import nh3

from flask import has_request_context, g
from app.markdown_config import MARKDOWN_ALLOWED_TAGS, MARKDOWN_ALLOWED_ATTRIBUTES
from app.utils import sanitize_css as sanitize_css_util


def markdown_safe(text: str) -> str:
    """Render markdown and sanitize HTML using nh3."""
    html = markdown.markdown(text, extensions=["fenced_code", "tables"])
    return nh3.clean(
        html, tags=MARKDOWN_ALLOWED_TAGS, attributes=MARKDOWN_ALLOWED_ATTRIBUTES
    )


def reading_time(text: str) -> str:
    """Estimate reading time for text."""
    if not text:
        return "1 min read"
    words = len(text.split())
    minutes = max(1, round(words / 200))
    return f"{minutes} min read"


def sanitize_css(text: str) -> str:
    """Sanitize CSS using app.utils.sanitize_css."""
    return sanitize_css_util(text) if text else ""


def post_image_url(post, upload_folder: str):
    """Get the image URL for a post if the image exists."""
    if not post or not post.image:
        return None
    if has_request_context():
        if not hasattr(g, "_post_image_cache"):
            g._post_image_cache = {}
        post_id = id(post)
        if post_id in g._post_image_cache:
            return g._post_image_cache[post_id]
        path = os.path.join(upload_folder, post.image)
        result = post.image if os.path.isfile(path) else None
        g._post_image_cache[post_id] = result
        return result
    path = os.path.join(upload_folder, post.image)
    return post.image if os.path.isfile(path) else None


def register_filters(app):
    """Register all template filters with the Flask app."""
    app.jinja_env.filters['markdown_safe'] = markdown_safe
    app.jinja_env.filters['reading_time'] = reading_time
    app.jinja_env.filters['sanitize_css'] = sanitize_css
    # post_image_url needs access to app.config
    app.jinja_env.filters['post_image_url'] = lambda post: post_image_url(post, app.config["UPLOAD_FOLDER"])
```

**Then modify `create_app()`** in `/home/sugarwookie/projects/blog/app/__init__.py`:

```python
def create_app():
    # ... existing setup ...
    
    from app.filters import register_filters
    register_filters(app)
    
    # Remove the old filter definitions (lines 184-220)
    # ... rest of function ...
```

**Steps**:
1. Create `/home/sugarwookie/projects/blog/app/filters.py` with above code
2. Modify `create_app()` in `app/__init__.py` to use `register_filters()`
3. Delete filter definitions from `create_app()` (lines 184-220)
4. Write unit tests in `tests/test_filters.py`
5. Run tests: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v`

**Estimated Effort**: 2 hours

---

### Task 2.2: Add Warning for Missing File Locking

**Problem**: When `fcntl` is unavailable (Windows), code runs without locking but doesn't warn user. Could cause duplicate newsletter sends.

**Location**: `/home/sugarwookie/projects/blog/app/scheduler.py` - add to `init_scheduler()`

**Fix**: Add warning at line 293 (after imports, before SMTP check):

```python
def init_scheduler(app) -> Optional["BackgroundScheduler"]:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    import atexit

    from app.config import NEWSLETTER_SEND_TIME, SMTP_HOST

    # Warn if file locking unavailable
    if not HAS_FCNTL:
        app.logger.warning(
            "File locking (fcntl) unavailable - likely running on Windows. "
            "Scheduled tasks will not be protected against concurrent execution "
            "with multiple workers, which may cause duplicate newsletter sends."
        )

    if not SMTP_HOST:
        app.logger.info("SMTP_HOST not configured; newsletter scheduler disabled")
        return None
    # ... rest of function ...
```

**Steps**:
1. Modify `init_scheduler()` function in `app/scheduler.py`
2. Add warning log when `HAS_FCNTL` is False
3. Run tests: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/test_newsletter.py -v`

**Estimated Effort**: 15 minutes

---

### Task 2.3: Create Reusable Transaction Helper

**Problem**: 53 occurrences of `db.session.rollback()` with inconsistent patterns across codebase.

**Location**: Create new file `/home/sugarwookie/projects/blog/app/transaction.py`

**Implementation**:

```python
"""Database transaction helpers for consistent error handling."""
from functools import wraps
from sqlalchemy.exc import IntegrityError, OperationalError
from flask import flash, redirect, url_for, current_app
from app.extensions import db


def transactional(
    on_integrity_error=None,
    error_message="Database error occurred. Please try again.",
    error_redirect=None,
):
    """
    Decorator to handle database transactions with proper rollback.
    
    Args:
        on_integrity_error: Optional callback that receives the exception.
                            Should return a response or None to use default.
        error_message: Flash message on error.
        error_redirect: URL to redirect to on error.
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except IntegrityError as e:
                db.session.rollback()
                if on_integrity_error:
                    result = on_integrity_error(e)
                    if result is not None:
                        return result
                flash(error_message, "error")
                return redirect(error_redirect or url_for("admin.dashboard"))
            except OperationalError:
                db.session.rollback()
                flash(error_message, "error")
                return redirect(error_redirect or url_for("admin.dashboard"))
        return wrapped
    return decorator


def commit_with_slug_retry(
    model_class,
    instance,
    title,
    exclude_id=None,
    fts_sync_callback=None,
):
    """
    Commit with automatic slug regeneration on IntegrityError.
    
    Args:
        model_class: The model class (Post, Page, etc.)
        instance: The model instance to commit
        title: Title used for slug generation
        exclude_id: ID to exclude from slug uniqueness check
        fts_sync_callback: Optional callback for FTS sync before commit
    
    Returns:
        The (possibly updated) instance
    """
    from app.routes.admin.helpers.slug import _generate_unique_slug
    
    for attempt in range(2):
        try:
            if fts_sync_callback:
                if not fts_sync_callback():
                    raise Exception("FTS sync failed")
            db.session.commit()
            return instance
        except IntegrityError as e:
            db.session.rollback()
            if attempt == 0 and "slug" in str(e).lower():
                instance.slug = _generate_unique_slug(
                    model_class, title, exclude_id=exclude_id
                )
                db.session.add(instance)
            else:
                raise
    return instance
```

**Steps**:
1. Create `/home/sugarwookie/projects/blog/app/transaction.py`
2. Optionally refactor one file (e.g., `pages.py`) to use the helper
3. Run tests: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v`

**Estimated Effort**: 3 hours (1 hour for helper, 2 hours for optional refactoring)

---

## Priority 3: LOW (Optional Improvements - 1-2 hours)

### Task 3.1: Extract SQL Constants in search.py

**Problem**: Raw SQL strings scattered through function bodies in `search.py`.

**Location**: `/home/sugarwookie/projects/blog/app/search.py`

**Fix**: Extract SQL to module-level constants:

```python
# At top of search.py, after imports
_SQL_CHECK_FTS_TABLE = """
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='posts_fts'
"""

_SQL_CREATE_FTS_TABLE = """
    CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts 
    USING fts5(title, body, summary, prefix='2 3 4')
"""

_SQL_REBUILD_FTS = "INSERT INTO posts_fts(posts_fts) VALUES('rebuild')"

_SQL_SYNC_FTS = """
    INSERT OR REPLACE INTO posts_fts(rowid, title, body, summary) 
    VALUES(:id, :title, :body, :summary)
"""

_SQL_DELETE_FTS = "DELETE FROM posts_fts WHERE rowid = :id"

_SQL_SEARCH_FTS = """
    SELECT rowid, rank FROM posts_fts 
    WHERE posts_fts MATCH :q 
    ORDER BY rank 
    LIMIT :limit
"""

_SQL_GET_INDEXED_TERMS = "SELECT title FROM posts WHERE published = 1"
```

Then use in functions:
```python
def _check_fts_enabled() -> bool:
    global _fts_enabled, _fts_check_time
    import time
    now = time.monotonic()
    if _fts_enabled is None or (now - _fts_check_time) > _FTS_CHECK_TTL:
        check = db.session.execute(text(_SQL_CHECK_FTS_TABLE)).fetchone()
        _fts_enabled = bool(check)
        _fts_check_time = now
    return _fts_enabled
```

**Steps**:
1. Read `search.py` to identify all SQL strings
2. Extract to constants at module level
3. Replace inline strings with constants
4. Run tests: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/test_search.py -v`

**Estimated Effort**: 1 hour

---

### Task 3.2: Lazy-Load Config (Optional)

**Problem**: Config loads at import time (line 69 in `config.py`). Fail-fast is good, but lazy-loading follows Flask best practices.

**Location**: `/home/sugarwookie/projects/blog/app/config.py` line 69

**Fix** (minimal change):

```python
# In config.py, replace line 69:
# _config = load_config()  # Remove this line

def _get_config():
    """Get config, loading if necessary."""
    if not hasattr(_get_config, '_cached'):
        _get_config._cached = load_config()
    return _get_config._cached
```

Then in `create_app()`:
```python
def create_app():
    from app.config import _get_config
    _config = _get_config()
    
    _validate_config(_config)
    # ... rest of function uses _config dict ...
```

**Note**: This requires changing all the module-level variables (`APP_TITLE`, etc.) to use `_get_config()` or passing config dict to `create_app()`. **Higher risk of regression.**

**Recommendation**: Skip this task unless you're actively facing import-time config issues.

**Estimated Effort**: 1 hour (with testing)

---

## Implementation Order

### Phase 1: High Priority (Do First)
1. **Task 1.1**: Fix pages.py error handling (prevents data loss)
2. **Task 1.2**: Add API error handling (prevents 500 errors)
3. **Task 1.3**: Refactor _send_email() (prevents future bugs)

### Phase 2: Medium Priority (Do When Convenient)
4. **Task 2.2**: Add Windows warning (quick win, 15 min)
5. **Task 2.1**: Extract filters (improves testability)
6. **Task 2.3**: Create transaction helper (improves consistency)

### Phase 3: Low Priority (Optional)
7. **Task 3.1**: Extract SQL constants (style improvement)
8. **Task 3.2**: Lazy-load config (Flask best practice, higher risk)

---

## Testing Strategy

After each task:
1. Run the specific test file for the modified module
2. Run full test suite: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ --ignore=tests/e2e -v`
3. Verify 514 tests still pass

**Target**: Maintain 514 passing tests throughout refactoring.

---

## Risk Assessment

| Task | Risk Level | Reason |
|------|-------------|--------|
| 1.1 Fix pages.py | **Low** | Follows proven pattern from posts.py |
| 1.2 Add API error handling | **Low** | Adding try/except, not changing logic |
| 1.3 Refactor _send_email() | **Low** | Equivalent logic, just different syntax |
| 2.1 Extract filters | **Low** | Same functions, just moved to new file |
| 2.2 Add warning | **None** | Additive only, doesn't change behavior |
| 2.3 Create helper | **Low** | New file, doesn't change existing code unless you refactor |
| 3.1 Extract SQL | **Low** | Same SQL, just assigned to variables |
| 3.2 Lazy config | **Medium** | Touches many modules, higher regression risk |

---

## Success Criteria

- [ ] All HIGH priority tasks completed
- [ ] 514 tests passing (or more if new tests added)
- [ ] No new linting errors
- [ ] Code consistency improved (error handling, patterns)
- [ ] Testability improved (filters can be unit tested)

---

## Notes

- **Don't do everything at once**. Tackle one task, run tests, commit.
- **Follow existing patterns**. The codebase is well-written; maintain its style.
- **Document as you go**. Update docstrings if behavior changes.
- **Skip Task 3.2** if it feels too risky - the current fail-fast behavior is acceptable.

---

## Quick Reference - What to Do First

| Priority | Task | Why First? | Time |
|----------|------|-----------|------|
| **1** | **Task 1.1** - Fix pages.py error handling | Prevents data loss on slug collisions | 1 hour |
| **2** | **Task 1.2** - Add API error handling | Prevents 500 errors on slug conflicts | 30 min |
| **3** | **Task 1.3** - Refactor _send_email() | Consistency with AGENTS.md guidelines | 30 min |
| **4** | **Task 2.2** - Add Windows warning | Quick win, 15 min, alerts users | 15 min |

After completing HIGH priority tasks, the codebase will be more consistent and have fewer edge-case bugs.

---

## Verification Checklist

After completing all tasks:
- [ ] All 514 tests still pass (`ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ --ignore=tests/e2e -v`)
- [ ] No new mypy/pylint errors
- [ ] Code follows existing patterns in the codebase
- [ ] Changes committed with clear commit messages
- [ ] AGENTS.md updated if behavior changes

---

**End of Plan**
