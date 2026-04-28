# Plan 9: Codebase Improvement Plan

**Date**: 2026-04-28  
**Scope**: Based on deep-dive review of DevLog Blog CMS  
**Exclusions**: Rate limiting (will be handled at reverse proxy level per DEPLOY.md)

---

## Executive Summary

Post deep-dive investigation of all identified codebase areas, this plan outlines actionable improvements organized by priority. Security and performance are verified as strong—focus is on testing gaps, refactoring opportunities, and future-scaling preparations.

**No rate limiting changes**—maintain reverse proxy approach (nginx/Cloudflare) as documented.

---

## Priority 1: High (Testing Coverage Gaps)

### 1.1 Add Missing Tests for Untested Admin Features

**Problem**: 486 passing tests (not 487 as claimed in AGENTS.md), with significant gaps in admin functionality.

**Tests to Add** (~20 new tests):

| Feature | File | Tests Needed | Priority |
|---------|------|--------------|----------|
| Static Pages CRUD | `tests/test_pages.py` | `test_create_page`, `test_edit_page`, `test_delete_page`, `test_page_publish` | High |
| Site Settings/Theme | `tests/test_settings.py` | `test_theme_preset_selection`, `test_custom_css_sanitization`, `test_logo_text_update` | High |
| Password Reset Flow | `tests/test_auth.py` | `test_forgot_password_email`, `test_reset_token_valid`, `test_reset_token_invalid`, `test_reset_password_submit` | High |
| Post Revisions | `tests/test_revisions.py` | `test_revision_history`, `test_restore_revision`, `test_revision_created_on_publish` | Medium |
| Session Management | `tests/test_sessions.py` | `test_revoke_session`, `test_session_ip_warning` (mock IP change) | Medium |
| Scheduler Status | `tests/test_scheduler.py` | `test_scheduler_status_endpoint`, `test_scheduler_health` | Low |

**Implementation**:
```bash
# Create new test files
touch tests/test_pages.py
touch tests/test_settings.py
touch tests/test_auth.py
touch tests/test_revisions.py
```

**Estimated effort**: 4-6 hours

---

### 1.2 Add Session Fixation Prevention Test

**Problem**: AGENTS.md documents `session.clear()` before `login_user()`, but no test verifies this.

**Test** (add to `tests/test_security.py`):
```python
def test_session_fixation_prevention(client, sample_user):
    """Verify session is cleared before login_user() to prevent fixation."""
    # First, set some session data before login
    with client.session_transaction() as sess:
        sess["existing_key"] = "some_value"
        sess["viewed_posts"] = [1, 2, 3]
    
    # Now login
    response = client.post("/admin/login", data={
        "username": sample_user.username,
        "password": "test-password-123"
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # Verify session was cleared (existing_key should be gone)
    with client.session_transaction() as sess:
        assert "existing_key" not in sess
        # viewed_posts may be re-initialized by the app, so check it's fresh
```

**Location**: Add to `tests/test_security.py`

**Estimated effort**: 30 minutes

---

### 1.3 Fix Flaky Upload Test

**Problem**: `test_upload_browse_delete_image` in `tests/test_integration.py` fails intermittently due to async timing.

**Investigation needed**:
- Read `tests/test_integration.py::test_upload_browse_delete_image`
- Check if using proper `wait` patterns for JS-driven dynamic content
- Consider increasing timeouts or using explicit waits

**Proposed fix**:
```python
# Instead of implicit sleep
time.sleep(0.5)  # flaky

# Use explicit wait for file to appear in DOM
from playwright.sync_api import expect
expect(page.locator("#file-list li")).to_be_visible(timeout=5000)
```

**Estimated effort**: 1 hour

---

## Priority 2: Medium (Testing Infrastructure)

### 2.1 Configure pytest-cov for Coverage Measurement

**Problem**: `pytest-cov` installed but not configured. No visibility into actual coverage.

**Implementation**:
```ini
# pytest.ini (add to existing)
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    e2e: end-to-end browser tests
addopts = --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=75
```

**Initial targets**:
- 75% coverage (current estimated: 65-70%)
- Increase to 85% after Priority 1 tests added

**Estimated effort**: 30 minutes

---

### 2.2 Refactor Duplicate Fixtures

**Problem**: Some fixtures duplicated across test files instead of living in `conftest.py`.

**Action**: Audit `test_api.py`, `test_search.py`, etc. for duplicate fixtures and consolidate into `conftest.py`.

**Estimated effort**: 1 hour

---

## Priority 3: Low-Medium (Refactoring)

### 3.1 Extract THEME_PRESETS from models.py

**Problem**: `THEME_PRESETS` dict (92 lines, lines 275-366) is configuration data in `models.py`. Contains 4 themes: github-dark, github-light, solarized-dark, monokai.

**Implementation Steps**:

1. **Create `app/theme_presets.py`**:
```python
"""Theme preset definitions for the blog.

This module defines available color schemes that can be applied
to the blog via the SiteSettings model.
"""
from typing import Optional

# Direct copy from models.py lines 275-366
THEME_PRESETS = {
    "github-dark": {
        "name": "GitHub Dark",
        "bg": "#0d1117",
        "bg-surface": "#161b22",
        "bg-elevated": "#1c2128",
        "border": "#30363d",
        "text": "#e6edf3",
        "text-muted": "#8b949e",
        "text-dim": "#7d8590",
        "text-dim-strong": "#9ca3af",
        "accent": "#58a6ff",
        "accent-hover": "#79c0ff",
        "accent-dim": "rgba(88, 166, 255, 0.1)",
        "green": "#3fb950",
        "green-dim": "rgba(63, 185, 80, 0.15)",
        "red": "#f85149",
        "red-dim": "rgba(248, 81, 73, 0.15)",
        "yellow": "#d29922",
        "purple": "#a371f7",
        "purple-dim": "rgba(163, 113, 247, 0.15)",
        "coral": "#f78166",
        "coral-dim": "rgba(247, 129, 102, 0.15)",
    },
    "github-light": {
        "name": "GitHub Light",
        "bg": "#f6f8fa",
        "bg-surface": "#ffffff",
        "bg-elevated": "#f0f2f5",
        "border": "#d0d7de",
        "text": "#1f2328",
        "text-muted": "#57606a",
        "text-dim": "#6e7781",
        "text-dim-strong": "#8b949e",
        "accent": "#0969da",
        "accent-hover": "#0550ae",
        "accent-dim": "rgba(9, 105, 218, 0.1)",
        "green": "#1a7f37",
        "green-dim": "rgba(26, 127, 55, 0.15)",
        "red": "#cf222e",
        "red-dim": "rgba(207, 34, 46, 0.15)",
        "yellow": "#9a6700",
        "purple": "#8250df",
        "purple-dim": "rgba(130, 80, 223, 0.15)",
        "coral": "#d4513d",
        "coral-dim": "rgba(212, 81, 61, 0.15)",
    },
    "solarized-dark": {
        "name": "Solarized Dark",
        "bg": "#002b36",
        "bg-surface": "#073642",
        "bg-elevated": "#094857",
        "border": "#586e75",
        "text": "#839496",
        "text-muted": "#586e75",
        "text-dim": "#657b83",
        "accent": "#268bd2",
        "accent-hover": "#1e86c8",
        "accent-dim": "rgba(38, 139, 210, 0.1)",
        "green": "#859900",
        "green-dim": "rgba(133, 153, 0, 0.15)",
        "red": "#dc322f",
        "red-dim": "rgba(220, 50, 47, 0.15)",
        "yellow": "#b58900",
        "purple": "#6c71c4",
        "purple-dim": "rgba(108, 113, 196, 0.15)",
        "coral": "#cb4b16",
        "coral-dim": "rgba(203, 75, 22, 0.15)",
    },
    "monokai": {
        "name": "Monokai",
        "bg": "#272822",
        "bg-surface": "#3e3d32",
        "bg-elevated": "#49483e",
        "border": "#75715e",
        "text": "#f8f8f2",
        "text-muted": "#a6a69c",
        "text-dim": "#8b8b7a",
        "accent": "#66d9ef",
        "accent-hover": "#a6e3e8",
        "accent-dim": "rgba(102, 217, 239, 0.1)",
        "green": "#a6e22e",
        "green-dim": "rgba(166, 226, 46, 0.15)",
        "red": "#f92672",
        "red-dim": "rgba(249, 38, 114, 0.15)",
        "yellow": "#e6db74",
        "yellow-dim": "rgba(230, 219, 116, 0.15)",
        "purple": "#ae81ff",
        "purple-dim": "rgba(174, 129, 255, 0.15)",
        "coral": "#fd971f",
        "coral-dim": "rgba(253, 151, 31, 0.15)",
    },
}

def get_theme_preset(name: str) -> Optional[dict]:
    """Get a theme preset by name, returning None if not found."""
    return THEME_PRESETS.get(name)

def list_theme_names() -> list[str]:
    """Return list of available theme preset names."""
    return list(THEME_PRESETS.keys())
```

2. **Update `app/models.py`**: Remove THEME_PRESETS dict (lines 275-366), add import:
```python
# THEME_PRESETS moved to app.theme_presets
from app.theme_presets import THEME_PRESETS
```

3. **Update imports** (verified with grep):
   - `app/routes/admin/settings.py` (line 6): Change `from app.models import SiteSettings, THEME_PRESETS` to:
     ```python
     from app.models import SiteSettings
     from app.theme_presets import THEME_PRESETS
     ```
   - `app/context_processors.py` (lines 138, 154, 158, 162, 163, 173, 180, 184): Change all `from app.models import THEME_PRESETS` to `from app.theme_presets import THEME_PRESETS`

4. **Run tests**: `pytest tests/ -v`

**Estimated effort**: 1 hour

---

### 3.2 Split public.py into Package

**Problem**: `public.py` is 914 lines with 14 distinct route handlers.

**Proposed Structure**:
```
app/routes/public/
├── __init__.py          # Blueprint creation + imports
├── blog.py              # index, archive, post, page, tag routes
├── search.py            # search route + FTS helpers
├── subscribe.py         # subscribe, confirm, unsubscribe routes
├── share.py             # track_share, short_url_redirect, public_preview
├── sitemap.py           # robots_txt, sitemap_xml, favicon
├── health.py            # health_check
└── helpers.py           # _safe_redirect_url, _get_cached_tags_and_counts, _get_related_posts
```

**Implementation Steps**:

1. **Create directory and files**:
```bash
mkdir -p app/routes/public
touch app/routes/public/__init__.py
touch app/routes/public/helpers.py
touch app/routes/public/blog.py
touch app/routes/public/search.py
touch app/routes/public/subscribe.py
touch app/routes/public/share.py
touch app/routes/public/sitemap.py
touch app/routes/public/health.py
```

2. **Move code** following the admin blueprint pattern in `app/routes/admin/__init__.py`

3. **Update `app/__init__.py`**: No change needed if `from app.routes.public import public` still works

4. **Run full test suite**: `pytest tests/ -v`

**Estimated effort**: 3-4 hours

**Risk**: Low (follows existing admin blueprint pattern)

---

## Priority 4: Low (PostgreSQL Migration Preparation)

### 4.1 Add Alembic SQLite Batch Mode

**Problem**: SQLite migrations may fail without batch mode for certain schema changes.

**Implementation** (`migrations/env.py`):
```python
def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    # Add batch mode for SQLite
    conf_args = current_app.extensions['migrate'].configure_args
    if connectable.dialect.name == 'sqlite':
        conf_args["render_as_batch"] = True
    
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, **conf_args)
        # ... rest of function
```

**Estimated effort**: 30 minutes

---

### 4.2 Create Database Dialect Detection Utility

**Problem**: No way to detect if running on SQLite vs PostgreSQL.

**Implementation** (`app/utils.py`):
```python
def get_db_dialect() -> str:
    """Return the database dialect name (sqlite, postgresql, etc.)."""
    from app.extensions import db
    return db.engine.dialect.name
```

**Estimated effort**: 15 minutes

---

### 4.3 Update Health Check for PostgreSQL Compatibility

**Problem**: `app/routes/public.py:881` uses `sqlite_master` query that fails on PostgreSQL.

**Implementation**:
```python
# In health_check() function
from app.utils import get_db_dialect

dialect = get_db_dialect()
if dialect == 'sqlite':
    has_fts = db.session.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'"
    )).fetchone() is not None
elif dialect == 'postgresql':
    has_fts = db.session.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name='posts' AND column_name='search_vector')"
    )).scalar()
else:
    has_fts = False
```

**Estimated effort**: 30 minutes

---

### 4.4 Create PostgreSQL Search Module (Future-Ready)

**Problem**: No PostgreSQL FTS implementation exists. Search breaks if migrating to PostgreSQL.

**Implementation** (`app/search_postgres.py`):
```python
"""PostgreSQL full-text search implementation."""
from sqlalchemy import text
from app.extensions import db
from app.config import FTS_RESULT_LIMIT

def search(query: str) -> list[tuple[int, float]]:
    """Search using PostgreSQL tsvector."""
    tsquery = " & ".join(query.split())
    result = db.session.execute(text("""
        SELECT id, ts_rank(search_vector, plainto_tsquery('english', :q)) AS rank
        FROM posts
        WHERE published = TRUE
          AND search_vector @@ plainto_tsquery('english', :q)
        ORDER BY rank DESC
        LIMIT :limit
    """), {"q": tsquery, "limit": FTS_RESULT_LIMIT})
    return [(row[0], float(row[1])) for row in result.fetchall()]

def get_did_you_mean(query: str, threshold: float = 0.3) -> str | None:
    """Use pg_trgm for 'Did you mean?' suggestions."""
    result = db.session.execute(text("""
        SELECT title, similarity(title, :q) AS sim
        FROM posts WHERE published = TRUE
        ORDER BY sim DESC LIMIT 1
    """), {"q": query})
    row = result.first()
    if row and row[1] >= threshold:
        return row[0]
    return None

# ... implement other functions from search.py with PostgreSQL equivalents
```

**Note**: Don't integrate yet—just create the file for future use.

**Estimated effort**: 4-6 hours

---

## Priority 5: Low (APScheduler - Keep Current Approach)

### 5.1 Add Scheduler Health Check Enhancement (Optional)

**Problem**: Basic scheduler health info, no job execution history.

**Enhancement** (optional, low priority):
```python
# In app/scheduler.py, enhance get_scheduler_health()
def get_scheduler_health() -> dict:
    """Return enhanced scheduler health info."""
    if scheduler is None:
        return {"status": "not_initialized"}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "func": job.func.__name__
        })
    
    return {
        "status": "running" if scheduler.running else "stopped",
        "jobs": jobs,
        "worker_id": os.getpid()
    }
```

**Recommendation**: **Skip this**. Current approach is sufficient for single-server deployment. Revisit if scaling to multiple servers.

**Estimated effort**: 1 hour (optional)

---

## Priority 6: Low (File Uploads - Keep Local Storage)

### 6.1 Create Storage Abstraction Layer (Future-Ready)

**Problem**: No abstraction for storage—tightly coupled to local filesystem.

**Recommendation**: **Skip for now**. At current scale (5.9MB, 1,472 files), local storage is optimal.

**If implementing later** (for reference):
- Create `app/storage.py` with `StorageBackend` abstract class
- Implement `LocalStorage` and `S3Storage` classes
- Add configuration option in `config.toml`
- Estimated effort: 4-6 hours

---

## Implementation Order

| Phase | Items | Estimated Time | Dependencies |
|-------|-------|----------------|-------------|
| **Phase 1** | 1.1 (Add missing tests), 1.2 (Session fixation test) | 5-7 hours | None |
| **Phase 2** | 1.3 (Fix flaky test), 2.1 (pytest-cov), 2.2 (Fixtures) | 2-3 hours | Phase 1 |
| **Phase 3** | 3.1 (THEME_PRESETS), 3.2 (Split public.py) | 4-5 hours | None (can parallel with Phase 1) |
| **Phase 4** | 4.1-4.4 (PostgreSQL prep) | 5-7 hours | None (future-ready, can defer) |
| **Phase 5** | 5.1 (Scheduler), 6.1 (Storage) | Skip | N/A |

**Total estimated time for recommended items**: 11-15 hours

---

## Success Metrics

- [ ] Test count: 486 → **506+** (20 new tests)
- [ ] Coverage: ~65-70% → **75%+**
- [ ] `models.py` reduced from 366 → **274 lines** (extract THEME_PRESETS)
- [ ] `public.py` reduced from 914 → **split into <200 line modules**
- [ ] Flaky test fixed (consistent pass rate)
- [ ] PostgreSQL migration path: **ready but not required**

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Splitting public.py breaks imports | Low | High | Follow admin blueprint pattern; run tests after each module move |
| Test additions break existing tests | Low | Medium | Run full suite after each new test file |
| PostgreSQL prep not needed | High | Low | These are future-ready (low priority, can defer) |
| Refactoring introduces regressions | Low | Medium | Comprehensive test suite catches issues |

---

## Conclusion

The codebase is **production-ready** with strong security and performance. This plan focuses on:
1. **Testing gaps** (highest impact—untested admin features)
2. **Code organization** (maintainability—large file refactoring)
3. **Future readiness** (PostgreSQL prep—deferrable)

**No rate limiting changes**—reverse proxy approach is correct for this architecture.
