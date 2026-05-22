# Architecture Review Plan

## Overview

This plan organizes a comprehensive review of all architecture documentation modules using subagents. Each subagent will:
1. Review their designated module's documentation
2. Verify claims against actual code implementation
3. Identify discrepancies, bugs, and improvements
4. Write an improvement plan to `plans/<module>_review.md`

## Modules to Review

| Module | Directory | Documents | Subagent Output |
|--------|-----------|-----------|----------------|
| Core | `architecture/core/` | app-factory.md, configuration.md, models.md | `plans/core_review.md` |
| Services | `architecture/services/` | backup.md, overview.md, search.md, serialization.md, slug.md, tag_cache.md, tag.md | `plans/services_review.md` |
| Routes | `architecture/routes/` | admin-routes.md, api-routes.md, public-routes.md, rss-feeds.md | `plans/routes_review.md` |
| Tasks | `architecture/tasks/` | celery-tasks.md, overview.md, scheduler.md | `plans/tasks_review.md` |
| Infrastructure | `architecture/infrastructure/` | email.md, overview.md, search.md, storage.md, webhooks.md | `plans/infrastructure_review.md` |
| Frontend | `architecture/frontend/` | overview.md, static-assets.md, templates.md | `plans/frontend_review.md` |
| Deployment | `architecture/deployment/` | cicd.md, docker.md, overview.md, security.md | `plans/deployment_review.md` |
| Testing | `architecture/testing/` | test-suite.md | `plans/testing_review.md` |

## Review Workflow

For each module, the subagent should:
1. Read all documentation files in the module directory
2. Cross-reference claims with actual code in `app/`
3. Verify implementation details against documentation
4. Identify any bugs, inconsistencies, or improvement opportunities
5. Document findings in `plans/<module>_review.md`

## Subagent Execution

Launch subagents in parallel for independent modules:

### 1. Core Review (architecture/core/)
- **app-factory.md** - Flask app creation, extensions, context processors
- **configuration.md** - Config classes, environment variables
- **models.md** - SQLAlchemy models, relationships

### 2. Services Review (architecture/services/)
- **backup.md** - Backup service, encryption
- **search.md** - Search provider abstraction, FTS5
- **serialization.md** - JSON serialization
- **slug.md** - Slug generation
- **tag_cache.md** - Tag caching
- **tag.md** - Tag service

### 3. Routes Review (architecture/routes/)
- **admin-routes.md** - Admin dashboard routes
- **api-routes.md** - REST API endpoints
- **public-routes.md** - Public facing routes
- **rss-feeds.md** - Atom/RSS/JSON feeds

### 4. Tasks Review (architecture/tasks/)
- **celery-tasks.md** - Celery task definitions
- **scheduler.md** - APScheduler jobs

### 5. Infrastructure Review (architecture/infrastructure/)
- **email.md** - Email sending, SMTP handling
- **search.md** - Search infrastructure
- **storage.md** - S3 storage backend
- **webhooks.md** - Webhook delivery, encryption

### 6. Frontend Review (architecture/frontend/)
- **static-assets.md** - JS/CSS assets, Vite
- **templates.md** - Jinja2 templates

### 7. Deployment Review (architecture/deployment/)
- **docker.md** - Docker configuration
- **cicd.md** - CI/CD pipeline
- **security.md** - Security configuration

### 8. Testing Review (architecture/testing/)
- **test-suite.md** - Test infrastructure

## Output Format

Each module's improvement plan should contain:
- **Verified Claims** - Documentation claims confirmed in code
- **Discrepancies** - Documentation vs implementation mismatches
- **Bugs Found** - Actual bugs discovered
- **Improvement Opportunities** - Suggested enhancements
- **Priority** - High/Medium/Low classification