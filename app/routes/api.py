"""REST API for Post/Subscriber Management.

Requires API key authentication via X-API-Key header.
Rate limiting should be handled by the reverse proxy (same as admin routes).
"""

import os
import hmac
from functools import wraps

from flask import Blueprint, jsonify, request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import Post, Subscriber, PageView, ShareEvent
from app.config import DASHBOARD_PER_PAGE, SUBSCRIBERS_PER_PAGE
from app.utils import utc_now, is_valid_email
from app.validators import validate_string, validate_email, validate_boolean
from app import limiter

api = Blueprint("api", __name__, url_prefix="/api")

API_KEY = os.environ.get("API_KEY", "")

DEFAULT_LIMIT = "20 per minute"
WRITE_LIMIT = "10 per minute"


def require_api_key(f):
    """Decorator to require API key authentication."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if not API_KEY:
            return jsonify({"error": "API not configured"}), 503

        provided = request.headers.get("X-API-Key", "")
        if not provided or not hmac.compare_digest(provided, API_KEY):
            return jsonify({"error": "Invalid or missing API key"}), 401

        return f(*args, **kwargs)

    return decorated


def _post_to_dict(post: Post) -> dict:
    """Serialize a Post model to a dictionary."""
    return {
        "id": post.id,
        "title": post.title,
        "slug": post.slug,
        "body": post.body,
        "summary": post.summary,
        "image": post.image,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
        "published": post.published,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "scheduled_publish_at": (
            post.scheduled_publish_at.isoformat()
            if post.scheduled_publish_at
            else None
        ),
        "newsletter_sent_at": (
            post.newsletter_sent_at.isoformat()
            if post.newsletter_sent_at
            else None
        ),
        "newsletter_attempts": post.newsletter_attempts,
        "tags": [tag.name for tag in post.tags],
    }


def _subscriber_to_dict(subscriber: Subscriber) -> dict:
    """Serialize a Subscriber model to a dictionary."""
    return {
        "id": subscriber.id,
        "email": subscriber.email,
        "confirmed": subscriber.confirmed,
        "created_at": (
            subscriber.created_at.isoformat() if subscriber.created_at else None
        ),
        "expires_at": (
            subscriber.expires_at.isoformat() if subscriber.expires_at else None
        ),
        "unsubscribed_at": (
            subscriber.unsubscribed_at.isoformat()
            if subscriber.unsubscribed_at
            else None
        ),
    }


@api.route("/posts", methods=["GET"])
@require_api_key
@limiter.limit(DEFAULT_LIMIT)
def list_posts() -> Response:
    """List posts with pagination.

    Query params:
        page: Page number (default 1)
        per_page: Items per page (default 20, max 100)
        published: Filter by published status (true/false)

    Returns:
        JSON with posts array and pagination info
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    published_filter = request.args.get("published")

    query = select(Post).options(joinedload(Post.tags)).order_by(Post.created_at.desc())

    if published_filter is not None:
        published_val = published_filter.lower() in ("true", "1", "yes")
        query = query.filter(Post.published == published_val)

    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "posts": [_post_to_dict(p) for p in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "page": page,
            "per_page": per_page,
        }
    )


@api.route("/posts/<int:post_id>", methods=["GET"])
@require_api_key
@limiter.limit(DEFAULT_LIMIT)
def get_post(post_id: int) -> Response:
    """Get a single post by ID.

    Returns:
        JSON with post data or 404 error
    """
    post = db.session.execute(
        select(Post).options(joinedload(Post.tags)).filter(Post.id == post_id)
    ).unique().scalar_one_or_none()
    if not post:
        return jsonify({"error": "Post not found"}), 404

    return jsonify(_post_to_dict(post))


@api.route("/posts", methods=["POST"])
@require_api_key
@limiter.limit(WRITE_LIMIT)
def create_post() -> Response:
    """Create a new post.

    JSON body:
        title: Post title (required)
        slug: URL slug (optional, auto-generated if not provided)
        body: Post content (required)
        summary: Post summary (optional)
        image: Image filename (optional)
        published: Published status (default false)
        tags: List of tag names (optional)

    Returns:
        JSON with created post data
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
        slug, err = validate_string(slug, 100, "slug")
        if err:
            return jsonify({"error": err}), 400

    if not slug:
        slug = Post.generate_slug(title)

    from app.routes.admin.helpers.slug import _generate_unique_slug

    slug = _generate_unique_slug(Post, title, slug)

    summary = data.get("summary", "")
    if summary:
        summary, err = validate_string(summary, 500, "summary")
        if err:
            return jsonify({"error": err}), 400

    image = data.get("image")
    if image:
        image, err = validate_string(image, 200, "image")
        if err:
            return jsonify({"error": err}), 400

    published = data.get("published", False)
    published, err = validate_boolean(published, "published")
    if err:
        return jsonify({"error": err}), 400

    post = Post(
        title=title,
        slug=slug,
        body=body,
        summary=summary,
        image=image,
        published=published,
    )

    tags = data.get("tags", [])
    if tags:
        from app.routes.admin.helpers.tags import _get_or_create_tags

        post.tags = _get_or_create_tags(tags)

    db.session.add(post)
    db.session.flush()

    from app.search import sync_fts

    if not sync_fts(post.id, post.title, post.body, post.summary, post.published):
        db.session.rollback()
        return jsonify({"error": "Search index unavailable"}), 503

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Duplicate slug or database constraint violation"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database operational error"}), 500

    return jsonify(_post_to_dict(post)), 201


@api.route("/posts/<int:post_id>", methods=["PUT"])
@require_api_key
@limiter.limit(WRITE_LIMIT)
def update_post(post_id: int) -> Response:
    """Update an existing post.

    JSON body (all optional):
        title: Post title
        slug: URL slug
        body: Post content
        summary: Post summary
        image: Image filename
        published: Published status
        tags: List of tag names

    Returns:
        JSON with updated post data or 404 error
    """
    post = db.session.execute(
        select(Post).options(joinedload(Post.tags)).filter(Post.id == post_id)
    ).unique().scalar_one_or_none()
    if not post:
        return jsonify({"error": "Post not found"}), 404

    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    if "title" in data:
        title, err = validate_string(data["title"], 200, "title")
        if err:
            return jsonify({"error": err}), 400
        post.title = title
    if "slug" in data:
        new_slug, err = validate_string(data["slug"], 100, "slug")
        if err:
            return jsonify({"error": err}), 400
        if new_slug != post.slug:
            from app.routes.admin.helpers.slug import _generate_unique_slug

            post.slug = _generate_unique_slug(Post, post.title, new_slug, exclude_id=post_id)
    if "body" in data:
        body, err = validate_string(data["body"], 50000, "body")
        if err:
            return jsonify({"error": err}), 400
        post.body = body
    if "summary" in data:
        summary, err = validate_string(data["summary"], 500, "summary")
        if err:
            return jsonify({"error": err}), 400
        post.summary = summary
    if "image" in data:
        image, err = validate_string(data["image"], 200, "image")
        if err:
            return jsonify({"error": err}), 400
        post.image = image
    if "published" in data:
        published, err = validate_boolean(data["published"], "published")
        if err:
            return jsonify({"error": err}), 400
        post.published = published
        if published and not post.published_at:
            post.published_at = utc_now()

    if "tags" in data:
        from app.routes.admin.helpers.tags import _get_or_create_tags

        post.tags = _get_or_create_tags(data["tags"])

    from app.search import sync_fts

    if not sync_fts(post.id, post.title, post.body, post.summary, post.published):
        db.session.rollback()
        return jsonify({"error": "Search index unavailable"}), 503

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Duplicate slug or database constraint violation"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database operational error"}), 500

    return jsonify(_post_to_dict(post))


@api.route("/posts/<int:post_id>", methods=["DELETE"])
@require_api_key
@limiter.limit(WRITE_LIMIT)
def delete_post(post_id: int) -> Response:
    """Delete a post.

    Returns:
        JSON with success message or 404 error
    """
    post = db.session.execute(
        select(Post).options(joinedload(Post.tags)).filter(Post.id == post_id)
    ).unique().scalar_one_or_none()
    if not post:
        return jsonify({"error": "Post not found"}), 404

    from app.utils import safe_delete_file

    old_image = post.image
    post_image = post.image
    post_tags = list(post.tags)

    db.session.delete(post)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Database constraint violation"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database operational error"}), 500

    if old_image:
        safe_delete_file(old_image)

    from app.search import remove_fts

    remove_fts(post_id)

    return jsonify({"message": "Post deleted successfully"})


@api.route("/subscribers", methods=["GET"])
@require_api_key
@limiter.limit(DEFAULT_LIMIT)
def list_subscribers() -> Response:
    """List subscribers with pagination.

    Query params:
        page: Page number (default 1)
        per_page: Items per page (default 50, max 100)
        confirmed: Filter by confirmed status (true/false)

    Returns:
        JSON with subscribers array and pagination info
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)
    confirmed_filter = request.args.get("confirmed")

    query = select(Subscriber).order_by(Subscriber.created_at.desc())

    if confirmed_filter is not None:
        confirmed_val = confirmed_filter.lower() in ("true", "1", "yes")
        query = query.filter(Subscriber.confirmed == confirmed_val)

    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "subscribers": [_subscriber_to_dict(s) for s in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "page": page,
            "per_page": per_page,
        }
    )


@api.route("/subscribers", methods=["POST"])
@require_api_key
@limiter.limit(WRITE_LIMIT)
def create_subscriber() -> Response:
    """Create a new subscriber.

    JSON body:
        email: Subscriber email (required)

    Returns:
        JSON with created subscriber data
    """
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    email = data.get("email")
    if not email:
        return jsonify({"error": "email is required"}), 400

    email, err = validate_email(email)
    if err:
        return jsonify({"error": err}), 400

    existing = db.session.execute(
        select(Subscriber).filter_by(email=email)
    ).scalar_one_or_none()

    if existing:
        return jsonify(_subscriber_to_dict(existing))

    from app.config import CONFIRMATION_EXPIRY_HOURS

    subscriber = Subscriber(
        email=email,
        expires_at=utc_now()
        + __import__("datetime").timedelta(hours=CONFIRMATION_EXPIRY_HOURS),
    )
    db.session.add(subscriber)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = db.session.execute(
            select(Subscriber).filter_by(email=email)
        ).scalar_one_or_none()
        if existing:
            return jsonify(_subscriber_to_dict(existing))
        return jsonify({"error": "Failed to create subscriber"}), 500
    except OperationalError as e:
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify(_subscriber_to_dict(subscriber)), 201


@api.route("/subscribers/<int:subscriber_id>", methods=["DELETE"])
@require_api_key
@limiter.limit(WRITE_LIMIT)
def delete_subscriber(subscriber_id: int) -> Response:
    """Delete a subscriber.

    Returns:
        JSON with success message or 404 error
    """
    subscriber = db.session.get(Subscriber, subscriber_id)
    if not subscriber:
        return jsonify({"error": "Subscriber not found"}), 404

    db.session.delete(subscriber)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        return jsonify({"error": "Database error occurred"}), 500

    return jsonify({"message": "Subscriber deleted successfully"})


@api.route("/stats", methods=["GET"])
@require_api_key
@limiter.limit(DEFAULT_LIMIT)
def get_stats() -> Response:
    """Get dashboard statistics.

    Returns:
        JSON with total views, posts, shares, subscribers, and trends
    """
    from datetime import timedelta
    from sqlalchemy import text

    now = utc_now()
    thirty_days_ago = now - timedelta(days=30)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Combine all COUNT queries into a single query using subqueries
    counts = db.session.execute(
        text("""
            SELECT
                (SELECT COUNT(*) FROM page_views) as total_views,
                (SELECT COUNT(*) FROM posts WHERE published = 1) as total_posts,
                (SELECT COUNT(*) FROM share_events) as total_shares,
                (SELECT COUNT(*) FROM subscribers WHERE confirmed = 1) as total_subscribers,
                (SELECT COUNT(*) FROM page_views WHERE created_at >= :thirty_days_ago) as views_this_month,
                (SELECT COUNT(*) FROM subscribers WHERE created_at >= :month_start) as new_subscribers_this_month
        """),
        {"thirty_days_ago": thirty_days_ago, "month_start": month_start}
    ).fetchone()

    return jsonify(
        {
            "total_views": counts[0] or 0,
            "total_posts": counts[1] or 0,
            "total_shares": counts[2] or 0,
            "total_subscribers": counts[3] or 0,
            "views_this_month": counts[4] or 0,
            "new_subscribers_this_month": counts[5] or 0,
        }
    )
