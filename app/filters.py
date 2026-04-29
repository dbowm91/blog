"""Template filters for the blog CMS."""

import os

import markdown
import nh3
from flask import g, has_request_context

from app.markdown_config import MARKDOWN_ALLOWED_ATTRIBUTES, MARKDOWN_ALLOWED_TAGS


def register_filters(app):
    @app.template_filter("markdown_safe")
    def markdown_safe_filter(text: str) -> str:
        html = markdown.markdown(text, extensions=["fenced_code", "tables"])
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
    def sanitize_css_filter(text):
        from app.utils import sanitize_css

        return sanitize_css(text) if text else ""

    @app.template_filter("post_image_url")
    def post_image_url_filter(post):
        if not post or not post.image:
            return None
        if has_request_context():
            if not hasattr(g, "_post_image_cache"):
                g._post_image_cache = {}
            post_id = id(post)
            if post_id in g._post_image_cache:
                return g._post_image_cache[post_id]
            path = os.path.join(app.config["UPLOAD_FOLDER"], post.image)
            result = post.image if os.path.isfile(path) else None
            g._post_image_cache[post_id] = result
            return result
        path = os.path.join(app.config["UPLOAD_FOLDER"], post.image)
        return post.image if os.path.isfile(path) else None
