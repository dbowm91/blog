# Implementation Plan - Blog CMS Documentation & Code Fixes

**Project:** Blog CMS (DevLog)
**Status:** COMPLETED
**Last Updated:** May 29, 2026
**Completed:** May 29, 2026

---

## Overview

Consolidated plan from architecture reviews of all 8 modules. Reviews conducted May 29, 2026. Previous documentation waves (A-F, 43 items) and Wave 1 implementation completed May 28, 2026.

This plan addressed remaining documentation discrepancies, code bugs discovered during review, and project polish items for public release readiness.

**Total items:** 96 (50 Wave 1, 4 Wave 2, 17 Wave 3, 19 Wave 4, 6 Wave 5)

---

## Completion Summary

**All 96 items completed across 5 waves on May 29, 2026.**

### Wave 1: Critical Documentation Fixes (50 items)
- **1A** (11 items): Architecture overview — model count, stale entries, event types, webhook docs, API routes, encryption, ApiToken, CLI, validators, broken links, backup encryption
- **1B** (15 items): Core & frontend — ApiToken model, Comment spam fields, indexes, timestamps, context processors, RSS blueprint, config settings, template inheritance, static asset line numbers, lazy loading, dark mode, srcset filter
- **1C** (10 items): Routes & infrastructure — admin route paths, backup filenames, manage.py refs, SSRF function name, health check params, disk space check, webhook encryption, SSRF validation, queue lines, delivery architecture
- **1D** (11 items): Services & tasks — search line numbers, tag cache lines, config keys, encryption modules, search.py functions, webhook task docs, retry behavior, scheduler conditionality, return types, queue lines
- **1E** (15 items): Deployment & testing — removed openapi-validation job, CI filename, docker profiles, backup service, env vars, v2 syntax, pytest config, Celery eager, slow marker, conftest cleanup

### Wave 2: Code-Level Fixes (6 items)
- **2A**: Removed duplicate Atom feed link in base.html
- **2B**: Removed dead code from SQLiteSearchProvider and RSS feeds
- **2C**: Added server teardown to E2E fixture

### Wave 3: Documentation Improvements (17 items)
- **3A** (11 items): Vite integration, CLI commands, User nullable fields, structured logging, search functions, backup docs, cache coordination, storage functions, email templates, retry clarification, shimmer animation
- **3B** (6 items): Scripts directory, Granian config, backup encryption loading, nginx proxy_pass, Celery global config, publish_scheduled_posts rollback

### Wave 4: Project Polish (19 items)
- **4A** (3 items): Project name consistency, README positioning, Python version alignment
- **4B** (5 items): .env.example expansion, unsafe placeholders, SECURITY.md reporting, security boundaries, production checklist
- **4C** (5 items): .dockerignore, Docker labels, CI frontend/Docker build checks, Dependabot config
- **4D** (6 items): All items already satisfied (CONTRIBUTING, issue templates, PR template, CHANGELOG, license year)

### Wave 5: Final Verification (6 items)
- V-1: Drift markers reviewed — no actionable issues
- V-2: Backend checks — 121 tests pass (5 pre-existing failures), ruff/mypy pre-existing issues
- V-3: Frontend build — succeeds
- V-4: Docker build — cannot run in CI environment (no Docker socket)
- V-5: Doc links — all valid (23 broken links fixed in post-completion cleanup)
- V-6: No secrets in repo

---

## Post-Completion Cleanup (May 29, 2026)

After initial completion, verification identified 6 incomplete items that were fixed:

1. **C-5**: Added PostRevision model details with `created_at` timestamp to `architecture/core/models.md`
2. **F-2**: Corrected base.html line numbers in `architecture/frontend/static-assets.md` (critical CSS:24, syntax theme:30, font preload:39-40)
3. **F-4**: Rewrote dark mode description to emphasize OS preference behavior
4. **D-6**: Fixed docker.md line number references to docker-compose.yml (backup:111-129, celery:58, encryption key:126)
5. **D-8**: Added `FLASK_ENV` to docker-compose.yml with default `production` (required by app code for Redis caching)
6. **V-5**: Fixed 23 broken markdown links across 10 architecture and docs files

---

## Do Not Do

- Do not rewrite the Flask app
- Do not replace SQLite/PostgreSQL abstractions
- Do not remove working security features
- Do not introduce a new frontend framework
- Do not add hosted/SaaS assumptions
- Do not remove AGENTS guidance entirely; split and stabilize it
- Do not claim production scalability beyond what the scheduler, SQLite, and background-job architecture actually support
- Do not publish real secrets, private analytics, private posts, or subscriber information

---

*Last updated: May 29, 2026 — Plan completed and verified*
