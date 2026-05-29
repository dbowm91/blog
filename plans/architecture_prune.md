# Architecture Prune Recommendations

**Generated:** 2026-05-29
**Purpose:** Identify and propose actions for stale, missing, or superseded architecture documents

---

## Missing Module Reviews

The following module review files were expected to be created but are missing:

| Missing File | Module | Status |
|-------------|--------|--------|
| `plans/frontend_review.md` | Frontend | Not written to disk despite subagent completing |
| `plans/deployment_review.md` | Deployment | Not written to disk despite subagent completing |

**Action:** Re-run or manually create these review files using findings from subagent results (available in task output history).

---

## Stale Doc References (Broken Links)

These architecture docs reference files that do not exist:

| Doc | Line | Broken Reference | Proposed Action |
|-----|------|-----------------|-----------------|
| `architecture/deployment/security.md` | 103-105 | `../core/app-factory.md`, `../core/models.md` | Create stub files or remove references |
| `architecture/deployment/cicd.md` | 77 | `../testing/test-suite.md` | Create stub file or remove reference |

---

## Conflicting Module Boundaries

| Issue | Description |
|-------|-------------|
| Search straddles Infrastructure and Services | `overview.md` shows search under Infrastructure with `app/search.py`, but `app/services/search/__init__.py` (SearchProvider ABC) is listed under Services. `app/tag_cache.py` not listed in any module table despite being in the directory structure. |
| SSRF protection source mismatch | Overview lists SSRF under Security sources but omits `app/utils.py`; includes it in directory structure under "Utilities". |

---

## Prune Candidates

Based on review findings, no architecture docs are purely stale (entirely wrong or referencing removed features). However, the following docs have significant gaps:

| Doc | Issue | Proposed Action |
|-----|-------|-----------------|
| `architecture/frontend/templates.md` | Missing partial templates (`_error.html`, `_post_content.html`, `_sidebar.html`, `public/comments.html`, `macros.html`) not documented | Add missing template documentation |
| `architecture/frontend/static-assets.md` | Font weight claims (Inter 300-700, JetBrains Mono 400,500) unverified against actual font files | Verify and correct or remove claims |
| `architecture/deployment/security.md` | Multiple broken cross-references to non-existent docs | Fix references or remove sections |
| `architecture/deployment/cicd.md` | Broken reference to `../testing/test-suite.md` | Fix reference or remove section |
| `architecture/infrastructure/webhooks.md` | Hardcoded line numbers become stale quickly | Consider removing line-specific references |

---

## Known Bugs Too Significant to Prune

These bugs were surfaced during review and indicate the architecture docs are actively maintained but have some inaccurate claims:

| Bug | Module | Severity |
|-----|--------|----------|
| `_update_delivery_status()` always reports "delivered" | Tasks/Infrastructure | HIGH |
| APScheduler multi-worker race condition (FileLock single-node only) | Tasks | HIGH |
| E2E test password inconsistency (`testpassword` vs `test-password`) | Testing | HIGH |
| E2E `app` fixture missing, fails in isolation | Testing | HIGH |

These bugs are **code issues**, not documentation issues. The architecture docs accurately described the intended behavior; the bugs are in implementation.

---

## Summary

- **No docs to DELETE** outright
- **No docs to MERGE** at this time
- **2 docs to REWRITE partially**: `architecture/deployment/security.md` (broken refs), `architecture/deployment/cicd.md` (broken refs)
- **2 missing reviews** that must be completed: `frontend_review.md`, `deployment_review.md`
- **Directory cleanup**: No orphan architecture files found
