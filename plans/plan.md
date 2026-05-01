# Consolidated Improvement Plan

**Date:** 2026-05-01
**Status:** Active
**Consolidated From:** multiple source plans

This plan serves as the single source of truth for all identified improvements, bug fixes, and features for the DevLog Blog Platform.

---

## Wave 1: Critical Fixes (DO FIRST - Parallelizable)

### Wave 1A: Backend Bugs
- [x] **BUG-1: Fix Rate Limiter Config Key Mismatch** - `app/__init__.py:186` assigns to `RATELIMIT_STORAGE_URL` but Flask-Limiter expects `RATELIMIT_STORAGE_URI`. Ensure it uses `RATE_LIMIT_STORAGE_URI` from config.
- [x] **BUG-2: Fix Scheduler File Lock Race Condition** - Remove all `os.remove(lock_path)` calls from `app/scheduler.py` (8 locations: lines 77, 147, 160, 198, 211, 257, 277, 319). Linux file locks are advisory and shouldn't be deleted.
- [x] **BUG-3: Fix Backup Strategy (WAL Mode)** - `shutil.copy2()` in `app/scheduler.py:299` misses WAL file. Replace with `sqlite3.backup()` API for consistent snapshots.
- [ ] **P0-1: Fix Broken CI Pipeline** - Add `ruff>=0.8.0` and `mypy>=1.8.0` to `requirements-dev.txt`.
- [ ] **P0-2: Fix JavaScript Dynamic Imports** - Replace variable-based `import(m)` in `app/static/js/main.js` with `import.meta.glob()` for Vite-compatible bundling.
- [ ] **BUG-5: Fix Python 3.12 sqlite3 Datetime Deprecation** - Register custom adapters in `app/__init__.py` using `sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())` and corresponding converters.
- [ ] **ALIGN-1: Standardize Python Environment** - Harmonize Python version to 3.12 across `setup.sh`, `pyproject.toml`, and `Dockerfile` to ensure Celery/Granian stability.

### Wave 1B: Frontend Bugs
- [ ] **FE-BUG-1: Fix Invalid Nested Anchor Tags** - Implement "Stretched Link" pattern for post cards in `index.html`, `tag.html`, `search.html`, and `archive.html`. Use `.post-card-link::before` with `z-index: 1` and ensure `.post-tags` has `z-index: 2`.
- [ ] **FE-BUG-2: Fix Admin Templates to Use vite_asset()** - Replace `url_for('static', ...)` with `vite_asset(...)` in `app/templates/admin/base.html` for all CSS and JS files.
- [ ] **FE-BUG-3: Fix Hero Gradient Text Accessibility** - Add `@supports (background-clip: text)` wrapper and `CanvasText` fallback for High Contrast Mode in `style.css` and `base.html`. Remove duplicate inline gradient in `base.html:59`.

---

## Wave 2: Security Hardening (HIGH - Parallelizable with Wave 1)

- [ ] **SEC-1: Fix Information Leakage** - Strip `str(e)` from flash messages in `admin/newsletter.py:65`, `admin/series.py`, and `backup_integrity.py:78,80`. Use generic error messages and log the details instead.
- [x] **SEC-2: Upgrade Backup Encryption (PBKDF2)** - Upgrade `_derive_key()` in `app/backup_encryption.py` to use PBKDF2-HMAC-SHA256 with 600,000 iterations (NIST SP 800-132) and a 16-byte random salt.
- [x] **SEC-3: SSRF Protection for Webhooks** - Implement `is_safe_webhook_url(url)` in `app/utils.py` using `socket.getaddrinfo` and `ipaddress.is_global` to block private/loopback/metadata IPs. Apply to `deliver_webhook` in `app/webhooks.py` and `app/tasks.py:197`. Set `allow_redirects=False`.
- [x] **SEC-4: Webhook Logic Reconciliation** - Integrate HMAC-SHA256 signing from `app/webhooks.py` into the Celery task in `app/tasks.py`. Ensure all background deliveries are signed.
- [x] **SEC-5: API Input Validation Gaps** - Add `validate_integer()`, `validate_list()`, and regex-based `validate_tags()` (max 10 tags, 50 chars each, alpha-numeric) to `app/validators.py`. Add `require_json_content_type` decorator.
- [x] **SEC-6: Fix User __repr__ Leaks** - Change `User.__repr__` in `app/models.py:63` to return `id` instead of `username` to prevent log leakage.
- [x] **SEC-7: Implement Session Fixation Protection** - Add `session.regenerate_id()` (requires `Flask-Session` with Redis) or document current `session.clear()` mitigation and IP binding limitation.

---

## Wave 3: Configuration & Infrastructure (Parallelizable)

- [x] **CFG-1: Configuration Fail-Fast** - Remove empty string defaults for `SECRET_KEY` and `ADMIN_PASSWORD` in `app/config.py` to force environment validation.
- [x] **CFG-2: Database Connection Pool SQLite Protection** - Add dialect check in `app/__init__.py:214` to only apply pool settings for non-SQLite databases.
- [x] **CFG-3: Add HTTP Compression** - Install `flask-compress`, configure in `app/__init__.py` and `config.py` with `COMPRESS_ALGORITHM = ['zstd', 'br', 'gzip']`.
- [x] **CFG-4: Tune Granian Server** - Update `Dockerfile` to use 4 workers and 60s timeout.
- [x] **CFG-5: Infrastructure-Aware Health Checks** - Expand `/health` to monitor disk space (crucial for SQLite), background worker status, and database integrity. Add a Prometheus-compatible `/metrics` endpoint.

---

## Wave 4: Code Quality Improvements

- [ ] **CQ-1: Create Unified Backup Service** - Move robust logic from `backup.py` and `app/scheduler.py` into a centralized `app/services/backup.py` used by CLI, cron, and scheduler.
- [ ] **CQ-2: Service Layer Extraction** - Centralize shared logic for Slug Generation, Serialization, and Tag Management into `app/services/` to reduce duplication between CLI, API, and Admin routes.
- [ ] **CQ-3: Replace Broad `except Exception`** - Replace with specific exceptions (e.g., `SQLAlchemyError`, `OSError`, `ValueError`) in high-risk files: `backup_encryption.py:243,268`, `webhooks.py:83`, `tasks.py:115,228,246`, `page_view_buffer.py:129,190`.
- [ ] **CQ-4: Improve Transaction Management** - Implement `db_transaction()` context manager in `app/transaction.py` with automatic rollback on `IntegrityError` or `SQLAlchemyError`.
- [ ] **CQ-5: Refactor Large Route Files** - Split `app/routes/public.py` (978 lines) and `app/routes/admin/posts.py` (762 lines) into sub-packages following the `admin/helpers/` pattern.
- [ ] **CQ-6: Standardize String Formatting** - Convert ~89 instances of `%` formatting to f-strings, focusing on `posts.py`, `public.py`, and `scheduler.py`.
- [ ] **CQ-7: CLI Error Handling** - Add `commit_with_rollback()` or `db_transaction()` to all `db.session.commit()` calls in `app/cli.py` (15+ instances).

---

## Wave 5: Performance Optimizations

- [ ] **PERF-1: Fix N+1 in RSS/Atom Feeds** - Add `joinedload(Post.tags)` to `_get_feed_posts()` in `app/routes/rss.py`.
- [ ] **PERF-2: Fix N+1 in Series View** - Add `joinedload(PostSeries.post)` in `app/routes/public.py:419-429`.
- [ ] **PERF-3: Add Missing Database Indexes** - Create migration for `ix_posts_scheduled_publish_at` and `ix_share_events_platform`.
- [ ] **PERF-4: CSS Minification & Consolidation** - Import CSS in `main.js` for Vite processing. Delete redundant `style.css` (80KB) after verifying no references.
- [ ] **PERF-5: Fix Lazy Load Fallback** - Replace existing fallback in `lazy-load.js` with a proper `IntersectionObserver` polyfill.
- [ ] **PERF-6: Prefetch Rate Limiting** - Add `MAX_CONCURRENT = 3` and `MAX_QUEUE = 10` to `prefetch.js`. Use `AbortController` for cancellation.
- [ ] **PERF-7: Optimize Celery Tasks** - Add `retry_backoff=True`, `task_routes` for different queues, and ensure `db.session.remove()` in `finally` blocks.
- [ ] **PERF-8: Optimize FTS5 Search** - Replace custom ranking logic in `app/search.py` with native `bm25()` and `snippet()` functions.
- [ ] **PERF-9: Enable Page View Buffer** - Set `PAGE_VIEW_BUFFER_SIZE = 100` for production in `config.toml`.

---

## Wave 6: Frontend Improvements

- [ ] **FE-1: Navigation Enhancements** - Remove unnecessary homepage breadcrumb. Add mobile search icon toggle and reorder search in mobile menu.
- [ ] **FE-2: Sidebar & Footer Polish** - Remove duplicate subscribe form from footer. Add "Recent Posts" and context-aware "Series Navigation" to sidebar. Fix hardcoded footer year.
- [ ] **FE-3: Visual Improvements** - Add Toast CSS to public stylesheet. Implement "Reading Time" clock icon in post cards. Fix image skeleton animation by adding `.loaded` class in `lazy-load.js`.
- [ ] **FE-4: Pagination** - Replace "Newer/Older" with numbered pagination using the existing macro in `macros.html`.
- [ ] **FE-5: Critical CSS Automation** - Install `vite-plugin-beasties` to automate inlining of critical CSS and remove ~65 lines of manual inline CSS from `base.html`.

---

## Wave 7: Documentation (Parallelizable)

- [ ] **DOC-1: Post Series Guide** - Document workflow, examples, and comparison with tags in `USAGE.md`.
- [ ] **DOC-2: Preview Links Guide** - Document HMAC security, expiry, and programmatic generation in `USAGE.md`.
- [ ] **DOC-3: Syntax Highlighting Docs** - Add theme table and document the `main.js` hardcoding bug/fix in `USAGE.md`.
- [ ] **DOC-4: Analytics Guide** - Add interpretation guide (Traffic Sources, Share Events) to `USAGE.md`.
- [ ] **DOC-5: Rate Limiting & Vite Guides** - Add troubleshooting for rate limiting and a "Vite for Admins" guide to `DEPLOY.md`.

---

## Wave 8: Future Features (Implementation)

- [ ] **FEAT-1: Audit Log UI** - Integrate existing `AdminAuditLog` model with a dashboard UI for tracking admin actions.
- [ ] **FEAT-2: Post Revision Diff** - Implement a diff viewer for `PostRevision` using Python's `difflib`.
- [ ] **FEAT-3: Comments System** - Implement `Comment` model with nested replies and moderation.
- [ ] **FEAT-4: 2FA** - Add TOTP support for admin logins.

---

## Wave 9: Strategic Cleanup & Simplification

- [ ] **STRAT-1: Celery vs APScheduler** - Strategic decision: Either stabilize Celery (downgrade to Python 3.12 for worker stability) OR remove Celery entirely and use APScheduler for all async tasks to simplify the stack (removes Redis dependency).
- [ ] **STRAT-2: Codebase Reduction** - If simplifying, remove: `webhooks.py`, `celery_app.py`, `page_view_buffer.py`, `backup_encryption.py` (if GPG subprocess is enough), and `tag_cache.py`.
- [ ] **STRAT-3: Python 3.14 Compatibility** - If keeping Celery, wait for 3.14 support or stick to 3.12 for stability.

---

## Implementation Notes for Future Agents

### Security Rules
- **Log ID, not Username**: When logging user actions, always use `user.id`. Never log raw objects or usernames.
- **SSRF Validation**: Use `is_safe_webhook_url` BEFORE any `requests.post` call in background tasks.
- **HMAC Comparison**: Always use `hmac.compare_digest()` for tokens.

### Database Rules
- **FTS5 Sync Timing**: Sync FTS index BEFORE `db.session.commit()`. If commit fails, FTS doesn't need rollback because it's a virtual table based on real data (or handle it with a transaction if using FTS5 `content` option).
- **WAL Mode**: Always use `sqlite3.backup()` for backups when WAL mode is enabled to ensure `shm` and `wal` files are handled correctly.

### Frontend Rules
- **Vite Imports**: Use `import.meta.glob` for all dynamic route-based module loading in `main.js`.
- **CSS Precedence**: `vite_asset` handles hashing. Ensure `base.css` is loaded first.

---

## Verification Checklist
1. `pytest tests/ --cov=app` (Goal: 80%+)
2. `npm run build` (Verify dist chunks)
3. `ruff check app/`
4. `mypy app`
5. `flask db upgrade` (Verify migrations)
