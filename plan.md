# Improvement Plan

All items from Waves 1-8 have been completed. This document outlines the consolidated plan for future improvements.

---

## Completed Waves Reference

### Wave 1-8 Summary (COMPLETED)

| Wave | Focus | Items |
|------|-------|-------|
| Wave 1 | Critical Bugs | 5 items (SMTP, footer cache, CSS variables, admin preview) |
| Wave 2 | Security & Session | 4 items (CSRF logout, DB query, share allowlist, List-Unsubscribe) |
| Wave 3 | Performance | 7 items (N+1 queries, FTS fallback, media caching, footer cache) |
| Wave 4 | Code Quality | 8 items (slug return, error blocks, regex, indexes, TOCTOU) |
| Wave 5 | Multi-Admin | 3 items (promote/demote, ownership transfer, type hints) |
| Wave 6 | UI/Template | 12 items (login base, image verification, breadcrumbs, mobile) |
| Wave 7 | JavaScript & Dead Code | 9 items (dynamic imports, share tracking, CSS cleanup, macros) |
| Wave 8 | Minor Improvements | 14 items (settings singleton, relationships, session expiry) |

**Total: 297 tests passing**

---

## Future Waves Overview

| Wave | Focus | Priority | Items | Est. Effort |
|------|-------|----------|-------|-------------|
| **Wave A** | Quick Security Fixes | High | 3 | ~2 hours |
| **Wave B** | Critical Performance | Critical | 5 | ~3 hours |
| **Wave C** | Medium Performance | Medium | 8 | ~8-10 hours |
| **Wave D** | Code Quality | Medium | 4 | ~5-7 hours |
| **Wave E** | Feature Completeness | Medium | 6 | ~20-24 hours |
| **Wave F** | Developer Experience | Medium | 5 | ~13-15 hours |
| **Wave G** | UI/UX | Low | 5 | ~8-10 hours |
| **Wave H** | Production Operations | Medium | 5 | ~16-18 hours |
| **Wave I** | Testing Infrastructure | Low | 3 | ~9-11 hours |

**Grand Total: ~84-100 hours**

---

## Wave A: Quick Security Fixes

These items are low-effort, high-impact security improvements.

### A1: Remove `last_newsletter_send` from Health Check

**Priority**: High
**Files**: `app/routes/public.py:783-793`
**Effort**: Low — 30 minutes

**Description**:
The `/health` endpoint exposes `last_newsletter_send` timestamp, revealing newsletter configuration. Remove this field while keeping scheduler status.

**Implementation**:
```python
# Remove last_newsletter_send from the health check response dict
# Keep: database, scheduler, search checks
```

---

### A2: CSRF Token Rotation on Privilege Changes

**Priority**: High
**Files**: `app/routes/admin/users.py`
**Effort**: Low — 30 minutes

**Description**:
Rotate CSRF token when user privileges change to prevent token reuse after demotion.

**Implementation**:
Add to handlers: `promote_user`, `demote_user`, `make_owner`, `change_password`
```python
# After successful privilege change:
session["csrf_token"] = secrets.token_hex(32)
```

---

### A3: Constant-Time Login Delay

**Priority**: High
**Files**: `app/routes/admin/auth.py:29-53`
**Effort**: Low — 30 minutes

**Description**:
Equalize timing between successful and failed login to prevent timing attacks.

**Implementation**:
```python
# Add delay before password check in failed login path
time.sleep(0.05)  # Adjust based on measured successful path duration
```

---

## Wave B: Critical Performance Fixes

These items address critical performance issues that affect scalability.

### B1: O(n²) Newsletter String Replacement

**Priority**: Critical
**Files**: `app/email.py:168-173`
**Effort**: Low — 1 hour

**Description**:
Per-subscriber `str.replace()` on full HTML body. With 10,000 subscribers, this creates ~20,000 full-string scans.

**Current Code**:
```python
for i, sub in enumerate(subscribers, 1):
    unsub_url = unsub_url_base + sub.token
    html = pre_rendered_html.replace(unsub_url_base + "TOKEN", unsub_url)
    text = pre_rendered_text.replace(unsub_url_base + "TOKEN", unsub_url)
```

**Implementation**:
Use `str.format()` or f-string with placeholder in template:
```python
# Template: <a href="{unsubscribe_url}">Unsubscribe</a>
html = pre_rendered_html.format(unsubscribe_url=unsub_url)
```
Requires updating email templates to use `{unsubscribe_url}` placeholder instead of `TOKEN`.

---

### B2: N+1 Query in Bulk Operations

**Priority**: Critical
**Files**: `app/routes/admin/posts.py:478-552`
**Effort**: Low — 15 minutes

**Description**:
The `bulk_operations()` query does not eager load tags. Accessing `post.tags` in loop triggers separate query per post.

**Implementation**:
```python
from sqlalchemy.orm import joinedload

posts = (
    db.session.execute(
        select(Post).filter(Post.id.in_(valid_ids)).options(joinedload(Post.tags))
    ).scalars().all()
)
```

---

### B3: N+1 Query in Tag Creation

**Priority**: Critical
**Files**: `app/routes/admin/helpers/tags.py:38-57`
**Effort**: Low — 30 minutes

**Description**:
`_get_or_create_tags()` performs separate DB query for each tag name inside loop.

**Implementation**:
```python
def _get_or_create_tags(names: list[str]) -> list[Tag]:
    if not names:
        return []

    slugs = [Tag.generate_slug(name) for name in names]
    existing = (
        db.session.execute(select(Tag).filter(Tag.slug.in_(slugs))).scalars().all()
    )
    existing_by_slug = {tag.slug: tag for tag in existing}

    tags = []
    for name in names:
        slug = Tag.generate_slug(name)
        tag = existing_by_slug.get(slug)
        if not tag:
            tag = Tag(name=name, slug=slug)
            db.session.add(tag)
        tags.append(tag)

    return tags
```

---

### B4: Blocking `time.sleep()` in Email Retry

**Priority**: Critical
**Files**: `app/email.py:104-124`
**Effort**: Low — 30 minutes

**Description**:
`time.sleep()` blocks APScheduler thread during exponential backoff, blocking other scheduler tasks.

**Implementation**:
Short-term: Remove sleep for transient failures and let next scheduler run handle retry. Long-term: Consider async migration.

---

### B5: All Posts Loaded Into Memory for Newsletter

**Priority**: Critical
**Files**: `app/scheduler.py:76-89`
**Effort**: Low — 30 minutes

**Description**:
Uses `.all()` which loads every matching post into memory. Subscriber iteration correctly uses `yield_per(500)`.

**Implementation**:
```python
posts = (
    db.session.execute(
        select(Post).filter(...).order_by(Post.published_at.desc())
    ).scalars().yield_per(100)  # Add yield_per like subscribers
)
```

---

## Wave C: Medium Priority Performance

### C1: Render-Blocking JavaScript

**Priority**: Medium
**Files**: `app/templates/base.html:129-131`, `app/templates/admin/base.html:148-150`
**Effort**: Low — 30 minutes

**Description**:
Prism (40KB) and main.js loaded synchronously, blocking page render.

**Implementation**:
Add `defer` attribute to all script tags:
```html
<script defer src="{{ url_for('static', filename='js/prism.min.js') }}"></script>
<script defer src="{{ url_for('static', filename='js/prism-languages.js') }}"></script>
<script defer src="{{ url_for('static', filename='js/main.js') }}"></script>
```

---

### C2: Route-Based Code Splitting in main.js

**Priority**: Medium
**Files**: `app/static/js/main.js:1-31`
**Effort**: Medium — 3-4 hours

**Description**:
All 15 modules loaded on every page regardless of need. Each dynamic import is a separate HTTP request.

**Implementation**:
```javascript
const ROUTE_MODULES = {
    '/admin/': ['./shared/utils.js', './shared/modal.js', './admin/shortcuts.js', './admin/bulk.js'],
    '/admin/posts': ['./shared/utils.js', './admin/editor.js'],
    // ... other routes
};

function getModulesForPath(path) {
    for (const [route, modules] of Object.entries(ROUTE_MODULES)) {
        if (path.startsWith(route)) return modules;
    }
    return ['./shared/utils.js', './shared/dark-mode.js', './public/share.js'];
}

document.addEventListener("DOMContentLoaded", () => {
    const modules = getModulesForPath(window.location.pathname);
    modules.forEach(m => loadModule(m, fn => fn()));
});
```

---

### C3: `reading_time` Filter Called Repeatedly

**Priority**: Medium
**Files**: `app/__init__.py:149-155`, multiple templates
**Effort**: Medium — 2 hours

**Description**:
O(n) text operation performed per post, called multiple times per post in templates.

**Implementation**:
Add as cached attribute on Post model:
```python
# In Post model
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self._reading_time = None

@property
def reading_time(self) -> str:
    if self._reading_time is None:
        words = len((self.body or '').split())
        minutes = max(1, round(words / 200))
        self._reading_time = f"{minutes} min read"
    return self._reading_time
```

---

### C4: `post_image_url` Does File I/O Every Call

**Priority**: Medium
**Files**: `app/__init__.py:163-169`, `app/templates/post.html`
**Effort**: Medium — 1 hour

**Description**:
`os.path.isfile()` called 3 times for same post's image in post.html (og:image, twitter:image, JSON-LD).

**Implementation**:
Compute once per post in route, pass via context:
```python
# In route
for post in posts:
    post.image_url = post_image_url_filter(post)
```

---

### C5: Theme CSS Regenerated Per Request

**Priority**: Medium
**Files**: `app/templates/base.html:28-32`, `app/templates/admin/base.html:13-17`
**Effort**: Low — 1 hour

**Description**:
`theme_vars.items()` loop generates CSS variables inline on every request.

**Implementation**:
Cache generated CSS string in `_SITE_SETTINGS_CACHE`:
```python
# In context_processors.py
css = '\n'.join(f'--{k}: {v};' for k, v in theme_vars.items() if k != 'name')
```

---

### C6: Archive Re-Sorting in Jinja2

**Priority**: Medium
**Files**: `app/templates/archive.html:19-48`
**Effort**: Low — 15 minutes

**Description**:
Data already sorted in Python (`public.py:184-194`), then re-sorted with `| sort(reverse=True)` in template.

**Implementation**:
Remove `| sort()` calls — data already sorted.

---

### C7: FTS Table Check Cached

**Priority**: Medium
**Files**: `app/search.py:150-156`
**Effort**: Low — 30 minutes

**Description**:
`sqlite_master` query on every search could be cached with 5-minute TTL.

**Implementation**:
```python
_fts_enabled = None  # None = not yet checked, True/False = cached result

def search(query: str) -> list[tuple[int, int]]:
    global _fts_enabled
    if _fts_enabled is None:
        check = db.session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'")
        ).fetchone()
        _fts_enabled = bool(check)
    # ... rest of search
```

---

### C8: Lazy Load Threshold Bug

**Priority**: Medium
**Files**: `app/static/js/shared/lazy-load.js:5`
**Effort**: Low — 15 minutes

**Description**:
Threshold `window.innerHeight * 3` means images within 3x viewport don't get lazy loading.

**Implementation**:
```javascript
if (rect.top > window.innerHeight) {  // Change from * 3 to * 1
```

---

## Wave D: Code Quality

### D1: Complete Type Hint Coverage

**Priority**: Medium
**Files**: Throughout codebase
**Effort**: Medium — 2-3 hours

**Description**:
Type hints inconsistently applied. Some functions lack annotations entirely.

**Affected Areas**:
- `app/routes/admin/posts.py` — several route handlers lack return type annotations
- `app/routes/admin/subscribers.py` — bulk operations lack type hints
- `app/routes/admin/media.py` — `list_media()` and `delete_media()` lack return type annotations

**Implementation**:
Use `from __future__ import annotations` to defer evaluation and avoid circular imports.

---

### D2: Consistent Error Handling Patterns

**Priority**: Medium
**Files**: Throughout codebase
**Effort**: Low — 2-3 hours

**Description**:
Some routes catch specific exceptions while others use bare `except Exception`.

**Affected Areas**:
- `app/search.py` line 43 — `except Exception`
- `app/routes/admin/posts.py` line 261 — `except Exception as e`
- `app/email.py` line 112 — `except Exception`
- `app/routes/admin/helpers/shared.py` line 27 — `except Exception`
- `app/routes/errors.py` line 30 — `except Exception`

**Implementation**:
Replace with specific exceptions:
- File operations: `OSError`, `IOError`, `FileNotFoundError`
- Database: `IntegrityError`, `OperationalError`, `SQLAlchemyError`
- Network: `ConnectionError`, `SMTPServerDisconnected`, `timeout`

---

### D3: Per-Request CSRF Token Rotation

**Priority**: Medium
**Files**: `app/csrf.py`, `app/__init__.py`, templates
**Effort**: Medium — 3-4 hours

**Description**:
CSRF token is session-scoped, not per-request. An obtained token can be reused until logout.

**Implementation**:
Sliding window of 5 valid tokens per session:
1. Store multiple valid tokens in session (sliding window)
2. Check submitted token is in valid set
3. Remove used token after successful validation
4. Rotate token after each successful validation

---

### D4: Helper Module Export Organization

**Priority**: Low
**Files**: `app/routes/admin/helpers/`
**Effort**: Low — 1 hour

**Description**:
Create `__init__.py` in `helpers/` that re-exports common helpers for cleaner imports.

**Implementation**:
```python
# app/routes/admin/helpers/__init__.py
from .slug import _generate_unique_slug, generate_slug
from .tags import _cleanup_orphan_tags
from .images import _detect_image_type, _save_image
# etc.
```

---

## Wave E: Feature Completeness

### E1: REST API for Post/Subscriber Management

**Priority**: Medium
**Files**: New files + templates
**Effort**: Medium — 4-6 hours

**Description**:
Admin panel lacks programmatic API for external integrations.

**Proposed Endpoints**:
```
GET    /api/posts           — List posts (paginated)
GET    /api/posts/<id>      — Get single post
POST   /api/posts           — Create post
PUT    /api/posts/<id>      — Update post
DELETE /api/posts/<id>      — Delete post
GET    /api/subscribers      — List subscribers (paginated)
POST   /api/subscribers      — Create subscriber
DELETE /api/subscribers/<id> — Delete subscriber
GET    /api/stats           — Dashboard stats
```

**Implementation Notes**:
- Require API key authentication (add `API_KEY` env var)
- Return JSON responses
- Use existing model serialization patterns
- Add rate limiting via proxy (same as admin routes)

---

### E2: Password Reset Functionality

**Priority**: Medium
**Files**: `app/routes/admin/auth.py`, templates, email handling
**Effort**: Medium — 4-5 hours

**Description**:
If admin forgets password, direct database access is required to reset.

**Proposed Flow**:
1. `GET /admin/forgot-password` — form to enter username/email
2. `POST /admin/forgot-password` — generate reset token, send email
3. `GET /admin/reset/<token>` — form to enter new password
4. `POST /admin/reset/<token>` — validate token, update password

**Implementation Notes**:
- Store `reset_token` hash in User model (not plaintext)
- Token expires in 1 hour (`reset_token_expires_at`)
- Require password complexity validation (same as user creation)
- Invalidate existing admin sessions after reset

---

### E3: Scheduled Post Management UI

**Priority**: Low
**Files**: `app/routes/admin/posts.py`, templates
**Effort**: Low — 2-3 hours

**Description**:
Editor has scheduling field but no dedicated UI to view/manage scheduled posts.

**Proposed Additions**:
- Dashboard filter: `?status=scheduled` to show only scheduled posts
- Badge indicating "Scheduled for {datetime}" in post list
- Ability to cancel/unschedule from list view

---

### E4: Post Versioning/Revision History

**Priority**: Low
**Files**: New model, `app/routes/admin/posts.py`, templates
**Effort**: Medium — 5-6 hours

**Description**:
No history of post edits is kept. Revision system would track changes.

**Proposed Implementation**:
- `PostRevision` model: `id`, `post_id`, `title`, `slug`, `body`, `summary`, `created_at`, `author_id`
- Save revision on each publish (not on every auto-save draft)
- View revision history at `/admin/posts/<id>/revisions`
- Diff view between revisions
- One-click restore to previous revision

---

### E5: Advanced Search Features

**Priority**: Low
**Files**: `app/search.py`, templates
**Effort**: Low-Medium — 3-4 hours

**Description**:
Search could be improved with:
- Search result highlighting in snippets
- Search analytics (popular queries)
- "Did you mean?" suggestions on no results
- Category/tag filtering in search

---

### E6: Draft Sharing/Preview Links

**Priority**: Low
**Files**: `app/routes/admin/posts.py`, `app/routes/public.py`
**Effort**: Low — 2-3 hours

**Description**:
Currently draft preview requires admin login. Shareable preview link would allow external reviewers.

**Proposed Implementation**:
- Generate signed URL: `/preview/<post_id>?token=<hmac_signature>`
- Token contains expiry timestamp
- Token validated via HMAC of post_id + expiry + SECRET_KEY
- Configurable expiry (default 7 days)

---

## Wave F: Developer Experience

### F1: Comprehensive API Documentation

**Priority**: Medium
**Files**: `docs/api.md` or OpenAPI spec
**Effort**: Medium — 4-5 hours

**Description**:
No formal API documentation exists beyond inline comments.

**Recommended Format**: OpenAPI 3.0 spec in `docs/openapi.yaml`

---

### F2: Development Environment Script

**Priority**: Low
**Files**: `dev.py` or `scripts/dev.sh`
**Effort**: Low — 1 hour

**Description**:
New developers must manually set up virtualenv, env vars, and run migrations.

**Proposed Script**:
```bash
#!/bin/bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config.toml.example config.toml
flask db upgrade
echo "Run: source venv/bin/activate && ADMIN_PASSWORD=... SECRET_KEY=... flask run"
```

---

### F3: Better CLI Commands

**Priority**: Low
**Files**: `app/cli.py` or individual modules
**Effort**: Low — 2-3 hours

**Description**:
Additional useful commands:
- `flask export-data` — Export all posts/subscribers as JSON
- `flask import-data` — Import from JSON
- `flask promote-admin <username>` — CLI admin promotion
- `flask check-integrity` — Run DB integrity check
- `flask seed` — Generate sample data for testing

---

### F4: Test Coverage Improvement

**Priority**: Medium
**Files**: `tests/`
**Effort**: Medium — 4-5 hours

**Description**:
Coverage gaps identified:
- Error handlers (404, 500, 413)
- Backup/restore operations
- FTS LIKE fallback path
- Property-based tests with `hypothesis`
- Integration tests for newsletter flow

---

### F5: Faster Test Suite

**Priority**: Low
**Files**: `tests/conftest.py`
**Effort**: Low — 2-3 hours

**Description**:
Test suite takes ~30 seconds. Optimization opportunities:
- Use `pytest-xdist` for parallel test execution
- Session-scoped database where possible
- Mock time-consuming operations (SMTP, file I/O)
- Reduce unnecessary `db.create_all()` / `db.drop_all()` cycles

---

## Wave G: UI/UX Improvements

### G1: Image Gallery/Lightbox Improvements

**Priority**: Low
**Files**: Templates, `app/static/js/public/lightbox.js`
**Effort**: Low — 2-3 hours

**Description**:
Current lightbox is basic. Improvements:
- Swipe navigation between images in same post
- Image captions from alt text
- Zoom functionality
- Keyboard navigation (left/right arrows)

---

### G2: Better Dashboard Widgets

**Priority**: Low
**Files**: `app/routes/admin/posts.py`, templates
**Effort**: Low — 2-3 hours

**Description**:
Dashboard shows table of posts. Additional widgets:
- Traffic chart (last 30 days)
- Subscriber growth chart
- Top posts by views/shares

---

### G3: Toast Notifications

**Priority**: Low
**Files**: Templates, JS, CSS
**Effort**: Low — 2-3 hours

**Description**:
Currently uses flash messages. Toast notifications would be less intrusive:
- Non-blocking overlay in corner
- Auto-dismiss after 5 seconds
- Stack multiple toasts
- Types: success, error, warning, info

---

### G4: Improved Mobile Editor

**Priority**: Low
**Files**: `app/templates/admin/editor.html`, CSS
**Effort**: Low — 1-2 hours

**Description**:
Post editor is difficult on mobile:
- Larger textarea with mobile-friendly keyboard
- Toggle preview off by default on mobile
- Better datetime picker integration

---

### G5: Better Error Pages

**Priority**: Low
**Files**: `app/templates/errors/`, `app/templates/_error.html`
**Effort**: Low — 1-2 hours

**Description**:
Current error pages could be more helpful:
- 404: Suggest related posts, search box, popular posts
- 500: Apologize, suggest retry, link to home
- Both: Consistent styling with base template

---

## Wave H: Production Operations

### H1: Structured Logging

**Priority**: Medium
**Files**: `app/__init__.py`, throughout codebase
**Effort**: Medium — 3-4 hours

**Description**:
Current logging is basic string formatting. Structured logging (JSON) improves log aggregation.

**Proposed Format**:
```json
{
  "timestamp": "2026-04-21T10:30:00Z",
  "level": "INFO",
  "request_id": "a1b2c3d4",
  "message": "Post published",
  "post_id": 42,
  "user_id": 1
}
```

**Implementation**:
- Use `python-json-logger` or custom formatter
- Add contextual fields via `logging.LoggerAdapter`

---

### H2: Health Check Enhancement

**Priority**: Low
**Files**: `app/routes/public.py`
**Effort**: Low — 1-2 hours

**Description**:
Current `/health` returns basic status. Enhancement options:
- Add configurable `health_check_secret` for detailed status
- Include database query latency
- Include scheduler next run time
- Include cache hit rates

---

### H3: Graceful Shutdown

**Priority**: Medium
**Files**: `run.py`, `app/scheduler.py`
**Effort**: Medium — 3-4 hours

**Description**:
On SIGTERM, the app should:
- Stop accepting new requests
- Wait for in-flight requests to complete
- Stop scheduler (finish current newsletter send)
- Close database connections

**Implementation**:
```python
signal.signal(signal.SIGTERM, handler)  # In run.py
# Set shutdown event, scheduler pauses
# ASGI supports lifespan protocol
```

---

### H4: PostgreSQL Migration Guide

**Priority**: Low
**Files**: `DEPLOY.md`, `alembic/`
**Effort**: Medium — 4-5 hours

**Description**:
DEPLOY.md documents PostgreSQL path but untested. Full migration guide needed.

**Contents**:
- Step-by-step migration process
- Required changes to config
- FTS5 → PostgreSQL full-text search migration
- Known limitations (SQLite-specific features)

---

### H5: Docker Compose Production Profile

**Priority**: Low
**Files**: `docker-compose.yml`
**Effort**: Medium — 4-5 hours

**Description**:
Production profile could include:
- Nginx reverse proxy
- Gunicorn/uWSGI workers
- Health checks
- Log aggregation
- Backup automation

---

## Wave I: Testing Infrastructure

### I1: Property-Based Testing

**Priority**: Low
**Files**: `tests/`
**Effort**: Low — 2-3 hours

**Description**:
Add `hypothesis` for property-based testing:
- Slug generation edge cases
- Email validation boundaries
- Password complexity enforcement
- Markdown sanitization

---

### I2: End-to-End Browser Tests

**Priority**: Low
**Files**: `tests/e2e/` (new)
**Effort**: Medium — 5-6 hours

**Description**:
Add Playwright-based browser tests:
- Admin login flow
- Post creation and publishing
- Newsletter subscription flow
- Mobile responsiveness

---

### I3: Performance Benchmarks

**Priority**: Low
**Files**: `tests/benchmarks/`
**Effort**: Low — 2-3 hours

**Description**:
Add benchmark tests to catch performance regressions:
- Search query time (FTS5 vs LIKE fallback)
- Newsletter send time per subscriber
- Dashboard page load time
- Database query counts per request

---

## Low Priority Items

These items have minimal impact and can be addressed incidentally:

| Item | Files | Effort | Description |
|------|-------|--------|-------------|
| L1 | `app/routes/admin/newsletter.py:49-51` | 5 min | Redundant admin user query (use `current_user`) |
| L2 | `app/scheduler.py:94-98` | 15 min | Redundant COUNT query before newsletter |
| L3 | `app/static/js/shared/utils.js:148` | 5 min | 10ms scroll throttle too aggressive (use 50-100ms) |
| L4 | `app/scheduler.py:293-299` | 5 min | Scheduler runs every minute (change to 5 min) |
| L5 | `app/static/css/style.css:150-151` | 30 min | `backdrop-filter: blur()` GPU intensive |
| L6 | `app/templates/_sidebar.html:14,17` | 5 min | Redundant `tag_counts.get()` call |
| L7 | `app/templates/post.html:4,6,10,18` | 5 min | `truncate` called 4x for same post |

---

## Parallelization Strategy

Waves are organized to enable parallel execution by sub-agents:

**Phase 1 (Can run in parallel)**:
- Wave A: Quick Security Fixes (3 items, ~2 hours)
- Wave B: Critical Performance (5 items, ~3 hours)

**Phase 2 (Can run in parallel)**:
- Wave C: Medium Performance (8 items, ~8-10 hours)
- Wave D: Code Quality (4 items, ~5-7 hours)

**Phase 3 (Feature work, can run in parallel)**:
- Wave E: Feature Completeness (6 items, ~20-24 hours)
- Wave F: Developer Experience (5 items, ~13-15 hours)
- Wave G: UI/UX (5 items, ~8-10 hours)

**Phase 4 (Operations, can run in parallel)**:
- Wave H: Production Operations (5 items, ~16-18 hours)
- Wave I: Testing Infrastructure (3 items, ~9-11 hours)

**Incidental**:
- Low Priority Items (L1-L7): Address when touching relevant code

---

## Notes

1. **Wave B Items B2 and B3** are quick wins that cause real N+1 query overhead on every bulk/tag operation — fix immediately when starting Wave B.

2. **Wave E Item E2 (Password Reset)** requires email infrastructure. Consider whether manual DB reset process is sufficient before implementing.

3. **Wave H Item H1 (Structured Logging)** depends on deployment log aggregation infrastructure.

4. **Wave H Item H4 (PostgreSQL Migration)** is low priority since SQLite with WAL handles most production loads well.

5. All changes should maintain the 297 passing tests and follow existing code conventions.

---

## Testing

Run tests after each wave:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-21 | Consolidated plan created from plan.md, plan2.md, plan3.md, plan4.md |