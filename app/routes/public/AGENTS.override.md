# Public Routes Module Override

## Purpose
Public-facing routes for blog readers (homepage, posts, pages, search, RSS/Atom feeds).

## Structure
This is a **package** (not a single file like `api.py`):
- `__init__.py` - Package init
- `browse.py` - Homepage, archive, tag pages
- `posts.py` - Individual post view, series
- `subscribe.py` - Newsletter subscription
- `meta.py` - Sitemap, robots.txt
- `comments.py` - Public comment viewing
- `media.py` - Serves uploaded media from the configured upload folder

## Key Routes
- `/` - Homepage dispatcher (blog, static page, or project)
- `/posts` - Blog post index
- `/projects` and `/projects/<slug>` - Published project directory and landing pages; draft projects return 404
- `/post/<slug>` - Individual post
- `/archive` - Archive by year/month
- `/tag/<tag>` - Posts by tag
- `/search` - Full-text search
- `/rss`, `/atom`, `/json` - Feed endpoints
- `/subscribe`, `/confirm/<token>`, `/unsubscribe/<token>` - Newsletter
- `/comments/<post_id>` - View comments
- `/static/uploads/<path:filename>` - Uploaded media, served from `UPLOAD_FOLDER`

## Performance Notes
- Uses `joinedload(Post.tags)` to fix N+1 queries
- FTS5 search with native `bm25()` and `snippet()`
- Page view buffer enabled in production
