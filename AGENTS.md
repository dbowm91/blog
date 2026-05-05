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
| Routes | `app/routes/AGENTS.override.md` | General routing concerns, API authentication, RSS feeds, error handlers |
| Admin Routes | `app/routes/admin/AGENTS.override.md` | Admin dashboard, post/subscriber/user management |
| Frontend | `app/static/AGENTS.override.md` | JS/CSS assets, Vite build |
| Templates | `app/templates/AGENTS.override.md` | Jinja2 templates, filters |
| Tests | `tests/AGENTS.override.md` | Testing patterns, fixtures |
| OpenCode Config | `.opencode/AGENTS.override.md` | Agent tool configuration |
| Documentation | `docs/AGENTS.override.md` | Documentation structure |
| Scripts | `scripts/AGENTS.override.md` | Shell scripts, DevOps |
| Services | `app/services/AGENTS.override.md` | Backup, slug, serialization, tag services |
| Plans | `plans/AGENTS.override.md` | Roadmap, execution waves, project planning |

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

These files previously used broad `except Exception` clauses. All have been replaced with specific exceptions:
- `app/routes/public/meta.py`
- `app/email.py`
- `app/backup_integrity.py`
- `app/webhooks.py`
- `app/tasks.py`
- `app/page_view_buffer.py`

## Test Interference Notes

### Page View Buffer Test Issues
- The page view buffer (`app/page_view_buffer.py`) can cause test interference when running full suite
- Buffer is started during `create_app()` if `PAGE_VIEW_BUFFER_SIZE > 0`
- In tests: disable via `app.config.PAGE_VIEW_BUFFER_SIZE = 0` and call `shutdown_page_view_buffer()`
- The `conftest.py` session-scoped `app` fixture may allow buffer restart - use autouse fixture in `tests/conftest.py` to ensure disabled.

### Test Database Session Issues
- `db.session.refresh()` fails if object isn't in current session
- Fix: Re-query object from database instead of using `refresh()`.

## Completed Work (Historical)

- **Wave 1:** Security & Stability (SQLi, CSSi, Encryption, Exceptions)
- **Wave 2:** Performance & Architecture (N+1 Queries, Indexes, FTS5vocab, API Modularization, Utility Consolidation, Logging)
- **Wave 3:** Features & Future (CDN, S3 Security, Benchmarking, Audit)

## Current Focus (May 2026)

The project is currently executing from the **Consolidated Improvement Plan** located at `plans/plan.md`. This document replaces all prior fragmented `plan*.md` files and is organized into logical waves (Waves 4-9) that can often be parallelized. 
Agents undertaking new work should consult `plans/plan.md` and use it as a living document to track progress.

## Skills
 
Load specialized skills using the `skill` tool with the skill name.
 
| Skill | Description | Triggers |
|-------|-------------|----------|
| `blog_cms` | Blog CMS - Flask-based blogging platform with admin dashboard, newsletter scheduling, FTS5 search, multi-admin sessions, custom CSS theming, syntax highlighting themes, post series, Atom feed, 2FA, Comments, Audit Log, Post Revision Diff | Flask app, SQLAlchemy, session management, CSRF, newsletter, APScheduler, FTS5, REST API, password reset, post revisions, preview links, toasts, dashboard charts, graceful shutdown, Docker deployment, Vite bundler, 2FA, Comments, Audit Log |
| `e2e_testing` | End-to-end browser testing with Playwright | E2E tests, playwright, browser tests, pytest-playwright, UI testing |
| `ainews` | AI news pipeline — Flask backend, Celery workers, LLM pipeline (select→research→write→edit), subagent system, SQLite/WAL, Granian ASGI | pipeline, celery, newsletter, article, source, subscriber, admin, config, health, metrics |
| `nara` | Nara chain CLI agent — free PoMI mining, wallet, transfer, quest, on-chain skills, ZK ID, agent registry | NARA, quest, mining, airdrop, earn/claim/collect NARA, wallet, balance, transfer, skills, zkid, agent, referral, PoMI, keypair, mnemonic, faucet, deposit, withdraw |
| `osinit` | OSINIT Dashboard - FastAPI backend with 24 intelligence sources, React/TypeScript frontend with 3D globe | build, test, deploy, run, data source, panel, SSE, sweep, synthesis, authentication, rate limiting, cache, delta, VIX, SSRF, circuit breaker, routers, Granian |
