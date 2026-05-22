# Implementation Plan - Blog CMS Documentation Updates

**Project:** Blog CMS
**Status:** IN PROGRESS (38% complete - Wave A and E3/E5 done, E1-E2,E4,E6-E10, Waves B-F remaining)
**Last Updated:** May 22, 2026

---

## Overview

This plan consolidates documentation updates from architecture reviews across testing, frontend, services, tasks, routes, infrastructure, and deployment. Items are organized into **waves** indicating parallelization potential.

**Total: 45 action items across 6 waves (8 completed, 37 pending)**

---

## Wave A: Testing Documentation Fixes (Priority 1)

| # | Action Item | File | Details | Status |
|---|-------------|------|---------|--------|
| A1 | **Remove test_api.py from import list** | `tests/AGENTS.override.md` line 73 | test_api.py does NOT import from shared_fixtures; e2e and benchmarks conftest files are the actual importers | ✅ DONE |
| A2 | **Change E2E setup from @playwright/test to pytest-playwright** | `architecture/testing/test-suite.md` lines 87-91 | Project uses pytest-playwright, not @playwright/test | ✅ DONE |
| A3 | **Add missing fixtures to documentation table** | `tests/AGENTS.override.md` | Missing: `sample_post`, `sample_tag`, `sample_subscriber` (conftest.py), `clean_analytics_cache` (shared_fixtures.py), `clean_db` (benchmarks/conftest.py), `api_client` (test_api.py) | ✅ DONE |
| A4 | **Update test file list with actual test files** | `tests/AGENTS.override.md` | Missing: test_2fa.py, test_search.py, test_webhooks.py, test_tasks.py, test_scheduler.py, test_newsletter.py, test_comments_admin.py | ⏳ PENDING |
| A5 | **Remove specific test count** | `tests/AGENTS.override.md` | "524 tests pass" claim is outdated (now 36 test files) | ✅ DONE |
| A6 | **Simplify test file list pattern** | `tests/AGENTS.override.md` | Show directory structure pattern rather than enumerating all test files | ✅ DONE |

**Files to modify:** `tests/AGENTS.override.md`, `architecture/testing/test-suite.md`

---

## Wave B: Services Documentation Fixes (High Priority)

| # | Action Item | File | Details |
|---|-------------|------|---------|
| B1 | **Remove line numbers from tag_cache.md invalidation calls** | `architecture/services/tag_cache.md` | Line numbers are fragile; replace with functional descriptions |
| B2 | **Fix search.md documentation source confusion** | `architecture/services/search.md` | Documents SearchProvider abstraction but cites `app/search.py` line numbers instead of `app/services/search/sqlite.py` |
| B3 | **Add reset_fts_available() to search.md** | `architecture/services/search.md` | Function at `app/search.py:36` missing from docs |
| B4 | **Update backup.md line numbers** | `architecture/services/backup.md` | `run_daily_backup()` at line 145, not 48 |
| B5 | **Update slug.md line number** | `architecture/services/slug.md` | `generate_unique_slug()` at line 13, not 12 |

**Files to modify:** `architecture/services/tag_cache.md`, `architecture/services/search.md`, `architecture/services/backup.md`, `architecture/services/slug.md`

**Dependency:** B2 (search.md source) should be done after understanding SearchProvider abstraction in `app/services/search/__init__.py`

---

## Wave C: Services & Tasks Documentation (Medium Priority)

| # | Action Item | File | Details |
|---|-------------|------|---------|
| C1 | **Document app/search.py relationship** | `architecture/services/search.md` | Clarify that module-level functions in app/search.py are wrapped by SQLiteSearchProvider |
| C2 | **Document exception handling in search functions** | `architecture/services/search.md` | OperationalError, ProgrammingError, DatabaseError caught and return empty/false |
| C3 | **Document "Did You Mean" exact match behavior** | `architecture/services/search.md` | search.py:349-351 special logic for exact case match |
| C4 | **Add error handling table to celery-tasks.md** | `architecture/tasks/celery-tasks.md` | Document retry behavior for each task |
| C5 | **Document deliver_webhook_task non-retry behavior** | `architecture/tasks/celery-tasks.md` | Has max_retries=3 but NEVER calls self.retry() despite the config; exceptions caught don't trigger Celery retry |
| C6 | **Fix line numbers in celery-tasks.md** | `architecture/tasks/celery-tasks.md` | db.session.remove() lines: send_newsletter_task ~181 (not 178), deliver_webhook_task ~260 (not 258) |
| C7 | **Document non-retry for generate_image_variants and run_backup_task** | `architecture/tasks/celery-tasks.md` | Both return False on failure without retry |

**Files to modify:** `architecture/services/search.md`, `architecture/tasks/celery-tasks.md`

---

## Wave D: Routes Documentation Fixes (Medium/Low Priority)

| # | Action Item | File | Details |
|---|-------------|------|---------|
| D1 | **Fix public comments rate limit** | `architecture/routes/api-routes.md` line 139 | Documentation claims 20/min, actual is 10/min (`app/routes/public/comments.py:15`) |
| D2 | **Fix sitemap cache claim** | `architecture/routes/public-routes.md` line 99 | Claims "Cache: 5 minutes" but `app/routes/public/meta.py` has no explicit cache decorator |
| D3 | **Add pages field to API response docs** | `architecture/routes/api-routes.md` lines 36-44 | Response includes `pages` field not documented |
| D4 | **Document authors field in JSON Feed** | `architecture/routes/rss-feeds.md` | rss.py:272 includes `"authors": [{"name": AUTHOR_NAME or "admin"}]` |
| D5 | **Remove duplicate comment section** | `architecture/routes/public-routes.md` lines 118-127 | Comment routes described twice |
| D6 | **Verify sitemap cache implementation** | `app/routes/public/meta.py` | If 5-minute caching intended, add `@flask_cache.cached(timeout=300)` to `sitemap_xml()` |
| D7 | **Document series_posts endpoint** | `architecture/routes/api-routes.md` | Optional enhancement - document endpoint |

**Files to modify:** `architecture/routes/api-routes.md`, `architecture/routes/public-routes.md`, `architecture/routes/rss-feeds.md`, `app/routes/public/meta.py` (if D6)

---

## Wave E: Frontend Documentation Fixes (High/Medium Priority)

| # | Action Item | File | Details | Status |
|---|-------------|------|---------|--------|
| E1 | **Update templates.md directory structure** | `architecture/frontend/templates.md` | `admin/posts.html` → `admin/editor.html`; `admin/newsletter.html` does not exist | ⏳ PENDING |
| E2 | **Fix templates.md context processors** | `architecture/frontend/templates.md` | `site_name` → `site_title`; `site_tagline` → `site_description` | ⏳ PENDING |
| E3 | **Update app/templates/AGENTS.override.md structure** | `app/templates/AGENTS.override.md` | Lists non-existent files; missing actual templates like `admin/backup_codes.html`, `admin/2fa_setup.html` | ✅ DONE |
| E4 | **Add critical.css to static-assets.md** | `architecture/frontend/static-assets.md` | `critical.css` exists at `app/static/css/critical.css` and is used in `base.html:22` | ⏳ PENDING |
| E5 | **Add critical.css to AGENTS.override.md** | `app/static/AGENTS.override.md` | CSS section doesn't include `critical.css` | ✅ DONE |
| E6 | **Update static-assets.md module list** | `architecture/frontend/static-assets.md` | Missing `upload.js` and `image-preview.js` modules | ⏳ PENDING |
| E7 | **Clarify route-based code splitting** | `architecture/frontend/static-assets.md` | Admin routes include utils, modal, nav-dropdown, filter-select, toast, shortcuts, bulk | ⏳ PENDING |
| E8 | **Fix CSS media="print" onload pattern** | `app/templates/base.html:23-27` | `media="print"` may cause deprioritization in preload scanners; recommend `media="screen"` with preload | ⏳ PENDING |
| E9 | **Document image URL handling** | `architecture/frontend/templates.md` | `post_image_url` filter description incomplete - doesn't mention `storage.exists()` check or fallback behavior | ⏳ PENDING |
| E10 | **Document lazy loading strategy** | `architecture/frontend/static-assets.md` | Document `lazy-load.js` fallback behavior | ⏳ PENDING |

**Files to modify:** `architecture/frontend/templates.md`, `app/templates/AGENTS.override.md`, `architecture/frontend/static-assets.md`, `app/static/AGENTS.override.md`, `app/templates/base.html`

---

## Wave F: Infrastructure & Deployment Documentation (Medium/Low Priority)

| # | Action Item | File | Details |
|---|-------------|------|---------|
| F1 | **Update queue routing line numbers** | `architecture/infrastructure/webhooks.md` | Line numbers off by 1-3 |
| F2 | **Clarify health check email status** | `architecture/infrastructure/overview.md` | Email check NOT separate - SMTP only used for scheduler status |
| F3 | **Document WEBHOOK_TIMEOUT configuration** | `architecture/infrastructure/webhooks.md` | Configuration not currently documented |
| F4 | **Add search provider configuration details** | `architecture/infrastructure/search.md` | SEARCH_PROVIDER config not fully documented |
| F5 | **Add variant cleanup to S3 flow documentation** | `architecture/infrastructure/storage.md` | Variant cleanup on re-upload uses prefix, not explicit deletion |
| F6 | **Add ADMIN_USERNAME, FLASK_ENV to docker.md** | `architecture/deployment/docker.md` | Missing documented environment variables |
| F7 | **Document Celery concurrency setting** | `architecture/deployment/docker.md` | concurrency=1 not documented |
| F8 | **Clarify backup encryption key requirements** | `architecture/deployment/docker.md:128-133`, `architecture/deployment/security.md:57-62` | 12 chars vs 64 hex confusion |
| F9 | **Document PYTHONPATH for backup service** | `docker-compose.yml` or `architecture/deployment/docker.md` | PYTHONPATH=/home/blog for backup service |

**Files to modify:** `architecture/infrastructure/webhooks.md`, `architecture/infrastructure/overview.md`, `architecture/infrastructure/search.md`, `architecture/infrastructure/storage.md`, `architecture/deployment/docker.md`, `architecture/deployment/security.md`, `docker-compose.yml`

---

## Implementation Order

### Phase 1: High Priority (Waves A, B)
1. Wave A - Testing documentation fixes
2. Wave B - Services documentation fixes (High priority)

### Phase 2: Medium Priority (Waves C, D, E)
3. Wave C - Services & Tasks documentation
4. Wave D - Routes documentation fixes
5. Wave E - Frontend documentation fixes

### Phase 3: Lower Priority (Wave F)
6. Wave F - Infrastructure & Deployment documentation

---

## Deferred Items

**B2 (Per-Webhook Retry) from previous plan** - Intentionally deferred:
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
- **Search Provider**: Understand `app/services/search/__init__.py` before updating search.md
- **Celery Tasks**: Verify task behavior in `app/tasks.py` before documenting error handling
- **Frontend Templates**: Check `app/templates/` directory for actual template files
- **Routes**: Cross-reference route handlers in `app/routes/` with documentation

---

*Last updated: May 22, 2026*