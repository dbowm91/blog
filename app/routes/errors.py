"""Error handlers blueprint."""

import logging

from flask import Blueprint, render_template, redirect, url_for, flash, request as req
from sqlalchemy import select

from app.extensions import db
from app.models import Post
from app.config import MAX_UPLOAD_SIZE

logger = logging.getLogger(__name__)

errors = Blueprint("errors", __name__)


def _get_recent_posts(limit=5):
    """Shared helper to fetch recent published posts for error pages."""
    try:
        return (
            db.session.execute(
                select(Post)
                .filter_by(published=True)
                .order_by(Post.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
    except Exception:
        return []


@errors.app_errorhandler(404)
def not_found(e):
    recent_posts = _get_recent_posts(5)
    return render_template(
        "404.html",
        recent_posts=recent_posts,
        error_code="404",
        error_title="Page not found",
        error_message="The page you're looking for doesn't exist or has been moved.",
    ), 404


@errors.app_errorhandler(500)
def internal_error(e):
    logger.exception("Unhandled exception on %s", req.path)
    recent_posts = _get_recent_posts(5)
    return render_template(
        "500.html",
        recent_posts=recent_posts,
        error_code="500",
        error_title="Internal Server Error",
        error_message="Something went wrong. Please try again later.",
    ), 500


@errors.app_errorhandler(413)
def handle_large_request(e):
    flash(
        f"File too large. Maximum upload size is {MAX_UPLOAD_SIZE // (1024 * 1024)}MB.",
        "error",
    )
    return redirect(req.referrer or url_for("admin.dashboard"))
