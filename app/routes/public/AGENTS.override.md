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
- `comments.py` - Public comment viewing (NEW in Wave 8)

## Key Routes
- `/` - Homepage with post listing
- `/post/<slug>` - Individual post
- `/archive` - Archive by year/month
- `/tag/<tag>` - Posts by tag
- `/search` - Full-text search
- `/rss`, `/atom`, `/json` - Feed endpoints
- `/subscribe`, `/confirm/<token>`, `/unsubscribe/<token>` - Newsletter
- `/comments/<post_id>` - View comments (NEW)

## Performance Notes
- Uses `joinedload(Post.tags)` to fix N+1 (PERF-1, PERF-2)
- FTS5 search with native `bm25()` and `snippet()` (PERF-8)
- Page view buffer enabled in production (PERF-9)
