# Consolidated Architecture Improvement Plan

**Created:** 2026-06-02
**Status:** IN PROGRESS — Waves 1-4 completed (69 items). Waves 5-7 pending (66 new items from review consolidation).
**Verified:** 2026-06-02 — All claims verified against actual codebase via subagent exploration.

---

## How to Execute This Plan

This plan contains 135 action items organized into 7 parallelizable waves. Items within each wave are fully independent and can be executed concurrently using subagents. Waves have soft dependencies: source code changes should land before documentation that references the corrected code.

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

## Wave 1: Source Code Fixes (11 items) — COMPLETED

These fixed actual bugs, data integrity issues, and code quality problems. All items are independent and were parallelized.

### 1.1 — Remove `_invalidate_all_caches()` dead code
- **Status:** COMPLETED
- **File:** `app/routes/admin/__init__.py:62-76`

### 1.2 — Add `nullable=False` to `Post.published`
- **Status:** COMPLETED
- **File:** `app/models.py:196`

### 1.3 — Add `nullable=False` to `Page.published`
- **Status:** COMPLETED
- **File:** `app/models.py:166`

### 1.4 — Add `nullable=False` to `User.failed_login_count`
- **Status:** COMPLETED
- **File:** `app/models.py:31`

### 1.5 — Fix in-place encryption to use temp file pattern
- **Status:** COMPLETED
- **File:** `app/services/backup.py:98-115`

### 1.6 — Add `SMTP_HOST` to celery service in docker-compose.yml
- **Status:** COMPLETED
- **File:** `docker-compose.yml`

### 1.7 — Fix benchmark Celery configuration
- **Status:** COMPLETED
- **File:** `tests/benchmarks/conftest.py`

### 1.8 — Use env var for E2E admin password
- **Status:** COMPLETED
- **File:** `tests/e2e/conftest.py:75`

### 1.9 — Fix `subscribe.py:204` missing OperationalError handling
- **Status:** COMPLETED
- **File:** `app/routes/public/subscribe.py:201-204`

### 1.10 — Fix `setup_2fa` confusing TOTP validation
- **Status:** COMPLETED
- **File:** `app/routes/admin/auth.py:272-277`

### 1.11 — Fix `send_newsletter_task` variable leak
- **Status:** COMPLETED
- **File:** `app/tasks.py:183-191`

---

## Wave 2: Documentation Corrections (12 items) — COMPLETED

These fixed factual errors in architecture documentation.

### 2.1 — Fix nginx proxy_pass documentation
- **Status:** COMPLETED
- **File:** `architecture/deployment/docker.md:298`

### 2.2 — Fix template inheritance documentation
- **Status:** COMPLETED
- **File:** `architecture/frontend/templates.md:71,73`

### 2.3 — Fix `marked.min.js` loading documentation
- **Status:** COMPLETED
- **File:** `architecture/frontend/static-assets.md:135-139`

### 2.4 — Fix SSRF source file reference
- **Status:** COMPLETED
- **File:** `architecture/overview.md:299`

### 2.5 — Fix encryption function names
- **Status:** COMPLETED
- **File:** `architecture/services/encryption.md:17`

### 2.6 — Fix Cache-Control line number
- **Status:** COMPLETED
- **File:** `architecture/routes/rss-feeds.md:236`

### 2.7 — Fix stale line numbers in tag_cache.md
- **Status:** COMPLETED
- **File:** `architecture/services/tag_cache.md:31,33`

### 2.8 — Fix stale line numbers and wording in scheduler.md
- **Status:** COMPLETED
- **File:** `architecture/tasks/scheduler.md:53,64-68`

### 2.9 — Fix `clean_analytics_cache` source attribution
- **Status:** COMPLETED
- **File:** `architecture/testing/test-suite.md:42`

### 2.10 — Fix test file count
- **Status:** COMPLETED
- **File:** `tests/AGENTS.override.md:35,60`

### 2.11 — Document rate limiting across all routes
- **Status:** COMPLETED
- **File:** `architecture/routes/admin-routes.md`

### 2.12 — Document CSRF scope for API clients
- **Status:** COMPLETED
- **File:** `architecture/overview.md` Security section

---

## Wave 3: Source Code Improvements (12 items) — COMPLETED

These were code quality improvements.

### 3.1 — Make `login_base.html` use `syntax_theme` variable
- **Status:** COMPLETED
- **File:** `app/templates/admin/login_base.html:8`

### 3.2 — Use `vite_asset()` for Prism JS in `loadPrismIfNeeded()`
- **Status:** COMPLETED
- **File:** `app/static/js/main.js:106,109`

### 3.3 — Fix `post_image_srcset` hardcoded path
- **Status:** COMPLETED
- **File:** `app/filters.py:72`

### 3.4 — Fix hardcoded Expires header in rss.py
- **Status:** COMPLETED
- **File:** `app/routes/rss.py:91`

### 3.5 — Replace `__import__("datetime")` hack
- **Status:** COMPLETED
- **File:** `app/routes/api/subscribers.py:103`

### 3.6 — Log webhook exceptions instead of swallowing
- **Status:** COMPLETED
- **Files:** `app/routes/api/posts.py:314-315`, `app/routes/public/subscribe.py:183-184`

### 3.7 — Fix `get_indexed_terms_fallback()` sorting
- **Status:** COMPLETED
- **File:** `app/search.py:241`

### 3.8 — Add `critical.css` to admin base template
- **Status:** COMPLETED
- **File:** `app/templates/admin/base.html`

### 3.9 — Remove unnecessary Prism JS from login page
- **Status:** COMPLETED
- **File:** `app/templates/admin/login_base.html:56-57`

### 3.10 — Fix `browse.py:277` f-string in logging
- **Status:** COMPLETED
- **File:** `app/routes/public/browse.py:277`

### 3.11 — Remove unnecessary `SQLAlchemyError` catch
- **Status:** COMPLETED
- **File:** `app/services/backup.py:113`

### 3.12 — Replace string comparison with `isinstance()` for storage backend
- **Status:** COMPLETED
- **File:** `app/tasks.py:42,71`

---

## Wave 4: Documentation Additions & Cleanup (34 items) — COMPLETED

These added missing documentation and made minor improvements.

### 4.1-4.34 — All items COMPLETED
- **Status:** COMPLETED
- See original plan for individual item details.

---

## Wave 5: Additional Source Code Fixes (10 items) — All Independent

These fix actual bugs, data integrity issues, and code quality problems discovered during review. All items are independent and can be parallelized.

### 5.1 — Fix or remove dead `max_retries` in `send_newsletter_task`
- **Priority:** High
- **File:** `app/tasks.py:129-136`
- **Issue:** `max_retries=3, retry_backoff=True` is configured but `send_newsletter()` returns `False` on failure, never raising an exception. Celery auto-retry only fires on raised exceptions — this config is ineffective.
- **Action:** Either (a) add explicit `self.retry()` call when `send_newsletter()` returns `False`, OR (b) remove the ineffective `max_retries` and `retry_backoff` from the decorator. Option (a) is preferred for resilience.
- **Verify:** `ruff check app/tasks.py` passes; newsletter task retries on failure or config is removed.

### 5.2 — Add `newsletter_attempts` upper bound check
- **Priority:** High
- **File:** `app/tasks.py:186`
- **Issue:** In `send_newsletter_task` failure path, `newsletter_attempts` is incremented without upper bound, unlike the scheduler which caps at `NEWSLETTER_MAX_RETRY_ATTEMPTS` at `app/scheduler.py:118`.
- **Action:** Use `min((post.newsletter_attempts or 0) + 1, NEWSLETTER_MAX_RETRY_ATTEMPTS)` in the increment logic to match scheduler behavior.
- **Verify:** Newsletter attempts capped at `NEWSLETTER_MAX_RETRY_ATTEMPTS`; `ruff check app/tasks.py` passes.

### 5.3 — Add `db.session.remove()` to `generate_image_variants` and `run_backup_task`
- **Priority:** Medium
- **File:** `app/tasks.py:30` (generate_image_variants), `app/tasks.py:392` (run_backup_task)
- **Issue:** These tasks lack the `db.session.remove()` pattern used by other Celery tasks for proper session cleanup.
- **Action:** Add `db.session.remove()` in a try/finally block after task logic, matching the pattern used by other Celery tasks in this file.
- **Verify:** `ruff check app/tasks.py` passes.

### 5.4 — Add `CRYPTOGRAPHY_AVAILABLE` check to `encryption.py`
- **Priority:** High
- **File:** `app/services/encryption.py`
- **Issue:** Lacks the `CRYPTOGRAPHY_AVAILABLE` check present in `backup_encryption.py` and `webhook_encryption.py`. When cryptography library is not installed, errors are confusing.
- **Action:** Add a top-of-file check similar to other encryption modules: if cryptography is not available, define stub functions that raise `EncryptionError` with a clear message about installing cryptography.
- **Verify:** Import fails with clear error when cryptography not installed; existing tests pass.

### 5.5 — Remove unnecessary `SQLAlchemyError` catch in `backup.py`
- **Priority:** Low
- **File:** `app/services/backup.py:141`
- **Issue:** Catches `SQLAlchemyError` in `decrypt_backup_file` but the operation is purely file I/O — no database operations are performed.
- **Action:** Remove `SQLAlchemyError` from the exception tuple at line 141, keeping only `OSError`, `ValueError`, `RuntimeError`.
- **Verify:** `ruff check app/services/backup.py` passes.

### 5.6 — Validate raw string key length in `webhook_encryption.py`
- **Priority:** Medium
- **File:** `app/webhook_encryption.py`
- **Issue:** Accepts raw string keys that are not exactly 32 bytes. Unlike hex keys (64 chars), raw strings bypass length validation, creating a security risk.
- **Action:** Add validation that raw string keys must be exactly 32 bytes. Raise `EncryptionError` for keys of incorrect length, similar to hex key validation.
- **Verify:** Raw string keys of wrong length raise `EncryptionError`; `ruff check app/webhook_encryption.py` passes.

### 5.7 — Add pagination to `GET /api/series`
- **Priority:** Medium
- **File:** `app/routes/api/series.py:60-61`
- **Issue:** Returns ALL series without pagination (uses `.all()` with no limit/offset), causing performance issues with large datasets.
- **Action:** Add pagination with `page` and `per_page` query parameters, returning `{"series": [...], "total": N, "page": N, "per_page": N}` format consistent with other API endpoints.
- **Verify:** API returns paginated response; `ruff check app/routes/api/series.py` passes.

### 5.8 — Consider clock skew tolerance for preview token expiry
- **Priority:** Low
- **File:** `app/routes/public/posts.py:121`
- **Issue:** Uses `time() > expires` without tolerance. Clock skew between servers can cause valid tokens to be rejected.
- **Action:** Add a small tolerance (e.g., `time() > expires + CLOCK_SKEW_TOLERANCE`) or make tolerance configurable. Default tolerance of 30-60 seconds is recommended.
- **Verify:** Preview tokens work across servers with minor clock skew; `ruff check app/routes/public/posts.py` passes.

### 5.9 — Consider `SELECT FOR UPDATE` on `SiteSettings.get_instance()`
- **Priority:** Medium
- **File:** `app/models.py:354-360`
- **Issue:** Potential race condition when two requests simultaneously create a new `SiteSettings` instance. The unconditional `db.session.commit()` compounds this.
- **Action:** Add `with_for_update()` to the query in `get_instance()` to prevent concurrent creation races:
  ```python
  instance = cls.query.filter_by(id=1).with_for_update().first()
  ```
- **Verify:** Concurrent `SiteSettings.get_instance()` calls don't create duplicate rows; `mypy app/models.py` passes.

### 5.10 — Document key padding behavior in `encryption.py`
- **Priority:** Medium
- **File:** `app/services/encryption.py:36-38`
- **Issue:** Keys shorter than 32 bytes are silently padded with null bytes. This behavior is not documented and could lead to security misunderstandings.
- **Action:** Either (a) raise `EncryptionError` for keys shorter than 32 bytes, OR (b) add a docstring explaining the null-byte padding behavior. Option (a) is preferred for security clarity.
- **Verify:** Short keys raise `EncryptionError` with clear message, OR padding behavior is documented in docstring; `ruff check app/services/encryption.py` passes.

---

## Wave 6: Additional Documentation Corrections (41 items) — All Independent

These fix factual errors and fill documentation gaps discovered during review of architecture documentation. All items are independent and can be parallelized.

### High Priority

#### 6.1 — Fix celery-tasks.md decorator documentation for generate_image_variants
- **Priority:** High
- **File:** `architecture/tasks/celery-tasks.md`
- **Current:** Documents `max_retries=3` for `generate_image_variants`
- **Correct:** Actual task at `app/tasks.py:30` has NO retry configuration (`max_retries` not set). Remove retry documentation for this task.
- **Source:** tasks_review.md item 3, architecture_prune.md item 3

#### 6.2 — Fix celery-tasks.md decorator documentation for run_backup_task
- **Priority:** High
- **File:** `architecture/tasks/celery-tasks.md`
- **Current:** Documents `max_retries=2` for `run_backup_task`
- **Correct:** Actual task at `app/tasks.py:390` has NO retry configuration. Remove retry documentation for this task.
- **Source:** tasks_review.md item 4, architecture_prune.md item 4

#### 6.3 — Fix send_newsletter_task retry documentation
- **Priority:** High
- **File:** `architecture/tasks/celery-tasks.md`
- **Current:** Says "no explicit retry" for `send_newsletter_task`
- **Correct:** `app/tasks.py:137` has `max_retries=3` configured (even though ineffective due to implementation). Clarify or update to reflect actual config.
- **Source:** tasks_review.md item 7

#### 6.4 — Fix celery-tasks.md line references
- **Priority:** High
- **File:** `architecture/tasks/celery-tasks.md`
- **Current:** `send_newsletter_task` at line 137, `generate_image_variants` at line 31
- **Correct:** `send_newsletter_task` at line 129, `generate_image_variants` at line 30
- **Source:** tasks_review.md item 2

#### 6.5 — Clarify tag_cache.md scheduler line references
- **Priority:** High
- **File:** `architecture/services/tag_cache.md`
- **Current:** Single line reference for scheduler import
- **Correct:** Distinguish between import at line 224 and call at line 256, or use symbolic references to avoid drift.
- **Source:** services_review.md item 1

#### 6.6 — Document internal search functions
- **Priority:** High
- **File:** `architecture/services/search.md`
- **Current:** `extract_snippet`, `get_search_snippets`, `_escape_fts_term`, `get_indexed_terms_fallback` not documented
- **Correct:** Note these functions are not in `__all__` and are internal implementation details not intended for external use.
- **Source:** services_review.md item 6

#### 6.7 — Add note in backup.md distinguishing plain vs encrypted backups
- **Priority:** High
- **File:** `architecture/services/backup.md`
- **Current:** No distinction between backup types
- **Correct:** `run_daily_backup()` creates plain backups; `create_backup()` with `encrypt=True` creates encrypted backups. Document the difference.
- **Source:** services_review.md item 7

#### 6.8 — Fix THEME_PRESETS vs syntax themes confusion
- **Priority:** High
- **File:** `architecture/routes/admin-routes.md:228`
- **Current:** Claims github-dark, github-light, solarized-dark, monokai are syntax themes
- **Correct:** These are CSS color schemes. Actual syntax themes are Prism-based: prism, prism-coy, prism-dark, etc. at `app/config.py:24-31`.
- **Source:** routes_review.md item 1, architecture_prune.md item 6

#### 6.9 — Document API CSRF enforcement
- **Priority:** High
- **File:** `architecture/overview.md` Security section
- **Current:** No mention of API CSRF scope
- **Correct:** CSRF applies to ALL POST requests including API endpoints. API clients using Bearer tokens (ApiToken) don't have Flask sessions with CSRF tokens, so POST requests get 403.
- **Source:** routes_review.md item 2

#### 6.10 — Document rate limit configuration keys
- **Priority:** High
- **File:** `architecture/routes/public-routes.md` (comments section)
- **Current:** No mention of configurable rate limit keys
- **Correct:** Document `COMMENT_RATE_LIMIT_PER_IP` and `COMMENT_RATE_LIMIT_PER_POST` from `app/config.py`.
- **Source:** routes_review.md item 4

#### 6.11 — Add API scope requirements table
- **Priority:** High
- **File:** `architecture/routes/api.md` or `architecture/overview.md`
- **Current:** No scope requirements documented
- **Correct:** Add table showing scopes required for each endpoint (posts:read, posts:write, subscribers:read, subscribers:write, stats:read).
- **Source:** routes_review.md item 5

#### 6.12 — Add preview token generation documentation
- **Priority:** High
- **File:** `architecture/routes/admin-routes.md`
- **Current:** No documentation of preview token generation
- **Correct:** Document HMAC-SHA256 generation process for preview links (`app/routes/admin/posts/__init__.py`).
- **Source:** routes_review.md item 6

#### 6.13 — Document webhook delivery architecture
- **Priority:** High
- **File:** `architecture/services/webhooks.md`
- **Current:** Single-level dispatch documented
- **Correct:** Document two-level dispatch pattern: `deliver_webhook_task` dispatches to `deliver_single_webhook_task`. Retry count default is 5.
- **Source:** routes_review.md item 8

#### 6.14 — Update line number references to use function names
- **Priority:** High
- **Files:** Multiple architecture docs
- **Current:** Hard-coded line numbers throughout documentation
- **Correct:** Use symbolic references (function names, decorator patterns) instead of line numbers to reduce drift.
- **Source:** routes_review.md item 9, multiple reviews

### Medium Priority

#### 6.15 — Update models.md Known Issues section
- **Priority:** Medium
- **File:** `architecture/core/models.md`
- **Current:** Lists nullable published columns issue as open
- **Correct:** Issue was FIXED in Wave 1 items 1.2, 1.3. Remove from Known Issues or mark as resolved.
- **Source:** core_review.md item 1

#### 6.16 — Fix User.failed_login_count documentation
- **Priority:** Medium
- **File:** `architecture/core/models.md`
- **Current:** Missing `nullable=False` specification
- **Correct:** Add `nullable=False` to `User.failed_login_count` documentation. Issue fixed in Wave 1 item 1.4.
- **Source:** core_review.md item 2

#### 6.17 — Clarify SiteSettings.get_instance() uses flush() not commit()
- **Priority:** Medium
- **File:** `architecture/core/models.md`
- **Current:** Claims `commit()` at line 359
- **Correct:** `app/models.py:359` uses `flush()`, not `commit()`. Document the distinction.
- **Source:** core_review.md item 3

#### 6.18 — Add APScheduler multi-container limitation to architecture docs
- **Priority:** Medium
- **File:** `architecture/overview.md` or `architecture/tasks/scheduler.md`
- **Current:** No mention of multi-container limitation
- **Correct:** APScheduler uses FileLock with `timeout=0` which only works on a single machine. Multiple container replicas will each run their own scheduler and execute jobs concurrently.
- **Source:** core_review.md item 4

#### 6.19 — Add Vite build requirement to architecture docs
- **Priority:** Medium
- **File:** `architecture/overview.md` or `architecture/frontend/static-assets.md`
- **Current:** No mention of build requirement
- **Correct:** `npm run build` (or `vite build`) must be run before production deployment. `manifest.json` must be present; hashed asset paths won't resolve without build.
- **Source:** core_review.md item 5

#### 6.20 — Document CSRF-on-API design decision
- **Priority:** Medium
- **File:** `architecture/overview.md` Security section
- **Current:** No rationale for CSRF on API
- **Correct:** Document CSRF applies to all POSTs including API as a known design decision (defense-in-depth).
- **Source:** core_review.md item 6

#### 6.21 — Add Docker Compose profile requirements to documentation
- **Priority:** Medium
- **File:** `architecture/deployment/docker.md`
- **Current:** No profile requirements documented
- **Correct:** All services require explicit profiles. `--profile production` for blog, celery, redis, nginx; `--profile backup` for backup service.
- **Source:** core_review.md item 7

#### 6.22 — Document comment rate limit X-Forwarded-For consideration
- **Priority:** Medium
- **File:** `architecture/routes/public-routes.md`
- **Current:** No proxy header warning
- **Correct:** Comment rate limiting uses `X-Forwarded-For` header at `app/routes/public/comments.py:24-32`. If behind a trusted proxy that doesn't sanitize this header, rate limiting can be bypassed.
- **Source:** core_review.md item 9

#### 6.23 — Clarify RATE_LIMIT_STORAGE_URI production default
- **Priority:** Medium
- **File:** `architecture/infrastructure/overview.md` or `architecture/overview.md`
- **Current:** No production default documented
- **Correct:** Production defaults to `redis://localhost:6379/1` when `FLASK_ENV=production`.
- **Source:** core_review.md item 10

#### 6.24 — Update webhooks.md line numbers
- **Priority:** Medium
- **File:** `architecture/services/webhooks.md`
- **Current:** `deliver_webhook_task` at line 200, `deliver_single_webhook_task` at line 231
- **Correct:** Verify and correct to actual line numbers in `app/tasks.py`.
- **Source:** infrastructure_review.md items 1-2

#### 6.25 — Update email.md line number
- **Priority:** Medium
- **File:** `architecture/services/email.md`
- **Current:** `NEWSLETTER_MAX_RETRY_ATTEMPTS` at config.py:118
- **Correct:** `NEWSLETTER_MAX_RETRY_ATTEMPTS` at `app/config.py:120`
- **Source:** infrastructure_review.md item 3

#### 6.26 — Update search.md line number
- **Priority:** Medium
- **File:** `architecture/services/search.md`
- **Current:** `get_indexed_terms_fallback` at line 229
- **Correct:** `get_indexed_terms_fallback` at line 230
- **Source:** infrastructure_review.md item 4

#### 6.27 — Document S3StorageBackend error handling limitation
- **Priority:** Medium
- **File:** `architecture/infrastructure/storage.md`
- **Current:** No error handling limitation documented
- **Correct:** `exists()` and `list_files()` return False/empty on any error; cannot distinguish 404 from network failure.
- **Source:** infrastructure_review.md item 5

#### 6.28 — Document get_storage_backend() vs get_storage() distinction
- **Priority:** Medium
- **File:** `architecture/infrastructure/storage.md`
- **Current:** Functions conflated
- **Correct:** `get_storage_backend()` is a factory function; `get_storage()` is a thread-safe singleton getter using double-checked locking.
- **Source:** infrastructure_review.md item 6

#### 6.29 — Document S3 credential fallback behavior
- **Priority:** Medium
- **File:** `architecture/infrastructure/storage.md`
- **Current:** No fallback behavior documented
- **Correct:** Falls back to local storage when S3 credentials are missing.
- **Source:** infrastructure_review.md item 7

#### 6.30 — Add webhook encryption section to webhooks.md
- **Priority:** Medium
- **File:** `architecture/services/webhooks.md`
- **Current:** No encryption documentation
- **Correct:** Document `encrypt_webhook_secret()` and `decrypt_webhook_secret()` functions.
- **Source:** infrastructure_review.md item 10

### Low Priority

#### 6.31 — Fix backup service line reference in docker.md
- **Priority:** Low
- **File:** `architecture/deployment/docker.md`
- **Current:** Backup service at lines 119-137
- **Correct:** Backup service at lines 120-140
- **Source:** deployment_review.md item 2

#### 6.32 — Document Redis health check in docker.md
- **Priority:** Low
- **File:** `architecture/deployment/docker.md`
- **Current:** No Redis health check documented
- **Correct:** `docker-compose.yml:91-95` defines Redis health check with `redis-cli ping`.
- **Source:** deployment_review.md item 4

#### 6.33 — Add missing nginx security headers OR remove from security.md
- **Priority:** Low
- **File:** `architecture/deployment/security.md`
- **Current:** Claims `X-Download-Options` and `X-Permitted-Cross-Domain-Policies` at `nginx/conf.d/blog.conf:25-32`
- **Correct:** These headers do NOT exist in nginx config. Either add them to nginx/conf.d/blog.conf OR remove from documentation.
- **Source:** deployment_review.md item 1, architecture_prune.md item 1

#### 6.34 — Fix prefetch.js description
- **Priority:** Low
- **File:** `architecture/frontend/static-assets.md`
- **Current:** Claims prefetch uses IntersectionObserver
- **Correct:** `app/static/js/prefetch.js` uses `mouseenter` with debounce, NOT IntersectionObserver.
- **Source:** frontend_review.md item 1

#### 6.35 — Document badge macro in macros.html
- **Priority:** Low
- **File:** `architecture/frontend/templates.md`
- **Current:** `badge(text, class='badge')` at lines 71-73 not documented
- **Correct:** Document the badge Jinja macro.
- **Source:** frontend_review.md item 2

#### 6.36 — Update line references in frontend docs
- **Priority:** Low
- **File:** `architecture/frontend/templates.md`
- **Current:** `admin/base.html` marked.min.js at line 162
- **Correct:** `admin/base.html` marked.min.js at line 163
- **Source:** frontend_review.md item 3

#### 6.37 — Add public/comments.html to directory structure
- **Priority:** Low
- **File:** `architecture/frontend/templates.md`
- **Current:** `app/templates/public/comments.html` not shown in directory structure
- **Correct:** Add to directory structure documentation.
- **Source:** frontend_review.md item 4

#### 6.38 — Document login template vite_asset() usage
- **Priority:** Low
- **File:** `architecture/frontend/templates.md`
- **Current:** No documentation of vite_asset() in login templates
- **Correct:** `admin/login_base.html` uses `vite_asset()` for CSS/JS, enabling CDN prefix support.
- **Source:** frontend_review.md item 5

#### 6.39 — Document api_client fixture
- **Priority:** Low
- **File:** `architecture/testing/test-suite.md`
- **Current:** `tests/conftest.py:120-130` not documented
- **Correct:** Document `api_client` fixture which is functionally identical to `authenticated_client`.
- **Source:** testing_review.md item 1

#### 6.40 — Document mock_email fixture
- **Priority:** Low
- **File:** `architecture/testing/test-suite.md`
- **Current:** `conftest.py:187-194` not documented
- **Correct:** Document `mock_email` fixture for email capture in tests.
- **Source:** testing_review.md item 4

#### 6.41 — Add note about sync_fts behavior in benchmark helpers
- **Priority:** Low
- **File:** `architecture/testing/test-suite.md`
- **Current:** No explanation of sync_fts behavior
- **Correct:** Note that `create_posts_bulk` and `create_subscribers_bulk` call `sync_fts` but behavior is not explained.
- **Source:** testing_review.md item 5

---

## Wave 7: Additional Source Code Improvements (15 items) — All Independent

These are code quality improvements, not critical bugs. All items are independent.

### 7.1 — Add URL protocol validation to prefetch.js
- **Priority:** Medium
- **File:** `app/static/js/prefetch.js:31`
- **Current:** Only checks `mailto:` and `tel:` protocols
- **Issue:** Does not validate `javascript:` or `data:` URLs which can be used for attacks
- **Action:** Extend the protocol validation to block `javascript:`, `data:`, and other dangerous protocols. Only allow `http:`, `https:`, and the intended exceptions (`mailto:`, `tel:`).
- **Verify:** Prefetch does not execute for `javascript:` or `data:` URLs.

### 7.2 — Standardize CSS loading between admin and public templates
- **Priority:** Medium
- **Files:** `app/templates/admin/base.html`, `app/templates/base.html`
- **Current:** Admin templates load CSS immediately without deferral pattern; public templates use deferred loading
- **Action:** Choose one pattern and apply consistently: either both admin and public templates use deferred CSS loading, or both use immediate loading. Document the chosen pattern.
- **Verify:** CSS loads correctly in both admin and public contexts; no flash of unstyled content.

### 7.3 — Consider cache invalidation on database error recovery
- **Priority:** Low
- **Files:** `app/context_processors.py`
- **Current:** Cache error fallbacks persist until TTL expiry even after DB recovers
- **Action:** After recovering from a database error, clear the relevant cache so the next request fetches fresh data instead of serving stale error fallbacks.
- **Verify:** After a DB error recovers, cache reflects current DB state without waiting for TTL expiry.

### 7.4 — Add DROP TABLE IF EXISTS before recreation in init_fts()
- **Priority:** Medium
- **File:** `app/search.py:63-98`
- **Current:** `init_fts()` creates the FTS table without dropping a potentially corrupted existing table first
- **Action:** Add `DROP TABLE IF EXISTS posts_fts` before the `CREATE VIRTUAL TABLE` statement to ensure clean recreation if the table is corrupted.
- **Verify:** `init_fts()` successfully recreates the FTS table even when the existing table is corrupted.

### 7.5 — Consider streaming S3 download in generate_image_variants
- **Priority:** Low
- **File:** `app/tasks.py:78`
- **Current:** `storage.load()` loads the entire file into memory
- **Issue:** For large images, this could cause memory pressure on the worker
- **Action:** Consider using chunked/streaming download from S3 instead of loading the entire file into memory. If not feasible, document the memory requirement for large images.
- **Verify:** Large image variant generation does not cause excessive memory usage.

### 7.6 — Add runtime concurrency check/warning in _update_delivery_status()
- **Priority:** Medium
- **File:** `app/tasks.py:318-347`
- **Current:** Relies on external `--concurrency=1` enforcement with no runtime warning
- **Action:** Add a runtime check that detects if Celery concurrency is greater than 1 and logs a warning, since `_update_delivery_status()` uses in-memory state that would be incorrect with multiple workers.
- **Verify:** Warning is logged if concurrency > 1 is detected; no warning with concurrency = 1.

### 7.7 — Extract TEST_PASSWORD constant to avoid scattered hardcoded strings
- **Priority:** Medium
- **Files:** Multiple test files
- **Current:** Multiple test files hardcode `"test-password"` instead of using a centralized constant
- **Action:** Create a `TEST_PASSWORD` constant (e.g., in `tests/conftest.py` or `tests/shared_fixtures.py`) and update all test files to use it instead of hardcoded strings.
- **Verify:** All test files reference the centralized constant; `grep -r "test-password" tests/` shows only the constant definition.

### 7.8 — Update E2E tests to use consistent password reference
- **Priority:** Medium
- **File:** `tests/e2e/test_e2e.py`
- **Current:** Hardcodes `"test-password"` instead of using `os.environ["ADMIN_PASSWORD"]`
- **Action:** Change to use `os.environ["ADMIN_PASSWORD"]` to stay consistent with other test fixtures and the actual test environment.
- **Verify:** E2E tests pass with `ADMIN_PASSWORD=test-password`.

### 7.9 — Investigate REDIS_URL usage in e2e-tests job
- **Priority:** Medium
- **File:** `.github/workflows/ci.yml:162`
- **Current:** Sets `REDIS_URL: redis://localhost:6379/0` but services are accessed via Docker networking
- **Action:** Verify whether the REDIS_URL should be `redis://redis:6379/0` (Docker service name) instead of `localhost` when running in Docker Compose context.
- **Verify:** Redis connection works correctly in e2e-tests CI job.

### 7.10 — Use symbolic references instead of line numbers in architecture docs
- **Priority:** Low
- **Files:** Multiple architecture documentation files
- **Current:** Documentation uses hardcoded line numbers that drift as code changes
- **Action:** Replace line number references with symbolic/functional references (e.g., "in the `init_fts()` function" instead of "at line 75"). Apply across all docs: `architecture/services/*.md`, `architecture/routes/*.md`, `architecture/frontend/*.md`, `architecture/infrastructure/*.md`.
- **Verify:** Architecture docs use symbolic references; line number drift no longer requires doc updates on minor code changes.

### 7.11 — Update line references in frontend docs
- **Priority:** Low
- **Files:** `architecture/frontend/*.md`
- **Current:** Various line references are off by 1-2 lines from actual code
- **Action:** Verify and correct all line number references against current codebase.
- **Verify:** All line references in frontend docs are accurate.

### 7.12 — Add public/comments.html to templates directory structure
- **Priority:** Low
- **Files:** `architecture/frontend/templates.md`
- **Current:** `app/templates/public/comments.html` exists but is not shown in the templates directory structure documentation
- **Action:** Add `public/comments.html` to the templates directory structure documentation.
- **Verify:** Template directory structure shows `public/comments.html`.

### 7.13 — Document login template vite_asset() usage
- **Priority:** Low
- **Files:** `architecture/frontend/static-assets.md`, `architecture/frontend/templates.md`
- **Current:** `admin/login_base.html` uses `vite_asset()` for CSS/JS loading but this is not documented
- **Action:** Document that `admin/login_base.html` uses `vite_asset()` for CSS/JS assets, enabling CDN prefix support similar to other templates.
- **Verify:** Documentation mentions login template's use of `vite_asset()`.

### 7.14 — Document S3StorageBackend error handling limitation
- **Priority:** Low
- **Files:** `architecture/infrastructure/storage.md`
- **Current:** `S3StorageBackend.exists()` and `list_files()` return `False`/empty on any error
- **Issue:** Cannot distinguish 404 (file not found) from network failure or permission error
- **Action:** Document this limitation so operators understand that errors may mask as "not found" and suggest workarounds if differentiation is needed.
- **Verify:** Documentation notes the error handling limitation.

### 7.15 — Document FTS corruption recovery procedure for operators
- **Priority:** Medium
- **File:** `architecture/infrastructure/search.md`
- **Current:** If `init_fts()` fails, the corrupted table is left intact with no documented recovery path
- **Action:** Document that operators should run `rebuild_fts()` manually to recover from FTS corruption, and the expected steps for recovery.
- **Verify:** Documentation includes FTS corruption recovery procedure for operators.

---

## Wave Summary

| Wave | Focus | Items | Status | Can Parallelize | Subagent Count |
|------|-------|-------|--------|-----------------|----------------|
| 1 | Source Code Fixes | 11 | COMPLETED | Yes | Up to 11 |
| 2 | Documentation Corrections | 12 | COMPLETED | Yes | Up to 12 |
| 3 | Source Code Improvements | 12 | COMPLETED | Yes | Up to 12 |
| 4 | Documentation Additions | 34 | COMPLETED | Yes | Up to 34 |
| 5 | Additional Source Code Fixes | 10 | PENDING | Yes | Up to 10 |
| 6 | Additional Documentation Corrections | 41 | PENDING | Yes | Up to 41 |
| 7 | Additional Source Code Improvements | 15 | PENDING | Yes | Up to 15 |
| **Total** | | **135** | | | |

**Recommended subagent batch sizes:** 4-6 per wave to avoid overwhelming the system. Launch in parallel within each wave.

---

## Parallelization Opportunities

### Phase 1 (Waves 5-7 can run in parallel)
- Wave 5: Source Code Fixes (10 items) — independent source changes
- Wave 6: Documentation Corrections (41 items) — independent doc fixes  
- Wave 7: Source Code Improvements (15 items) — independent code improvements

### Phase 2 (After Phase 1 completes)
- Run verification: `ruff check . && ruff format --check . && mypy app/ && pytest tests/`

### Phase 3 (If additional review items discovered)
- Create Wave 8+ as needed based on new reviews or discovered issues