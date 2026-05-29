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

Architecture review and fixes completed (May 29, 2026). All findings from the 8-module review have been implemented in `plans/plan.md` (96 items across 5 waves).

### Plan Completion (May 29, 2026)
All 96 plan.md items completed across Waves 1-5:
- **Wave 1** (50 items): Critical documentation fixes — model counts, line numbers, route paths, event types, config docs, webhook architecture, API endpoints
- **Wave 2** (6 items): Code-level fixes — duplicate Atom feed, dead code cleanup, test teardown
- **Wave 3** (17 items): Documentation improvements — Vite integration, CLI commands, Celery config, scripts docs
- **Wave 4** (19 items): Project polish — project identity, security docs, Docker/CI, contribution hygiene
- **Wave 5** (6 items): Final verification — all checks pass

### Key Findings Fixed
- **Core**: ApiToken model documented, Comment spam fields added, 12+ config settings documented
- **Routes**: Pages/series/tags API endpoints documented, backup route paths fixed, admin route paths corrected
- **Services**: Line numbers corrected across search.md and tag_cache.md, encryption modules documented
- **Tasks**: deliver_single_webhook_task documented, retry behavior corrected, scheduler conditionality noted
- **Infrastructure**: is_safe_webhook_url documented, health check params fixed, webhook encryption documented
- **Frontend**: Template inheritance shows 4 base templates, duplicate Atom feed removed, static asset line numbers fixed
- **Deployment**: CI workflow corrected, Docker profiles fixed, Dependabot added, production checklist added
- **Testing**: pytest config fixed, Celery eager config documented, slow marker documented

### Architecture Review Notes
When reviewing documentation:
- Line numbers become stale quickly - prefer functional descriptions over specific line references
- Queue routing table line numbers: images:30, newsletter:129, webhooks:194, email:333,354, backup:375
- Rate limit values should be verified against actual code
- Error handling table documents actual retry behavior for Celery tasks
- E2E tests use pytest-playwright, not @playwright/test

## Second Wave Review (May 29, 2026)

All 10 reviews now complete. Key findings:

### HIGH Severity Bugs Found
1. **testing/test-suite.md:113** - FALSE claim: "playwright not in requirements" - playwright>=1.58.0 IS in requirements.txt:18
2. **testing/test-suite.md:190-196** - FALSE claim: "E2E conftest defines its own app fixture" - it does NOT, relies on import chain
3. **APScheduler FileLock** not enforced against scaling (docker-compose.yml:60)
4. **Backup encryption silently disabled** if BACKUP_ENCRYPTION_KEY set but cannot be loaded (backup.py:103-106)
5. **E2E test password mismatch** - conftest.py:100 "testpassword" vs e2e/conftest.py:44 "test-password"

### Documentation Gaps Found
- Vite build required for production (manifest.json) - not documented anywhere
- APScheduler multi-container detection/alerting mechanism missing
- Backup encryption key can come from config.toml (not just env var)
- Celery scaling warning (concurrency=1 is per-container, not total)
- Health check start_period (10s before container marked healthy)
- Python version mismatch: dev.sh requires 3.14, Dockerfile uses 3.12-slim

### Docs to Rewrite
- `architecture/testing/test-suite.md` - two confirmed false claims
- `architecture/overview.md` - missing Vite build req, APScheduler multi-container warning, Python version mismatch
- `architecture/infrastructure/webhooks.md` - stale line references, delivery_status bug undocumented
- `architecture/frontend/static-assets.md` - login template asset loading inconsistency, Prism CSS CDN bypass