# Implementation Plan - Blog CMS Documentation Updates

**Project:** Blog CMS
**Status:** IN PROGRESS (estimated 30% complete based on verified status)
**Last Updated:** May 22, 2026

---

## Overview

This plan consolidates documentation updates from architecture reviews across testing, frontend, services, tasks, routes, infrastructure, and deployment. Items are organized into **waves** indicating parallelization potential.

**Total: 43 action items across 6 waves (verified count after removing invalid items)**

---

## Wave A: Testing Documentation (Priority 1)

| # | Action Item | File | Details | Status |
|---|-------------|------|---------|--------|
| A1 | Remove test_api.py from import list claim | `tests/AGENTS.override.md` | test_api.py does NOT import from shared_fixtures; e2e and benchmarks conftest files are the actual importers | ✅ DONE |
| A2 | Change E2E setup from @playwright/test to pytest-playwright | `architecture/testing/test-suite.md` | Project uses pytest-playwright, not @playwright/test | ✅ DONE |
| A3 | Add missing `clean_db` fixture to documentation | `tests/AGENTS.override.md` | `clean_db` fixture from `benchmarks/conftest.py:52` is not documented in the fixtures list | ⏳ PENDING |
| A4 | Update test file list with actual test files | `tests/AGENTS.override.md` | Missing: test_2fa.py, test_search.py, test_webhooks.py, test_tasks.py, test_scheduler.py, test_newsletter.py, test_comments_admin.py, test_404.py, test_500.py, test_429.py, test_cli.py, test_models.py (line numbers), etc. The ~36 test files are not fully enumerated | ⏳ PENDING |
| A5 | Remove specific test count | `tests/AGENTS.override.md` | "524 tests pass" claim is outdated (now ~36 test files) | ✅ DONE |
| A6 | Simplify test file list pattern | `tests/AGENTS.override.md` | Directory structure pattern shown rather than enumerating all test files | ✅ DONE |

**Files to modify:** `tests/AGENTS.override.md`, `architecture/testing/test-suite.md`

**Parallelization:** All Wave A items are independent and can be done in parallel.

---

## Wave B: Services Documentation (High Priority)

| # | Action Item | File | Details | Status |
|---|-------------|------|---------|--------|
| B1 | ~~Remove line numbers from tag_cache.md~~ | ~~N/A~~ | **REMOVED** - Line numbers in tag_cache.md are accurate and up-to-date. No action needed. | ✅ N/A |
| B2 | Fix search.md documentation source confusion | `architecture/services/search.md` | Documents SearchProvider abstraction but cites `app/search.py` line numbers instead of clarifying that `SQLiteSearchProvider` in `app/services/search/sqlite.py` is a SEPARATE implementation (not a wrapper) | ⏳ PENDING |
| B3 | Document `reset_fts_available()` in search.md | `architecture/services/search.md` | Function at `app/search.py:36` exists but is NOT part of SearchProvider abstraction - it's a module-level function | ⏳ PENDING |
| B4 | Update backup.md line numbers | `architecture/services/backup.md` | `run_daily_backup()` is at `app/scheduler.py:261` (NOT line 145). The function doesn't exist in `app/services/backup.py` | ⏳ PENDING |
| B5 | Clarify slug.md line number | `architecture/services/slug.md` | `generate_unique_slug()` is at line 13 (correct). Plan claimed it was "not 12" but 13 is accurate | ✅ DONE |

**Files to modify:** `architecture/services/search.md`, `architecture/services/backup.md`

**Dependencies:** B2 should be done first to understand the SearchProvider vs app/search.py relationship

---

## Wave C: Services & Tasks Documentation (Medium Priority)

| # | Action Item | File | Details | Status |
|---|-------------|------|---------|--------|
| C1 | Clarify app/search.py vs SQLiteSearchProvider relationship | `architecture/services/search.md` | `app/search.py` module-level functions and `SQLiteSearchProvider` class in `app/services/search/sqlite.py` are SEPARATE implementations, NOT a wrapping relationship. Both exist independently | ⏳ PENDING |
| C2 | Document exception handling in search functions | `architecture/services/search.md` | OperationalError, ProgrammingError, DatabaseError caught in search.py functions and return empty/false | ✅ DONE |
| C3 | Document "Did You Mean" exact match behavior | `architecture/services/search.md` | `app/search.py:349-351` returns original indexed term (preserving case) when exact case-insensitive match is found. `search.md` mentions fuzzy matching but not the case-preserving return | ⏳ PENDING |
| C4 | Add error handling table to celery-tasks.md | `architecture/tasks/celery-tasks.md` | Document retry behavior for each task | ⏳ PENDING |
| C5 | Document deliver_webhook_task non-retry behavior | `architecture/tasks/celery-tasks.md` | Has `max_retries=3` but NEVER calls `self.retry()` - exceptions caught at `app/tasks.py:234-246` don't trigger Celery retry. Failed webhooks are silently skipped | ⏳ PENDING |
| C6 | Fix line numbers in celery-tasks.md | `architecture/tasks/celery-tasks.md:116` | `db.session.remove()` lines: send_newsletter_task at 181 (not 178), deliver_webhook_task at 260 (not 258) | ⏳ PENDING |
| C7 | Document non-retry for generate_image_variants and run_backup_task | `architecture/tasks/celery-tasks.md` | Both return False on failure without retry (tasks.py lines 121, 124, 320) | ⏳ PENDING |

**Files to modify:** `architecture/services/search.md`, `architecture/tasks/celery-tasks.md`

**Parallelization:** C2, C3 depend on understanding B2 (search architecture). C4-C7 are independent of C1-C3.

---

## Wave D: Routes Documentation (Medium Priority)

| # | Action Item | File | Details | Status |
|---|-------------|------|---------|--------|
| D1 | Fix public comments rate limit | `architecture/routes/api-routes.md:139` | Documentation claims 20/min, actual is 10/min (`app/routes/public/comments.py:15`) | ⏳ PENDING |
| D2 | Fix sitemap cache claim | `architecture/routes/public-routes.md:99` | Claims "Cache: 5 minutes" but `app/routes/public/meta.py:177-181` has NO explicit cache decorator - only `@limiter.limit("60 per minute")` | ⏳ PENDING |
| D3 | Add pages field to API response docs | `architecture/routes/api-routes.md:36-44` | Response includes `pages: pagination.pages` (line 79 in api/posts.py) not documented | ⏳ PENDING |
| D4 | Document authors field in JSON Feed | `architecture/routes/rss-feeds.md` | `app/routes/rss.py:272` includes `"authors": [{"name": AUTHOR_NAME or "admin"}]` not documented | ⏳ PENDING |
| D5 | Remove duplicate comment section | `architecture/routes/public-routes.md:118-127` | Comment routes described twice - second occurrence is duplicate | ⏳ PENDING |
| D6 | Verify sitemap cache implementation | `app/routes/public/meta.py` | If 5-minute caching intended, add `@flask_cache.cached(timeout=300)` to `sitemap_xml()` | ⏳ PENDING |

**Files to modify:** `architecture/routes/api-routes.md`, `architecture/routes/public-routes.md`, `app/routes/public/meta.py` (if D6)

**Parallelization:** D1-D6 are all independent and can be done in parallel.

---

## Wave E: Frontend Documentation (High/Medium Priority)

| # | Action Item | File | Details | Status |
|---|-------------|------|---------|--------|
| E1 | ~~Update templates.md directory structure~~ | ~~N/A~~ | **REMOVED** - templates.md already shows `admin/editor.html` (not posts.html) and no `admin/newsletter.html` | ✅ DONE |
| E2 | ~~Fix templates.md context processors~~ | ~~N/A~~ | **REMOVED** - templates.md already correctly shows `site_title` and `site_description` | ✅ DONE |
| E3 | Update app/templates/AGENTS.override.md structure | `app/templates/AGENTS.override.md` | Lists non-existent files; missing actual templates like `admin/backup_codes.html`, `admin/2fa_setup.html` | ✅ DONE |
| E4 | Add critical.css to static-assets.md | `architecture/frontend/static-assets.md` | `critical.css` exists at `app/static/css/critical.css` and is used in `base.html:22` with `media="screen"` | ✅ DONE |
| E5 | Add critical.css to AGENTS.override.md | `app/static/AGENTS.override.md` | CSS section doesn't include `critical.css` | ✅ DONE |
| E6 | ~~Update static-assets.md module list~~ | ~~N/A~~ | **REMOVED** - upload.js and image-preview.js are already listed in static-assets.md lines 37-39 | ✅ DONE |
| E7 | Complete route-based code splitting documentation | `architecture/frontend/static-assets.md:66-70` | Uses `...` ellipsis but should show full module list. Full list in `main.js:30-62`: `/admin/posts`: utils, modal, nav-dropdown, filter-select, toast, shortcuts, bulk, editor, image-preview; `/admin/media`: utils, modal, nav-dropdown, filter-select, toast, shortcuts, bulk, upload, image-preview; `/admin/`: utils, modal, nav-dropdown, filter-select, toast, shortcuts, bulk | ⏳ PENDING |
| E8 | ~~Fix CSS media="print" onload pattern~~ | ~~N/A~~ | **REMOVED** - `critical.css` already uses `media="screen"`. The `media="print" onload` pattern for non-critical CSS is a VALID and widely-used defer technique, not a bug. `base.html:23-28` use this pattern correctly | ✅ N/A |
| E9 | Document post_image_url filter completely | `architecture/frontend/templates.md:80` | Current description incomplete - doesn't mention `storage.exists()` check at `app/filters.py:45,50` that returns None if file missing, or the request-level caching behavior | ⏳ PENDING |
| E10 | Document lazy-load.js fallback behavior | `architecture/frontend/static-assets.md` | JS fallback behavior not documented: (1) native `loading="lazy"` if supported, (2) IntersectionObserver with `rootMargin: '200px 0px'` as polyfill, (3) loads all immediately if no IntersectionObserver support | ⏳ PENDING |

**Files to modify:** `architecture/frontend/templates.md`, `architecture/frontend/static-assets.md`

**Parallelization:** E7, E9, E10 are independent. E1-E6, E8 are DONE.

---

## Wave F: Infrastructure & Deployment Documentation (Medium/Low Priority)

| # | Action Item | File | Details | Status |
|---|-------------|------|---------|--------|
| F1 | Fix queue routing line number | `architecture/infrastructure/webhooks.md:125` | Says `app/tasks.py:192` but `deliver_webhook_task` is at line 184 | ⏳ PENDING |
| F2 | Clarify health check email status | `architecture/infrastructure/overview.md` | Email is an optional check (line 34) and does NOT affect overall status - correctly documented | ✅ DONE |
| F3 | Document WEBHOOK_TIMEOUT configuration | `architecture/infrastructure/webhooks.md` | `app/config.py:140` shows `WEBHOOK_TIMEOUT` is configurable via config, but webhooks.md line 69 says "10 second timeout" implying hardcoded | ⏳ PENDING |
| F4 | Add search provider configuration details | `architecture/infrastructure/search.md` | SEARCH_PROVIDER config correctly documented at line 24 | ✅ DONE |
| F5 | Document variant cleanup on image replacement | `architecture/infrastructure/storage.md` | `upload_with_processing()` cleans up old variants (400_, 800_, 1200_, .webp, .avif) using prefix matching before creating new ones. Not documented in storage.md | ⏳ PENDING |
| F6 | Add FLASK_ENV to docker.md environment variables | `architecture/deployment/docker.md` | ADMIN_USERNAME documented but FLASK_ENV missing from environment variables table | ⏳ PENDING |
| F7 | Document Celery concurrency setting | `architecture/deployment/docker.md` | `docker-compose.yml:50` shows `concurrency=1` - not documented | ✅ DONE |
| F8 | Fix backup encryption key generation command | `architecture/deployment/docker.md:132`, `architecture/deployment/security.md:57-62` | Command shows `secrets.token_hex(32)` which generates 64 hex characters, but 12-character minimum is required. Should use `secrets.token_urlsafe(12)` or similar | ⏳ PENDING |
| F9 | Document PYTHONPATH for backup service | `docker-compose.yml:114` | `PYTHONPATH=/home/blog` for backup service - docker.md doesn't mention this | ⏳ PENDING |

**Files to modify:** `architecture/infrastructure/webhooks.md`, `architecture/infrastructure/overview.md`, `architecture/infrastructure/storage.md`, `architecture/deployment/docker.md`, `architecture/deployment/security.md`

**Parallelization:** F1-F9 are all independent and can be done in parallel.

---

## Implementation Order (Waves)

### Phase 1: High Priority (Waves A, B)
**Recommended: Run Wave A and Wave B in parallel with sub-agents**

1. Wave A - Testing documentation fixes (A1, A2, A3, A4, A5, A6)
2. Wave B - Services documentation fixes (B2, B3, B4)

### Phase 2: Medium Priority (Waves C, D, E)
**Recommended: Run Waves C, D, E in parallel with sub-agents**

3. Wave C - Services & Tasks documentation (C1, C2, C3, C4, C5, C6, C7)
4. Wave D - Routes documentation (D1, D2, D3, D4, D5, D6)
5. Wave E - Frontend documentation (E7, E9, E10)

### Phase 3: Lower Priority (Wave F)
6. Wave F - Infrastructure & Deployment documentation (F1, F3, F5, F6, F8, F9)

---

## Deferred Items

**Per-Webhook Retry** - Intentionally deferred:
- Location: `app/tasks.py:234-246`
- Status: Not implemented - would require significant refactoring
- Current behavior: Failed webhooks are logged but silently skipped
- Documentation: Acknowledged in `architecture/tasks/celery-tasks.md` and `architecture/infrastructure/webhooks.md`

---

## Notes for Future Agents

### Verification Steps
When updating line numbers in documentation, verify against actual source:
- Use `grep -n` or read the file directly to confirm current line numbers
- Line numbers change with code modifications; use functional descriptions when possible

### Context for Implementation
- **Search Provider Architecture**: `app/search.py` and `SQLiteSearchProvider` in `app/services/search/sqlite.py` are SEPARATE implementations. The SearchProvider abstraction is a wrapper/interface pattern, but the actual functions in app/search.py are standalone FTS5 functions. See `app/services/search/__init__.py` for the abstraction.
- **Celery Tasks**: Verify task behavior in `app/tasks.py` before documenting error handling
- **Frontend Templates**: Check `app/templates/` directory for actual template files
- **Routes**: Cross-reference route handlers in `app/routes/` with documentation
- **Lazy Load JS**: See `app/static/js/shared/lazy-load.js` for full fallback behavior

### Key Line Numbers (Verified May 2026)
- `app/tasks.py`: generate_image_variants(28), send_newsletter_task(127), deliver_webhook_task(184), send_confirmation_task(263), send_password_reset_task(284), run_backup_task(305)
- `app/search.py`: reset_fts_available(36), search(201), sync_fts(112), sync_fts_batch(136), remove_fts(177), rebuild_fts(102), get_search_snippets(282), get_did__mean(327), highlight_query(356), extract_snippet(253), get_indexed_terms(224)

---

*Last updated: May 22, 2026*
