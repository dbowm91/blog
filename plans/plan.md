# Implementation Plan - Blog CMS (Consolidated)

**Project:** Blog CMS
**Status:** WAVE N - IN PROGRESS
**Last Updated:** May 2026

---

## Overview

This file contains the consolidated implementation plan for the Blog CMS project, derived from architecture review findings across 8 modules. It serves as the single source of truth for implementation tasks.

All previously identified items (Waves A through M) have been completed. This document tracks items identified in the Wave N review.

---

## Wave N: Current Implementation Items

### N-1: HIGH PRIORITY (Code Fixes)

#### N-1.1: Email Tasks Don't Retry Properly
- **File:** `app/tasks.py:264-303`
- **Issue:** `send_confirmation_task` and `send_password_reset_task` catch exceptions and return `False` without calling `self.retry()`. These tasks do NOT have `max_retries` set and will not retry on failure. Despite `retry_backoff=True`, exceptions are swallowed.
- **Impact:** Email tasks may fail permanently on first error with no retry.
- **Fix:** Add `max_retries=3` to both task decorators and implement `self.retry()` after catching exceptions:
  ```python
  @shared_task(bind=True, max_retries=3, retry_backoff=True, queue='email')
  def send_confirmation_task(self: Any, subscriber_id: int) -> bool:
      try:
          subscriber = db.session.get(Subscriber, subscriber_id)
          if not subscriber:
              return False
          send_confirmation(subscriber)
          return True
      except Exception as e:
          logger.error(f"Confirmation email failed: {e}")
          self.retry(exc=e)  # Trigger retry instead of returning False
      finally:
          db.session.remove()
  ```
- **Status:** PENDING
- **Verification:** Run tests with SMTP disabled to confirm retry behavior

#### N-1.2: mobile-menu.jsx Import Bug
- **File:** `app/static/js/main.js:18,72`
- **Issue:** main.js imports `./shared/mobile-menu.jsx` but the file is actually named `mobile-menu.jsx` (JSX extension). While Vite's glob pattern happens to match this, the import path is inconsistent with other `.js` imports in the file and could break if Vite's behavior changes.
- **Impact:** Low - currently works by coincidence
- **Fix:** Either:
  1. Rename `mobile-menu.jsx` to `mobile-menu.js` if no JSX features are used, OR
  2. Update imports on lines 18 and 72 to use consistent `.jsx` extension throughout (currently line 18 uses `.jsx` but line 72 uses `.jsx` as well - this is actually consistent. The actual issue is the file extension mismatch)
- **Note:** The file `app/static/js/shared/mobile-menu.jsx` contains JSX-like code (className, etc.) but may work without actual JSX processing. Verify if `.jsx` processing is needed.
- **Status:** PENDING

---

### N-2: MEDIUM PRIORITY - DOCUMENTATION

#### N-2.1: Document ADMIN_RATE_LIMITS
- **File:** `docs/core/configuration.md`
- **Issue:** `ADMIN_RATE_LIMITS` (config.py:145-152) is not documented. `PAGE_VIEW_BUFFER_SIZE` is already documented.
- **Fix:** Add documentation for `ADMIN_RATE_LIMITS` configuration:
  ```python
  ADMIN_RATE_LIMITS = {
      "login": (5, 60),       # 5 attempts per 60 seconds
      "api_write": (100, 60), # 100 writes per 60 seconds
      "api_read": (500, 60),  # 500 reads per 60 seconds
      "settings": (50, 60),   # 50 settings changes per 60 seconds
      "post_create": (100, 60),
      "post_update": (100, 60),
  }
  ```
- **Status:** PENDING

#### N-2.2: S3 Storage Documentation Misleading
- **File:** `docs/infrastructure/storage.md`
- **Issue:** Documentation claims settings are read from `config.toml` but actual code reads from environment variables in `app/storage.py:41`.
- **Fix:** Update storage.md to clarify S3 uses environment variables: `S3_BUCKET`, `S3_REGION`, `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_PUBLIC_URL`
- **Status:** PENDING

#### N-2.3: Webhook.secret Documentation Wrong
- **File:** `docs/core/models.md`
- **Issue:** Line 187 incorrectly states `# Plain text storage`. `Webhook.secret` is actually AES-256-GCM encrypted via `app/webhook_encryption.py` (see `app/models.py:490,499-517`).
- **Fix:** Update models.md to reflect encrypted storage and reference `app/webhook_encryption.py`
- **Status:** PENDING

#### N-2.4: WebhookEvent.delivery_status Not Documented
- **File:** `docs/core/models.md`
- **Issue:** `WebhookEvent.delivery_status` field exists in `app/models.py:533` but not documented.
- **Fix:** Add documentation for `delivery_status` field values: `'delivered'`, `'partial_failure'`, `'failed'`
- **Status:** PENDING

#### N-2.5: Search.md Config Location Wrong
- **File:** `docs/services/search.md`
- **Issue:** If documentation mentions `_FTS_CHECK_TTL` and `_SQLITE_MAX_VARS` locations, they are hardcoded in `app/search.py:30,298` not in `app/config.py`.
- **Fix:** Update search.md to reflect actual locations (hardcoded constants, not config values)
- **Status:** PENDING

#### N-2.6: Search.md Indexing Description Wrong
- **File:** `docs/services/search.md`
- **Issue:** Documentation claims "indexing via signals" but posts are indexed via direct function calls (e.g., `sync_fts()` in routes), not automatic signals.
- **Fix:** Clarify that indexing is triggered manually in routes after post save/update
- **Status:** PENDING

#### N-2.7: admin-routes.md posts/list.py Doesn't Exist
- **File:** `docs/routes/admin-routes.md` (or `architecture/routes/admin-routes.md`)
- **Issue:** Module structure includes `posts/list.py` which does not exist. Post listing is in `admin/posts/__init__.py` as `dashboard()` function.
- **Fix:** Remove reference to `posts/list.py` and clarify actual location is `posts/__init__.py:dashboard()`
- **Status:** PENDING

#### N-2.8: Page Route Paths Incorrect in admin-routes.md
- **File:** `docs/routes/admin-routes.md` (or `architecture/routes/admin-routes.md`)
- **Issue:** Page routes use wrong paths (e.g., `/admin/pages/create` vs actual `/admin/pages/new`).
- **Fix:** Update page route paths to match actual implementation:
  - `GET/POST /admin/pages/new` (not create)
  - `GET/POST /admin/pages/edit/<int:page_id>` (not rename)
  - `POST /admin/pages/delete/<int:page_id>` (not delete)
- **Status:** PENDING

#### N-2.9: Docker Compose v2 Syntax in CI
- **File:** `.github/workflows/test.yml:119-120`
- **Issue:** Uses `docker-compose` (v1 syntax with hyphen) but GitHub Actions includes Docker Compose v2 which uses `docker compose` (space).
- **Fix:** Update to `docker compose` (space) syntax:
  ```yaml
  - run: docker compose up -d --profile production
  - run: docker compose wait redis
  ```
- **Status:** PENDING

#### N-2.10: Permissions-Policy Header Missing from nginx
- **File:** `nginx/conf.d/blog.conf`
- **Issue:** Documentation claims header is set but actual nginx config does not contain `Permissions-Policy`.
- **Fix:** Add to nginx/conf.d/blog.conf:
  ```
  add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
  ```
- **Status:** PENDING

#### N-2.11: Python Version Sync Issue
- **File:** `.github/workflows/test.yml:8-36`
- **Issue:** `lint-and-type` job only tests Python 3.12, but `test` job tests both 3.12 and 3.13. This is a minor documentation discrepancy in the workflow.
- **Fix:** Either:
  1. Update test.yml to include 3.13 in lint-and-type matrix, OR
  2. Note that lint is tested against 3.12 only (intentional for CI efficiency)
- **Status:** PENDING

---

### N-3: LOW PRIORITY - IMPROVEMENTS

#### N-3.1: Email.md "Wrapper Pattern" Description Inaccurate
- **File:** `docs/infrastructure/email.md`
- **Issue:** The documentation describes a "wrapper pattern" but actual implementation directly calls email functions from tasks without a wrapper layer. The documentation at lines 22-23 correctly notes "Swallows exception - task will NOT retry" but the overall framing is misleading.
- **Fix:** Update email.md to accurately describe direct function calling pattern and clarify retry behavior is intentionally disabled to prevent retry storms
- **Status:** PENDING

#### N-3.2: Serialization.md Missing Fields
- **File:** `docs/services/serialization.md` (or architecture/services/serialization.md)
- **Issue:** Documentation omits additional fields returned by functions (`published`, `scheduled_publish_at` for posts; `id`, `expires_at`, `unsubscribed_at` for subscribers).
- **Fix:** Document all fields returned by each serialization function
- **Status:** PENDING

#### N-3.3: slug.md Parameter Table Too Restrictive
- **File:** `docs/services/slug.md`
- **Issue:** Says supported models are "Post, Page, Tag, Series" but actual code accepts any model with `slug` attribute.
- **Fix:** Update parameter table to clarify model flexibility
- **Status:** PENDING

#### N-3.4: Benchmark admin_user Fixture Missing email Parameter
- **File:** `tests/benchmarks/conftest.py:71`
- **Issue:** Benchmark's `admin_user` fixture creates users without email while main conftest creates with `email="admin@example.com"`.
- **Fix:** Add `email="admin@example.com"` to benchmark's admin_user fixture:
  ```python
  admin_user = User(
      username="admin",
      email="admin@example.com",  # Add this line
      is_admin=True
  )
  ```
- **Status:** PENDING

#### N-3.5: Remove Redundant ensure_buffer_disabled Import
- **File:** `tests/conftest.py:4,187`
- **Issue:** `conftest.py` has `from tests.shared_fixtures import *` but also defines its own `ensure_buffer_disabled`. The import is redundant since local definition shadows imported one.
- **Fix:** Remove redundant import and keep only local definition, or consolidate to import from shared_fixtures
- **Status:** PENDING

#### N-3.6: Benchmark clean_db FTS Cleanup Missing
- **File:** `tests/benchmarks/conftest.py:52-60`
- **Issue:** `clean_db` fixture deletes all data but doesn't clean up FTS index entries. Orphaned FTS entries may affect benchmark accuracy.
- **Fix:** Consider adding FTS cleanup (call to `reset_fts()` or similar) to `clean_db` fixture
- **Status:** PENDING

#### N-3.7: Celery Tasks Documentation Stale Line Numbers
- **Files:** `docs/tasks/celery-tasks.md`, `architecture/tasks/scheduler.md`
- **Issue:** Line numbers in documentation are stale (code has shifted ~5-7 lines).
- **Fix:** Remove specific line numbers or note they may be outdated
- **Status:** PENDING

#### N-3.8: deliver_webhook Deprecation Not Documented in docs/
- **File:** `docs/infrastructure/webhooks.md`
- **Issue:** Should note that `deliver_webhook()` raises `DeprecationWarning` when called. Note: `architecture/infrastructure/webhooks.md` correctly documents this.
- **Fix:** Add deprecation notice to docs/infrastructure/webhooks.md
- **Status:** PENDING

#### N-3.9: Backup Naming Documentation Incomplete
- **Files:** `docs/tasks/celery-tasks.md`, `architecture/tasks/scheduler.md`
- **Issue:** Scheduler backup naming may differ from Celery backup naming in documentation.
- **Fix:** Verify actual naming from `app/services/backup.py:167` - pattern is `blog_YYYYMMDD_HHMMSS.db` (with optional .gz for compressed, .gpg for encrypted). Update documentation to reflect this.
- **Status:** PENDING

#### N-3.10: AGENTS.override.md vite-plugin-flask Reference Wrong
- **File:** `app/static/AGENTS.override.md`
- **Issue:** Mentions `vite-plugin-flask` for Flask integration but this plugin is not present in package.json or vite.config.js.
- **Fix:** Remove reference to vite-plugin-flask (Vite works without it via manifest parsing)
- **Status:** PENDING

---

## Parallelization Analysis (Waves)

Items are grouped by dependency and parallelization potential:

### Wave N-A: Documentation Fixes (Can run in parallel)
All N-2 items (N-2.1 through N-2.11) and N-3 items (N-3.1 through N-3.10) can be executed in parallel as they don't depend on each other.

**Agents can work on these simultaneously:**
- Agent 1: N-2.1 through N-2.4 (config/docs fixes)
- Agent 2: N-2.5 through N-2.8 (route documentation fixes)
- Agent 3: N-2.9 through N-2.11 (CI/deployment fixes)
- Agent 4: N-3.1 through N-3.5 (low priority improvements)
- Agent 5: N-3.6 through N-3.10 (low priority improvements)

### Wave N-B: Code Fixes (Must run sequentially)
- N-1.1 (Email retry logic) - requires code change + testing
- N-1.2 (mobile-menu.jsx import) - if file rename is needed, must be done together

### Recommended Order
1. First complete Wave N-A (documentation, can be parallelized)
2. Then complete Wave N-B (code fixes with testing)

---

## Implementation Detail: Email Task Retry Fix (N-1.1)

### Current Code Behavior
```python
@shared_task(bind=True, queue='email')
def send_confirmation_task(self: Any, subscriber_id: int) -> bool:
    try:
        subscriber = db.session.get(Subscriber, subscriber_id)
        if not subscriber:
            return False
        send_confirmation(subscriber)
        return True
    except Exception as e:
        logger.error(f"Confirmation email failed: {e}")
        return False  # No retry!
    finally:
        db.session.remove()
```

### Required Changes
1. Add `max_retries=3` to decorator
2. Change exception handling to call `self.retry(exc=e)` instead of returning False
3. Update the `except` block to trigger retry

### Implementation:
```python
@shared_task(bind=True, max_retries=3, retry_backoff=True, queue='email')
def send_confirmation_task(self: Any, subscriber_id: int) -> bool:
    try:
        subscriber = db.session.get(Subscriber, subscriber_id)
        if not subscriber:
            return False
        send_confirmation(subscriber)
        return True
    except Exception as e:
        logger.error(f"Confirmation email failed: {e}")
        raise self.retry(exc=e)  # Trigger retry with exponential backoff
    finally:
        db.session.remove()
```

### Testing
1. Disable SMTP or use invalid SMTP settings
2. Trigger confirmation email via subscriber signup
3. Verify Celery logs show retry attempts (max 3)
4. After 3 failures, task should stop retrying

---

## Implementation Detail: mobile-menu.jsx Fix (N-1.2)

### Step 1: Check if JSX is Actually Used
Read `app/static/js/shared/mobile-menu.jsx` and check if it uses any JSX-specific syntax (React components, `<>`, etc.)

### Step 2A: If No JSX Syntax
Rename file: `mobile-menu.jsx` → `mobile-menu.js`
No import changes needed since Vite's glob matches both.

### Step 2B: If JSX Syntax Used
Keep `.jsx` extension but ensure import consistency across main.js

### Step 3: Verify
Run `npm run dev` and check no errors on pages using mobile menu

---

## Important Context for Future Agents

### Email Task Retry Issue (N-1.1)
`send_confirmation_task` and `send_password_reset_task` in `app/tasks.py` catch exceptions and return `False` without calling `self.retry()`. With `retry_backoff=True`, tasks will NOT automatically retry because exceptions are swallowed.

### Configuration Options Not in Docs
- `PAGE_VIEW_BUFFER_SIZE` - Controls page view buffer size (default 0)
- `ADMIN_RATE_LIMITS` - Rate limits for admin operations: login (5/60s), api_write (100/60s), api_read (500/60s), settings (50/60s), post_create (100/60s), post_update (100/60s)

### Context Processors
Actual context processor function names (not the injected variable names):
- `inject_csrf()` - Injects `csrf_token` and `csp_nonce`
- `inject_config()` - Injects `site_title`, `site_description`, `author_name`, `author_role`, `author_avatar`, `base_url`, `current_year`, `canonical_url`
- `inject_theme()` - Injects theme settings and `custom_css`
- `inject_footer_data()` - Injects footer links and data
- `inject_show_footer_posts()` - Injects `show_footer_posts` boolean

### Template Filters
Actual filters (defined in `app/filters.py`):
- `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub`
- NOT `format_date`, `markdown`, `slugify` (these don't exist)

### Backup Naming
Both `create_backup()` (Celery) and `run_daily_backup()` (scheduler) use `blog_*.db` pattern:
- `blog_YYYYMMDD_HHMMSS.db` - plain backup
- `blog_YYYYMMDD_HHMMSS.db.gz` - compressed
- `blog_YYYYMMDD_HHMMSS.db.gpg` - encrypted

### S3 Storage Configuration
S3 settings are read from environment variables, NOT from config.toml:
- `S3_BUCKET`, `S3_REGION`, `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_PUBLIC_URL`

---

## Previously Completed Items (Reference)

### Wave M - All Items Completed (May 2026)
All critical bugs and documentation issues from Wave M review have been verified as completed.

### Wave L - All Items Completed (Previously)
All items from earlier reviews verified correct.

---

*Last updated: May 2026 - Wave N in progress*