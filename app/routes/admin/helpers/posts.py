"""Post-related helpers for admin routes."""

from sqlalchemy import select, Select
from sqlalchemy.orm import joinedload, QueryableAttribute
from typing import cast, Any, Optional

from app.models import Post
from app.utils import utc_now
from app.routes.admin.helpers.tags import _get_or_create_tags


from sqlalchemy.sql.expression import Select


def _get_posts_query(status: str, search: str, order_by: Optional[Any] = None) -> Select[Any]:
    base_q = select(Post).options(joinedload(cast(QueryableAttribute, Post.tags)))
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search_term = f"%{escaped}%"
        base_q = base_q.filter(Post.title.ilike(search_term, escape="\\"))
    if status == "published":
        base_q = base_q.filter(Post.published)
    elif status == "draft":
        base_q = base_q.filter(Post.published.is_(False))
    elif status == "scheduled":
        base_q = base_q.filter(Post.published.is_(False), Post.scheduled_publish_at.isnot(None))
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
    scheduled_publish_at: Any,
    tag_names: list[str],
) -> Post:
    post.title = title
    post.body = body
    post.summary = summary
    post.published = published
    post.scheduled_publish_at = scheduled_publish_at
    if published and not was_published:
        post.published_at = utc_now()
    setattr(post, "tags", _get_or_create_tags(tag_names))
    return post
