# Improvement Plan

**Date:** 2026-04-28
**Status:** IN PROGRESS - Consolidation from multiple plan files
**Source:** plan.md, plan2.md, plan3.md, plan4.md, plan5.md, plan6.md, plan7.md, plan8.md

---

## Verification Status

- 514 tests pass (excluding E2E)
- All completed items marked ✓ COMPLETED
- Deferred items marked ✗ SKIPPED or ✓ COMPLETED (if later implemented)

---

## Critical Bugs (Immediate Priority)

These items represent **broken functionality** that should be fixed first:

### CB-1: JS Module Initialization Bug [CRITICAL]
**Status:** ✗ NOT FIXED
**Priority:** CRITICAL
**Files:** `app/static/js/main.js:68`, `app/static/js/shared/*.js`
**Effort:** 2 hours

**Issue:** Module initialization calls the module object as a function instead of calling the correct named exports.

**Fix Required:**
1. Add `export default initXxx;` to 19 JS modules (all except toast.js)
2. Update `main.js:68` to call `module.default()` instead of treating module as callable

All JavaScript functionality is currently broken due to this bug.

---

### CB-2: Toast Stacking Logic
**Status:** ✗ NOT FIXED
**Priority:** HIGH
**Files:** `app/static/js/shared/toast.js:51-53`
**Effort:** 30 min

**Issue:** `translateY(-100%)` is relative to each element's own height. With 3+ toasts, they overlap because offset isn't cumulative.

**Fix:** Replace with cumulative pixel-based offsets using GAP=12px.

---

### CB-3: Modal transitionend Multiple Fires
**Status:** ✗ NOT FIXED
**Priority:** HIGH
**Files:** `app/static/js/shared/modal.js:24-33`
**Effort:** 15 min

**Issue:** Modal has both `opacity` and `transform` CSS transitions so `transitionend` fires twice per open/close cycle.

**Fix:** Check `event.propertyName` to filter.

---

### CB-4: HN Platform Mismatch
**Status:** ✗ NOT FIXED
**Priority:** HIGH
**Files:** `app/templates/_share_buttons.html`
**Effort:** 5 min

**Issue:** API expects "hackernews" but template sends "hn", causing Hacker News shares to not be tracked.

**Fix:** Change `data-platform="hn"` to `data-platform="hackernews"` in template.

---

### CB-5: JSON Feed Missing content_html
**Status:** ✗ NOT FIXED
**Priority:** HIGH
**Files:** `app/routes/rss.py:138`
**Effort:** 15 min

**Issue:** JSON Feed 1.1 spec requires `content_html` or `content_text` field. Currently only provides `summary`.

**Fix:** Add `content_html` field to JSON Feed response with the post body HTML.

---

### CB-6: IntegrityError Rollback in pages.py
**Status:** ✗ NOT FIXED
**Priority:** HIGH
**Files:** `app/routes/admin/pages.py` (lines 77-82, 143-148)
**Effort:** 1 hour

**Issue:** After `db.session.rollback()` in `new_page()` and `edit_page()`, changes are not re-applied. SQLAlchemy expires all attributes after rollback.

**Fix:** Follow `posts.py` pattern with slug regeneration and retry. Reapply ALL field changes after rollback.

---

### CB-7: Missing API Error Handling
**Status:** ✗ NOT FIXED
**Priority:** HIGH
**Files:** `app/routes/api.py` (lines 192-201, 257-261)
**Effort:** 30 min

**Issue:** `db.session.commit()` not wrapped in try/except for IntegrityError/OperationalError.

**Fix:** Add `from sqlalchemy.exc import IntegrityError, OperationalError`. Return 409 on duplicate slug, 500 on operational error.

---

### CB-8: CSS Sanitization Not Applied to custom_css
**Status:** ✗ NOT FIXED
**Priority:** HIGH
**Files:** `app/routes/admin/settings.py` (lines 52-53)
**Effort:** 15 min

**Issue:** `custom_css` is saved directly without calling `sanitize_css()`.

**Fix:** Apply `sanitize_css()` to `custom_css` before saving.

---

## Wave 1: Security Fixes

### 1.1 SMTP Context Manager Consistency
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/email.py` (lines 24-43)
**Effort:** 30 min

**Issue:** `_send_email()` uses `with smtplib.SMTP() as server:` context manager while other functions use try/finally pattern.

**Fix:** Replace with manual `try/finally` pattern for consistency. The context manager warning from AGENTS.md indicates potential issues with this pattern.

---

### 1.2 CSRF Token Rotation Bug
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/routes/admin/users.py` (lines 145, 182, 230), `app/csrf.py`
**Effort:** 1 hour

**Issue:** Code sets singular `session["csrf_token"]` but sliding window uses a list `csrf_tokens`.

**Fix:** Reset `session["csrf_tokens"]` list on privilege change (promote/demote/make_owner).

---

### 1.3 make_owner() Race Condition
**Status:** ✗ NOT FIXED
**Priority:** HIGH
**Files:** `app/routes/admin/users.py` (lines 218-230)
**Effort:** 2 hours

**Issue:** Demotes ALL admins first, then promotes target. If commit fails, no admins exist.

**Fix:** First promote target user (so at least ONE admin always exists), then demote others. Use `db.session.flush()` after promoting.

---

### 1.4 Session IP Binding Enforcement
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/config.py`, `app/routes/admin/__init__.py`
**Effort:** 1 hour

**Issue:** Currently only logs warning on IP change; should support enforce mode.

**Fix:** Add `SESSION_IP_BINDING` config with options: `off`, `log`, `enforce`. In enforce mode, invalidate session and redirect to login.

---

### 1.5 Account Lockout Mechanism
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/models.py` (add to User), `app/routes/admin/auth.py`, `app/config.py`
**Effort:** 2-3 hours

**Issue:** No protection against brute force login attempts.

**Fix:** Add `failed_login_count`, `locked_until` to User model. Add `is_locked()`, `record_failed_login()`, `reset_failed_login()` methods. Config: `MAX_FAILED_ATTEMPTS=5`, `LOCKOUT_DURATION_MINUTES=15`. Check lockout BEFORE password check.

---

### 1.6 Search Highlighting XSS Prevention
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/search.py`
**Effort:** 15 min

**Issue:** `highlight_query()` adds `<mark>` tags to raw text without sanitization.

**Fix:** Use `nh3.clean(text, tags=set(), attributes={})` before highlighting. Also sanitize query input.

---

### 1.7 File Upload Dimension Validation
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/routes/admin/helpers/images.py`
**Effort:** 1 hour

**Issue:** No validation of uploaded image dimensions.

**Fix:** Add `PIL.Image` dimension check (max 5000x5000 pixels).

---

### 1.8 Backup File Permission Hardening
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/routes/admin/backup.py`
**Effort:** 10 min

**Issue:** Backup files may have overly permissive file mode.

**Fix:** Set `os.chmod(backup_path, 0o600)` after backup creation.

---

## Wave 2: Frontend Fixes

### 2.1 Fix Share Button Class Mismatch
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/static/css/style.css:3482`
**Effort:** 15 min

**Issue:** Mobile CSS hides non-existent classes (`.share-btn-linkedin`, etc.) instead of correct classes (`.share-linkedin`, `.share-hn`, `.share-reddit`).

**Fix:** Update CSS selectors to match actual class names.

---

### 2.2 Lazy Load Polyfill
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/static/js/shared/lazy-load.js` + templates
**Effort:** 1 hour

**Issue:** For browsers without native `loading="lazy"`, code sets attribute which has no effect.

**Fix:** Implement IntersectionObserver fallback. Update templates to use `data-src` pattern.

---

### 2.3 Add focus-visible to Interactive Cards
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/static/css/style.css`
**Effort:** 30 min

**Issue:** Interactive cards lack `:focus-visible` styles for keyboard navigation.

**Fix:** Add `:focus-visible` styles to `.preset-card`, `.related-card`. Add `tabindex="0"` and focus styles to `.media-card` and `.stat-card`.

---

### 2.4 Guard Against Duplicate Dark Mode Toggle
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/static/js/shared/dark-mode.js:34-40`
**Effort:** 15 min

**Issue:** No check for existing `.theme-toggle` button - multiple `initDarkMode()` calls create duplicates.

**Fix:** Add check for existing toggle before insertion.

---

### 2.5 Add aria-selected to Search Suggestions
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/static/js/public/search.js`
**Effort:** 15 min

**Issue:** Keyboard navigation (ArrowUp/Down) toggles `active` class but never sets `aria-selected="true"`.

**Fix:** Update ArrowDown/ArrowUp handlers to set `aria-selected="true"`.

---

### 2.6 Add theme-color Meta Tag
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/templates/base.html`
**Effort:** 5 min

**Issue:** Mobile browser chrome color doesn't match site theme.

**Fix:** Add `<meta name="theme-color" content="{{ theme_vars.bg }}">`.

---

### 2.7 Add Sidebar Skip Link
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/templates/base.html`
**Effort:** 5 min

**Issue:** Only main content has skip link - sidebar has no skip target.

**Fix:** Add `<a href="#sidebar" class="skip-link">Skip to sidebar</a>`.

---

### 2.8 Preload Inter 700 Font Weight
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/templates/base.html`
**Effort:** 5 min

**Issue:** Only Inter 400 and JetBrains Mono 400 are preloaded. Inter 700 (headings) causes FOUT.

**Fix:** Add preload for Inter 700 font weight.

---

### 2.9 Fix Duplicate CSS Definitions
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/static/css/style.css`, `app/static/js/public/anchor-links.js`
**Effort:** 15 min

**Issue:** (1) `--space-sm-md: 12px` defined twice (lines 102 and 1613). (2) `.toast` defined twice (lines 1495 and 3831).

**Fix:** Remove duplicate `--space-sm-md`. Rename second `.toast` to `.toast-copied` and update anchor-links.js to use `.toast-copied`.

---

### 2.10 Critical CSS Inlining + Async Loading
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/templates/base.html`, `app/templates/admin/base.html`
**Effort:** 4-6 hours

**Issue:** Full stylesheet blocks rendering.

**Fix:** Inline critical CSS (~5-7KB: navbar, hero, first post card styles). Use `<link rel="stylesheet" media="print" onload="this.media='all'">` pattern. Add `fetchpriority="high"` to font preloads.

---

### 2.11 Conditional Prism.js Loading
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/static/js/main.js`, `app/templates/base.html`
**Effort:** 2-3 hours

**Issue:** Prism.js loaded on all pages even when no code blocks present.

**Fix:** Add `loadPrismIfNeeded()` checking `document.querySelector('pre[class*="language-"]')`. Remove Prism script tags from base.html (loaded dynamically). Keep in admin/base.html for editor.

---

### 2.12 Remove Prism.js from Login Page
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/templates/admin/login_base.html` (lines 52-53)
**Effort:** 15 min

**Issue:** Login page has no code blocks but loads Prism.js.

**Fix:** Remove Prism script tags from login_base.html.

---

## Wave 3: Backend Improvements

### 3.1 Extract Template Filters to Separate Module
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/__init__.py` (lines 184-220), new `app/filters.py`
**Effort:** 2 hours

**Issue:** Filters defined in `create_app()` not easily testable.

**Fix:** Create `register_filters(app)` function in new `app/filters.py`. Filters: `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`.

---

### 3.2 Create Reusable Transaction Helper
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** New `app/transaction.py`
**Effort:** 3 hours

**Issue:** 53 occurrences of `db.session.rollback()` with inconsistent patterns.

**Fix:** Create `@transactional` decorator and `commit_with_slug_retry()` helper for IntegrityError slug retry pattern.

---

### 3.3 Add Request-Level Caching to Expensive Filters
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/__init__.py` (template filter definitions)
**Effort:** 2 hours

**Issue:** Filters like `reading_time` and `markdown_safe` recompute on every call.

**Fix:** Use Flask `g` object caching with `has_request_context()` and `g._reading_time_cache`, `g._markdown_cache`. Cache key: `hash(text)`. Also fix `post_image_url` cache key to use `post.id` (database ID) not `id(post)` (Python object ID).

---

### 3.4 Extract SQL Constants in search.py
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/search.py`
**Effort:** 1 hour

**Issue:** Raw SQL strings defined inline.

**Fix:** Extract to module-level constants: `_SQL_CHECK_FTS_TABLE`, `_SQL_CREATE_FTS_TABLE`, `_SQL_REBUILD_FTS`, `_SQL_SYNC_FTS`, `_SQL_DELETE_FTS`, `_SQL_SEARCH_FTS`, `_SQL_GET_INDEXED_TERMS`.

---

### 3.5 Newsletter Return Value Semantics
**Status:** ✗ NOT FIXED
**Priority:** HIGH
**Files:** `app/email.py` (lines 142-213), `app/scheduler.py` (line 136)
**Effort:** 3 hours

**Issue:** `send_newsletter()` returns True even when `all_sent=False`.

**Fix:** Return `(all_succeeded: bool, failed_post_ids: list[int])`. Update scheduler to only increment `newsletter_attempts` for actually attempted posts.

---

### 3.6 Add Post Revision Limits
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/config.py`, `app/models.py`, `app/routes/admin/posts.py`, `app/cli.py`
**Effort:** 3 hours

**Issue:** Unlimited revisions can accumulate.

**Fix:** Add config `max_revisions_per_post = 10` (0 = unlimited). Update `_save_revision()` to delete oldest revisions beyond limit. Add `flask cleanup-revisions` CLI command.

---

### 3.7 Add Site Settings Double-Checked Locking
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/context_processors.py`
**Effort:** 2 hours

**Issue:** `_get_cached_settings()` slow path inside lock (not true double-checked locking).

**Fix:** Fast path outside lock, slow path with double-check inside lock (match `app/cache.py` pattern).

---

### 3.8 Add FTS5 Search Fallback Logic Fix
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/search.py`, `app/routes/public.py`
**Effort:** 2 hours

**Issue:** `search()` returns `[]` for both FTS unavailable and no results cases.

**Fix:** Return `([], False)` when FTS unavailable, `([], True)` when no results. Update caller to only trigger LIKE fallback when `fts_available == False`.

---

### 3.9 Add CSS Size Limit Validation
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/routes/admin/settings.py`
**Effort:** 1 hour

**Issue:** No limit on custom_css size.

**Fix:** Add `MAX_CSS_LENGTH = 50000` and check before save. Flash error if exceeded.

---

### 3.10 APScheduler Persistent Job Store
**Status:** ✗ NOT FIXED
**Priority:** HIGH
**Files:** `app/scheduler.py`, `app/models.py` (optional)
**Effort:** 4 hours

**Issue:** Jobs lost on restart; relies on fcntl file locking (Unix-only).

**Fix:** Replace `BackgroundScheduler` with `SQLAlchemyJobStore` using existing SQLite. Remove all `fcntl` imports and lock logic. Jobs persist across restarts.

---

### 3.11 Add Periodic Maintenance Jobs
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/scheduler.py`, `app/config.py` (optional)
**Effort:** 3 hours

**Issue:** No automated maintenance tasks.

**Fix:** Add 4 new jobs:
- `check_database_integrity` (daily 3AM)
- `checkpoint_wal` (daily 4AM)
- `check_fts_integrity` (weekly Sun 2AM)
- `optimize_database` (daily 1AM)

---

### 3.12 Standardize Caching with Flask-Caching
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `requirements.txt`, `app/extensions.py`, `app/__init__.py`, `app/cache.py`, `app/context_processors.py`
**Effort:** 4-6 hours

**Issue:** 4 custom caching implementations.

**Fix:** Replace with `flask-caching` using `SimpleCache` backend. Add `@cache.memoize()` and `@cache.cached()` decorators. Update `app/routes/rss.py`, `app/routes/admin/helpers/dashboard.py`, `app/routes/admin/helpers/analytics.py`.

---

### 3.13 Server-Side Sessions with Redis
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/__init__.py`, `app/config.py`, `config.toml`
**Effort:** 6-8 hours

**Issue:** Cookie-based sessions have size limits and security concerns.

**Fix:** Add `flask-session>=0.8.0,<1.0`, `redis>=5.0.0,<6.0` dependencies. Config: `SESSION_TYPE=redis`, `SESSION_REDIS_HOST`, `SESSION_REDIS_PORT`, `SESSION_REDIS_DB`, `SESSION_KEY_PREFIX`. Note: Users must log in again after migration.

---

### 3.14 Email Batching with RSET
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/email.py` send_newsletter()
**Effort:** 2-3 hours

**Issue:** No verification of SMTP connection during large newsletter batches.

**Fix:** Add `batch_size=50` parameter. Call `server.rset()` after each batch to verify connection.

---

### 3.15 Add Warning for Missing File Locking
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/scheduler.py`
**Effort:** 15 min

**Issue:** No warning when fcntl is unavailable (Windows).

**Fix:** Log warning at line 293 before SMTP check when `HAS_FCNTL` is False.

---

## Wave 4: Database & Performance

### 4.1 PostRevision.author_id Index
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/models.py` (line 165)
**Effort:** 1 hour

**Issue:** Missing index on PostRevision.author_id foreign key.

**Fix:** Add `db.Index("ix_post_revisions_author_id", "author_id")` to PostRevision.__table_args__.

---

### 4.2 Optimize get_indexed_terms() with FTS5 Vocabulary
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/search.py` (lines 210-228)
**Effort:** 2 hours

**Issue:** `get_indexed_terms()` queries posts table directly.

**Fix:** Use FTS5 vocabulary table: `fts5vocab('posts_fts', 'row')` for better performance.

---

### 4.3 Scheduler Persistence with Job Logging
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/models.py` (add ScheduledJobExecution), `app/scheduler.py`
**Effort:** 6-8 hours

**Issue:** No audit trail for scheduled job executions.

**Fix:** Create `ScheduledJobExecution` model: job_id, job_name, executed_at, status, items_processed, items_failed, error_message, execution_time_ms. Add indexes.

---

### 4.4 Connection Pool Tuning (PostgreSQL)
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/__init__.py`
**Effort:** 1 hour

**Issue:** No connection pool tuning for PostgreSQL.

**Fix:** Add `SQLALCHEMY_ENGINE_OPTIONS`: pool_size=5, max_overflow=10, pool_timeout=30, pool_recycle=3600, pool_pre_ping=True.

---

### 4.5 Responsive Images with srcset
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/routes/admin/helpers/images.py`, templates, CLI command
**Effort:** 8-12 hours

**Issue:** No responsive image variants.

**Fix:** Add `Pillow>=10.0.0,<11.0`. Generate variants: 400w, 800w, 1200w, 1920w. Add `responsive_image` Jinja filter. Add `flask generate-image-variants` CLI command.

---

### 4.6 Page View Buffer (Optional)
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** New `app/pageview_buffer.py`, `app/models.py`
**Effort:** 6-8 hours

**Issue:** High page view write volume.

**Fix:** Buffer writes and batch flush. Only implement if site has >1000 page views/day.

---

## Wave 5: Documentation

### 5.1 Rewrite README.md
**Status:** ✗ NOT FIXED
**Priority:** HIGH
**Files:** `/home/sugarwookie/projects/blog/README.md`
**Effort:** 3-4 hours

**Issue:** Current README is feature-listing style, not task-oriented.

**Fix:** Transform to task-oriented documentation. Expand to 450-550 lines. Add "Quick Start", "Configuration Reference", "Troubleshooting" (15 common issues), "FAQ" (10 questions).

---

### 5.2 Create USAGE.md
**Status:** ✗ NOT FIXED
**Priority:** HIGH
**Files:** `/home/sugarwookie/projects/blog/USAGE.md` (new)
**Effort:** 4 hours

**Issue:** No comprehensive user guide.

**Fix:** Create 400-500 line user guide: Getting Started (50), Writing Posts (100), Customizing Appearance (75), Newsletter Management (75), Admin Tasks (100), API Usage (50).

---

### 5.3 Improve DEPLOY.md
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `/home/sugarwookie/projects/blog/DEPLOY.md`
**Effort:** 2 hours

**Issue:** Missing troubleshooting and performance tuning sections.

**Fix:** Add table of contents with anchor links, "Quick Deploy", "Troubleshooting", "Performance Tuning". Cross-reference README.md. Add nginx rate limiting examples.

---

### 5.4 Enhance docs/openapi.yaml
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `/home/sugarwookie/projects/blog/docs/openapi.yaml`
**Effort:** 2 hours

**Issue:** Missing request/response examples and error documentation.

**Fix:** Add examples to each endpoint. Document authentication error responses (401, 503). Fix JSON Feed reference (incorrectly says "RSS Feed"). Add examples for common operations.

---

### 5.5 Update AGENTS.md
**Status:** ✗ NOT FIXED
**Priority:** HIGH
**Files:** `/home/sugarwookie/projects/blog/AGENTS.md`
**Effort:** 2 hours

**Issue:** Missing documentation for newer features.

**Fix:** Add JSON Feed, Preview Links, Scheduled Publishing, Post Revisions workflow, Health Check endpoint, Share Tracking. Fix any outdated information.

---

### 5.6 Create Asset Update Script
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** New `scripts/update-assets.sh`
**Effort:** 2 hours

**Issue:** No automated way to update self-hosted assets.

**Fix:** Create script to curl updates for marked.js, Prism.js, Prism languages from jsdelivr CDN.

---

### 5.7 Add Scheduler Configuration Options
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `config.toml`, `run.py`
**Effort:** 2 hours

**Issue:** No way to disable scheduler on multi-instance deployments.

**Fix:** Add `SCHEDULER_ENABLED` config. Check in `_get_scheduler()` and return None if disabled.

---

## Wave 6: Code Quality

### 6.1 Add Linting and Formatting
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** New `pyproject.toml`, `.pre-commit-config.yaml`, `.github/workflows/test.yml`, `requirements-dev.txt`
**Effort:** 4 hours

**Issue:** No automated linting/formatting.

**Fix:** Configure ruff (E, F, W, I, UP, B, SIM, TCH rules; line-length 100), black, mypy, pre-commit hooks. Add lint step to CI workflow.

---

### 6.2 Add Coverage Reporting to CI
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `.github/workflows/test.yml`
**Effort:** 1 hour

**Issue:** No coverage tracking.

**Fix:** Add `--cov=app`, `--cov-report=term-missing`, `--cov-report=xml`. Add `--cov-fail-under=80`. Optional: upload to Codecov.

---

### 6.3 Formalize Dev Dependencies
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `requirements-dev.txt`, `requirements.txt`, `ruff.toml` (new), `mypy.ini` (new)
**Effort:** 2 hours

**Issue:** Dev dependencies mixed with production.

**Fix:** Add ruff, mypy, pytest-mock to dev dependencies. Move playwright to dev-only. Create ruff.toml and mypy.ini config files.

---

### 6.4 Backup Encryption
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `app/routes/admin/backup.py`, `app/templates/admin/backup.html`
**Effort:** 2-3 hours

**Issue:** Backups not encrypted.

**Fix:** Add `python-gnupg==0.5.5` dependency. Add encrypt checkbox. Support asymmetric (GPG recipient) and symmetric (passphrase) encryption.

---

### 6.5 Optional S3-Compatible Media Storage
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/storage.py` (new), `app/template_helpers.py` (new), multiple templates
**Effort:** 8-12 hours

**Issue:** Media only stored locally.

**Fix:** Create storage abstraction layer with LocalStorage and S3Storage classes. Create `media_url()` template helper. Update 8+ templates to use `media_url()`.

---

### 6.6 Remove ASGI Adapter Overhead
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `run.py`, `requirements.txt`, `Dockerfile`, `README.md`, `DEPLOY.md`, `AGENTS.md`
**Effort:** 2 hours

**Issue:** `asgiref.WsgiToAsgi` wrapper adds latency overhead.

**Fix:** Remove `asgiref.WsgiToAsgi` wrapper, use WSGI interface directly with Granian. Expected: +8% RPS, -54% latency improvement.

---

### 6.7 Config File Permission Checks
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/config.py`
**Effort:** 15 min

**Issue:** No warning if config file is world-readable.

**Fix:** Add `check_config_permissions()` using `stat.S_IRGRP | stat.S_IROTH`. Recommend `chmod 600`.

---

### 6.8 Login Delay Increase
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/routes/admin/auth.py`
**Effort:** 5 min

**Issue:** Login delay too short.

**Fix:** Increase `time.sleep(0.05)` to `time.sleep(0.25)` in auth.py:60.

---

### 6.9 Token Enumeration Delay Optimization
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/routes/admin/auth.py` (forgot_password route)
**Effort:** 30 min

**Issue:** Delay not uniform on valid/invalid paths.

**Fix:** Change default `TOKEN_ENUMERATION_DELAY` from 0.1 to 0.5 seconds. Apply delay after both success and failure paths.

---

### 6.10 CSP report-uri Implementation
**Status:** ✗ NOT FIXED
**Priority:** LOW
**Files:** `app/__init__.py`
**Effort:** 30 min

**Issue:** No CSP violation reporting.

**Fix:** Add `/csp-violation` endpoint and `report-uri` to CSP header. Log violations to `logger.warning()`.

---

### 6.11 Clean Test Uploads
**Status:** ✗ NOT FIXED
**Priority:** HIGH
**Files:** `app/static/uploads/`, `tests/conftest.py`
**Effort:** 1 hour

**Issue:** 1,580 test files (6.3 MB) in uploads directory.

**Fix:** Remove test files. Add `cleanup_uploads_at_session_end` fixture to conftest.py.

---

### 6.12 Fix PostgreSQL Migration Script
**Status:** ✗ NOT FIXED
**Priority:** MEDIUM
**Files:** `DEPLOY.md` (lines 262-350)
**Effort:** 4 hours

**Issue:** Import SQL doesn't match actual schema.

**Fix:** Remove non-existent `created_at` from users. Update `site_settings` columns. Change `content` to `body` in pages table. Fix page_views to use `referrer`.

---

## Wave 7: Deferred Items (Confirmed Skip)

These items were considered but **intentionally deferred or skipped**:

### Security
| Item | Priority | Reason |
|------|----------|--------|
| Application-Level Rate Limiting | HIGH | BY DESIGN - Intentionally not included at app level. Configure at reverse proxy/WAF level. See nginx example in AGENTS.md. |
| CSP `unsafe-inline` Removal | HIGH | 8+ hours of significant refactoring for marginal security benefit |

### Code Quality
| Item | Priority | Reason |
|------|----------|--------|
| Static Type Analysis Integration | MEDIUM | Not a priority; Python 3.14 compatibility documented |
| Flask-Caching for Scalability | MEDIUM | Existing caching is sufficient |
| Strategic Logic Extraction | LOW | Not a priority |
| Asset Minification/Bundling | LOW | Not a priority |
| Extract CSP Headers to Helper | LOW | Adds indirection without benefit |
| Lazy-Loading Config | LOW | Not a priority |

### Documentation
| Item | Priority | Reason |
|------|----------|--------|
| README.md Restructuring | HIGH | Current README is adequate |

### Permanently Skipped
| Item | Reason |
|------|--------|
| PostgreSQL Migration | SQLite (WAL mode) is sufficient for current write-load profile |
| WebSub/PubSubHubbub | Low adoption |
| Ping Services | Obsolete protocol |
| Tinycss2 for CSS sanitization | Current regex is sufficient |

---

## Implementation Waves

For parallelization, items can be grouped as follows:

### Wave A (Parallel: Critical Bugs)
Can be done concurrently:
- CB-1: JS Module Init Bug
- CB-2: Toast Stacking
- CB-3: Modal transitionend
- CB-4: HN Platform Mismatch
- CB-5: JSON Feed missing content_html
- CB-6: IntegrityError Rollback pages.py
- CB-7: Missing API Error Handling
- CB-8: CSS Sanitization missing

### Wave B (Parallel: Security)
- 1.1 SMTP Context Manager
- 1.2 CSRF Token Rotation
- 1.3 make_owner Race Condition
- 1.4 Session IP Binding
- 1.5 Account Lockout
- 1.6 Search Highlighting XSS
- 1.7 File Upload Validation
- 1.8 Backup Permission Hardening

### Wave C (Parallel: Frontend)
- 2.1 Share Button Classes
- 2.2 Lazy Load Polyfill
- 2.3 focus-visible Cards
- 2.4 Dark Mode Guard
- 2.5 aria-selected Search
- 2.6 theme-color Meta
- 2.7 Sidebar Skip Link
- 2.8 Inter 700 Preload
- 2.9 Duplicate CSS
- 2.10 Critical CSS Inlining (larger effort)
- 2.11 Conditional Prism.js
- 2.12 Remove Prism from Login

### Wave D (Parallel: Backend)
- 3.1 Extract Template Filters
- 3.2 Transaction Helper
- 3.3 Request-Level Caching
- 3.4 SQL Constants
- 3.5 Newsletter Return Value
- 3.6 Post Revision Limits
- 3.7 Settings Double-Checked Locking
- 3.8 FTS5 Fallback Logic
- 3.9 CSS Size Limit
- 3.10 APScheduler Persistence
- 3.11 Maintenance Jobs
- 3.12 Flask-Caching
- 3.13 Redis Sessions
- 3.14 Email Batching
- 3.15 fcntl Warning

### Wave E (Parallel: Database/Performance)
- 4.1 PostRevision.author_id Index
- 4.2 get_indexed_terms FTS5 Vocab
- 4.3 Job Execution Logging
- 4.4 Connection Pool Tuning
- 4.5 Responsive Images
- 4.6 Page View Buffer (optional)

### Wave F (Documentation)
- 5.1 README Rewrite
- 5.2 USAGE.md Creation
- 5.3 DEPLOY.md Improvements
- 5.4 openapi.yaml Enhancement
- 5.5 AGENTS.md Updates
- 5.6 Asset Update Script
- 5.7 Scheduler Config

### Wave G (Code Quality)
- 6.1 Linting/Formatting
- 6.2 Coverage Reporting
- 6.3 Dev Dependencies
- 6.4 Backup Encryption
- 6.5 S3 Storage
- 6.6 Remove ASGI Adapter
- 6.7 Config Permission Checks
- 6.8 Login Delay Increase
- 6.9 Token Enum Delay
- 6.10 CSP report-uri
- 6.11 Clean Test Uploads
- 6.12 PostgreSQL Migration Script

---

## Previously Completed Items

The following items were completed and verified:

| Item | Status | Verification |
|------|--------|--------------|
| 1.1 API Key Timing Attack Fix | ✓ COMPLETED | `hmac.compare_digest()` in `app/routes/api.py` |
| 1.2 Granian Not Used in Docker | ✓ COMPLETED | Dockerfile uses `granian --interface asgi` |
| 1.3 Docker-Compose Circular Dependency | ✓ COMPLETED | `blog` service removed `depends_on: nginx` |
| 1.4 Health Endpoint Documentation | ✓ COMPLETED | DEPLOY.md matches docker-compose.yml |
| 1.5 Fix yield_per() Defeated by .all() | ✓ COMPLETED | `.scalars()` iterator in `app/scheduler.py` |
| 1.6 Docker-Compose Backup Service Entrypoint | ✓ COMPLETED | `entrypoint: ["python3", "backup.py"]` in compose |
| 1.7 Nginx Security Configuration Guide | ✓ COMPLETED | Rate limiting snippets in DEPLOY.md |
| 2.1 Fix Empty footer_tag_counts | ✓ COMPLETED | Caching in `app/context_processors.py` |
| 2.2 Fix N+1 Query in Revisions Route | ✓ COMPLETED | `joinedload(PostRevision.author)` in posts.py:694 |
| 2.3 Fix SMTP Connection Handling | ✓ COMPLETED | `_connect_smtp()` and retry logic in `app/email.py` |
| 2.4 Password Reset Token Hashing | ✓ COMPLETED | SHA-256 hashing in `app/routes/admin/auth.py` |
| 2.5 Backup Integrity Verification | ✓ COMPLETED | `app/backup_integrity.py` module exists |
| 2.6 Off-site Backup Sync | ✓ COMPLETED | `scripts/sync_backups.sh` exists |
| 3.1 JSON Feed Implementation | ✓ COMPLETED | `/json` endpoint in `app/routes/rss.py` |
| 3.2 RSS Feed Enhancements | ✓ COMPLETED | Enhanced RSS in `app/routes/rss.py` |
| 3.3 Conditional GET Support | ✓ COMPLETED | ETag support in RSS routes |
| 3.4 Cache Headers for Feeds | ✓ COMPLETED | Cache-Control headers in RSS routes |
| 4.1 Search Experience Enhancements | ✓ COMPLETED | `app/static/js/public/search.js` exists |
| 4.3 Editor Preview Latency Reduction | ✓ COMPLETED | Client-side marked.js + server-side fallback in `editor.js` |
| 5.1 Pages Link in Admin Navigation | ✓ COMPLETED | Pages link in admin base template |
| 5.2 Restore Button Distinct Styling | ✓ COMPLETED | Amber/warning color for restore |
| 5.3 Active State Highlighting for Nested Nav | ✓ COMPLETED | Active state in admin nav |
| 5.4 Confirm Modal Replacement | ✓ COMPLETED | Modal JS in `app/static/js/shared/` |
| 6.1 Missing Admin Tests | ✓ COMPLETED | 13 new tests in `tests/test_admin.py` |
| 6.2 Session Fixation Prevention Test | ✓ COMPLETED | Test in `tests/test_security.py` |
| 6.3 Fix Flaky Media Upload Test | ✓ COMPLETED | Test fixed in `tests/test_integration.py` |
| 6.4 pytest-cov Configuration | ✓ COMPLETED | `pytest.ini` configured |
| 6.5 CI/CD Workflow Definition | ✓ COMPLETED | `.github/workflows/test.yml` created |
| 7.1 Combine Redundant COUNT Queries | ✓ COMPLETED | Single SQL query with subqueries |
| 7.2 Fix Regex Recompilation in Loop | ✓ COMPLETED | Compiled regex at module level in `app/search.py` |
| 7.3 Add post_tags.tag_id Index | ✓ COMPLETED | `ix_post_tags_tag_id` index added |
| 7.4 Fix FTS5 Initialization | ✓ COMPLETED | `reset_fts_available()` fixed; `sync_fts()` uses atomic `INSERT OR REPLACE` |
| 7.5 Add FTS5 Prefix Index | ✓ COMPLETED | `prefix='2 3 4'` in FTS5 table; `search()` appends `*` for prefix matching |
| 7.6 Alembic SQLite Batch Mode | ✓ COMPLETED | `render_as_batch=True` in migrations/env.py |
| 7.7 Simplify get_indexed_terms() | ✓ COMPLETED | Simplified in `app/search.py` |
| 8.3 Create Centralized Error Handlers | ✓ COMPLETED | `app/routes/errors.py` already exists |
| 9.2 AGENTS.md Updates | ✓ COMPLETED | AGENTS.md updated |

---

## End of Plan
