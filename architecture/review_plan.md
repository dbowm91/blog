# Architecture Review Plan

**Purpose:** Systematic review of all architecture documentation against actual codebase implementation. Each discrete module is reviewed by a subagent that verifies claims, identifies discrepancies, interrogates code for bugs and improvements, and writes improvement plans to `plans/`.

**Created:** May 31, 2026
**Status:** COMPLETE — All reviews consolidated into `plans/plan.md` (June 2, 2026). Individual review files removed.

---

## Scope

All documents in `architecture/` **except this file**. Nine discrete modules:

| # | Module | Directory | Docs | Source Files to Verify |
|---|--------|-----------|------|----------------------|
| 1 | Core | `architecture/core/` | `app-factory.md`, `configuration.md`, `models.md` | `app/__init__.py`, `app/config.py`, `app/models.py`, `app/extensions.py`, `app/filters.py`, `app/context_processors.py` |
| 2 | Routes | `architecture/routes/` | `admin-routes.md`, `api-routes.md`, `public-routes.md`, `rss-feeds.md` | `app/routes/admin/`, `app/routes/api/`, `app/routes/public/`, `app/routes/rss.py`, `app/routes/errors.py` |
| 3 | Services | `architecture/services/` | `overview.md`, `backup.md`, `encryption.md`, `search.md`, `slug.md`, `tag.md`, `tag_cache.md`, `serialization.md` | `app/services/`, `app/tag_cache.py`, `app/backup_encryption.py`, `app/webhook_encryption.py` |
| 4 | Tasks | `architecture/tasks/` | `overview.md`, `celery-tasks.md`, `scheduler.md` | `app/tasks.py`, `app/scheduler.py`, `app/celery_app.py` |
| 5 | Infrastructure | `architecture/infrastructure/` | `overview.md` (if exists), `search.md`, `email.md`, `storage.md`, `webhooks.md` | `app/search.py`, `app/email.py`, `app/storage.py`, `app/webhooks.py`, `app/utils.py` |
| 6 | Frontend | `architecture/frontend/` | `overview.md`, `templates.md`, `static-assets.md` | `app/templates/`, `app/static/`, `app/filters.py`, `app/vite.py`, `app/context_processors.py` |
| 7 | Deployment | `architecture/deployment/` | `overview.md`, `docker.md`, `security.md`, `cicd.md` | `Dockerfile`, `docker-compose.yml`, `nginx/`, `.github/workflows/ci.yml`, `scripts/` |
| 8 | Testing | `architecture/testing/` | `test-suite.md` | `tests/`, `tests/conftest.py`, `tests/e2e/conftest.py`, `pytest.ini` |
| 9 | Overview | `architecture/` | `overview.md` | Cross-references all module findings |

**Total documents:** 33 (excluding this review plan)

---

## Subagent Review Instructions

Each module review is handled by a dedicated `explore` subagent. Subagents must:

1. **Read all architecture docs** in the module directory
2. **Read all source files** referenced in the docs
3. **Cross-reference every factual claim** against actual code:
   - Function signatures, parameter names/types/defaults
   - Route paths, HTTP methods, decorator patterns
   - Model field names, types, relationships, indexes
   - Config keys, default values, environment variable names
   - Line number references (flag drift >5 lines as significant)
4. **Interrogate the code** for:
   - Bugs (race conditions, missing error handling, incorrect assumptions)
   - Security concerns (injection, SSRF, credential leaks, missing validation)
   - Anti-patterns (code duplication, resource leaks, performance issues)
   - Missing edge cases
5. **Write findings** to `plans/{module}_review.md` following the output format below
6. **DO NOT** edit any architecture docs or source code — findings only

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
Focus on: Flask app factory initialization steps, Config class structure and defaults, all 17 model definitions and relationships, extension initialization order.
Write findings to: `plans/core_review.md`

**Routes Subagent**
Review `architecture/routes/` containing `admin-routes.md`, `api-routes.md`, `public-routes.md`, `rss-feeds.md`.
Verify claims against: `app/routes/admin/`, `app/routes/api/`, `app/routes/public/`, `app/routes/rss.py`, `app/routes/errors.py`.
Focus on: All route paths and HTTP methods, auth decorator usage, CSRF protection patterns, request/response formats, rate limiting configuration.
Write findings to: `plans/routes_review.md`

**Services Subagent**
Review `architecture/services/` containing `overview.md`, `backup.md`, `encryption.md`, `search.md`, `slug.md`, `tag.md`, `tag_cache.md`, `serialization.md`.
Verify claims against: `app/services/`, `app/tag_cache.py`, `app/backup_encryption.py`, `app/webhook_encryption.py`.
Focus on: Service abstractions and function signatures, encryption module implementations, error handling patterns, cache coordination.
Write findings to: `plans/services_review.md`

**Tasks Subagent**
Review `architecture/tasks/` containing `overview.md`, `celery-tasks.md`, `scheduler.md`.
Verify claims against: `app/tasks.py`, `app/scheduler.py`, `app/celery_app.py`.
Focus on: Celery task configs and queue names, APScheduler job definitions and schedules, retry behavior, concurrency limits, email retry count (verify default is 5 not 3).
Write findings to: `plans/tasks_review.md`

**Infrastructure Subagent**
Review `architecture/infrastructure/` containing any `overview.md`, `search.md`, `email.md`, `storage.md`, `webhooks.md`.
Verify claims against: `app/search.py`, `app/email.py`, `app/storage.py`, `app/webhooks.py`, `app/utils.py`.
Focus on: FTS5 search functions and error handling, SMTP email delivery and retry logic, storage backend abstraction, webhook SSRF protection and HMAC signing, health check implementation.
Write findings to: `plans/infrastructure_review.md`

**Frontend Subagent**
Review `architecture/frontend/` containing `overview.md`, `templates.md`, `static-assets.md`.
Verify claims against: `app/templates/`, `app/static/`, `app/filters.py`, `app/vite.py`, `app/context_processors.py`.
Focus on: Template inheritance hierarchy, Jinja2 filters (verify actual registered filters), CSS/JS asset pipeline, `critical.css` loading, Vite config and manifest, context variables (verify `site_title`/`site_description` not `site_name`/`site_tagline`).
Write findings to: `plans/frontend_review.md`

**Deployment Subagent**
Review `architecture/deployment/` containing `overview.md`, `docker.md`, `security.md`, `cicd.md`.
Verify claims against: `Dockerfile`, `docker-compose.yml`, `nginx/`, `.github/workflows/ci.yml`, `scripts/`.
Focus on: Docker service definitions and profiles, nginx configuration, CI workflow jobs (verify 6 jobs), security headers, resource limits, health check parameters, Python version consistency between dev.sh and Dockerfile.
Write findings to: `plans/deployment_review.md`

**Testing Subagent**
Review `architecture/testing/` containing `test-suite.md`.
Verify claims against: `tests/`, `tests/conftest.py`, `tests/e2e/conftest.py`, `pytest.ini`.
Focus on: Test structure and fixture definitions, coverage configuration, E2E setup with Playwright, known inconsistencies (E2E password mismatch, playwright in requirements.txt claim, E2E conftest app fixture claim).
Write findings to: `plans/testing_review.md`

---

## Phase 2: Overview Cross-Reference

After all 8 module reviews complete, launch a 9th subagent to review `architecture/overview.md`.

**Overview Subagent**
Review `architecture/overview.md`.
Cross-reference all claims against the 8 module review findings in `plans/*_review.md`.
Focus on: Cross-cutting references, module interdependencies, consistency of terminology, completeness of module coverage, model count verification (17 models), queue count verification (5 queues), scheduled job count verification (4 jobs).
Write findings to: `plans/overview_review.md`

---

## Phase 3: Stale Item Pruning

After all 9 reviews complete, the executing agent will:

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
- Any stale items (lines in docs referencing removed files/functions)

---

## Final Deliverables

After execution, the following files were created and then consolidated:

| File | Status |
|------|--------|
| `plans/core_review.md` | Consolidated into `plans/plan.md`, then removed |
| `plans/routes_review.md` | Consolidated into `plans/plan.md`, then removed |
| `plans/services_review.md` | Consolidated into `plans/plan.md`, then removed |
| `plans/tasks_review.md` | Consolidated into `plans/plan.md`, then removed |
| `plans/infrastructure_review.md` | Consolidated into `plans/plan.md`, then removed |
| `plans/frontend_review.md` | Consolidated into `plans/plan.md`, then removed |
| `plans/deployment_review.md` | Consolidated into `plans/plan.md`, then removed |
| `plans/testing_review.md` | Consolidated into `plans/plan.md`, then removed |
| `plans/overview_review.md` | Consolidated into `plans/plan.md`, then removed |
| `plans/architecture_prune.md` | Consolidated into `plans/plan.md`, then removed |
| **`plans/plan.md`** | **Active — single source of truth for all architecture improvements** |

---

## Notes

- This plan is **review-only**. No direct code changes are prescribed.
- Subagents should NOT edit architecture docs or source code — all findings go into `plans/`.
- Line number references in docs are expected to drift. Flag drifts >5 lines but minor drift is low priority.
- Use `explore` subagent type for all module reviews.
- This is a fresh review plan (May 31, 2026), replacing the prior completed plan.
