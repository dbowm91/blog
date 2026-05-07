# Implementation Plan - Documentation Consolidation

**Date:** May 2026
**Status:** COMPLETED - All waves implemented
**Consolidated from:** Architecture review files (core_review, deployment_review, frontend_review, infrastructure_review, routes_review, services_review, tasks_review, testing_review)

---

## Overview

This plan consolidates action items from architecture reviews. All items require documentation updates in `architecture/` directory files unless otherwise specified. Code fixes are specified with actual file paths.

---

## Verified Already Completed

| Item | Status | Notes |
|------|--------|-------|
| critical.css | EXISTS | `app/static/css/critical.css` |
| E2E conftest buffer | PROTECTED | `tests/conftest.py` has `ensure_buffer_disabled` autouse fixture |
| Webhook triggering | IMPLEMENTED | `app/routes/api/posts.py:294-300` and `app/routes/public/subscribe.py:147-153` |
| S3 upload bug | FIXED | `app/tasks.py` |
| Celery PYTHONPATH | CORRECT | Set to `/home/blog` |
| nginx user directive | CORRECT | `user nginx;` in nginx/conf.d/blog.conf |
| Backup encryption | CORRECT | AES-256-GCM (not GPG) |
| RSS/JSON feeds | IMPLEMENTED | `/atom`, `/rss`, `/json` endpoints |
| APScheduler schedules | CORRECT | `cleanup_expired_subscribers` every 5 min, `run_daily_backup` at 02:00 |
| Frontend filters | CORRECT | `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset` |
| Email retry count | CORRECT | 5 (in `app/config.py:114`) |
| Redis dependency | DOCUMENTED | In `architecture/deployment/docker.md:11` |
| Queue names | VERIFIED | `images`, `newsletter`, `webhooks`, `email`, `backup` (tasks.py lines 29,129,192,264,285,306) |
| CSS directory | CORRECT | Files directly in `app/static/css/` (not css/styles/) |

---

## Implementation Phases

### PHASE 1: Test Infrastructure

#### 1.1 Add Coverage Enforcement
| Item | File | Action | Status |
|------|------|--------|--------|
| Add `fail_under = 80` | `pytest.ini` | Add `fail_under = 80` to enforce minimum 80% coverage | COMPLETED |

#### 1.2 Test API Fixture Review (Optional)
| Item | Priority | File | Action | Status |
|------|----------|------|--------|--------|
| Consider shared fixture | Low | `tests/test_api.py` | Has own `app` fixture (lines 29-45) and `ensure_buffer_disabled` fixture (lines 12-20). Consider refactoring to use shared `conftest.py` fixture for consistency. | DEFERRED |

---

### PHASE 2: Service Layer Documentation

#### 2.1 Tag Service Updates
| Item | Priority | File | Action | Status |
|------|----------|------|--------|--------|
| Document slug collision limit | Low | `app/services/tag.py` | Add note that slug counter hardcoded to 100 tries before UUID fallback (actual implementation in `app/services/slug.py`) | COMPLETED |

#### 2.2 Backup Service Documentation
| Item | Priority | File | Action | Status |
|------|----------|------|--------|--------|
| Document `run_daily_backup()` | Medium | `app/services/backup.py:144-186` | Add docstring noting: uses `backup_*.db` pattern (not `blog_*.db`), lacks compression/encryption | COMPLETED |
| Clarify backup naming | Medium | `app/services/backup.py` | Two implementations exist: `create_backup()` uses `blog_*.db` (line 45), `run_daily_backup()` uses `backup_*.db` (line 161) | COMPLETED |

#### 2.3 Serialization Service
| Item | Priority | File | Action | Status |
|------|----------|------|--------|--------|
| Fix import documentation | High | `architecture/services/serialization.md` | Remove claim that serialization service handles import (only export exists; import is in `app/cli.py`) | COMPLETED |
| Move import to service | Low | `app/cli.py`, `app/services/serialization.py` | Consider moving import functionality from CLI to serialization service (deferred) | DEFERRED |

---

### PHASE 3: APScheduler Documentation

#### 3.1 Schedule Corrections
| Item | File | Wrong Docs | Correct | Status |
|------|------|------------|---------|--------|
| `cleanup_expired_subscribers` | `architecture/tasks/scheduler.md:12,22` | Hourly | Every 5 minutes (`*/5`) - actual at `app/scheduler.py:281` | COMPLETED |
| `run_daily_backup` | `architecture/tasks/scheduler.md:12,34` | Midnight | 02:00 - actual at `app/scheduler.py:295` | COMPLETED |

#### 3.2 Scheduler Documentation
| Item | Priority | File | Action | Status |
|------|----------|------|--------|--------|
| Document two backup implementations | Medium | `architecture/tasks/scheduler.md` | Clarify scheduler uses inline backup logic, Celery task uses `create_backup()` service function | COMPLETED |
| Add queue routing docs | Medium | `architecture/tasks/scheduler.md` | Document queue names used by tasks: `images` (tasks.py:29), `newsletter` (tasks.py:129), `webhooks` (tasks.py:192), `email` (tasks.py:264,285), `backup` (tasks.py:306) | COMPLETED |

---

### PHASE 4: Frontend Documentation

#### 4.1 Template Filters (Already Correct - No Action)
- `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`

#### 4.2 Context Processors
| Item | Priority | File | Action | Status |
|------|----------|------|--------|--------|
| Document `inject_show_footer_posts()` | Low | `architecture/frontend/templates.md` | Add missing function at `context_processors.py:193-199` - injects `show_footer_posts` boolean | COMPLETED |

#### 4.3 AGENTS.override.md Filter Fix
| Item | File | Action | Status |
|------|------|--------|--------|
| Verify filter docs | `app/templates/AGENTS.override.md` | Correct filters documented (lines 44-49). Verify `custom_css` noted as context variable (line 52). | VERIFIED CORRECT |

#### 4.4 CSS Directory Structure (Already Correct)
| Item | File | Action | Status |
|------|------|--------|--------|
| Verify claim | `architecture/frontend/static-assets.md:14` | Verified correct - CSS files in `app/static/css/` | VERIFIED CORRECT |

#### 4.5 Vite Code Splitting
| Item | Priority | File | Action | Status |
|------|----------|------|--------|--------|
| Document route-based code splitting | Medium | `architecture/frontend/static-assets.md` | Add documentation for Vite route-based code splitting (deferred - frontend scope) | DEFERRED |

---

### PHASE 5: Infrastructure Documentation

#### 5.1 Email Configuration (Already Correct - No Action)
- Email retry count of 5 is correct in code and documentation

#### 5.2 Search Documentation
| Item | Priority | File | Action | Status |
|------|----------|------|--------|--------|
| Document `rebuild_fts()` | Medium | `architecture/infrastructure/search.md` | Add `rebuild_fts()` at `app/search.py:102-109` (uses `INSERT INTO posts_fts(posts_fts) VALUES('rebuild')`) | COMPLETED |
| Document SQLite batching | Medium | `architecture/infrastructure/search.md` | Document `_SQLITE_MAX_VARS = 500` batching at `app/search.py:298,318` in `get_search_snippets()` | COMPLETED |

#### 5.3 Queue Names Documentation
| Item | Priority | File | Action | Status |
|------|----------|------|--------|--------|
| Document Celery queues | Medium | `architecture/infrastructure/webhooks.md` | Add queue names: `images`, `newsletter`, `webhooks`, `email`, `backup` | COMPLETED |

---

### PHASE 6: Core Model Documentation

#### 6.1 User Model
| Item | File | Action | Status |
|------|------|--------|--------|
| Update `__repr__` docs | `architecture/core/models.md:65-66` | Document `__repr__` returns `<User id={self.id}>` (not username - for PII/security) | COMPLETED |

#### 6.2 Relationship Diagram
| Item | Priority | File | Action | Status |
|------|----------|------|--------|--------|
| Clarify User relationships | `architecture/core/models.md:35-40` | User model only has `admin_sessions` relationship. `Posts` relationship is on Post model (line 142-143), `AdminAuditLog` is on AdminAuditLog model (line 419). Update docs to clarify reverse lookups are on target models. | COMPLETED |

#### 6.3 SiteSettings
| Item | Priority | File | Action | Status |
|------|----------|------|--------|--------|
| Add `logo_text` field | `architecture/core/models.md` | Document `logo_text` field at `app/models.py:297` | COMPLETED |

---

### PHASE 7: Deployment Documentation

#### 7.1 Backup Encryption (Already Correct - No Action)
- Code uses AES-256-GCM (not GPG)

#### 7.2 Security Header Alignment
| Item | Priority | File | Action | Status |
|------|----------|------|--------|--------|
| Align X-Frame-Options | High | `nginx/conf.d/blog.conf:25` | Flask sets `DENY` (`app/__init__.py:344`), nginx sets `SAMEORIGIN`. Aligned nginx to use `DENY`. | COMPLETED |
| Add COOP to nginx | Medium | `nginx/conf.d/blog.conf` | Flask sets `Cross-Origin-Opener-Policy: same-origin` (`app/__init__.py:347`). Added to nginx. | COMPLETED |

#### 7.3 Redis Documentation (Already Complete)
- Redis dependency already documented in `architecture/deployment/docker.md:11`

---

### PHASE 8: Routes Documentation Updates

Routes (RSS/JSON feeds, webhook triggering) are already implemented. This phase covers documentation corrections.

#### 8.1 Post Editor Routes
| Item | File | Wrong | Correct | Status |
|------|------|-------|---------|--------|
| New post route | `architecture/routes/` | `/admin/posts/new` | `/admin/new` (`app/routes/admin/posts/editor.py:137`) | COMPLETED |
| Edit post route | `architecture/routes/` | `/admin/posts/<id>/edit` | `/admin/edit/<id>` (`app/routes/admin/posts/editor.py:215`) | COMPLETED |

#### 8.2 Tag Delete Route
| Item | File | Wrong | Correct | Status |
|------|------|-------|---------|--------|
| Tag delete method | `architecture/routes/` | `DELETE /admin/tags/<id>` | `POST /admin/tags/delete/<id>` (`app/routes/admin/tags.py:87`) | COMPLETED |

#### 8.3 User Management Routes
| Item | File | Action | Status |
|------|------|--------|--------|
| REST-style vs action-based | `architecture/routes/` | Update documentation to reflect action-based routes: `/admin/users/create`, `/admin/users/delete/<id>`, `/admin/users/<id>/promote` (NO `PUT` route exists) | COMPLETED |

#### 8.4 Comment Route Path
| Item | File | Wrong | Correct | Status |
|------|------|-------|---------|--------|
| Comment submission | `architecture/routes/` | `POST /comment/<int:post_id>` | `POST /post/<slug>/comment` (`app/routes/public/comments.py:12`) | COMPLETED |

#### 8.5 Subscribe Route
| Item | File | Action | Status |
|------|------|--------|--------|
| GET route missing | `architecture/routes/` | Document that only `POST /subscribe` exists (`app/routes/public/subscribe.py:55`), no GET handler | COMPLETED |

#### 8.6 Additional Routes to Document
| Item | Priority | File | Action | Status |
|------|----------|------|--------|--------|
| Backup routes | Low | `architecture/routes/` | Add documented routes: `/admin/backup/download/<filename>` (GET), `/admin/backup/delete/<filename>` (POST), `/admin/backup/verify/<filename>` (GET), `/admin/backup/verify-all` (GET) - from `app/routes/admin/backup.py` | COMPLETED |
| Static page route | Low | `architecture/routes/` | Document `/page/<slug>` route (`app/routes/public/browse.py:208`) | COMPLETED |

#### 8.7 Stats API Documentation
| Item | Priority | File | Action | Status |
|------|----------|------|--------|--------|
| Fix API response fields | Medium | `architecture/routes/` | API returns `total_views`, `total_shares`, etc. (NOT `total_page_views`) at `app/routes/api/stats.py:54-62` | COMPLETED |

---

### PHASE 9: Testing Documentation Updates

#### 9.1 Test Directory Structure
| Item | File | Wrong | Correct | Status |
|------|------|-------|---------|--------|
| Unit/integration dirs | `architecture/testing/test-suite.md` | `tests/unit/` and `tests/integration/` | Flat structure with all tests in `tests/` root; separate `benchmarks/` and `e2e/` subdirectories | COMPLETED |

#### 9.2 Fixture Names
| Item | File | Wrong | Correct | Status |
|------|------|-------|---------|--------|
| `authenticated_admin` | `architecture/testing/test-suite.md` | `authenticated_admin` | Actual fixtures: `admin_user` (`tests/conftest.py:88`), `authenticated_client` (`tests/conftest.py:103`) | COMPLETED |

#### 9.3 Coverage Configuration
| Item | File | Action | Status |
|------|------|--------|--------|
| Add fail_under | `pytest.ini` | Add `fail_under = 80` (see Phase 1.1) | COMPLETED |

#### 9.4 Benchmarks Directory
| Item | File | Action | Status |
|------|------|--------|--------|
| Document benchmarks dir | `architecture/testing/test-suite.md` | Add `tests/benchmarks/` (has conftest.py and test_benchmarks.py) | COMPLETED |

---

## Implementation Waves (Completed)

### Wave A: Documentation Corrections
**Status: COMPLETED**

All items completed via parallel subagents:
- [x] Phase 4.2: Add `inject_show_footer_posts()` to `architecture/frontend/templates.md`
- [x] Phase 6.1: Update User `__repr__` docs in `architecture/core/models.md`
- [x] Phase 6.2: Clarify User relationship diagram in `architecture/core/models.md`
- [x] Phase 6.3: Add `logo_text` field to SiteSettings docs
- [x] Phase 7.2: Security header alignment (X-Frame-Options, COOP)
- [x] Phase 8.1: Correct post editor routes in `architecture/routes/`
- [x] Phase 8.2: Correct tag delete route in `architecture/routes/`
- [x] Phase 8.3: Update user management routes in `architecture/routes/`
- [x] Phase 8.4: Correct comment route in `architecture/routes/`
- [x] Phase 8.5: Document GET /subscribe missing
- [x] Phase 8.6: Add backup and page routes to `architecture/routes/`
- [x] Phase 8.7: Fix stats API field names
- [x] Phase 9.1: Correct test directory structure in `architecture/testing/test-suite.md`
- [x] Phase 9.2: Correct fixture names in `architecture/testing/test-suite.md`
- [x] Phase 9.4: Add benchmarks directory to `architecture/testing/test-suite.md`

### Wave B: Code Improvements
**Status: COMPLETED**

All items completed:
- [x] Phase 2.1: Add slug collision note to `app/services/tag.py`
- [x] Phase 2.2: Add docstring to `run_daily_backup()` in `app/services/backup.py`
- [x] Phase 3.1: Update APScheduler schedules in `architecture/tasks/scheduler.md`
- [x] Phase 3.2: Document two backup implementations and queue routing
- [x] Phase 5.2: Document `rebuild_fts()` and SQLite batching in `architecture/infrastructure/search.md`
- [x] Phase 5.3: Document Celery queue names in `architecture/infrastructure/webhooks.md`
- [x] Phase 2.3: Fix serialization import docs in `architecture/services/serialization.md`

### Wave C: Configuration
**Status: COMPLETED**

- [x] Phase 1.1: Add `fail_under = 80` to `pytest.ini`

### Wave D: Optional/Low Priority
**Status: DEFERRED**

All items deferred due to scope:
- [ ] Phase 1.2: Refactor test_api.py to use shared conftest fixture (low priority)
- [ ] Phase 2.3: Move import to serialization service (deferred)
- [ ] Phase 4.5: Vite code splitting documentation (deferred - frontend scope)

---

## Deferred Items

These items were deferred due to scope:

| Item | Reason Deferred |
|------|-----------------|
| TOTP encryption (2FA) | Requires encryption helpers, model changes, UI |
| 2FA backup codes | Requires UI + model changes |
| Admin rate limiting | Requires testing 35+ routes |
| PostgreSQL FTS abstraction | Significant architecture change |
| Vite code splitting | Frontend scope |
| AVIF support | Frontend scope |
| Brotli compression | Nginx config |

---

## Verification Checklist

After implementation, verify:
- [x] `pytest.ini` has `fail_under = 80`
- [x] All context processors documented (including `inject_show_footer_posts()`)
- [x] APScheduler schedules in docs match code (5 min cleanup, 02:00 backup)
- [x] All routes documentation matches actual routes
- [x] Backup encryption documented as AES-256-GCM
- [x] Test directory structure accurate in docs
- [x] User model `__repr__` documented correctly
- [x] Relationship diagram clarified
- [x] Security headers aligned between Flask and nginx

---

## Dependencies

Key cross-cutting dependencies:

| Item | Status | Notes |
|------|--------|-------|
| Webhook event triggering | ALREADY IMPLEMENTED | `app/webhooks.py` |
| S3 image variant upload | ALREADY FIXED | `app/storage.py` |
| RSS/JSON feeds | ALREADY IMPLEMENTED | |
| Page view buffer | PROTECTED | `tests/conftest.py` has `ensure_buffer_disabled` |
| Celery PYTHONPATH | CORRECT | |
| nginx user directive | CORRECT | |

---

## Notes for Future Agents

### Test Fixtures
The `ensure_buffer_disabled` autouse fixture in `tests/conftest.py` (lines 185-193) handles page view buffer shutdown. Use `shutdown_page_view_buffer()` in any custom test fixtures.

### Backup Implementations
Two separate backup implementations:
- `app/services/backup.py:create_backup()` - Celery task, `blog_*.db`, encryption/compression
- `app/scheduler.py:run_daily_backup()` - APScheduler, `backup_*.db`, no encryption/compression

### Slug Generation
Slug collision limit hardcoded to 100 tries before UUID suffix fallback (`app/services/slug.py`).

### User Model `__repr__`
Returns `<User id={self.id}>` for PII/security reasons.

### Context Processor Names
`inject_csrf()`, `inject_config()`, `inject_theme()`, `inject_footer_data()`, `inject_show_footer_posts()` (not `site_settings`, `tag_cache`, etc.)

### Celery Queue Names
`images`, `newsletter`, `webhooks`, `email`, `backup`

### Actual Routes
- New post: `/admin/new` (not `/admin/posts/new`)
- Edit post: `/admin/edit/<id>` (not `/admin/posts/<id>/edit`)
- Tag delete: `POST /admin/tags/delete/<id>` (not `DELETE`)
- Comment submission: `POST /post/<slug>/comment` (not `/comment/<int:post_id>`)
- Subscribe: Only `POST /subscribe` exists (no GET)

### Security Headers
- Flask sets `X-Frame-Options: DENY` and `Cross-Origin-Opener-Policy: same-origin`
- nginx now aligned to use `DENY` and `Cross-Origin-Opener-Policy: same-origin`
