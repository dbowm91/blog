# Tag Service (`app/services/tag.py`)

Tag CRUD operations and post count management.

## Public Functions

| Function | Location | Description |
|----------|----------|-------------|
| `get_or_create_tags()` | `app/services/tag.py:12` | Get existing tags or create new ones from names |
| `get_tag_by_slug()` | `app/services/tag.py:34` | Get a tag by its slug |
| `get_all_tags()` | `app/services/tag.py:41` | Get all tags ordered by name |
| `delete_tag_if_unused()` | `app/services/tag.py:58` | Delete tag if it has no associated posts |
| `get_tag_post_count()` | `app/services/tag.py:48` | Get count of **published** posts for a tag |

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

## See Also
- [Models](core/models.md) - Tag model
