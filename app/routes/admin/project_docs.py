from __future__ import annotations

import hashlib
from mimetypes import guess_type

from flask import abort, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import current_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import MAX_UPLOAD_SIZE
from app.extensions import db
from app.models import AdminAuditLog, Project, ProjectDocument, ProjectDocumentAsset
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import _save_image
from app.services import project_docs
from app.services.project_docs import DocumentPathError
from app.services.project_docs_sync import ProjectDocsSyncError, _normalize_root, sync_project_docs
from app.services.project_releases import sync_project_releases
from app.services.github_client import validate_repository_identity
from app.storage import get_storage

MAX_DOCUMENT_ASSET_BYTES = min(MAX_UPLOAD_SIZE, 5 * 1024 * 1024)


def _project(project_id: int) -> Project:
    project = db.session.get(Project, project_id)
    if project is None:
        abort(404)
    return project


def _document(project_id: int, document_id: int) -> ProjectDocument:
    document = db.session.execute(
        select(ProjectDocument).where(
            ProjectDocument.id == document_id,
            ProjectDocument.project_id == project_id,
            ProjectDocument.version_key == "current",
        )
    ).scalar_one_or_none()
    if document is None:
        abort(404)
    return document


def _audit(action: str, project: Project, document: ProjectDocument | None = None) -> None:
    db.session.add(
        AdminAuditLog(
            actor_id=current_user.id,
            action=action,
            target_id=document.id if document and document.id else project.id,
            target_type="project_document" if document else "project",
            details=f"Project documentation {action.rsplit('.', 1)[-1]} for project id {project.id}",
            ip_address=request.remote_addr,
        )
    )


def _render_editor(
    project: Project,
    document: ProjectDocument | None,
    errors: list[str] | None = None,
    *,
    status: int = 200,
) -> ResponseReturnValue:
    return (
        render_template(
            "admin/project_doc_editor.html",
            project=project,
            document=document,
            errors=errors or [],
        ),
        status,
    )


def _document_values(project: Project, document_id: int | None) -> tuple[dict | None, list[str]]:
    errors: list[str] = []
    try:
        path = project_docs.normalize_document_path(request.form.get("path", ""))
    except DocumentPathError:
        return None, ["Enter a safe Markdown path ending in .md or .markdown."]

    collision = project_docs.find_path_collision(project.id, path, document_id=document_id)
    if collision is not None:
        errors.append("A document already uses this path, including a case-insensitive match.")

    title = request.form.get("title", "").strip()
    if not title or len(title) > project_docs.MAX_DOC_TITLE:
        errors.append("A document title is required and must be 200 characters or fewer.")
    body = request.form.get("body", "")
    if len(body) > project_docs.MAX_DOC_BODY:
        errors.append("Document Markdown must be 100,000 characters or fewer.")
    nav_title = request.form.get("nav_title", "").strip()
    if len(nav_title) > project_docs.MAX_DOC_NAV_TITLE:
        errors.append("Navigation titles must be 120 characters or fewer.")
    try:
        nav_order = int(request.form.get("nav_order", "0"))
    except (TypeError, ValueError):
        errors.append("Navigation order must be a whole number.")
        nav_order = 0
    if not -100_000 <= nav_order <= 100_000:
        errors.append("Navigation order must be between -100000 and 100000.")
    if errors:
        return None, errors
    return {
        "path": path,
        "title": title,
        "body": body,
        "nav_title": nav_title or None,
        "nav_order": nav_order,
        "published": request.form.get("published") == "1",
    }, []


def _save_document(
    project: Project, document: ProjectDocument | None
) -> tuple[ProjectDocument | None, list[str]]:
    values, errors = _document_values(project, document.id if document else None)
    if errors or values is None:
        return None, errors
    if document is None:
        document = ProjectDocument(project_id=project.id, version_key="current")
        db.session.add(document)
    for key, value in values.items():
        setattr(document, key, value)
    try:
        db.session.flush()
        _audit("project_docs.save", project, document)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None, ["A document with that path already exists."]
    return document, []


@admin.route("/projects/<int:project_id>/docs", methods=["GET"])
@admin_required
def project_docs_admin(project_id: int) -> ResponseReturnValue:
    project = _project(project_id)
    documents = project_docs.list_documents(project.id, published_only=False)
    assets = db.session.execute(
        select(ProjectDocumentAsset)
        .where(ProjectDocumentAsset.project_id == project.id)
        .order_by(ProjectDocumentAsset.path)
    ).scalars()
    return render_template(
        "admin/project_docs.html",
        project=project,
        documents=documents,
        assets=list(assets),
    )


@admin.route("/projects/<int:project_id>/docs/settings", methods=["POST"])
@admin_required
def project_docs_settings(project_id: int) -> ResponseReturnValue:
    project = _project(project_id)
    raw_home_path = request.form.get("docs_home_path", "").strip()
    home_path = None
    if raw_home_path:
        try:
            home_path = project_docs.normalize_document_path(raw_home_path)
        except DocumentPathError:
            flash("The documentation home must be a valid Markdown path.", "error")
            return redirect(url_for("admin.project_docs_admin", project_id=project.id))
        home = project_docs.get_document(project, home_path, published_only=False)
        if home is None or not home.published:
            flash("The documentation home must identify a published document.", "error")
            return redirect(url_for("admin.project_docs_admin", project_id=project.id))
    source_kind = request.form.get("docs_source_kind", "local")
    if source_kind not in {"local", "github"}:
        flash("Choose a valid documentation source.", "error")
        return redirect(url_for("admin.project_docs_admin", project_id=project.id))
    owner = request.form.get("github_owner", "").strip()
    repository = request.form.get("github_repository", "").strip()
    ref = request.form.get("github_docs_ref", "").strip() or None
    try:
        root = _normalize_root(request.form.get("github_docs_root", "docs").strip() or "docs")
        if owner or repository:
            owner, repository = validate_repository_identity(owner, repository)
        elif source_kind == "github":
            raise ValueError("A public GitHub owner and repository are required.")
        if ref and (len(ref) > 256 or any(ord(char) < 32 for char in ref)):
            raise ValueError("The GitHub ref is invalid.")
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin.project_docs_admin", project_id=project.id))
    project.docs_enabled = request.form.get("docs_enabled") == "1"
    project.docs_home_path = home_path
    project.docs_source_kind = source_kind
    project.github_owner = owner or None
    project.github_repository = repository or None
    project.github_docs_ref = ref
    project.github_docs_root = root
    _audit("project_docs.settings", project)
    db.session.commit()
    flash("Documentation settings saved.", "success")
    return redirect(url_for("admin.project_docs_admin", project_id=project.id))


@admin.route("/projects/<int:project_id>/docs/sync", methods=["POST"])
@admin_required
def project_docs_sync(project_id: int) -> ResponseReturnValue:
    project = _project(project_id)
    try:
        snapshot = sync_project_docs(project.id)
    except ProjectDocsSyncError as exc:
        flash(f"Documentation sync failed: {exc}", "error")
    else:
        _audit("project_docs.sync", project)
        db.session.commit()
        flash(
            f"Documentation snapshot {snapshot.commit_sha[:12]} is active ({snapshot.file_count} files).",
            "success",
        )
    return redirect(url_for("admin.project_docs_admin", project_id=project.id))


@admin.route("/projects/<int:project_id>/releases/settings", methods=["POST"])
@admin_required
def project_releases_settings(project_id: int) -> ResponseReturnValue:
    project = _project(project_id)
    project.releases_enabled = request.form.get("releases_enabled") == "1"
    project.releases_include_prereleases = request.form.get("include_prereleases") == "1"
    _audit("project_releases.settings", project)
    db.session.commit()
    flash("Release catalog settings saved.", "success")
    return redirect(url_for("admin.project_docs_admin", project_id=project.id))


@admin.route("/projects/<int:project_id>/releases/sync", methods=["POST"])
@admin_required
def project_releases_sync(project_id: int) -> ResponseReturnValue:
    project = _project(project_id)
    try:
        releases = sync_project_releases(project.id)
    except ProjectDocsSyncError as exc:
        flash(f"Release metadata sync failed: {exc}", "error")
    else:
        _audit("project_releases.sync", project)
        db.session.commit()
        flash(f"Cached {len(releases)} published releases.", "success")
    return redirect(url_for("admin.project_docs_admin", project_id=project.id))


@admin.route("/projects/<int:project_id>/docs/new", methods=["GET", "POST"])
@admin_required
def project_doc_new(project_id: int) -> ResponseReturnValue:
    project = _project(project_id)
    if request.method == "GET":
        return _render_editor(project, None)
    document, errors = _save_document(project, None)
    if errors or document is None:
        return _render_editor(
            project, None, errors or ["The document could not be saved."], status=400
        )
    flash("Project document created.", "success")
    return redirect(
        url_for("admin.project_doc_edit", project_id=project.id, document_id=document.id)
    )


@admin.route("/projects/<int:project_id>/docs/<int:document_id>/edit", methods=["GET", "POST"])
@admin_required
def project_doc_edit(project_id: int, document_id: int) -> ResponseReturnValue:
    project = _project(project_id)
    document = _document(project.id, document_id)
    if request.method == "GET":
        return _render_editor(project, document)
    saved, errors = _save_document(project, document)
    if errors or saved is None:
        return _render_editor(
            project, document, errors or ["The document could not be saved."], status=400
        )
    flash("Project document saved.", "success")
    return redirect(url_for("admin.project_doc_edit", project_id=project.id, document_id=saved.id))


@admin.route("/projects/<int:project_id>/docs/<int:document_id>/move", methods=["POST"])
@admin_required
def project_doc_move(project_id: int, document_id: int) -> ResponseReturnValue:
    project = _project(project_id)
    document = _document(project.id, document_id)
    direction = request.form.get("direction")
    if direction not in {"up", "down"}:
        abort(400)
    ordered = project_docs.list_documents(project.id, published_only=False)
    index = ordered.index(document)
    neighbor_index = index - 1 if direction == "up" else index + 1
    if 0 <= neighbor_index < len(ordered):
        ordered.pop(index)
        ordered.insert(neighbor_index, document)
        for position, item in enumerate(ordered):
            item.nav_order = position * 10
        _audit("project_docs.reorder", project, document)
        db.session.commit()
    return redirect(url_for("admin.project_docs_admin", project_id=project.id))


@admin.route("/projects/<int:project_id>/docs/assets", methods=["POST"])
@admin_required
def project_doc_asset_upload(project_id: int) -> ResponseReturnValue:
    project = _project(project_id)
    try:
        path = project_docs.normalize_asset_path(request.form.get("path", ""))
    except DocumentPathError:
        flash("Enter a safe image path ending in PNG, JPG, GIF, or WebP.", "error")
        return redirect(url_for("admin.project_docs_admin", project_id=project.id))
    upload = request.files.get("asset")
    if upload is None or not upload.filename:
        flash("Choose an image to upload.", "error")
        return redirect(url_for("admin.project_docs_admin", project_id=project.id))
    upload.seek(0, 2)
    upload_size = upload.tell()
    upload.seek(0)
    if upload_size <= 0 or upload_size > MAX_DOCUMENT_ASSET_BYTES:
        flash(
            f"Images must be between 1 byte and {MAX_DOCUMENT_ASSET_BYTES // (1024 * 1024)} MiB.",
            "error",
        )
        return redirect(url_for("admin.project_docs_admin", project_id=project.id))
    storage_key, error = _save_image(upload)
    if error or not storage_key:
        flash(error or "The image could not be stored.", "error")
        return redirect(url_for("admin.project_docs_admin", project_id=project.id))
    storage = get_storage()
    data = storage.load(storage_key)
    if not data or len(data) > MAX_DOCUMENT_ASSET_BYTES:
        storage.delete(storage_key)
        flash("The stored image did not pass the size check.", "error")
        return redirect(url_for("admin.project_docs_admin", project_id=project.id))
    content_type = guess_type(storage_key)[0]
    if content_type not in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
        storage.delete(storage_key)
        flash("Only PNG, JPG, GIF, and WebP images are supported.", "error")
        return redirect(url_for("admin.project_docs_admin", project_id=project.id))

    existing = project_docs.get_document_asset(project, path)
    previous_key = existing.storage_key if existing else None
    if existing is None:
        existing = ProjectDocumentAsset(project_id=project.id, path=path, storage_key=storage_key)
        db.session.add(existing)
    existing.storage_key = storage_key
    existing.content_type = content_type
    existing.file_size = len(data)
    existing.sha256 = hashlib.sha256(data).hexdigest()
    try:
        db.session.flush()
        _audit("project_docs.asset_upload", project)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        storage.delete(storage_key)
        flash("An image at that project documentation path already exists.", "error")
        return redirect(url_for("admin.project_docs_admin", project_id=project.id))
    if previous_key and previous_key != storage_key:
        storage.delete(previous_key)
    flash("Documentation image uploaded.", "success")
    return redirect(url_for("admin.project_docs_admin", project_id=project.id))


@admin.route("/projects/<int:project_id>/docs/assets/<int:asset_id>/delete", methods=["POST"])
@admin_required
def project_doc_asset_delete(project_id: int, asset_id: int) -> ResponseReturnValue:
    project = _project(project_id)
    asset = db.session.execute(
        select(ProjectDocumentAsset).where(
            ProjectDocumentAsset.id == asset_id,
            ProjectDocumentAsset.project_id == project.id,
        )
    ).scalar_one_or_none()
    if asset is None:
        abort(404)
    storage_key = asset.storage_key
    db.session.delete(asset)
    _audit("project_docs.asset_delete", project)
    db.session.commit()
    get_storage().delete(storage_key)
    flash("Documentation image removed.", "success")
    return redirect(url_for("admin.project_docs_admin", project_id=project.id))


@admin.route("/projects/<int:project_id>/docs/<int:document_id>/delete", methods=["POST"])
@admin_required
def project_doc_delete(project_id: int, document_id: int) -> ResponseReturnValue:
    project = _project(project_id)
    document = _document(project.id, document_id)
    db.session.delete(document)
    _audit("project_docs.delete", project, document)
    db.session.commit()
    flash("Project document deleted.", "success")
    return redirect(url_for("admin.project_docs_admin", project_id=project.id))


@admin.route("/projects/<int:project_id>/docs/preview", methods=["POST"])
@admin_required
def project_docs_preview(project_id: int) -> ResponseReturnValue:
    project = _project(project_id)
    values, errors = _document_values(project, None)
    if errors or values is None:
        return _render_editor(project, None, errors, status=400)
    draft = ProjectDocument(
        project_id=project.id,
        version_key="current",
        **values,
    )
    documents = project_docs.list_documents(project.id)
    return render_template(
        "projects/docs.html",
        project=project,
        document=draft,
        documents=documents,
        document_index=None,
        rendered_body=project_docs.render_document(project, draft),
        preview=True,
    )
