# Services Module Override

## Purpose
Centralized service layer for shared logic between CLI, API, and Admin routes.

## Services
- `backup.py` - Centralized backup service with `create_backup()` (used by Celery task) and `run_daily_backup()` (used by APScheduler - inline implementation, no encryption)
- `slug.py` - Slug generation (replaces `app/routes/admin/helpers/slug.py` and `app/models.py`)
- `serialization.py` - Serialization for CLI export (replaces `app/cli.py` functions)
- `tag.py` - Tag management service (no update_tag function exists)

## Slug Collision
Slug generation has a hardcoded limit of 100 tries before falling back to UUID suffix.

## Usage
Import services from this package:
```python
from app.services import backup
from app.services.slug import generate_unique_slug
from app.services.serialization import serialize_post
```
