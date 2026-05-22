# Architecture Review Plan

## Overview

This plan outlines a comprehensive review of the architecture documentation. Each module will be reviewed by a subagent that will:
1. Verify claims in the documentation against the actual code
2. Identify any inconsistencies, outdated information, or missing details
3. Propose improvements and identify potential bugs or security issues
4. Write their findings to `plans/<module>_review.md`

## Modules to Review

| Module | Documents | Assigned Agent |
|--------|-----------|----------------|
| **core** | app-factory.md, models.md, configuration.md | explore |
| **deployment** | docker.md, security.md, cicd.md, overview.md | explore |
| **frontend** | static-assets.md, templates.md, overview.md | explore |
| **infrastructure** | storage.md, webhooks.md, search.md, email.md, overview.md | explore |
| **routes** | public-routes.md, api-routes.md, admin-routes.md, rss-feeds.md | explore |
| **services** | tag.md, tag_cache.md, search.md, backup.md, serialization.md, slug.md, overview.md | explore |
| **tasks** | celery-tasks.md, scheduler.md, overview.md | explore |
| **testing** | test-suite.md | explore |

## Review Instructions for Each Subagent

For each module, the subagent must:

1. **Read all documents** in the module's directory under `architecture/`
2. **Cross-reference with actual code** - Find the corresponding implementation files and verify:
   - Route paths match
   - Function signatures are correct
   - Configuration values are accurate
   - Timing/scheduling details are correct
   - Security measures are implemented as documented
3. **Check AGENTS.override.md** for any module-specific guidance
4. **Identify issues**:
   - Outdated documentation
   - Missing documentation for new features
   - Incorrect claims about behavior
   - Potential bugs or security vulnerabilities
   - Code improvements opportunities
5. **Write improvement plan** to `plans/<module>_review.md` with:
   - Summary of findings
   - List of verified claims
   - List of discrepancies/issues found
   - Recommended improvements
   - Potential bugs or security concerns

## Module Directories

- `architecture/core/` - Core application factory, models, configuration
- `architecture/deployment/` - Docker, security, CI/CD deployment docs
- `architecture/frontend/` - Static assets, templates
- `architecture/infrastructure/` - Storage, webhooks, search, email
- `architecture/routes/` - Public, API, admin routes, RSS feeds
- `architecture/services/` - Tag, backup, search, serialization, slug services
- `architecture/tasks/` - Celery tasks, scheduler
- `architecture/testing/` - Test suite documentation

## Execution Order

1. Launch subagents for all modules concurrently (max 4 at a time)
2. Wait for completion and launch remaining modules
3. Compile summary from all `plans/<module>_review.md` files

## Output Files

Each subagent will write their findings to:
- `plans/core_review.md`
- `plans/deployment_review.md`
- `plans/frontend_review.md`
- `plans/infrastructure_review.md`
- `plans/routes_review.md`
- `plans/services_review.md`
- `plans/tasks_review.md`
- `plans/testing_review.md`

## Wave O Completion (May 2026)

Implementation of architecture review findings from previous review cycles:

| Module | Fixes Applied |
|--------|---------------|
| **deployment** | docker.md: Added ADMIN_USERNAME and FLASK_ENV to env vars, documented Celery concurrency=1, clarified BACKUP_ENCRYPTION_KEY generation, added PYTHONPATH for backup service |
| **frontend** | static-assets.md: Added critical.css to CSS file list; templates.md: Added comments clarifying editor.html and page_editor.html |
| **infrastructure** | webhooks.md: Fixed queue routing line numbers; overview.md: Clarified email check via scheduler status; storage.md: Added _delete_existing_variants() to S3 variant flow |
| **routes** | api-routes.md: Fixed public comments rate limit (20/min->10/min), added 'pages' field to response; public-routes.md: Removed duplicate comment section, fixed sitemap cache claim; rss-feeds.md: Documented authors field in JSON Feed |
| **services** | tag_cache.md: Removed stale line numbers from invalidation calls; backup.md: Added line number for run_daily_backup() |
| **tasks** | celery-tasks.md: Fixed line numbers for db.session.remove(), added error handling table documenting retry behavior |
| **testing** | test-suite.md: Fixed E2E setup instructions (pytest-playwright), added api_client and clean_db fixtures |

**Status:** INCOMPLETE - Additional waves may be needed for further improvements.

## See Also
- `plans/` - Individual module review files with detailed findings
- `architecture/AGENTS.override.md` - Module-specific agent guidance