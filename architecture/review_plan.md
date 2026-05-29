# Architecture Review Plan

**Purpose:** Systematic review of all architecture documentation against actual codebase implementation. Each discrete module is reviewed by a subagent that verifies claims, identifies discrepancies, and writes improvement plans to `plans/`.

**Last Updated:** May 29, 2026
**Status:** READY FOR EXECUTION

---

## Scope

All documents in `architecture/` **except this file**. Eight discrete modules plus the root `overview.md`:

| # | Module | Directory | Docs to Review |
|---|--------|-----------|----------------|
| 1 | Core | `architecture/core/` | `app-factory.md`, `configuration.md`, `models.md` |
| 2 | Routes | `architecture/routes/` | `admin-routes.md`, `api-routes.md`, `public-routes.md`, `rss-feeds.md` |
| 3 | Services | `architecture/services/` | `overview.md`, `backup.md`, `search.md`, `slug.md`, `tag.md`, `tag_cache.md`, `serialization.md` |
| 4 | Tasks | `architecture/tasks/` | `overview.md`, `celery-tasks.md`, `scheduler.md` |
| 5 | Infrastructure | `architecture/infrastructure/` | `overview.md`, `search.md`, `email.md`, `storage.md`, `webhooks.md` |
| 6 | Frontend | `architecture/frontend/` | `overview.md`, `templates.md`, `static-assets.md` |
| 7 | Deployment | `architecture/deployment/` | `overview.md`, `docker.md`, `security.md`, `cicd.md` |
| 8 | Testing | `architecture/testing/` | `test-suite.md` |
| 9 | Overview | `architecture/` | `overview.md` |

---

## Subagent Review Instructions

Each module review is handled by a dedicated `explore` subagent. Subagents must:

1. **Read all architecture docs** in the module directory
2. **Read all source files** referenced in the docs (verify paths from `AGENTS.override.md` if present, or inline file references)
3. **Cross-reference every factual claim** against actual code:
   - Function signatures, parameter names/types/defaults
   - Route paths, HTTP methods, decorator patterns
   - Model field names, types, relationships, indexes
   - Config keys, default values, environment variable names
   - Line number references (flag drift >5 lines as significant)
4. **Document findings** in `plans/{module}_review.md` following the output format below
5. **Identify bugs or architectural concerns** surfaced during review
6. **Suggest specific, actionable improvements** for documentation gaps or code issues

**This is a review-only plan. Subagents should NOT edit any architecture docs or source code. All findings go into `plans/{module}_review.md`.**

---

## Output Format

Each `plans/{module}_review.md` must use this structure:

```markdown
# {Module Name} Architecture Review

**Reviewed:** YYYY-MM-DD
**Architecture Docs:** {list of docs reviewed}
**Source Files:** {list of source files verified}

## Findings

### Verified Claims (Correct)
- (list claims confirmed against code)

### Discrepancies (Doc vs Code)
- (specific file:line => what the doc claims vs what the code actually does)

### Missing Documentation
- (important aspects not covered in existing docs)

### Potential Bugs / Concerns
- (incorrect assumptions, race conditions, missing error handling, anti-patterns)

### Improvement Suggestions
- (enhancements that would improve docs, code quality, or architecture)

## Action Items
| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | high/med/low | ... | docs/source |
```

---

## Phase 1: Module Reviews (Parallel)

Launch all 8 module subagents in parallel. Each subagent works independently and writes to its designated `plans/{module}_review.md` file.

### Subagent Prompts

**Core Subagent**
Review `architecture/core/` containing `app-factory.md`, `configuration.md`, `models.md`.
Verify claims against: `app/__init__.py`, `app/config.py`, `app/models.py`, `app/extensions.py`, `app/filters.py`, `app/context_processors.py`.
Focus on: Flask app factory pattern, Config class structure, all 17 model definitions.
Write findings to: `plans/core_review.md`

**Routes Subagent**
Review `architecture/routes/` containing `admin-routes.md`, `api-routes.md`, `public-routes.md`, `rss-feeds.md`.
Verify claims against: `app/routes/admin/`, `app/routes/api/`, `app/routes/public/`, `app/routes/rss.py`, `app/routes/errors.py`.
Focus on: All route paths, HTTP methods, auth decorators, CSRF protection, request/response patterns.
Write findings to: `plans/routes_review.md`

**Services Subagent**
Review `architecture/services/` containing `overview.md`, `backup.md`, `search.md`, `slug.md`, `tag.md`, `tag_cache.md`, `serialization.md`.
Verify claims against: `app/services/`, `app/tag_cache.py`, `app/backup_encryption.py`, `app/webhook_encryption.py`.
Focus on: Service abstractions, function signatures, error handling patterns, encryption modules.
Write findings to: `plans/services_review.md`

**Tasks Subagent**
Review `architecture/tasks/` containing `overview.md`, `celery-tasks.md`, `scheduler.md`.
Verify claims against: `app/tasks.py`, `app/scheduler.py`, `app/celery_app.py`.
Focus on: Celery task configs, APScheduler job definitions, queue names, retry behavior, email retry count.
Write findings to: `plans/tasks_review.md`

**Infrastructure Subagent**
Review `architecture/infrastructure/` containing `overview.md`, `search.md`, `email.md`, `storage.md`, `webhooks.md`.
Verify claims against: `app/search.py`, `app/email.py`, `app/storage.py`, `app/webhooks.py`, `app/utils.py`.
Focus on: Search functions, email SMTP handling, storage backends, webhook SSRF protection and HMAC signing.
Write findings to: `plans/infrastructure_review.md`

**Frontend Subagent**
Review `architecture/frontend/` containing `overview.md`, `templates.md`, `static-assets.md`.
Verify claims against: `app/templates/`, `app/static/`, `app/filters.py`, `app/vite.py`, `app/context_processors.py`.
Focus on: Template structure, Jinja2 filters (actual filters: `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub`), CSS/JS assets, `critical.css`, Vite config, context variables (`site_title`, `site_description`).
Write findings to: `plans/frontend_review.md`

**Deployment Subagent**
Review `architecture/deployment/` containing `overview.md`, `docker.md`, `security.md`, `cicd.md`.
Verify claims against: `Dockerfile`, `docker-compose.yml`, `nginx/`, `.github/workflows/ci.yml`, `scripts/`.
Focus on: Docker setup, compose profiles, nginx config, CI workflow jobs (6 jobs), security headers, Docker compose explicit profile requirements.
Write findings to: `plans/deployment_review.md`

**Testing Subagent**
Review `architecture/testing/` containing `test-suite.md`.
Verify claims against: `tests/`, `pytest.ini`.
Focus on: Test structure, fixtures, coverage configuration, E2E setup with Playwright, test retry patterns.
Write findings to: `plans/testing_review.md`

---

## Phase 2: Overview Cross-Reference

After all 8 module reviews complete, launch a 9th subagent to review `architecture/overview.md`.

**Overview Subagent**
Review `architecture/overview.md`.
Cross-reference all claims against the 8 module review findings in `plans/*_review.md`.
Focus on: Cross-cutting references, module interdependencies, consistency of terminology, completeness of module coverage.
Write findings to: `plans/overview_review.md`

---

## Phase 3: Stale Item Pruning

After both phases complete, the executing agent (this agent) will:

1. Collect all `plans/*_review.md` files created by subagents
2. Scan `architecture/` for docs that reference removed features, non-existent files, or incorrect patterns
3. Identify docs where >50% of claims are wrong or source files no longer exist
4. Write pruning recommendations to `plans/architecture_prune.md`

### Prune Criteria

An architecture doc is a prune candidate if:
- Its source files no longer exist in the codebase
- More than 50% of claims are demonstrably wrong
- It documents a feature that has been removed
- It is a duplicate of another doc with no unique content
- It references deprecated APIs or patterns exclusively
- It has not been updated despite significant code changes since its creation

### Prune Output Format

`plans/architecture_prune.md` should contain:
- List of docs to DELETE (with rationale)
- List of docs to REWRITE (with rationale and scope)
- List of docs to MERGE (with rationale)
- Any stanzing items (lines in docs referencing removed files/functions)

---

## Final Deliverables

After execution, these files should exist in `plans/`:

| File | Contents |
|------|----------|
| `plans/core_review.md` | Core module review findings |
| `plans/routes_review.md` | Routes module review findings |
| `plans/services_review.md` | Services module review findings |
| `plans/tasks_review.md` | Tasks module review findings |
| `plans/infrastructure_review.md` | Infrastructure module review findings |
| `plans/frontend_review.md` | Frontend module review findings |
| `plans/deployment_review.md` | Deployment module review findings |
| `plans/testing_review.md` | Testing module review findings |
| `plans/overview_review.md` | Overview cross-reference findings |
| `plans/architecture_prune.md` | Stale item pruning recommendations |

---

## Notes

- This plan is **review-only**. No direct code changes are prescribed.
- Subagents should NOT edit architecture docs or source code.
- Line number references in docs are expected to drift. Flag drifts >5 lines but minor drift is low priority.
- Use `explore` subagent type for all module reviews.
- The `plans/plan.md` file (previous implementation plan) is completed and out of scope.
- Commit this plan to `main` after writing.
