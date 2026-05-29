# Architecture Prune Recommendations

**Generated:** 2026-05-29
**Purpose:** Identify and propose actions for stale, missing, or superseded architecture documents

---

## Missing Module Reviews

**RESOLVED:** Both previously missing reviews now exist:

| File | Module | Status |
|------|--------|--------|
| `plans/frontend_review.md` | Frontend | NOW EXISTS -- fully reviewed with 135 findings |
| `plans/deployment_review.md` | Deployment | NOW EXISTS -- fully reviewed with 235 findings |

All 10 module reviews are now complete:
1. `plans/core_review.md` -- EXISTS
2. `plans/routes_review.md` -- EXISTS
3. `plans/services_review.md` -- EXISTS
4. `plans/tasks_review.md` -- EXISTS
5. `plans/infrastructure_review.md` -- EXISTS
6. `plans/testing_review.md` -- EXISTS
7. `plans/frontend_review.md` -- NOW EXISTS
8. `plans/deployment_review.md` -- NOW EXISTS
9. `plans/overview_review.md` -- Cross-reference review EXISTS
10. `plans/architecture_prune.md` -- This document

---

## Stale Doc References (Broken Links)

**PREVIOUSLY FALSE POSITIVES:** The "broken links" in the prior version were incorrectly flagged. All referenced files exist:

| Doc | Line | Claimed Broken Reference | Actual Status |
|-----|------|------------------------|---------------|
| `architecture/deployment/security.md` | 103-105 | `../core/app-factory.md`, `../core/models.md` | BOTH EXIST (architecture/core/app-factory.md, architecture/core/models.md) |
| `architecture/deployment/cicd.md` | 77 | `../testing/test-suite.md` | EXISTS (architecture/testing/test-suite.md) |

---

## Stale/Factual Errors in Architecture Docs

### HIGH severity -- False claims in docs

| Doc | Line | False Claim | Actual Truth | Source |
|-----|------|-------------|-------------|--------|
| `architecture/testing/test-suite.md` | 113 | "E2E tests require pytest-playwright, which is **not** in committed requirements files" | playwright>=1.58.0 and pytest-playwright>=0.7.0 ARE in requirements.txt lines 18-19 | testing_review.md:70 |
| `architecture/testing/test-suite.md` | 190-196 | "E2E conftest creates its own session-scoped app fixture" | e2e/conftest.py does NOT define `app` fixture; relies on import chain from main conftest | testing_review.md:71,93 |

### MEDIUM severity -- Incomplete/outdated documentation

| Doc | Issue | Missing/Incorrect | Source |
|-----|-------|-------------------|--------|
| `architecture/testing/test-suite.md` | `ensure_buffer_disabled` location | Doc says it's in conftest.py but it's only in shared_fixtures.py (imported via `*`) | testing_review.md:65-66 |
| `architecture/testing/test-suite.md` | `db` fixture scope in benchmarks | Doc says "function" but benchmarks conftest.py:38-39 shows session-scoped | testing_review.md:67 |
| `architecture/testing/test-suite.md` | `mock_email` description | Doc says it "composes" mock_render and mock_smtp but it's a no-op that just yields | testing_review.md:69 |
| `architecture/services/backup.md` | 140 | References `run_daily_backup()` at `app/scheduler.py:261` | Actual at line 262 (off by 1); implementation at app/services/backup.py:150 | services_review.md:39 |
| `architecture/infrastructure/webhooks.md` | 116-118 | Line references for `deliver_webhook_task` and `deliver_single_webhook_task` | deliver_single_webhook_task is at line 234, not 233 (off by 1) | infrastructure_review.md:70 |
| `architecture/tasks/scheduler.md` | 64-68 | Celery queue line numbers inaccurate | deliver_webhook_task:194, deliver_single_webhook_task:233 (correct) | tasks_review.md:54-56 |

---

## Conflicting Module Boundaries

| Issue | Description | Evidence |
|-------|-------------|----------|
| Search straddles Infrastructure and Services | `overview.md` shows search under Infrastructure with `app/search.py`, but `app/services/search/__init__.py` (SearchProvider ABC) is listed under Services. The `app/services/search/` wraps `app/search.py`, creating confusion about which layer owns search. | overview_review.md:89-90 |
| `app/tag_cache.py` not in any module table | Directory structure shows it; Discrete Modules table omits it | overview_review.md:108-109 |
| `app/middleware/rate_limit.py` not in module table | Shows in directory structure under app/middleware/ but not in Core Application or Security module tables | overview_review.md:111-112 |
| SSRF protection source mismatch | Overview lists SSRF under Security sources but omits `app/utils.py`; utils.py is included in directory structure but not in Infrastructure source column | overview_review.md:94-95, 102-103 |
| `app/csrf.py` missing from Security sources | Overview says "Sliding window tokens (5 valid)" but doesn't list the actual CSRF implementation file | overview_review.md:98-100 |
| Redis diagram ambiguity | Overview shows two separate Redis boxes ("Broker + Cache" and "Rate Limits") but code uses single REDIS_URL for all three purposes | overview_review.md:82 |

---

## Prune Candidates

### Docs needing significant factual corrections

| Doc | Issue | Proposed Action |
|-----|-------|-----------------|
| `architecture/testing/test-suite.md` | Two false claims (playwright not in requirements, E2E app fixture) and several inaccurate fixture descriptions | REWRITE sections 113-117 and 190-196 with correct information |
| `architecture/frontend/static-assets.md` | Login template asset loading inconsistency (url_for vs vite_asset), Prism CSS loaded via JS bypasses vite_asset, marked.min.js outside Vite | Add section documenting these inconsistencies; consider adding action items for code fixes |

### Docs needing partial updates

| Doc | Issue | Proposed Action |
|-----|-------|-----------------|
| `architecture/overview.md` | Missing: Vite build requirement, multi-container APScheduler warning, backup encryption key validation behavior, Python version mismatch (dev 3.14 vs prod 3.12), health check start_period, E2E test dependency chain, login template CDN inconsistency, Prism CSS CDN bypass | Add sections for Vite build requirement, Python version alignment, health check timing, E2E dependency clarification |
| `architecture/infrastructure/webhooks.md` | Hardcoded line numbers (tasks.py:194, 233) become stale quickly; `_update_delivery_status` described as working correctly but code has bug | Replace line numbers with function names; add note about delivery_status tracking limitation |
| `architecture/deployment/docker.md` | APScheduler multi-container limitation documented but no detection/alerting mechanism; backup encryption key can silently fall back to unencrypted | Add section on detection/alerting for APScheduler races; clarify encryption key validation |
| `architecture/deployment/security.md` | Rate limiting config is in nginx.conf (not blog.conf) -- minor location discrepancy | Clarify rate limiting zone location |

### Previously flagged but now resolved

| Doc | Issue | Status |
|-----|-------|--------|
| `architecture/frontend/templates.md` | Missing partial templates | frontend_review.md confirmed all templates exist; this was not a prune issue |
| `architecture/frontend/static-assets.md` | Font weight claims | frontend_review.md:58-61 verified all font files present |

---

## Known Bugs Too Significant to Prune

These are **code bugs** surfaced during review. The architecture docs described intended behavior; the bugs are in implementation:

| Bug | Module | Severity | Code Location | Impact |
|-----|--------|----------|---------------|--------|
| `_update_delivery_status()` always reports "delivered" | Tasks/Infrastructure | HIGH | tasks.py:311-330 | Webhook delivery status misleading; checks dispatcher's event.delivered (set BEFORE individual deliveries) not per-webhook success |
| APScheduler multi-worker race condition | Tasks/Deployment | HIGH | scheduler.py:3-8 | FileLock with timeout=0 only works single-node; multi-container = duplicate job execution |
| E2E test password inconsistency | Testing | HIGH | conftest.py:100 ("testpassword") vs e2e/conftest.py:44 ("test-password") | Tests may fail inconsistently |
| E2E `app` fixture missing | Testing | HIGH | tests/e2e/conftest.py (no app fixture defined) | `pytest tests/e2e/` alone fails; requires import chain |
| Backup encryption silently disabled | Deployment | HIGH | backup.py:103-106 | BACKUP_ENCRYPTION_KEY set but cannot be loaded -> backup proceeds unencrypted, no error |
| APScheduler FileLock not enforced against scaling | Deployment | HIGH | docker-compose.yml:60 | No warning prevents `docker-compose up -d --scale celery=3` causing duplicate job execution |
| `get_storage()` singleton not thread-safe | Infrastructure | MEDIUM | storage.py:260-265 | Multiple threads could create multiple storage instances |
| Admin password hardcoded differently in E2E vs unit tests | Testing | MEDIUM | tests/conftest.py vs tests/e2e/conftest.py | `testpassword` vs `test-password` - different passwords |
| SESSION_IP_BINDING enforcement uncertain | Core | MEDIUM | core_review.md:114 | IP binding config exists but enforcement logic appears missing from before_request_handler |
| Prism CSS loaded via JS bypasses vite_asset/CDN | Frontend | MEDIUM | main.js:102 | If CDN_URL configured, Prism CSS won't include it |

---

## Missing Documentation (New from All Reviews)

These are significant gaps where architecture docs are silent on important behavior:

| Gap | Doc(s) That Should Cover It | Source |
|-----|----------------------------|--------|
| Vite build must run before production (manifest.json required) | overview.md, frontend docs | frontend_review.md:117, overview_review.md:115-116 |
| APScheduler multi-container detection/alerting mechanism | docker.md, scheduler.md | deployment_review.md:130-133 |
| Backup encryption key can come from config.toml (not just env var) | docker.md | deployment_review.md:135-139 |
| Celery scaling warning (concurrency=1 is per-container, not total) | docker.md | deployment_review.md:141-144 |
| Health check start_period (10s before container marked healthy) | docker.md, overview.md | deployment_review.md:146-149, overview_review.md:176-177 |
| E2E test depends on docker-build but NOT frontend-build | ci.yml docs | deployment_review.md:219-220 |
| Redis health dependency missing for backup service | docker-compose.yml docs | deployment_review.md:223 |
| Tag/series RSS/Atom/JSON feeds undocumented | rss-feeds.md | routes_review.md:107-109 |
| API error response codes (401,403,404,409,429,503) undocumented | api-routes.md | routes_review.md:128-129 |
| Rate limits for pages/series/tags API endpoints undocumented | api-routes.md | routes_review.md:117-118 |
| `SESSION_IP_BINDING` not confirmed implemented | overview.md, core docs | core_review.md:114 |
| Silent FTS initialization failure | overview.md, core docs | core_review.md:108 |
| `extract_snippet()` and `init_fts()` missing from search.md | search.md | services_review.md:52 |
| Private `_encrypt_backup_file()` undocumented | backup.md | services_review.md:46 |
| Exception hierarchy for encryption modules undocumented | backup.md, webhooks.md | services_review.md:47-50 |
| `WEBHOOK_TIMEOUT` default not documented | celery-tasks.md | tasks_review.md:72 |
| Newsletter three-way path (scheduler -> email.py -> Celery task) not shown | overview.md | tasks_review.md:76 |
| S3StorageBackend error differentiation (not_found vs error) | storage.md | infrastructure_review.md:92-94 |
| SEARCH_PROVIDER config validation (unknown value falls back silently) | search.md | infrastructure_review.md:96-98 |
| Webhook SSRF DNS time-of-check gap | webhooks.md | infrastructure_review.md:103-106 |

---

## Summary

- **No docs to DELETE** outright
- **No docs to MERGE** at this time
- **1 doc to REWRITE significantly**: `architecture/testing/test-suite.md` (two factually false claims confirmed by testing_review.md)
- **2 docs to REWRITE partially**: `architecture/overview.md` (missing Vite build req, APScheduler multi-container, Python version, health check timing, E2E deps); `architecture/infrastructure/webhooks.md` (line references stale, delivery_status bug not documented)
- **0 missing reviews** -- all 10 reviews complete
- **Directory cleanup**: `docs/` tree appears to be a separate documentation mirror of `architecture/`; verify if intentional duplication
- **Key new findings from frontend/deployment reviews**:
  - `test-suite.md` contains confirmed false claims (playwright not in requirements, E2E app fixture self-defined)
  - APScheduler FileLock limitation is more severe than previously noted (deployment_review.md adds that no enforcement/warning exists in docker-compose.yml)
  - Backup encryption can silently fall back to unencrypted (deployment_review.md)
  - Vite production build requirement was never documented (frontend_review.md)
  - Python version mismatch (dev.sh 3.14 vs Dockerfile 3.12) is a dev/prod inconsistency (deployment_review.md)
