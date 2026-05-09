# Architecture Review Plan

This document outlines the review plan for architecture documentation in this directory.

## Modules to Review

| Module | Documents | Review Subagent | Output Plan |
|--------|-----------|-----------------|-------------|
| [Core](core/) | app-factory.md, configuration.md, models.md | core_reviewer | plans/core_review.md |
| [Routes](routes/) | public-routes.md, admin-routes.md, api-routes.md, rss-feeds.md | routes_reviewer | plans/routes_review.md |
| [Services](services/) | overview.md, backup.md, serialization.md, slug.md, tag.md | services_reviewer | plans/services_review.md |
| [Tasks](tasks/) | overview.md, scheduler.md, celery-tasks.md | tasks_reviewer | plans/tasks_review.md |
| [Infrastructure](infrastructure/) | overview.md, search.md, email.md, storage.md, webhooks.md | infrastructure_reviewer | plans/infrastructure_review.md |
| [Frontend](frontend/) | overview.md, static-assets.md, templates.md | frontend_reviewer | plans/frontend_review.md |
| [Deployment](deployment/) | overview.md, docker.md, cicd.md, security.md | deployment_reviewer | plans/deployment_review.md |
| [Testing](testing/) | test-suite.md | testing_reviewer | plans/testing_review.md |

## Review Methodology

For each module, the subagent will:
1. Read all architecture documents in the module directory
2. Verify claims against actual code implementation
3. Identify discrepancies, outdated information, or missing documentation
4. Interrogate code for potential bugs, security issues, and improvements
5. Write an improvement plan to the designated output file in `plans/`

## Subagent Prompts

### core_reviewer
Review the Core module (`architecture/core/`):
- app-factory.md: Verify Flask app initialization, extensions, middleware
- configuration.md: Verify config loading priority and mechanisms
- models.md: Verify all models (User, Post, Tag, Comment, etc.) match documentation

Output: Write improvement plan to `plans/core_review.md`

### routes_reviewer
Review the Routes module (`architecture/routes/`):
- public-routes.md: Blog pages, search, comments, subscription endpoints
- admin-routes.md: Dashboard, post editor, settings, analytics
- api-routes.md: REST API endpoints for posts, subscribers, stats
- rss-feeds.md: RSS 2.0, Atom, JSON feed implementations

Output: Write improvement plan to `plans/routes_review.md`

### services_reviewer
Review the Services module (`architecture/services/`):
- backup.md: Database backup with compression/encryption
- serialization.md: JSON export/import
- slug.md: Unique slug generation
- tag.md: Tag CRUD and count management

Output: Write improvement plan to `plans/services_review.md`

### tasks_reviewer
Review the Tasks module (`architecture/tasks/`):
- celery-tasks.md: Async task queue workers
- scheduler.md: APScheduler in-process scheduled jobs

Output: Write improvement plan to `plans/tasks_review.md`

### infrastructure_reviewer
Review the Infrastructure module (`architecture/infrastructure/`):
- search.md: FTS5 full-text search implementation
- email.md: SMTP email delivery
- storage.md: Local/S3 storage abstraction
- webhooks.md: Webhook delivery with SSRF protection

Output: Write improvement plan to `plans/infrastructure_review.md`

### frontend_reviewer
Review the Frontend module (`architecture/frontend/`):
- static-assets.md: JS, CSS, uploads, Vite build
- templates.md: Jinja2 templates

Output: Write improvement plan to `plans/frontend_review.md`

### deployment_reviewer
Review the Deployment module (`architecture/deployment/`):
- docker.md: Container orchestration
- cicd.md: GitHub Actions pipelines
- security.md: Authentication, CSRF, sanitization

Output: Write improvement plan to `plans/deployment_review.md`

### testing_reviewer
Review the Testing module (`architecture/testing/`):
- test-suite.md: Unit, integration, e2e test infrastructure

Output: Write improvement plan to `plans/testing_review.md`

## Execution

Review tasks will be executed in parallel using subagents. Each subagent will:
1. Read all documents in their designated module directory
2. Cross-reference with actual source code
3. Document findings including:
   - Verified accurate claims
   - Inaccurate or outdated claims
   - Missing documentation
   - Potential bugs or security issues
   - Improvement recommendations
4. Write structured improvement plan to the plans directory

---

## Completion Status

**Status: ALL REVIEWS COMPLETED** - May 2026 review pass

| Module | Plan File | Status |
|--------|-----------|--------|
| Core | plans/core_review.md | COMPLETED |
| Routes | plans/routes_review.md | COMPLETED |
| Services | plans/services_review.md | COMPLETED |
| Tasks | plans/tasks_review.md | COMPLETED |
| Infrastructure | plans/infrastructure_review.md | COMPLETED |
| Frontend | plans/frontend_review.md | COMPLETED |
| Deployment | plans/deployment_review.md | COMPLETED |
| Testing | plans/testing_review.md | COMPLETED |

### Key Findings Summary (May 2026 Review Pass)

| Module | Accurate Claims | Inaccuracies | Missing Docs | Issues |
|--------|----------------|--------------|--------------|--------|
| Core | 25+ | 6 | 15+ | 4 |
| Routes | 12 | 9 | 21 | 4 |
| Services | 5 | 4 | 4 | 4 |
| Tasks | 14 | 4 | 4 | 3 |
| Infrastructure | 6 | 5 | 5 | 2 |
| Frontend | 5 | 3 | 6 | 3 |
| Deployment | 6 | 4 | 7 | 3 |
| Testing | 5 | 4 | 7 | 4 |
| **Total** | **78+** | **39** | **69+** | **27** |

### Critical Fixes Required

1. **User.totp_secret** - Documented as column but is encrypted property
2. **API publish endpoint** - Non-existent `/api/posts/<id>/publish` endpoint documented
3. **Backup encryption** - GPG documented but AES-256-GCM implemented
4. **Routes 9 incorrect routes** - Preview, logout, tag create, media delete, newsletter, settings, etc.
5. **Models missing** - AdminSession, Series, PostSeries, Webhook, WebhookEvent undocumented
6. **Config settings missing** - ~17 settings not documented
7. **Tests directory structure** - `tests/unit` and `tests/integration` don't exist

### Detailed Findings

Each module has a detailed improvement plan in `architecture/plans/`:
- `core_review.md` - totp_secret, SESSION_COOKIE_SECURE, SQLite pragmas, missing models
- `routes_review.md` - 9 incorrect routes, 21 missing documentation items
- `services_review.md` - GPG vs AES-256-GCM, tag cache docs missing
- `tasks_review.md` - Newsletter sync vs async, backup naming conventions
- `infrastructure_review.md` - Search abstraction layer, health check system undocumented
- `frontend_review.md` - Vite chunks, CSS aggregation, missing filters
- `deployment_review.md` - nginx location, Referrer-Policy mismatch, Redis version
- `testing_review.md` - Directory structure wrong, fixtures undocumented

### Implementation Notes

- Subagents used to execute reviews in sequence (not parallel) to avoid conflicts
- Each review created detailed improvement plans cross-referenced with actual code
- All plan files are in `architecture/plans/` for iterative documentation improvement