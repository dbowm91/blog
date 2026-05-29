"""Tags API endpoints."""

from typing import Any, cast

from flask import jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.extensions import db
from app.models import Tag
from app.tag_cache import invalidate_tag_cache
from app.utils import generate_slug
from app.validators import validate_string, validate_tags
from app import limiter
from app.routes.api import api
from app.routes.api.auth import require_api_key, require_scope

DEFAULT_LIMIT = "20 per minute"
WRITE_LIMIT = "10 per minute"


def _tag_to_dict(tag: Tag, include_post_count: bool = False) -> dict:
    """Serialize a Tag model to a dictionary."""
    result = {
        "id": tag.id,
        "name": tag.name,
        "slug": tag.slug,
        "created_at": tag.created_at.isoformat() if tag.created_at else None,
    }
    if include_post_count:
        result["post_count"] = len(tag.posts)
    return result


@api.route("/tags", methods=["GET"])
@require_api_key
@require_scope("tags:read")
@limiter.limit(DEFAULT_LIMIT)
def list_tags() -> Any:
    """List all tags.

    Query params:
        include_count: Include post count (true/false)

    Returns:
        JSON with tags array
    """
    include_count = request.args.get("include_count", "").lower() in ("true", "1", "yes")

    query = select(Tag).order_by(Tag.name)
    tags = db.session.execute(query).scalars().all()

    return jsonify({
        "tags": [_tag_to_dict(t, include_post_count=include_count) for t in tags],
        "total": len(tags),
    })


@api.route("/tags/<int:tag_id>", methods=["GET"])
@require_api_key
@require_scope("tags:read")
@limiter.limit(DEFAULT_LIMIT)
def get_tag(tag_id: int) -> Any:
    """Get a single tag by ID.

    Returns:
        JSON with tag data or 404 error
    """
    tag = db.session.get(Tag, tag_id)
    if not tag:
        return jsonify({"error": "Tag not found"}), 404

    return jsonify(_tag_to_dict(tag))


@api.route("/tags", methods=["POST"])
@require_api_key
@require_scope("tags:write")
@limiter.limit(WRITE_LIMIT)
def create_tag() -> Any:
    """Create a new tag.

    JSON body:
        name: Tag name (required, 1-50 chars)

    Returns:
        JSON with created tag data
    """
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    name = data.get("name")
    if not name:
        return jsonify({"error": "name is required"}), 400

    name, err = validate_string(name, 50, "name")
    if err:
        return jsonify({"error": err}), 400

    tags_list = [name]
    validated, err = validate_tags(tags_list, "name", max_tags=1)
    if err:
        return jsonify({"error": err}), 400
    name = validated[0]

    slug = generate_slug(name)

    existing = db.session.execute(
        select(Tag).filter_by(slug=slug)
    ).scalar_one_or_none()
    if existing:
        return jsonify(_tag_to_dict(existing))

    tag = Tag(name=name, slug=slug)
    db.session.add(tag)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = db.session.execute(
            select(Tag).filter_by(slug=slug)
        ).scalar_one_or_none()
        if existing:
            return jsonify(_tag_to_dict(existing))
        return jsonify({"error": "Failed to create tag"}), 500
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    invalidate_tag_cache()
    return jsonify(_tag_to_dict(tag)), 201


@api.route("/tags/<int:tag_id>", methods=["PUT"])
@require_api_key
@require_scope("tags:write")
@limiter.limit(WRITE_LIMIT)
def update_tag(tag_id: int) -> Any:
    """Update an existing tag.

    JSON body:
        name: New tag name (required, 1-50 chars)

    Returns:
        JSON with updated tag data or 404 error
    """
    tag = db.session.get(Tag, tag_id)
    if not tag:
        return jsonify({"error": "Tag not found"}), 404

    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    name = data.get("name")
    if not name:
        return jsonify({"error": "name is required"}), 400

    name, err = validate_string(name, 50, "name")
    if err:
        return jsonify({"error": err}), 400

    tags_list = [name]
    validated, err = validate_tags(tags_list, "name", max_tags=1)
    if err:
        return jsonify({"error": err}), 400
    name = validated[0]

    slug = generate_slug(name)

    existing = db.session.execute(
        select(Tag).filter(Tag.slug == slug, Tag.id != tag_id)
    ).scalar_one_or_none()
    if existing:
        return jsonify({"error": "A tag with this name already exists"}), 409

    tag.name = name
    tag.slug = slug

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Database constraint violation"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    invalidate_tag_cache()
    return jsonify(_tag_to_dict(tag))


@api.route("/tags/<int:tag_id>", methods=["DELETE"])
@require_api_key
@require_scope("tags:write")
@limiter.limit(WRITE_LIMIT)
def delete_tag(tag_id: int) -> Any:
    """Delete a tag.

    Returns:
        JSON with success message or 404 error
    """
    tag = db.session.get(Tag, tag_id)
    if not tag:
        return jsonify({"error": "Tag not found"}), 404

    name = tag.name
    db.session.delete(tag)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Database constraint violation"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    invalidate_tag_cache()
    return jsonify({"message": f"Tag '{name}' deleted successfully"})