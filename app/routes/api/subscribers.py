"""Subscribers API endpoints."""

from datetime import timedelta

from flask import jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.extensions import db
from app.models import Subscriber
from app.utils import utc_now
from app.validators import validate_email
from app import limiter
from app.routes.api import api
from app.routes.api.auth import require_api_key, require_scope

DEFAULT_LIMIT = "20 per minute"
WRITE_LIMIT = "10 per minute"


def _subscriber_to_dict(subscriber: Subscriber) -> dict:
    """Serialize a Subscriber model to a dictionary."""
    return {
        "id": subscriber.id,
        "email": subscriber.email,
        "confirmed": subscriber.confirmed,
        "created_at": (subscriber.created_at.isoformat() if subscriber.created_at else None),
        "expires_at": (subscriber.expires_at.isoformat() if subscriber.expires_at else None),
        "unsubscribed_at": (
            subscriber.unsubscribed_at.isoformat() if subscriber.unsubscribed_at else None
        ),
    }


@api.route("/subscribers", methods=["GET"])
@require_api_key
@require_scope("subscribers:read")
@limiter.limit(DEFAULT_LIMIT)
def list_subscribers() -> any:
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
@require_scope("subscribers:write")
@limiter.limit(WRITE_LIMIT)
def create_subscriber() -> any:
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

    existing = db.session.execute(select(Subscriber).filter_by(email=email)).scalar_one_or_none()

    if existing:
        return jsonify(_subscriber_to_dict(existing))

    from app.config import CONFIRMATION_EXPIRY_HOURS

    subscriber = Subscriber(
        email=email,
        expires_at=utc_now() + timedelta(hours=CONFIRMATION_EXPIRY_HOURS),
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
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify(_subscriber_to_dict(subscriber)), 201


@api.route("/subscribers/<int:subscriber_id>", methods=["DELETE"])
@require_api_key
@require_scope("subscribers:write")
@limiter.limit(WRITE_LIMIT)
def delete_subscriber(subscriber_id: int) -> any:
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
