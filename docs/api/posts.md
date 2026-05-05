# Posts API

## List Posts

```
GET /api/posts
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | - | Search query |
| `page` | int | 1 | Page number |
| `per_page` | int | 10 | Items per page |
| `published` | bool | - | Filter by published status |

### Response

```json
{
  "posts": [
    {
      "id": 1,
      "title": "Post Title",
      "slug": "post-title",
      "body": "Post content...",
      "summary": "Summary...",
      "published": true,
      "published_at": "2026-05-05T10:00:00Z",
      "tags": ["python", "flask"]
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 10
}
```

## Get Post

```
GET /api/posts/<slug or id>
```

### Response

```json
{
  "id": 1,
  "title": "Post Title",
  "slug": "post-title",
  "body": "Post content...",
  "summary": "Summary...",
  "image": "image.jpg",
  "published": true,
  "published_at": "2026-05-05T10:00:00Z",
  "created_at": "2026-05-01T08:00:00Z",
  "updated_at": "2026-05-05T10:00:00Z",
  "tags": ["python", "flask"]
}
```

## Create Post

```
POST /api/posts
```

Requires `X-API-Key` header.

### Request Body

```json
{
  "title": "New Post",
  "body": "Post content...",
  "summary": "Summary for previews",
  "tags": ["python"],
  "published": false
}
```

## Update Post

```
PUT /api/posts/<slug or id>
```

Requires `X-API-Key` header.

### Request Body

```json
{
  "title": "Updated Title",
  "body": "Updated content..."
}
```

## Delete Post

```
DELETE /api/posts/<slug or id>
```

Requires `X-API-Key` header.

Returns `204 No Content` on success.