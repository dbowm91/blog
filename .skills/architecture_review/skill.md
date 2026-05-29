# Architecture Review Skill

## Description
Architecture documentation review and improvement workflow. Reviews architecture documents against actual source code and generates improvement plans.

## Triggers
architecture, review, documentation, verify, cross-reference

## Module Directories
- `architecture/core/` - app-factory.md, configuration.md, models.md
- `architecture/routes/` - public-routes.md, admin-routes.md, api-routes.md, rss-feeds.md
- `architecture/services/` - overview.md, backup.md, serialization.md, slug.md, tag.md, tag_cache.md
- `architecture/tasks/` - overview.md, scheduler.md, celery-tasks.md
- `architecture/infrastructure/` - overview.md, search.md, email.md, storage.md, webhooks.md
- `architecture/frontend/` - overview.md, static-assets.md, templates.md
- `architecture/deployment/` - overview.md, docker.md, cicd.md, security.md
- `architecture/testing/` - test-suite.md

## Status

Architecture review completed (May 29, 2026). All 3 phases done: 8 module reviews (Phase 1), overview cross-reference (Phase 2), stale pruning (Phase 3). Findings in `plans/`.

### Architecture Review Completion (May 29, 2026)
Full architecture review completed across 3 phases:
- **Phase 1**: 8 module reviews (Core, Routes, Services, Tasks, Infrastructure, Frontend, Deployment, Testing)
- **Phase 2**: Overview cross-reference review
- **Phase 3**: Stale item pruning (0 prune candidates, 8 docs need minor fixes, 26 fine as-is)

Key findings:
- **Core**: ApiToken model missing from docs, Comment model missing spam fields, 12+ config settings undocumented
- **Routes**: 18+ API endpoints undocumented (tags, pages, series), scoped token auth system missing, backup route paths wrong
- **Services**: Line number drift in search.md (-1 to -7), tag_cache.md drift, _SQLITE_MAX_VARS misrepresented
- **Tasks**: deliver_webhook_task retry behavior outdated (dispatches to deliver_single_webhook_task which does retry)
- **Infrastructure**: is_safe_url → is_safe_webhook_url, health check ?detailed=true, disk space 10% free
- **Frontend**: Template inheritance has 4 base templates (not 2), duplicate Atom feed link bug
- **Deployment**: CI workflow is ci.yml not test.yml, missing validate_openapi.py script, WORKDIR mismatch
- **Testing**: pytest.ini reference wrong (config in pyproject.toml), phantom fixtures (regular_user, post)

### Wave 1 Completion (May 28, 2026)
15 documentation files updated across 8 modules:
- **Core**: Fixed totp_secret_encrypted, backup code methods, webhook_secret_encrypted, delivery_status
- **Routes**: Removed false POST /api/auth, documented require_api_key decorator
- **Services**: Created tag_cache.md, documented encryption modules (3), slug service, decryption path, serialization import
- **Tasks**: Clarified scheduler vs Celery newsletter, FileLock docs, backup comparison table
- **Deployment**: Backup service working dir, nginx security headers (8 present, 2 missing), rate limiting zones, SSL gap, process model
- **Infrastructure**: Fixed search provider description (wraps app/search.py), SSRF protection docs, S3 storage backend
- **Testing**: Fixtures documentation, E2E config, command reference
- **Frontend**: AVIF filter (deprecated), CSS architecture, dark mode, Vite asset helper, lazy image progressive enhancement

### Wave O Fixes Applied
- **deployment**: Env vars (ADMIN_USERNAME, FLASK_ENV), Celery concurrency, BACKUP_ENCRYPTION_KEY clarification, PYTHONPATH
- **frontend**: critical.css added, editor.html/page_editor.html clarified
- **infrastructure**: Queue routing line numbers fixed, email check via scheduler, S3 variant cleanup
- **routes**: Rate limit (10/min), pages field, duplicate section removed, sitemap cache, authors field
- **services**: Stale line numbers removed, run_daily_backup() line number added
- **tasks**: Line numbers fixed, error handling table added
- **testing**: pytest-playwright instructions, api_client fixture added

### Plan Completion (May 22, 2026)
All 43 plan.md items completed across Waves A-F:
- Wave A (testing): clean_db fixture, test file list with line numbers
- Wave B (services): search.md source clarification, reset_fts_available(), backup.md line numbers
- Wave C (tasks): error handling table, deliver_webhook_task non-retry, line numbers fixed, generate_image_variants/run_backup_task non-retry documented
- Wave D (routes): comment rate limit 10/min, sitemap cache claim, API pages field, JSON feed authors field, duplicate comment section removed
- Wave E (frontend): route-based code splitting expanded, post_image_url filter documented, lazy-load.js fallback documented
- Wave F (infrastructure): queue routing line number fixed, WEBHOOK_TIMEOUT configurable, variant cleanup documented, FLASK_ENV added, BACKUP_ENCRYPTION_KEY generation fixed, PYTHONPATH documented

See `plans/plan.md` for full implementation summary.

### Critical Bugs Fixed
1. `app/webhooks.py:111` - Missing logger (NameError at runtime)
2. `app/static/js/shared/mobile-menu.jsx:42` - Extra `});` caused parse failure
3. `app/templates/search.html:31` - Missing srcset variable
4. `app/scheduler.py:269-271` - SMTP disable logic disabled all jobs, not just newsletter

### Verified Behavior
- All routes match documented paths
- All function signatures match documentation
- All configuration values verified
- All Celery queue names and line numbers correct
- All APScheduler schedules correct

### Architecture Review Notes
When reviewing documentation:
- Line numbers become stale quickly - prefer functional descriptions over specific line references
- Queue routing table line numbers updated to actual: images:28, newsletter:127, webhooks:184, email:263,284, backup:305
- Rate limit values should be verified against actual code (e.g., public comments is 10/min, not 20/min)
- Error handling table documents actual retry behavior for Celery tasks
- E2E tests use pytest-playwright, not @playwright/test