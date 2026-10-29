from __future__ import annotations

import unicodedata
from html import escape
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

from sqlalchemy import select

from app.extensions import db
from app.filters import get_media_url
from app.markdown_renderer import render_markdown
from app.models import Project, ProjectDocument, ProjectDocumentAsset

MAX_DOC_PATH = 512
MAX_DOC_DEPTH = 16
MAX_DOC_BODY = 100_000
MAX_DOC_TITLE = 200
MAX_DOC_NAV_TITLE = 120
ALLOWED_DOC_ASSET_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})


class DocumentPathError(ValueError):
    pass


def _normalize_path(value: str, suffixes: frozenset[str]) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_DOC_PATH:
        raise DocumentPathError("Invalid document path")
    if unquote(value) != value or "%" in value or "\\" in value or value.startswith("/"):
        raise DocumentPathError("Invalid document path")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise DocumentPathError("Invalid document path")
    value = unicodedata.normalize("NFC", value)
    parts = value.split("/")
    if len(parts) > MAX_DOC_DEPTH or any(part in {"", ".", ".."} for part in parts):
        raise DocumentPathError("Invalid document path")
    if not any(parts[-1].lower().endswith(suffix) for suffix in suffixes):
        raise DocumentPathError("Invalid document path")
    if any(unicodedata.normalize("NFKC", part) != part for part in parts):
        raise DocumentPathError("Invalid document path")
    return "/".join(parts)


def normalize_document_path(value: str) -> str:
    return _normalize_path(value, frozenset({".md", ".markdown"}))


def normalize_asset_path(value: str) -> str:
    return _normalize_path(value, ALLOWED_DOC_ASSET_EXTENSIONS)


def _resolve_relative_parts(base_parts: list[str], relative: str) -> list[str] | None:
    """Resolve a relative reference against the directory of the linking document.

    ``.`` segments are dropped and ``..`` segments pop one directory. A ``..``
    that would climb above the documentation root escapes the root and is
    rejected rather than clamped, so a link can never address content the
    project does not publish.
    """
    resolved = list(base_parts)
    for part in relative.split("/"):
        if part == ".":
            continue
        if part == "..":
            if not resolved:
                return None
            resolved.pop()
            continue
        if not part:
            return None
        resolved.append(part)
    return resolved or None


def _relative_reference(relative: str) -> str | None:
    """Return the path component of a relative reference.

    A fragment or a query is not part of the path, and a reference that names
    a scheme or a host is not relative at all.
    """
    try:
        parsed = urlsplit(relative)
    except ValueError:
        return None
    if parsed.scheme or parsed.netloc:
        return None
    return parsed.path


def resolve_document_path(base_path: str, relative: str) -> str | None:
    """Return the canonical document path a relative link points at.

    ``base_path`` is the path of the document holding the link. The result is
    ``None`` when the reference escapes the documentation root or does not name
    a Markdown document.
    """
    reference = _relative_reference(relative)
    if reference is None:
        return None
    parts = _resolve_relative_parts(base_path.split("/")[:-1], reference)
    if parts is None:
        return None
    try:
        return normalize_document_path("/".join(parts))
    except DocumentPathError:
        return None


def resolve_asset_path(base_path: str, relative: str) -> str | None:
    """Return the canonical asset path a relative image reference points at."""
    reference = _relative_reference(relative)
    if reference is None:
        return None
    parts = _resolve_relative_parts(base_path.split("/")[:-1], reference)
    if parts is None:
        return None
    try:
        return normalize_asset_path("/".join(parts))
    except DocumentPathError:
        return None


def list_documents(project_id: int, published_only: bool = True) -> list[ProjectDocument]:
    project = db.session.get(Project, project_id)
    if project is None:
        return []
    statement = select(ProjectDocument).where(ProjectDocument.project_id == project_id)
    if project.docs_source_kind == "github" and project.active_docs_snapshot_id:
        statement = statement.where(ProjectDocument.snapshot_id == project.active_docs_snapshot_id)
    else:
        statement = statement.where(ProjectDocument.snapshot_id.is_(None))
        statement = statement.where(ProjectDocument.version_key == "current")
    if published_only:
        statement = statement.where(ProjectDocument.published.is_(True))
    return list(
        db.session.execute(
            statement.order_by(ProjectDocument.nav_order, ProjectDocument.path)
        ).scalars()
    )


def get_document(
    project: Project, path: str, published_only: bool = True
) -> ProjectDocument | None:
    try:
        path = normalize_document_path(path)
    except DocumentPathError:
        return None
    statement = select(ProjectDocument).where(
        ProjectDocument.project_id == project.id,
        ProjectDocument.path == path,
    )
    if project.docs_source_kind == "github" and project.active_docs_snapshot_id:
        statement = statement.where(ProjectDocument.snapshot_id == project.active_docs_snapshot_id)
    else:
        statement = statement.where(
            ProjectDocument.snapshot_id.is_(None), ProjectDocument.version_key == "current"
        )
    if published_only:
        statement = statement.where(ProjectDocument.published.is_(True))
    return db.session.execute(statement).scalar_one_or_none()


def find_path_collision(
    project_id: int, path: str, *, document_id: int | None = None
) -> ProjectDocument | None:
    normalized = normalize_document_path(path)
    documents = db.session.execute(
        select(ProjectDocument).where(
            ProjectDocument.project_id == project_id,
            ProjectDocument.version_key == "current",
        )
    ).scalars()
    return next(
        (
            document
            for document in documents
            if document.id != document_id and document.path.casefold() == normalized.casefold()
        ),
        None,
    )


def get_document_asset(project: Project, path: str) -> ProjectDocumentAsset | None:
    try:
        path = normalize_asset_path(path)
    except DocumentPathError:
        return None
    return db.session.execute(
        select(ProjectDocumentAsset).where(
            ProjectDocumentAsset.project_id == project.id,
            ProjectDocumentAsset.path == path,
        )
    ).scalar_one_or_none()


class _Links(HTMLParser):
    def __init__(self, project: Project, document: ProjectDocument):
        super().__init__(convert_charrefs=False)
        self.project = project
        self.document = document
        self.output: list[str] = []

    def handle_starttag(self, tag, attrs):
        rewritten = []
        for key, value in attrs:
            if value is None:
                continue
            if key in {"href", "src"}:
                value = self._resolve(tag, key, value)
                if value is None:
                    continue
            rewritten.append(f'{escape(key, quote=True)}="{escape(value, quote=True)}"')
        self.output.append(f"<{tag}" + (" " + " ".join(rewritten) if rewritten else "") + ">")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.output[-1] = self.output[-1][:-1] + "/>"

    def handle_endtag(self, tag):
        self.output.append(f"</{tag}>")

    def handle_data(self, data):
        self.output.append(data)

    def handle_entityref(self, name):
        self.output.append(f"&{name};")

    def handle_charref(self, name):
        self.output.append(f"&#{name};")

    def _resolve(self, tag: str, attribute: str, value: str) -> str | None:
        try:
            parsed = urlsplit(value)
        except ValueError:
            return None
        if parsed.scheme:
            if parsed.scheme.lower() == "mailto" and tag == "a" and attribute == "href":
                return value
            if parsed.scheme.lower() == "https" and tag == "a" and attribute == "href":
                if parsed.username or parsed.password or not parsed.hostname:
                    return None
                return value
            return None
        if value.startswith("//"):
            return None
        if not parsed.path:
            if tag == "img" or not parsed.fragment:
                return None
            return f"{self._url(self.document.path)}#{parsed.fragment}"

        if tag == "img" and attribute == "src":
            asset_path = resolve_asset_path(self.document.path, parsed.path)
            if asset_path is None:
                return None
            asset = get_document_asset(self.project, asset_path)
            if asset is None:
                return None
            return get_media_url(asset.storage_key)

        target = resolve_document_path(self.document.path, parsed.path)
        if target is None:
            return None
        if get_document(self.project, target) is None:
            return None
        suffix = f"#{parsed.fragment}" if parsed.fragment else ""
        return f"{self._url(target)}{suffix}"

    def _url(self, path: str) -> str:
        from flask import url_for

        return url_for("public.project_doc", slug=self.project.slug, doc_path=path)


def render_document(project: Project, document: ProjectDocument) -> str:
    parser = _Links(project, document)
    parser.feed(render_markdown(document.body))
    return "".join(parser.output)


def home_document(project: Project) -> ProjectDocument | None:
    docs = list_documents(project.id)
    if project.docs_home_path:
        explicit = get_document(project, project.docs_home_path)
        if explicit:
            return explicit
    return next(
        (doc for doc in docs if doc.path.lower() in {"index.md", "readme.md"}),
        docs[0] if docs else None,
    )
