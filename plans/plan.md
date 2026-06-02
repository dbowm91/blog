# Consolidated Architecture Improvement Plan

**Created:** 2026-06-02
**Status:** PENDING — All items below need implementation.
**Verified:** 2026-06-02 — All claims verified against actual codebase via subagent exploration.

## How to Execute This Plan

This plan contains 69 action items organized into 4 parallelizable waves. Items within each wave are fully independent and can be executed concurrently using subagents. Waves have soft dependencies: source code changes (Wave 1) should land before documentation that references the corrected code (Waves 2-4), but documentation can be partially updated in parallel with notes like "pending fix."

### Subagent Execution Pattern

For maximum parallelization, launch subagents per wave. Each subagent should:
1. Read this plan and the relevant item details below
2. Read the target file(s) for context
3. Make the change
4. Verify with `ruff check .` and `ruff format --check .` (for source changes)
5. Report what was changed

### Verification After All Waves

```bash
ruff check .
ruff format --check .
mypy app/
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/
```

---

## Wave 1: Source Code Fixes (11 items) — All Independent

These fix actual bugs, data integrity issues, and code quality problems. All items are independent and can be parallelized.

### 1.1 — Remove `_invalidate_all_caches()` dead code
- **Priority:** Critical
- **File:** `app/routes/admin/__init__.py:62-76`
- **Issue:** `_invalidate_all_caches()` is defined but never called or imported anywhere in the codebase. Individual caches are invalidated separately in route handlers via direct `invalidate_tag_cache()`, `invalidate_analytics_cache()`, etc. calls.
- **Action:** Delete the function (lines 62-76). Also check `architecture/services/tag.md` and `architecture/services/tag_cache.md` — if they reference this function, update them to document the actual per-function invalidation pattern used in route handlers.
- **Verify:** `grep -r "_invalidate_all_caches" --include="*.py"` returns no matches.

### 1.2 — Add `nullable=False` to `Post.published`
- **Priority:** High
- **File:** `app/models.py:196`
- **Current code:** `published = db.Column(db.Boolean, default=False)`
- **Action:** Change to `published = db.Column(db.Boolean, default=False, nullable=False)`. Generate and apply a migration (`flask db migrate -m "add nullable false to post published"` then `flask db upgrade`). The migration should set any existing NULL values to False before applying the constraint.
- **Verify:** `sqlite3 instance/blog.db ".schema posts"` shows `NOT NULL` on the published column.

### 1.3 — Add `nullable=False` to `Page.published`
- **Priority:** High
- **File:** `app/models.py:166`
- **Current code:** `published = db.Column(db.Boolean, default=False)`
- **Action:** Same as 1.2 — add `nullable=False` and create a migration. Handle existing NULLs.
- **Verify:** Same as 1.2 for the pages table.

### 1.4 — Add `nullable=False` to `User.failed_login_count`
- **Priority:** High
- **File:** `app/models.py:31`
- **Current code:** `failed_login_count = db.Column(db.Integer, default=0)`
- **Action:** Change to `failed_login_count = db.Column(db.Integer, default=0, nullable=False)`. The `record_failed_login()` method at line 116 does `self.failed_login_count += 1` which would TypeError on NULL from legacy data. Generate migration.
- **Verify:** Column no longer allows NULL.

### 1.5 — Fix in-place encryption to use temp file pattern
- **Priority:** High
- **File:** `app/services/backup.py:98-115` (specifically line 112)
- **Current code:** `return encrypt_backup_file(filepath, filepath)` — reads and writes to same path, risking corruption if killed mid-write.
- **Action:** Write encrypted output to `filepath + ".enc.tmp"`, then use `os.replace(filepath + ".enc.tmp", filepath)` on success. Clean up temp file on failure in a `finally` block.
- **Verify:** Backup with encryption enabled completes successfully; no leftover `.enc.tmp` files.

### 1.6 — Add `SMTP_HOST` to celery service in docker-compose.yml
- **Priority:** High
- **File:** `docker-compose.yml` (celery service environment block, around line 71)
- **Current code:** Celery service has `SMTP_USER` and `SMTP_PASSWORD` but omits `SMTP_HOST`. The blog service (line 16) has `SMTP_HOST=${SMTP_HOST:-}`.
- **Action:** Add `- SMTP_HOST=${SMTP_HOST:-}` to the celery service environment block, after `SMTP_PASSWORD` and before `PYTHONPATH`.
- **Verify:** `docker compose config` shows SMTP_HOST in celery service environment.

### 1.7 — Fix benchmark Celery configuration
- **Priority:** High
- **File:** `tests/benchmarks/conftest.py`
- **Issue:** No `task_always_eager=True` configured; Celery tasks triggered during benchmarks would go to a real broker and hang/fail.
- **Action:** Add Celery eager mode configuration after the `app` fixture setup (after line 35). Match the pattern from `tests/conftest.py:50-56`:
  ```python
  from celery import current_app as celery_app
  celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
  ```
- **Verify:** `grep -r "task_always_eager" tests/benchmarks/` shows the configuration.

### 1.8 — Use env var for E2E admin password
- **Priority:** High
- **File:** `tests/e2e/conftest.py:75`
- **Current code:** `admin.set_password("test-password")` (hardcoded string)
- **Action:** Change to `admin.set_password(os.environ["ADMIN_PASSWORD"])` to stay in sync with the environment variable set at line 7. Also check `tests/conftest.py:101` which has the same hardcoded pattern for `user.set_password("test-password")` and fix that too.
- **Verify:** E2E tests still pass with `ADMIN_PASSWORD=test-password`.

### 1.9 — Fix `subscribe.py:204` missing OperationalError handling
- **Priority:** High
- **File:** `app/routes/public/subscribe.py:201-204`
- **Current code:**
  ```python
  sub_email = sub.email
  sub.unsubscribed_at = utc_now()
  sub.confirmed = False
  db.session.commit()  # No try/except
  ```
- **Issue:** Every other `db.session.commit()` in this file is wrapped in `try/except (IntegrityError, OperationalError)` with rollback. This one is not.
- **Action:** Wrap in try/except matching the pattern used elsewhere in the file:
  ```python
  try:
      db.session.commit()
  except (IntegrityError, OperationalError):
      db.session.rollback()
      flash("An error occurred. Please try again.", "error")
      return redirect("/")
  ```
- **Verify:** Existing tests pass; error path doesn't propagate unhandled.

### 1.10 — Fix `setup_2fa` confusing TOTP validation
- **Priority:** High
- **File:** `app/routes/admin/auth.py:272-277`
- **Current code:** Checks `if secret and pyotp.TOTP(secret).verify(token)` — if the token validates against the existing secret, it says "2FA is already enabled." This is confusing on the setup page.
- **Action:** Replace the condition with `if user.totp_enabled:` — if 2FA is already enabled, redirect with info message. The subsequent code (lines 279-280) generates a new secret, which shouldn't happen if 2FA is already enabled.
- **Verify:** Test 2FA setup flow: enabling when not enabled works; visiting setup when already enabled shows info message.

### 1.11 — Fix `send_newsletter_task` variable leak
- **Priority:** High
- **File:** `app/tasks.py:183-191`
- **Current code:** After the `for post in posts` loop, line 190 references `post.newsletter_attempts` — this uses the loop variable after the loop ends, reflecting only the last post's count. If `posts` is empty, this would be an UnboundLocalError.
- **Action:** Track the last attempt count during the loop:
  ```python
  last_attempts = 0
  for post in posts:
      if post is not None:
          post.newsletter_attempts = (post.newsletter_attempts or 0) + 1
          last_attempts = post.newsletter_attempts
  db.session.commit()
  logger.warning(
      "Newsletter task failed for %d posts (attempts incremented to %d)",
      len(posts),
      last_attempts,
  )
  ```
- **Verify:** Newsletter task logs correctly; no NameError on edge cases.

---

## Wave 2: Documentation Corrections (12 items) — All Independent

These fix factual errors in architecture documentation. These reference source code locations and should be done alongside or after Wave 1.

### 2.1 — Fix nginx proxy_pass documentation
- **Priority:** High
- **File:** `architecture/deployment/docker.md:298`
- **Current:** Claims `proxy_pass http://127.0.0.1:5000`
- **Correct:** `proxy_pass http://blog:5000` (Docker service name, per `nginx/conf.d/blog.conf:52`)

### 2.2 — Fix template inheritance documentation
- **Priority:** High
- **File:** `architecture/frontend/templates.md:71,73`
- **Current:** Claims `admin/base.html` and `admin/login_base.html` extend `base.html`
- **Correct:** All three (`base.html`, `admin/base.html`, `admin/login_base.html`) are standalone templates with their own `<!DOCTYPE html>`. `admin/base.html` does NOT extend `base.html`. Rewrite the Template Inheritance section to document 3 standalone base templates and note the triple duplication maintenance risk.

### 2.3 — Fix `marked.min.js` loading documentation
- **Priority:** High
- **File:** `architecture/frontend/static-assets.md:135-139`
- **Current:** Claims `marked.min.js` is loaded outside Vite via `url_for('static', ...)`
- **Correct:** Both `base.html:150` and `admin/base.html:162` use `vite_asset('js/lib/marked.min.js')` — it goes through Vite's asset pipeline with content hashing and CDN support.

### 2.4 — Fix SSRF source file reference
- **Priority:** High
- **File:** `architecture/overview.md:299`
- **Current:** Claims SSRF protection is at `app/webhooks.py`
- **Correct:** `is_safe_webhook_url()` is defined at `app/utils.py:383-485`. The `app/webhooks.py` file imports and calls it but doesn't define it.

### 2.5 — Fix encryption function names
- **Priority:** Medium
- **File:** `architecture/services/encryption.md:17`
- **Current:** Claims functions are `encrypt_secret()` and `decrypt_secret()`
- **Correct:** Actual names are `encrypt()` and `decrypt()` at `app/services/encryption.py:41,69`. Developers calling the documented names would get ImportError.

### 2.6 — Fix Cache-Control line number
- **Priority:** Low
- **File:** `architecture/routes/rss-feeds.md:236`
- **Current:** References `rss.py:98`
- **Correct:** Cache-Control header is set at `rss.py:90` (inside `_add_cache_headers()` function).

### 2.7 — Fix stale line numbers in tag_cache.md
- **Priority:** Low
- **File:** `architecture/services/tag_cache.md:31,33`
- **Current:** `editor.py:89,204` and `manage.py:82`
- **Correct:** Verify actual line numbers against current code (`editor.py:77,192` and `manage.py:70`) and update.

### 2.8 — Fix stale line numbers and wording in scheduler.md
- **Priority:** Low
- **File:** `architecture/tasks/scheduler.md:53,64-68`
- **Current:** "inline `run_daily_backup()` service function" and off-by-one task file line references
- **Correct:** Wording should be "imports from `app.services.backup`" (not "inline"). Correct line numbers to match actual task decorators.

### 2.9 — Fix `clean_analytics_cache` source attribution
- **Priority:** Medium
- **File:** `architecture/testing/test-suite.md:42`
- **Current:** Attributes `clean_analytics_cache` to `conftest.py`
- **Correct:** Defined in `tests/shared_fixtures.py:17-24`. Both `conftest.py` and `benchmarks/conftest.py` import it via `from tests.shared_fixtures import *`.

### 2.10 — Fix test file count
- **Priority:** Low
- **File:** `tests/AGENTS.override.md:35,60`
- **Current:** Claims "~36 test files"
- **Correct:** Actual count is ~39 test files (37 in tests/ root + benchmarks/test_benchmarks.py + e2e/test_e2e.py).

### 2.11 — Document rate limiting across all routes
- **Priority:** High
- **File:** `architecture/routes/admin-routes.md` (add new section or table)
- **Action:** Add a comprehensive rate limit table:
  | Endpoint | Limit | Key |
  |----------|-------|-----|
  | Admin login | 5/min | per-IP |
  | 2FA login | 5/min | per-IP |
  | Forgot password | 5/min | per-IP |
  | Public browse | 60/min | per-IP |
  | Search | 20/min | per-IP |
  | Archive | 30/min | per-IP |
  | Subscribe | 10/min | per-IP |
  | Comments | dual-key | per-IP + per-post |
  | API reads | 20/min | per-IP |
  | API writes | 10/min | per-IP |
- **Source:** `app/config.py:164-171` (`ADMIN_RATE_LIMITS`), route decorators.

### 2.12 — Document CSRF scope for API clients
- **Priority:** High
- **File:** `architecture/overview.md` Security section
- **Action:** Document that CSRF applies to ALL POST requests including API endpoints (`app/__init__.py:297-298`). API clients using Bearer tokens (ApiToken) don't have Flask sessions with CSRF tokens, so POST requests would get 403. Note this as a known interaction.

---

## Wave 3: Source Code Improvements (12 items) — All Independent

These are code quality improvements, not critical bugs. All items are independent.

### 3.1 — Make `login_base.html` use `syntax_theme` variable
- **Priority:** Medium
- **File:** `app/templates/admin/login_base.html:8`
- **Current:** `<link rel="stylesheet" href="{{ vite_asset('css/prism-okaidia.css') }}">`
- **Action:** Change to `<link rel="stylesheet" href="{{ vite_asset('css/' + syntax_theme + '.css') }}">` to respect user's configured syntax theme. Note: the `data-prism-css-url` attribute on line 2 already uses `syntax_theme` dynamically, so this is just making the actual `<link>` tag consistent.

### 3.2 — Use `vite_asset()` for Prism JS in `loadPrismIfNeeded()`
- **Priority:** Medium
- **File:** `app/static/js/main.js:106,109`
- **Current:** Hardcodes `/static/js/prism.min.js` and `/static/js/prism-languages.js`
- **Action:** Pass Vite-resolved URLs via data attributes on a script tag in the base templates, then read them in `loadPrismIfNeeded()`. For example, add `data-prism-js-url` and `data-prism-langs-url` attributes similar to the existing `data-prism-css-url` pattern at `base.html:2`.

### 3.3 — Fix `post_image_srcset` hardcoded path
- **Priority:** Medium
- **File:** `app/filters.py:72`
- **Current:** `f"{base_url.rstrip('/')}/static/uploads/{variant_name}"`
- **Action:** Replace with `url_for('static', filename=f'uploads/{variant_name}')` or a storage-aware URL builder that respects CDN_URL.

### 3.4 — Fix hardcoded Expires header in rss.py
- **Priority:** Medium
- **File:** `app/routes/rss.py:91`
- **Current:** `response.headers["Expires"] = "Thu, 01 Jan 2027 00:00:00 GMT"` (fixed date)
- **Action:** Either dynamically calculate expiry (now + max-age) or remove the Expires header entirely since `Cache-Control: max-age=3600` is already set at line 90 and takes precedence for HTTP/1.1 clients.

### 3.5 — Replace `__import__("datetime")` hack
- **Priority:** Medium
- **File:** `app/routes/api/subscribers.py:103`
- **Current:** `__import__("datetime").timedelta(hours=CONFIRMATION_EXPIRY_HOURS)`
- **Action:** Add `from datetime import timedelta` at the top of the file and use `timedelta(...)` directly. Check if there are other imports at the top of the file that would conflict.

### 3.6 — Log webhook exceptions instead of swallowing
- **Priority:** Medium
- **Files:** `app/routes/api/posts.py:314-315`, `app/routes/public/subscribe.py:183-184`
- **Current:** Bare `except Exception: pass` around `create_webhook_event` calls
- **Action:** Replace with `except Exception: logger.warning("Webhook event creation failed", exc_info=True)` (or similar). Ensure `logger` is imported in both files.

### 3.7 — Fix `get_indexed_terms_fallback()` sorting
- **Priority:** Medium
- **File:** `app/search.py:241`
- **Current:** `return list(set(terms))` — unordered
- **Action:** Change to `return sorted(set(terms))` for consistent autocomplete behavior. The main `get_indexed_terms()` at line 219-227 returns alphabetically sorted results, so the fallback should match.

### 3.8 — Add `critical.css` to admin base template
- **Priority:** Medium
- **File:** `app/templates/admin/base.html`
- **Current:** Admin pages don't load `critical.css`, missing above-the-fold optimization
- **Action:** Add `{{ vite_asset('css/critical.css') }}` with `media="screen"` in the `<head>` section, similar to `base.html:24`.

### 3.9 — Remove unnecessary Prism JS from login page
- **Priority:** Medium
- **File:** `app/templates/admin/login_base.html:56-57`
- **Current:** Loads `prism.min.js` and `prism-languages.js` eagerly on login pages (no code blocks exist on login pages)
- **Action:** Remove the Prism script tags entirely. Login pages don't need syntax highlighting.

### 3.10 — Fix `browse.py:277` f-string in logging
- **Priority:** Low
- **File:** `app/routes/public/browse.py:277`
- **Current:** `logging.warning(f"FTS returned invalid results: {post_results}")`
- **Action:** Change to `logging.warning("FTS returned invalid results: %s", post_results)` for lazy evaluation.

### 3.11 — Remove unnecessary `SQLAlchemyError` catch
- **Priority:** Low
- **File:** `app/services/backup.py:113`
- **Current:** Catches `SQLAlchemyError` in `_encrypt_backup_file`, but the underlying `encrypt_backup_file()` only raises `OSError`, `ValueError`, `RuntimeError`.
- **Action:** Remove `SQLAlchemyError` from the exception tuple at line 113.

### 3.12 — Replace string comparison with `isinstance()` for storage backend
- **Priority:** Low
- **File:** `app/tasks.py:42,71`
- **Current:** `storage.__class__.__name__ == "LocalStorageBackend"` / `"S3StorageBackend"`
- **Action:** Use `isinstance(storage, LocalStorageBackend)` and `isinstance(storage, S3StorageBackend)` instead. Import the classes from `app.storage`.

---

## Wave 4: Documentation Additions & Cleanup (34 items) — All Independent

These add missing documentation or make minor improvements. All items are independent. Many are low-priority and can be batched.

### High Priority

#### 4.1 — Document token enumeration protection
- **File:** `architecture/routes/public-routes.md`
- **Action:** Note that subscribe confirm/unsubscribe routes use `time.sleep(TOKEN_ENUMERATION_DELAY)` (at `app/routes/public/subscribe.py:146,192`) to prevent token enumeration attacks.

#### 4.2 — Document search fallback behavior
- **File:** `architecture/infrastructure/search.md` or `architecture/routes/public-routes.md`
- **Action:** Document that FTS search falls back to ILIKE when FTS returns no results (`app/routes/public/browse.py:290-308`), and that "did you mean" suggestions are provided via `get_did_you_mean()`.

#### 4.3 — Document X-Forwarded-For trust assumption
- **File:** `architecture/routes/public-routes.md` (comments section)
- **Action:** Note that comment rate limiting uses `X-Forwarded-For` header for IP detection (`app/routes/public/comments.py:24-32`). If behind a trusted proxy that doesn't sanitize this header, rate limiting can be bypassed.

#### 4.4 — Document admin session IP binding modes
- **File:** `architecture/routes/admin-routes.md`
- **Action:** Document enforce/warn modes for `SESSION_IP_BINDING` and their behavioral differences (enforce: invalidates session; warn: logs only). Source: `app/routes/admin/__init__.py:25-55`.

#### 4.5 — Document health check endpoint
- **File:** New section in `architecture/infrastructure/` or add to `architecture/overview.md`
- **Action:** Document `/health` endpoint at `app/routes/public/meta.py:188-321` with all check types (DB, scheduler, FTS, disk, integrity, Redis, Celery, backup freshness) and `?detailed=true&secret=<key>` authentication.

#### 4.6 — Create `architecture/infrastructure/overview.md`
- **File:** `architecture/infrastructure/overview.md`
- **Action:** Create overview doc describing how search, email, storage, webhooks, and health checks interact. Currently each doc is siloed.

### Medium Priority

#### 4.7 — Document ETag/conditional GET for feeds
- **File:** `architecture/routes/rss-feeds.md`
- **Action:** Document that all feed endpoints implement `If-None-Match` / `304 Not Modified` responses for efficient caching (e.g., `rss.py:190-192, 240-242, 292-294`).

#### 4.8 — Document `Post.published` and `Page.published` nullable issue
- **File:** `architecture/core/models.md`
- **Action:** Note that `Post.published` and `Page.published` columns allow NULL despite documented intent of `nullable=False`. Reference Wave 1 items 1.2 and 1.3 for the fix.

#### 4.9 — Document admin template independence
- **File:** `architecture/frontend/templates.md`
- **Action:** Add note that `admin/base.html` and `admin/login_base.html` are standalone templates, not extending `base.html`. This is a critical architectural detail for template maintenance.

#### 4.10 — Document CSRF scope for API clients (overview)
- **File:** `architecture/overview.md` Security section
- **Action:** Note that CSRF applies to all POSTs including API endpoints and that API clients using Bearer tokens need to handle this.

#### 4.11 — Document health check authentication
- **File:** Health check doc or `architecture/overview.md`
- **Action:** Note that `?detailed=true` requires `?secret=<HEALTH_CHECK_SECRET>` parameter for authenticated detailed results.

#### 4.12 — Document error handler routes
- **File:** `architecture/routes/public-routes.md`
- **Action:** Add section covering error handlers in `app/routes/errors.py` (404, 500, 413).

### Low Priority

#### 4.13 — Document series feed ordering
- **File:** `architecture/routes/rss-feeds.md`
- **Action:** Note that series feeds preserve `PostSeries.order_index` ordering rather than date ordering.

#### 4.14 — Document backup verify JSON return format
- **File:** `architecture/routes/admin-routes.md`
- **Action:** Document that verify endpoints return JSON with `valid` and `message` fields.

#### 4.15 — Document available syntax themes in settings
- **File:** `architecture/routes/admin-routes.md`
- **Action:** Document the 4 available syntax themes (github-dark, github-light, solarized-dark, monokai) from `app/models.py:366-457`.

#### 4.16 — Document unschedule bulk action
- **File:** `architecture/routes/admin-routes.md`
- **Action:** Document the unschedule action in admin bulk operations (`app/routes/admin/posts/__init__.py:148-232`).

#### 4.17 — Document subscriber bulk resend
- **File:** `architecture/routes/admin-routes.md`
- **Action:** Document the "resend" action in subscriber bulk operations (`app/routes/admin/subscribers.py:183-195`).

#### 4.18 — Add required environment variables summary
- **File:** `architecture/overview.md`
- **Action:** List critical env vars: SECRET_KEY, ADMIN_PASSWORD, SMTP_HOST, REDIS_URL, HEALTH_CHECK_SECRET with purposes.

#### 4.19 — Document `app/page_view_buffer.py`
- **File:** `architecture/overview.md` or `architecture/core/app-factory.md`
- **Action:** Document daemon thread mechanics, configurable buffer size via `PAGE_VIEW_BUFFER_SIZE`.

#### 4.20 — Document `marked.min.js` uses `vite_asset()` in overview
- **File:** `architecture/overview.md` Frontend section
- **Action:** Ensure Frontend section notes all JS assets use `vite_asset()`.

#### 4.21 — Add utility file descriptions to directory structure
- **File:** `architecture/overview.md`
- **Action:** Add purpose descriptions for `app/backup_integrity.py`, `app/base62.py`, `app/csv_utils.py`, `app/markdown_config.py`, `app/transaction.py`.

#### 4.22 — Document `_update_delivery_status` function
- **File:** `architecture/tasks/celery-tasks.md`
- **Action:** Document the delivery status determination logic at `app/tasks.py:316-345` and its `--concurrency=1` dependency.

#### 4.23 — Document fire-and-forget dispatch pattern
- **File:** `architecture/tasks/celery-tasks.md`
- **Action:** Note that `deliver_webhook_task` uses `.delay()` (fire-and-forget); parent success doesn't indicate child delivery success.

#### 4.24 — Document `Subscriber`, `Tag`, `PageView`, `ShareEvent` models
- **File:** `architecture/core/models.md`
- **Action:** Add detailed model sections for these 4 models (field definitions, relationships, purposes).

#### 4.25 — Document `app/validators.py` location
- **File:** `architecture/overview.md`
- **Action:** Note that validators are at `app/validators.py` (NOT `app/core/validators.py`).

### Cleanup Items

#### 4.26 — Add word boundary to `highlight_query()` regex
- **File:** `app/search.py:362`
- **Current:** `re.compile(re.escape(query), re.IGNORECASE)` — matches inside words
- **Action:** Use `r'\b' + re.escape(query) + r'\b'` unless partial matching is desired (in which case document the behavior).

#### 4.27 — Fix `highlight_query()` docstring
- **File:** `app/search.py:354`
- **Current:** Docstring says "(may contain HTML)" for `text` parameter
- **Action:** Clarify that input should be raw text, not pre-escaped HTML, to match the documentation at `architecture/services/search.md:151`.

#### 4.28 — Remove dead `max_retries`/`retry_backoff` from non-retrying tasks
- **File:** `app/tasks.py:30,390`
- **Current:** `generate_image_variants` and `run_backup_task` have `max_retries` configured but never call `self.retry()`
- **Action:** Remove `max_retries` and `retry_backoff` from these task decorators, or add actual retry logic if retries are desired.

#### 4.29 — Fix `media.py` redundant `get_storage()` call
- **File:** `app/routes/admin/media.py:66-97`
- **Current:** `_scan_media_directory` calls `get_storage()` twice (lines 68-69 and 72-73) inside the loop
- **Action:** Remove the duplicate call and re-import inside the loop.

#### 4.30 — Fix `errors.py:62-68` 413 redirect logic
- **File:** `app/routes/errors.py:62-68`
- **Current:** 413 handler redirects to `req.referrer or url_for("admin.dashboard")` — public users hitting 413 would be redirected to admin dashboard
- **Action:** Check if referrer is an admin URL first; otherwise redirect to home page (`url_for("public.index")`).

#### 4.31 — Consolidate `slow` marker registration
- **Files:** `pytest.ini:3`, `tests/conftest.py:20-23`
- **Current:** `slow` marker registered in both `pytest.ini` and `conftest.py`
- **Action:** Remove from `pytest.ini:3` since `conftest.py` handles it via `pytest_configure`.

#### 4.32 — Make `cleanup_uploads` path more robust
- **File:** `tests/conftest.py:202`
- **Current:** Uses fragile relative path via `__file__`
- **Action:** Use project root detection or add logging if path doesn't exist.

#### 4.33 — Review `SiteSettings.get_instance()` unconditional commit
- **File:** `app/models.py:359`
- **Current:** `db.session.commit()` unconditionally when creating new instance
- **Action:** Consider using `db.session.merge()` or check-then-create pattern to avoid committing outer transactions' uncommitted changes.

#### 4.34 — Add `SEARCH_PROVIDER` and `SEARCH_CONFIG` to `__all__`
- **File:** `app/config.py:6-61`
- **Current:** These are defined at lines 173-174 but not in `__all__`
- **Action:** Add to `__all__` if they are considered public API.

---

## Cross-Cutting Concerns

### CSRF Scope Investigation
- **Priority:** High
- **Files:** `app/__init__.py:297-298`, `app/routes/api/auth.py`
- **Issue:** CSRF is enforced for ALL POST requests globally, including API endpoints. API clients using Bearer tokens don't have Flask sessions with CSRF tokens.
- **Action:** Investigate whether this is intentional (defense-in-depth) or if API routes should be exempt. Document the behavior regardless. See Wave 2 item 2.12.

### Post.published Nullable Migration
- **Files:** `app/models.py:196,166`, `app/cli.py` (seed command)
- **Note:** Wave 1 items 1.2 and 1.3 require database migrations. The seed command at `app/cli.py:267` has `--published/--draft` flags which should continue working after the migration.

---

## Wave Summary

| Wave | Focus | Items | Can Parallelize | Subagent Count |
|------|-------|-------|-----------------|----------------|
| 1 | Source Code Fixes | 11 | Yes | Up to 11 |
| 2 | Documentation Corrections | 12 | Yes | Up to 12 |
| 3 | Source Code Improvements | 12 | Yes | Up to 12 |
| 4 | Documentation Additions | 34 | Yes | Up to 34 |
| **Total** | | **69** | | |

**Recommended subagent batch sizes:** 4-6 per wave to avoid overwhelming the system. Launch in parallel within each wave.
