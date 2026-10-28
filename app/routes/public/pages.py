"""Public routes for the static page index."""

from __future__ import annotations

import html as html_stdlib
import logging
import re
from typing import Any

from flask import render_template
from flask.typing import ResponseReturnValue
from sqlalchemy import select

from app import limiter
from app.extensions import db
from app.markdown_renderer import render_markdown
from app.models import Page

logger = logging.getLogger(__name__)

SUMMARY_CHAR_LIMIT = 200

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")
_TAG_RE = re.compile(r"<[^>]+>")

_REGISTERED_BLUEPRINTS: set[str] = set()


def _first_paragraph(body: str) -> str:
    """Return the first non-empty paragraph of a markdown body."""
    for block in _PARAGRAPH_SPLIT_RE.split(body.strip()):
        paragraph = block.strip()
        if paragraph:
            return paragraph
    return ""


def _plain_text(markdown_source: str) -> str:
    """Render markdown and return its text content."""
    rendered = render_markdown(markdown_source)
    text = _TAG_RE.sub(" ", rendered)
    text = html_stdlib.unescape(text)
    return " ".join(text.split())


def page_summary(body: str, limit: int = SUMMARY_CHAR_LIMIT) -> str:
    """Return the first paragraph of a page body as a truncated summary.

    The paragraph is rendered through the shared markdown pipeline and then
    reduced to its text content, so the summary reads like the post listing
    summaries.
    """
    paragraph = _first_paragraph(body)
    if not paragraph:
        return ""
    text = _plain_text(paragraph)
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip() + "…"


def render_page(page: Any, is_homepage: bool = False) -> ResponseReturnValue:
    """Render an ordinary page.

    The renderer is shared by the page route and by the homepage dispatcher,
    so a page that is the homepage is rendered exactly like a page that is
    not. The flag only changes the breadcrumb.
    """
    return render_template("page.html", page=page, is_homepage=is_homepage)


def register_page_routes(public: Any) -> None:
    """Register the public page index route on the Blueprint.

    Registration is idempotent: calling this twice for the same blueprint is
    a no-op, so the route can be wired up by the blueprint package and by a
    caller that imports this module directly.
    """
    if public.name in _REGISTERED_BLUEPRINTS:
        return
    _REGISTERED_BLUEPRINTS.add(public.name)

    @public.route("/pages")
    @limiter.limit("60 per minute")
    def pages_index() -> ResponseReturnValue:
        """Index of every published static page."""
        pages = (
            db.session.execute(select(Page).filter(Page.published.is_(True)).order_by(Page.title))
            .scalars()
            .all()
        )
        entries = [(page, page_summary(page.body)) for page in pages]
        return render_template("pages.html", pages=entries)
