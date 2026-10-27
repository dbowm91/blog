"""Context processors for injecting common template variables."""

__all__ = [
    "invalidate_settings_cache",
    "invalidate_footer_cache",
    "get_site_settings",
    "resolve_page_menu",
]

import logging

from datetime import datetime

from flask import request, session
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from typing import Any

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
from app.csrf import generate_csrf_token, CSRF_HEADER_NAME
from app.services.site_settings import invalidate_site_settings_cache, read_site_settings
from app.tag_cache import _get_tag_counts

logger = logging.getLogger(__name__)

_APPEARANCE_FALLBACK: dict[str, Any] = {
    "appearance_css": (
        ":root {\n"
        "  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;\n"
        "  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;\n"
        "  --backdrop-tint: transparent;\n"
        "  --backdrop-image: none;\n"
        "}"
    ),
    "appearance_font_sans": "inter",
    "appearance_font_mono": "jetbrains-mono",
    "appearance_backdrop": "",
    "appearance_backdrop_url": "",
    "appearance_backdrop_tint_dark": "transparent",
    "appearance_backdrop_tint_light": "transparent",
    "appearance_font_sans_stack": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    "appearance_font_mono_stack": "'JetBrains Mono', 'Fira Code', monospace",
    "appearance_preload_fonts": [],
}


def invalidate_settings_cache() -> None:
    """Invalidate the SiteSettings cache."""
    flask_cache.delete("site_settings")
    invalidate_site_settings_cache()
    try:
        from app.themes.service import get_theme_service

        get_theme_service().invalidate_settings_cache()
    except Exception:
        pass
    try:
        from app.appearance.service import get_appearance_service

        get_appearance_service().invalidate_settings_cache()
    except Exception:
        pass


def invalidate_footer_cache() -> None:
    """Invalidate the footer cache."""
    flask_cache.delete_memoized(_get_footer_data)


def get_site_settings() -> dict[str, Any]:
    """Read the site-level settings for public rendering.

    Uses a plain select rather than ``SiteSettings.get_instance()``, which
    performs ``db.session.flush()`` and would flush unrelated pending changes
    on a public request.
    """
    defaults: dict[str, Any] = {
        "comments_enabled": True,
        "footer_text": "",
        "footer_show_posts": True,
        "footer_show_tags": True,
    }

    try:
        settings = read_site_settings()
    except OperationalError:
        logger.exception("Database error loading site settings, using defaults")
        return defaults

    if settings is None:
        return defaults

    return {
        "comments_enabled": settings.comments_enabled,
        "footer_text": settings.footer_text,
        "footer_show_posts": settings.footer_show_posts,
        "footer_show_tags": settings.footer_show_tags,
    }


def resolve_page_menu() -> list[Any]:
    """The ordered list of pages shown in the site navigation."""
    try:
        from app.services.navigation import resolve_page_menu as resolver
    except ImportError:
        return []
    try:
        return resolver()
    except Exception:
        logger.exception("Failed to resolve the page menu")
        return []


def _get_settings_cache_key() -> str:
    return "site_settings"


@flask_cache.cached(timeout=300, key_prefix=_get_settings_cache_key)  # type: ignore[arg-type]
def _get_cached_settings() -> dict[str, Any]:
    """Emergency fallback when ThemeService is unavailable.

    This path is only reached when ``inject_theme`` catches an exception
    from the theme service. Normal rendering should never depend on this
    function. Uses ``EMERGENCY_DEFAULT`` from the theme model which
    provides the same palette as the EMERGENCY_DEFAULT theme.
    """
    from app.themes.model import EMERGENCY_DEFAULT
    from app.themes.translate import to_legacy_vars

    emergency_vars = to_legacy_vars(EMERGENCY_DEFAULT)

    try:
        settings = read_site_settings()

        if not settings:
            return {
                "theme_vars": emergency_vars,
                "custom_css_enabled": False,
                "custom_css": "",
                "logo_text": "",
            }

        return {
            "theme_vars": emergency_vars,
            "custom_css_enabled": settings.custom_css_enabled,
            "custom_css": settings.custom_css if settings.custom_css_enabled else "",
            "logo_text": settings.logo_text,
        }
    except OperationalError:
        logger.exception("Database error loading theme settings, using fallback")
        invalidate_settings_cache()
        return {
            "theme_vars": emergency_vars,
            "custom_css_enabled": False,
            "custom_css": "",
            "logo_text": "",
        }


@flask_cache.memoize(timeout=45)
def _get_footer_data() -> dict[str, Any]:
    """Get footer data with caching."""
    from app.models import Post, Tag

    recent_posts = (
        db.session.execute(
            select(Post).filter_by(published=True).order_by(Post.created_at.desc()).limit(3)
        )
        .scalars()
        .all()
    )
    footer_tags = db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()

    tag_counts = _get_tag_counts()
    footer_tag_counts = {
        tag_id: tag_counts.get(tag_id, 0) for tag_id in [t.id for t in footer_tags]
    }

    return {
        "recent_posts_footer": list(recent_posts),
        "footer_tags": list(footer_tags),
        "footer_tag_counts": footer_tag_counts,
    }


def register_context_processors(app: Any) -> None:
    """Register all context processors with the Flask app."""

    @app.context_processor
    def inject_csrf() -> dict[str, str]:
        try:
            from flask import g

            nonce = getattr(g, "csp_nonce", "")
        except RuntimeError:
            nonce = ""
        tokens = session.get("csrf_tokens", [])
        csrf_token = tokens[-1] if tokens else generate_csrf_token()
        return {
            "csrf_token": csrf_token,
            "csrf_header_name": CSRF_HEADER_NAME,
            "csp_nonce": nonce,
        }

    @app.context_processor
    def inject_config() -> dict[str, Any]:
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
    def inject_theme() -> dict[str, Any]:
        try:
            from app.themes.service import get_theme_service

            return get_theme_service().get_context()
        except Exception:
            logger.warning(
                "theme service unavailable, using emergency fallback "
                "(this should not happen in normal operation)"
            )
            return _get_cached_settings()

    @app.context_processor
    def inject_appearance() -> dict[str, Any]:
        try:
            from app.appearance.service import get_appearance_service

            return get_appearance_service().get_context()
        except Exception:
            logger.warning(
                "appearance service unavailable, using defaults "
                "(this should not happen in normal operation)"
            )
            return _APPEARANCE_FALLBACK

    @app.context_processor
    def inject_footer_data() -> dict[str, Any]:
        path = request.path if request else ""
        if path.startswith("/admin") or path.startswith("/api") or path.startswith("/rss"):
            return {
                "recent_posts_footer": [],
                "footer_tags": [],
                "footer_tag_counts": {},
            }

        try:
            return _get_footer_data()
        except OperationalError:
            logger.exception("Database error loading footer data, using fallback")
            invalidate_footer_cache()
            return {
                "recent_posts_footer": [],
                "footer_tags": [],
                "footer_tag_counts": {},
            }

    @app.context_processor
    def inject_show_footer_posts() -> dict[str, bool]:
        path = request.path if request else ""
        return {"show_footer_posts": not (path.startswith("/search") or path.startswith("/tag/"))}

    @app.context_processor
    def inject_site_settings() -> dict[str, Any]:
        return get_site_settings()

    @app.context_processor
    def inject_page_menu() -> dict[str, Any]:
        path = request.path if request else ""
        if path.startswith("/admin") or path.startswith("/api"):
            return {"page_menu": []}
        return {"page_menu": resolve_page_menu()}
