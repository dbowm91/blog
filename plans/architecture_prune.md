# Architecture Documentation Pruning Recommendations

**Analyzed:** May 29, 2026
**Based on:** Direct codebase verification against all 34 architecture docs

## Executive Summary

Overall documentation health is **good**. No documents need removal. The architecture docs are well-structured, accurate, and follow consistent conventions. Key issues are:

- **Model count inconsistency** in `overview.md` (claims 20 and 19 models; actual count is 17)
- **3 missing API endpoints** in `api-routes.md` (pages, series, tags exist in code but not in doc)
- **Stale webhook task architecture** in `celery-tasks.md` (dispatch pattern changed, missing `deliver_single_webhook_task`)
- **Incorrect webhook event type** in `webhooks.md` and `celery-tasks.md` (`post.created` does not exist; actual event is `post.unpublished`)
- **Missing service** in `services/overview.md` (encryption service not listed)
- **Broken links** in `overview.md` (references non-existent `plans/{module}_review.md` files)

No documents are candidates for removal or merge. All are salvageable with targeted fixes.

## Per-Document Analysis

### architecture/overview.md
- **Status:** Needs minor fixes
- **Issues:**
  - Line 99: Claims "20 models" — actual count is 17 model classes in `app/models.py`
  - Line 312: Claims "19 models" in directory structure — also wrong
  - Lines 492-499: "Review Plans" section links to `plans/{module}_review.md` files that do not exist (these are Phase 3 deliverables, not yet created)
  - Missing `app/services/encryption.py` from Services Layer table (line 168)
  - Missing `app/base62.py`, `app/csv_utils.py`, `app/transaction.py`, `app/backup_integrity.py`, `app/validators.py`, `app/cli.py`, `app/page_view_buffer.py`, `app/markdown_config.py` from directory structure
- **Recommendation:** Fix model count to 17, remove or mark review plan links as pending, add missing modules to directory structure

### architecture/core/app-factory.md
- **Status:** Minor fixes needed
- **Issues:**
  - CSP policy (lines 83-94) may not match current implementation — needs verification against `app/__init__.py`
  - Line 141: References `routes/overview.md` which does not exist
- **Recommendation:** Verify CSP policy against code, fix broken See Also link

### architecture/core/configuration.md
- **Status:** Fine as-is
- **Issues:** None significant. Config keys and defaults verified against `app/config.py`.
- **Recommendation:** No action needed

### architecture/core/models.md
- **Status:** Minor fixes needed
- **Issues:**
  - Line 7: Overview table header says "20 models" implicitly via the model count context — actual count is 17
  - `ApiToken` model (line 121 of models.py) is documented in overview.md but missing from the models.md overview table
- **Recommendation:** Add ApiToken to model overview table, verify model count consistency

### architecture/routes/admin-routes.md
- **Status:** Fine as-is
- **Issues:** All routes verified against source files. Accurate.
- **Recommendation:** No action needed

### architecture/routes/api-routes.md
- **Status:** Needs minor fixes
- **Issues:**
  - Missing 3 endpoints that exist in `app/routes/api/`:
    - `/api/pages` (GET, POST) — `app/routes/api/pages.py`
    - `/api/series` (GET, POST) — `app/routes/api/series.py`
    - `/api/tags` (GET, POST) — `app/routes/api/tags.py`
  - These ARE listed in `overview.md:152-155` but absent from the detailed `api-routes.md`
- **Recommendation:** Add pages, series, and tags endpoints to api-routes.md

### architecture/routes/public-routes.md
- **Status:** Fine as-is
- **Issues:** None. Routes verified against source.
- **Recommendation:** No action needed

### architecture/routes/rss-feeds.md
- **Status:** Fine as-is
- **Issues:** None. Feed formats and endpoints verified.
- **Recommendation:** No action needed

### architecture/services/overview.md
- **Status:** Needs minor fix
- **Issues:**
  - Missing `app/services/encryption.py` from the services table — this module handles TOTP secret encryption and is documented in `backup.md` but not listed in the overview
- **Recommendation:** Add encryption service to the overview table

### architecture/services/backup.md
- **Status:** Minor fixes needed
- **Issues:**
  - Line 97: File naming shows `.db.gpg` extension, but the actual encrypted format uses `.db.gpg` (correct). However, the doc implies GPG encryption when the actual mechanism is AES-256-GCM — this was fixed in a previous wave but the `.gpg` extension naming is misleading
  - Line 124: References `app/scheduler.py:261` for `run_daily_backup()` — line number may have drifted
- **Recommendation:** Clarify that `.gpg` extension is used for AES-256-GCM encrypted files (not GPG), verify line number

### architecture/services/search.md
- **Status:** Fine as-is
- **Issues:** None significant. Provider abstraction and functions verified.
- **Recommendation:** No action needed

### architecture/services/slug.md
- **Status:** Fine as-is
- **Issues:** None. Function signature and behavior verified.
- **Recommendation:** No action needed

### architecture/services/tag.md
- **Status:** Fine as-is
- **Issues:** None. Functions and behavior verified.
- **Recommendation:** No action needed

### architecture/services/tag_cache.md
- **Status:** Fine as-is
- **Issues:** None significant. Line number references may have minor drift.
- **Recommendation:** No action needed

### architecture/services/serialization.md
- **Status:** Fine as-is
- **Issues:** None. Correctly documents absence of deserialize functions.
- **Recommendation:** No action needed

### architecture/tasks/overview.md
- **Status:** Fine as-is
- **Issues:** None.
- **Recommendation:** No action needed

### architecture/tasks/celery-tasks.md
- **Status:** Needs minor fixes
- **Issues:**
  - Missing `deliver_single_webhook_task` (line 234 of `app/tasks.py`) — the per-webhook retry task that `deliver_webhook_task` dispatches to. This is a significant architectural change from what's documented
  - Lines 61, 102, 107: State that `deliver_webhook_task` never calls `self.retry()` and silently skips failures — this is outdated. The task now dispatches to `deliver_single_webhook_task` which has its own retry logic
  - Lines 118-133: Database session management section lists specific line numbers that may have drifted
  - `deliver_webhook_task` docs don't mention the dispatch-to-subtask pattern
- **Recommendation:** Document `deliver_single_webhook_task`, update `deliver_webhook_task` description to reflect dispatch pattern, verify line numbers

### architecture/tasks/scheduler.md
- **Status:** Fine as-is
- **Issues:** None significant. Jobs and behavior verified against `app/scheduler.py`.
- **Recommendation:** No action needed

### architecture/infrastructure/overview.md
- **Status:** Fine as-is
- **Issues:** None. Health check and storage docs verified.
- **Recommendation:** No action needed

### architecture/infrastructure/search.md
- **Status:** Fine as-is
- **Issues:** None. Functions and behavior verified.
- **Recommendation:** No action needed

### architecture/infrastructure/email.md
- **Status:** Fine as-is
- **Issues:** None. Retry count (5) correctly documented.
- **Recommendation:** No action needed

### architecture/infrastructure/storage.md
- **Status:** Fine as-is
- **Issues:** None. Backends and configuration verified.
- **Recommendation:** No action needed

### architecture/infrastructure/webhooks.md
- **Status:** Needs minor fix
- **Issues:**
  - Line 119: Lists `post.created` as an event type — this event does not exist in the codebase. The actual events are `post.published`, `post.unpublished`, and `subscriber.confirmed`
- **Recommendation:** Replace `post.created` with `post.unpublished` in the event types table

### architecture/frontend/overview.md
- **Status:** Fine as-is
- **Issues:** None.
- **Recommendation:** No action needed

### architecture/frontend/templates.md
- **Status:** Fine as-is
- **Issues:** None. Template structure and filters verified.
- **Recommendation:** No action needed

### architecture/frontend/static-assets.md
- **Status:** Fine as-is
- **Issues:** None significant. Vite config and JS patterns verified.
- **Recommendation:** No action needed

### architecture/deployment/overview.md
- **Status:** Fine as-is
- **Issues:** None.
- **Recommendation:** No action needed

### architecture/deployment/docker.md
- **Status:** Fine as-is
- **Issues:** None significant. Services, profiles, and env vars verified.
- **Recommendation:** No action needed

### architecture/deployment/security.md
- **Status:** Fine as-is
- **Issues:** None. Security features and headers verified.
- **Recommendation:** No action needed

### architecture/deployment/cicd.md
- **Status:** Fine as-is
- **Issues:** None. Workflow structure verified.
- **Recommendation:** No action needed

### architecture/testing/test-suite.md
- **Status:** Fine as-is
- **Issues:** None. Test structure and fixtures verified.
- **Recommendation:** No action needed

## Stale Content Summary

| Doc | Section | Issue | Action |
|-----|---------|-------|--------|
| overview.md | Data Models (line 99) | Claims "20 models" — actual is 17 | Fix count |
| overview.md | Directory Structure (line 312) | Claims "19 models" — actual is 17 | Fix count |
| overview.md | Review Plans (lines 492-499) | Links to non-existent review files | Remove or mark as pending |
| overview.md | Services Layer (line 168) | Missing `encryption.py` | Add to table |
| overview.md | Directory Structure | Missing 8 Python modules | Add to tree |
| core/app-factory.md | See Also (line 141) | References non-existent `routes/overview.md` | Fix link |
| core/models.md | Overview table | Missing `ApiToken` model | Add to table |
| routes/api-routes.md | Endpoints table | Missing pages, series, tags endpoints | Add 3 endpoint groups |
| services/overview.md | Services table | Missing `encryption.py` | Add to table |
| services/backup.md | File naming (line 97) | `.gpg` extension implies GPG, actual is AES-256-GCM | Clarify |
| tasks/celery-tasks.md | deliver_webhook_task | Missing dispatch to deliver_single_webhook_task | Document subtask |
| tasks/celery-tasks.md | Error Handling table | Claims webhook task never retries — outdated | Update |
| infrastructure/webhooks.md | Event Types (line 119) | Lists `post.created` — does not exist | Replace with `post.unpublished` |

## Prune Candidates

**None.** All 34 architecture documents are grounded in real codebase modules. No document:
- References source files that don't exist
- Has >50% wrong claims
- Documents a removed feature
- Is a duplicate of another doc
- References exclusively deprecated APIs

The documentation is in better shape than the review plan anticipated. Previous implementation waves (A-F, 43 items) and the May 28 Wave 1 fixes addressed most major discrepancies.

## Recommended Actions

| # | Priority | Action | Doc |
|---|----------|--------|-----|
| 1 | High | Fix model count from 20/19 to 17 | `overview.md` |
| 2 | High | Add `deliver_single_webhook_task` documentation and update dispatch pattern | `tasks/celery-tasks.md` |
| 3 | High | Replace `post.created` with `post.unpublished` in event types | `infrastructure/webhooks.md` |
| 4 | Medium | Add pages, series, tags API endpoints | `routes/api-routes.md` |
| 5 | Medium | Add `encryption.py` to services overview | `services/overview.md` |
| 6 | Medium | Add `ApiToken` to models overview table | `core/models.md` |
| 7 | Medium | Remove or mark review plan links as pending | `overview.md` |
| 8 | Low | Fix broken `routes/overview.md` link in See Also | `core/app-factory.md` |
| 9 | Low | Clarify `.gpg` extension is AES-256-GCM, not GPG | `services/backup.md` |
| 10 | Low | Add missing Python modules to directory structure | `overview.md` |
| 11 | Low | Verify/update stale line number references across all docs | Multiple |

## Documentation Health Metrics

| Metric | Value |
|--------|-------|
| Total architecture docs | 34 |
| Need major rewrite | 0 |
| Need minor fixes | 8 |
| Fine as-is | 26 |
| Prune candidates | 0 |
| Missing docs for existing modules | ~8 (backup_integrity, transaction, csv_utils, base62, validators, cli, page_view_buffer, markdown_config) |
