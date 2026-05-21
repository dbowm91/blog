# Tag Cache (`app/tag_cache.py`)

Tag count caching using flask-caching with TTL-based invalidation.

## Purpose

Provides efficient tag count queries with caching to avoid repeated database hits for the tag cloud/sidebar display.

## Configuration

- `TAG_CACHE_TTL_SECONDS` from `app/config.py` - Cache timeout (default: 60 seconds)

## Functions

| Function | Description |
|----------|-------------|
| `_get_tag_counts_cached()` | Cached tag counts query using `flask_cache.memoize` |
| `_get_tag_counts()` | Get tag counts with caching (respects request context) |
| `_get_tag_counts_uncached()` | Direct database query (for non-request contexts) |
| `invalidate_tag_cache()` | Clear the memoized cache |

## Cache Invalidation

Cache is invalidated when:
1. A post is created, updated, or deleted (via `invalidate_tag_cache()` calls)
2. The cache expires after `TAG_CACHE_TTL_SECONDS`

Invalidation calls found in:
- `app/routes/admin/posts.py` - post save/delete operations
- `app/routes/admin/tags.py` - tag creation/deletion

## Implementation Details

The cached function uses `flask_cache.memoize` which stores results based on function arguments. Since `_get_tag_counts_cached()` takes no arguments, the result is cached for the TTL duration.

```python
@flask_cache.memoize(timeout=TAG_CACHE_TTL_SECONDS)
def _get_tag_counts_cached() -> dict[Any, Any]:
    rows = _build_tag_counts_query()
    return {row[0]: row[1] for row in rows}
```

## See Also
- [Tag Service](services/tag.md) - Tag CRUD operations
- `app/config.py` - `TAG_CACHE_TTL_SECONDS` configuration