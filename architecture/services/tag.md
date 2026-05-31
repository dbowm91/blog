# Tag Service (`app/services/tag.py`)

Tag CRUD operations and post count management.

## Public Functions

| Function | Location | Description |
|----------|----------|-------------|
| `get_or_create_tags()` | `app/services/tag.py:12` | Get existing tags or create new ones from names |
| `get_tag_by_slug()` | `app/services/tag.py:32` | Get a tag by its slug |
| `get_all_tags()` | `app/services/tag.py:37` | Get all tags ordered by name |
| `delete_tag_if_unused()` | `app/services/tag.py:55` | Delete tag if it has no associated posts |
| `get_tag_post_count()` | `app/services/tag.py:42` | Get count of **published** posts for a tag |

**Note:** `get_tag_post_count()` only counts published posts, not all posts.

## Features

- Create, read, delete tags
- Post count queries (published only)
- Slug generation with collision handling (100 tries, then UUID suffix)

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

## Cache Coordination

### `_invalidate_all_caches()`

Defined in `app/routes/admin/__init__.py:62`. Coordinates invalidation of all application caches after admin operations:

| Cache | Invalidation Function |
|-------|----------------------|
| Tag count cache | `invalidate_tag_cache()` (from `app/tag_cache.py`) |
| FTS availability flag | `reset_fts_available()` (from `app/search.py`) |
| Analytics cache | `invalidate_analytics_cache()` (from `app/routes/admin/helpers/analytics.py`) |
| Dashboard cache | `invalidate_dashboard_cache()` (from `app/routes/admin/helpers.py`) |
| Footer data cache | `invalidate_footer_cache()` (from `app/context_processors.py`) |

Called after post create/update/delete, tag operations, and settings changes to ensure all cached data stays consistent.

## See Also
- [Models](core/models.md) - Tag model
