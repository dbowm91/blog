"""Navigation service - resolving the site page menu.

This module is the single producer of the page menu. Templates and routes
must not re-derive it.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.extensions import db
from app.models import Page
from app.services.site_settings import parse_menu_pages, read_site_settings

logger = logging.getLogger(__name__)


def parse_menu_page_ids(raw: str | None) -> list[int]:
    """Parse the stored ``menu_pages`` value into a list of page ids.

    The column holds a JSON array of page ids in menu order. An empty or
    unparsable value means "no explicit order". Ids that are not positive
    integers, and repeated ids, are discarded.

    The format is owned by ``app.services.site_settings``, which also parses
    the submitted form; this is a thin alias so there is one parser.
    """
    return parse_menu_pages(raw)


def get_menu_settings() -> tuple[bool, list[int]]:
    """Read the page menu settings without flushing the session.

    ``SiteSettings.get_instance()`` flushes, which would push unrelated
    pending changes into the transaction, so the row is read directly.
    """
    settings = read_site_settings()
    if settings is None:
        return True, []
    return bool(settings.show_pages_in_menu), parse_menu_page_ids(settings.menu_pages)


def resolve_page_menu() -> list[Page]:
    """Return the published pages that make up the site navigation menu.

    The explicit ``menu_pages`` order wins when it is stored; ids that no
    longer exist and pages that are not published are dropped. When no
    explicit order is stored the menu falls back to every published page
    flagged ``show_in_menu``, ordered by title.

    The result is read fresh on every call so a page that is published,
    unpublished or deleted is reflected immediately.
    """
    show_pages_in_menu, menu_ids = get_menu_settings()
    if not show_pages_in_menu:
        return []

    if menu_ids:
        pages = (
            db.session.execute(select(Page).filter(Page.published.is_(True), Page.id.in_(menu_ids)))
            .scalars()
            .all()
        )
        by_id = {page.id: page for page in pages}
        return [by_id[page_id] for page_id in menu_ids if page_id in by_id]

    fallback = (
        db.session.execute(
            select(Page)
            .filter(Page.published.is_(True), Page.show_in_menu.is_(True))
            .order_by(Page.title)
        )
        .scalars()
        .all()
    )
    return list(fallback)
