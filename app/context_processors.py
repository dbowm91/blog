"""Context processors for injecting common template variables."""

from datetime import datetime

from flask import request
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.extensions import db
from app.config import (
    APP_TITLE,
    APP_DESCRIPTION,
    AUTHOR_NAME,
    AUTHOR_ROLE,
    AUTHOR_AVATAR,
    BASE_URL,
)
from app.csrf import generate_csrf_token
from app.cache import _get_tag_counts


def register_context_processors(app):
    """Register all context processors with the Flask app."""

    @app.context_processor
    def inject_csrf():
        try:
            from flask import g

            nonce = getattr(g, "csp_nonce", "")
        except RuntimeError:
            nonce = ""
        return {"csrf_token": generate_csrf_token(), "csp_nonce": nonce}

    @app.context_processor
    def inject_config():
        return {
            "site_title": APP_TITLE,
            "site_description": APP_DESCRIPTION,
            "author_name": AUTHOR_NAME,
            "author_role": AUTHOR_ROLE,
            "author_avatar": AUTHOR_AVATAR,
            "base_url": BASE_URL,
            "current_year": datetime.now().year,
        }

    @app.context_processor
    def inject_footer_data():
        path = request.path if request else ""
        if (
            path.startswith("/admin")
            or path.startswith("/api")
            or path.startswith("/rss")
        ):
            return {
                "recent_posts_footer": [],
                "footer_tags": [],
                "footer_tag_counts": {},
            }

        from app.models import Post, Tag

        try:
            recent_posts = (
                db.session.execute(
                    select(Post)
                    .filter_by(published=True)
                    .order_by(Post.created_at.desc())
                    .limit(3)
                )
                .scalars()
                .all()
            )
            footer_tags = (
                db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()
            )
            tag_counts = _get_tag_counts()
            return {
                "recent_posts_footer": recent_posts,
                "footer_tags": footer_tags,
                "footer_tag_counts": tag_counts,
            }
        except OperationalError:
            return {
                "recent_posts_footer": [],
                "footer_tags": [],
                "footer_tag_counts": {},
            }

    @app.context_processor
    def inject_show_footer_posts():
        path = request.path if request else ""
        return {
            "show_footer_posts": not (
                path.startswith("/search") or path.startswith("/tag/")
            )
        }
