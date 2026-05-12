# Tag Service (`app/services/tag.py`)

Tag CRUD operations and post count management.

## Features

- Create, read, delete tags
- Post count queries
- Slug generation

## Tag Caching (`app/tag_cache.py`)

Tag counts are cached for performance:

| Function | Description |
|----------|-------------|
| `_get_tag_counts()` | Returns dict of `{tag_id: count}` with caching |
| `invalidate_tag_cache()` | Clears the tag count cache |

**Configuration:**
- `TAG_CACHE_TTL_SECONDS` (default: 60) - Cache TTL in seconds

**Cache Invalidation Triggers:**
- Post create/update/delete
- Post publish/unpublish
- Tag create/delete/update

## See Also
- [Models](core/models.md) - Tag model
