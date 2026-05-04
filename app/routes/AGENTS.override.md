# Routes Agent Override

Specialized handling for public routes, API, and RSS.

## Key Files

- `public.py` - Public-facing routes (index, post, page, tag, series, archive, search, share, subscribe, confirm, unsubscribe)
- `api.py` - REST API (Post/Subscriber endpoints) - **Modularized into `app/routes/api/` package (Wave 2 complete)**
- `rss.py` - RSS feed generation
- `errors.py` - Error handlers
- `admin/` - Admin routes package (requires login)

## Public Routes

- `/` - Homepage with recent posts
- `/<slug>` - Post view
- `/page/<slug>` - Static page view
- `/tag/<slug>` - Tag archive
- `/series/<slug>` - Series archive
- `/archive` - Full archive
- `/search` - Search results
- `/s/<code>` - Short URL redirect
- `/subscribe` - Newsletter subscription
- `/confirm/<token>` - Email confirmation
- `/unsubscribe/<token>` - Unsubscribe

## Share Tracking

POST `/share` tracks share events. `ALLOWED_SHARE_PLATFORMS` in public.py expects `"hackernews"` not `"hn"`. Always check that template `data-platform` attributes match the API constants.

## Related Posts

`_get_related_posts()` in `public.py` uses tag intersection scoring:
- Subquery counts shared tags per post via `post_tags` table
- Orders by `shared_count DESC, created_at DESC`
- Uses `.unique()` after `.options(joinedload(Post.tags))` to avoid SQLAlchemy "unique() required" error
- Configurable via `RELATED_POSTS_COUNT` in `config.toml` (default: 3, hard limit: 6)

## FTS5 Search (`app/search.py`)

- FTS5 virtual table `posts_fts` (title, body, summary) with `prefix='2 3 4'` for prefix matching
- Prefix search enabled: searching "Py" matches "Python" (automatically appends `*` to terms)
- **FTS5 Sync Timing**: 
    - `sync_fts()` MUST be called **BEFORE** `db.session.commit()` for create/edit/publish.
    - `remove_fts()` MUST be called **AFTER** `db.session.commit()` for delete.
- FTS table existence cached with 5-minute TTL
- LIKE fallback filters by `Post.published == True`
- "Did you mean?" suggestions via `difflib.get_close_matches()`
- Query term highlighting with `<mark>` tags

## LIKE Wildcard Escaping

Search input containing `%` or `_` causes unexpected pattern matching. Escape them before interpolating:
```python
escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
search_term = f"%{escaped}%"
Post.title.ilike(search_term, escape="\\")
```

## Session

- `session["viewed_posts"]` tracks viewed post IDs to avoid double-counting page views—capped at `MAX_VIEWED_POSTS` (default 100)
- Session configuration: `SESSION_COOKIE_SECURE` defaults to "true", `SESSION_COOKIE_SAMESITE` is `"Lax"`

## API Authentication

- REST API uses `X-API-Key` header (env var `API_KEY`)
- API key comparison using `hmac.compare_digest()` (timing-safe)

## API Error Handling

All `db.session.commit()` calls in API endpoints must be wrapped in try/except for `IntegrityError` and `OperationalError`. Return 409 Conflict on duplicate slug, 500 Internal Server Error on operational errors. Import from `sqlalchemy.exc`.

## API Input Validation

Input validation via `app/validators.py`:
- `validate_string(value, max_length, field_name)` - validates string fields
- `validate_email(value, max_length)` - validates email format and length
- `validate_boolean(value, field_name)` - validates boolean fields
- Returns `(value, error_message)` tuple

## Feed Formats

- **RSS 2.0**: `/rss` (cached 5 min)
- **Atom 1.0**: `/atom`
- **JSON Feed 1.1**: `/json` (includes `content_html`)
- Cache invalidation on post publish/unpublish/delete

## JSON Feed content_html

The JSON Feed 1.1 spec requires either `content_html` or `content_text`. The `/json` endpoint must include `content_html`. See `app/routes/rss.py`.

## Sitemap

Dynamic sitemap.xml generation at `/sitemap.xml`:
- Includes homepage, archive page, static pages, posts, and tags
- Uses streaming XML generation to handle large sites
- Respects `BASE_URL` from config

## Open Graph / Social Meta

Templates include Open Graph and Twitter Card meta tags:
- `og:image` and `twitter:image` in `post.html`, `page.html`, `index.html`
- Defaults to `/static/img/default-post.svg` when no image set

## Token Enumeration Prevention

/confirm/<token> uses `scalar_one_or_none()` + `time.sleep(0.1)` to prevent token enumeration. Invalid tokens return success (not 404).