"""Tag management service for centralized tag operations."""

from typing import List, Optional

from sqlalchemy import select, func

from app.extensions import db
from app.models import Tag, Post
from app.utils import generate_slug


def get_or_create_tags(tag_names: List[str]) -> List[Tag]:
    """Get existing tags or create new ones from a list of tag names.

    Args:
        tag_names: List of tag name strings

    Returns:
        List of Tag model instances
    """
    tags: List[Tag] = []
    for name in tag_names:
        slug = generate_slug(name)
        tag = db.session.execute(select(Tag).filter_by(slug=slug)).scalar_one_or_none()
        if not tag:
            tag = Tag(name=name, slug=slug)
            db.session.add(tag)
        tags.append(tag)
    return tags


def get_tag_by_slug(slug: str) -> Optional[Tag]:
    """Get a tag by its slug."""
    return db.session.execute(select(Tag).filter_by(slug=slug)).scalar_one_or_none()


def get_all_tags() -> List[Tag]:
    """Get all tags ordered by name."""
    return list(db.session.execute(select(Tag).order_by(Tag.name)).scalars().all())


def get_tag_post_count(tag_id: int) -> int:
    """Get the number of published posts for a tag."""
    return (
        db.session.execute(
            select(func.count(Post.id))
            .select_from(Tag)
            .outerjoin(Post.tags)
            .filter(Tag.id == tag_id, Post.published)
        ).scalar_one_or_none()
        or 0
    )


def delete_tag_if_unused(tag: Tag) -> bool:
    """Delete a tag if it has no associated posts.

    Returns:
        True if deleted, False if tag still has posts

    Note:
        Slug generation for new tags uses a collision limit of 100 tries
        before falling back to UUID suffix (see `app/services/slug.py`).
    """
    if tag.posts:
        return False
    db.session.delete(tag)
    db.session.commit()
    return True
