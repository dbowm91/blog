# Implementation Plan - Consolidated from Architecture Reviews

**Date:** May 2026
**Status:** Consolidated from all architecture review files

---

## Overview

This plan consolidates action items from architecture reviews of:
- `routes_review.md` - API routes, public routes, admin routes
- `testing_review.md` - Test infrastructure and fixtures
- `core_review.md` - App factory, models, configuration
- `services_review.md` - Backup, slug, serialization, tag services
- `frontend_review.md` - Templates, static assets, filters, context processors
- `infrastructure_review.md` - Email, search, storage, webhooks
- `tasks_review.md` - Celery tasks and APScheduler jobs
- `deployment_review.md` - Docker, nginx, CI/CD, security

**Note:** Several critical bugs mentioned in reviews were already fixed prior to this consolidation (per AGENTS.md May 2026 update): S3 image variant upload, RSS/JSON feed endpoints, webhook triggering, Celery PYTHONPATH, nginx user directive, critical.css creation, page view buffer test protection.

---

## Verified Already Completed

The following items from the architecture reviews have been verified as already implemented/fixed:

| Item | Source | Verification |
|------|--------|---------------|
| critical.css | frontend_review | EXISTS at `app/static/css/critical.css` |
| E2E conftest buffer | testing_review | ALREADY HAS buffer protection |
| Benchmarks conftest buffer | testing_review | ALREADY HAS buffer protection |
| test_api.py buffer | testing_review | ALREADY HAS its own buffer protection |
| Webhook triggering | infrastructure_review | IMPLEMENTED in posts.py:294-300 and subscribe.py:147-153 |
| S3 upload bug | tasks_review | ALREADY FIXED |
| Celery PYTHONPATH | deployment_review | ALREADY SET to `/home/blog` |
| nginx user directive | deployment_review | ALREADY CORRECT (`user nginx;`) |
| Backup encryption | deployment_review | ALREADY AES-256-GCM (not GPG) |
| RSS/JSON feeds | routes_review | ALREADY IMPLEMENTED |
| APScheduler schedules | tasks_review | ALREADY CORRECT (5 min, 02:00) |

---

## PHASE 1: Test Infrastructure Improvements

### 1.1 Coverage Enforcement

| Item | File | Action |
|------|------|--------|
| Add fail_under | `pytest.ini` | Add `fail_under = 80` for coverage enforcement |

### 1.2 Test API Fixture Review

| Item | Priority | File | Action |
|------|----------|------|--------|
| Consider using shared fixture | Medium | `tests/test_api.py` | Has its own app fixture; consider refactoring to use shared `conftest.py` fixture for consistency |

---

## PHASE 2: Service Layer Improvements

### 2.1 Tag Service Updates

| Item | Priority | File | Action |
|------|----------|------|--------|
| Add `update_tag()` function | Low | `app/services/tag.py` | Implement update_tag(tag_id, name) function |
| Add error handling to `delete_tag_if_unused()` | Low | `app/services/tag.py` | Add session state validation before commit |
| Document slug collision limit | Low | `app/services/tag.py` | Document that slug counter hardcoded to 100 tries then falls back to UUID |

### 2.2 Backup Service Improvements

| Item | Priority | File | Action |
|------|----------|------|--------|
| Document `run_daily_backup()` | Medium | `app/services/backup.py` | Add docstring; note it uses `backup_*.db` pattern (not `blog_*.db`) and lacks compression/encryption |
| Document `decrypt_backup_file()` | Medium | `app/services/backup.py` | Add docstring for the decryption function |
| Fix inconsistent backup naming | Medium | `app/services/backup.py` | Clarify two backup paths: `create_backup()` uses `blog_*.db`, `run_daily_backup()` uses `backup_*.db` |
| Add params to `run_backup_task` | Low | `app/tasks.py` | Add compression/encryption support to Celery backup task |

### 2.3 Serialization Service

| Item | Priority | File | Action |
|------|----------|------|--------|
| Fix import documentation | High | `architecture/services/serialization.md` | Remove claim that serialization service handles import (currently only export exists; import is in `app/cli.py`) |
| Move import to service | High | `app/cli.py`, `app/services/serialization.py` | Consider moving import functionality from CLI to serialization service (future enhancement) |

---

## PHASE 3: APScheduler Documentation Fixes

### 3.1 Schedule Corrections

| Item | File | Current (Wrong) | Actual (Correct) |
|------|------|-----------------|-------------------|
| `cleanup_expired_subscribers` | `architecture/tasks/scheduler.md:12,22` | Hourly | Every 5 minutes (`*/5`) |
| `run_daily_backup` | `architecture/tasks/scheduler.md:12,34` | Daily at midnight | Daily at 02:00 |
| APScheduler cleanup schedule | `app/scheduler.py:281` | N/A | Runs every 5 minutes |
| APScheduler backup schedule | `app/scheduler.py:295` | N/A | Runs at 02:00 |

### 3.2 Scheduler Documentation

| Item | Priority | File | Action |
|------|----------|------|--------|
| Document two backup implementations | Medium | `architecture/tasks/scheduler.md` | Clarify scheduler uses inline backup logic, Celery task uses `create_backup()` service function |
| Add queue routing docs | Medium | `app/celery_app.py` | Document queue names: images, newsletter, webhooks, email, backup |

---

## PHASE 4: Frontend Documentation Updates

### 4.1 Template Filters (Already Correct)

The architecture doc `architecture/frontend/templates.md` already documents the correct filters:
- `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`

**No action needed.**

### 4.2 Context Processors

| Item | Priority | File | Action |
|------|----------|------|--------|
| Add `inject_show_footer_posts()` | Low | `architecture/frontend/templates.md` | Missing from docs - injects `show_footer_posts` boolean at `context_processors.py:194-199` |

### 4.3 AGENTS.override.md Filter Fix

| Item | File | Action |
|------|------|--------|
| Verify filter docs | `app/templates/AGENTS.override.md` | Ensure only actual filters are documented (`truncate` is Jinja2 built-in, `custom_css` is context variable - neither should be listed as custom filters) |

### 4.4 CSS Directory Structure

| Item | File | Action |
|------|------|--------|
| Verify claim | `architecture/frontend/static-assets.md:14` | Verify CSS files are directly in `app/static/css/` (not `css/styles/`) |

### 4.5 Vite Code Splitting

| Item | Priority | File | Action |
|------|----------|------|--------|
| Document route-based code splitting | Medium | `architecture/frontend/static-assets.md` | Add documentation for Vite route-based code splitting (deferred - frontend scope) |

---

## PHASE 5: Infrastructure Documentation Updates

### 5.1 Email Configuration (Already Correct)

The email retry count of 5 is correct in code. Verify documentation reflects this.

### 5.2 Search Documentation

| Item | Priority | File | Action |
|------|----------|------|--------|
| Document `rebuild_fts()` | Low | `architecture/infrastructure/search.md` | Add `rebuild_fts()` at `app/search.py:102-109` to documentation |
| Document SQLite batching | Medium | `architecture/infrastructure/search.md` | Document `_SQLITE_MAX_VARS = 500` batching in `get_search_snippets()` |

### 5.3 Queue Names Documentation

| Item | Priority | File | Action |
|------|----------|------|--------|
| Document Celery queues | Medium | `architecture/infrastructure/webhooks.md` | Document queue names: images, newsletter, webhooks, email, backup |

---

## PHASE 6: Core Model Documentation

### 6.1 User Model

| Item | File | Action |
|------|------|--------|
| Update `__repr__` docs | `architecture/core/models.md:98-99` | Document that `__repr__` returns `<User id={self.id}>` not username (for PII/security reasons) |

### 6.2 Relationship Diagram

| Item | Priority | File | Action |
|------|----------|------|--------|
| Clarify User relationships | `architecture/core/models.md:26-53` | Either remove reverse lookup relationships (`Posts (1:N)`, `AdminAuditLog (1:N)`) from User section OR add explicit note they are on target models |

### 6.3 SiteSettings

| Item | Priority | File | Action |
|------|----------|------|--------|
| Add logo_text field | `architecture/core/models.md` | Document `logo_text` field in SiteSettings |

---

## PHASE 7: Deployment Documentation Updates

### 7.1 Backup Encryption (Already Correct)

Code already uses AES-256-GCM. Verify architecture documentation reflects this (not GPG).

### 7.2 Security Header Alignment

| Item | Priority | File | Action |
|------|----------|------|--------|
| Verify header consistency | `app/__init__.py:344`, `nginx/conf.d/blog.conf:25` | Flask sets `DENY`, nginx sets `SAMEORIGIN` - choose one consistently or document why different |
| Add COOP header to nginx | Medium | `nginx/conf.d/blog.conf` | If COOP is set in Flask app but not nginx, align |

### 7.3 Redis Documentation

| Item | Priority | File | Action |
|------|----------|------|--------|
| Document redis dependency | Low | `architecture/deployment/docker.md` | Note production profile requires redis |

---

## PHASE 8: Routes Documentation Updates

Routes (RSS/JSON feeds, webhook triggering) are already implemented. This phase covers documentation corrections.

### 8.1 Post Editor Routes

| Item | File | Documented (Wrong) | Actual (Correct) |
|------|------|---------------------|-------------------|
| New post route | `architecture/routes/` | `/admin/posts/new` | `/admin/new` |
| Edit post route | `architecture/routes/` | `/admin/posts/<id>/edit` | `/admin/edit/<id>` |

### 8.2 Tag Delete Route

| Item | File | Documented (Wrong) | Actual (Correct) |
|------|------|---------------------|-------------------|
| Tag delete method | `architecture/routes/` | `DELETE /admin/tags/<id>` | `POST /admin/tags/delete/<id>` |

### 8.3 User Management Routes

| Item | File | Action |
|------|------|--------|
| REST-style vs action-based | `architecture/routes/` | Update documentation to reflect action-based routes: `/admin/users/create`, `/admin/users/delete/<id>`, `/admin/users/<id>/promote`, etc. (NO `PUT` route exists) |

### 8.4 Comment Route Path

| Item | File | Documented (Wrong) | Actual (Correct) |
|------|------|---------------------|-------------------|
| Comment submission | `architecture/routes/` | `POST /comment/<int:post_id>` | `POST /post/<slug>/comment` |

### 8.5 Subscribe Route

| Item | File | Action |
|------|------|--------|
| GET route missing | `architecture/routes/` | Document that `GET /subscribe` route exists |

### 8.6 Additional Routes to Document

| Item | Priority | File | Action |
|------|----------|------|--------|
| Backup download/delete/verify routes | Low | `architecture/routes/` | Add: `/admin/backup/download/<filename>`, `/admin/backup/delete/<filename>`, `/admin/backup/verify/<filename>`, `/admin/backup/verify-all` |
| Static page route | Low | `architecture/routes/` | Document `/page/<slug>` route |

### 8.7 Stats API Documentation

| Item | Priority | File | Action |
|------|----------|------|--------|
| Fix API response fields | Medium | `architecture/routes/` | API returns `total_views`, `total_shares`, etc. not `total_page_views` |

---

## PHASE 9: Testing Documentation Updates

### 9.1 Test Directory Structure

| Item | File | Documented (Wrong) | Actual (Correct) |
|------|------|---------------------|-------------------|
| Unit/integration dirs | `architecture/testing/test-suite.md` | `tests/unit/` and `tests/integration/` | Flat structure with all tests in `tests/` root; separate `benchmarks/` and `e2e/` subdirectories |

### 9.2 Fixture Names

| Item | File | Documented (Wrong) | Actual (Correct) |
|------|------|---------------------|-------------------|
| authenticated_admin | `architecture/testing/test-suite.md` | `authenticated_admin` fixture | Actual fixtures are `admin_user` and `authenticated_client` |

### 9.3 Coverage Configuration

| Item | File | Action |
|------|------|--------|
| Add fail_under | `pytest.ini` | Add `fail_under = 80` for coverage enforcement (see Phase 1.1) |

### 9.4 Benchmarks Directory

| Item | File | Action |
|------|------|--------|
| Document benchmarks directory | `architecture/testing/test-suite.md` | Add `tests/benchmarks/` to documentation |

---

## Implementation Waves

Items are grouped by potential parallelization. Already-verified items are marked as complete.

### Wave A: Documentation Corrections (Can run in parallel)

**Already Verified Complete:**
- [x] Frontend filters documentation (already correct in architecture/frontend/templates.md)
- [x] APScheduler schedules (already correct: 5 min, 02:00)
- [x] Email retry count (already correct: 5)

**Remaining Work:**
- [ ] Phase 4.2: Add `inject_show_footer_posts()` to context processor docs
- [ ] Phase 4.3: Verify AGENTS.override.md filter documentation
- [ ] Phase 5.2: Document `rebuild_fts()` and SQLite batching in search docs
- [ ] Phase 5.3: Document Celery queue names
- [ ] Phase 6.1-6.3: Update core model docs (User repr, relationships, logo_text)
- [ ] Phase 7.2: Verify/align security headers between Flask and nginx
- [ ] Phase 7.3: Document redis dependency
- [ ] Phase 8: Update routes documentation (all route path corrections)
- [ ] Phase 9: Update testing docs (directory structure, fixture names)

### Wave B: Code Improvements (Can run in parallel)

- [ ] Phase 2.1: Add `update_tag()` function to tag service (optional - low priority)
- [ ] Phase 2.1: Add error handling to `delete_tag_if_unused()` (optional - low priority)
- [ ] Phase 2.2: Document `run_daily_backup()` and clarify backup naming conventions
- [ ] Phase 2.3: Consider moving import functionality to serialization service (deferred - low priority)
- [ ] Phase 3: Add queue routing documentation to celery_app.py

### Wave C: Configuration Improvements

- [ ] Phase 1.1: Add `fail_under = 80` to pytest.ini
- [ ] Phase 1.2: Consider refactoring test_api.py to use shared conftest fixture (optional)

---

## Verification Checklist

After implementation, verify:
- [ ] pytest.ini has `fail_under = 80`
- [ ] Frontend context processors all documented (including `inject_show_footer_posts()`)
- [ ] APScheduler schedules in docs match code (5 min cleanup, 02:00 backup)
- [ ] All routes documentation matches actual routes
- [ ] Backup encryption documented as AES-256-GCM (not GPG)
- [ ] Test directory structure accurate in docs
- [ ] User model `__repr__` documented correctly
- [ ] Relationship diagram clarified

---

## Deferred Items

The following items were deferred due to scope (per AGENTS.md):

| Item | Reason Deferred |
|------|-----------------|
| TOTP encryption (2FA encryption of secrets) | Requires encryption helpers, model changes, UI |
| 2FA backup codes | Requires UI + model changes |
| Admin rate limiting | Requires testing 35+ routes |
| PostgreSQL FTS abstraction | Significant architecture change |
| Vite code splitting | Frontend scope |
| AVIF support | Frontend scope |
| Brotli compression | Nginx config |
| Move import to serialization service | CLI currently handles it; low priority |
| Add `update_tag()` function | Tag service works without it; low priority |
| Add error handling to `delete_tag_if_unused()` | Works without it; low priority |

---

## Dependencies

Key cross-cutting dependencies identified:

1. **Webhook event triggering** (infrastructure_review) - depends on `app/webhooks.py` - ALREADY IMPLEMENTED
2. **S3 image variant upload** (tasks_review) - depends on `app/storage.py` - ALREADY FIXED
3. **RSS/JSON feeds** (routes_review) - ALREADY IMPLEMENTED
4. **Page view buffer** (testing_review) - all test fixtures need protection - SEE PHASE 1
5. **Celery PYTHONPATH** (deployment_review) - ALREADY CORRECT
6. **nginx user directive** (deployment_review) - ALREADY CORRECT

---

## Notes for Future Agents

When implementing items in this plan:

1. **Test fixtures** (`tests/conftest.py`) - The `ensure_buffer_disabled` autouse fixture handles page view buffer shutdown. Use `shutdown_page_view_buffer()` in any custom test fixtures.

2. **Backup paths** - There are two separate backup implementations:
   - `app/services/backup.py:create_backup()` - Used by Celery task, uses `blog_*.db` pattern, supports encryption/compression
   - `app/scheduler.py:run_daily_backup()` - Used by APScheduler, uses `backup_*.db` pattern, no encryption/compression

3. **Slug collision** - The slug service hardcodes 100 tries before falling back to UUID suffix.

4. **User model __repr__** - Returns `<User id={self.id}>` for PII/security reasons, not username.

5. **Context processors** - Actual names: `inject_config()`, `inject_theme()`, `inject_footer_data()`, `inject_csrf()` (not `site_settings`, `tag_cache`, `footer_data`)

6. **Filters** - Actual filters: `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset` (not `format_date`, `markdown`, `slugify`)
