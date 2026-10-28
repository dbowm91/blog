# Architecture Module Agent Override

## Purpose
Architecture documentation for the blog CMS application.

## Key Files
- `architecture/overview.md` - Birds-eye module map and index to every deep-dive document
- `architecture/core/` - App factory, configuration, models, filesystem layout, onboarding, theme system
- `architecture/routes/` - API, admin, public routes, RSS feeds
- `architecture/services/` - Service layer, operations services, doctor
- `architecture/tasks/` - Celery tasks, APScheduler, task overview
- `architecture/infrastructure/` - Webhooks, search, email, storage, health
- `architecture/frontend/` - Static assets, templates, appearance layer
- `architecture/deployment/` - Operator CLI, managed deployment, security, install, Docker, CI/CD
- `architecture/testing/` - Test suite documentation

## Document Convention

`architecture/overview.md` is the index. Every module named there links to a
deep-dive document in the same directory tree. When adding a module, add the
deep-dive file first, then add the row to the overview's module map.

Deep-dive documents follow these rules:

- H1 title naming the module and its source path, then a one-paragraph intro
  saying what the module is and why it exists.
- A table of the module's files and what each one owns.
- Symbolic references (function names, class names, config keys) rather than
  line numbers — line numbers drift as the code changes.
- A `## See Also` section at the end with relative links that resolve **from
  the document's own directory**. A sibling file uses its bare filename
  (`models.md`); a file in another directory needs the right `../` prefix
  (`../frontend/static-assets.md`). Authoring a link as if the base were
  `architecture/` produces a broken link — verify each target exists before
  finishing.
- A `## Notes and Gotchas` section for surprising behaviour, defects, and
  inconsistencies found while reading the source. Document them; do not fix
  code from a documentation task.


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

### Backup Encryption Failure Is Not Silent
`app/services/backup.py:_encrypt_backup_file()` catches exceptions and returns `False`. `create_backup()` then removes the unencrypted file, logs `Backup encryption failed, discarding unencrypted backup` at ERROR level and returns `None`. If `BACKUP_ENCRYPTION_KEY` is set but cannot be loaded, the backup fails — it never falls back to an unencrypted backup on disk.

### Python Version
`scripts/dev.sh:11` requires Python >= 3.12. `Dockerfile:1` uses `python:3.12-slim`. Both are aligned at Python 3.12.

