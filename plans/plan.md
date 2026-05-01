# Consolidated Improvement Plan

**Date:** 2026-05-01
**Status:** Active
**Source Plans:** plan.md (COMPLETED), plan2.md, plan3.md, plan4.md, plan5.md, plan6.md, plan7.md, plan8.md, plan9.md

---

## Wave 1: Critical Bug Fixes (DO FIRST - Can run in parallel)

### Backend Bugs

- [ ] **BUG-1: Fix Rate Limiter Config Key Mismatch** - `app/__init__.py:186` assigns to `RATELIMIT_STORAGE_URL` but Flask-Limiter expects `RATELIMIT_STORAGE_URI`. The imported variable is `RATE_LIMIT_STORAGE_URI` - key name is wrong.
- [ ] **BUG-2: Fix Scheduler File Lock Race Condition** - `os.remove(lock_path)` dangerous on Linux; remove all lock file deletions from `app/scheduler.py` (8 locations found: lines 77, 147, 160, 198, 211, 257, 277, 319)
- [ ] **BUG-3: Fix Backup Strategy Incompatible with WAL Mode** - `shutil.copy2()` in `app/scheduler.py:299` misses WAL file; use `sqlite3.backup()` API instead (backup.py doesn't exist as separate file)
- [ ] **P0-1: Fix Broken CI Pipeline** - Add `ruff` and `mypy` to `requirements-dev.txt` (missing from CI but used in GitHub Actions) - CONFIRMED
- [ ] **P0-2: Fix JavaScript Dynamic Imports** - Replace variable-based `import(path).then(...)` with `import.meta.glob()` for Vite-compatible bundling in `app/static/js/main.js:4` - CONFIRMED
- [ ] **BUG-4: SSRF in Webhook Delivery** - No `is_safe_webhook_url()` utility exists. `app/webhooks.py:49` and `app/tasks.py:197` make direct requests.post() calls without validation. Create SSRF protection utility, add `allow_redirects=False`
- [ ] **BUG-5: Fix Python 3.12 sqlite3 Datetime Deprecation** - No datetime adapter registration found in `app/__init__.py`. Register custom adapters for datetime handling

### Frontend Bugs

- [ ] **FE-BUG-1: Fix Invalid Nested Anchor Tags** - Invalid HTML5 in post cards. `app/templates/index.html:22` opens outer `<a class="post-card">`, then `app/templates/index.html:40` has nested `<a class="tag">` - anchor nested inside anchor. Use CSS pseudo-element "stretched link" pattern. Also affects: `tag.html`, `search.html`, `archive.html`
- [ ] **FE-BUG-2: Fix Admin Templates to Use vite_asset()** - `app/templates/admin/base.html:8-14` uses `url_for('static', filename='css/...')` for stylesheets instead of `vite_asset()`. Bypasses Vite cache-busting.
- [ ] **FE-BUG-3: Fix Hero Gradient Text Accessibility** - `app/templates/base.html:59` and `app/static/css/style.css:367` use gradient text with `-webkit-text-fill-color: transparent`. Text invisible in Windows High Contrast Mode, fails WCAG AA. `app/static/css/base.css` does NOT have gradient (only base.css:69-96 has variables). Add fallback or aria-label.

---

## Wave 2: Security Hardening (HIGH - Can run in parallel with Wave 1)

- [ ] **SEC-1: Fix Information Leakage in Error Messages** - CONFIRMED in multiple files. `app/routes/admin/newsletter.py:65` exposes exception in flash message. `app/routes/admin/series.py:91,137,162,205,228` expose `str(e)` details. `app/backup_integrity.py:78,80` expose SQLite/verification errors. Strip exception details from user-facing messages.
- [ ] **SEC-2: Upgrade Weak Backup Encryption Key Derivation** - CONFIRMED. `app/backup_encryption.py:37-47` `_derive_key()` just returns `password.encode("utf-8")` - no SHA-256, no PBKDF2. Upgrade to PBKDF2-HMAC-SHA256 with 600,000 iterations (NIST SP 800-132).
- [ ] **SEC-3: Implement Session Fixation Protection** - DISCREPANCY: `app/__init__.py` uses Flask-Caching with Redis (`RedisCache`) for caching, NOT Flask-Session. Sessions are cookie-based with sliding expiration (lines 266-300). Implement Flask-Session with Redis backend OR document current limitation.
- [ ] **SEC-4: Add API Input Validation Gaps** - NOT FOUND: `app/core/validators.py` does not exist. Validators are in `app/validators.py` which only has `validate_string`, `validate_email`, `validate_boolean`. Add `validate_integer()`, `validate_list()`, `validate_tags()` to `app/validators.py`; add Content-Type validation.
- [ ] **SEC-5: Improve Session Timeout & Conditional Nonce Generation** - Generate nonce for ALL requests including static files; add early return for `/static/`, skip nonce for `/api/`/`/rss`. Files: `app/__init__.py`. Verify implementation.
- [ ] **SEC-6: Fix User __repr__ Leaks Username to Logs** - CONFIRMED. `app/models.py:63-64`: `__repr__` returns `f"<User {self.username!r} admin={self.is_admin}>"` exposing username. Change to use `id` instead. Also check admin routes for username logging.

---

## Wave 3: Configuration & Infrastructure (Can run in parallel with Wave 1-2)

- [ ] **CFG-1: Configuration Fail-Fast for Secrets** - CONFIRMED. `app/config.py:80` has `SECRET_KEY = _env("SECRET_KEY", "")` and `app/config.py:86` has `ADMIN_PASSWORD = _env("ADMIN_PASSWORD", "")` - empty string defaults present. While `app/__init__.py:121-133` validates these, remove empty string defaults for fail-fast.
- [ ] **CFG-2: Database Connection Pool SQLite Protection** - DISCREPANCY. `app/__init__.py:214-221` `set_sqlite_pragma` is registered inside `with app.app_context():` which runs on every app creation, not just production. Add dialect check to only apply pool settings for non-SQLite.
- [ ] **CFG-3: Add HTTP Compression** - NOT FOUND in requirements.txt. `flask-compress>=1.24,<2.0` not present. Add to requirements.txt, configure in `app/__init__.py`, `config.py` with zstd/br/gzip.
- [ ] **CFG-4: Tune Granian Server** - Update Dockerfile: 4 workers, 60s timeout. Verify current settings.

---

## Wave 4: Code Quality Improvements (Medium Priority)

- [ ] **CQ-1: Replace Broad `except Exception` Clauses** - CONFIRMED 13+ instances across high-risk files: `backup.py` (top-level), `backup_encryption.py:243,268`, `webhooks.py:83`, `tasks.py:115,228,246`, `page_view_buffer.py:129,190` - need specific exception types
- [ ] **CQ-2: Improve Transaction Management** - CONFIRMED. `app/transaction.py` only has basic IntegrityError/OperationalError rollback, no automatic retry or proper scoping. Enhance with context manager for manual `db.session.commit()` calls.
- [ ] **CQ-3: Refactor Large Route Files** - CONFIRMED line counts: `app/routes/public.py` (978 lines), `app/routes/admin/posts.py` (762 lines). Split into sub-packages following `admin/helpers/` pattern.
- [ ] **CQ-4: Standardize String Formatting** - CONFIRMED. Found **89 matches** of old-style `%` format across codebase, not just 3. Major locations: `posts.py:190,204,283,385,448,756`, `public.py:620,679,690,720,730`, `scheduler.py:141,193,248,253,289,293,300,313,315`. Convert to f-strings systematically.
- [ ] **CQ-5: Add Missing Error Handling in CLI Commands** - DISCREPANCY. `app/cli.py:65-66` has `db.session.commit()` in create-admin without IntegrityError handling. `app/cli.py:86` has commit in promote-admin without transaction guard. Fix these unguarded commits.
- [ ] **CQ-6: Type Hint Coverage Improvement** - Install mypy (already in plan), fix `app/validators.py` type hints (currently missing validate_integer, validate_list, validate_tags), create Pydantic schemas for API validation.
- [ ] **CQ-7: Optimize Celery Tasks** - Add `retry_backoff=True`, task routing, `db.session.remove()` in `app/tasks.py`, `app/celery_app.py`. Verify current retry configuration.

---

## Wave 5: Performance Optimizations

- [ ] **PERF-1: Fix N+1 in RSS/Atom Feeds** - NOT CONFIRMED as clear N+1. `app/routes/rss.py:38-45` shows simple query. Verify if joinedload is needed after code review. May be a false positive.
- [ ] **PERF-2: Fix N+1 in Series View** - CONFIRMED. `app/routes/public.py:419-429` fetches PostSeries objects, then `sp.post` access in line 429 lazy-loads each post individually - classic N+1. Add `joinedload(PostSeries.post)` or `selectinload(PostSeries.post)`.
- [ ] **PERF-3: Add Missing Database Indexes** - CONFIRMED. `ix_posts_scheduled_publish_at` NOT in Post.__table_args__ (line 154-160). `ix_share_events_platform` NOT in ShareEvent.__table_args__ (line 252-254). Create Alembic migration.
- [ ] **PERF-4: CSS Not Minified** - Import CSS files in main.js for Vite processing. Files: `vite.config.js`, `app/static/js/main.js`. Verify CSS processing.
- [ ] **PERF-5: Remove Duplicate CSS Variables** - CONFIRMED. `app/templates/base.html:25-41` inline `:root` CSS variables duplicate `app/static/css/base.css:69-96`. Remove inline, consolidate in base.css.
- [ ] **PERF-6: Fix Broken Lazy Load Fallback** - DISCREPANCY. `lazy-load.js` exists but condition `rect.top > window.innerHeight` may miss in-viewport images. Replace with proper Intersection Observer polyfill.
- [ ] **PERF-7: Delete Redundant style.css** - CONFIRMED. `app/static/css/style.css` exists with 80,496 bytes (~80KB). Comment in `base.css:2` says "Generated from style.css" - legacy file.
- [ ] **PERF-8: Conditional Admin Prism Loading** - CONFIRMED. `app/templates/admin/base.html:162-163` loads Prism.js unconditionally on ALL admin pages. Only load when `pre[class*="language-"]` exists.
- [ ] **PERF-9: Vite JS Code Splitting** - CONFIRMED. `vite.config.js` has NO `manualChunks` configuration. Add code splitting for vendor libs.
- [ ] **PERF-10: Enable Page View Buffer** - CONFIRMED. `app/page_view_buffer.py:32` has `PAGE_VIEW_BUFFER_SIZE = int(os.environ.get("PAGE_VIEW_BUFFER_SIZE", "0"))` - defaults to 0 (disabled). Set to 100 in production.
- [ ] **PERF-11: Improve Cache Efficiency** - CONFIRMED. `app/context_processors.py:94` footer cache TTL is **45 seconds**, not 300s. Update to 300s, add Redis pool config, eviction policy.
- [ ] **PERF-12: Add AVIF Image Support** - Extend `generate_image_variants` to create AVIF variants. Verify current implementation.
- [ ] **PERF-13: Prefetch Rate Limiting** - Add max 3 concurrent, queue size 10, AbortController. Verify current prefetch implementation.
- [ ] **PERF-14: Optimize FTS5 Search** - Use built-in `bm25()` and `snippet()` instead of custom logic. Verify current search implementation.
- [ ] **PERF-15: Database Connection Pooling** - Add `pool_use_lifo=True` to SQLAlchemy engine options in `app/__init__.py`. Verify current pool settings.
- [ ] **PERF-16: Optimize Responsive Image LCP** - Add `fetchpriority="high"` to hero images. Verify image loading.
- [ ] **PERF-17: joinedload vs selectinload** - DISCREPANCY. `app/routes/api.py` is a SINGLE FILE, not `app/routes/api/` directory. All queries use `joinedload` (lines 114, 143, 272, 350). Consider `selectinload` for large collections to avoid Cartesian products.
- [ ] **PERF-18: Backup Encryption Subprocess** - Verify `python-gnupg>=0.5.0` in requirements.txt, remove insecure subprocess fallback in `app/backup_encryption.py`.

---

## Wave 6: Frontend Improvements

- [ ] **FE-1: Remove Unnecessary Homepage Breadcrumb** - Single-item breadcrumb has zero user value
- [ ] **FE-2: Fix Hardcoded Footer Year** - `&copy; 2026` should use `{{ current_year }}` template variable
- [ ] **FE-3: Add Toast CSS to Public Stylesheet** - Toast JS loaded but unstyled on public pages
- [ ] **FE-4: Improve Pagination with Numbered Pages** - Replace "Newer/Older" with numbered pagination using existing macro
- [ ] **FE-5: Add Mobile Search Visibility** - Search hidden on mobile; reorder in mobile menu + add search icon toggle
- [ ] **FE-6: Improve Sidebar Utility** - Remove duplicate subscribe from footer, add recent posts, series navigation
- [ ] **FE-7: Regroup Admin 'More' Dropdown** - Group dropdown items (Content, Users, System) with visual separation in admin base template
- [ ] **FE-8: Improve Empty State Engagement** - Public empty state wrongly says "Create your first post", add subscribe form
- [ ] **FE-9: Optimize Post Card Hover Transition** - Change cubic-bezier for snappier feel
- [ ] **FE-10: Add Reading Time Icon** - Add clock icon to reading time display
- [ ] **FE-11: Fix Image Skeleton Animation** - Skeleton animation not triggered; fix `lazy-load.js` and add wrapper div
- [ ] **FE-12: Add Secondary Accent Color** - Add `--brand` color for logo brackets differentiation in CSS
- [ ] **FE-13: Automate Critical CSS Generation** - Install `vite-plugin-beasties` to inline critical CSS, remove 65 lines of inline CSS from `base.html`

---

## Wave 7: Backend Improvements

- [ ] **BE-1: Centralized Error Handling** - Create `app/core/errors.py` with RFC 7807 Problem Details format; register API error handlers
- [ ] **BE-2: Event-Driven FTS5 Sync** - Add SQLAlchemy event listeners (`after_insert/update/delete`) for automatic FTS sync; remove manual `sync_fts()` calls in `app/search.py`
- [ ] **BE-3: Rate Limiting Enhancements** - Exempt `/robots.txt`, `/favicon.ico`; increase health check; add burst protection
- [ ] **BE-4: File Upload Extension Check Order** - Remove redundant `_allowed_file()`, ensure magic byte validation runs first in `app/routes/admin/media.py`

---

## Wave 8: Documentation Improvements

- [ ] **DOC-1: Post Series Documentation** - Add to USAGE.md (after "Tags") - workflow, examples, Series vs Tags comparison, gotchas
- [ ] **DOC-2: Preview Links Documentation** - Add to USAGE.md (after "Short URLs") - security mechanism, code examples, use cases
- [ ] **DOC-3: Syntax Highlighting Documentation** - Expand settings docs in USAGE.md - theme table, bug warning (main.js:71 hardcodes Okaidia), how to add themes
- [ ] **DOC-4: Analytics Interpretation Guide** - Add guide with actions to take in USAGE.md
- [ ] **DOC-5: Search Features Documentation** - Expand with highlighting, did-you-mean, FTS5 tips, limitations, index rebuild instructions
- [ ] **DOC-6: Rate Limiting Documentation** - Add troubleshooting guide to DEPLOY.md
- [ ] **DOC-7: Vite for Admins Guide** - Add guide to DEPLOY.md
- [ ] **DOC-8: Expand README.md** - Add database models section

---

## Wave 9: Future Features (Implementation Phase)

### Quick Wins (1-4 hours each)
- [ ] **FEAT-1: Activity/Audit Log** - Model exists at `models.py:397-417` but NOT actively used; integrate with existing utility function
- [ ] **FEAT-2: Post Revision Diff Viewer** - `PostRevision` model exists; just needs diff UI using Python's `difflib`

### High Impact Features (1-2 days each)
- [ ] **FEAT-3: Comments System** - New `Comment` model with nested replies, spam detection, moderation UI
- [ ] **FEAT-4: Two-Factor Authentication (2FA)** - Add TOTP to User model, modify login flow, QR code enrollment
- [ ] **FEAT-5: Author Profiles & Bylines** - Extend User/Post models with profile fields, add `/author/<username>` route

### Medium Priority Features
- [ ] **FEAT-6: Hierarchical Categories** - New `Category` model with self-referential parent/children relationships
- [ ] **FEAT-7: Content Approval Workflow** - Add `status`, `reviewer_id`, `review_notes` to Post model; approval queue
- [ ] **FEAT-8: SEO Analysis Panel** - Client-side real-time analysis in post editor (title length, keyword density, etc.)
- [ ] **FEAT-9: Broken Link Checker** - New `LinkCheck` model, Celery task for async link verification, admin UI
- [ ] **FEAT-10: Custom Fields/Meta Fields** - New `PostMeta` model for key-value pairs on posts

### Nice to Have Features
- [ ] **FEAT-11: PWA Support** - Service worker, manifest.json, offline caching
- [ ] **FEAT-12: Dark Mode Toggle for Readers** - Refactor public CSS to use CSS custom properties
- [ ] **FEAT-13: Post Templates** - New `PostTemplate` model for reusable templates
- [ ] **FEAT-14: Auto Internal Linking** - API endpoint suggestions using FTS5
- [ ] **FEAT-15: OAuth/SSO Login** - New `OAuth` model, Flask-Dance integration
- [ ] **FEAT-16: Podcast/RSS Enclosure Support** - Add audio fields to Post, iTunes namespace in RSS

### Integration Features
- [ ] **FEAT-17: Social Media Auto-Post** - New `SocialAccount` model, webhook triggers, platform APIs (tweepy, Mastodon.py)
- [ ] **FEAT-18: Webmention Support** - New `Webmention` model, verification endpoint, mf2py parsing
- [ ] **FEAT-19: Analytics Integration** - Plausible/Umami/SimpleAnalytics script embedding

---

## Wave 10: Technical Debt & Cleanup (Future)

- [ ] **DEBT-1: Python 3.14 Compatibility** - Downgrade Dockerfile from `python:3.14-slim` to `python:3.12-slim` (Celery 5.3.x lacks 3.14 support)
- [ ] **DEBT-2: Mixed Async Simplification** - Choose Option A (remove Celery, use APScheduler-only) to eliminate Redis dependency (plan5.md)
- [ ] **DEBT-3: Codebase Over-Engineering Reduction** - Remove: webhooks.py, celery_app.py/tasks.py, page_view_buffer.py, backup_encryption.py, backup_integrity.py, S3 storage abstraction, tag_cache.py, transaction.py, unnecessary models (AdminAuditLog, ShareEvent, PostRevision, AdminSession) → reduce ~3,000-3,500 LOC
- [ ] **DEBT-4: Test Coverage Gap** - Current 62.39% (below 80% threshold); add tests for zero-coverage files, fix 4 failing benchmark tests, expand E2E coverage
- [ ] **DEBT-5: Migration Hygiene** - Add CI check for multiple heads, remove manual alembic_version updates, use hex revision IDs
- [ ] **DEBT-6: Backup Strategy Automation** - Remove `profiles: - backup`, add cron for daily 2AM backups, integrate S3 sync into `backup.py`
- [ ] **DEBT-7: Frontend Modernization** - Run Vite build, bundle vendor libs, add ESLint/Prettier
- [ ] **DEBT-8: Error Handling Patterns** - Replace 14 broad `except Exception`, add logging to silent failures, replace `logger.error()` with `logger.exception()`
- [ ] **DEBT-9: Documentation Refinement** - Split DEPLOY.md/USAGE.md into `docs/` subdirectories
- [ ] **DEBT-10: Monitoring Gaps** - Add `/metrics` endpoint (Prometheus), add Sentry SDK, wrap APScheduler jobs with metrics
- [ ] **DEBT-11: File Cleanup (.DS_Store)** - Remove 3 tracked `.DS_Store` files from repo

---

## Dependencies & Notes

### Critical Path
1. Wave 1 (Bugs) must complete before Wave 4+ (Code Quality)
2. Wave 2 (Security) can run in parallel with Wave 1
3. Wave 3 (Config) can run in parallel with Wave 1-2
4. Wave 8 (Docs) can run anytime (informational)
5. Wave 9 (Features) and Wave 10 (Tech Debt) are independent

### Parallelization Strategy
- **Wave 1A (Backend Bugs)**: BUG-1, BUG-2, BUG-3, BUG-4, BUG-5, P0-1, P0-2 - Can run in parallel
- **Wave 1B (Frontend Bugs)**: FE-BUG-1, FE-BUG-2, FE-BUG-3 - Can run in parallel (separate agent)
- **Wave 2 (Security)**: SEC-1 through SEC-6 - Can run in parallel
- **Wave 3 (Config)**: CFG-1 through CFG-4 - Can run in parallel
- **Wave 4, 5, 6, 7**: Can be split across 4 sub-agents working in parallel
- **Wave 8, 9, 10**: Sequential work, can have 1 sub-agent handle all

### Known Issues from Plans
- `app/static/js/main.js:4` uses variable-based import() instead of import.meta.glob()
- `WebhookEvent.webhook_id` never populated
- Webhook Celery task missing HMAC signing
- Post Series has zero documentation
- Preview Links has no user guide
- Admin Audit Logs model exists but no implementation

### Files at Risk (Broad Exception Handling)
- `app/backup.py` (top-level backup module)
- `app/backup_encryption.py:243,268`
- `app/webhooks.py:83`
- `app/tasks.py:115,228,246`
- `app/page_view_buffer.py:129,190`

### Codebase Structure Notes
- API routes are in `app/routes/api.py` (SINGLE FILE), not `app/routes/api/` directory
- Backup functionality is in `app/scheduler.py:run_daily_backup()` not separate `app/backup.py`
- Validators are in `app/validators.py`, NOT `app/core/validators.py`
- Admin Audit Log model at `app/models.py:397-417`
- PostRevision model at `app/models.py:173`

### Verification Status Summary
- **CONFIRMED**: 15 items verified in codebase
- **DISCREPANCY**: 10 items have location/content differences
- **NOT FOUND**: 5 items missing from expected locations
- **89 instances** of old-style % string formatting found (not 3)