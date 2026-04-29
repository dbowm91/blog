"""Tag count caching using flask-caching."""

__all__ = ["_get_tag_counts", "invalidate_tag_cache"]

from flask import has_request_context
from sqlalchemy import select, func

from app import cache as flask_cache
from app.config import TAG_CACHE_TTL_SECONDS
from app.extensions import db
from app.models import Post, post_tags


@flask_cache.memoize(timeout=TAG_CACHE_TTL_SECONDS)
def _get_tag_counts_cached():
    """Cached tag counts query."""
    counts = db.session.execute(
        select(post_tags.c.tag_id, func.count(post_tags.c.post_id).label("cnt"))
        .join(Post, Post.id == post_tags.c.post_id)
        .filter(Post.published == True)
        .group_by(post_tags.c.tag_id)
    ).all()
    return {row[0]: row[1] for row in counts}


def _get_tag_counts():
    """Get tag counts with caching."""
    if has_request_context():
        return _get_tag_counts_cached()
    return _get_tag_counts_uncached()


def _get_tag_counts_uncached():
    """Uncached tag counts query (for non-request contexts)."""
    counts = db.session.execute(
        select(post_tags.c.tag_id, func.count(post_tags.c.post_id).label("cnt"))
        .join(Post, Post.id == post_tags.c.post_id)
        .filter(Post.published == True)
        .group_by(post_tags.c.tag_id)
    ).all()
    return {row[0]: row[1] for row in counts}


def invalidate_tag_cache():
    """Invalidate tag count cache."""
    flask_cache.delete_memoized(_get_tag_counts_cached)
