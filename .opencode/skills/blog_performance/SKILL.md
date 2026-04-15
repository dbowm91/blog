# Performance Optimization Patterns

This skill documents the performance patterns implemented in the blog CMS.

## Caching Patterns

### 1. TTL-based In-memory Cache with Double-Checked Locking

Used for tag counts, site settings, and footer data:

```python
_CACHE: dict[str, object] = {"data": None, "timestamp": 0}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL = 300  # seconds

def _get_cached():
    with _CACHE_LOCK:
        now = _time.monotonic()
        if _CACHE["data"] is not None and (now - _CACHE["timestamp"]) < _CACHE_TTL:
            return _CACHE["data"].copy()
    # Query DB outside lock
    data = _query_db()
    with _CACHE_LOCK:
        now = _time.monotonic()
        if _CACHE["data"] is None or (now - _CACHE["timestamp"]) >= _CACHE_TTL:
            _CACHE["data"] = data
            _CACHE["timestamp"] = now
        return _CACHE["data"].copy()
```

Key points:
- Lock check is OUTSIDE the DB query to avoid blocking concurrent requests
- Second check UNDER lock handles race condition where another thread populated cache
- Returns a copy to prevent external mutation
- Uses `time.monotonic()` for TTL (not `time.time()` which can jump)

### 2. Request-level Cache with Flask `g`

Used for tag list caching across multiple queries within a single request:

```python
from flask import g

def _get_cached_tags_and_counts():
    if not hasattr(g, "_cached_tags"):
        g._cached_tags = db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()
    if not hasattr(g, "_cached_tag_counts"):
        g._cached_tag_counts = _get_tag_counts()
    return g._cached_tags, g._cached_tag_counts
```

### 3. Cache Invalidation

Call `invalidate_*` functions when underlying data changes:

```python
def invalidate_tag_cache() -> None:
    with _TAG_CACHE_LOCK:
        _TAG_COUNTS_CACHE["data"] = None
        _TAG_COUNTS_CACHE["timestamp"] = 0
```

## Query Optimization

### 1. LEFT JOIN for Combined Queries

Instead of N+1 queries, combine with LEFT JOIN:

```python
# BEFORE (2 queries):
tags = db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()
tag_counts = dict(db.session.execute(
    select(post_tags.c.tag_id, func.count(post_tags.c.post_id))
    .group_by(post_tags.c.tag_id)
).all())

# AFTER (1 query):
rows = db.session.execute(
    select(Tag, func.count(post_tags.c.post_id).label("cnt"))
    .outerjoin(post_tags, Tag.id == post_tags.c.tag_id)
    .group_by(Tag.id)
    .order_by(Tag.name)
).all()
tags = [row[0] for row in rows]
tag_counts = {row[0].id: row[1] for row in rows}
```

### 2. CTE for Derived Values

Derive values from existing queries instead of new queries:

```python
# Create CTE for daily views
daily_views_cte = select(
    func.date(PageView.created_at).label("date"),
    func.count(PageView.id).label("views"),
).filter(PageView.created_at >= start_date).group_by(
    func.date(PageView.created_at)
).cte()

# Derive total_views from CTE (no new query)
total_views = db.session.execute(
    select(func.sum(daily_views_cte.c.views))
).scalar_one()
```

### 3. Subqueries with OUTER JOIN

For dashboard post view/share counts:

```python
view_counts_sq = (
    select(PageView.post_id, func.count(PageView.id).label("cnt"))
    .where(PageView.post_id.in_(post_ids))
    .group_by(PageView.post_id)
    .subquery()
)
share_counts_sq = (
    select(ShareEvent.post_id, func.count(ShareEvent.id).label("cnt"))
    .where(ShareEvent.post_id.in_(post_ids))
    .group_by(ShareEvent.post_id)
    .subquery()
)
rows = db.session.execute(
    select(
        Post.id,
        func.coalesce(view_counts_sq.c.cnt, 0).label("views"),
        func.coalesce(share_counts_sq.c.cnt, 0).label("shares"),
    )
    .outerjoin(view_counts_sq, Post.id == view_counts_sq.c.post_id)
    .outerjoin(share_counts_sq, Post.id == share_counts_sq.c.post_id)
    .where(Post.id.in_(post_ids))
).all()
```

## Database Indexes

Key indexes for performance:

- `ix_posts_published_created`: (published, created_at) - for post listings
- `ix_posts_published_updated`: (published, updated_at) - for dashboard
- `ix_page_views_post_created`: (post_id, created_at) - for view counts
- `ix_page_views_referrer`: (referrer, created_at) - for analytics referrer aggregation
- `ix_share_events_post_created`: (post_id, created_at) - for share counts

Add new indexes for `__table_args__`:

```python
__table_args__ = (
    db.Index("ix_table_column", "column"),
    db.Index("ix_table_composite", "col1", "col2"),
)
```

## Session Optimization

For viewed_posts tracking:

```python
# BEFORE: append + slice from end
viewed.append(post.id)
if len(viewed) > MAX_VIEWED_POSTS:
    viewed = viewed[-MAX_VIEWED_POSTS:]

# AFTER: prepend + deduplicate + slice from front
if post.id in viewed:
    viewed.remove(post.id)
viewed.insert(0, post.id)
if len(viewed) > MAX_VIEWED_POSTS:
    viewed = viewed[:MAX_VIEWED_POSTS]
```

Benefits:
- Most recent items at front for O(1) lookup
- Deduplication avoids list growth
- Slicing from front is efficient

## Thread-Safe Scheduler Health

For tracking scheduler state:

```python
_last_newsletter_send_lock = threading.Lock()
_last_newsletter_send: Optional[datetime] = None

def get_scheduler_health() -> dict:
    with _last_newsletter_send_lock:
        return {
            "status": "running" if _scheduler_running.is_set() else "stopped",
            "last_newsletter_send": _last_newsletter_send,
        }

def send_daily_newsletter(app):
    # ... send newsletter ...
    with _last_newsletter_send_lock:
        _last_newsletter_send = utc_now()
```

## Async Newsletter Considerations

The ThreadPoolExecutor approach for async sending was reverted due to test compatibility issues. Key lesson: when using ThreadPoolExecutor:

1. Each thread must create its own connections (no shared SMTP)
2. Config values must be passed as arguments (not closure over module globals)
3. Exceptions in threads propagate via `future.result()` and must be caught
4. Test mocks that patch module-level functions don't work with closures

The existing single-SMTP-connection approach with reconnection-on-disconnect is robust and efficient for most use cases.
