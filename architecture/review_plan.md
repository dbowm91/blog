# Architecture Review Plan

**Created:** May 2026
**Status:** IN PROGRESS

This document outlines the review plan for architecture documents in the `architecture/` directory (excluding `review_plan.md` itself).

## Modules to Review

| Module | Documents | Review Agent | Output | Status |
|--------|-----------|--------------|--------|--------|
| **Core** | `core/app-factory.md`, `core/configuration.md`, `core/models.md` | core-reviewer | `plans/core_review.md` | 🔄 PENDING |
| **Services** | `services/backup.md`, `services/serialization.md`, `services/tag.md`, `services/slug.md`, `services/tag_cache.md`, `services/overview.md` | services-reviewer | `plans/services_review.md` | 🔄 PENDING |
| **Routes** | `routes/api-routes.md`, `routes/admin-routes.md`, `routes/public-routes.md`, `routes/rss-feeds.md` | routes-reviewer | `plans/routes_review.md` | 🔄 PENDING |
| **Testing** | `testing/test-suite.md` | testing-reviewer | `plans/testing_review.md` | 🔄 PENDING |
| **Tasks** | `tasks/celery-tasks.md`, `tasks/scheduler.md`, `tasks/overview.md` | tasks-reviewer | `plans/tasks_review.md` | 🔄 PENDING |
| **Infrastructure** | `infrastructure/webhooks.md`, `infrastructure/search.md`, `infrastructure/email.md`, `infrastructure/storage.md`, `infrastructure/overview.md` | infrastructure-reviewer | `plans/infrastructure_review.md` | 🔄 PENDING |
| **Frontend** | `frontend/static-assets.md`, `frontend/templates.md`, `frontend/overview.md` | frontend-reviewer | `plans/frontend_review.md` | 🔄 PENDING |
| **Deployment** | `deployment/docker.md`, `deployment/security.md`, `deployment/cicd.md`, `deployment/overview.md` | deployment-reviewer | `plans/deployment_review.md` | 🔄 PENDING |

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