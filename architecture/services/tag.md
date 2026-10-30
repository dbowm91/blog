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

## AI Tag Suggestions

AI tag suggestions are produced by `app/services/ai_assist.py`, not by this CRUD service. The AI adapter reuses `Tag.generate_slug()` and `validate_tag_name()` as the canonical policy. It generates 3–5 candidates, deterministically reuses exact matches from the requesting role's visible catalog, and makes at most one additional model request to reconcile unresolved names against a bounded catalog of IDs, names, and published-post usage counts. Existing IDs and names are verified before response; model suggestions never create or attach tags. Only the normal post save path calls `_get_or_create_tags()`.

The catalog is limited to 80 entries and 8,000 serialized characters; non-admins see only tags with published usage. Admins may see private taxonomy metadata but no unpublished post text is sent. See [Services Overview](overview.md#optional-ai-authoring) for provider configuration, request bounds, and the provider-policy gate.

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
- [Models](../core/models.md) - Tag model
