# Consolidated Architecture Review Plan

**Created:** 2026-06-02 (consolidated from individual review files)
**Source Reviews:** core_review.md, routes_review.md, services_review.md, tasks_review.md, infrastructure_review.md, frontend_review.md, deployment_review.md, testing_review.md, overview_review.md, architecture_prune.md
**Status:** PENDING — All items below need implementation.

## Summary

Consolidated action items from all 10 architecture review files. Items are organized into 6 parallelizable waves. Each wave contains items that can be executed concurrently (no inter-dependencies within a wave). Items across waves have soft dependencies (Wave 1 source fixes should land before Wave 3+ documentation references them, but documentation fixes can be done in parallel with source fixes).

| Wave | Focus | Items | Parallelizable |
|------|-------|-------|----------------|
| 1 | Critical & High Source Fixes | 11 | Yes (all independent) |
| 2 | High & Medium Documentation Corrections | 10 | Yes (all independent) |
| 3 | Medium Source Code Fixes | 10 | Yes (all independent) |
| 4 | Medium Documentation Additions | 12 | Yes (all independent) |
| 5 | Low Source Improvements | 12 | Yes (all independent) |
| 6 | Low Documentation & Cleanup | 14 | Yes (all independent) |

**Total: 69 action items**

---

## Wave 1: Critical & High Source Code Fixes

These are actual bugs or data integrity issues in the source code. All items are independent and can be parallelized.

### 1.1 — Investigate/remove `_invalidate_all_caches()` dead code
- **Priority:** Critical
- **File:** `app/routes/admin/__init__.py:62-76`
- **Issue:** `_invalidate_all_caches()` is defined but never called anywhere in the codebase. Individual caches are invalidated separately in route handlers.
- **Action:** Either wire it up to be called from relevant route handlers, or remove it entirely. If removing, also update `architecture/services/tag.md` and `architecture/services/tag_cache.md` to reflect the actual per-function invalidation pattern.
- **Verify:** Grep for `_invalidate_all_caches` after changes; ensure no references remain.

### 1.2 — Add `nullable=False` to `Post.published`
- **Priority:** High
- **File:** `app/models.py:196`
- **Current:** `published = db.Column(db.Boolean, default=False)` (implicitly nullable)
- **Action:** Add `nullable=False` to the column definition. This requires a database migration (`flask db migrate` + `flask db upgrade`).
- **Verify:** Column no longer allows NULL; existing NULL rows handled by migration (set to False).

### 1.3 — Add `nullable=False` to `Page.published`
- **Priority:** High
- **File:** `app/models.py:166`
- **Current:** `published = db.Column(db.Boolean, default=False)` (implicitly nullable)
- **Action:** Same as 1.2 — add `nullable=False` and create migration.
- **Verify:** Same as 1.2.

### 1.4 — Add `nullable=False` to `User.failed_login_count`
- **Priority:** High
- **File:** `app/models.py:31`
- **Current:** `failed_login_count = db.Column(db.Integer, default=0)` (implicitly nullable)
- **Action:** Add `nullable=False`. The `record_failed_login()` method does `self.failed_login_count += 1` which would TypeError on NULL.
- **Verify:** Column no longer allows NULL.

### 1.5 — Fix in-place encryption to use temp file pattern
- **Priority:** High
- **File:** `app/services/backup.py:112`
- **Current:** `encrypt_backup_file(filepath, filepath)` — reads and writes to same path, risking corruption on crash.
- **Action:** Write to `filepath + ".enc.tmp"`, then `os.replace()` to `filepath` on success. This prevents data loss if the process is killed mid-write.
- **Verify:** Test backup with encryption enabled; verify temp file is cleaned up.

### 1.6 — Add `SMTP_HOST` to celery service in docker-compose.yml
- **Priority:** High
- **File:** `docker-compose.yml:67-72`
- **Current:** Celery service has `SMTP_USER` and `SMTP_PASSWORD` but omits `SMTP_HOST`.
- **Action:** Add `- SMTP_HOST=${SMTP_HOST:-}` to the celery service environment block (after line 71, before `PYTHONPATH`).
- **Verify:** `docker compose config` shows SMTP_HOST in celery service.

### 1.7 — Fix benchmark Celery configuration
- **Priority:** High
- **File:** `tests/benchmarks/conftest.py`
- **Current:** No `task_always_eager=True` configured; Celery tasks would go to a real broker.
- **Action:** Add Celery eager mode configuration matching `tests/conftest.py:50-56`:
  ```python
  from app.celery_app import celery_app
  celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
  ```
- **Verify:** Run `pytest tests/benchmarks/` — tasks should execute synchronously.

### 1.8 — Use env var for E2E admin password
- **Priority:** High
- **File:** `tests/e2e/conftest.py:75`
- **Current:** `admin.set_password("test-password")` (hardcoded)
- **Action:** Change to `admin.set_password(os.environ["ADMIN_PASSWORD"])` to stay in sync with the environment variable set at line 7.
- **Verify:** E2E tests still pass with `ADMIN_PASSWORD=test-password`.

### 1.9 — Fix `subscribe.py:204` missing OperationalError handling
- **Priority:** High
- **File:** `app/routes/public/subscribe.py:203-204`
- **Current:** `db.session.commit()` has no try/except for OperationalError, unlike every other commit in this file.
- **Action:** Wrap in `try/except (IntegrityError, OperationalError)` matching the pattern used elsewhere in the file.
- **Verify:** Existing tests pass; error path doesn't propagate unhandled.

### 1.10 — Fix `admin/auth.py:272` setup_2fa confusing TOTP validation
- **Priority:** High
- **File:** `app/routes/admin/auth.py:272-277`
- **Current:** Checks `if secret and pyotp.TOTP(secret).verify(token)` — if the token validates against the existing secret, it says "2FA is already enabled." This is confusing because the user is on the setup page.
- **Action:** Replace with `if user.totp_enabled:` check. If 2FA is already enabled, redirect with info message.
- **Verify:** Test 2FA setup flow: enabling when not enabled, and visiting setup when already enabled.

### 1.11 — Fix `send_newsletter_task` variable leak
- **Priority:** High (was Medium, elevated because it's a real code smell)
- **File:** `app/tasks.py:190`
- **Current:** `post.newsletter_attempts` references the loop variable after the `for post in posts` loop. Safe in practice (early return at line 152 ensures non-empty), but brittle.
- **Action:** Track `last_attempts` variable during the loop, or move the warning inside the loop body.
- **Verify:** Newsletter task still logs correctly; no UnboundLocalError on edge cases.

---

## Wave 2: High & Medium Documentation Corrections

These fix factual errors in architecture documentation. All items are independent. These should be done alongside or after Wave 1 so docs reference correct code.

### 2.1 — Fix nginx proxy_pass documentation
- **Priority:** High
- **File:** `architecture/deployment/docker.md:298`
- **Current:** Claims `proxy_pass http://127.0.0.1:5000`
- **Action:** Change to `proxy_pass http://blog:5000` matching `nginx/conf.d/blog.conf:52`.

### 2.2 — Fix template inheritance documentation
- **Priority:** High
- **File:** `architecture/frontend/templates.md:71,73`
- **Current:** Claims `admin/base.html` and `admin/login_base.html` extend `base.html`
- **Action:** Rewrite Template Inheritance section to document 3 standalone base templates. Note that `admin/base.html` and `admin/login_base.html` each have `<!DOCTYPE html>` and are fully independent. Add note about triple duplication maintenance risk.

### 2.3 — Fix `marked.min.js` loading documentation
- **Priority:** High
- **File:** `architecture/frontend/static-assets.md:135-139`
- **Current:** Claims `marked.min.js` is loaded outside Vite via `url_for('static', ...)`
- **Action:** Correct to state that both `base.html:150` and `admin/base.html:162` use `vite_asset('js/lib/marked.min.js')`.

### 2.4 — Fix SSRF source file reference
- **Priority:** High
- **File:** `architecture/overview.md:299`
- **Current:** Claims SSRF protection is at `app/webhooks.py`
- **Action:** Change to `app/utils.py:383-485` where `is_safe_webhook_url()` is actually defined.

### 2.5 — Fix encryption function names
- **Priority:** Medium
- **File:** `architecture/services/encryption.md:17`
- **Current:** Claims functions are `encrypt_secret()` and `decrypt_secret()`
- **Action:** Change to `encrypt()` and `decrypt()` matching `app/services/encryption.py:41,69`.

### 2.6 — Fix Cache-Control line number
- **Priority:** Low
- **File:** `architecture/routes/rss-feeds.md:236`
- **Current:** References `rss.py:98`
- **Action:** Change to `rss.py:90` (inside `_add_cache_headers()` function).

### 2.7 — Fix stale line numbers in tag_cache.md
- **Priority:** Low
- **File:** `architecture/services/tag_cache.md:31,33`
- **Current:** `editor.py:89,204` and `manage.py:82`
- **Action:** Verify actual line numbers against current code and update.

### 2.8 — Fix stale line numbers in scheduler.md
- **Priority:** Low
- **File:** `architecture/tasks/scheduler.md:53,64-68`
- **Current:** "inline `run_daily_backup()`" and off-by-one task file line references
- **Action:** Fix wording to "imports from `app.services.backup`" and correct line numbers.

### 2.9 — Fix `clean_analytics_cache` source attribution
- **Priority:** Medium
- **File:** `architecture/testing/test-suite.md:42`
- **Current:** Attributes `clean_analytics_cache` to `conftest.py`
- **Action:** Change to `tests/shared_fixtures.py:17-24` where it's actually defined.

### 2.10 — Update test file count
- **Priority:** Low
- **File:** `tests/AGENTS.override.md:35,60`
- **Current:** Claims "~36 test files"
- **Action:** Change to "~30" (actual count: 28 in tests/ root + 2 in subdirectories = 30).

---

## Wave 3: Medium Source Code Fixes

These are source code improvements that are not critical bugs but improve correctness, robustness, or developer experience. All items are independent.

### 3.1 — Make `login_base.html` use `syntax_theme` variable
- **Priority:** Medium
- **File:** `app/templates/admin/login_base.html:8`
- **Current:** Hardcodes `css/prism-okaidia.css`
- **Action:** Change to `css/{{ syntax_theme }}.css` to respect user's configured syntax theme.

### 3.2 — Use `vite_asset()` for Prism JS in `loadPrismIfNeeded()`
- **Priority:** Medium
- **File:** `app/static/js/main.js:106,109`
- **Current:** Hardcodes `/static/js/prism.min.js` and `/static/js/prism-languages.js`
- **Action:** Use a data attribute or Vite-resolved URL instead of hardcoded paths. Options: (a) pass Vite URLs via a data attribute on a script tag, or (b) use `import()` with dynamic paths that Vite can resolve.

### 3.3 — Fix `post_image_srcset` hardcoded path
- **Priority:** Medium
- **File:** `app/filters.py:72`
- **Current:** Hardcodes `f"{base_url.rstrip('/')}/static/uploads/{variant_name}"`
- **Action:** Replace with `url_for('static', filename=f'uploads/{variant_name}')` or a storage-aware URL builder.

### 3.4 — Fix hardcoded Expires header in rss.py
- **Priority:** Medium
- **File:** `app/routes/rss.py:91`
- **Current:** `response.headers["Expires"] = "Thu, 01 Jan 2027 00:00:00 GMT"` (fixed date)
- **Action:** Either dynamically calculate expiry (now + max-age) or remove in favor of `Cache-Control: max-age=3600` which is already set at line 90.

### 3.5 — Replace `__import__("datetime")` hack
- **Priority:** Medium
- **File:** `app/routes/api/subscribers.py:103`
- **Current:** Uses `__import__("datetime").timedelta(...)` instead of a normal import
- **Action:** Add `from datetime import timedelta` at the top of the file and use `timedelta(...)` directly.

### 3.6 — Log webhook exceptions instead of swallowing
- **Priority:** Medium
- **Files:** `app/routes/api/posts.py:314`, `app/routes/public/subscribe.py:183`
- **Current:** Bare `except Exception: pass` around `create_webhook_event` calls
- **Action:** Replace with `except Exception: logger.warning("Webhook event creation failed", exc_info=True)` (or similar logging).

### 3.7 — Fix `get_indexed_terms_fallback()` sorting
- **Priority:** Medium
- **File:** `app/search.py:241`
- **Current:** `return list(set(terms))` — unordered
- **Action:** Change to `return sorted(set(terms))` for consistent autocomplete behavior.

### 3.8 — Add `critical.css` to admin base template
- **Priority:** Medium
- **File:** `app/templates/admin/base.html`
- **Current:** Admin pages don't load `critical.css`, missing above-the-fold optimization
- **Action:** Add `{{ vite_asset('css/critical.css') }}` with `media="screen"` similar to `base.html:24`.

### 3.9 — Remove unnecessary Prism JS from login page
- **Priority:** Medium
- **File:** `app/templates/admin/login_base.html:56-57`
- **Current:** Loads `prism.min.js` and `prism-languages.js` eagerly on login pages (no code blocks)
- **Action:** Remove the Prism script tags. Login pages don't need syntax highlighting.

### 3.10 — Fix `browse.py:277` f-string in logging
- **Priority:** Low
- **File:** `app/routes/public/browse.py:277`
- **Current:** `logging.warning(f"FTS returned invalid results: {post_results}")`
- **Action:** Change to `logging.warning("FTS returned invalid results: %s", post_results)` for lazy evaluation.

---

## Wave 4: Medium Documentation Additions

These add missing documentation. All items are independent.

### 4.1 — Document rate limiting across all routes
- **Priority:** High
- **File:** `architecture/routes/admin-routes.md` (or new section)
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

### 4.2 — Document CSRF scope for API clients
- **Priority:** High
- **File:** `architecture/overview.md` Security section
- **Action:** Document that CSRF applies to ALL POST requests including API endpoints. API clients using Bearer tokens (ApiToken) don't have Flask sessions with CSRF tokens, so POST requests would get 403. Note this as a known interaction.

### 4.3 — Document ETag/conditional GET for feeds
- **Priority:** Medium
- **File:** `architecture/routes/rss-feeds.md`
- **Action:** Document that all feed endpoints implement `If-None-Match` / `304 Not Modified` responses for efficient caching.

### 4.4 — Document token enumeration protection
- **Priority:** Medium
- **File:** `architecture/routes/public-routes.md`
- **Action:** Note that subscribe confirm/unsubscribe routes use `time.sleep(TOKEN_ENUMERATION_DELAY)` to prevent token enumeration attacks.

### 4.5 — Document search fallback behavior
- **Priority:** Medium
- **File:** `architecture/infrastructure/search.md` (or `architecture/routes/public-routes.md`)
- **Action:** Document that FTS search falls back to ILIKE when FTS returns no results, and that "did you mean" suggestions are provided via `get_did_you_mean()`.

### 4.6 — Document X-Forwarded-For trust assumption
- **Priority:** Medium
- **File:** `architecture/routes/public-routes.md` or comments section
- **Action:** Note that comment rate limiting uses `X-Forwarded-For` header for IP detection. If behind a trusted proxy that doesn't sanitize this header, rate limiting can be bypassed.

### 4.7 — Document admin session IP binding modes
- **Priority:** Medium
- **File:** `architecture/routes/admin-routes.md`
- **Action:** Document enforce/warn modes for `SESSION_IP_BINDING` and their behavioral differences (enforce: invalidates session; warn: logs only).

### 4.8 — Document health check endpoint
- **Priority:** Medium
- **File:** New file `architecture/infrastructure/health.md` or add to `overview.md`
- **Action:** Document `/health` endpoint at `app/routes/public/meta.py:188-321` with all check types (DB, scheduler, FTS, disk, integrity, Redis, Celery, backup freshness) and `?detailed=true&secret=<key>` authentication.

### 4.9 — Create `architecture/infrastructure/overview.md`
- **Priority:** Medium
- **File:** `architecture/infrastructure/overview.md`
- **Action:** Create overview doc describing how search, email, storage, webhooks, and health checks interact. Currently each doc is siloed.

### 4.10 — Document `Post.published` and `Page.published` nullable issue
- **Priority:** Medium
- **File:** `architecture/core/models.md`
- **Action:** Note that `Post.published` and `Page.published` columns allow NULL despite documented intent of `nullable=False`. Reference the fix in Wave 1.

### 4.11 — Document health check authentication
- **Priority:** Medium
- **File:** `architecture/overview.md` or health check doc
- **Action:** Note that `?detailed=true` requires `?secret=<HEALTH_CHECK_SECRET>` parameter for authenticated detailed results.

### 4.12 — Document admin template independence
- **Priority:** Medium
- **File:** `architecture/frontend/templates.md`
- **Action:** Add note that `admin/base.html` and `admin/login_base.html` are standalone templates, not extending `base.html`. This is a critical architectural detail for template maintenance.

---

## Wave 5: Low Source Code Improvements

These are minor improvements. All items are independent.

### 5.1 — Remove unnecessary `SQLAlchemyError` catch
- **Priority:** Low
- **File:** `app/services/backup.py:113`
- **Current:** Catches `SQLAlchemyError` in `_encrypt_backup_file`, but the underlying function only raises `OSError`, `ValueError`, `RuntimeError`.
- **Action:** Remove `SQLAlchemyError` from the exception tuple.

### 5.2 — Replace string comparison with `isinstance()` for storage backend
- **Priority:** Low
- **File:** `app/tasks.py:42,71`
- **Current:** `storage.__class__.__name__ == "LocalStorageBackend"` / `"S3StorageBackend"`
- **Action:** Use `isinstance(storage, LocalStorageBackend)` instead.

### 5.3 — Add word boundary to `highlight_query()` regex
- **Priority:** Low
- **File:** `app/search.py:362`
- **Current:** `re.escape(query)` without word boundary — highlights "cat" inside "category"
- **Action:** Use `\b` word boundary: `r'\b' + re.escape(query) + r'\b'` (unless partial matching is desired, in which case document it).

### 5.4 — Fix `highlight_query()` docstring
- **Priority:** Low
- **File:** `app/search.py:354`
- **Current:** Docstring says "(may contain HTML)" but docs say "input text should be raw text, not pre-escaped HTML"
- **Action:** Align docstring with documentation: clarify that input should be raw text.

### 5.5 — Remove dead `max_retries`/`retry_backoff` from non-retrying tasks
- **Priority:** Low
- **File:** `app/tasks.py:30,390`
- **Current:** `generate_image_variants` and `run_backup_task` have `max_retries` configured but never call `self.retry()`
- **Action:** Remove `max_retries` and `retry_backoff` from these task decorators, or add actual retry logic if retries are desired.

### 5.6 — Fix `media.py` redundant `get_storage()` call
- **Priority:** Low
- **File:** `app/routes/admin/media.py:66-97`
- **Current:** `_scan_media_directory` calls `get_storage()` twice (lines 68-69 and 72-73) inside the loop
- **Action:** Remove the duplicate call.

### 5.7 — Fix `errors.py:62-68` 413 redirect logic
- **Priority:** Low
- **File:** `app/routes/errors.py:62-68`
- **Current:** 413 handler redirects to `req.referrer or url_for("admin.dashboard")` — public users hitting 413 would be redirected to admin dashboard
- **Action:** Check if referrer is an admin URL first; otherwise redirect to home page.

### 5.8 — Consolidate `slow` marker registration
- **Priority:** Low
- **Files:** `pytest.ini:3`, `tests/conftest.py:20-23`
- **Current:** `slow` marker registered in both `pytest.ini` and `conftest.py`
- **Action:** Remove from `pytest.ini:3` since `conftest.py` handles it via `pytest_configure`.

### 5.9 — Make `cleanup_uploads` path more robust
- **Priority:** Low
- **File:** `tests/conftest.py:202`
- **Current:** Uses fragile relative path via `__file__`
- **Action:** Use project root detection (e.g., from `pyproject.toml` or a known marker file) or add logging if path doesn't exist.

### 5.10 — Remove or differentiate `api_client` fixture
- **Priority:** Low
- **File:** `tests/conftest.py:120-130`
- **Current:** Functionally identical to `authenticated_client` — both just login via POST
- **Action:** Either remove `api_client` or differentiate it (e.g., set an API key header for API-specific tests).

### 5.11 — Review `SiteSettings.get_instance()` unconditional commit
- **Priority:** Low
- **File:** `app/models.py:359`
- **Current:** `db.session.commit()` unconditionally when creating new instance — could commit outer transaction's uncommitted changes
- **Action:** Consider using `db.session.merge()` or check-then-create pattern.

### 5.12 — Add `SEARCH_PROVIDER` and `SEARCH_CONFIG` to `__all__`
- **Priority:** Low
- **File:** `app/config.py:6-61`
- **Current:** These are defined at lines 173-174 but not in `__all__`
- **Action:** Add to `__all__` if they are considered public API.

---

## Wave 6: Low Documentation & Cleanup

These are minor documentation additions. All items are independent.

### 6.1 — Document error handler routes
- **Priority:** Low
- **File:** `architecture/routes/public-routes.md`
- **Action:** Add section covering error handlers in `app/routes/errors.py` (404, 500, 413).

### 6.2 — Document series feed ordering
- **Priority:** Low
- **File:** `architecture/routes/rss-feeds.md`
- **Action:** Note that series feeds preserve `PostSeries.order_index` ordering rather than date ordering.

### 6.3 — Document backup verify JSON return format
- **Priority:** Low
- **File:** `architecture/routes/admin-routes.md`
- **Action:** Document that verify endpoints return JSON with `valid` and `message` fields.

### 6.4 — Document available syntax themes in settings
- **Priority:** Low
- **File:** `architecture/routes/admin-routes.md`
- **Action:** Document the 4 available syntax themes (github-dark, github-light, solarized-dark, monokai).

### 6.5 — Document unschedule bulk action
- **Priority:** Low
- **File:** `architecture/routes/admin-routes.md`
- **Action:** Document the unschedule action in admin bulk operations.

### 6.6 — Document subscriber bulk resend
- **Priority:** Low
- **File:** `architecture/routes/admin-routes.md`
- **Action:** Document the "resend" action in subscriber bulk operations.

### 6.7 — Add required environment variables summary
- **Priority:** Low
- **File:** `architecture/overview.md`
- **Action:** List critical env vars: SECRET_KEY, ADMIN_PASSWORD, SMTP_HOST, REDIS_URL, HEALTH_CHECK_SECRET with purposes.

### 6.8 — Document `app/page_view_buffer.py`
- **Priority:** Low
- **File:** `architecture/overview.md` or `architecture/core/app-factory.md`
- **Action:** Document daemon thread mechanics, configurable buffer size via `PAGE_VIEW_BUFFER_SIZE`.

### 6.9 — Document `marked.min.js` uses `vite_asset()`
- **Priority:** Low
- **File:** `architecture/frontend/static-assets.md`
- **Action:** Ensure Frontend section notes all JS assets use `vite_asset()`.

### 6.10 — Add utility file descriptions to directory structure
- **Priority:** Low
- **File:** `architecture/overview.md`
- **Action:** Add purpose descriptions for `app/backup_integrity.py`, `app/base62.py`, `app/csv_utils.py`, `app/markdown_config.py`, `app/transaction.py`.

### 6.11 — Document `_update_delivery_status` function
- **Priority:** Low
- **File:** `architecture/tasks/celery-tasks.md`
- **Action:** Document the delivery status determination logic and its `--concurrency=1` dependency.

### 6.12 — Document fire-and-forget dispatch pattern
- **Priority:** Low
- **File:** `architecture/tasks/celery-tasks.md`
- **Action:** Note that `deliver_webhook_task` uses `.delay()` (fire-and-forget); parent success doesn't indicate child delivery success.

### 6.13 — Document `Subscriber`, `Tag`, `PageView`, `ShareEvent` models
- **Priority:** Low
- **File:** `architecture/core/models.md`
- **Action:** Add detailed model sections for these 4 models (field definitions, relationships, purposes).

### 6.14 — Document `app/validators.py` location
- **Priority:** Low
- **File:** `architecture/overview.md`
- **Action:** Note that validators are at `app/validators.py` (NOT `app/core/validators.py`).

---

## Cross-Cutting Concerns

These items span multiple files and should be addressed as part of the relevant waves:

### CSRF Scope Investigation
- **Priority:** High
- **Files:** `app/__init__.py:297-298`, `app/routes/api/auth.py`
- **Issue:** CSRF is enforced for ALL POST requests globally, including API endpoints. API clients using Bearer tokens don't have Flask sessions with CSRF tokens.
- **Action:** Investigate whether this is intentional (defense-in-depth) or if API routes should be exempt. Document the behavior regardless.

### Post.published Nullable Migration
- **Files:** `app/models.py:196,166`, `app/cli.py` (seed command)
- **Note:** Wave 1 items 1.2 and 1.3 require database migrations. The seed command at `app/cli.py:267` has `--published/--draft` flags which should continue working after the migration.

---

## Verification Checklist

After all waves are complete, verify:

1. `ruff check .` — no new lint errors
2. `ruff format --check .` — formatting preserved
3. `mypy app/` — no new type errors
4. `ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/` — all tests pass
5. Manual review of changed architecture docs for accuracy
6. `docker compose config` — verify SMTP_HOST in celery service
