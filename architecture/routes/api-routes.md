# API Routes (`app/routes/api/`)

REST API for programmatic access to blog data.

## Endpoints

| File | Endpoint | Methods | Purpose |
|------|----------|---------|---------|
| `posts.py` | `/api/posts` | GET, POST | List/create posts |
| `posts.py` | `/api/posts/<id>` | GET, PUT, DELETE | Single post operations (publish via PUT with `published` field) |
| `subscribers.py` | `/api/subscribers` | GET | List subscribers |
| `subscribers.py` | `/api/subscribers/export` | POST | Export subscribers |
| `stats.py` | `/api/stats` | GET | Dashboard statistics |
| `auth.py` | `/api/auth` | POST | API key authentication |

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

### Publish Post
```
POST /api/posts/<id>/publish
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
```
POST /api/subscribers/export
```
Response: CSV file download

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

## See Also
- [Admin Routes](routes/admin-routes.md) - Admin dashboard
- [Public Routes](routes/public-routes.md) - Public blog routes
- [RSS/Feeds](routes/rss-feeds.md) - Feed formats
