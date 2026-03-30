import threading
import time as _time

from app.extensions import db
from app.models import Post, post_tags
from sqlalchemy import func

_TAG_COUNTS_CACHE = {"data": None, "timestamp": 0}
_TAG_COUNTS_TTL = 60
_TAG_CACHE_LOCK = threading.Lock()


def invalidate_tag_cache():
    """Invalidate the tag counts cache."""
    with _TAG_CACHE_LOCK:
        _TAG_COUNTS_CACHE["data"] = None
        _TAG_COUNTS_CACHE["timestamp"] = 0


def _get_tag_counts():
    with _TAG_CACHE_LOCK:
        now = _time.monotonic()
        if _TAG_COUNTS_CACHE["data"] is not None and (now - _TAG_COUNTS_CACHE["timestamp"]) < _TAG_COUNTS_TTL:
            return _TAG_COUNTS_CACHE["data"].copy()

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
        if _TAG_COUNTS_CACHE["data"] is None or (now - _TAG_COUNTS_CACHE["timestamp"]) >= _TAG_COUNTS_TTL:
            _TAG_COUNTS_CACHE["data"] = result
            _TAG_COUNTS_CACHE["timestamp"] = now
            return result.copy()
        return _TAG_COUNTS_CACHE["data"].copy()
