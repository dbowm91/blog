# Architecture Review Plan

**Purpose:** Systematic review of all architecture documentation against actual codebase implementation. Each discrete module is reviewed by a subagent that verifies claims, identifies discrepancies, and writes improvement plans to `plans/`.

**Last Updated:** May 29, 2026

---

## Scope

All documents in `architecture/` **except this file** (`review_plan.md`). The review covers 8 discrete modules plus the root `overview.md`.

### Module Inventory

| # | Module | Directory | Docs | Source Files |
|---|--------|-----------|------|--------------|
| 1 | Core | `architecture/core/` | `app-factory.md`, `configuration.md`, `models.md` | `app/__init__.py`, `app/config.py`, `app/models.py`, `app/extensions.py`, `app/filters.py`, `app/context_processors.py` |
| 2 | Routes | `architecture/routes/` | `admin-routes.md`, `api-routes.md`, `public-routes.md`, `rss-feeds.md` | `app/routes/` (admin/, api/, public/, rss.py, errors.py) |
| 3 | Services | `architecture/services/` | `overview.md`, `backup.md`, `search.md`, `slug.md`, `tag.md`, `tag_cache.md`, `serialization.md` | `app/services/`, `app/tag_cache.py`, `app/backup_encryption.py`, `app/webhook_encryption.py` |
| 4 | Tasks | `architecture/tasks/` | `overview.md`, `celery-tasks.md`, `scheduler.md` | `app/tasks.py`, `app/scheduler.py`, `app/celery_app.py` |
| 5 | Infrastructure | `architecture/infrastructure/` | `overview.md`, `search.md`, `email.md`, `storage.md`, `webhooks.md` | `app/search.py`, `app/email.py`, `app/storage.py`, `app/webhooks.py`, `app/utils.py` |
| 6 | Frontend | `architecture/frontend/` | `overview.md`, `templates.md`, `static-assets.md` | `app/templates/`, `app/static/`, `app/filters.py`, `app/vite.py` |
| 7 | Deployment | `architecture/deployment/` | `overview.md`, `docker.md`, `security.md`, `cicd.md` | `Dockerfile`, `docker-compose.yml`, `nginx/`, `.github/workflows/`, `scripts/` |
| 8 | Testing | `architecture/testing/` | `test-suite.md` | `tests/`, `pytest.ini` |
| 9 | Overview | `architecture/` | `overview.md` | Cross-cutting (references all modules) |

---

## Review Methodology

### For Each Module

1. **Read** all architecture docs in the module directory
2. **Read** the corresponding source files listed in each doc
3. **Verify** every factual claim (function signatures, line numbers, route paths, field names, relationships, config keys, defaults)
4. **Interrogate** for improvements and bugs:
   - Missing or incorrect function signatures
   - Missing route endpoints or HTTP methods
   - Incorrect model field names, types, or relationships
   - Missing index definitions
   - Incorrect config keys or defaults
   - Missing error handling patterns
   - Stale line number references
   - Inconsistencies between docs within the same module
   - Security concerns or anti-patterns
   - Missing edge case documentation
   - Incorrect CSP headers, security headers, or rate limits
5. **Write** findings to `plans/{module}_review.md`

### Verification Approach

For each claim in architecture docs:
- Confirm function/class exists at referenced location
- Confirm parameter names, types, and defaults match source
- Confirm route paths, HTTP methods, and decorators match source
- Confirm model fields, relationships, and indexes match source
- Confirm config keys exist and have stated defaults
- Confirm line number references are still valid (code may have shifted)

---

## Subagent Instructions

Each module review is handled by a dedicated subagent. Subagents must:

1. **Read all architecture docs** in the module directory first
2. **Read all referenced source files** (verify paths from `AGENTS.override.md` and overview.md)
3. **Cross-reference** every claim against actual code
4. **Document discrepancies** with specific file paths, line numbers, and what needs to change
5. **Suggest improvements** for missing documentation, unclear descriptions, or architectural concerns
6. **Identify bugs** surfaced during review (incorrect assumptions, race conditions, missing error handling)
7. **Write output** to `plans/{module}_review.md`

### Output Format

Each `plans/{module}_review.md` must follow this structure:

```markdown
# {Module Name} Architecture Review

**Reviewed:** {date}
**Architecture Docs:** {list of docs reviewed}
**Source Files:** {list of source files verified}

## Findings

### Verified Claims (Correct)
- ...

### Discrepancies (Doc vs Code)
- ...

### Missing Documentation
- ...

### Potential Bugs / Concerns
- ...

### Improvement Suggestions
- ...

## Action Items
| # | Priority | Description | Docs Affected |
|---|----------|-------------|---------------|
| 1 | high/med/low | ... | ... |
```

---

## Execution Order

Subagents run in parallel for all 8 modules. The overview module is reviewed last since it references all others.

| Phase | Module | Subagent Prompt Summary |
|-------|--------|------------------------|
| 1 (parallel) | Core | Verify app factory, config, models against `app/__init__.py`, `app/config.py`, `app/models.py` |
| 1 (parallel) | Routes | Verify all route definitions, HTTP methods, auth decorators across `app/routes/` |
| 1 (parallel) | Services | Verify service abstractions, function signatures, encryption modules |
| 1 (parallel) | Tasks | Verify Celery task configs, APScheduler jobs, queue names, retry behavior |
| 1 (parallel) | Infrastructure | Verify search functions, email SMTP, storage backends, webhook SSRF |
| 1 (parallel) | Frontend | Verify template structure, CSS/JS files, Vite config, filters, context processors |
| 1 (parallel) | Deployment | Verify Docker setup, nginx config, CI workflows, security headers |
| 1 (parallel) | Testing | Verify test structure, fixtures, coverage config, E2E setup |
| 2 (serial) | Overview | Verify overview.md cross-references against all module findings |

---

## Stale Item Pruning (Phase 3)

After all module reviews complete:

1. **Collect** all `plans/{module}_review.md` files
2. **Identify** architecture docs that are entirely superseded or contain only stale content
3. **Identify** docs that reference files, functions, or patterns that no longer exist
4. **List** candidates for removal or major rewrite in `plans/architecture_prune.md`
5. **Propose** specific prune actions (delete, rewrite, merge) with rationale

### Prune Criteria

An architecture doc is a prune candidate if:
- Its source files no longer exist in the codebase
- More than 50% of claims are demonstrably wrong
- It documents a feature that has been removed
- It is a duplicate of another doc with no unique content
- It references deprecated APIs or patterns exclusively

---

## Final Deliverables

After all phases complete, the following files exist in `plans/`:

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

- This plan is **review-only**. It does not prescribe code changes.
- The executing agent should NOT edit architecture docs directly. Findings go into `plans/`.
- Line number references in architecture docs are expected to drift over time. Flag significant drift (>5 lines) but minor drift is low priority.
- The `plans/plan.md` file (previous implementation plan) is completed and should not be modified.
- The `plans/improvements.md` file is a separate polish plan and should not be modified.
