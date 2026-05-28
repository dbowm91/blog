# Architecture Review Plan

## Purpose

This plan defines a systematic approach to reviewing all architecture documentation against the actual codebase. Each module is reviewed by a dedicated subagent that verifies claims, identifies discrepancies, interrogates the code for improvements and bugs, and writes a structured improvement plan to `plans/<module>_review.md`.

**This plan does not prescribe direct code changes.** Each subagent produces a review document; implementation is a separate concern.

---

## Modules

| # | Module | Directory | Documents | Output |
|---|--------|-----------|-----------|--------|
| 1 | **core** | `architecture/core/` | `app-factory.md`, `configuration.md`, `models.md` | `plans/core_review.md` |
| 2 | **routes** | `architecture/routes/` | `admin-routes.md`, `api-routes.md`, `public-routes.md`, `rss-feeds.md` | `plans/routes_review.md` |
| 3 | **services** | `architecture/services/` | `overview.md`, `backup.md`, `search.md`, `serialization.md`, `slug.md`, `tag.md`, `tag_cache.md` | `plans/services_review.md` |
| 4 | **tasks** | `architecture/tasks/` | `celery-tasks.md`, `scheduler.md`, `overview.md` | `plans/tasks_review.md` |
| 5 | **infrastructure** | `architecture/infrastructure/` | `overview.md`, `email.md`, `search.md`, `storage.md`, `webhooks.md` | `plans/infrastructure_review.md` |
| 6 | **frontend** | `architecture/frontend/` | `overview.md`, `static-assets.md`, `templates.md` | `plans/frontend_review.md` |
| 7 | **deployment** | `architecture/deployment/` | `docker.md`, `security.md`, `cicd.md`, `overview.md` | `plans/deployment_review.md` |
| 8 | **testing** | `architecture/testing/` | `test-suite.md` | `plans/testing_review.md` |

---

## Review Instructions

Each subagent must execute the following workflow for its assigned module:

### Phase 1: Read Documentation

1. Read every `.md` file in the module's `architecture/<module>/` directory
2. Read `architecture/AGENTS.override.md` for module-specific guidance
3. Note all concrete claims: route paths, function signatures, line numbers, configuration values, timing/scheduling details, security behaviors, model fields, queue names, file paths, and behavioral descriptions

### Phase 2: Cross-Reference with Code

For each claim, locate and verify against actual source code:

| Claim Type | Verification Method |
|------------|---------------------|
| Route paths | Read the route handler file in `app/routes/` |
| Function signatures | Read the function definition |
| Configuration values | Read `app/config.py` or `app/__init__.py` |
| Line numbers | Read the referenced file at the stated line |
| Model fields/relationships | Read `app/models.py` |
| Task names/queues | Read `app/tasks.py` and `app/scheduler.py` |
| Security behaviors | Read the implementation (auth, CSRF, rate limiting, etc.) |
| File paths | Verify the file exists at the stated location |
| Behavioral descriptions | Trace the code path end-to-end |

If a claim references a line number that has shifted, note the current line number and whether the claim's substance is still correct.

### Phase 3: Interrogate Code

Beyond verification, actively look for:

- **Bugs**: Logic errors, race conditions, unhandled edge cases
- **Security issues**: Missing validation, overly broad exception handling, credential leakage
- **Missing error handling**: Bare `except Exception`, silent `pass` on failures
- **Inconsistencies**: Mismatches between documentation, AGENTS.md, and actual code
- **Dead code**: Functions or imports that are no longer used
- **Stale documentation**: Claims about features that have been removed or renamed

### Phase 4: Write Improvement Plan

Write findings to `plans/<module>_review.md` using this structure:

```markdown
# <Module> Module Architecture Review

**Review Date:** <date>
**Reviewer:** <module>_reviewer

## Verified Accurate Claims

| Claim | Source | Evidence |
|-------|--------|----------|
| ... | file:line | ... |

## Inaccurate/Outdated Claims

### <Issue Title>
**Location:** <doc file + line>
**Claim:** <what the doc says>
**Reality:** <what the code actually does>
**Correction:** <what the doc should say>

## Missing Documentation

### <Feature/Component>
**Location:** <source file>
**Missing:** <what is not documented>
**Impact:** <why it matters>

## Potential Issues

### <Issue Title>
**Severity:** High/Medium/Low
**Location:** <file:line>
**Issue:** <description>
**Recommendation:** <suggested action>

## Recommended Improvements

### Priority 1: <Category>
1. <specific improvement>

### Priority 2: <Category>
1. <specific improvement>

## Summary

| Category | Count |
|----------|-------|
| Verified Accurate Claims | N |
| Inaccurate/Outdated Claims | N |
| Missing Documentation | N |
| Potential Issues | N |
```

---

## Execution

### Wave 1: Modules 1-4 (parallel)

Launch 4 subagents concurrently, one for each module:

| Subagent | Module | Output File |
|----------|--------|-------------|
| `core_reviewer` | core | `plans/core_review.md` |
| `routes_reviewer` | routes | `plans/routes_review.md` |
| `services_reviewer` | services | `plans/services_review.md` |
| `tasks_reviewer` | tasks | `plans/tasks_review.md` |

### Wave 2: Modules 5-8 (parallel)

Launch 4 subagents concurrently after Wave 1 completes:

| Subagent | Module | Output File |
|----------|--------|-------------|
| `infrastructure_reviewer` | infrastructure | `plans/infrastructure_review.md` |
| `frontend_reviewer` | frontend | `plans/frontend_review.md` |
| `deployment_reviewer` | deployment | `plans/deployment_review.md` |
| `testing_reviewer` | testing | `plans/testing_review.md` |

### Wave 3: Stale Item Pruning

After all module reviews are complete, launch a pruning agent that:

1. Reads all `plans/<module>_review.md` files
2. Cross-references findings against current `architecture/` documents
3. Identifies stale items in the review plans:
   - Claims that were already fixed in prior waves (check git log for commits referencing the issue)
   - Items that are no longer relevant due to code changes
   - Duplicate findings across modules
4. Writes a pruning summary to `plans/pruning_summary.md` listing:
   - Items confirmed still relevant
   - Items confirmed fixed (with commit references)
   - Items that are stale/no longer applicable

### Wave 4: Final Compilation

After Wave 3, update `architecture/review_plan.md` with:

1. Wave completion status
2. Links to all `plans/<module>_review.md` files
3. Summary statistics from all reviews
4. Outstanding items that still need attention

---

## Subagent Prompt Template

Each subagent receives this prompt (with module-specific values substituted):

```
You are a code architecture reviewer. Your task is to review the <MODULE> module
of the blog CMS architecture documentation.

## Your Assignment

1. Read all documents in architecture/<MODULE>/
2. Read architecture/AGENTS.override.md for module-specific guidance
3. Cross-reference every concrete claim against the actual source code
4. Interrogate the code for bugs, security issues, and improvements
5. Write your findings to plans/<MODULE>_review.md

## Review Scope

Documents to review:
<list of .md files in the module directory>

Source code to cross-reference:
<list of relevant source files>

## Output

Write a structured review to plans/<MODULE>_review.md following the template
in architecture/review_plan.md. Do NOT make code changes - only document findings.

## Important Notes

- Work only within /Users/davidbowman/projects/blog/
- Verify line numbers by reading files directly
- Note both accurate and inaccurate claims
- Flag potential bugs and security concerns
- Prioritize findings by severity
```

---

## Output Files

| File | Content |
|------|---------|
| `plans/core_review.md` | Core module review findings |
| `plans/routes_review.md` | Routes module review findings |
| `plans/services_review.md` | Services module review findings |
| `plans/tasks_review.md` | Tasks module review findings |
| `plans/infrastructure_review.md` | Infrastructure module review findings |
| `plans/frontend_review.md` | Frontend module review findings |
| `plans/deployment_review.md` | Deployment module review findings |
| `plans/testing_review.md` | Testing module review findings |
| `plans/pruning_summary.md` | Stale item pruning results |

---

## Previous Review History

| Wave | Date | Modules | Key Fixes |
|------|------|---------|-----------|
| Wave O | May 2026 | All | Line number fixes, documentation corrections across all modules |
| Wave A-F | May 22, 2026 | All | 43 action items completed (search, backup, routes, frontend, infrastructure docs) |

This review cycle starts fresh, re-verifying all claims against current code.
