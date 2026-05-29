# Tag Cache (`app/tag_cache.py`)

Tag count caching using flask-caching with TTL-based invalidation.

## Purpose

Provides efficient tag count queries with caching to avoid repeated database hits for the tag cloud/sidebar display.

## Configuration

- `TAG_CACHE_TTL_SECONDS` from `app/config.py` - Cache timeout (default: 60 seconds)

## Functions

| Function | Line | Description |
|----------|------|-------------|
| `_build_tag_counts_query()` | 16 | Build the raw tag counts query joining `post_tags` with `Post` for published posts |
| `_get_tag_counts_cached()` | 30 | Cached tag counts query using `flask_cache.memoize` |
| `_get_tag_counts()` | 37 | Main entry point; uses cached version in request context, uncached otherwise |
| `_get_tag_counts_uncached()` | 44 | Direct database query (for non-request contexts) |
| `invalidate_tag_cache()` | 50 | Clear the memoized cache via `delete_memoized` |

## Cache Invalidation

Cache is invalidated when:
1. A post is created, updated, or deleted (via `invalidate_tag_cache()` calls)
2. The cache expires after `TAG_CACHE_TTL_SECONDS`

Invalidation calls found in:
- `app/routes/admin/__init__.py:68` (via `_invalidate_all_caches()`)
- `app/routes/admin/posts/editor.py:89,204`
- `app/routes/admin/posts/revisions.py:97`
- `app/routes/admin/posts/manage.py:82`
- `app/routes/admin/tags.py:76,104,142`
- `app/routes/admin/posts/__init__.py:158,179,198,216`
- `app/scheduler.py:224,256`
- `app/routes/api/tags.py:130,189,219`

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