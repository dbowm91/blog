# Architecture Review Plan

This plan outlines a comprehensive review of the architecture documentation. Each module will be reviewed by a subagent that will verify claims against the code and produce an improvement plan.

## Modules to Review

| Module | Documents | Subagent Output |
|--------|-----------|-----------------|
| core | app-factory.md, configuration.md, models.md | plans/core_review.md |
| routes | admin-routes.md, api-routes.md, public-routes.md, rss-feeds.md | plans/routes_review.md |
| services | backup.md, search.md, serialization.md, slug.md, tag.md, tag_cache.md, overview.md | plans/services_review.md |
| tasks | celery-tasks.md, scheduler.md, overview.md | plans/tasks_review.md |
| frontend | static-assets.md, templates.md, overview.md | plans/frontend_review.md |
| infrastructure | overview.md, webhooks.md, search.md, email.md, storage.md | plans/infrastructure_review.md |
| deployment | overview.md, security.md, cicd.md, docker.md | plans/deployment_review.md |
| testing | test-suite.md | plans/testing_review.md |

## Review Process

For each module, the subagent will:
1. Read all documents in the module directory
2. Verify claims against actual implementation in `app/`
3. Identify discrepancies, outdated information, or missing coverage
4. Interrogate code for potential improvements and bugs
5. Write improvement plan to the designated file in `plans/`

## Execution Order

Subagents will be launched in parallel where possible:

1. **Core Review** - Review `architecture/core/` documents
2. **Routes Review** - Review `architecture/routes/` documents
3. **Services Review** - Review `architecture/services/` documents
4. **Tasks Review** - Review `architecture/tasks/` documents
5. **Frontend Review** - Review `architecture/frontend/` documents
6. **Infrastructure Review** - Review `architecture/infrastructure/` documents
7. **Deployment Review** - Review `architecture/deployment/` documents
8. **Testing Review** - Review `architecture/testing/` documents

## Review Tasks

### Task 1: Core Module Review
- Directory: `architecture/core/`
- Output: `plans/core_review.md`
- Focus: app-factory.md, configuration.md, models.md

### Task 2: Routes Module Review
- Directory: `architecture/routes/`
- Output: `plans/routes_review.md`
- Focus: admin-routes.md, api-routes.md, public-routes.md, rss-feeds.md

### Task 3: Services Module Review
- Directory: `architecture/services/`
- Output: `plans/services_review.md`
- Focus: backup.md, search.md, serialization.md, slug.md, tag.md, tag_cache.md

### Task 4: Tasks Module Review
- Directory: `architecture/tasks/`
- Output: `plans/tasks_review.md`
- Focus: celery-tasks.md, scheduler.md, overview.md

### Task 5: Frontend Module Review
- Directory: `architecture/frontend/`
- Output: `plans/frontend_review.md`
- Focus: static-assets.md, templates.md, overview.md

### Task 6: Infrastructure Module Review
- Directory: `architecture/infrastructure/`
- Output: `plans/infrastructure_review.md`
- Focus: webhooks.md, search.md, email.md, storage.md

### Task 7: Deployment Module Review
- Directory: `architecture/deployment/`
- Output: `plans/deployment_review.md`
- Focus: security.md, cicd.md, docker.md

### Task 8: Testing Module Review
- Directory: `architecture/testing/`
- Output: `plans/testing_review.md`
- Focus: test-suite.md

## Launch Commands

Each subagent will be launched with the architecture_review skill and detailed instructions to:
1. Review the designated module documents
2. Cross-reference with actual code in `app/`
3. Document findings in the appropriate `plans/` file