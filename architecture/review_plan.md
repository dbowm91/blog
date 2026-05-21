# Architecture Review Plan

**Created:** May 2026
**Status:** ✅ COMPLETED - Wave L (All 8 modules reviewed and issues fixed)

## Summary

All 8 architecture modules have been reviewed against actual code implementation. Multiple discrepancies, bugs, and documentation issues were identified and fixed.

| Module | Issues Found | Priority | Status |
|--------|-------------|----------|--------|
| Core | Webhook.secret plain text, Post.user_id false doc, missing indexes | High | ✅ Fixed |
| Services | TAG_CACHE_TTL wrong default (60 vs 300), backup naming docs, slug signature | Medium | ✅ Fixed |
| Routes | Preview route security (HMAC + session), API endpoints | Medium | ✅ Fixed |
| Tasks | Scheduler SMTP disable logic (disabled all jobs, not just newsletter) | High | ✅ Fixed |
| Infrastructure | Missing logger in webhooks.py | Critical | ✅ Fixed |
| Frontend | mobile-menu.jsx syntax error, srcset undefined in search.html | Critical | ✅ Fixed |
| Deployment | celery concurrency missing, pip-audit silenced, webhook encryption path | Medium | ✅ Fixed |
| Testing | clean_analytics_cache import inconsistency (low impact - different cache layers) | Low | ✅ Verified |

**Total: 1 critical bug fixed (webhooks missing logger, mobile-menu syntax), 2 high priority bugs fixed, 5 medium/low issues fixed**

---

## Issues Fixed

### Critical Bugs Fixed
1. **webhooks.py missing logger** - `app/webhooks.py:111` would have raised `NameError` at runtime
2. **mobile-menu.jsx syntax error** - Extra `});` caused parse failure in `app/static/js/shared/mobile-menu.jsx:42`
3. **srcset undefined in search.html** - Missing `{% set srcset = post|post_image_srcset %}` in `app/templates/search.html`
4. **scheduler.py SMTP disable logic** - Entire scheduler was disabled when SMTP not configured, not just newsletter job

### High Priority Fixes
1. **docker-compose.yml celery concurrency** - Added `--concurrency=1` to prevent memory issues
2. **.github/workflows/test.yml pip-audit** - Changed `pip-audit || true` to `pip-audit --fail-on=all`

### Documentation Fixes
1. **preview route security** - Corrected auth requirement (HMAC + session, not HMAC only)
2. **TAG_CACHE_TTL default** - Corrected 60 seconds (was 300)
3. **backup.md naming** - Corrected false docs about `backup_*.db` pattern
4. **slug.md signature** - Corrected parameter names to match implementation
5. **models.md Webhook.secret** - Corrected "Encrypted storage" to "Plain text storage"
6. **models.md Post.user_id** - Removed false reverse lookup claim, added clarification
7. **models.md indexes** - Added missing indexes (ix_pages_published_slug, ix_page_views_post_created, ix_share_events_post_created/platform)
8. **security.md webhook encryption** - Corrected path from `app/backup_encryption.py` to `app/webhook_encryption.py`

## Modules to Review

| Module | Documents | Review Agent | Output | Status |
|--------|-----------|--------------|--------|--------|
| **Core** | `core/app-factory.md`, `core/configuration.md`, `core/models.md` | core-reviewer | `plans/core_review.md` | ✅ COMPLETED |
| **Services** | `services/backup.md`, `services/serialization.md`, `services/tag.md`, `services/slug.md`, `services/tag_cache.md`, `services/overview.md` | services-reviewer | `plans/services_review.md` | ✅ COMPLETED |
| **Routes** | `routes/api-routes.md`, `routes/admin-routes.md`, `routes/public-routes.md`, `routes/rss-feeds.md` | routes-reviewer | `plans/routes_review.md` | ✅ COMPLETED |
| **Testing** | `testing/test-suite.md` | testing-reviewer | `plans/testing_review.md` | ✅ COMPLETED |
| **Tasks** | `tasks/celery-tasks.md`, `tasks/scheduler.md`, `tasks/overview.md` | tasks-reviewer | `plans/tasks_review.md` | ✅ COMPLETED |
| **Infrastructure** | `infrastructure/webhooks.md`, `infrastructure/search.md`, `infrastructure/email.md`, `infrastructure/storage.md`, `infrastructure/overview.md` | infrastructure-reviewer | `plans/infrastructure_review.md` | ✅ COMPLETED |
| **Frontend** | `frontend/static-assets.md`, `frontend/templates.md`, `frontend/overview.md` | frontend-reviewer | `plans/frontend_review.md` | ✅ COMPLETED |
| **Deployment** | `deployment/docker.md`, `deployment/security.md`, `deployment/cicd.md`, `deployment/overview.md` | deployment-reviewer | `plans/deployment_review.md` | ✅ COMPLETED |

## Subagent Instructions

Each subagent will:
1. Read all documents in their designated module under `architecture/`
2. Verify architectural claims against actual code implementation in `app/`
3. Cross-reference with related services, models, and routes
4. Identify bugs, inconsistencies, and improvement opportunities
5. Write a detailed improvement plan to `plans/<module>_review.md`

### 1. Core Review (`core-reviewer`)
**Documents:** `architecture/core/app-factory.md`, `architecture/core/configuration.md`, `architecture/core/models.md`
**Output:** `plans/core_review.md`

### 2. Services Review (`services-reviewer`)
**Documents:** `architecture/services/backup.md`, `architecture/services/serialization.md`, `architecture/services/tag.md`, `architecture/services/slug.md`, `architecture/services/tag_cache.md`, `architecture/services/overview.md`
**Output:** `plans/services_review.md`

### 3. Routes Review (`routes-reviewer`)
**Documents:** `architecture/routes/api-routes.md`, `architecture/routes/admin-routes.md`, `architecture/routes/public-routes.md`, `architecture/routes/rss-feeds.md`
**Output:** `plans/routes_review.md`

### 4. Testing Review (`testing-reviewer`)
**Documents:** `architecture/testing/test-suite.md`
**Output:** `plans/testing_review.md`

### 5. Tasks Review (`tasks-reviewer`)
**Documents:** `architecture/tasks/celery-tasks.md`, `architecture/tasks/scheduler.md`, `architecture/tasks/overview.md`
**Output:** `plans/tasks_review.md`

### 6. Infrastructure Review (`infrastructure-reviewer`)
**Documents:** `architecture/infrastructure/webhooks.md`, `architecture/infrastructure/search.md`, `architecture/infrastructure/email.md`, `architecture/infrastructure/storage.md`, `architecture/infrastructure/overview.md`
**Output:** `plans/infrastructure_review.md`

### 7. Frontend Review (`frontend-reviewer`)
**Documents:** `architecture/frontend/static-assets.md`, `architecture/frontend/templates.md`, `architecture/frontend/overview.md`
**Output:** `plans/frontend_review.md`

### 8. Deployment Review (`deployment-reviewer`)
**Documents:** `architecture/deployment/docker.md`, `architecture/deployment/security.md`, `architecture/deployment/cicd.md`, `architecture/deployment/overview.md`
**Output:** `plans/deployment_review.md`

## Review Process

1. **Launch subagents** in parallel (8 modules)
2. **Each subagent** reads all documents for their module
3. **Cross-reference** with actual code in `app/` directory
4. **Document findings** in `plans/<module>_review.md`
5. **Aggregate** findings into this document upon completion

## Sign-off

Once all subagent reviews are complete, update this document with final status and links to each module's improvement plan.