"""Site-level settings: parsing, validation and the homepage selection.

The site settings form owns the comments switch, the footer text, the two
footer column switches, the pages-in-menu switch, the ordered page menu, the
projects-menu switch and label, and the homepage selection. Parsing and
validation live here so the route never interprets raw form values on its own.

The homepage selection spans two tables, so there is no foreign key to lean
on. The service therefore validates the target at write time and falls back
to the blog at render time when the stored target is gone or unpublished.
"""

from __future__ import annotations

import json
import logging

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, Optional

if TYPE_CHECKING:
    from app.models import Page, Project, SiteSettings

logger = logging.getLogger(__name__)

MAX_FOOTER_TEXT = 300
MAX_PROJECTS_MENU_LABEL = 64

HOME_KIND_BLOG = "blog"
HOME_KIND_PAGE = "page"
HOME_KIND_PROJECT = "project"
HOME_KINDS: tuple[str, ...] = (HOME_KIND_BLOG, HOME_KIND_PAGE, HOME_KIND_PROJECT)

DEFAULT_PROJECTS_MENU_LABEL = "Projects"

_SETTINGS_CACHE_ATTR = "_devlog_site_settings"
_HOMEPAGE_CACHE_ATTR = "_devlog_homepage_target"
_UNSET = object()


class SiteSettingsValidationError(ValueError):
    """The submitted site settings failed validation.

    ``messages`` holds one human-readable line per rejected field.
    """

    def __init__(self, messages: Any) -> None:
        self.messages: tuple[str, ...] = tuple(messages)
        super().__init__("; ".join(self.messages))


@dataclass(frozen=True)
class SiteSettingsPayload:
    comments_enabled: bool
    footer_text: str
    footer_show_posts: bool
    footer_show_tags: bool
    show_pages_in_menu: bool
    menu_pages: str
    show_projects_in_menu: bool
    projects_menu_label: str
    homepage_kind: str
    homepage_target_id: Optional[int]


@dataclass(frozen=True)
class HomepageTarget:
    """The resolved homepage selection.

    ``kind`` is one of ``blog``, ``page`` or ``project``. Exactly one of
    ``page`` and ``project`` is set when the kind is not ``blog``.
    """

    kind: str
    page: Optional[Any] = None
    project: Optional[Any] = None

    @property
    def is_blog(self) -> bool:
        return self.kind == HOME_KIND_BLOG

    @property
    def slug(self) -> Optional[str]:
        """Return the slug of the selected target, when there is one."""
        if self.page is not None:
            return getattr(self.page, "slug", None)
        if self.project is not None:
            return getattr(self.project, "slug", None)
        return None


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


def parse_homepage_target_id(raw: object) -> Optional[int]:
    """Parse the submitted homepage target id.

    An empty or unparseable value means "no target", which is what the blog
    homepage needs.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        value = int(text)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _load_page(page_id: int) -> Optional["Page"]:
    from sqlalchemy import select

    from app.extensions import db
    from app.models import Page

    return db.session.execute(select(Page).where(Page.id == page_id)).scalar_one_or_none()


def _load_project(project_id: int) -> Optional["Project"]:
    from sqlalchemy import select

    from app.extensions import db
    from app.models import Project

    return db.session.execute(select(Project).where(Project.id == project_id)).scalar_one_or_none()


def validate_homepage_selection(kind: str, target_id: Optional[int]) -> tuple[str, Optional[int]]:
    """Validate a homepage selection and return the normalized pair.

    The selection is validated as a whole, so a kind and a target that do not
    belong together are rejected together.
    """
    normalized_kind = (kind or "").strip() or HOME_KIND_BLOG
    if normalized_kind not in HOME_KINDS:
        raise SiteSettingsValidationError(
            ["The homepage kind is not one of the available options."]
        )

    if normalized_kind == HOME_KIND_BLOG:
        return HOME_KIND_BLOG, None

    if target_id is None:
        raise SiteSettingsValidationError(["Choose a published target for the homepage."])

    if normalized_kind == HOME_KIND_PAGE:
        page = _load_page(target_id)
        if page is None:
            raise SiteSettingsValidationError(["That page no longer exists."])
        if not page.published:
            raise SiteSettingsValidationError(["That page is not published."])
    else:
        project = _load_project(target_id)
        if project is None:
            raise SiteSettingsValidationError(["That project no longer exists."])
        if not project.published:
            raise SiteSettingsValidationError(["That project is not published."])

    return normalized_kind, target_id


def validate_site_settings(form: Mapping[str, str]) -> SiteSettingsPayload:
    """Turn the raw settings form into a validated payload.

    Raises :class:`SiteSettingsValidationError` when a field is rejected.
    """
    footer_text = form.get("footer_text", "").strip()[:MAX_FOOTER_TEXT]
    menu_pages = json.dumps(parse_menu_pages(_menu_values(form)))

    if "projects_menu_label" in form:
        projects_menu_label = (form.get("projects_menu_label") or "").strip()
        if not projects_menu_label:
            raise SiteSettingsValidationError(["The projects menu label cannot be empty."])
        projects_menu_label = projects_menu_label[:MAX_PROJECTS_MENU_LABEL]
    else:
        projects_menu_label = DEFAULT_PROJECTS_MENU_LABEL

    homepage_kind = (form.get("homepage_kind") or HOME_KIND_BLOG).strip() or HOME_KIND_BLOG
    homepage_target_id = parse_homepage_target_id(form.get("homepage_target_id"))
    homepage_kind, homepage_target_id = validate_homepage_selection(
        homepage_kind, homepage_target_id
    )

    return SiteSettingsPayload(
        comments_enabled=_checkbox(form, "comments_enabled"),
        footer_text=footer_text,
        footer_show_posts=_checkbox(form, "footer_show_posts"),
        footer_show_tags=_checkbox(form, "footer_show_tags"),
        show_pages_in_menu=_checkbox(form, "show_pages_in_menu"),
        menu_pages=menu_pages,
        show_projects_in_menu=_checkbox(form, "show_projects_in_menu"),
        projects_menu_label=projects_menu_label,
        homepage_kind=homepage_kind,
        homepage_target_id=homepage_target_id,
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


def resolve_homepage_target() -> HomepageTarget:
    """Return the homepage selection, failing closed to the blog.

    A stored target that no longer exists, or that is no longer published,
    resolves to the blog index rather than raising. The result is cached for
    the request, so the dispatcher and the canonical URL producer share one
    lookup.
    """
    from flask import g

    try:
        cached = g.__dict__.get(_HOMEPAGE_CACHE_ATTR, _UNSET)
    except RuntimeError:
        cached = _UNSET

    if cached is not _UNSET:
        return cached

    target = _resolve_homepage_target_uncached()
    try:
        setattr(g, _HOMEPAGE_CACHE_ATTR, target)
    except RuntimeError:
        pass
    return target


def _resolve_homepage_target_uncached() -> HomepageTarget:
    settings = read_site_settings()
    if settings is None:
        return HomepageTarget(kind=HOME_KIND_BLOG)

    kind = (settings.homepage_kind or HOME_KIND_BLOG).strip() or HOME_KIND_BLOG
    target_id = settings.homepage_target_id

    if kind == HOME_KIND_BLOG or not target_id:
        return HomepageTarget(kind=HOME_KIND_BLOG)

    if kind == HOME_KIND_PAGE:
        page = _load_page(target_id)
        if page is None or not page.published:
            logger.warning(
                "Homepage page %s is gone or unpublished; falling back to the blog", target_id
            )
            return HomepageTarget(kind=HOME_KIND_BLOG)
        return HomepageTarget(kind=HOME_KIND_PAGE, page=page)

    if kind == HOME_KIND_PROJECT:
        project = _load_project(target_id)
        if project is None or not project.published:
            logger.warning(
                "Homepage project %s is gone or unpublished; falling back to the blog", target_id
            )
            return HomepageTarget(kind=HOME_KIND_BLOG)
        return HomepageTarget(kind=HOME_KIND_PROJECT, project=project)

    logger.warning("Unknown homepage kind %r; falling back to the blog", kind)
    return HomepageTarget(kind=HOME_KIND_BLOG)


def reset_homepage_target_if_needed(kind: str, target_id: int) -> bool:
    """Reset the homepage selection to the blog when its target goes away.

    The selection spans two tables, so the reset is applied by hand in the
    same mutation that deletes or unpublishes the target. Returns ``True``
    when the selection was changed.
    """
    settings = read_site_settings()
    if settings is None:
        return False
    if (settings.homepage_kind or HOME_KIND_BLOG) != kind:
        return False
    if settings.homepage_target_id != target_id:
        return False

    settings.homepage_kind = HOME_KIND_BLOG
    settings.homepage_target_id = None
    invalidate_site_settings_cache()
    return True


def invalidate_site_settings_cache() -> None:
    """Drop the cached ``SiteSettings`` row and homepage target."""
    from flask import g

    try:
        g.__dict__.pop(_SETTINGS_CACHE_ATTR, None)
        g.__dict__.pop(_HOMEPAGE_CACHE_ATTR, None)
    except RuntimeError:
        pass
