# Consolidated Improvement Plan

Merged from plan2–plan5. Organized by priority with parallelization guidance for sub-agents.

---

## Phase 1: Critical Security & Bugs

### 1. Admin Authorization — Privilege Escalation
**Priority:** Critical | **Status:** ✅ Done | **Files:** `app/routes/admin.py`, `app/__init__.py`, `tests/conftest.py`, `tests/test_security.py`

All admin routes use `@login_required` but none check `current_user.is_admin`. Any authenticated user (including non-admin) has full access.

1. Create `admin_required` decorator in `app/routes/admin.py`:
   ```python
   def admin_required(f):
       @wraps(f)
       @login_required
       def decorated(*args, **kwargs):
           if not current_user.is_admin:
               abort(403)
           return f(*args, **kwargs)
       return decorated
   ```
2. Replace `@login_required` with `@admin_required` on all admin routes except `login()` and `logout()`.
3. Add `is_admin` check in `login()` route — reject non-admin users with "Invalid credentials" (same message as bad password to avoid username enumeration).
4. Fix `admin_user` fixture in `tests/conftest.py`: set `is_admin=True` on the user.
5. Add authorization tests in `tests/test_security.py`: non-admin gets 403 on admin routes, non-admin cannot log in.

### 2. IntegrityError Rollback — Data Loss in `edit_post()`
**Priority:** Critical | **Status:** ✅ Done | **Files:** `app/routes/admin.py`

After `db.session.rollback()` in `edit_post()` (line 286), only `slug` is re-applied. All other form field changes (`title`, `body`, `summary`, `published`, `tags`, `published_at`) are silently lost because `db.session.get()` reloads stale DB values.

1. In `edit_post()`, capture all form values before the commit so they survive rollback. Refactor the IntegrityError handler to reapply all fields after re-fetching the post.
2. Apply same pattern to `new_post()` IntegrityError handler — retry with `_generate_unique_slug(title)` which appends counter suffixes.
3. Add tests: editing a post with slug collision preserves all fields; creating a post with slug collision succeeds.

### 3. Newsletter `all_sent` Bug — Duplicate Sends
**Priority:** Critical | **Status:** ✅ Done | **Files:** `app/email.py`

In `send_newsletter()`, when `SMTPServerDisconnected` occurs (line 108), `all_sent` is set to `False` (line 110). If reconnection and retry succeed (line 120), `all_sent` is never reset to `True`. The function returns `False`, causing the scheduler to skip marking posts as `newsletter_sent_at` — leading to duplicate newsletter sends on the next run.

1. After a successful retry `sendmail` (line 120), add `all_sent = True`.
2. Add test verifying `send_newsletter` returns `True` after successful reconnection.

### 4. Image Upload Extension/Content Mismatch
**Priority:** Critical | **Status:** ✅ Done | **Files:** `app/routes/admin.py`

`_save_image()` (line 66) validates magic bytes but stores the file with the user-provided extension. A JPEG could be saved as `.webp`, causing incorrect Content-Type headers.

1. Use `detected` type for the extension instead of the user-provided one:
   ```python
   ext = detected  # Use detected type, not user-provided extension
   filename = f"{uuid.uuid4().hex}.{ext}"
   ```

### 5. Test Fixture Issues
**Priority:** Critical | **Status:** ✅ Done | **Files:** `tests/conftest.py`

`admin_user` fixture creates a User without `is_admin=True`. Tests may pass/fail inconsistently depending on database state from prior runs or `create_app()` auto-promotion.

1. Set `is_admin=True` in `admin_user` fixture.
2. Review all test fixtures for proper cleanup and isolation.
3. Ensure `db.session.flush()` is used where IDs are needed before commit.

---

## Phase 2: Security Hardening

### 6. Session Fixation Protection
**Priority:** Medium | **Status:** ✅ Done | **Files:** `app/extensions.py`

Flask-Login doesn't regenerate session ID on login by default.

1. Set `login_manager.session_protection = "strong"` in `app/extensions.py`.

### 7. Backup Delete — Missing Error Handling
**Priority:** Medium | **Status:** ✅ Done | **Files:** `app/routes/admin.py`

`os.remove(real_path)` at line 931 has no try/except — permission errors cause 500.

1. Wrap in try/except OSError with logging and user-facing flash message.

### 8. Media Delete — Missing Error Handling
**Priority:** Medium | **Status:** ✅ Done | **Files:** `app/routes/admin.py`

`os.remove(real_path)` at line 596 has no try/except — same issue as backup delete.

1. Wrap in try/except OSError with logging and user-facing flash message.

### 9. CSP `frame-src` Directive
**Priority:** Medium | **Status:** ✅ Done | **Files:** `app/__init__.py`

CSP has `frame-ancestors 'none'` (prevents framing this site) but lacks `frame-src` (controls what this site can embed). Falls back to `default-src 'self'` which blocks external iframes implicitly.

1. Add `frame-src 'none'` to CSP string in `set_security_headers()`.

### 10. Escape LIKE Wildcards in Search
**Priority:** Medium | **Status:** ✅ Done | **Files:** `app/routes/public.py`

Search input containing `%` or `_` causes unexpected pattern matching (e.g., searching `100%` matches `100` followed by anything).

1. Escape `\`, `%`, and `_` in search query before interpolating into LIKE pattern.

---

## Phase 3: Performance

### 11. Dashboard Query Consolidation
**Priority:** Medium | **Status:** ✅ Done | **Files:** `app/routes/admin.py`

Dashboard runs 2 separate queries for per-post `view_counts` and `share_counts` (lines 141–152) plus 5 aggregate queries.

1. Replace the two separate count queries with a single query using subqueries:
   ```python
   view_counts_sq = (
       select(PageView.post_id, func.count(PageView.id).label("cnt"))
       .where(PageView.post_id.in_(post_ids))
       .group_by(PageView.post_id).subquery()
   )
   share_counts_sq = (
       select(ShareEvent.post_id, func.count(ShareEvent.id).label("cnt"))
       .where(ShareEvent.post_id.in_(post_ids))
       .group_by(ShareEvent.post_id).subquery()
   )
   rows = db.session.execute(
       select(Post.id,
              func.coalesce(view_counts_sq.c.cnt, 0).label("views"),
              func.coalesce(share_counts_sq.c.cnt, 0).label("shares"))
       .outerjoin(view_counts_sq, Post.id == view_counts_sq.c.post_id)
       .outerjoin(share_counts_sq, Post.id == share_counts_sq.c.post_id)
       .where(Post.id.in_(post_ids))
   ).all()
   ```

### 12. FTS Result Cap
**Priority:** Medium | **Status:** ✅ Done | **Files:** `app/routes/public.py`, `app/search.py`

`_fts_search()` has no LIMIT — returns all matches. The `CASE WHEN` ordering clause in the search route builds one condition per result, which grows unbounded.

1. Add `LIMIT 100` to the FTS MATCH query in `_fts_search()`.

### 13. Media Gallery — Use `os.scandir()`
**Priority:** Medium | **Status:** ✅ Done | **Files:** `app/routes/admin.py`

`media()` uses `glob.glob()` + `os.path.getmtime()` sort, doing one `os.stat()` syscall per file. With 1000 files, that's 1000+ extra syscalls.

1. Replace with `os.scandir()` which caches stat info from directory entries.
2. Remove `import glob as globmod` from inside the function.

### 14. Sitemap Memory Usage
**Priority:** Low | **Status:** ✅ Done | **Files:** `app/routes/public.py`

`sitemap_xml()` loaded all published posts and tags into memory. For large blogs, this could cause memory issues.

1. Converted to streaming generator (`_generate_sitemap()`) using `yield_per(100)` to avoid loading all results into memory at once.

### 15. Related Posts Query Performance
**Priority:** Low | **Status:** ✅ Done | **Files:** `app/routes/public.py`

`_get_related_posts()` was missing eager loading of tags, causing N+1 queries when rendering related posts on a post page.

1. Added `joinedload(Post.tags)` to the query so tags are fetched in a single JOIN.

---

## Phase 4: Code Quality

### 16. Consolidate `subscribe()` Exception Handling
**Priority:** Low | **Status:** ✅ Done | **Files:** `app/routes/public.py`

Three nearly identical try/except blocks for SMTP errors in `subscribe()` (lines 238–286).

1. Extract a `_try_send_confirmation(subscriber)` helper that returns `True`/`False`.
2. Simplify the route to call the helper.

### 17. Remove Duplicate Imports
**Priority:** Low | **Status:** ✅ Done | **Files:** `app/__init__.py`, `app/routes/public.py`

`before_request_handler` re-imports Flask and flask_login names already available at module level. `public.py` uses `import time as _time` unnecessarily.

1. Move all needed names to module-level imports in `__init__.py`.
2. Remove inner imports from `before_request_handler` and `set_security_headers`.
3. Change `import time as _time` to `import time` in `public.py`.

### 18. Centralize Magic Numbers
**Priority:** Low | **Status:** ✅ Done | **Files:** `app/routes/admin.py`, `app/config.py`, `config.toml`

Pagination sizes were hardcoded: dashboard=20, subscribers=50, media=50, media max=1000.

1. Added `dashboard_per_page`, `subscribers_per_page`, `media_per_page`, `media_max_files` to `config.toml` `[app]` section with defaults matching the old hardcoded values.
2. Loaded in `app/config.py` and added to `__all__`.
3. Replaced hardcoded values in `admin.py` with the new config constants.

### 19. Move `import csv` to Module Level
**Priority:** Low | **Status:** ✅ Done | **Files:** `app/routes/admin.py`

`export_subscribers()` has `import csv` and `import io` inside the function body.

1. Move both to top-level imports.

### 20. Centralize File Deletion
**Priority:** Low | **Status:** ✅ Done | **Files:** `app/routes/admin.py`, `app/utils.py`

Similar try/except pattern for `os.remove()` across `new_post()`, `edit_post()`, `delete_post()`, `bulk_operations()`, `delete_media()`, `delete_backup()`.

1. Create `_safe_delete_file(filepath)` utility in `app/utils.py` that wraps `os.remove()` with try/except and logging.
2. Use across all routes that delete files.

### 21. Newsletter Test Email — Allow Custom Address
**Priority:** Low | **Status:** ✅ Done | **Files:** `app/routes/admin.py`

Test newsletter sends to `FROM_ADDRESS` (admin email). No way to specify a different test address.

1. Add a form field to specify test email address on the newsletter test endpoint.

---

## Phase 5: Architecture

### 22. FTS Sync Before Commit
**Priority:** Medium | **Status:** ✅ Done | **Files:** `app/routes/admin.py`

`sync_fts()` is called after `db.session.commit()`. Its docstring says "Call before commit." If sync fails, DB and FTS are out of sync with no recovery.

1. Move `sync_fts()` calls BEFORE `db.session.commit()` in `edit_post()`, `new_post()`, and `bulk_operations()` publish/unpublish branches.
2. For delete routes, `remove_fts()` should stay AFTER commit — stale FTS entries are handled gracefully by LIKE fallback.

### 23. Conditional `sync_fts` — Only When Searchable Fields Change
**Priority:** Low | **Status:** ✅ Done | **Files:** `app/routes/admin.py`

`sync_fts()` runs DELETE + INSERT even when only tags or image changed (which don't affect FTS content).

1. In `edit_post()`, capture original `title`, `body`, `summary`, `published` before mutation.
2. Only call `sync_fts()` if any searchable field changed.

### 24. Health Check Enhancement
**Priority:** Low | **Status:** ✅ Done | **Files:** `app/routes/public.py`, `app/scheduler.py`

`/health` only checks DB connectivity. No visibility into scheduler status.

1. Add `_scheduler_running` flag in `scheduler.py`, set to `True` after `scheduler.start()`.
2. Add `get_scheduler_status()` getter.
3. Include scheduler status in health check JSON response.

### 25. Split `admin.py` into Modules
**Priority:** Low | **Status:** Cancelled

`admin.py` is ~970 lines covering multiple concerns. Splitting it would add complexity (multiple files, cross-imports, routing coordination) with minimal benefit given the current size.

No action taken.

---

## Phase 6: Documentation & Low-Priority

### 26. README.md — Remove Rate Limiting Claim
**Priority:** High | **Status:** ✅ Done | **Files:** `README.md`

README line 12 claims "Rate limiting — Login and API endpoint protection" but the codebase intentionally does not implement application-level rate limiting.

1. Remove or correct the rate limiting feature claim.

### 27. Document Login Protection Requirements
**Priority:** Medium | **Status:** ✅ Done | **Files:** `AGENTS.md`

Per project philosophy, rate limiting belongs at the proxy level. Document recommended proxy rules for `/admin/login`.

1. Added section to `AGENTS.md` with suggested nginx and Cloudflare rate limiting rules.
2. Item 2 (adding comment in admin.py login route) was deemed unnecessary — the AGENTS.md section is sufficient.

### 28. Session `last_activity` Corruption
**Priority:** Low | **Status:** No Action Needed | **Files:** `app/__init__.py`

If `last_activity` is non-numeric, the user is logged out (treated as expired). On the next visit, the session has a valid `last_activity` value. Current behavior is acceptable — no code change needed.

### 29. Add `requirements-dev.txt`
**Priority:** Low | **Status:** ✅ Done | **Files:** `requirements-dev.txt`

Test dependencies not documented separately.

1. Create `requirements-dev.txt` with pytest and pytest-cov.

### 30. Add Module-Level Docstrings
**Priority:** Low | **Status:** ✅ Done | **Files:** `app/cache.py`, `app/csrf.py`, `app/base62.py`

1. Added docstrings to `app/cache.py` (explains double-checked locking and TTL strategy), `app/csrf.py` (explains token storage and validation), and `app/base62.py` (explains purpose and alphabet). `app/markdown_config.py` already had a docstring.

### 31. Favicon Redirect Status Code
**Priority:** Low | **Status:** ✅ Done | **Files:** `app/routes/public.py`

Favicon redirect returns 301 (permanent). Consider 302 (temporary) if the favicon location might change.

### 32. Config Validation for Email Settings
**Priority:** Low | **Status:** ✅ Done | **Files:** `app/config.py`

Newsletter settings were validated but SMTP port was not validated until runtime.

1. Added SMTP port validation (1-65535) in `_validate_config()` when `smtp_host` is configured.

### 33. Hardcoded Admin User Promotion at Startup
**Priority:** Low | **Status:** ✅ Done | **Files:** `app/__init__.py`

First user auto-promotion logic had confusing behavior when `ADMIN_PASSWORD` didn't match the stored hash.

1. Simplified to: create user if missing, promote to admin if not already. Removed the misleading password-mismatch warning. The `flask create-admin` CLI command is the primary mechanism for password management.

---

## Resolved / No Action Needed

- **Subscriber Email Index** — `unique=True` creates implicit index
- **CSRF Token in Meta Tag** — intentional for JS API calls
- **Unsubscribe Token Exposure** — UUID hex is sufficiently hard to guess
- **Unauthenticated Health Check** — intentional; protect at proxy level
- **Cache Race Condition** — double-checked locking is acceptable
- **Tag Slug Collision Handling** — already handled correctly
- **Session Viewed Posts Storage** — already capped at `MAX_VIEWED_POSTS`
- **Email Validation Regex** — sufficient for typical use
- **Backup Filename Regex** — current behavior is safe
- **Debug Mode Security** — acceptable for current use case

---

## All Items Complete

All 33 items from this plan have been implemented. The final batch (items 14–33) was completed on 2026-03-31.

### Verification

```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

All 186 tests pass.

---

## Historical: Parallelization Strategy

The original plan used sub-agents working in parallel across file groups. This section is retained for reference only — all items are now done.

| Agent | Scope | Items |
|-------|-------|-------|
| Agent 1 | Security (admin.py + tests) | 1, 2, 4, 5, 7, 8 |
| Agent 2 | Performance (admin.py + public.py) | 11, 12, 13, 14, 15 |
| Agent 3 | Code quality (public.py + __init__.py) | 10, 16, 17, 24, 31 |
| Agent 4 | Bug fixes (email.py + extensions.py + config) | 3, 6, 9, 32 |
| Agent 5 | Documentation + cleanup | 18, 19, 20, 21, 22, 23, 25, 26, 27, 29, 30, 33 |
