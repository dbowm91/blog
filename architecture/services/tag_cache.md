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
- `app/routes/admin/__init__.py:67,100`
- `app/routes/admin/posts/editor.py:88,206`
- `app/routes/admin/posts/revisions.py:98`
- `app/routes/admin/posts/manage.py:83`
- `app/routes/admin/tags.py:79,109,147`
- `app/routes/admin/posts/__init__.py:155,176,195,213`
- `app/scheduler.py:225,255`

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