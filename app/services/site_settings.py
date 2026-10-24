"""Validation for the site-level settings form.

The site settings form owns six values: the comments switch, the footer text,
the two footer column switches, the pages-in-menu switch and the ordered page
menu. Parsing and validation live here so the route never interprets raw form
values on its own.
"""

from __future__ import annotations

import json
import logging

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from app.models import SiteSettings

logger = logging.getLogger(__name__)

MAX_FOOTER_TEXT = 300

_SETTINGS_CACHE_ATTR = "_devlog_site_settings"
_UNSET = object()


@dataclass(frozen=True)
class SiteSettingsPayload:
    comments_enabled: bool
    footer_text: str
    footer_show_posts: bool
    footer_show_tags: bool
    show_pages_in_menu: bool
    menu_pages: str


def _checkbox(form: Mapping[str, str], name: str) -> bool:
    return form.get(name) == "on"


def _menu_values(form: Mapping[str, str]) -> list[str]:
    getlist = getattr(form, "getlist", None)
    if callable(getlist):
        return [str(value) for value in getlist("menu_pages")]
    value = form.get("menu_pages")
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [str(value)]


def parse_menu_pages(values: object) -> list[int]:
    """Parse the ordered menu payload into a list of page ids.

    The stored value is a JSON array of page ids in menu order. The form
    submits the ids as a multi-select, so a list of raw values is also
    accepted. Anything unparseable, or anything that is not a positive
    integer, is discarded rather than rejected, so a corrupted field cannot
    break the settings page.
    """
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple)):
        return []

    if len(values) == 1 and isinstance(values[0], str) and values[0].lstrip().startswith("["):
        try:
            values = json.loads(values[0])
        except ValueError:
            logger.warning("Discarding unparseable menu_pages payload")
            return []

    if not isinstance(values, (list, tuple)):
        return []

    page_ids: list[int] = []
    for item in values:
        if isinstance(item, bool):
            continue
        try:
            page_id = int(item)
        except (TypeError, ValueError):
            continue
        if page_id <= 0 or page_id in page_ids:
            continue
        page_ids.append(page_id)
    return page_ids


def validate_site_settings(form: Mapping[str, str]) -> SiteSettingsPayload:
    """Turn the raw settings form into a validated payload."""
    footer_text = form.get("footer_text", "").strip()[:MAX_FOOTER_TEXT]
    menu_pages = json.dumps(parse_menu_pages(_menu_values(form)))

    return SiteSettingsPayload(
        comments_enabled=_checkbox(form, "comments_enabled"),
        footer_text=footer_text,
        footer_show_posts=_checkbox(form, "footer_show_posts"),
        footer_show_tags=_checkbox(form, "footer_show_tags"),
        show_pages_in_menu=_checkbox(form, "show_pages_in_menu"),
        menu_pages=menu_pages,
    )


def read_site_settings() -> "SiteSettings | None":
    """Read the single ``SiteSettings`` row, at most once per request.

    The theme service, the public context processors and the navigation
    service all need the same row. Reading it once per request keeps the
    homepage inside its query budget and guarantees every consumer sees the
    same values.

    The row is cached on the application context and dropped at the start of
    every request, so a write is always visible to the next request. The
    caller owns any database error handling: an ``OperationalError`` is
    raised rather than swallowed.
    """
    from flask import g
    from sqlalchemy import select

    from app.extensions import db
    from app.models import SiteSettings

    try:
        cached = g.__dict__.get(_SETTINGS_CACHE_ATTR, _UNSET)
    except RuntimeError:
        cached = _UNSET

    if cached is not _UNSET:
        return cached

    settings = db.session.execute(
        select(SiteSettings).order_by(SiteSettings.id).limit(1)
    ).scalar_one_or_none()

    try:
        setattr(g, _SETTINGS_CACHE_ATTR, settings)
    except RuntimeError:
        pass
    return settings


def invalidate_site_settings_cache() -> None:
    """Drop the cached ``SiteSettings`` row for the current context."""
    from flask import g

    try:
        g.__dict__.pop(_SETTINGS_CACHE_ATTR, None)
    except RuntimeError:
        pass
