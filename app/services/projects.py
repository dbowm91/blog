"""Service layer for project showcase entries.

The service owns every rule about projects that route handlers and templates
must not re-implement: field validation, slug generation and collision
handling, publication filtering, ordering, theme fallback and the
directory-summary projection.

The theme contract is deliberately narrow. A project may name a dark and a
light theme; those names are resolved through the theme registry and the
resulting variables are emitted *inside the project's own container*. The
service never touches the site-wide theme, the visitor's colour scheme or the
theme service's settings cache.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

from sqlalchemy import select

from app.extensions import db
from app.models import Project

logger = logging.getLogger(__name__)

LANDING_STYLES: tuple[str, ...] = ("product", "showcase", "documentation", "minimal", "terminal")
DEFAULT_LANDING_STYLE = "minimal"

# The labels the project editor shows in the landing-layout picker. The stored
# value stays the layout name; only the picker speaks in sentences.
LANDING_STYLE_LABELS: dict[str, str] = {
    "product": "Product page",
    "showcase": "Product showcase",
    "documentation": "Documentation",
    "minimal": "Minimal",
    "terminal": "Terminal",
}

MAX_TITLE_LENGTH = 200
MAX_SUMMARY_LENGTH = 500
MAX_BODY_LENGTH = 100_000
MAX_NAV_LABEL_LENGTH = 120
MAX_REPO_URL_LENGTH = 512
MAX_HERO_IMAGE_LENGTH = 256
MAX_HERO_IMAGE_ALT_LENGTH = 256
MAX_SCREENSHOTS = 6
MAX_FEATURES = 6
MAX_FEATURE_TITLE_LENGTH = 120
MAX_FEATURE_TEXT_LENGTH = 400

# A repository link is a plain https URL. Anything else is rejected rather
# than rendered, so a project page cannot smuggle in a javascript:, data: or
# executable URL, and it cannot carry credentials or a fragment.
ALLOWED_REPO_SCHEMES: frozenset[str] = frozenset({"https"})
GITHUB_HOSTS: frozenset[str] = frozenset({"github.com", "www.github.com"})


class ProjectValidationError(ValueError):
    """A submitted project failed validation.

    ``messages`` holds one human-readable line per rejected field.
    """

    def __init__(self, messages: Iterable[str]) -> None:
        self.messages: tuple[str, ...] = tuple(messages)
        super().__init__("; ".join(self.messages))


@dataclass(frozen=True, slots=True)
class ProjectFeature:
    """One entry of a project's feature list.

    A feature is a title and an optional supporting text. It is the unit the
    product-page layouts render as a card.
    """

    title: str
    text: str = ""

    def to_dict(self) -> dict[str, str]:
        """Return the mapping stored in the ``features`` column."""
        return {"title": self.title, "text": self.text}


@dataclass(frozen=True, slots=True)
class ProjectPayload:
    """A validated, ready-to-persist project."""

    title: str
    slug: str
    summary: str
    body: str
    published: bool
    sort_order: int
    repo_url: Optional[str]
    landing_style: str
    theme_dark_name: Optional[str]
    theme_light_name: Optional[str]
    show_in_nav: bool
    nav_label: Optional[str]
    hero_image: Optional[str]
    hero_image_alt: Optional[str]
    screenshots: tuple[str, ...]
    features: tuple[ProjectFeature, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectDirectoryEntry:
    """The projection the projects directory renders from."""

    id: int
    title: str
    slug: str
    summary: str
    landing_style: str
    repo_url: Optional[str]
    nav_label: Optional[str]
    hero_image: Optional[str]
    hero_image_alt: Optional[str]
    screenshot_count: int
    thumbnail_key: Optional[str] = None

    @property
    def url(self) -> str:
        from flask import url_for

        return url_for("public.project", slug=self.slug)


@dataclass(frozen=True, slots=True)
class ProjectThemeScope:
    """Scoped theme variables for one project container.

    An empty side means "no override"; the site theme applies there.
    """

    dark_vars: dict[str, str]
    light_vars: dict[str, str]
    dark_name: Optional[str]
    light_name: Optional[str]

    @property
    def has_override(self) -> bool:
        return bool(self.dark_vars) or bool(self.light_vars)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def normalize_optional(value: Any) -> Optional[str]:
    """Return a trimmed string, or ``None`` when the value is empty."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def validate_repo_url(raw: Any) -> Optional[str]:
    """Return a normalised repository URL, or ``None`` when it is empty.

    Raises :class:`ProjectValidationError` when the URL is present but is not
    a plain https link without credentials or a fragment.
    """
    value = normalize_optional(raw)
    if value is None:
        return None
    if len(value) > MAX_REPO_URL_LENGTH:
        raise ProjectValidationError(["The repository URL is too long."])
    try:
        parsed = urlparse(value)
    except ValueError:
        raise ProjectValidationError(["The repository URL is not a valid URL."]) from None
    if parsed.scheme.lower() not in ALLOWED_REPO_SCHEMES:
        raise ProjectValidationError(["The repository URL must use https."])
    if parsed.hostname is None:
        raise ProjectValidationError(["The repository URL is not a valid URL."])
    if parsed.username or parsed.password:
        raise ProjectValidationError(["The repository URL must not carry credentials."])
    if parsed.fragment:
        raise ProjectValidationError(["The repository URL must not carry a fragment."])
    return value


def github_repository_identity(url: Optional[str]) -> Optional[tuple[str, str]]:
    """Return the ``(owner, repository)`` of a GitHub repository URL.

    The value is an identity, not a fetch target: nothing in this phase
    contacts the host. A URL that is not a GitHub repository URL returns
    ``None``.
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if parsed.scheme.lower() not in ALLOWED_REPO_SCHEMES:
        return None
    if parsed.hostname is None or parsed.hostname.lower() not in GITHUB_HOSTS:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None
    owner, repository = parts[0], parts[1]
    if repository.endswith(".git"):
        repository = repository[: -len(".git")]
    if not owner or not repository:
        return None
    return owner, repository


def resolve_theme_name(raw: Any) -> Optional[str]:
    """Return a theme name that the registry can resolve, or ``None``.

    An unknown name is dropped rather than stored, so a project never points
    at a theme that cannot be loaded. The caller gets no error for it: a
    missing override falls back to the site theme.
    """
    value = normalize_optional(raw)
    if value is None:
        return None
    from app.themes.service import get_theme_service

    registry = get_theme_service().get_registry()
    try:
        descriptor = registry.resolve(value)
    except Exception:
        logger.warning("project theme %r could not be resolved", value)
        return None
    if descriptor is None:
        logger.warning("project theme %r is not in the registry", value)
        return None
    return descriptor.canonical_name


def validate_project_form(form: Any) -> ProjectPayload:
    """Validate a submitted project form and return the payload.

    The form is a Werkzeug ``MultiDict``; unknown keys are ignored. Every
    rejected field is collected so the caller can report all of them at once.
    """
    messages: list[str] = []

    title = (form.get("title") or "").strip()
    if not title:
        messages.append("The title is required.")
    elif len(title) > MAX_TITLE_LENGTH:
        messages.append(f"The title must be {MAX_TITLE_LENGTH} characters or fewer.")

    summary = (form.get("summary") or "").strip()
    if len(summary) > MAX_SUMMARY_LENGTH:
        messages.append(f"The summary must be {MAX_SUMMARY_LENGTH} characters or fewer.")

    body = form.get("body") or ""
    if len(body) > MAX_BODY_LENGTH:
        messages.append("The body is too long.")

    landing_style = (form.get("landing_style") or "").strip() or DEFAULT_LANDING_STYLE
    if landing_style not in LANDING_STYLES:
        messages.append("The landing layout is not one of the available presets.")
        landing_style = DEFAULT_LANDING_STYLE

    try:
        repo_url = validate_repo_url(form.get("repo_url"))
    except ProjectValidationError as exc:
        messages.extend(exc.messages)
        repo_url = None

    nav_label = normalize_optional(form.get("nav_label"))
    if nav_label and len(nav_label) > MAX_NAV_LABEL_LENGTH:
        messages.append(f"The navigation label must be {MAX_NAV_LABEL_LENGTH} characters or fewer.")
        nav_label = nav_label[:MAX_NAV_LABEL_LENGTH]

    hero_image = normalize_optional(form.get("hero_image"))
    if hero_image and len(hero_image) > MAX_HERO_IMAGE_LENGTH:
        messages.append("The hero image key is too long.")
        hero_image = None

    hero_image_alt = normalize_optional(form.get("hero_image_alt"))
    if hero_image_alt and len(hero_image_alt) > MAX_HERO_IMAGE_ALT_LENGTH:
        messages.append("The hero image description is too long.")
        hero_image_alt = hero_image_alt[:MAX_HERO_IMAGE_ALT_LENGTH]

    screenshots = _parse_screenshot_keys(form.get("screenshots"))
    if len(screenshots) > MAX_SCREENSHOTS:
        messages.append(f"A project can carry at most {MAX_SCREENSHOTS} screenshots.")
        screenshots = screenshots[:MAX_SCREENSHOTS]

    features = _parse_features(form.get("features"))
    if len(features) > MAX_FEATURES:
        messages.append(f"A project can carry at most {MAX_FEATURES} features.")
        features = features[:MAX_FEATURES]
    features = _fit_features(features, messages)

    try:
        sort_order = int(str(form.get("sort_order") or "0").strip() or "0")
    except (TypeError, ValueError):
        messages.append("The sort order must be a whole number.")
        sort_order = 0

    published = _as_bool(form.get("published"))
    show_in_nav = _as_bool(form.get("show_in_nav"))

    if messages:
        raise ProjectValidationError(messages)

    return ProjectPayload(
        title=title,
        slug=normalize_optional(form.get("slug")) or "",
        summary=summary,
        body=body,
        published=published,
        sort_order=sort_order,
        repo_url=repo_url,
        landing_style=landing_style,
        theme_dark_name=resolve_theme_name(form.get("theme_dark_name")),
        theme_light_name=resolve_theme_name(form.get("theme_light_name")),
        show_in_nav=show_in_nav,
        nav_label=nav_label,
        hero_image=hero_image,
        hero_image_alt=hero_image_alt,
        screenshots=tuple(screenshots),
        features=tuple(features),
    )


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_screenshot_keys(raw: Any) -> list[str]:
    """Return the submitted screenshot media keys.

    A multi-file input arrives as a list of ``FileStorage`` objects; a text
    input arrives as a newline separated string. Both are accepted, and only
    strings are kept, so a browser cannot inject an arbitrary URL.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = [part.strip() for part in raw.replace(",", "\n").splitlines()]
        return [part for part in parts if part]
    if isinstance(raw, (list, tuple)):
        keys: list[str] = []
        for item in raw:
            if isinstance(item, str):
                value = item.strip()
                if value:
                    keys.append(value)
            else:
                filename = getattr(item, "filename", None)
                if isinstance(filename, str) and filename.strip():
                    keys.append(filename.strip())
        return keys
    return []


def _parse_features(raw: Any) -> list[ProjectFeature]:
    """Return the submitted feature entries.

    Two shapes are accepted. A text input carries one feature per line as
    ``Title | Description``; the separator is optional, so a line without one
    becomes a title with no description. A JSON body carries a list of
    ``{"title": ..., "text": ...}`` mappings.

    An entry without a title is dropped: a feature card needs a title, and a
    half-typed line in the editor should not become an empty card.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = raw.replace("\r\n", "\n").splitlines()
    if not isinstance(raw, (list, tuple)):
        return []

    features: list[ProjectFeature] = []
    for entry in raw:
        if isinstance(entry, dict):
            title = entry.get("title")
            text = entry.get("text")
            title = title.strip() if isinstance(title, str) else ""
            text = text.strip() if isinstance(text, str) else ""
        elif isinstance(entry, str):
            title, text = _split_feature_line(entry)
        else:
            continue
        if not title:
            continue
        features.append(ProjectFeature(title=title, text=text))
    return features


def _split_feature_line(line: str) -> tuple[str, str]:
    """Split a ``Title | Description`` line into its two halves."""
    value = line.strip()
    if not value:
        return "", ""
    title, separator, text = value.partition("|")
    if not separator:
        return value, ""
    return title.strip(), text.strip()


def _fit_features(features: list[ProjectFeature], messages: list[str]) -> list[ProjectFeature]:
    """Truncate over-long feature fields and report each truncation."""
    fitted: list[ProjectFeature] = []
    for feature in features:
        title = feature.title
        text = feature.text
        if len(title) > MAX_FEATURE_TITLE_LENGTH:
            messages.append(
                f"A feature title must be {MAX_FEATURE_TITLE_LENGTH} characters or fewer."
            )
            title = title[:MAX_FEATURE_TITLE_LENGTH]
        if len(text) > MAX_FEATURE_TEXT_LENGTH:
            messages.append(
                f"A feature description must be {MAX_FEATURE_TEXT_LENGTH} characters or fewer."
            )
            text = text[:MAX_FEATURE_TEXT_LENGTH]
        fitted.append(ProjectFeature(title=title, text=text))
    return fitted


# ---------------------------------------------------------------------------
# Slugs
# ---------------------------------------------------------------------------


def generate_unique_project_slug(
    title: str,
    exclude_id: Optional[int] = None,
    slug: Optional[str] = None,
) -> str:
    """Return a slug that no other project uses.

    An explicit slug wins over the generated one; a collision appends a
    counter, and an exhausted counter set falls back to a short random suffix.
    """
    from app.utils import generate_slug

    base_slug = (slug or "").strip() or generate_slug(title)
    base_slug = base_slug or "project"

    candidate = base_slug
    counter = 2
    while counter <= 100:
        query = select(Project).filter(Project.slug == candidate)
        if exclude_id is not None:
            query = query.filter(Project.id != exclude_id)
        existing = db.session.execute(query).scalar_one_or_none()
        if existing is None:
            return candidate
        candidate = f"{base_slug}-{counter}"
        counter += 1

    import uuid

    return f"{base_slug}-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def _published_query():
    return select(Project).where(Project.published.is_(True))


def list_published_projects() -> list[Project]:
    """Return every published project in directory order.

    The order is the stored ``sort_order`` first and the title second, so two
    projects with the same order still have a stable, readable sequence.
    """
    statement = _published_query().order_by(Project.sort_order.asc(), Project.title.asc())
    return list(db.session.execute(statement).scalars().all())


def list_nav_projects() -> list[Project]:
    """Return the published projects that are promoted into the navigation."""
    statement = (
        _published_query()
        .where(Project.show_in_nav.is_(True))
        .order_by(Project.sort_order.asc(), Project.title.asc())
    )
    return list(db.session.execute(statement).scalars().all())


def list_dropdown_projects() -> list[Project]:
    """Return the published projects that are not promoted into the navigation."""
    statement = (
        _published_query()
        .where(Project.show_in_nav.is_(False))
        .order_by(Project.sort_order.asc(), Project.title.asc())
    )
    return list(db.session.execute(statement).scalars().all())


def get_published_project(slug: str) -> Optional[Project]:
    """Return a published project by slug, or ``None``.

    An unpublished project is invisible here: the public routes answer 404
    rather than revealing that a draft exists.
    """
    if not slug:
        return None
    statement = _published_query().where(Project.slug == slug)
    return db.session.execute(statement).scalar_one_or_none()


def get_project_by_slug(slug: str) -> Optional[Project]:
    """Return a project by slug, published or not.

    The admin preview uses this to reach a draft; the public routes only
    call it after the caller has established that the visitor may see it.
    """
    if not slug:
        return None
    statement = select(Project).where(Project.slug == slug)
    return db.session.execute(statement).scalar_one_or_none()


def get_project(project_id: int) -> Optional[Project]:
    """Return a project by id, published or not."""
    statement = select(Project).where(Project.id == project_id)
    return db.session.execute(statement).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


def project_directory_entry(project: Project) -> ProjectDirectoryEntry:
    """Project a project into the shape the directory renders."""
    screenshots = project.screenshot_keys
    return ProjectDirectoryEntry(
        id=project.id,
        title=project.title,
        slug=project.slug,
        summary=project.summary or "",
        landing_style=project.landing_style or DEFAULT_LANDING_STYLE,
        repo_url=project.repo_url,
        nav_label=project.nav_label,
        hero_image=project.hero_image,
        hero_image_alt=project.hero_image_alt,
        screenshot_count=len(screenshots),
        thumbnail_key=project.hero_image or (screenshots[0] if screenshots else None),
    )


def project_nav_label(project: Project) -> str:
    """Return the label a project carries in the navigation."""
    return (project.nav_label or "").strip() or project.title


def resolve_landing_style(project: Project) -> str:
    """Return the landing layout a project renders with.

    A project whose stored layout is not one of the presets falls back to the
    default, so a template never has to know a layout name that no longer
    exists.
    """
    style = (project.landing_style or "").strip()
    return style if style in LANDING_STYLES else DEFAULT_LANDING_STYLE


# ---------------------------------------------------------------------------
# Theme scope
# ---------------------------------------------------------------------------


def _theme_vars(name: Optional[str]) -> dict[str, str]:
    """Load a theme's legacy variables, or nothing when it cannot be loaded."""
    if not name:
        return {}
    from app.themes.registry import ThemeLoadError, ThemeNotFoundError, ThemeParseFailure
    from app.themes.service import get_theme_service

    registry = get_theme_service().get_registry()
    try:
        loaded = registry.load(name)
    except (ThemeNotFoundError, ThemeParseFailure, ThemeLoadError):
        logger.warning("project theme %r could not be loaded; the site theme applies", name)
        return {}
    except Exception:
        logger.exception("project theme %r failed to load; the site theme applies", name)
        return {}
    return dict(loaded.legacy_vars)


def resolve_project_theme_scope(project: Project) -> ProjectThemeScope:
    """Return the scoped theme variables for a project.

    A side without a resolved theme stays empty, so the site theme keeps
    painting that half of the container. The global theme and the visitor's
    colour scheme are never modified.
    """
    dark_name = project.theme_dark_name or None
    light_name = project.theme_light_name or None
    return ProjectThemeScope(
        dark_vars=_theme_vars(dark_name),
        light_vars=_theme_vars(light_name),
        dark_name=dark_name,
        light_name=light_name,
    )


__all__ = [
    "DEFAULT_LANDING_STYLE",
    "GITHUB_HOSTS",
    "LANDING_STYLES",
    "LANDING_STYLE_LABELS",
    "MAX_FEATURES",
    "MAX_FEATURE_TEXT_LENGTH",
    "MAX_FEATURE_TITLE_LENGTH",
    "MAX_SCREENSHOTS",
    "ProjectDirectoryEntry",
    "ProjectFeature",
    "ProjectPayload",
    "ProjectThemeScope",
    "ProjectValidationError",
    "generate_unique_project_slug",
    "get_project",
    "get_project_by_slug",
    "get_published_project",
    "github_repository_identity",
    "list_dropdown_projects",
    "list_nav_projects",
    "list_published_projects",
    "normalize_optional",
    "project_directory_entry",
    "project_nav_label",
    "resolve_landing_style",
    "resolve_project_theme_scope",
    "resolve_theme_name",
    "validate_project_form",
    "validate_repo_url",
]
