# Blog Codebase Improvement Plan

**Date**: April 28, 2026  
**Review Type**: Comprehensive deep-dive review  
**Status**: Planning phase (not yet started)

---

## Executive Summary

Following a comprehensive codebase review using multiple analysis agents, this plan outlines improvements across 11 key areas. The codebase is **well-architected** with strong security posture and excellent documentation (514 tests, full SQLAlchemy 2.0 adoption, comprehensive AGENTS.md).

**Key Findings:**
- Critical: Test uploads must be cleaned before production (1,580 files)
- Critical: nginx rate limiting documented but NOT implemented
- Critical: Newsletter system has incorrect return value semantics
- High: PostgreSQL migration script has schema mismatches
- High: No linting/formatting configuration
- Medium: Several caching gaps and consistency issues

---

## Priority 1: Critical (Fix Before Production)

### 1.1 Clean Test Uploads

**Issue**: `app/static/uploads/` contains 1,580 test files (6.3 MB) that must not be deployed to production.

**Files Affected**:
- `app/static/uploads/` (entire directory contents)
- `tests/conftest.py` (missing cleanup fixture)

**Implementation**:
```bash
# One-time cleanup
rm -rf /home/sugarwookie/projects/blog/app/static/uploads/*

# Verify
ls -la /home/sugarwookie/projects/blog/app/static/uploads/
```

**Add to `tests/conftest.py`**:
```python
import pytest
import os
from app.config import UPLOAD_FOLDER

@pytest.fixture(scope="session", autouse=True)
def cleanup_uploads_at_session_end():
    """Clean up uploads directory after all tests complete."""
    yield
    if os.path.exists(UPLOAD_FOLDER):
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Warning: Could not delete {file_path}: {e}")
```

**Verification**:
- `ls app/static/uploads/` should return empty
- Run full test suite, verify uploads cleaned after

---

### 1.2 Implement nginx Rate Limiting

**Issue**: DEPLOY.md documents rate limiting recommendations, but `nginx/conf.d/blog.conf` does NOT implement them. Creates false sense of security.

**Files Affected**:
- `nginx/conf.d/blog.conf`
- `DEPLOY.md` (verification checklist)

**Current State**: No rate limit zones defined, no rate limiting applied to endpoints.

**Implementation for `nginx/conf.d/blog.conf`**:

Add to `nginx.conf` http block (or add here if using conf.d only):
```nginx
# In nginx.conf http block, or at top of blog.conf if allowed:
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=admin:10m rate=20r/m;
limit_req_zone $binary_remote_addr zone=api:10m rate=20r/m;
limit_req_zone $binary_remote_addr zone=public:10m rate=100r/m;
```

Update `blog.conf` server block:
```nginx
server {
    # ... existing config ...

    # Rate limit login endpoint (most sensitive)
    location = /admin/login {
        limit_req zone=login burst=5 nodelay;
        limit_req_status 429;
        proxy_pass http://127.0.0.1:5000;
        # ... rest of proxy settings ...    }

    # Rate limit all other admin routes
    location /admin/ {
        limit_req zone=admin burst=5 nodelay;
        limit_req_status 429;
        proxy_pass http://127.0.0.1:5000;
        # ... rest of proxy settings ...    }

    # Rate limit API routes
    location /api/ {
        limit_req zone=api burst=10 nodelay;
        limit_req_status 429;
        proxy_pass http://127.0.0.1:5000;
        # ... rest of proxy settings ...    }

    # Public routes (less restrictive)
    location / {
        limit_req zone=public burst=20 nodelay;
        limit_req_status 429;
        proxy_pass http://127.0.0.1:5000;
        # ... rest of proxy settings ...    }
}
```

**Testing**:
```bash
# Test nginx config
nginx -t

# Test rate limiting (expects 429 after burst)
ab -n 20 -c 10 http://yourdomain/admin/login

# Monitor logs
tail -f /var/log/nginx/error.log | grep "limiting requests"
```

---

### 1.3 Fix Newsletter Return Value Semantics

**Issue**: `send_newsletter()` in `app/email.py` returns `False` ONLY if initial SMTP connection fails. Returns `True` even if SOME individual emails fail (when `all_sent=False`). This causes `scheduler.py` to mark posts as "sent" incorrectly.

**Files Affected**:
- `app/email.py` (lines 142-213, `send_newsletter()` function)
- `app/scheduler.py` (line 136, where return value is checked)

**Current Behavior**:
```python
# email.py - current (problematic)
def send_newsletter(posts, subscribers, app=None):
    # ...
    if not all_sent:
        app.logger.warning(f"Some emails failed to send")
        return True  # BUG: Returns True even when some failed!
    return True
```

**Fix Implementation**:
```python
# email.py - fixed version
def send_newsletter(posts, subscribers, app=None):
    """Send newsletter to subscribers.
    
    Returns:    - True if ALL emails sent successfully
        - False if initial SMTP connection fails OR any emails failed
    """
    # ... existing connection logic ...
    
    if not all_sent:
        app.logger.warning(f"Some emails failed to send")
        return False  # FIXED: Return False when some fail
    
    return True
```

**Also fix per-post attempt tracking in `scheduler.py`** (lines 146-148):
```python
# scheduler.py - current issue
if not send_result:
    # Increments attempts for ALL posts, even those not attempted
    for post in posts:
        post.newsletter_attempts += 1  
        
# Fixed version - only increment attempted posts
if not send_result:
    for post in posts:
        # Only increment if post was actually attempted
        # (Need to track which posts were attempted vs skipped)
        post.newsletter_attempts += 1
```

**Better approach**: Modify `send_newsletter()` to return list of failed post IDs:
```python
def send_newsletter(posts, subscribers, app=None):
    """Returns: (all_succeeded: bool, failed_post_ids: list[int])"""
    # ... 
    return all_sent, failed_post_ids

# In scheduler.py:
all_sent, failed_post_ids = send_newsletter(posts, subscribers, app)
if not all_sent:
    for post in posts:
        if post.id in failed_post_ids:
            post.newsletter_attempts += 1
```

**Verification**:
- Run newsletter tests: `pytest tests/test_newsletter.py -v`
- Check that failed sends don't mark posts as successfully sent

---

### 1.4 Fix `make_owner()` Race Condition

**Issue**: In `app/routes/admin/users.py`, `make_owner()` first demotes ALL admins (temporarily leaving ZERO admins), then promotes target. If commit fails, system has no admins.

**File**: `app/routes/admin/users.py` (lines 218-223)

**Current Code**:
```python
# DANGEROUS: Temporarily no admins
all_admins = db.session.execute(select(User).filter(User.is_admin == True)).scalars().all()
for admin in all_admins:
    admin.is_admin = False  # Now NO admins exist
user.is_admin = True     # If this fails, system is broken
db.session.commit()
```

**Fixed Implementation**:
```python
@admin.route("/users/<int:user_id>/make-owner", methods=["POST"])
@admin_required
def make_owner(user_id):
    # ... existing password verification ...
    
    try:
        # FIXED: First promote target user (so at least ONE admin always exists)
        user.is_admin = True
        db.session.flush()  # Get new state ready
        
        # Now demote all other admins (target is already admin)
        all_admins = db.session.execute(
            select(User).filter(User.is_admin == True, User.id != user.id)
        ).scalars().all()
        
        for admin in all_admins:
            admin.is_admin = False
        
        # Handle ownership transfer for site settings
        settings = SiteSettings.get_instance()
        settings.ownership_user_id = user.id
        
        db.session.commit()
        # ... rest of success handling ...
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error transferring ownership: {str(e)}", "error")
    
    return redirect(url_for("admin.users"))
```

**Verification**:
- Run test: `pytest tests/test_users.py::test_make_owner -v`
- Verify at least one admin always exists during transfer

---

## Priority 2: High Priority

### 2.1 Add Linting and Formatting

**Issue**: No linting/formatting tools configured. No `ruff`, `flake8`, `black`, or pre-commit hooks.

**Files to Create**:
- `pyproject.toml` (tool configuration)
- `.pre-commit-config.yaml`
- Update `.github/workflows/test.yml` to add linting step

**Implementation**:

**`pyproject.toml`**:
```toml
[tool.ruff]
target-version = "py314"
line-length = 100
select = ["E", "F", "W", "I", "UP", "B", "SIM", "TCH"]

[tool.ruff.format]
quote-style = "double"

[tool.black]
line-length = 100
target-version = ["py314"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**`.pre-commit-config.yaml`**:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.0
    hooks:
      - id: mypy
        additional_dependencies: [flask, sqlalchemy]
        args: [--ignore-missing-imports]
```

**Update `.github/workflows/test.yml`**:
```yaml
- name: Run linters
  run: |
    pip install ruff
    ruff check app/ tests/
    ruff format --check app/ tests/
```

**`requirements-dev.txt`** (update):
```
-r requirements.txt
pytest>=9.0.2
pytest-cov>=4.0
ruff>=0.3.0
mypy>=1.11.0
```

**Verification**:
```bash
pip install ruff mypy
ruff check app/ tests/
ruff format --check app/ tests/
```

---

### 2.2 Fix CSRF Token Rotation on Privilege Change

**Issue**: In `app/routes/admin/users.py`, privilege change routes (promote, demote, make-owner) set `session["csrf_token"]` (singular) instead of properly updating `session["csrf_tokens"]` (plural sliding window list).

**File**: `app/routes/admin/users.py` (lines 145, 182, 230)

**Current Code**:
```python
# Incorrect - sets singular token, not updating sliding window
session["csrf_token"] = secrets.token_hex(32)
```

**Fixed Implementation**:
```python
from app.csrf import generate_csrf_token

# In promote_user():
session["csrf_tokens"] = [generate_csrf_token()]  # Reset sliding window

# Same for demote_user() and make_owner()
```

**Alternative** (if `generate_csrf_token()` relies on request context):
```python
# In app/csrf.py, add exportable function:
def reset_csrf_tokens() -> str:
    """Generate new token and reset sliding window."""
    new_token = secrets.token_hex(32)
    session["csrf_tokens"] = [new_token]
    return new_token

# In users.py:
from app.csrf import reset_csrf_tokens
# ...
new_token = reset_csrf_tokens()
```

**Verification**:
- Run test: `pytest tests/test_csrf.py -v`
- Verify sliding window still works after privilege change

---

### 2.3 Add Request-Level Caching to Expensive Filters

**Issue**: `reading_time` and `markdown_safe` filters lack request-level caching via Flask `g` object, unlike `post_image_url` which has it.

**File**: `app/__init__.py` (template filter definitions)

**Implementation for `reading_time` filter**:
```python
@app.template_filter("reading_time")
def reading_time_filter(text: str) -> str:
    if not text:
        return "1 min read"
    
    # Request-level caching
    if has_request_context():
        if not hasattr(g, "_reading_time_cache"):
            g._reading_time_cache = {}
        text_hash = hash(text)
        if text_hash in g._reading_time_cache:
            return g._reading_time_cache[text_hash]
    
    words = len(text.split())
    minutes = max(1, round(words / 200))
    result = f"{minutes} min read"
    
    if has_request_context():
        g._reading_time_cache[text_hash] = result
    
    return result
```

**Implementation for `markdown_safe` filter**:
```python
@app.template_filter("markdown_safe")
def markdown_safe_filter(text: str) -> str:
    if not text:
        return ""
    
    # Request-level caching
    if has_request_context():
        if not hasattr(g, "_markdown_cache"):
            g._markdown_cache = {}
        text_hash = hash(text)
        if text_hash in g._markdown_cache:
            return g._markdown_cache[text_hash]
    
    html = markdown.markdown(text, extensions=["fenced_code", "tables"])
    result = nh3.clean(
        html, tags=MARKDOWN_ALLOWED_TAGS, attributes=MARKDOWN_ALLOWED_ATTRIBUTES
    )
    
    if has_request_context():
        g._markdown_cache[text_hash] = result
    
    return result
```

**Also fix `post_image_url` cache key** (line ~210):
```python
# Current (incorrect):
post_id = id(post)  # Python object ID, not database ID

# Fixed:
post_id = post.id  # Use database ID for consistency
```

**Verification**:
- Run existing template filter tests
- Add new tests for caching behavior in `tests/test_filters.py`

---

### 2.4 Fix PostgreSQL Migration Script

**Issue**: DEPLOY.md import SQL script has schema mismatches that will cause migration failures. Refers to non-existent columns.

**File**: `DEPLOY.md` (lines 262-350, import SQL script)

**Schema Mismatches**:

| Table | Import SQL Column | Actual Model Column | Fix |
|-------|-------------------|---------------------|-----|
| `users` | `created_at` | Does NOT exist | Remove from import |
| `site_settings` | `logo_type`, `footer_html`, `created_at` | Has: `theme_preset`, `custom_css_enabled`, `custom_css`, `logo_text`, `updated_at` | Update to match model |
| `page_views` | `ip_address`, `user_agent` | Has: `referrer` | Update to match model |
| `pages` | `content` | Has: `body` | Change to `body` |

**Fixed Import SQL** (replace lines 262-350 in DEPLOY.md):

```sql
-- migration_temp/import_postgresql.sql
-- Run with: psql -U blog_user -d blog -f import_postgresql.sql

-- Disable triggers for initial import
SET session_replication_role = replica;

-- Users
\COPY users(id, username, password_hash, is_admin) FROM 'users.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users)) FROM users;

-- Posts
\COPY posts(id, title, slug, body, summary, image, created_at, updated_at, published, published_at, scheduled_publish_at, newsletter_sent_at, newsletter_attempts) FROM 'posts.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('posts_id_seq', (SELECT MAX(id) FROM posts)) FROM posts;

-- Tags
\COPY tags(id, name, slug, created_at) FROM 'tags.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('tags_id_seq', (SELECT MAX(id) FROM tags)) FROM tags;

-- Post-Tags relationship
\COPY post_tags(post_id, tag_id) FROM 'post_tags.csv' WITH (FORMAT csv, NULL 'NULL');

-- Subscribers
\COPY subscribers(id, email, token, confirmed, created_at, expires_at, unsubscribed_at) FROM 'subscribers.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('subscribers_id_seq', (SELECT MAX(id) FROM subscribers)) FROM subscribers;

-- Page Views
\COPY page_views(id, post_id, referrer, created_at) FROM 'page_views.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('page_views_id_seq', (SELECT MAX(id) FROM page_views)) FROM page_views;

-- Share Events
\COPY share_events(id, post_id, platform, created_at) FROM 'share_events.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('share_events_id_seq', (SELECT MAX(id) FROM share_events)) FROM share_events;

-- Admin Sessions
\COPY admin_sessions(id, user_id, session_id, ip_address, user_agent, created_at, last_activity) FROM 'admin_sessions.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('admin_sessions_id_seq', (SELECT MAX(id) FROM admin_sessions)) FROM admin_sessions;

-- Site Settings
\COPY site_settings(id, theme_preset, custom_css_enabled, custom_css, logo_text, updated_at) FROM 'site_settings.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('site_settings_id_seq', (SELECT MAX(id) FROM site_settings)) FROM site_settings;

-- Post Revisions
\COPY post_revisions(id, post_id, title, slug, body, summary, created_at, author_id) FROM 'post_revisions.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('post_revisions_id_seq', (SELECT MAX(id) FROM post_revisions)) FROM post_revisions;

-- Pages
\COPY pages(id, title, slug, body, published, created_at, updated_at) FROM 'pages.csv' WITH (FORMAT csv, NULL 'NULL');
SELECT setval('pages_id_seq', (SELECT MAX(id) FROM pages)) FROM pages;

-- Re-enable triggers
RESET session_replication_role;

-- [Rest of FTS migration code remains the same...]
```

**Also update CSV export section** (lines 214-240) to match actual schema:
```bash
sqlite3 ../instance/blog.db << 'EOF'
.mode csv
.headers on
.output users.csv
SELECT id, username, password_hash, is_admin FROM users;
# ... update all SELECT statements to match actual columns ...
EOF
```

**Verification**:
1. Create test SQLite database with sample data
2. Export using updated CSV statements
3. Create PostgreSQL database
4. Run Flask-Migrate to create schema
5. Import CSV using fixed SQL script
6. Verify data integrity

---

### 2.5 Add Coverage Reporting to CI

**Issue**: `pytest.ini` configures coverage, but GitHub Actions workflow doesn't run it. No coverage threshold enforcement.

**File**: `.github/workflows/test.yml`

**Current Workflow** (likely):
```yaml
- name: Run tests
  run: |
    pip install -r requirements-dev.txt
    ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ --ignore=tests/e2e -v
```

**Updated Workflow**:
```yaml
- name: Install dependencies
  run: |
    pip install -r requirements-dev.txt
    pip install pytest-cov

- name: Run tests with coverage
  run: |
    ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ --ignore=tests/e2e -v \
      --cov=app \
      --cov-report=term-missing \
      --cov-report=xml \
      --cov-fail-under=80

- name: Upload coverage to Codecov (optional)
  uses: codecov/codecov-action@v4
  with:
    file: ./coverage.xml
    fail_ci_if_error: false
```

**Verification**:
- Push to GitHub, verify workflow runs
- Check that coverage < 80% fails the build

---

## Priority 3: Medium Priority

### 3.1 Add Post Revision Limits

**Issue**: Revisions grow unbounded. No max revisions per post, no cleanup mechanism.

**Files Affected**:
- `app/config.py` (add config option)
- `app/models.py` (PostRevision model)
- `app/routes/admin/posts.py` (`_save_revision()` function)
- `app/cli.py` (add cleanup command)

**Implementation**:

**`config.toml`** (add to `[app]` section):
```toml
[app]
# ... existing settings ...
max_revisions_per_post = 10  # 0 = unlimited
```

**`app/config.py`** (add to config loading):
```python
MAX_REVISIONS_PER_POST = int(_config["app"].get("max_revisions_per_post", 10))
```

**`app/routes/admin/posts.py`** (update `_save_revision()`):
```python
def _save_revision(post, author_id: int) -> None:
    """Save current post state as revision, enforcing max revisions limit."""
    revision = PostRevision(
        post_id=post.id,
        title=post.title,
        slug=post.slug,
        body=post.body,
        summary=post.summary,
        author_id=author_id,
    )
    db.session.add(revision)
    
    # Enforce max revisions limit
    max_revisions = current_app.config["MAX_REVISIONS_PER_POST"]
    if max_revisions > 0:
        # Delete oldest revisions beyond limit
        old_revisions = (
            db.session.execute(
                select(PostRevision)
                .filter_by(post_id=post.id)
                .order_by(PostRevision.created_at.desc())
                .offset(max_revisions)
            )
            .scalars()
            .all()
        )
        for rev in old_revisions:
            db.session.delete(rev)
```

**`app/cli.py`** (add cleanup command):
```python
@cli.command("cleanup-revisions")
def cleanup_revisions():
    """Delete old revisions beyond max_revisions_per_post limit."""
    max_rev = current_app.config["MAX_REVISIONS_PER_POST"]
    if max_rev <= 0:
        click.echo("Unlimited revisions configured, no cleanup needed.")
        return
    
    # ... implementation ...
    click.echo(f"Cleaned up {deleted} old revisions.")
```

**Verification**:
- Create test with >10 revisions, verify oldest gets deleted
- Run `flask cleanup-revisions` command

---

### 3.2 Add Site Settings Double-Checked Locking

**Issue**: `_get_cached_settings()` in `app/context_processors.py` uses threading lock but doesn't do slow path outside lock (not true double-checked locking).

**File**: `app/context_processors.py`

**Current Code**:
```python
def _get_cached_settings():
    now = time.monotonic()
    with _SITE_SETTINGS_LOCK:  # Lock always acquired
        if (_SITE_SETTINGS_CACHE["data"] is not None
                and (now - _SITE_SETTINGS_CACHE["timestamp"]) < _SITE_SETTINGS_TTL):
            return _SITE_SETTINGS_CACHE["data"]
        # Slow path inside lock (should be outside)
        settings = SiteSettings.get_instance()
        # ...
```

**Fixed Implementation** (match `app/cache.py` pattern):
```python
def _get_cached_settings():
    ttl = current_app.config.get("SITE_SETTINGS_TTL", 300)
    
    # Fast path: check without lock
    if _SITE_SETTINGS_CACHE["data"] is not None:
        now = time.monotonic()
        if (now - _SITE_SETTINGS_CACHE["timestamp"]) < ttl:
            return _SITE_SETTINGS_CACHE["data"]
    
    # Slow path: query outside lock
    settings = SiteSettings.get_instance()
    result = {settings.theme_preset, settings.custom_css_enabled, ...}
    
    # Acquire lock and double-check
    with _SITE_SETTINGS_LOCK:
        now = time.monotonic()
        if (_SITE_SETTINGS_CACHE["data"] is None
                or (now - _SITE_SETTINGS_CACHE["timestamp"]) >= ttl):
            _SITE_SETTINGS_CACHE["data"] = result
            _SITE_SETTINGS_CACHE["timestamp"] = now
            return result.copy()
        return _SITE_SETTINGS_CACHE["data"].copy()
```

---

### 3.3 Add FTS5 Search Fallback Logic Fix

**Issue**: `search()` returns `[]` for both "FTS unavailable" and "no results found". Caller can't distinguish, so LIKE fallback triggers unnecessarily.

**File**: `app/search.py` and `app/routes/public.py`

**Fix for `search()` function**:
```python
def search(query: str) -> tuple[list[tuple[int, int]], bool]:
    """Search posts using FTS5.
    
    Returns:    - results: List of (post_id, rank) tuples
        - fts_available: True if FTS5 is available
    """
    fts_available = _check_fts_enabled()
    
    if not fts_available:
        return [], False
    
    # ... FTS query logic ...
    
    if not results:
        return [], True  # FTS available but no results
    
    return results, True
```

**Update caller in `app/routes/public.py`**:
```python
# Old logic:
# post_results = _fts_search(query)
# if post_results:
#     use FTS
# else:
#     LIKE fallback  # Triggered on BOTH "FTS down" and "no results"

# New logic:
post_results, fts_available = _fts_search(query)
if post_results:
    # Use FTS results
    pass
elif not fts_available:
    # FTS is down, use LIKE fallback
    pass
else:
    # FTS available but no results - don't use fallback
    pass
```

---

### 3.4 Add CSS Size Limit Validation

**Issue**: `custom_css` field in `SiteSettings` model is `db.Text` with no length validation. Could store extremely large CSS.

**Files Affected**:
- `app/routes/admin/settings.py`
- `app/models.py` (optional: add model-level validation)

**Implementation**:

**`app/routes/admin/settings.py`** (in custom CSS update):
```python
MAX_CSS_LENGTH = 50000  # 50KB max

@app.route("/settings/theme", methods=["POST"])
@admin_required
def update_theme():
    # ...
    custom_css = request.form.get("custom_css", "")
    if len(custom_css) > MAX_CSS_LENGTH:
        flash(f"Custom CSS too large (max {MAX_CSS_LENGTH} characters)", "error")
        return redirect(url_for("admin.settings"))
    
    # Proceed with update
    settings.custom_css = custom_css
    # ...
```

---

## Priority 4: Low Priority

### 4.1 Create Asset Update Script

**Issue**: No automated way to update self-hosted assets (marked.js, Prism.js, fonts).

**Create**: `scripts/update-assets.sh`

```bash
#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATIC_DIR="$PROJECT_DIR/app/static"

echo "Updating third-party assets..."

# Update marked.js
echo "Updating marked.js..."
curl -L "https://cdn.jsdelivr.net/npm/marked/marked.min.js" \
  -o "$STATIC_DIR/js/lib/marked.min.js"

# Update Prism.js
echo "Updating Prism.js..."
curl -L "https://cdn.jsdelivr.net/npm/prismjs/prism.min.js" \
  -o "$STATIC_DIR/js/lib/prism.min.js"

# Update Prism languages
echo "Updating Prism languages..."
curl -L "https://cdn.jsdelivr.net/npm/prismjs/components/prism-core.min.js" \
  -o "$STATIC_DIR/js/lib/prism.min.js"
# ... more languages ...

echo "Assets updated successfully!"
```

---

### 4.2 Add Scheduler Configuration Options

**Issue**: No way to disable scheduler on multi-instance deployments. No persistent job store.

**Implementation**:

**`config.toml`** (add):
```toml
[app]
# ... existing ...
scheduler_enabled = true  # Set to false on secondary instances
```

**`run.py`** (update):
```python
def _get_scheduler():
    global _scheduler
    if _scheduler is None:
        from app.config import SCHEDULER_ENABLED
        if not SCHEDULER_ENABLED:
            return None
        _scheduler = init_scheduler(app)
    return _scheduler
```

---

## Timeline and Milestones

### Week 1 (Critical Items)
- [ ] Day 1-2: Clean test uploads, add cleanup fixture
- [ ] Day 3-4: Implement nginx rate limiting, test
- [ ] Day 5: Fix newsletter return value, fix `make_owner()` race condition

### Week 2 (High Priority)
- [ ] Day 1-2: Add linting/formatting, CI integration
- [ ] Day 3: Fix CSRF rotation, add filter caching
- [ ] Day 4-5: Fix PostgreSQL migration script, test migration

### Week 3 (Medium Priority)
- [ ] Day 1: Add revision limits
- [ ] Day 2: Fix site settings caching
- [ ] Day 3: Fix FTS5 fallback logic
- [ ] Day 4: Add CSS size validation

### Week 4 (Low Priority + Testing)
- [ ] Day 1-2: Create asset update script
- [ ] Day 3: Add scheduler config options
- [ ] Day 4-5: Full regression testing, performance benchmarking

---

## Verification Checklist

### Before Each Change
- [ ] Read relevant AGENTS.md section
- [ ] Run tests before changes: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ --ignore=tests/e2e -v`
- [ ] Create feature branch

### After Each Change
- [ ] Run full test suite
- [ ] Run linting (if added): `ruff check app/ tests/`
- [ ] Check coverage hasn't dropped
- [ ] Test manually (especially admin routes)
- [ ] Update relevant documentation

### Before Production Deployment
- [ ] All critical items completed
- [ ] nginx rate limiting tested and verified
- [ ] Test uploads cleaned (verify `ls app/static/uploads/`)
- [ ] PostgreSQL migration tested (if migrating)
- [ ] Security checklist from DEPLOY.md Section 10 completed
- [ ] Load testing completed (if high traffic expected)

---

## Summary of Changes

| Priority | Item | Est. Hours | Files Affected |
|----------|------|------------|----------------|
| Critical | Clean test uploads | 1 | `tests/conftest.py` |
| Critical | nginx rate limiting | 2 | `nginx/conf.d/blog.conf` |
| Critical | Newsletter return value | 3 | `app/email.py`, `app/scheduler.py` |
| Critical | `make_owner()` race condition | 2 | `app/routes/admin/users.py` |
| High | Linting/formatting | 4 | `pyproject.toml`, `.pre-commit-config.yaml`, CI |
| High | CSRF rotation fix | 1 | `app/routes/admin/users.py`, `app/csrf.py` |
| High | Filter caching | 2 | `app/__init__.py` |
| High | PostgreSQL migration | 4 | `DEPLOY.md` |
| High | Coverage in CI | 1 | `.github/workflows/test.yml` |
| Medium | Revision limits | 3 | `app/config.py`, `app/models.py`, `app/routes/admin/posts.py` |
| Medium | Site settings cache | 2 | `app/context_processors.py` |
| Medium | FTS5 fallback fix | 2 | `app/search.py`, `app/routes/public.py` |
| Medium | CSS size limit | 1 | `app/routes/admin/settings.py` |
| Low | Asset update script | 2 | `scripts/update-assets.sh` |
| Low | Scheduler config | 2 | `config.toml`, `run.py` |

**Total Estimated Time**: ~31 hours

---

## Appendix: Testing Strategy

### Unit Tests to Add
- `tests/test_filters.py`: Test request-level caching for `reading_time`, `markdown_safe`
- `tests/test_newsletter.py`: Test `send_newsletter()` return value semantics
- `tests/test_users.py`: Test `make_owner()` race condition fix
- `tests/test_csrf.py`: Test sliding window after privilege change

### Integration Tests to Add
- Test nginx rate limiting with actual HTTP requests
- Test PostgreSQL migration end-to-end
- Test revision limit enforcement

### Manual Testing Checklist
- [ ] Newsletter send with partial failure (some emails fail)
- [ ] Ownership transfer (verify no admin gap)
- [ ] Rate limiting (trigger 429 response)
- [ ] Template filter caching (verify cache hits)
- [ ] PostgreSQL migration (full process)
