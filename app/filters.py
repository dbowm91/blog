"""Template filters for the blog CMS."""

import markdown
import nh3
from typing import Any
from flask import Flask, g, has_request_context

from app.markdown_config import MARKDOWN_ALLOWED_ATTRIBUTES, MARKDOWN_ALLOWED_TAGS


def register_filters(app: Flask) -> None:
    @app.template_filter("markdown_safe")
    def markdown_safe_filter(text: str) -> str:
        html = markdown.markdown(text, extensions=["fenced_code", "tables", "footnotes"])
        return nh3.clean(
            html, tags=MARKDOWN_ALLOWED_TAGS, attributes=MARKDOWN_ALLOWED_ATTRIBUTES
        )

    @app.template_filter("reading_time")
    def reading_time_filter(text: str) -> str:
        if not text:
            return "1 min read"
        words = len(text.split())
        minutes = max(1, round(words / 200))
        return f"{minutes} min read"

    @app.template_filter("sanitize_css")
    def sanitize_css_filter(text: str | None) -> str:
        from app.utils import sanitize_css

        return sanitize_css(text) if text else ""

    @app.template_filter("post_image_url")
    def post_image_url_filter(post: Any) -> str | None:
        if not post or not post.image:
            return None
        if has_request_context():
            if not hasattr(g, "_post_image_cache"):
                g._post_image_cache = {}
            post_id = post.id
            if post_id in g._post_image_cache:
                return g._post_image_cache[post_id]
            from app.storage import get_storage
            storage = get_storage()
            result: str | None = post.image if storage.exists(post.image) else None
            g._post_image_cache[post_id] = result
            return result
        from app.storage import get_storage
        storage = get_storage()
        return post.image if storage.exists(post.image) else None

    @app.template_filter("post_image_srcset")
    def post_image_srcset_filter(post: Any) -> str | None:
        if not post or not post.image:
            return None
        if has_request_context():
            cache_key = f"_post_srcset_cache_{post.id}"
            if not hasattr(g, "_post_image_cache"):
                g._post_image_cache = {}
            if cache_key in g._post_image_cache:
                return g._post_image_cache[cache_key]
            from app.storage import get_storage
            from app.config import BASE_URL, CDN_URL
            storage = get_storage()
            base_url = CDN_URL if CDN_URL else BASE_URL
            srcset_parts = []
            for width in (400, 800, 1200):
                variant_name = f"{width}_{post.image}"
                if storage.exists(variant_name):
                    srcset_parts.append(f"{base_url.rstrip('/')}/static/uploads/{variant_name} {width}w")
            g._post_image_cache[cache_key] = ", ".join(srcset_parts) if srcset_parts else None
            return g._post_image_cache[cache_key]
        return None

    @app.template_filter("post_image_avif_url_stub")
    def post_image_avif_url_filter(post: Any) -> str | None:
        """Return AVIF variant URL if available, else None.

        DEPRECATED: This filter is a stub and will always return None until
        AVIF encoding is properly implemented. It has been renamed to avoid
        confusion with a functional implementation.
        """
        if not post or not post.image:
            return None
        return None
