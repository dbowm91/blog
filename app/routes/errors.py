"""Error handlers blueprint."""

import logging

from flask import Blueprint, render_template, redirect, url_for, flash, request as req
from werkzeug.wrappers import Response

from sqlalchemy import select
from sqlalchemy.exc import OperationalError, IntegrityError

from app.extensions import db
from app.models import Post
from app.config import MAX_UPLOAD_SIZE

logger = logging.getLogger(__name__)

errors = Blueprint("errors", __name__)


def _get_recent_posts(limit: int = 5) -> list[Post]:
    """Shared helper to fetch recent published posts for error pages."""
    try:
        result = (
            db.session.execute(
                select(Post).filter_by(published=True).order_by(Post.created_at.desc()).limit(limit)
            )
            .scalars()
            .all()
        )
        return list(result)
    except (OperationalError, IntegrityError):
        # Intentional catch-all: graceful degradation if DB is unavailable
        # Error pages should still render even if recent posts can't be fetched
        return []


@errors.app_errorhandler(404)
def not_found(e: Exception) -> tuple[str, int]:
    recent_posts = _get_recent_posts(5)
    return render_template(
        "404.html",
        recent_posts=recent_posts,
        error_code="404",
        error_title="Page not found",
        error_message="The page you're looking for doesn't exist or has been moved.",
    ), 404


@errors.app_errorhandler(500)
def internal_error(e: Exception) -> tuple[str, int]:
    logger.exception("Unhandled exception on %s", req.path)
    recent_posts = _get_recent_posts(5)
    return render_template(
        "500.html",
        recent_posts=recent_posts,
        error_code="500",
        error_title="Something went wrong",
        error_message="We're sorry for the inconvenience. Please try again or return to the home page.",
    ), 500


@errors.app_errorhandler(413)
def handle_large_request(e: Exception) -> Response:
    flash(
        f"File too large. Maximum upload size is {MAX_UPLOAD_SIZE // (1024 * 1024)}MB.",
        "error",
    )
    if req.referrer and "/admin" in req.referrer:
        return redirect(req.referrer)
    return redirect(url_for("public.index"))
