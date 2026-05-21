# Slug Service (`app/services/slug.py`)

Unique slug generation for posts, pages, tags, and series.

## Features

- URL-safe slug generation
- Collision detection with suffix enumeration (e.g., `my-post-2`)
- Maximum 100 collision attempts before falling back to UUID suffix
- UUID fallback format: `{base_slug}-{8_char_hex_uuid}`

## Core Function

```python
def generate_unique_slug(model: Type, title: str, exclude_id: Optional[int] = None, slug: Optional[str] = None) -> str:
```

**Parameters:**
- `model`: SQLAlchemy model to check for collisions (Post, Page, Tag, Series)
- `title`: The title to generate a slug from
- `exclude_id`: Optional ID to exclude from collision check (for edit operations)
- `slug`: Optional pre-defined slug to use (if None, generates from title)

**Returns:** A unique slug, either the base slug or `{base_slug}-{n}` for collisions, or `{base_slug}-{uuid8}` after 100 attempts.

## Slug Collision Handling

1. Check if `base_slug` exists - if not, return it
2. Try `base_slug-2`, `base_slug-3`, ... up to `base_slug-100`
3. If all 100 attempts collide, fall back to `base_slug-{uuid8}` where uuid8 is 8 characters from a random UUID

## See Also
- [Models](core/models.md) - Database models using slugs
