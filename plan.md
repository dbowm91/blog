# Improvement Plan

Consolidated from all plan files. Waves 1-9 were completed in previous sessions.

---

## Summary of Remaining Items

| Wave | Category | Items | Status |
|------|----------|-------|--------|
| ~~1~~ | ~~Critical Bugs~~ | 9 | ✅ Completed |
| ~~2~~ | ~~Security Fixes~~ | 10 | ✅ Completed |
| ~~3~~ | ~~Exception Handling~~ | 6 | ✅ Completed |
| ~~4~~ | ~~Performance~~ | 15 | ✅ Completed |
| ~~5~~ | ~~Code Quality~~ | 6 | ✅ Completed |
| ~~6~~ | ~~Documentation~~ | 7 | ✅ Completed |
| ~~7~~ | ~~New Features~~ | 18 | ✅ Completed |
| ~~8~~ | ~~Developer Experience~~ | 9 | ✅ Completed |
| ~~10~~ | ~~Critical Security~~ | 4 | ✅ Completed |
| ~~11~~ | ~~Code Quality~~ | 4 | ✅ Completed |
| ~~12~~ | ~~Performance~~ | 5 | ✅ Completed |
| ~~13~~ | ~~Security Hardening~~ | 2 | ✅ Completed |
| ~~14~~ | ~~Module Refactoring~~ | 1 | ✅ Completed |

---

## Wave 10: Critical Security

**Items that fix security vulnerabilities or resource leaks.**

### 10.1 XSS - Unescaped User Content in Templates

**Severity**: Critical — Cross-site scripting vulnerability

**Problem**: `tag.name`, `page.title`, and `post.title` are rendered without the `| escape` filter in multiple templates.

**Locations**:
- `app/templates/tag.html:3,4,10,14` — `{{ tag.name }}` without escape
- `app/templates/page.html:3,4,10,14` — `{{ page.title }}` without escape
- `app/templates/archive.html:37` — `{{ post.title }}` without escape
- `app/templates/_sidebar.html:16` — `{{ post.title }}` without escape

**Fix**: Add `| escape` filter to all user-generated content.

---

### 10.2 Missing CSRF Protection on Subscribe Form

**Severity**: Critical — CSRF vulnerability

**Problem**: The `/subscribe` POST endpoint does not validate a CSRF token.

**Location**: `app/routes/public.py:401-467`

**Fix**: Add CSRF token validation to the subscribe route:
```python
from app.csrf import validate_csrf_token

if not validate_csrf_token():
    flash("Invalid request. Please try again.", "error")
    return redirect(url_for("public.subscribe"))
```
Add hidden CSRF token field to `subscribe.html` form.

---

### 10.3 SMTP Connection Leak in _connect_smtp()

**Severity**: Critical — Resource leak

**Problem**: If `starttls()` or the second `ehlo()` fails in `_connect_smtp()`, the `server` object is never closed.

**Location**: `app/email.py:65-78`

**Fix**: Use try/finally to ensure cleanup even on failure.

---

### 10.4 Orphan Lock Files on fcntl Failure

**Severity**: Critical — File system pollution, scheduler failures

**Problem**: When `fcntl.flock()` raises `OSError`, the orphan lock file remains on disk.

**Locations**:
- `app/scheduler.py:52-62` (send_newsletter)
- `app/scheduler.py:127-138` (cleanup_expired_subscribers)
- `app/scheduler.py:178-189` (publish_scheduled_posts)

**Fix**: Delete the orphan lock file in the except block after flock failure.

---

## Wave 11: Code Quality

**High priority code quality improvements.**

### 11.1 N+1 Query in Archive Route

**Severity**: High — Performance

**Problem**: The `archive()` route loads ALL published posts at once into memory.

**Location**: `app/routes/public.py:117-148`

**Fix**: Implement pagination for the archive page.

---

### 11.2 Duplicate Slug Generation Code

**Severity**: Medium — Code duplication

**Problem**: Nearly identical `_generate_unique_slug()` implementations in `posts.py` and `pages.py`.

**Locations**:
- `app/routes/admin/helpers/posts.py:30-44`
- `app/routes/admin/pages.py:15-29`

**Fix**: Consolidate into a single helper in `app/routes/admin/helpers/slug.py`.

---

### 11.3 Silent OperationalError in Context Processors

**Severity**: Low — Hidden failures

**Problem**: `OperationalError` exceptions are silently swallowed in `inject_theme()` and `inject_footer_data()`.

**Locations**:
- `app/context_processors.py:174`
- `app/context_processors.py:200`

**Fix**: Add logging before returning fallback.

---

### 11.4 TOCTOU Race in Footer Cache

**Severity**: Low — Race condition

**Problem**: `_get_footer_data()` has a time-of-check-to-time-of-use race between lock release and re-acquire.

**Location**: `app/context_processors.py:62-105`

**Fix**: Simplify to hold lock for entire operation, or accept minor redundancy (current behavior is safe, just wasteful).

---

## Wave 12: Performance

**Query optimization and caching improvements.**

### 12.1 Pre-render Newsletter Template

**Problem**: Template rendered individually for each subscriber (O(n) template renders).

**Location**: `app/email.py:81-104`

**Fix**: Pre-render once and substitute per-subscriber unsubscribe token.

---

### 12.2 Fix `len(subscribers)` in Newsletter Loop

**Problem**: `len(subscribers)` on a generator causes it to be consumed.

**Location**: `app/scheduler.py`

**Fix**: Pre-query subscriber count with `func.count()` before the loop.

---

### 12.3 Cache FTS Table Existence Check

**Problem**: `sqlite_master` query runs on every search request.

**Location**: `app/search.py`

**Fix**: Add module-level `_fts_available` flag that caches the result.

---

### 12.4 Add LIMIT to LIKE Fallback

**Problem**: LIKE fallback has no LIMIT, can scan all posts.

**Location**: `app/routes/public.py:282-297`

**Fix**: Add `.limit(FTS_RESULT_LIMIT)` to LIKE fallback query.

### 12.5 Stream Archive with Cursor Pagination

**Problem**: Archive loads all posts into memory, groups in Python.

**Location**: `app/routes/public.py:117-148`

**Fix**: Use generator with `yield_per(100)` and group in Python. Add pagination for year/month navigation.

---

## Wave 13: Security Hardening

**Minor security improvements.**

### 13.1 Restrict class Attribute in Markdown Sanitization

**Problem**: `"*": {"class"}` allows any HTML element to have a class attribute.

**Location**: `app/markdown_config.py:14`

**Fix**: Remove the `"*": {"class"}` wildcard since only `span` and `div` need class attributes.

---

### 13.2 Normalize Subscribe Endpoint Flash Messages

**Problem**: Already-subscribed flash message implies confirmation email will be sent.

**Location**: `app/routes/public.py:427-430`

**Fix**: Change "Check your inbox to confirm your subscription." to "You're already subscribed!"

---

## Wave 14: Module Refactoring

**JavaScript modularization.**

### 14.1 Extract Remaining Inline JS from main.js

**Problem**: `main.js` still contains inline code that could be modularized.

**Effort**: 2-3 hours

**Fix**: Extract into modules under `app/static/js/shared/` and `app/static/js/public/`:
- `shared/mobile-menu.js` — mobile hamburger menu
- `shared/lazy-load.js` — image lazy loading
- `public/anchor-links.js` — heading anchor injection + copy
- `shared/filter-select.js` — dashboard/analytics auto-submit
- `shared/prefetch.js` — prefetch likely next pages
- `shared/nav-dropdown.js` — nav dropdown toggle
- `public/media-copy.js` — media copy URL button

**Already extracted** (Wave 8):
- `shared/utils.js`, `shared/dark-mode.js`, `shared/modal.js`
- `admin/editor.js`, `admin/bulk.js`, `admin/shortcuts.js`
- `public/lightbox.js`, `public/toc.js`, `public/share.js`, `public/code-copy.js`

---

## Additional Items from Codebase Review

**Identified but not yet scheduled. Listed for reference.**

### Low Priority (Not Scheduled)

| Issue | Location | Description |
|-------|----------|-------------|
| Regex-based CSS sanitization | `app/utils.py:sanitize_css()` | Uses regex instead of proper CSS parser. Potential bypass with complex selectors. |
| Newsletter scheduler single-machine lock | `app/scheduler.py` | File-based locking only; multi-worker needs Redis. |
| FTS sync errors swallowed | `app/search.py:sync_fts()` | Errors don't prevent DB commit, leaving FTS out of sync. |
| No orphaned image cleanup | `app/routes/admin/media.py` | Images uploaded but never associated with a post are never cleaned up. |

### Verified Not Issues

| Issue | Location | Resolution |
|-------|----------|------------|
| `SHIFT+Tab` dead code | `app/static/js/admin/shortcuts.js:113` | ✅ Already correctly uses `e.shiftKey` check. |

---

## Implementation Notes

### Testing

Run tests after each wave:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test-test-test-test-test-test-test-test-test python -m pytest tests/ -v
```

### Parallelization

Items within each wave can be worked on in parallel. Waves have the following dependencies:

| Wave | Dependencies | Can Start |
|------|--------------|-----------|
| 10 (Critical Security) | None | Immediately |
| 11 (Code Quality) | None | Immediately |
| 12 (Performance) | None | Immediately |
| 13 (Security Hardening) | None | Immediately |
| 14 (Module Refactoring) | None | Immediately |

**All waves are independent and can be parallelized.**

### Dependencies

- No new dependencies required for any items.
- All changes use existing packages (SQLAlchemy, Flask, smtplib).

---

## Related Files

- `AGENTS.md` — Project structure and patterns
- `DEPLOY.md` — Deployment guide
- `app/email.py` — Email sending
- `app/scheduler.py` — APScheduler jobs
- `app/context_processors.py` — Template context
- `app/routes/public.py` — Public routes
- `app/templates/` — Jinja2 templates

---

## Notes

- Items marked "Low" effort are 1-2 hours; "Medium" is 2-4 hours; "High" is 4+ hours
- All changes should maintain backward compatibility
- Run tests after each wave to verify nothing breaks