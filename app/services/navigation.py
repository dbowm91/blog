"""Navigation service - resolving the public site navigation.

This module is the single producer of every rendered public nav model.
Templates and routes must not re-derive it.

The resolved model is one ordered list of items. A plain item is a link; a
group item is a link with an optional disclosure menu. The order is fixed:
Posts, then the ordinary Pages, then the directly promoted Projects, then
the grouped Projects entry, and finally the account and admin actions that
the shell renders itself.
"""

from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import Optional, Union

from flask import request, url_for
from sqlalchemy import select

from app.extensions import db
from app.models import Page, Project
from app.services.site_settings import (
    DEFAULT_PROJECTS_MENU_LABEL,
    parse_menu_pages,
    read_site_settings,
    resolve_homepage_target,
)

logger = logging.getLogger(__name__)

POSTS_LINK_KEY = "posts"
PROJECTS_GROUP_KEY = "projects"
PROJECTS_MENU_ID = "nav-projects-menu"


@dataclass(frozen=True, slots=True)
class NavLink:
    """One plain link in the navigation."""

    key: str
    label: str
    url: str
    endpoint: str
    is_active: bool = False

    @property
    def kind(self) -> str:
        return "link"


@dataclass(frozen=True, slots=True)
class NavGroup:
    """A labelled entry that can carry a dropdown of child links.

    The label is itself a link, so the group stays reachable without the
    dropdown. The dropdown is an optional refinement.
    """

    key: str
    label: str
    url: str
    endpoint: str
    menu_id: str
    children: tuple[NavLink, ...] = ()
    is_active: bool = False

    @property
    def kind(self) -> str:
        return "group"

    @property
    def has_children(self) -> bool:
        return bool(self.children)


NavItem = Union[NavLink, NavGroup]


@dataclass(frozen=True, slots=True)
class NavigationModel:
    """The complete public navigation model."""

    items: tuple[NavItem, ...]
    posts: NavLink
    projects_enabled: bool


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


def _current_endpoint() -> Optional[str]:
    try:
        return request.endpoint
    except RuntimeError:
        return None


def _current_slug() -> Optional[str]:
    try:
        view_args = request.view_args or {}
    except RuntimeError:
        return None
    slug = view_args.get("slug")
    return str(slug) if slug else None


def _is_active(endpoint: str, slug: Optional[str] = None) -> bool:
    if _current_endpoint() != endpoint:
        return False
    if slug is None:
        return True
    return _current_slug() == slug


def _project_label(project: Project) -> str:
    """Return the label a project carries in the navigation."""
    return (project.nav_label or "").strip() or project.title


def _page_link(page: Page) -> NavLink:
    return NavLink(
        key=f"page:{page.id}",
        label=page.title,
        url=url_for("public.page", slug=page.slug),
        endpoint="public.page",
        is_active=_is_active("public.page", page.slug),
    )


def _project_link(project: Project) -> NavLink:
    return NavLink(
        key=f"project:{project.id}",
        label=_project_label(project),
        url=url_for("public.project", slug=project.slug),
        endpoint="public.project",
        is_active=_is_active("public.project", project.slug),
    )


def _published_projects() -> list[Project]:
    """Return every published project in directory order."""
    return list(
        db.session.execute(
            select(Project)
            .filter(Project.published.is_(True))
            .order_by(Project.sort_order.asc(), Project.title.asc())
        )
        .scalars()
        .all()
    )


def _posts_link() -> NavLink:
    """Return the Posts entry.

    The blog is the homepage until an operator selects another target, so
    the entry points at the root while the blog is home and at ``/posts``
    once the root renders something else.
    """
    homepage = resolve_homepage_target()
    blog_is_home = homepage.is_blog
    endpoint = "public.index" if blog_is_home else "public.posts"
    url = url_for(endpoint)

    current = _current_endpoint()
    is_active = current == "public.posts" or (blog_is_home and current == "public.index")

    return NavLink(
        key=POSTS_LINK_KEY,
        label="Posts",
        url=url,
        endpoint=endpoint,
        is_active=is_active,
    )


def _projects_group(published: list[Project]) -> Optional[NavGroup]:
    """Return the grouped Projects entry, or ``None`` when it is switched off.

    The group holds every published project that is not promoted into the
    navigation directly, so a promoted project never appears twice.
    """
    settings = read_site_settings()
    if settings is None or not settings.show_projects_in_menu:
        return None

    label = (settings.projects_menu_label or "").strip() or DEFAULT_PROJECTS_MENU_LABEL
    children = tuple(_project_link(project) for project in published if not project.show_in_nav)

    return NavGroup(
        key=PROJECTS_GROUP_KEY,
        label=label,
        url=url_for("public.projects_index"),
        endpoint="public.projects_index",
        menu_id=PROJECTS_MENU_ID,
        children=children,
        is_active=_is_active("public.projects_index"),
    )


def resolve_navigation() -> NavigationModel:
    """Return the complete public navigation model.

    The order is fixed: Posts, the ordinary Pages, the directly promoted
    Projects, and the grouped Projects entry.
    """
    posts = _posts_link()
    items: list[NavItem] = [posts]

    for page in resolve_page_menu():
        items.append(_page_link(page))

    published = _published_projects()
    for project in published:
        if project.show_in_nav:
            items.append(_project_link(project))

    group = _projects_group(published)
    if group is not None:
        items.append(group)

    return NavigationModel(
        items=tuple(items),
        posts=posts,
        projects_enabled=group is not None,
    )


def resolve_navigation_safely() -> NavigationModel:
    """Return the navigation model, or an empty model when resolution fails.

    The public shell must render even when the database is unavailable, so a
    failure degrades to the Posts entry alone.
    """
    try:
        return resolve_navigation()
    except Exception:
        logger.exception("Failed to resolve the site navigation")
        posts = NavLink(
            key=POSTS_LINK_KEY,
            label="Posts",
            url="/",
            endpoint="public.index",
            is_active=False,
        )
        return NavigationModel(items=(posts,), posts=posts, projects_enabled=False)


__all__ = [
    "NavGroup",
    "NavItem",
    "NavLink",
    "NavigationModel",
    "POSTS_LINK_KEY",
    "PROJECTS_GROUP_KEY",
    "PROJECTS_MENU_ID",
    "get_menu_settings",
    "parse_menu_page_ids",
    "resolve_navigation",
    "resolve_navigation_safely",
    "resolve_page_menu",
]
