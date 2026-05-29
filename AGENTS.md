# Agent Guidelines

Quick reference for AI agents working on this codebase.

## Project Overview

DevLog is a Flask blog CMS with admin dashboard, newsletter scheduling, FTS5 search, custom CSS theming, 2FA, comments, post series, and multi-admin sessions.

## Setup Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Set required env vars
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export ADMIN_PASSWORD="your-strong-password"

# Initialize database
export FLASK_APP=run:app
flask db upgrade

# Run tests
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/

# Run linter
ruff check .
ruff format --check .

# Type check
mypy app/
```

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
| Public Routes | `app/routes/public/AGENTS.override.md` | Public page handlers |
| Frontend | `app/static/AGENTS.override.md` | JS/CSS assets, Vite build |
| Templates | `app/templates/AGENTS.override.md` | Jinja2 templates, filters |
| Tests | `tests/AGENTS.override.md` | Testing patterns, fixtures |
| OpenCode Config | `.opencode/AGENTS.override.md` | Agent tool configuration (may not exist) |
| Documentation | `docs/AGENTS.override.md` | Documentation structure |
| Scripts | `scripts/AGENTS.override.md` | Shell scripts, DevOps |
| Services | `app/services/AGENTS.override.md` | Backup, slug, serialization, tag services |
| Architecture | `architecture/AGENTS.override.md` | Architecture documentation |
| Plans | `plans/AGENTS.override.md` | Implementation plans and deferred items |

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
| Admin Audit Log model | `app/models.py:461-481` |
| PostRevision model | `app/models.py:236-249` |
| User model `__repr__` | `app/models.py:63-64` |
| Comment model | `app/models.py` |
| Services | `app/services/` (backup, slug, serialization, tag) |
| Tag Cache | `app/tag_cache.py` (flask-caching with TTL) |

## Security & Privacy Rules

- **Log ID, not Username**: When logging user actions or system events, always use `user.id`. Never log raw User objects or usernames to prevent PII leakage.
- **Credential Protection**: Never log `SECRET_KEY`, `ADMIN_PASSWORD`, or API keys.
- **Route Verification**: Before editing or documenting routes, verify against actual implementation. Routes frequently differ from what documentation or comments claim.

## Code Style

- **Linting**: `ruff check .` and `ruff format --check .`
- **Type checking**: `mypy app/`
- **SQLAlchemy**: Use SQLAlchemy 2.0 style (`db.session.execute(select(...))` pattern)
- **No comments**: Do not add comments unless explicitly requested
- **Security**: Never commit secrets, keys, or credentials

## Important Notes for Future Agents

### APScheduler Multi-Container Limitation

APScheduler uses FileLock with `timeout=0` which only works on a single machine. Multiple container replicas will each run their own APScheduler and execute jobs concurrently (duplicate newsletter sends, duplicate backups, duplicate post publishes). No external coordination mechanism exists.

### E2E Test Password Inconsistency

`tests/conftest.py` uses `"testpassword"` (no hyphen) at line 100; `tests/e2e/conftest.py` uses `"test-password"` (with hyphen) at line 44. Tests may fail inconsistently depending on which fixture set is used.

### Webhook Delivery Status Tracking Bug

`_update_delivery_status()` sets `event.delivered = True` at the dispatcher level BEFORE `deliver_single_webhook_task` calls complete. The per-webhook status is never checked. Webhook delivery status in DB will be misleading.

### Backup Encryption Silent Failure

`app/services/backup.py:_encrypt_backup_file()` catches exceptions and returns `False`. If `BACKUP_ENCRYPTION_KEY` is set but cannot be loaded, backup proceeds unencrypted without error. The `backup.py` CLI uses `create_backup()` which handles encryption failures, but silently falls back.

### Vite Build Required for Production

The `npm run build` (or `vite build`) must be run before production deployment. The `manifest.json` must be present. If Vite build hasn't run, JS assets will return hashed paths that don't exist.

### APScheduler SMTP Handling

When SMTP_HOST is not configured, only the daily newsletter job is disabled. Other scheduler jobs (cleanup_expired_subscribers, publish_scheduled_posts, run_daily_backup) continue to run.

### Email Retry Count

Newsletter retry count default is 5 (not 3 as some documentation may claim).

### Template Context Variables

Use `site_title` and `site_description` as context variables (NOT `site_name` or `site_tagline`).

### Template Filters

Actual filters (defined in `app/filters.py`):

- `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub`
- NOT `format_date`, `markdown`, `slugify` (these don't exist)

### Critical CSS

The `critical.css` file at `app/static/css/critical.css` provides above-the-fold CSS for fast initial paint. It is loaded in `base.html:24` with `media="screen"` for immediate loading.

### Docker Compose Profiles

All services require explicit profiles. There is no default profile:
- `--profile production`: blog, celery, redis, nginx
- `--profile backup`: backup service

### CI Workflow

The CI workflow is at `.github/workflows/ci.yml` (not `test.yml`). It includes 6 jobs: `lint-and-type`, `test`, `security-audit`, `frontend-build`, `docker-build`, `e2e-tests`. Also has a weekly schedule trigger (Monday 08:00 UTC).

### Webhook Delivery Architecture

Webhook delivery uses a two-level dispatch pattern:
- `deliver_webhook_task` dispatches to `deliver_single_webhook_task`
- `deliver_single_webhook_task` handles per-webhook SSRF protection, HMAC signing, retry logic, and delivery status updates

### Model Count

There are exactly 17 model classes in `app/models.py`: User, Post, Tag, Subscriber, Page, PageView, ShareEvent, AdminSession, SiteSettings, Webhook, WebhookEvent, Series, PostSeries, Comment, PostRevision, AdminAuditLog, ApiToken. Any documentation claiming 19 or 20 models is outdated.

### Thread-Unsafe Storage Singleton

`app/storage.py:get_storage()` singleton is not thread-safe. Multiple threads could create multiple storage instances. Uses lazy initialization without locking.

### E2E Test Isolation

`tests/e2e/conftest.py` does not define its own `app` fixture. Running `pytest tests/e2e/` alone fails because it relies on import chain from main conftest.

### Login Template Asset Loading

`admin/login_base.html` uses `url_for('static', ...)` directly instead of `vite_asset()` unlike `admin/base.html`. Login pages won't benefit from content-hashed URLs or CDN prefix.

### Prism CSS CDN Bypass

`main.js:102` loads Prism CSS via direct path `/static/css/...` bypassing vite_asset(). If CDN_URL is configured, Prism CSS won't include it.

### Python Version Mismatch

`scripts/dev.sh:11` requires Python >= 3.14 but `Dockerfile:1` uses python:3.12-slim. This dev/prod version mismatch could cause compatibility issues.

### Session IP Binding Not Enforced

`SESSION_IP_BINDING` config option exists but enforcement logic appears missing from `before_request_handler`. Verify before relying on this security feature.

### Silent FTS Initialization

`app/__init__.py:430-433` catches `OperationalError` during FTS init silently. User is never informed if search won't work.

## Implementation Plan

The consolidated implementation plan is at `plans/plan.md`. It contains NEW items identified in architecture reviews (May 29, 2026) that were not addressed in the previous plan. The previous 96-item plan was marked complete May 29, 2026.

## Historical Implementation Caveats

For detailed implementation history, deprecated features, actual route corrections, test interference notes, encryption module details, task line numbers, and other maintainer context, see:

> [docs/internals/agent-maintainer-notes.md](docs/internals/agent-maintainer-notes.md)

## Skills

Load specialized skills using the `skill` tool with the skill name.

| Skill | Description | Triggers |
|-------|-------------|----------|
| `blog_cms` | Blog CMS - Flask-based blogging platform with admin dashboard, newsletter scheduling, FTS5 search, multi-admin sessions, custom CSS theming, syntax highlighting themes, post series, Atom feed, 2FA, Comments, Audit Log, Post Revision Diff | Flask app, SQLAlchemy, session management, CSRF, newsletter, APScheduler, FTS5, REST API, password reset, post revisions, preview links, toasts, dashboard charts, graceful shutdown, Docker deployment, Vite bundler, 2FA, Comments, Audit Log |
| `e2e_testing` | End-to-end browser testing with Playwright | E2E tests, playwright, browser tests, pytest-playwright, UI testing |
| `ainews` | AI news pipeline — Flask backend, Celery workers, LLM pipeline (select→research→write→edit), subagent system, SQLite/WAL, Granian ASGI | pipeline, celery, newsletter, article, source, subscriber, admin, config, health, metrics |
| `architecture_review` | Architecture documentation review and improvement workflow | architecture, review, documentation, verify, cross-reference, architecture review plan |
| `nara` | Nara chain CLI agent — free PoMI mining, wallet, transfer, quest, on-chain skills, ZK ID, agent registry | NARA, quest, mining, airdrop, earn/claim/collect NARA, wallet, balance, transfer, skills, zkid, agent, referral, PoMI, keypair, mnemonic, faucet, deposit, withdraw |
| `osinit` | OSINIT Dashboard - FastAPI backend with 24 intelligence sources, React/TypeScript frontend with 3D globe | build, test, deploy, run, data source, panel, SSE, sweep, synthesis, authentication, rate limiting, cache, delta, VIX, SSRF, circuit breaker, routers, Granian |

## Skills Directory Note

Skills are stored in `.skills/` which may be a symlink to an external location.
If the symlink is broken (shows as "broken symbolic link"), skills are not available.
To fix: `rm .skills && ln -s /actual/path/to/skills .skills`
