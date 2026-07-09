"""Series API endpoints."""

from typing import Any, cast

from flask import jsonify, request
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import QueryableAttribute, selectinload

from app.extensions import db
from app.models import Series, Post, PostSeries
from app.utils import generate_slug
from app.validators import validate_string, validate_list, validate_integer
from app import limiter
from app.routes.api import api
from app.routes.api.auth import require_api_key, require_scope

DEFAULT_LIMIT = "20 per minute"
WRITE_LIMIT = "10 per minute"


def _series_to_dict(series: Series, include_posts: bool = False) -> dict:
    """Serialize a Series model to a dictionary."""
    result = {
        "id": series.id,
        "name": series.name,
        "slug": series.slug,
        "description": series.description,
        "image": series.image,
        "created_at": series.created_at.isoformat() if series.created_at else None,
    }
    if include_posts:
        result["posts"] = [
            {
                "id": ps.post.id,
                "title": ps.post.title,
                "slug": ps.post.slug,
                "order_index": ps.order_index,
            }
            for ps in list(cast(Any, series.posts))
        ]
    return result


@api.route("/series", methods=["GET"])
@require_api_key
@require_scope("series:read")
@limiter.limit(DEFAULT_LIMIT)
def list_series() -> Any:
    """List all series.

    Query params:
        page: Page number (default 1)
        per_page: Items per page (default 20, max 100)
        include_posts: Include post list (true/false)

    Returns:
        JSON with series array and pagination info
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    include_posts = request.args.get("include_posts", "").lower() in ("true", "1", "yes")

    query = select(Series).order_by(Series.created_at.desc())
    if include_posts:
        query = query.options(selectinload(cast(QueryableAttribute, Series.posts)))
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "series": [_series_to_dict(s, include_posts=include_posts) for s in pagination.items],
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
        }
    )


@api.route("/series/<int:series_id>", methods=["GET"])
@require_api_key
@require_scope("series:read")
@limiter.limit(DEFAULT_LIMIT)
def get_series(series_id: int) -> Any:
    """Get a single series by ID.

    Query params:
        include_posts: Include post list (true/false)

    Returns:
        JSON with series data or 404 error
    """
    include_posts = request.args.get("include_posts", "").lower() in ("true", "1", "yes")

    query = select(Series).filter(Series.id == series_id)
    if include_posts:
        query = query.options(selectinload(cast(QueryableAttribute, Series.posts)))
    series = db.session.execute(query).scalars().unique().one_or_none()
    if not series:
        return jsonify({"error": "Series not found"}), 404

    return jsonify(_series_to_dict(series, include_posts=include_posts))


@api.route("/series", methods=["POST"])
@require_api_key
@require_scope("series:write")
@limiter.limit(WRITE_LIMIT)
def create_series() -> Any:
    """Create a new series.

    JSON body:
        name: Series name (required)
        description: Series description (optional)
        slug: URL slug (optional, auto-generated if not provided)

    Returns:
        JSON with created series data
    """
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    name = data.get("name")
    if not name:
        return jsonify({"error": "name is required"}), 400
    name, err = validate_string(name, 100, "name")
    if err:
        return jsonify({"error": err}), 400

    description = data.get("description", "")
    if description:
        description, err = validate_string(description, 500, "description")
        if err:
            return jsonify({"error": err}), 400

    slug = data.get("slug")
    if slug:
        slug, err = validate_string(slug, 100, "slug")
        if err:
            return jsonify({"error": err}), 400
        slug = generate_slug(slug)
    else:
        slug = generate_slug(name)

    existing = db.session.execute(select(Series).filter_by(slug=slug)).scalar_one_or_none()
    if existing:
        return jsonify({"error": "A series with this slug already exists"}), 409

    series = Series(
        name=name,
        slug=slug,
        description=description,
    )
    db.session.add(series)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Duplicate slug or database constraint violation"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database operational error"}), 500

    return jsonify(_series_to_dict(series)), 201


@api.route("/series/<int:series_id>", methods=["PUT"])
@require_api_key
@require_scope("series:write")
@limiter.limit(WRITE_LIMIT)
def update_series(series_id: int) -> Any:
    """Update an existing series.

    JSON body (all optional):
        name: Series name
        description: Series description
        slug: URL slug

    Returns:
        JSON with updated series data or 404 error
    """
    series = db.session.get(Series, series_id)
    if not series:
        return jsonify({"error": "Series not found"}), 404

    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    if "name" in data:
        name, err = validate_string(data["name"], 100, "name")
        if err:
            return jsonify({"error": err}), 400
        series.name = name

    if "description" in data:
        description, err = validate_string(data["description"], 500, "description")
        if err:
            return jsonify({"error": err}), 400
        series.description = description

    if "slug" in data:
        slug, err = validate_string(data["slug"], 100, "slug")
        if err:
            return jsonify({"error": err}), 400
        slug = generate_slug(slug)
        if slug != series.slug:
            existing = db.session.execute(
                select(Series).filter(Series.slug == slug, Series.id != series_id)
            ).scalar_one_or_none()
            if existing:
                return jsonify({"error": "A series with this slug already exists"}), 409
            series.slug = slug

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Duplicate slug or database constraint violation"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database operational error"}), 500

    return jsonify(_series_to_dict(series))


@api.route("/series/<int:series_id>", methods=["DELETE"])
@require_api_key
@require_scope("series:write")
@limiter.limit(WRITE_LIMIT)
def delete_series(series_id: int) -> Any:
    """Delete a series.

    Returns:
        JSON with success message or 404 error
    """
    series = db.session.get(Series, series_id)
    if not series:
        return jsonify({"error": "Series not found"}), 404

    name = series.name

    try:
        db.session.execute(PostSeries.__table__.delete().where(PostSeries.series_id == series_id))
        db.session.delete(series)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Database constraint violation"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database operational error"}), 500

    return jsonify({"message": f"Series '{name}' deleted successfully"})


@api.route("/series/<int:series_id>/posts", methods=["POST"])
@require_api_key
@require_scope("series:write")
@limiter.limit(WRITE_LIMIT)
def add_post_to_series(series_id: int) -> Any:
    """Add a post to a series.

    JSON body:
        post_id: Post ID to add (required)
        order_index: Position in series (optional, defaults to end)

    Returns:
        JSON with success message or error
    """
    series = db.session.get(Series, series_id)
    if not series:
        return jsonify({"error": "Series not found"}), 404

    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    post_id = data.get("post_id")
    if not post_id:
        return jsonify({"error": "post_id is required"}), 400

    post_id, err = validate_integer(post_id, "post_id", min_value=1)
    if err:
        return jsonify({"error": err}), 400

    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    existing = db.session.execute(
        select(PostSeries).filter_by(series_id=series_id, post_id=post_id)
    ).scalar_one_or_none()
    if existing:
        return jsonify({"error": "Post is already in this series"}), 409

    order_index = data.get("order_index")
    if order_index is not None:
        order_index, err = validate_integer(order_index, "order_index", min_value=0)
        if err:
            return jsonify({"error": err}), 400
    else:
        max_order = (
            db.session.execute(
                select(func.max(PostSeries.order_index)).filter_by(series_id=series_id)
            ).scalar()
            or 0
        )
        order_index = max_order + 1

    post_series = PostSeries(
        series_id=series_id,
        post_id=post_id,
        order_index=order_index,
    )
    db.session.add(post_series)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Database constraint violation"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify({"message": "Post added to series"}), 201


@api.route("/series/<int:series_id>/posts/<int:post_id>", methods=["DELETE"])
@require_api_key
@require_scope("series:write")
@limiter.limit(WRITE_LIMIT)
def remove_post_from_series(series_id: int, post_id: int) -> Any:
    """Remove a post from a series.

    Returns:
        JSON with success message or 404 error
    """
    series = db.session.get(Series, series_id)
    if not series:
        return jsonify({"error": "Series not found"}), 404

    post_series = db.session.execute(
        select(PostSeries).filter_by(series_id=series_id, post_id=post_id)
    ).scalar_one_or_none()
    if not post_series:
        return jsonify({"error": "Post not found in this series"}), 404

    db.session.delete(post_series)

    try:
        db.session.commit()
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify({"message": "Post removed from series"})


@api.route("/series/<int:series_id>/reorder", methods=["POST"])
@require_api_key
@require_scope("series:write")
@limiter.limit(WRITE_LIMIT)
def reorder_series_posts(series_id: int) -> Any:
    """Reorder posts within a series.

    JSON body:
        order: List of {post_id, order_index} objects

    Returns:
        JSON with success message or error
    """
    series = db.session.get(Series, series_id)
    if not series:
        return jsonify({"error": "Series not found"}), 404

    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    order = data.get("order")
    if not order:
        return jsonify({"error": "order is required"}), 400

    validated_order, err = validate_list(order, "order", max_length=500)
    if err or not validated_order:
        return jsonify({"error": err or "invalid order"}), 400

    for item in validated_order:
        if not isinstance(item, dict):
            return jsonify(
                {"error": "order items must be objects with post_id and order_index"}
            ), 400
        if "post_id" not in item or "order_index" not in item:
            return jsonify({"error": "each order item must have post_id and order_index"}), 400

        post_id = item["post_id"]
        order_index = item["order_index"]

        post_id, err = validate_integer(post_id, "post_id", min_value=1)
        if err:
            return jsonify({"error": err}), 400

        order_index, err = validate_integer(order_index, "order_index", min_value=0)
        if err:
            return jsonify({"error": err}), 400

        ps = db.session.execute(
            select(PostSeries).filter_by(series_id=series_id, post_id=post_id)
        ).scalar_one_or_none()
        if ps:
            ps.order_index = order_index

    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify({"message": "Series posts reordered"})
