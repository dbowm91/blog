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
| `projects.py` | `/api/projects` | GET, POST | List/create projects |
| `projects.py` | `/api/projects/<int:project_id>` | GET, PUT, DELETE | Single project operations |
| `series.py` | `/api/series` | GET, POST | List/create post series |
| `series.py` | `/api/series/<int:series_id>` | GET, PUT, DELETE | Single series operations |
| `series.py` | `/api/series/<int:series_id>/posts` | POST | Add post to series |
| `series.py` | `/api/series/<int:series_id>/posts/<int:post_id>` | DELETE | Remove post from series |
| `series.py` | `/api/series/<int:series_id>/reorder` | POST | Reorder posts within series |
| `tags.py` | `/api/tags` | GET, POST | List/create tags |
| `tags.py` | `/api/tags/<int:tag_id>` | GET, PUT, DELETE | Single tag operations |

### Scope Requirements

All endpoints require authentication via `X-API-Key` header. Scoped tokens (`ApiToken`) must have the required scope.

| Endpoint | Methods | Required Scope |
|----------|---------|----------------|
| `GET /api/posts` | GET | `posts:read` |
| `POST /api/posts` | POST | `posts:write` |
| `GET /api/posts/<id>` | GET | `posts:read` |
| `PUT /api/posts/<id>` | PUT | `posts:write` |
| `DELETE /api/posts/<id>` | DELETE | `posts:write` |
| `GET /api/subscribers` | GET | `subscribers:read` |
| `POST /api/subscribers` | POST | `subscribers:write` |
| `DELETE /api/subscribers/<id>` | DELETE | `subscribers:write` |
| `GET /api/stats` | GET | `stats:read` |
| `GET /api/pages` | GET | `pages:read` |
| `POST /api/pages` | POST | `pages:write` |
| `GET /api/pages/<id>` | GET | `pages:read` |
| `PUT /api/pages/<id>` | PUT | `pages:write` |
| `DELETE /api/pages/<id>` | DELETE | `pages:write` |
| `GET /api/projects` | GET | `projects:read` |
| `POST /api/projects` | POST | `projects:write` |
| `GET /api/projects/<id>` | GET | `projects:read` |
| `PUT /api/projects/<id>` | PUT | `projects:write` |
| `DELETE /api/projects/<id>` | DELETE | `projects:write` |
| `GET /api/series` | GET | `series:read` |
| `POST /api/series` | POST | `series:write` |
| `GET /api/series/<id>` | GET | `series:read` |
| `PUT /api/series/<id>` | PUT | `series:write` |
| `DELETE /api/series/<id>` | DELETE | `series:write` |
| `POST /api/series/<id>/posts` | POST | `series:write` |
| `DELETE /api/series/<id>/posts/<post_id>` | DELETE | `series:write` |
| `POST /api/series/<id>/reorder` | POST | `series:write` |
| `GET /api/tags` | GET | `tags:read` |
| `POST /api/tags` | POST | `tags:write` |
| `GET /api/tags/<id>` | GET | `tags:read` |
| `PUT /api/tags/<id>` | PUT | `tags:write` |
| `DELETE /api/tags/<id>` | DELETE | `tags:write` |


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

The `auth.py` module provides `require_api_key` and `require_scope` decorators for scoped access control. Protected API routes use `@require_api_key` which implements two-tier authentication:

1. **Legacy API_KEY**: Validates `X-API-Key` header against the `API_KEY` environment variable via HMAC comparison. Grants all scopes.
2. **Scoped ApiToken**: Validates token hash against the `api_tokens` table. Grants only the scopes listed on the token.

| Aspect | Details |
|--------|---------|
| Header | `X-API-Key: <api-key>` |
| Failure | 401 `{"error": "Invalid or missing API key"}` |
| Missing scope | 403 `{"error": "Missing scope: {scope}"}` |

### Scope Matching (`scope_allows()`)

The `scope_allows()` function determines whether a set of granted scopes satisfies a required scope. Matching semantics:

1. **Exact match** — A granted scope matching the required scope grants access (e.g. granted `posts:read` satisfies `posts:read`).
2. **`admin:*` grants all** — `admin:*` grants access to every API scope, regardless of category.
3. **Category wildcard** — A wildcard like `posts:*` grants access to all scopes in that category (`posts:read`, `posts:write`).
4. **Unknown scopes** — Unrecognized or malformed scopes grant no access.

### Wildcard Scopes

The `VALID_WILDCARD_SCOPES` set controls which category wildcards are recognized:

```
admin:*, posts:*, media:*, subscribers:*, newsletter:*, analytics:*, tags:*, pages:*, series:*
```

The `SCOPES` set (all valid scope strings) includes the individual scopes plus category wildcards:

```
posts:read, posts:write, posts:*, media:read, media:write, media:*, subscribers:read,
subscribers:write, subscribers:*, newsletter:send, newsletter:*, analytics:read, analytics:*,
tags:read, tags:write, tags:*, pages:read, pages:write, pages:*, projects:read, projects:write, projects:*, series:read, series:write,
series:*, admin:*
```

## Rate Limits

API endpoints have the following rate limits:

| Endpoint Type | Limit | Notes |
|---------------|-------|-------|
| Authenticated reads | 20/min | GET /api/posts, GET /api/subscribers, GET /api/stats, GET /api/pages, GET /api/series, GET /api/tags |
| Authenticated writes | 10/min | POST, PUT, DELETE operations on posts, subscribers, pages, series, tags |
| Public subscribe | 10/min | POST /subscribe |
| Public comments | 10/min | POST /post/<slug>/comment |

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

## Scoped API Tokens (`ApiToken` model)

ApiToken (`app/models.py:625-657`) provides scoped API authentication. Tokens are SHA-256 hashed before storage.

### Scopes

Full scope list (defined in `app/routes/api/auth.py`):

| Scope | Description |
|-------|-------------|
| `posts:read` | Read posts |
| `posts:write` | Create/update/delete posts |
| `posts:*` | Category wildcard — grants `posts:read` and `posts:write` |
| `media:read` | Read media |
| `media:write` | Upload/delete media |
| `media:*` | Category wildcard — grants all media scopes |
| `subscribers:read` | Read subscribers |
| `subscribers:write` | Create/delete subscribers |
| `subscribers:*` | Category wildcard — grants all subscriber scopes |
| `newsletter:send` | Send newsletters |
| `newsletter:*` | Category wildcard — grants all newsletter scopes |
| `analytics:read` | Read analytics |
| `analytics:*` | Category wildcard — grants all analytics scopes |
| `tags:read` | Read tags |
| `tags:write` | Create/update/delete tags |
| `tags:*` | Category wildcard — grants all tag scopes |
| `pages:read` | Read pages |
| `pages:write` | Create/update/delete pages |
| `pages:*` | Category wildcard — grants all page scopes |
| `projects:read` | Read project records |
| `projects:write` | Create/update/delete project records |
| `projects:*` | Category wildcard — grants all project scopes |
| `series:read` | Read series |
| `series:write` | Create/update/delete series |
| `series:*` | Category wildcard — grants all series scopes |
| `admin:*` | Grants all scopes across every category |

### `require_scope` decorator

Used after `@require_api_key` to enforce scope-based access:

```python
@require_api_key
@require_scope("posts:write")
def create_post():
    ...
```

## See Also
- [Admin Routes](admin-routes.md) - Admin dashboard
- [Public Routes](public-routes.md) - Public blog routes
- [RSS/Feeds](rss-feeds.md) - Feed formats
