# Agent Guidelines

Quick reference for AI agents working on this codebase.

## Agent Override Convention

This codebase uses a **module-level override system** for agent context. Each module (directory with a specific purpose) may contain an `AGENTS.override.md` file that provides specialized handling instructions for that module.

When an agent operates within a module, it should:
1. Read the root `AGENTS.md` for general guidance
2. Check for `AGENTS.override.md` in the current module for specialized handling
3. Override files take precedence over root-level guidance when working within that module

## Module Override Files

| Module | Override File | Purpose |
|--------|---------------|---------|
| App Core | `app/AGENTS.override.md` | Flask app, models, extensions, core utilities |
| Routes | `app/routes/AGENTS.override.md` | Public routes, API, RSS, services |
| Admin Routes | `app/routes/admin/AGENTS.override.md` | Admin dashboard, post/subscriber/user management |
| Frontend | `app/static/AGENTS.override.md` | JS/CSS assets, Vite build |
| Templates | `app/templates/AGENTS.override.md` | Jinja2 templates, filters |
| Tests | `tests/AGENTS.override.md` | Testing patterns, fixtures |
| OpenCode Config | `.opencode/AGENTS.override.md` | Agent tool configuration |
| Documentation | `docs/AGENTS.override.md` | Documentation structure |
| Scripts | `scripts/AGENTS.override.md` | Shell scripts, DevOps |
| Services | `app/services/AGENTS.override.md` | Backup, slug, serialization, tag services |

## Structure Convention

When adding agent guidance for a specific module:
1. Create `AGENTS.override.md` inside that module directory
2. Do not create a separate "agents" directory
3. Override files should be focused on module-specific concerns
4. Update this index when adding new override files

## Codebase Structure Reference

Important actual file locations (verify before assuming):

| Item | Actual Location |
|------|-----------------|
| API routes | `app/routes/api/` (PACKAGE with posts.py, subscribers.py, stats.py, auth.py) |
| Validators | `app/validators.py` (NOT `app/core/validators.py`) |
| Backup logic | `app/services/backup.py` (centralized service) |
| Admin Audit Log model | `app/models.py:397-417` |
| PostRevision model | `app/models.py:173` |
| User model `__repr__` | `app/models.py:63-64` |
| Comment model | `app/models.py` |
| Services | `app/services/` (backup, slug, serialization, tag) |

## Security & Privacy Rules

- **Log ID, not Username**: When logging user actions or system events, always use `user.id`. Never log raw User objects or usernames to prevent PII leakage.
- **Credential Protection**: Never log `SECRET_KEY`, `ADMIN_PASSWORD`, or API keys.

## High-Risk Files (Error Handling)

These files previously used broad `except Exception` clauses. Most have been replaced with specific exceptions (SQLAlchemyError, OSError, ValueError) per CQ-3, but some remain pending (see Wave 1 in `plans/plan.md`):
- `app/routes/public/meta.py` (Verified fixed - CQ-3)
- `app/email.py` (Verified fixed - CQ-3)
- `app/backup_integrity.py` (Verified fixed)
- `app/webhooks.py` (Verified fixed)
- `app/tasks.py` (Verified fixed)
- `app/page_view_buffer.py` (Verified fixed)

## Wave 1 Completed Items (May 2026)

Security remediations completed:
- **S-1 (FTS SQL Injection):** Fixed `app/search.py:get_search_snippets()` - use bindparam with tuple for IN clause
- **S-2 (CSS Injection):** Replaced regex with tinycss2 parser + allowlist in `app/utils.py:sanitize_css()`
- **S-3 (Webhook Encryption):** Created `app/webhook_encryption.py` with AES-256-GCM
- **CQ-3 (Exception Handling):** Fixed in `meta.py` and `email.py`

Test stability improvements:
- Replaced `db.session.refresh()` with `db.session.expire() + re-query` in 6 test files
- Removed duplicate `mock_image_processing` fixture from conftest.py
- Page view buffer properly disabled in test configuration

## Wave 2 Completed Items (May 2026)

Performance improvements:
- **N+1 Queries:** Fixed in `app/routes/admin/series.py:series_list()` using OUTER JOIN for counts, and `series_posts()` and public `series_view()` using `joinedload(PostSeries.post)`
- **Missing Indexes:** Added indexes for `webhook_events.webhook_id` and `comments.parent_id` via migration `add_missing_indexes.py`
- **FTS5vocab:** Created `posts_fts_vocab` virtual table for efficient term indexing in `app/search.py:init_fts()`

Codebase architecture:
- **API Modularization:** Split `app/routes/api.py` (546 lines) into `app/routes/api/` package with `__init__.py`, `auth.py`, `posts.py`, `subscribers.py`, `stats.py`
- **Utility Consolidation:** Centralized `generate_slug()` in `app/utils.py`, updated models (Tag, Page, Post, Series), `app/services/slug.py`, and `app/services/tag.py`
- **Logging:** Replaced `print()` with proper `logging` in `app/services/backup.py`

## Wave 3 Completed Items (May 2026)

Infrastructure & Security:
- **CDN Support:** Added `CDN_URL` config (env var) and updated `app/vite.py:vite_asset()` and `app/filters.py:post_image_srcset_filter()` to use CDN when configured
- **S3 Security:** Added `_clear_credentials()` method to `S3StorageBackend` that clears access_key and secret_key after boto3 client initialization
- **Benchmarking:** Performance tests exist in `tests/benchmarks/test_benchmarks.py` covering search, dashboard, query counts, newsletter, FTS indexing, and tag caching

Cleanup:
- **Audit:** All reviewed modules (`backup_encryption`, `backup_integrity`, `webhooks`, `celery_app`) are actively used - no removal needed

## Test Interference Notes

### Page View Buffer Test Issues
- The page view buffer (`app/page_view_buffer.py`) can cause test interference when running full suite
- Buffer is started during `create_app()` if `PAGE_VIEW_BUFFER_SIZE > 0`
- In tests: disable via `app.config.PAGE_VIEW_BUFFER_SIZE = 0` and call `shutdown_page_view_buffer()`
- The `conftest.py` session-scoped `app` fixture may allow buffer restart - use autouse fixture in `tests/conftest.py` to ensure disabled (Wave 1 task)

### Test Database Session Issues
- `db.session.refresh()` fails if object isn't in current session
- Fix: Re-query object from database instead of using `refresh()` (Wave 1 task)

## Current Focus (May 2026)

We are currently executing the **Consolidated Improvement Plan** in `plans/plan.md`.
- **Wave 1**: Security & Stability (SQLi, CSSi, Encryption, Exceptions) - COMPLETED
- **Wave 2**: Performance & Architecture (N+1 Queries, Indexes, FTS5vocab, API Modularization, Utility Consolidation, Logging) - COMPLETED
- **Wave 3**: Features & Future (CDN, S3 Security, Benchmarking, Audit) - COMPLETED (Documentation Overhaul pending)

## Skills
 
Load specialized skills using the `skill` tool with the skill name.
 
| Skill | Description | Triggers |
|-------|-------------|----------|
| `blog_cms` | Blog CMS - Flask-based blogging platform with admin dashboard, newsletter scheduling, FTS5 search, multi-admin sessions, custom CSS theming, syntax highlighting themes, post series, Atom feed, 2FA, Comments, Audit Log, Post Revision Diff | Flask app, SQLAlchemy, session management, CSRF, newsletter, APScheduler, FTS5, REST API, password reset, post revisions, preview links, toasts, dashboard charts, graceful shutdown, Docker deployment, Vite bundler, 2FA, Comments, Audit Log |
| `e2e_testing` | End-to-end browser testing with Playwright | E2E tests, playwright, browser tests, pytest-playwright, UI testing |
| `ainews` | AI news pipeline — Flask backend, Celery workers, LLM pipeline (select→research→write→edit), subagent system, SQLite/WAL, Granian ASGI | pipeline, celery, newsletter, article, source, subscriber, admin, config, health, metrics |
| `nara` | Nara chain CLI agent — free PoMI mining, wallet, transfer, quest, on-chain skills, ZK ID, agent registry | NARA, quest, mining, airdrop, earn/claim/collect NARA, wallet, balance, transfer, skills, zkid, agent, referral, PoMI, keypair, mnemonic, faucet, deposit, withdraw |
| `osinit` | OSINIT Dashboard - FastAPI backend with 24 intelligence sources, React/TypeScript frontend with 3D globe | build, test, deploy, run, data source, panel, SSE, sweep, synthesis, authentication, rate limiting, cache, delta, VIX, SSRF, circuit breaker, routers, Granian |
