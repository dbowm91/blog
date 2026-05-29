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

`deliver_webhook_task` (app/tasks.py:194) dispatches TO `deliver_single_webhook_task` (app/tasks.py:233). The parent iterates over webhook events and dispatches; the subtask handles per-webhook SSRF protection, HMAC signing, retry logic, and delivery status updates. Retries happen at the `deliver_single_webhook_task` level, not the parent.

### Exception Handling in Search
All module-level functions in `app/search.py` catch `OperationalError`, `ProgrammingError`, and `DatabaseError` exceptions from SQLAlchemy. When these exceptions occur during search operations, functions return empty results or `False` rather than propagating.

### Critical CSS
The `critical.css` file at `app/static/css/critical.css` provides above-the-fold CSS for fast initial paint. It is loaded in `base.html:22` with `media="screen"` for immediate loading.

### E2E Test Password Inconsistency
`tests/conftest.py` uses `"testpassword"` (no hyphen) at line 100; `tests/e2e/conftest.py` uses `"test-password"` (with hyphen) at line 44. Tests may fail inconsistently depending on which fixture set is used.

### Vite Build Required for Production
The `npm run build` (or `vite build`) must be run before production deployment. The `manifest.json` must be present. If Vite build hasn't run, JS assets will return hashed paths that don't exist.

### Backup Encryption Silent Failure
`app/services/backup.py:_encrypt_backup_file()` catches exceptions and returns `False`. If `BACKUP_ENCRYPTION_KEY` is set but cannot be loaded, backup proceeds unencrypted without error. The `backup.py` CLI uses `create_backup()` which handles encryption failures, but silently falls back.

### Testing/test-suite.md False Claims
The architecture doc at `architecture/testing/test-suite.md` contains two factually incorrect claims:
- Line 113: Claims playwright is NOT in requirements.txt - FALSE, it IS (playwright>=1.58.0 at requirements.txt:18)
- Lines 190-196: Claims E2E conftest creates its own `app` fixture - FALSE, it relies on import chain from main conftest

### Python Version Mismatch
`scripts/dev.sh:11` requires Python >= 3.14, but `Dockerfile:1` uses `python:3.12-slim`. Development requires Python 3.14 but production uses 3.12.