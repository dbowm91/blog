# Plans Module Override

## Overview

This module contains the implementation plan history and completed items reference.

## Plan Status

**COMPLETED** - All implementation plan items have been completed and verified (May 30, 2026).

The implementation plan `plans/plan.md` has been pruned. All items from the architecture review (90+ items across 6 waves) are now documented in the codebase and AGENTS.md notes.

## Architecture Review Findings (May 31, 2026)

A fresh architecture review was conducted. Findings are in `plans/*_review.md` and `plans/architecture_prune.md`.

### Key Action Items from Review

| Priority | Count | Description |
|----------|-------|-------------|
| HIGH | ~30 | Critical doc/code discrepancies across all modules |
| MEDIUM | ~50 | Documentation gaps, line reference drift, phantom claims |
| LOW | ~30 | Minor improvements, dead code, style issues |

### Pruning Recommendations

- **3 docs to REWRITE:** testing/test-suite.md, routes/public-routes.md, routes/admin-routes.md
- **2 docs to MERGE/FIX:** infrastructure/overview.md, services/overview.md
- **11 phantom claims** across search.md, email.md, storage.md, docker.md, backup.md, api-routes.md, configuration.md
- **8 docs with stale line references** (drift >5 lines)

### Notable Source Code Bugs Found

- RSS cache invalidation incomplete (atom/json feeds not invalidated)
- Global rate limit bypass via X-Forwarded-For spoofing
- `decrypt_backup_file()` missing RuntimeError catch
- `S3StorageBackend.save()` lacks error handling
- Admin Prism CSS hardcoded to okaidia (ignores user setting)
- Widespread test password inconsistency ("testpassword" vs "test-password")

## Historical Context

The plan contained ~90 items across 6 waves from architecture reviews conducted May 29, 2026:

- **Wave 1**: Critical code bugs (6 items) - APScheduler race, webhook status, E2E fixtures, backup encryption, Python version, thread-safe storage
- **Wave 2**: Documentation corrections (3 items) - test-suite rewrite, module boundaries, stale line references
- **Wave 3**: Missing documentation (13 items) - APScheduler detection, Vite build, encryption keys, feeds, API errors, rate limits, newsletter path, health check, session IP binding, FTS init, webhook SSRF, celery scaling, E2E race
- **Wave 4**: Frontend fixes (2 items) - login template assets, Prism CSS CDN
- **Wave 5**: Source cleanup (5 items) - dead imports, decrypt_backup_file export, session.remove(), metrics auth, S3 error differentiation
- **Wave 6**: Security hardening (2 items) - LOGIN_FAILURE_DELAY min, comment rate limit bypass

All items were verified complete before removal from plan.md.

## Key Files for Reference

| Item | Location |
|------|----------|
| APScheduler warning | `docker-compose.yml:56-58` |
| Webhook partial_failure | `app/tasks.py:312-341` |
| E2E password consistency | `tests/conftest.py:100`, `tests/e2e/conftest.py:7,79` |
| Backup encryption warning | `app/services/backup.py:68-71,107-110` |
| Python 3.12 alignment | `scripts/dev.sh:11`, `Dockerfile:1` |
| Thread-safe storage | `app/storage.py:270-277` |
| LOGIN_FAILURE_DELAY min | `app/config.py:148` |
| Prism CSS via vite_asset | `app/static/js/main.js:102`, `app/templates/base.html:2` |

## Maintenance Notes

When updating code that affects documented behavior:
1. Update the relevant AGENTS.override.md for that module
2. If adding new behavior, consider updating AGENTS.md Important Notes
3. If documentation becomes stale, update architecture docs or add a note in agent-maintainer-notes.md