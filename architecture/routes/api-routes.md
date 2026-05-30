# API Routes (`app/routes/api/`)

REST API for programmatic access to blog data.

## Endpoints

| File | Endpoint | Methods | Purpose |
|------|----------|---------|---------|
| `posts.py` | `/api/posts` | GET, POST | List/create posts |
| `posts.py` | `/api/posts/<id>` | GET, PUT, DELETE | Single post operations (publish via PUT with `published` field) |
| `subscribers.py` | `/api/subscribers` | GET, POST | List subscribers, create new subscriber |
| `subscribers.py` | `/api/subscribers/<int:subscriber_id>` | DELETE | Delete subscriber |
| `stats.py` | `/api/stats` | GET | Dashboard statistics |
| `pages.py` | `/api/pages` | GET, POST | List/create static pages |
| `pages.py` | `/api/pages/<int:page_id>` | GET, PUT, DELETE | Single page operations |
| `series.py` | `/api/series` | GET, POST | List/create post series |
| `series.py` | `/api/series/<int:series_id>` | GET, PUT, DELETE | Single series operations |
| `series.py` | `/api/series/<int:series_id>/posts` | POST | Add post to series |
| `series.py` | `/api/series/<int:series_id>/posts/<int:post_id>` | DELETE | Remove post from series |
| `series.py` | `/api/series/<int:series_id>/reorder` | POST | Reorder posts within series |
| `tags.py` | `/api/tags` | GET, POST | List/create tags |
| `tags.py` | `/api/tags/<int:tag_id>` | GET, PUT, DELETE | Single tag operations |


## Webhook Events

Post publish/unpublish via `PUT /api/posts/<id>` with `{"published": true/false}` triggers:
- `post.published` event when a post is published
- `post.unpublished` event when a post is unpublished

Subscriber confirmation (via `/confirm/<token>`) triggers:
- `subscriber.confirmed` event when a subscriber confirms their email

## Posts API (`posts.py`)

### List Posts
```
GET /api/posts
```
Query Parameters:
- `page` (int): Page number
- `per_page` (int): Items per page
- `published` (bool): Filter by published status

Response:
```json
{
  "posts": [...],
  "total": 100,
  "pages": 10,
  "page": 1,
  "per_page": 10
}
```

### Get Post
```
GET /api/posts/<id>
```

### Create Post
```
POST /api/posts
```
Body:
```json
{
  "title": "Post Title",
  "body": "Post content",
  "slug": "post-slug",
  "tags": ["tag1", "tag2"],
  "published": false
}
```

### Update Post
```
PUT /api/posts/<id>
```

### Delete Post
```
DELETE /api/posts/<id>
```

## Subscribers API (`subscribers.py`)

### List Subscribers
```
GET /api/subscribers
```
Query Parameters:
- `page` (int): Page number
- `per_page` (int): Items per page
- `confirmed` (bool): Filter by confirmed status

### Export Subscribers
**Note:** Subscriber export is only available in admin routes, not the public API.
See `/admin/subscribers/export` in admin routes.

## Stats API (`stats.py`)

### Get Statistics
```
GET /api/stats
```
Response:
```json
{
  "total_views": 10000,
  "total_posts": 50,
  "total_shares": 25,
  "total_subscribers": 100,
  "views_this_month": 500,
  "new_subscribers_this_month": 10
}
```

## Pages API (`pages.py`)

### List Pages
```
GET /api/pages
```
Query Parameters:
- `published` (bool): Filter by published status

Requires scope: `pages:read`

### Get Page
```
GET /api/pages/<int:page_id>
```
Requires scope: `pages:read`

### Create Page
```
POST /api/pages
```
Body:
```json
{
  "title": "Page Title",
  "body": "Page content",
  "slug": "page-slug",
  "published": false
}
```
Requires scope: `pages:write`

### Update Page
```
PUT /api/pages/<int:page_id>
```
Body (all optional): `title`, `slug`, `body`, `published`
Requires scope: `pages:write`

### Delete Page
```
DELETE /api/pages/<int:page_id>
```
Requires scope: `pages:write`

## Series API (`series.py`)

### List Series
```
GET /api/series
```
Query Parameters:
- `include_posts` (bool): Include post list

Requires scope: `series:read`

### Get Series
```
GET /api/series/<int:series_id>
```
Query Parameters:
- `include_posts` (bool): Include post list

Requires scope: `series:read`

### Create Series
```
POST /api/series
```
Body:
```json
{
  "name": "Series Name",
  "description": "Description",
  "slug": "series-slug"
}
```
Requires scope: `series:write`

### Update Series
```
PUT /api/series/<int:series_id>
```
Body (all optional): `name`, `description`, `slug`
Requires scope: `series:write`

### Delete Series
```
DELETE /api/series/<int:series_id>
```
Requires scope: `series:write`

### Add Post to Series
```
POST /api/series/<int:series_id>/posts
```
Body:
```json
{
  "post_id": 1,
  "order_index": 0
}
```
Requires scope: `series:write`

### Remove Post from Series
```
DELETE /api/series/<int:series_id>/posts/<int:post_id>
```
Requires scope: `series:write`

### Reorder Series Posts
```
POST /api/series/<int:series_id>/reorder
```
Body:
```json
{
  "order": [{"post_id": 1, "order_index": 0}, {"post_id": 2, "order_index": 1}]
}
```
Requires scope: `series:write`

## Tags API (`tags.py`)

### List Tags
```
GET /api/tags
```
Query Parameters:
- `include_count` (bool): Include post count

Requires scope: `tags:read`

### Get Tag
```
GET /api/tags/<int:tag_id>
```
Requires scope: `tags:read`

### Create Tag
```
POST /api/tags
```
Body:
```json
{
  "name": "tag-name"
}
```
Requires scope: `tags:write`

### Update Tag
```
PUT /api/tags/<int:tag_id>
```
Body:
```json
{
  "name": "new-tag-name"
}
```
Requires scope: `tags:write`

### Delete Tag
```
DELETE /api/tags/<int:tag_id>
```
Requires scope: `tags:write`

## Authentication (`auth.py`)

The `auth.py` module provides a `require_api_key` decorator (not a route). Protected API routes use `@require_api_key` to validate the `X-API-Key` header against the `API_KEY` environment variable via HMAC comparison.

| Aspect | Details |
|--------|---------|
| Header | `X-API-Key: <api-key>` |
| Env var | `API_KEY` (must be set, otherwise returns 503) |
| Failure | 401 `{"error": "Invalid or missing API key"}` |

## Rate Limits

API endpoints have the following rate limits:

| Endpoint Type | Limit | Notes |
|---------------|-------|-------|
| Authenticated reads | 20/min | GET /api/posts, GET /api/subscribers, GET /api/stats |
| Authenticated writes | 10/min | POST, PUT, DELETE operations |
| Public subscribe | 10/min | POST /subscribe |
| Public comments | 10/min | POST /post/<slug>/comment |
| API key check | 1000/hour | Per API key |

Rate limit headers are returned on all responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

When limits are exceeded, `429 Too Many Requests` is returned with `Retry-After` header.

## Error Responses

All API endpoints return consistent JSON error responses. Error responses include an `error` field with a human-readable message.

| Status Code | Meaning | Example Response |
|-------------|---------|------------------|
| 400 | Bad Request - Invalid JSON body or validation failure | `{"error": "Invalid JSON body"}` |
| 400 | Validation error - Missing or invalid field | `{"error": "title is required"}` |
| 401 | Unauthorized - Invalid or missing API key | `{"error": "Invalid or missing API key"}` |
| 403 | Forbidden - Missing required scope | `{"error": "Missing scope: pages:write"}` |
| 404 | Not Found - Resource does not exist | `{"error": "Post not found"}` |
| 409 | Conflict - Duplicate slug or constraint violation | `{"error": "Duplicate slug or database constraint violation"}` |
| 429 | Too Many Requests - Rate limit exceeded | Rate limit headers + `Retry-After` header |
| 500 | Internal Server Error - Database operational failure | `{"error": "Database operational error"}` |
| 503 | Service Unavailable - Search index unavailable | `{"error": "Search index unavailable"}` |

### Common Error Messages

| Error Message | Cause |
|---------------|-------|
| `Invalid JSON body` | Request body is not valid JSON |
| `title is required` | Required field missing in request body |
| `Invalid or missing API key` | No `X-API-Key` header or invalid key |
| `Missing scope: {scope}` | API key lacks required scope for endpoint |
| `{resource} not found` | Resource with given ID does not exist |
| `Duplicate slug or database constraint violation` | Slug already exists or other DB constraint failed |
| `A {resource} with this {field} already exists` | Unique constraint violation |
| `Database operational error` | Database connection or query failure |
| `Search index unavailable` | FTS5 search index sync failed (503) |

## See Also
- [Admin Routes](admin-routes.md) - Admin dashboard
- [Public Routes](public-routes.md) - Public blog routes
- [RSS/Feeds](rss-feeds.md) - Feed formats
