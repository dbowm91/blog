"""Slug generation service for generating unique slugs."""

import uuid
from typing import Optional, Type

from sqlalchemy import select

from app.extensions import db


def generate_unique_slug(
    model: Type, title: str, exclude_id: Optional[int] = None
) -> str:
    """Generate a unique slug for the given model.

    Args:
        model: The SQLAlchemy model class (Post or Page)
        title: The title to generate a slug from
        exclude_id: Optional ID to exclude from uniqueness check (for edits)

    Returns:
        A unique slug string
    """
    slug = model.generate_slug(title)
    base_slug = slug
    counter = 2
    while counter <= 100:
        q = select(model).filter(model.slug == slug)
        if exclude_id is not None:
            q = q.filter(model.id != exclude_id)
        if not db.session.execute(q).scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
    if counter > 100:
        slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"
    return slug
