# Slug Collision Handling

## Overview

The slug collision limit is **100 tries** before falling back to a UUID suffix.

## How It Works

```python
# From app/services/slug.py:32-41
counter = 2
while counter <= 100:
    slug_str = f"{base_slug}-{counter}"
    # Check uniqueness...
    counter += 1

if counter > 100:
    slug_str = f"{base_slug}-{uuid.uuid4().hex[:8]}"
```

## Example

| Attempt | Slug |
|---------|------|
| 1 | `my-post-title` |
| 2 | `my-post-title-2` |
| 3 | `my-post-title-3` |
| ... | ... |
| 100 | `my-post-title-100` |
| 101+ | `my-post-title-a1b2c3d4` |

## UUID Fallback

The UUID suffix uses the first 8 characters of a random UUID hex, resulting in slugs like:
- `my-post-title-a1b2c3d4`
- `my-post-title-7f8e9a0b`

This ensures uniqueness even under extreme collision scenarios.