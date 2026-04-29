"""Tag count caching using flask-caching."""

__all__ = ["_get_tag_counts", "invalidate_tag_cache", "_build_tag_counts_query"]

from flask import has_request_context
from sqlalchemy import select, func
from sqlalchemy.engine import Row

from app import cache as flask_cache
from app.config import TAG_CACHE_TTL_SECONDS
from app.extensions import db
from app.models import Post, post_tags


def _build_tag_counts_query() -> list[Row]:
    """Build the tag counts query, returning raw rows.

    Returns:
        List of Row objects with tag_id and cnt columns.
    """
    return db.session.execute(
        select(post_tags.c.tag_id, func.count(post_tags.c.post_id).label("cnt"))
        .join(Post, Post.id == post_tags.c.post_id)
        .filter(Post.published == True)
        .group_by(post_tags.c.tag_id)
    ).all()


@flask_cache.memoize(timeout=TAG_CACHE_TTL_SECONDS)
def _get_tag_counts_cached():
    """Cached tag counts query."""
    rows = _build_tag_counts_query()
    return {row[0]: row[1] for row in rows}


def _get_tag_counts():
    """Get tag counts with caching."""
    if has_request_context():
        return _get_tag_counts_cached()
    return _get_tag_counts_uncached()


def _get_tag_counts_uncached():
    """Uncached tag counts query (for non-request contexts)."""
    rows = _build_tag_counts_query()
    return {row[0]: row[1] for row in rows}


def invalidate_tag_cache():
    """Invalidate tag count cache."""
    flask_cache.delete_memoized(_get_tag_counts_cached)
