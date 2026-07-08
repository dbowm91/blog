"""Pages API endpoints."""

from typing import Any

from flask import jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.extensions import db
from app.models import Page
from app.utils import generate_slug
from app.validators import validate_string, validate_boolean
from app import limiter
from app.routes.api import api
from app.routes.api.auth import require_api_key, require_scope
from app.routes.admin.helpers.slug import _generate_unique_slug

DEFAULT_LIMIT = "20 per minute"
WRITE_LIMIT = "10 per minute"


def _page_to_dict(page: Page) -> dict:
    """Serialize a Page model to a dictionary."""
    return {
        "id": page.id,
        "title": page.title,
        "slug": page.slug,
        "body": page.body,
        "created_at": page.created_at.isoformat() if page.created_at else None,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None,
        "published": page.published,
    }


@api.route("/pages", methods=["GET"])
@require_api_key
@require_scope("pages:read")
@limiter.limit(DEFAULT_LIMIT)
def list_pages() -> Any:
    """List all pages.

    Query params:
        published: Filter by published status (true/false)

    Returns:
        JSON with pages array
    """
    published_filter = request.args.get("published")

    query = select(Page).order_by(Page.created_at.desc())

    if published_filter is not None:
        published_val = published_filter.lower() in ("true", "1", "yes")
        query = query.filter(Page.published == published_val)

    pages = db.session.execute(query).scalars().all()

    return jsonify(
        {
            "pages": [_page_to_dict(p) for p in pages],
            "total": len(pages),
        }
    )


@api.route("/pages/<int:page_id>", methods=["GET"])
@require_api_key
@require_scope("pages:read")
@limiter.limit(DEFAULT_LIMIT)
def get_page(page_id: int) -> Any:
    """Get a single page by ID.

    Returns:
        JSON with page data or 404 error
    """
    page = db.session.get(Page, page_id)
    if not page:
        return jsonify({"error": "Page not found"}), 404

    return jsonify(_page_to_dict(page))


@api.route("/pages", methods=["POST"])
@require_api_key
@require_scope("pages:write")
@limiter.limit(WRITE_LIMIT)
def create_page() -> Any:
    """Create a new page.

    JSON body:
        title: Page title (required)
        slug: URL slug (optional, auto-generated if not provided)
        body: Page content (required)
        published: Published status (default false)

    Returns:
        JSON with created page data
    """
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    title = data.get("title")
    if not title:
        return jsonify({"error": "title is required"}), 400
    title, err = validate_string(title, 200, "title")
    if err:
        return jsonify({"error": err}), 400

    body = data.get("body")
    if not body:
        return jsonify({"error": "body is required"}), 400
    body, err = validate_string(body, 50000, "body")
    if err:
        return jsonify({"error": err}), 400

    slug = data.get("slug")
    if slug:
        slug, err = validate_string(slug, 200, "slug")
        if err:
            return jsonify({"error": err}), 400
        slug = generate_slug(slug)

    if not slug:
        slug = generate_slug(title)

    slug = _generate_unique_slug(Page, title, slug=slug)

    published = data.get("published", False)
    published, err = validate_boolean(published, "published")
    if err:
        return jsonify({"error": err}), 400

    page = Page(
        title=title,
        slug=slug,
        body=body,
        published=published,
    )
    db.session.add(page)

    max_attempts = 100
    for attempt in range(max_attempts):
        try:
            db.session.flush()
            db.session.commit()
            break
        except IntegrityError:
            db.session.rollback()
            if attempt == max_attempts - 1:
                return jsonify({"error": "Duplicate slug or database constraint violation"}), 409
            page.slug = _generate_unique_slug(Page, title, exclude_id=page.id if page.id else None)
            db.session.add(page)
        except OperationalError:
            db.session.rollback()
            return jsonify({"error": "Database operational error"}), 500

    return jsonify(_page_to_dict(page)), 201


@api.route("/pages/<int:page_id>", methods=["PUT"])
@require_api_key
@require_scope("pages:write")
@limiter.limit(WRITE_LIMIT)
def update_page(page_id: int) -> Any:
    """Update an existing page.

    JSON body (all optional):
        title: Page title
        slug: URL slug
        body: Page content
        published: Published status

    Returns:
        JSON with updated page data or 404 error
    """
    page = db.session.get(Page, page_id)
    if not page:
        return jsonify({"error": "Page not found"}), 404

    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    if "title" in data:
        title, err = validate_string(data["title"], 200, "title")
        if err:
            return jsonify({"error": err}), 400
        page.title = title

    if "slug" in data:
        slug, err = validate_string(data["slug"], 200, "slug")
        if err:
            return jsonify({"error": err}), 400
        slug = generate_slug(slug)
        if slug != page.slug:
            page.slug = _generate_unique_slug(Page, page.title, slug=slug, exclude_id=page_id)

    if "body" in data:
        body, err = validate_string(data["body"], 50000, "body")
        if err:
            return jsonify({"error": err}), 400
        page.body = body

    if "published" in data:
        published, err = validate_boolean(data["published"], "published")
        if err:
            return jsonify({"error": err}), 400
        page.published = published

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Duplicate slug or database constraint violation"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database operational error"}), 500

    return jsonify(_page_to_dict(page))


@api.route("/pages/<int:page_id>", methods=["DELETE"])
@require_api_key
@require_scope("pages:write")
@limiter.limit(WRITE_LIMIT)
def delete_page(page_id: int) -> Any:
    """Delete a page.

    Returns:
        JSON with success message or 404 error
    """
    page = db.session.get(Page, page_id)
    if not page:
        return jsonify({"error": "Page not found"}), 404

    title = page.title
    db.session.delete(page)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Database constraint violation"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database operational error"}), 500

    return jsonify({"message": f"Page '{title}' deleted successfully"})
