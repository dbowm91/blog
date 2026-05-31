# Public Routes (`app/routes/public/`)

Public routes serve the blog's public-facing pages.

## Route Files

| File | Routes | Purpose |
|------|--------|---------|
| `browse.py` | `/`, `/tag/<slug>`, `/archive`, `/series/<slug>`, `/page/<slug>`, `/search` | Home, archive, tag pages, series, static pages |
| `posts.py` | `/post/<slug>`, `/preview/<int:post_id>`, `/s/<code>`, `/api/track-share` | Individual post pages, short URLs, share tracking |
| `subscribe.py` | `/subscribe`, `/confirm/<token>`, `/unsubscribe/<token>` | Newsletter subscription |
| `meta.py` | `/sitemap.xml`, `/robots.txt`, `/health`, `/metrics`, `/favicon.ico` | Sitemap, robots, health check, metrics |
| `comments.py` | `/post/<slug>/comment` (POST) | Comment submission |

## Browse Routes (`browse.py`)

### Home Page
- **Route**: `GET /`
- **Purpose**: Display paginated list of published posts (pagination via `?page=N` query param)
- **Template**: `public/index.html`
- **Context**: Recent posts, tag cloud, page number

### Tag Pages
- **Route**: `GET /tag/<slug>`
- **Purpose**: Display posts filtered by tag (pagination via `?page=N` query param)
- **Template**: `public/tag.html`

### Search
- **Route**: `GET /search`
- **Query Params**: `q` (search query)
- **Purpose**: Full-text search using FTS5
- **Template**: `public/search.html`

### Archive
- **Route**: `GET /archive`
- **Purpose**: Browse posts by year/month with cursor-based pagination
- **Template**: `public/archive.html`
- **Query Params**: `cursor` (ISO datetime string for pagination), `direction` (`next` or `prev`, default: `next`), `year` (filter by year)
- **Pagination**: Returns up to 200 posts per page (`ARCHIVE_PER_PAGE`). Cursor is the `created_at` timestamp of the last/first post in the current page. `has_next`/`has_prev` booleans indicate available navigation.

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
- **Auth**: HMAC token-based (token and expires query parameters)
- **Args**: `token` (HMAC signature), `expires` (Unix timestamp)

### Short URL Redirect
- **Route**: `GET /s/<code>`
- **Purpose**: Redirect base62-encoded post ID to canonical URL and track share event

### Share Tracking API
- **Route**: `POST /api/track-share`
- **Purpose**: Track social share events

## Comment Routes (`comments.py`)

### Submit Comment
- **Route**: `POST /post/<slug>/comment`
- **Purpose**: Submit a comment on a post
- **Fields**: author_name, author_email, content, parent_id (optional), csrf_token (hidden)
- **Moderation**: Comments require approval
- **Rate Limit**: 10 per minute
- **CSRF**: Requires valid `csrf_token` in form data
- **Spam Scoring**: `compute_spam_score()` (`app/routes/public/comments.py:41-74`) evaluates comments using heuristics:
  - Excessive links (>3 URLs: +0.15, >5: +0.3)
  - Repeated characters (5+ same char: +0.2)
  - Configured spam words (`COMMENT_SPAM_WORDS` config: +0.25)
  - Author name looks like email (+0.15)
  - Mostly uppercase content (>70% of alpha chars: +0.2)
  - Score capped at 1.0; threshold 0.7 triggers auto-quarantine (`is_spam=True`)
- **Honeypot**: Hidden `website_url` field — if filled, comment is silently accepted but not processed

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

### Robots.txt
- **Route**: `GET /robots.txt`
- **Purpose**: robots.txt for search engines

### Health Check
- **Route**: `GET /health`
- **Purpose**: Health check endpoint with optional `?detailed=true` and `?secret=<HEALTH_CHECK_SECRET>` query parameters
- **Auth**: Optional HMAC authentication when `HEALTH_CHECK_SECRET` is configured

### Metrics
- **Route**: `GET /metrics`
- **Purpose**: Prometheus-compatible metrics endpoint

### Favicon
- **Route**: `GET /favicon.ico`
- **Purpose**: Redirects to SVG favicon

## See Also
- [RSS/Feeds](rss-feeds.md) - RSS, Atom, JSON feeds
- [Admin Routes](admin-routes.md) - Admin dashboard routes
- [API Routes](api-routes.md) - REST API endpoints
