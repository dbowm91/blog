# Slug Generation Service

## Unique Slug Generation

The `generate_unique_slug()` function in `app/services/slug.py` creates URL-safe slugs for posts and pages.

## Slug Collision Resolution

The function handles slug collisions by appending a counter:

1. Attempt to use the base slug (e.g., "my-post-title")
2. If collision exists, try "my-post-title-2", "my-post-title-3", etc.
3. **Collision limit**: 100 tries before falling back to UUID suffix

```python
counter = 2
while counter <= 100:
    slug_str = f"{base_slug}-{counter}"
    # Check for existing slug...
    counter += 1

if counter > 100:
    # Fall back to UUID suffix
    slug_str = f"{base_slug}-{uuid.uuid4().hex[:8]}"
```

## UUID Fallback Behavior

When 100 collisions occur (extremely rare in practice), the slug falls back to:
```
my-post-title-a1b2c3d4
```

This ensures uniqueness while remaining human-readable.

## Usage

```python
from app.services.slug import generate_unique_slug

# Generate slug from title
slug = generate_unique_slug(Post, "My Post Title")

# Use custom slug
slug = generate_unique_slug(Post, "My Post", slug="custom-slug")

# Exclude current post (for edits)
slug = generate_unique_slug(Post, "My Post", exclude_id=current_post.id)
```

## Slug Generation Rules

- Lowercase alphanumeric and hyphens only
- Maximum length: 255 characters
- Strips special characters
- Trims leading/trailing hyphens