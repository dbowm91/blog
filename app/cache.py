import threading
import time as _time

from app.extensions import db
from app.models import Post, post_tags
from sqlalchemy import func

_TAG_COUNTS_CACHE = {"data": None, "timestamp": 0}
_TAG_CACHE_LOCK = threading.Lock()


def _get_tag_ttl():
    from app.config import TAG_CACHE_TTL_SECONDS
    return TAG_CACHE_TTL_SECONDS


def invalidate_tag_cache():
    """Invalidate the tag counts cache."""
    with _TAG_CACHE_LOCK:
        _TAG_COUNTS_CACHE["data"] = None
        _TAG_COUNTS_CACHE["timestamp"] = 0


def _get_tag_counts():
    ttl = _get_tag_ttl()
    # Fast path: return cached copy if still valid
    with _TAG_CACHE_LOCK:
        now = _time.monotonic()
        if _TAG_COUNTS_CACHE["data"] is not None and (now - _TAG_COUNTS_CACHE["timestamp"]) < ttl:
            return _TAG_COUNTS_CACHE["data"].copy()

    # Slow path: query DB outside lock so concurrent requests aren't blocked
    # by a slow query. Another thread may populate the cache while we query;
    # the second check below (under lock) handles that correctly.
    counts = (
        db.session.query(post_tags.c.tag_id, func.count(post_tags.c.post_id))
        .join(Post, Post.id == post_tags.c.post_id)
        .filter(Post.published == True)
        .group_by(post_tags.c.tag_id)
        .all()
    )
    result = {row[0]: row[1] for row in counts}

    with _TAG_CACHE_LOCK:
        now = _time.monotonic()
        if _TAG_COUNTS_CACHE["data"] is None or (now - _TAG_COUNTS_CACHE["timestamp"]) >= ttl:
            _TAG_COUNTS_CACHE["data"] = result
            _TAG_COUNTS_CACHE["timestamp"] = now
            return result.copy()
        return _TAG_COUNTS_CACHE["data"].copy()
