# Services Module Override

## Purpose
Centralized service layer for shared logic between CLI, API, and Admin routes.

## Services
- `backup.py` - Centralized backup service (replaces `app/scheduler.py:run_daily_backup()` and root `backup.py`)
- `slug.py` - Slug generation (replaces `app/routes/admin/helpers/slug.py` and `app/models.py`)
- `serialization.py` - Serialization for CLI export (replaces `app/cli.py` functions)
- `tag.py` - Tag management service

## Usage
Import services from this package:
```python
from app.services import backup
from app.services.slug import generate_unique_slug
from app.services.serialization import serialize_post
```
