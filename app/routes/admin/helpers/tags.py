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
    if not names:
        return []

    invalid_tags = []
    valid_names = []
    for name in names:
        name = name.strip()[:50]
        if not name:
            continue
        is_valid, _ = validate_tag_name(name)
        if not is_valid:
            invalid_tags.append(name)
        else:
            valid_names.append(name)

    if not valid_names:
        if invalid_tags:
            flash(f"Invalid tag names (skipped): {', '.join(invalid_tags)}", "warning")
        return []

    slugs = [Tag.generate_slug(name) for name in valid_names]
    existing = db.session.execute(select(Tag).filter(Tag.slug.in_(slugs))).scalars().all()
    existing_by_slug = {tag.slug: tag for tag in existing}

    tags = []
    for name in valid_names:
        slug = Tag.generate_slug(name)
        tag = existing_by_slug.get(slug)
        if not tag:
            tag = Tag(name=name, slug=slug)
            db.session.add(tag)
        tags.append(tag)

    if invalid_tags:
        flash(f"Invalid tag names (skipped): {', '.join(invalid_tags)}", "warning")
    return tags
