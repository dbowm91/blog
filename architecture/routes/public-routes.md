# Public Routes (`app/routes/public/`)

Public routes serve the blog's public-facing pages.

## Route Files

| File | Routes | Purpose |
|------|--------|---------|
| `browse.py` | `/`, `/page/<page>`, `/tag/<tag>`, `/tag/<tag>/<page>`, `/archive`, `/series/<slug>`, `/page/<slug>`, `/search` | Home, archive, tag pages, series, static pages |
| `posts.py` | `/post/<slug>`, `/preview/<int:post_id>`, `/s/<code>`, `/api/track-share` | Individual post pages, short URLs, share tracking |
| `subscribe.py` | `/subscribe`, `/confirm/<token>`, `/unsubscribe/<token>` | Newsletter subscription |
| `meta.py` | `/sitemap.xml`, `/robots.txt`, `/health`, `/metrics`, `/favicon.ico` | Sitemap, robots, health check, metrics |
| `comments.py` | `/post/<slug>/comment` (POST) | Comment submission |

## Browse Routes (`browse.py`)

### Home Page
- **Route**: `GET /` and `GET /page/<int:page>`
- **Purpose**: Display paginated list of published posts
- **Template**: `public/index.html`
- **Context**: Recent posts, tag cloud, page number

### Tag Pages
- **Route**: `GET /tag/<slug>` and `GET /tag/<slug>/<int:page>`
- **Purpose**: Display posts filtered by tag
- **Template**: `public/tag.html`

### Search
- **Route**: `GET /search`
- **Query Params**: `q` (search query)
- **Purpose**: Full-text search using FTS5
- **Template**: `public/search.html`

### Archive
- **Route**: `GET /archive`
- **Purpose**: Browse posts by year/month
- **Template**: `public/archive.html`

### Series
- **Route**: `GET /series/<slug>`
- **Purpose**: Display posts in a series
- **Template**: `public/series.html`

### Static Page
- **Route**: `GET /page/<slug>`
- **Purpose**: Display static pages

## Post Routes (`posts.py`)

### Published Post
- **Route**: `GET /post/<slug>`
- **Purpose**: Display single published post
- **Template**: `public/post.html`
- **Features**: Related posts, comments, share buttons

### Preview Post
- **Route**: `GET /preview/<int:post_id>?token=<hmac>&expires=<timestamp>`
- **Purpose**: Preview unpublished/scheduled posts via signed token
- **Auth**: HMAC token-based (no login required)
- **Args**: `token` (HMAC signature), `expires` (Unix timestamp)

### Short URL Redirect
- **Route**: `GET /s/<code>`
- **Purpose**: Redirect base62-encoded post ID to canonical URL and track share event

### Share Tracking API
- **Route**: `POST /api/track-share`
- **Purpose**: Track social share events

## Subscribe Routes (`subscribe.py`)

### Subscribe
- **Route**: `POST /subscribe`
- **Purpose**: Handle new subscription (only POST exists; no GET handler)

### Confirm Subscription
- **Route**: `GET /confirm/<token>`
- **Purpose**: Confirm subscriber email

### Unsubscribe
- **Route**: `GET /unsubscribe/<token>`
- **Purpose**: Unsubscribe from newsletter

## Meta Routes (`meta.py`)

### Sitemap
- **Route**: `GET /sitemap.xml`
- **Purpose**: XML sitemap for search engines
- **Cache**: 5 minutes

### Robots.txt
- **Route**: `GET /robots.txt`
- **Purpose**: robots.txt for search engines

### Health Check
- **Route**: `GET /health`
- **Purpose**: Health check endpoint with optional `?detailed=1`
- **Auth**: Optional secret via `HEALTH_CHECK_SECRET`

### Metrics
- **Route**: `GET /metrics`
- **Purpose**: Prometheus-compatible metrics endpoint

### Favicon
- **Route**: `GET /favicon.ico`
- **Purpose**: Redirects to SVG favicon

## Comment Routes (`comments.py`)

### Submit Comment
- **Route**: `POST /post/<slug>/comment`
- **Purpose**: Submit a comment on a post
- **Fields**: author_name, author_email, content, parent_id (optional)
- **Moderation**: Comments require approval

## See Also
- [RSS/Feeds](routes/rss-feeds.md) - RSS, Atom, JSON feeds
- [Admin Routes](routes/admin-routes.md) - Admin dashboard routes
- [API Routes](routes/api-routes.md) - REST API endpoints
