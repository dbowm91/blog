# Implementation Plan - Blog CMS Architecture Documentation & Code Fixes

**Project:** Blog CMS (DevLog)
**Status:** PENDING
**Last Updated:** May 29, 2026

---

## Overview

Consolidated plan from architecture reviews of all 8 modules. Reviews conducted May 29, 2026. Previous documentation waves (A-F, 43 items) and Wave 1 implementation completed May 28, 2026.

This plan addresses remaining documentation discrepancies, code bugs discovered during review, and project polish items for public release readiness.

---

## Wave 1: Critical Documentation Fixes (Parallelizable)

All items in Wave 1 are independent and can be executed in parallel by separate sub-agents.

### Wave 1A: Architecture Overview Fixes
| ID | Priority | Description | File | Verified |
|----|----------|-------------|------|----------|
| A-1 | high | Fix model count: "20 models" and "19 models" → "17 models" | `architecture/overview.md:99,312` | ✓ |
| A-2 | high | Remove stale `app/services/tag_cache.py` from directory structure (file is at `app/tag_cache.py`) | `architecture/overview.md:389` | ✓ |
| A-3 | high | Replace `post.created` with `post.unpublished` in event types table | `architecture/infrastructure/webhooks.md:119` | ✓ |
| A-4 | high | Add `deliver_single_webhook_task` documentation and update dispatch pattern | `architecture/tasks/celery-tasks.md` | ✓ |
| A-5 | med | Add missing API endpoints (pages, series, tags) to api-routes.md | `architecture/routes/api-routes.md` | ✓ |
| A-6 | med | Add `encryption.py` to services overview table | `architecture/services/overview.md` | ✓ |
| A-7 | med | Add `ApiToken` to models overview table | `architecture/core/models.md` | ✓ |
| A-8 | med | Add `app/cli.py` to directory structure and Core section component table | `architecture/overview.md:86-91,306-333` | ✓ |
| A-9 | med | Add `app/validators.py` to Core section component table | `architecture/overview.md:86-91` | ✓ |
| A-10 | low | Fix broken `routes/overview.md` link in See Also | `architecture/core/app-factory.md:141` | ✓ |
| A-11 | low | Clarify `.gpg` extension is AES-256-GCM, not GPG | `architecture/services/backup.md:97` | ✓ |

### Wave 1B: Core & Frontend Documentation Fixes
| ID | Priority | Description | File | Verified |
|----|----------|-------------|------|----------|
| C-1 | high | Add `ApiToken` model to models.md details section | `architecture/core/models.md` | ✓ |
| C-2 | high | Add `is_spam`, `spam_score`, `created_at` fields to Comment model docs | `architecture/core/models.md` | ✓ |
| C-3 | high | Add `ix_comments_is_spam` index to Comment index table | `architecture/core/models.md` | ✓ |
| C-4 | high | Add `canonical_url` to context processors list | `architecture/core/app-factory.md` | ✓ |
| C-5 | med | Document `created_at`/`updated_at` on Post, Page, Comment, PostRevision, SiteSettings | `architecture/core/models.md` | ✓ |
| C-6 | med | Fix rss blueprint prefix description (routes are top-level, not prefixed) | `architecture/core/app-factory.md` | ✓ |
| C-7 | med | Add `ADMIN_RATE_LIMITS` to configuration.md | `architecture/core/configuration.md` | ✓ |
| C-8 | med | Add comment settings (min/max length, rate limits, spam words) to configuration.md | `architecture/core/configuration.md` | ✓ |
| C-9 | med | Add `ANALYTICS_DAYS_MIN/MAX`, `PAGE_VIEW_BUFFER_SIZE` to configuration.md | `architecture/core/configuration.md` | ✓ |
| C-10 | med | Document `ix_admin_sessions_user_id` index in AdminSession section | `architecture/core/models.md` | ✓ |
| F-1 | high | Fix template inheritance diagram to show four base templates | `architecture/frontend/templates.md` | ✓ |
| F-2 | high | Fix line number references for critical CSS, font preload, syntax theme, vite functions | `architecture/frontend/static-assets.md` | ✓ |
| F-3 | med | Rewrite lazy loading tier 1 description to clarify JS defers to native browser handling | `architecture/frontend/static-assets.md` | ✓ |
| F-4 | med | Fix dark mode default description to note it follows OS preference | `architecture/frontend/static-assets.md` | ✓ |
| F-5 | med | Add `post_image_srcset` filter implementation details | `architecture/frontend/templates.md` | ✓ |

### Wave 1C: Routes & Infrastructure Documentation Fixes
| ID | Priority | Description | File | Verified |
|----|----------|-------------|------|----------|
| R-1 | high | Fix post list route path: `GET /admin/<int:page>` → `GET /admin/` with query param | `architecture/routes/admin-routes.md:96` | ✓ |
| R-2 | high | Fix backup route URLs: add `<filename>` path parameters | `architecture/routes/admin-routes.md:160-163` | ✓ |
| R-3 | high | Fix post delete/preview file reference: `manage.py` → `posts/manage.py` | `architecture/routes/admin-routes.md:85,89` | ✓ |
| I-1 | high | Fix `is_safe_url` → `is_safe_webhook_url` name and code block | `architecture/infrastructure/overview.md:89` | ✓ |
| I-2 | high | Fix `?detailed=1` → `?detailed=true` and document `?secret=` requirement | `architecture/infrastructure/overview.md:17` | ✓ |
| I-3 | high | Fix `disk_space` check description (10% free, not 100MB) | `architecture/infrastructure/overview.md:26` | ✓ |
| I-4 | med | Document `app/webhook_encryption.py` in webhooks.md | `architecture/infrastructure/webhooks.md` | ✓ |
| I-5 | med | Document `is_safe_webhook_url()` full validation logic | `architecture/infrastructure/webhooks.md` | ✓ |
| I-6 | med | Update queue line numbers in webhooks.md | `architecture/infrastructure/webhooks.md` | ✓ |
| I-7 | med | Document two-level webhook delivery architecture | `architecture/infrastructure/webhooks.md` | ✓ |

### Wave 1D: Services & Tasks Documentation Fixes
| ID | Priority | Description | File | Verified |
|----|----------|-------------|------|----------|
| S-1 | high | Update `search.md` line number references (11 functions, drift -1 to -7) | `architecture/services/search.md` | ✓ |
| S-2 | high | Update `tag_cache.md` invalidation call line numbers (15 references) | `architecture/services/tag_cache.md` | ✓ |
| S-3 | high | Remove `_SQLITE_MAX_VARS` from config keys section; add `FTS_RESULT_LIMIT` | `architecture/services/search.md` | ✓ |
| S-4 | med | Correct `tag_cache.md:30` — line 100 is import, not call (actual call at line 68) | `architecture/services/tag_cache.md` | ✓ |
| S-5 | med | Add encryption modules to overview.md services table | `architecture/overview.md` | ✓ |
| S-6 | med | Add `app/search.py` standalone functions to overview.md | `architecture/overview.md` | ✓ |
| T-1 | high | Document `deliver_single_webhook_task` and update `deliver_webhook_task` dispatch pattern | `architecture/tasks/celery-tasks.md` | ✓ |
| T-2 | high | Fix error handling table and Note paragraph for webhook retry behavior | `architecture/tasks/celery-tasks.md` | ✓ |
| T-3 | med | Add conditional note for `send_daily_newsletter` in jobs table | `architecture/tasks/scheduler.md` | ✓ |
| T-4 | low | Fix `init_scheduler` return type to `Optional["BackgroundScheduler"]` | `architecture/tasks/scheduler.md` | ✓ |
| T-5 | low | Fix `images` queue line number (30, not 28) in Celery Queue Reference | `architecture/tasks/scheduler.md` | ✓ |

### Wave 1E: Deployment & Testing Documentation Fixes
| ID | Priority | Description | File | Verified |
|----|----------|-------------|------|----------|
| D-1 | high | Create missing `scripts/validate_openapi.py` or remove the CI job referencing it | `.github/workflows/ci.yml:64` | ✓ |
| D-2 | high | Fix CI workflow filename: `test.yml` → `ci.yml` | `architecture/deployment/cicd.md:1` | ✓ |
| D-3 | high | Add `openapi-validation`, `frontend-build`, `docker-build` jobs and `schedule` trigger to CI docs | `architecture/deployment/cicd.md:11-31` | ✓ |
| D-4 | high | Fix docker-compose profiles: clarify blog/celery/redis/nginx require `--profile production`, backup requires `--profile backup` | `architecture/deployment/docker.md:18` | ✓ |
| D-5 | med | Add `backup` service to Docker Services table | `architecture/deployment/docker.md:7-12` | ✓ |
| D-6 | med | Fix line number references: backup.py:24→23, docker-compose.yml:103→105, docker-compose.yml:50→52 | `architecture/deployment/docker.md` | ✓ |
| D-7 | med | Add missing env vars: `SQLALCHEMY_DATABASE_URI`, `API_KEY`, `SESSION_COOKIE_SECURE` | `architecture/deployment/docker.md:86-103` | ✓ |
| D-8 | med | Remove `FLASK_ENV` if unused or document its actual purpose | `architecture/deployment/docker.md:90` | ✓ |
| D-9 | med | Fix `docker-compose` → `docker compose` (v2 syntax) | `architecture/deployment/cicd.md` | ✓ |
| D-10 | med | Fix `pytest.ini` documentation to reflect actual content | `architecture/deployment/cicd.md:35-38` | ✓ |
| TS-1 | high | Fix pytest.ini reference → pyproject.toml | `architecture/testing/test-suite.md:79-84` | ✓ |
| TS-2 | high | Remove phantom `regular_user` and `post` fixtures | `tests/AGENTS.override.md:68-69` | ✓ |
| TS-3 | med | Remove duplicate `clean_analytics_cache` from conftest.py | `tests/conftest.py:179-186` | ✓ |
| TS-4 | med | Document Celery eager configuration in tests | `architecture/testing/test-suite.md` | ✓ |
| TS-5 | med | Document `slow` marker from pytest_configure | `architecture/testing/test-suite.md` | ✓ |

---

## Wave 2: Code-Level Fixes (Parallelizable after Wave 1)

These are actual code changes, not just documentation fixes. Each can be done independently.

### Wave 2A: Template & Frontend Code Fixes
| ID | Priority | Description | File | Verified |
|----|----------|-------------|------|----------|
| CF-1 | high | Fix duplicate Atom feed link in `base.html:24` (remove hardcoded link, keep block) | `app/templates/base.html:24` | ✓ |
| CF-2 | low | Add `admin/login_base.html` and `email/base_email.html` to template directory structure listing | `architecture/frontend/templates.md` | ✓ |

### Wave 2B: Dead Code Cleanup
| ID | Priority | Description | File | Verified |
|----|----------|-------------|------|----------|
| DC-1 | low | Remove dead state variables from `SQLiteSearchProvider.__init__()` | `app/services/search/sqlite.py:10-12` | ✓ |
| DC-2 | low | Investigate dead code in RSS feed functions (unused `utc_now().isoformat()` expressions) | `app/routes/rss.py:201,306,354,459,640` | ✓ |

### Wave 2C: Test Cleanup
| ID | Priority | Description | File | Verified |
|----|----------|-------------|------|----------|
| TC-1 | med | Remove duplicate `clean_analytics_cache` definition from conftest.py | `tests/conftest.py:179-186` | ✓ |
| TC-2 | low | Add server teardown to `app_server` fixture | `tests/e2e/conftest.py:26-60` | ✓ |

---

## Wave 3: Documentation Improvements (Can run in parallel with Wave 2)

New documentation to add for completeness.

### Wave 3A: Missing Model & Config Documentation
| ID | Priority | Description | File |
|----|----------|-------------|------|
| MD-1 | med | Document Vite integration and CLI commands in app-factory.md | `architecture/core/app-factory.md` |
| MD-2 | low | Add `nullable` constraints to User model field docs (email nullable=True) | `architecture/core/models.md` |
| MD-3 | low | Document structured logging, ProxyFix, and cache configuration | `architecture/core/app-factory.md` |
| MD-4 | low | Document `get_indexed_terms_fallback()` and `_escape_fts_term()` in search.md | `architecture/services/search.md` |
| MD-5 | low | Document service-level `run_daily_backup()` in backup.md | `architecture/services/backup.md` |
| MD-6 | low | Document `_invalidate_all_caches()` coordination in tag.md | `architecture/services/tag.md` |
| MD-7 | low | Document `extract_snippet()`, `init_storage()`, `storage_delete_file()` | `architecture/services/search.md`, `architecture/infrastructure/storage.md` |
| MD-8 | low | Add `base_email.html` to email templates list | `architecture/infrastructure/email.md` |
| MD-9 | low | Clarify `_send_email_with_retry` default (3) vs newsletter override (5) in email.md | `architecture/infrastructure/email.md` |
| MD-10 | low | Document `img-skeleton` shimmer animation in the lazy loading section | `architecture/frontend/static-assets.md` |
| MD-11 | low | Add `admin/login_base.html` and `email/base_email.html` to template directory structure listing | `architecture/frontend/templates.md` |

### Wave 3B: Missing Infrastructure Documentation
| ID | Priority | Description | File |
|----|----------|-------------|------|
| ID-1 | low | Document scripts/ directory (build_assets, dev.sh, update-assets, sync_backups) | `architecture/deployment/docker.md` or new doc |
| ID-2 | low | Document Granian worker count (4) and timeout (60s) | `architecture/deployment/docker.md` |
| ID-3 | low | Address backup container config.toml / encryption key loading | `docker-compose.yml` |
| ID-4 | low | Verify nginx proxy_pass 127.0.0.1 works with Docker networking | `nginx/conf.d/blog.conf` |
| ID-5 | low | Document Celery global config (`task_time_limit`, `worker_prefetch_multiplier`, etc.) | `architecture/tasks/celery-tasks.md` |
| ID-6 | low | Document `publish_scheduled_posts` rollback on FTS sync failure | `architecture/tasks/scheduler.md` |

---

## Wave 4: Project Polish for Public Release (Sequential, lower priority)

These items are from the improvements.md plan and should be done after documentation fixes.

### Wave 4A: Public Project Identity
| ID | Priority | Description |
|----|----------|-------------|
| P-1 | med | Establish consistent project name (DevLog) across repository |
| P-2 | med | Add positioning section and badges to README.md |
| P-3 | med | Align Python version documentation (3.12/3.13) across docs |

### Wave 4B: Environment & Security Polish
| ID | Priority | Description |
|----|----------|-------------|
| P-4 | med | Expand `.env.example` with all supported env vars |
| P-5 | med | Replace unsafe placeholders with generation commands |
| P-6 | med | Add concrete vulnerability reporting path to SECURITY.md |
| P-7 | med | Add "Security Boundaries" section to SECURITY.md |
| P-8 | med | Add production checklist to deployment docs |

### Wave 4C: Docker & CI Polish
| ID | Priority | Description |
|----|----------|-------------|
| P-9 | med | Add or improve `.dockerignore` |
| P-10 | med | Add Docker labels if useful |
| P-11 | med | Add frontend build check to CI |
| P-12 | med | Add Docker build check to CI |
| P-13 | low | Add Dependabot configuration |

### Wave 4D: Contribution & Release Hygiene
| ID | Priority | Description |
|----|----------|-------------|
| P-14 | low | Clean CONTRIBUTING.md (remove internal branch naming) |
| P-15 | low | Add issue templates (bug report, feature request) |
| P-16 | low | Add PR template |
| P-17 | low | Add CHANGELOG.md |
| P-18 | low | Update license year if appropriate |
| P-19 | low | Add repository About metadata and topics |

---

## Wave 5: Final Verification (After all other waves)

| ID | Priority | Description |
|----|----------|-------------|
| V-1 | high | Run repository-wide drift marker search |
| V-2 | high | Run backend checks (ruff, mypy, pytest) |
| V-3 | high | Run frontend checks (npm build) |
| V-4 | high | Run Docker build check |
| V-5 | med | Validate docs links |
| V-6 | med | Verify no secrets or private data |

---

## Dependency Graph

```
Wave 1A ──┐
Wave 1B ──┤
Wave 1C ──┼──→ Wave 2 (Code Fixes) ──→ Wave 5 (Verification)
Wave 1D ──┤         │
Wave 1E ──┘         └──→ Wave 3 (New Docs) ──┘
                                        │
                                        └──→ Wave 4 (Project Polish) ──→ Wave 5
```

**Parallelization Notes:**
- All Wave 1 sub-waves (A-E) can run simultaneously
- Wave 2 and Wave 3 can run in parallel after Wave 1 completes
- Wave 4 can start after Wave 2 completes (some items need code fixes)
- Wave 5 must run after all other waves complete

---

## Estimated Item Count

| Wave | Items | Estimated Effort |
|------|-------|------------------|
| Wave 1 | 50 | Medium (documentation edits) |
| Wave 2 | 4 | Low (small code changes) |
| Wave 3 | 17 | Medium (new documentation) |
| Wave 4 | 19 | Medium (project polish) |
| Wave 5 | 6 | Low (verification) |
| **Total** | **96** | |

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

*Last updated: May 29, 2026 — Plan created from consolidated architecture reviews*
