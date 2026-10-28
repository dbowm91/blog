# Services Module Override

## Purpose
Centralized service layer for shared logic between CLI, API, and Admin routes.

## Services
- `backup.py` - Centralized backup service with `create_backup()` (used by Celery task, supports encryption/compression) and `run_daily_backup()` (used by APScheduler, creates `blog_*.db` files, manages retention via `blog_*.db` pattern)
- `slug.py` - Slug generation (replaces `app/routes/admin/helpers/slug.py` and `app/models.py`)
- `serialization.py` - Serialization for CLI export (replaces `app/cli.py` functions)
- `tag.py` - Tag management service (no update_tag function exists)
- `theme_settings.py` - Theme configuration validation, legacy preset migration, effective theme name resolution
- `projects.py` - Project validation, published queries, repository metadata, scoped themes
- `navigation.py` - Public navigation projection for published pages and projects
- `site_settings.py` - Homepage-target validation and navigation settings parsing

## Optional AI Authoring Service

`ai_assist.py` owns the provider adapters for local OpenAI-compatible endpoints and OpenCode Go. Keep inputs/output bounded, use the configurable inference timeout, retry only transient failures once, do not log prompts or secrets, do not write to the database, and sanitize provider errors for display. It must never create/attach tags or modify posts, revisions, indexes, or caches. Tag reconciliation must use canonical tag validation and only a bounded role-authorized catalog; send no prior post bodies or unpublished titles. Real provider requests require explicit user authorization and synthetic content unless the user authorizes editorial content for a provider.

## Operations Service Layer (`app/services/operations/`)

Extracted business logic from CLI handlers into reusable, testable services.

### Modules

| Module | Purpose |
|--------|---------|
| `results.py` | Typed `OperationResult` dataclasses with stable operation codes |
| `admin.py` | Admin user create/promote/reset-password/list |
| `database.py` | SQLite integrity check, FTS rebuild |
| `media.py` | Orphaned media scan and cleanup |
| `transfer.py` | Site data export/import with atomic writes |
| `themes.py` | Theme list/validate/inspect/refresh/paths/accessibility facade |
| `backup.py` | Backup creation and verification with structured results |

### Conventions

- Service functions never depend on Click, terminal output, or process exit
- All functions require Flask application context
- Return typed `OperationResult` subclasses (frozen dataclasses)
- Use `commit_with_rollback()` for transaction boundaries
- Password complexity validation is centralized in `admin.py`
- Secrets are never returned or logged
- Stable operation codes: `admin.created`, `db.integrity.ok`, `export.success`, etc.

### CLI Integration

The standalone `devlog` CLI commands (`devlog_cli/commands/`) call these services.
Flask commands (`app/cli.py`) remain as compatibility wrappers calling the same services.

## Slug Collision
Slug generation has a hardcoded limit of 100 tries before falling back to UUID suffix.

## Usage
Import services from this package:
```python
from app.services import backup
from app.services.slug import generate_unique_slug
from app.services.serialization import serialize_post
```
