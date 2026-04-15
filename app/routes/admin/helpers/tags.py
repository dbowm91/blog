"""Tag-related helpers for admin routes."""

from flask import flash
from sqlalchemy import delete, select

from app.extensions import db
from app.models import Tag
from app.routes.admin.helpers.shared import TAG_NAME_REGEX


def validate_tag_name(name: str) -> tuple[bool, str]:
    if not name or not TAG_NAME_REGEX.match(name):
        return (
            False,
            "Invalid tag name. Use only ASCII letters, numbers, spaces, and hyphens.",
        )
    if len(name) > 50:
        return False, "Tag name must be 50 characters or fewer."
    return True, ""


def _cleanup_orphan_tags() -> None:
    from app.models import post_tags

    orphan_tag_ids = (
        db.session.execute(
            select(Tag.id)
            .outerjoin(post_tags, Tag.id == post_tags.c.tag_id)
            .filter(post_tags.c.post_id.is_(None))
        )
        .scalars()
        .all()
    )
    if orphan_tag_ids:
        db.session.execute(delete(Tag).where(Tag.id.in_(orphan_tag_ids)))


def _get_or_create_tags(names: list[str]) -> list[Tag]:
    tags = []
    invalid_tags = []
    for name in names:
        name = name.strip()[:50]
        if not name:
            continue
        is_valid, _ = validate_tag_name(name)
        if not is_valid:
            invalid_tags.append(name)
            continue
        slug = Tag.generate_slug(name)
        tag = db.session.execute(select(Tag).filter_by(slug=slug)).scalar_one_or_none()
        if not tag:
            tag = Tag(name=name, slug=slug)
            db.session.add(tag)
        tags.append(tag)
    if invalid_tags:
        flash(f"Invalid tag names (skipped): {', '.join(invalid_tags)}", "warning")
    return tags
