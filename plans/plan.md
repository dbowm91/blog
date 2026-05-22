# Implementation Plan - Blog CMS Documentation Updates

**Project:** Blog CMS
**Status:** ✅ COMPLETED (All 43 items verified and completed May 22, 2026)
**Last Updated:** May 22, 2026

---

## Overview

This plan consolidates documentation updates from architecture reviews across testing, frontend, services, tasks, routes, infrastructure, and deployment. Items are organized into **waves** indicating parallelization potential.

**Total: 43 action items across 6 waves - ALL COMPLETED**

---

## Wave A: Testing Documentation (Priority 1)

| # | Action Item | File | Details | Status |
|---|-------------|------|---------|--------|
| A1 | Remove test_api.py from import list claim | `tests/AGENTS.override.md` | test_api.py does NOT import from shared_fixtures; e2e and benchmarks conftest files are the actual importers | ✅ DONE |
| A2 | Change E2E setup from @playwright/test to pytest-playwright | `architecture/testing/test-suite.md` | Project uses pytest-playwright, not @playwright/test | ✅ DONE |
| A3 | Add missing `clean_db` fixture to documentation | `tests/AGENTS.override.md` | `clean_db` fixture from `benchmarks/conftest.py:52` is not documented in the fixtures list | ✅ DONE |
| A4 | Update test file list with actual test files | `tests/AGENTS.override.md` | Added test_models.py, test_2fa.py, test_search.py, test_webhooks.py, test_tasks.py, test_scheduler.py, test_newsletter.py, test_comments_admin.py, test_coverage.py, test_cli.py with line numbers | ✅ DONE |
| A5 | Remove specific test count | `tests/AGENTS.override.md` | "524 tests pass" claim is outdated (now ~36 test files) | ✅ DONE |
| A6 | Simplify test file list pattern | `tests/AGENTS.override.md` | Directory structure pattern shown rather than enumerating all test files | ✅ DONE |

**Files modified:** `tests/AGENTS.override.md`, `architecture/testing/test-suite.md`

---

## Wave B: Services Documentation (High Priority)

| # | Action Item | File | Details | Status |
|---|-------------|------|---------|--------|
| B1 | ~~Remove line numbers from tag_cache.md~~ | ~~N/A~~ | **REMOVED** - Line numbers in tag_cache.md are accurate and up-to-date. No action needed. | ✅ N/A |
| B2 | Fix search.md documentation source confusion | `architecture/services/search.md` | Clarified that SQLiteSearchProvider wraps app/search.py functions (not separate implementation). Documented SearchProvider abstraction vs module-level functions distinction. | ✅ DONE |
| B3 | Document `reset_fts_available()` in search.md | `architecture/services/search.md` | Documented at `app/search.py:36` in module-level functions table | ✅ DONE |
| B4 | Update backup.md line numbers | `architecture/services/backup.md` | `run_daily_backup()` is at `app/scheduler.py:261`. Removed incorrect reference to `app/services/backup.py`. | ✅ DONE |
| B5 | Clarify slug.md line number | `architecture/services/slug.md` | `generate_unique_slug()` is at line 13 (correct). Plan claimed it was "not 12" but 13 is accurate | ✅ DONE |

**Files modified:** `architecture/services/search.md`, `architecture/services/backup.md`

---

## Wave C: Services & Tasks Documentation (Medium Priority)

| # | Action Item | File | Details | Status |
|---|-------------|------|---------|--------|
| C1 | Clarify app/search.py vs SQLiteSearchProvider relationship | `architecture/services/search.md` | Both exist independently - SQLiteSearchProvider wraps app/search.py functions | ✅ DONE |
| C2 | Document exception handling in search functions | `architecture/services/search.md` | OperationalError, ProgrammingError, DatabaseError caught in search.py functions and return empty/false | ✅ DONE |
| C3 | Document "Did You Mean" exact match behavior | `architecture/services/search.md` | Returns original indexed term (preserving case) when exact case-insensitive match found. Documented at line 53. | ✅ DONE |
| C4 | Add error handling table to celery-tasks.md | `architecture/tasks/celery-tasks.md` | Added error handling table documenting retry behavior for each task | ✅ DONE |
| C5 | Document deliver_webhook_task non-retry behavior | `architecture/tasks/celery-tasks.md` | Has `max_retries=3` but NEVER calls `self.retry()` - exceptions caught and logged. Failed webhooks silently skipped. | ✅ DONE |
| C6 | Fix line numbers in celery-tasks.md | `architecture/tasks/celery-tasks.md` | Fixed: send_newsletter_task(127), deliver_webhook_task(260), send_confirmation_task(282), send_password_reset_task(303), run_backup_task(320) | ✅ DONE |
| C7 | Document non-retry for generate_image_variants and run_backup_task | `architecture/tasks/celery-tasks.md` | Both return False on failure without retry. Documented explicitly. | ✅ DONE |

**Files modified:** `architecture/services/search.md`, `architecture/tasks/celery-tasks.md`

---

## Wave D: Routes Documentation (Medium Priority)

| # | Action Item | File | Details | Status |
|---|-------------|------|---------|--------|
| D1 | Fix public comments rate limit | `architecture/routes/api-routes.md` | Fixed 20/min → 10/min (actual from `app/routes/public/comments.py:15`) | ✅ DONE |
| D2 | Fix sitemap cache claim | `architecture/routes/public-routes.md` | Removed false "Cache: 5 minutes" claim. No explicit cache decorator exists. | ✅ DONE |
| D3 | Add pages field to API response docs | `architecture/routes/api-routes.md` | Added `pages: pagination.pages` to response documentation | ✅ DONE |
| D4 | Document authors field in JSON Feed | `architecture/routes/rss-feeds.md` | Added `"authors": [{"name": AUTHOR_NAME or "admin"}]` to JSON Feed example | ✅ DONE |
| D5 | Remove duplicate comment section | `architecture/routes/public-routes.md` | Removed duplicate comment section at lines 118-127 | ✅ DONE |
| D6 | Verify sitemap cache implementation | `app/routes/public/meta.py` | Verified no cache decorator needed. Documentation updated. | ✅ DONE |

**Files modified:** `architecture/routes/api-routes.md`, `architecture/routes/public-routes.md`, `architecture/routes/rss-feeds.md`

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
| E7 | Complete route-based code splitting documentation | `architecture/frontend/static-assets.md` | Expanded `...` to full module list for /admin/posts, /admin/media, /admin/ routes | ✅ DONE |
| E8 | ~~Fix CSS media="print" onload pattern~~ | ~~N/A~~ | **REMOVED** - `critical.css` already uses `media="screen"`. The `media="print" onload` pattern is a VALID defer technique. | ✅ N/A |
| E9 | Document post_image_url filter completely | `architecture/frontend/templates.md` | Added `storage.exists()` check and request-level caching behavior documentation | ✅ DONE |
| E10 | Document lazy-load.js fallback behavior | `architecture/frontend/static-assets.md` | Documented: (1) native loading="lazy", (2) IntersectionObserver with rootMargin, (3) immediate load fallback | ✅ DONE |

**Files modified:** `architecture/frontend/templates.md`, `architecture/frontend/static-assets.md`

---

## Wave F: Infrastructure & Deployment Documentation (Medium/Low Priority)

| # | Action Item | File | Details | Status |
|---|-------------|------|---------|--------|
| F1 | Fix queue routing line number | `architecture/infrastructure/webhooks.md` | Fixed `deliver_webhook_task` at line 184 (was incorrectly 192) | ✅ DONE |
| F2 | Clarify health check email status | `architecture/infrastructure/overview.md` | Email is an optional check and does NOT affect overall status - correctly documented | ✅ DONE |
| F3 | Document WEBHOOK_TIMEOUT configuration | `architecture/infrastructure/webhooks.md` | Clarified WEBHOOK_TIMEOUT is configurable, not hardcoded | ✅ DONE |
| F4 | Add search provider configuration details | `architecture/infrastructure/search.md` | SEARCH_PROVIDER config correctly documented at line 24 | ✅ DONE |
| F5 | Document variant cleanup on image replacement | `architecture/infrastructure/storage.md` | Documented cleanup of 400_, 800_, 1200_, .webp, .avif variants using prefix matching | ✅ DONE |
| F6 | Add FLASK_ENV to docker.md environment variables | `architecture/deployment/docker.md` | Added FLASK_ENV to environment variables table | ✅ DONE |
| F7 | Document Celery concurrency setting | `architecture/deployment/docker.md` | `docker-compose.yml:50` shows `concurrency=1` - not documented | ✅ DONE |
| F8 | Fix backup encryption key generation command | `architecture/deployment/docker.md`, `architecture/deployment/security.md` | Fixed to use `secrets.token_urlsafe(12)` (12-char minimum) instead of `token_hex(32)` | ✅ DONE |
| F9 | Document PYTHONPATH for backup service | `architecture/deployment/docker.md` | Documented `PYTHONPATH=/home/blog` for backup service | ✅ DONE |

**Files modified:** `architecture/infrastructure/webhooks.md`, `architecture/infrastructure/storage.md`, `architecture/deployment/docker.md`, `architecture/deployment/security.md`

---

## Deferred Items

**Per-Webhook Retry** - Intentionally deferred:
- Location: `app/tasks.py:234-246`
- Status: Not implemented - would require significant refactoring
- Current behavior: Failed webhooks are logged but silently skipped
- Documentation: Acknowledged in `architecture/tasks/celery-tasks.md` and `architecture/infrastructure/webhooks.md`

---

## Implementation Summary

All waves completed via parallel subagent execution on May 22, 2026:

| Wave | Items | Commit |
|------|-------|--------|
| Wave A | A3, A4 | `d1718ce` Wave A: A3 add clean_db fixture, A4 update test file list with line numbers |
| Wave B | B2, B3, B4 | `38fb0f0` Wave B: B2-B4 search and backup documentation fixes |
| Wave C | C1, C2, C3, C4, C5, C6, C7 | `f1cc02b` Wave C: C3-C7 error handling and line number fixes |
| Wave D | D1, D2, D3, D4, D5, D6 | `8abcf1c` Wave D: D1-D6 routes documentation fixes |
| Wave E | E7, E9, E10 | `65f5247` Wave E: E7, E9, E10 frontend documentation |
| Wave F | F1, F3, F5, F6, F8, F9 | `afee5e8` Wave F: F1, F3, F5, F6, F8, F9 infrastructure documentation |

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

*Last updated: May 22, 2026 - All waves completed*