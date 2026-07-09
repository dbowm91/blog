# Architecture Module Agent Override

## Purpose
Architecture documentation for the blog CMS application.

## Key Files
- `architecture/overview.md` - High-level architecture overview
- `architecture/core/` - App factory, configuration, models
- `architecture/routes/` - API, admin, public routes, RSS feeds
- `architecture/services/` - Backup, serialization, tag, slug services
- `architecture/tasks/` - Celery tasks, APScheduler, task overview
- `architecture/infrastructure/` - Webhooks, search, email, storage, health
- `architecture/frontend/` - Static assets, templates
- `architecture/deployment/` - Docker, CI/CD, security
- `architecture/testing/` - Test suite documentation

## Architecture Review Skill
See `.skills/architecture_review/skill.md` for detailed architecture review workflow.

## Review Notes

### Celery Concurrency
The Celery worker runs with `--concurrency=1` (see `docker-compose.yml:50`). This single-concurrency setting ensures newsletter emails are sent in order without duplication and webhook delivery is serialized.

### Search Provider Architecture
`SearchProvider` abstract class in `app/services/search/__init__.py` with implementations:
- `SQLiteSearchProvider` - Current default using FTS5
- `PostgreSQLSearchProvider` - Stub for future PostgreSQL support

**Important**: `app/search.py` module-level functions are SEPARATE from the `SearchProvider` abstraction. The functions in `app/search.py` (search, sync_fts, rebuild_fts, etc.) are standalone FTS5 implementations. `SQLiteSearchProvider` in `app/services/search/sqlite.py` is a wrapper class with its own implementation. They are NOT a wrapping relationship.

### Webhook Delivery Architecture

`deliver_webhook_task` (app/tasks.py:208) dispatches TO `deliver_single_webhook_task` (app/tasks.py:248). The parent iterates over webhook events and dispatches; the subtask handles per-webhook SSRF protection, HMAC signing, retry logic, and delivery status updates. Retries happen at the `deliver_single_webhook_task` level, not the parent.

### Exception Handling in Search
All module-level functions in `app/search.py` catch `OperationalError`, `ProgrammingError`, and `DatabaseError` exceptions from SQLAlchemy. When these exceptions occur during search operations, functions return empty results or `False` rather than propagating.

### Critical CSS
The `critical.css` file at `app/static/css/critical.css` provides above-the-fold CSS for fast initial paint. It is loaded in `base.html:22` with `media="screen"` for immediate loading.

### E2E Test Isolation
`tests/e2e/conftest.py` defines its own session-scoped `app` fixture (lines 11-43) with a separate database (`blog_e2e`). Running `pytest tests/e2e/` alone should work. However, the E2E `app_server` fixture (lines 64-66) contains dead code: it creates a new temp directory and overrides `SQLALCHEMY_DATABASE_URI` env var, but this has no effect because the Flask app is already configured by the `app` fixture.

### Vite Build Required for Production
The `npm run build` (or `vite build`) must be run before production deployment. The `manifest.json` must be present. If Vite build hasn't run, JS assets will return hashed paths that don't exist.

### Backup Encryption Silent Failure
`app/services/backup.py:_encrypt_backup_file()` catches exceptions and returns `False`. If `BACKUP_ENCRYPTION_KEY` is set but cannot be loaded, backup proceeds unencrypted without error. The `backup.py` CLI uses `create_backup()` which handles encryption failures, but silently falls back.

### Python Version
`scripts/dev.sh:11` requires Python >= 3.12. `Dockerfile:1` uses `python:3.12-slim`. Both are aligned at Python 3.12.

