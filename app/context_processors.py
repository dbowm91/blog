"""Context processors for injecting common template variables."""

__all__ = ["invalidate_settings_cache", "invalidate_footer_cache"]

import logging

from datetime import datetime

from flask import request, session
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app import cache as flask_cache
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
from app.tag_cache import _get_tag_counts

logger = logging.getLogger(__name__)


def invalidate_settings_cache():
    """Invalidate the SiteSettings cache."""
    flask_cache.delete("site_settings")


def invalidate_footer_cache():
    """Invalidate the footer cache."""
    flask_cache.delete_memoized(_get_footer_data)


def _get_settings_cache_key():
    return "site_settings"


@flask_cache.cached(timeout=300, key_prefix=_get_settings_cache_key)
def _get_cached_settings():
    """Get cached site settings."""
    from app.models import THEME_PRESETS

    try:
        from app.models import SiteSettings

        settings = db.session.execute(
            select(SiteSettings).order_by(SiteSettings.id).limit(1)
        ).scalar_one_or_none()

        if not settings:
            return {
                "theme_preset": "github-dark",
                "theme_vars": THEME_PRESETS["github-dark"],
                "syntax_theme": "prism",
                "custom_css_enabled": False,
                "custom_css": "",
                "logo_text": "",
                "theme_presets": THEME_PRESETS,
            }

        preset = THEME_PRESETS.get(
            settings.theme_preset, THEME_PRESETS["github-dark"]
        )
        return {
                "theme_preset": settings.theme_preset,
                "theme_vars": preset,
                "syntax_theme": settings.syntax_theme,
                "custom_css_enabled": settings.custom_css_enabled,
                "custom_css": settings.custom_css if settings.custom_css_enabled else "",
                "logo_text": settings.logo_text,
                "theme_presets": THEME_PRESETS,
            }
    except OperationalError:
        logger.exception("Database error loading theme settings, using fallback")
        from app.models import THEME_PRESETS

        return {
                "theme_preset": "github-dark",
                "theme_vars": THEME_PRESETS["github-dark"],
                "syntax_theme": "prism",
                "custom_css_enabled": False,
                "custom_css": "",
                "logo_text": "",
                "theme_presets": THEME_PRESETS,
            }



@flask_cache.memoize(timeout=45)
def _get_footer_data():
    """Get footer data with caching."""
    from app.models import Post, Tag

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
    recent_posts_sidebar = (
        db.session.execute(
            select(Post)
            .filter_by(published=True)
            .order_by(Post.created_at.desc())
            .limit(5)
        )
        .scalars()
        .all()
    )
    footer_tags = (
        db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()
    )

    tag_counts = _get_tag_counts()
    footer_tag_counts = {tag_id: tag_counts.get(tag_id, 0) for tag_id in [t.id for t in footer_tags]}

    return {
        "recent_posts_footer": list(recent_posts),
        "recent_posts_sidebar": list(recent_posts_sidebar),
        "footer_tags": list(footer_tags),
        "footer_tag_counts": footer_tag_counts,
    }


def register_context_processors(app):
    """Register all context processors with the Flask app."""

    @app.context_processor
    def inject_csrf():
        try:
            from flask import g

            nonce = getattr(g, "csp_nonce", "")
        except RuntimeError:
            nonce = ""
        tokens = session.get("csrf_tokens", [])
        csrf_token = tokens[-1] if tokens else generate_csrf_token()
        return {"csrf_token": csrf_token, "csp_nonce": nonce}

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
            "canonical_url": BASE_URL.rstrip("/") + request.path,
        }

    @app.context_processor
    def inject_theme():
        return _get_cached_settings()

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
                "recent_posts_sidebar": [],
                "footer_tags": [],
                "footer_tag_counts": {},
            }

        try:
            return _get_footer_data()
        except OperationalError:
            logger.exception("Database error loading footer data, using fallback")
            return {
                "recent_posts_footer": [],
                "recent_posts_sidebar": [],
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
