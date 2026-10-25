# Posts API

The `/api/posts` endpoints. Every endpoint in the API blueprint requires an API
key and a scope; there is no unauthenticated variant.

## Authentication

Send the token in the `X-API-Key` header:

```bash
curl -H "X-API-Key: $DEVLOG_API_KEY" https://blog.example.com/api/posts
```

| Requirement | Value |
|-------------|-------|
| Header | `X-API-Key` |
| Scope for `GET` | `posts:read` |
| Scope for `POST`, `PUT`, `DELETE` | `posts:write` |

A missing or invalid key returns `401`. A key without the required scope returns
`403`. `admin:*` grants every scope.

## List Posts

```
GET /api/posts
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 20 | Items per page, capped at 100 |
| `published` | bool | — | Filter by published status |

There is no free-text search parameter on this endpoint. Use the site's search
route for that.

### Response

```json
{
  "posts": [ { "...": "post object" } ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

## Get Post

```
GET /api/posts/<post_id>
```

`<post_id>` is the integer primary key. Slugs are not accepted.

### Response

```json
{
  "id": 1,
  "title": "Post Title",
  "slug": "post-title",
  "body": "Post content...",
  "summary": "Summary...",
  "image": "image.jpg",
  "created_at": "2026-05-01T08:00:00+00:00",
  "updated_at": "2026-05-05T10:00:00+00:00",
  "published": true,
  "published_at": "2026-05-05T10:00:00+00:00",
  "scheduled_publish_at": null,
  "newsletter_sent_at": null,
  "newsletter_attempts": 0,
  "tags": ["python", "flask"],
  "author": {
    "username": "david",
    "name": "David Bowman",
    "url": "/author/david"
  }
}
```

Returns `404` when the post does not exist.

## Create Post

```
POST /api/posts
```

### Request Body

| Field | Required | Notes |
|-------|----------|-------|
| `title` | yes | Max 200 characters |
| `body` | yes | Max 50,000 characters |
| `slug` | no | Auto-generated from the title when absent |
| `summary` | no | Max 500 characters |
| `image` | no | Uploaded image filename |
| `published` | no | Defaults to `false` |
| `tags` | no | List of tag names; unknown tags are created |
| `author_id` | no | Requires `posts:write`; defaults to the site author |

```json
{
  "title": "New Post",
  "body": "Post content...",
  "summary": "Summary for previews",
  "tags": ["python"],
  "published": false
}
```

Returns `201` with the created post. Returns `400` for a missing or invalid
field, `409` on a slug collision, and `503` when the search index cannot be
updated (the post is rolled back).

## Update Post

```
PUT /api/posts/<post_id>
```

All body fields are optional; only the ones present are changed.

```json
{
  "title": "Updated Title",
  "body": "Updated content..."
}
```

Changing `published` from `false` to `true` sets `published_at` and emits a
`post.published` webhook event; the reverse emits `post.unpublished`.

## Delete Post

```
DELETE /api/posts/<post_id>
```

Returns `200` with:

```json
{ "message": "Post deleted successfully" }
```

Returns `404` when the post does not exist.

## Rate Limits

| Operation | Limit |
|-----------|-------|
| `GET` | 20 requests per minute |
| `POST`, `PUT`, `DELETE` | 10 requests per minute |

## Other API Resources

| Resource | Endpoints |
|----------|-----------|
| Pages | `/api/pages`, `/api/pages/<page_id>` |
| Series | `/api/series`, `/api/series/<series_id>`, `/api/series/<series_id>/posts`, `/api/series/<series_id>/posts/<post_id>`, `/api/series/<series_id>/reorder` |
| Tags | `/api/tags`, `/api/tags/<tag_id>` |
| Subscribers | `/api/subscribers`, `/api/subscribers/<subscriber_id>` |
| Stats | `/api/stats` |

## See Also

- [OpenAPI specification](../openapi.yaml) — the full machine-readable spec
- [API routes](../../architecture/routes/api-routes.md) — scope matching and the
  `require_api_key` decorator
