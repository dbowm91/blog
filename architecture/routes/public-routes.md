# Public Routes (`app/routes/public/`)

Public routes serve the blog's public-facing pages.

## Route Files

| File | Routes | Purpose |
|------|--------|---------|
| `browse.py` | `/`, `/page/<page>`, `/tag/<tag>`, `/tag/<tag>/<page>`, `/search` | Home, archive, tag pages |
| `posts.py` | `/post/<slug>`, `/post/<slug>/preview/<token>` | Individual post pages |
| `subscribe.py` | `/subscribe`, `/confirm/<token>`, `/unsubscribe/<token>` | Newsletter subscription |
| `meta.py` | `/sitemap.xml`, `/robots.txt`, `/health` | Sitemap, robots, health check |
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

## Post Routes (`posts.py`)

### Published Post
- **Route**: `GET /post/<slug>`
- **Purpose**: Display single published post
- **Template**: `public/post.html`
- **Features**: Related posts, comments, share buttons

### Preview Post
- **Route**: `GET /post/<slug>/preview/<token>`
- **Purpose**: Preview unpublished/scheduled posts
- **Auth**: Token-based (no login required)

## Subscribe Routes (`subscribe.py`)

### Subscribe
- **Route**: `GET /subscribe`
- **Purpose**: Show subscription form
- **Route**: `POST /subscribe`
- **Purpose**: Handle new subscription

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
- **Purpose**: Health check endpoint
- **Auth**: Optional secret via `HEALTH_CHECK_SECRET`

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
