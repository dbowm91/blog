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
| `auth.py` | `/api/auth` | POST | API key authentication |

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

## Authentication (`auth.py`)

### API Key Auth
```
POST /api/auth
```
Body:
```json
{
  "api_key": "your-api-key"
}
```

Response:
```json
{
  "valid": true,
  "message": "API key is valid"
}
```

## Rate Limits

API endpoints have the following rate limits:

| Endpoint Type | Limit | Notes |
|---------------|-------|-------|
| Authenticated reads | 20/min | GET /api/posts, GET /api/subscribers, GET /api/stats |
| Authenticated writes | 10/min | POST, PUT, DELETE operations |
| Public subscribe | 10/min | POST /subscribe |
| Public comments | 20/min | POST /post/<slug>/comment |
| API key check | 1000/hour | Per API key |

Rate limit headers are returned on all responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

When limits are exceeded, `429 Too Many Requests` is returned with `Retry-After` header.

## See Also
- [Admin Routes](routes/admin-routes.md) - Admin dashboard
- [Public Routes](routes/public-routes.md) - Public blog routes
- [RSS/Feeds](routes/rss-feeds.md) - Feed formats
