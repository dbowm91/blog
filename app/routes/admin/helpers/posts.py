"""Post-related helpers for admin routes."""

from flask import current_app, flash
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import Post
from app.utils import utc_now
from app.routes.admin.helpers.tags import _get_or_create_tags


def _get_posts_query(status: str, search: str, order_by=None) -> select:
    base_q = select(Post).options(joinedload(Post.tags))
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search_term = f"%{escaped}%"
        base_q = base_q.filter(Post.title.ilike(search_term, escape="\\"))
    if status == "published":
        base_q = base_q.filter(Post.published == True)
    elif status == "draft":
        base_q = base_q.filter(Post.published == False)
    elif status == "scheduled":
        base_q = base_q.filter(
            Post.published == False, Post.scheduled_publish_at != None
        )
    if order_by is None:
        order_by = Post.updated_at.desc()
    return base_q.order_by(order_by)


def _apply_post_updates(
    post: Post,
    title: str,
    body: str,
    summary: str,
    published: bool,
    was_published: bool,
    scheduled_publish_at,
    tag_names: list[str],
) -> Post:
    post.title = title
    post.body = body
    post.summary = summary
    post.published = published
    post.scheduled_publish_at = scheduled_publish_at
    if published and not was_published:
        post.published_at = utc_now()
    post.tags = _get_or_create_tags(tag_names)
    return post
