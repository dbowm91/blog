"""Context processors for injecting common template variables."""

__all__ = ["invalidate_settings_cache"]

import threading
import time as _time

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


_SITE_SETTINGS_CACHE: dict[str, object] = {"data": None, "timestamp": 0}
_SETTINGS_CACHE_LOCK = threading.Lock()
_SETTINGS_TTL = 300

_FOOTER_CACHE: dict[str, object] = {"data": None, "timestamp": 0}
_FOOTER_CACHE_LOCK = threading.Lock()
_FOOTER_TTL = 45


def invalidate_settings_cache() -> None:
    """Invalidate the SiteSettings cache."""
    with _SETTINGS_CACHE_LOCK:
        _SITE_SETTINGS_CACHE["data"] = None
        _SITE_SETTINGS_CACHE["timestamp"] = 0


def _get_cached_settings() -> dict | None:
    with _SETTINGS_CACHE_LOCK:
        now = _time.monotonic()
        if (
            _SITE_SETTINGS_CACHE["data"] is not None
            and (now - _SITE_SETTINGS_CACHE["timestamp"]) < _SETTINGS_TTL
        ):
            return _SITE_SETTINGS_CACHE["data"]
    return None


def _set_cached_settings(data: dict) -> dict:
    with _SETTINGS_CACHE_LOCK:
        now = _time.monotonic()
        _SITE_SETTINGS_CACHE["data"] = data
        _SITE_SETTINGS_CACHE["timestamp"] = now
        return data


def _get_footer_data() -> dict:
    with _FOOTER_CACHE_LOCK:
        now = _time.monotonic()
        if (
            _FOOTER_CACHE["data"] is not None
            and (now - _FOOTER_CACHE["timestamp"]) < _FOOTER_TTL
        ):
            return {
                "recent_posts_footer": _FOOTER_CACHE["data"]["recent_posts"],
                "footer_tags": _FOOTER_CACHE["data"]["tags"],
                "footer_tag_counts": _get_tag_counts(),
            }

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
    footer_tags = db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()

    with _FOOTER_CACHE_LOCK:
        now = _time.monotonic()
        if (
            _FOOTER_CACHE["data"] is None
            or (now - _FOOTER_CACHE["timestamp"]) >= _FOOTER_TTL
        ):
            _FOOTER_CACHE["data"] = {
                "recent_posts": list(recent_posts),
                "tags": list(footer_tags),
            }
            _FOOTER_CACHE["timestamp"] = now

    return {
        "recent_posts_footer": recent_posts,
        "footer_tags": footer_tags,
        "footer_tag_counts": _get_tag_counts(),
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
    def inject_theme():
        from app.models import THEME_PRESETS

        cached = _get_cached_settings()
        if cached is not None:
            return cached

        try:
            from app.models import SiteSettings

            settings = db.session.execute(
                select(SiteSettings).order_by(SiteSettings.id).limit(1)
            ).scalar_one_or_none()

            if not settings:
                result = {
                    "theme_preset": "github-dark",
                    "theme_vars": THEME_PRESETS["github-dark"],
                    "custom_css_enabled": False,
                    "custom_css": "",
                    "logo_text": "",
                    "theme_presets": THEME_PRESETS,
                }
                return _set_cached_settings(result)

            preset = THEME_PRESETS.get(
                settings.theme_preset, THEME_PRESETS["github-dark"]
            )
            result = {
                "theme_preset": settings.theme_preset,
                "theme_vars": preset,
                "custom_css_enabled": settings.custom_css_enabled,
                "custom_css": settings.custom_css
                if settings.custom_css_enabled
                else "",
                "logo_text": settings.logo_text,
                "theme_presets": THEME_PRESETS,
            }
            return _set_cached_settings(result)
        except OperationalError:
            return {
                "theme_preset": "github-dark",
                "theme_vars": THEME_PRESETS["github-dark"],
                "custom_css_enabled": False,
                "custom_css": "",
                "logo_text": "",
                "theme_presets": THEME_PRESETS,
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

        try:
            return _get_footer_data()
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
