from __future__ import annotations

from flask import abort, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import current_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.extensions import db
from app.models import AdminAuditLog, Project
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import _save_image
from app.routes.public.projects import render_project
from app.services import projects as project_service
from app.services.projects import (
    LANDING_STYLES,
    MAX_SCREENSHOTS,
    ProjectValidationError,
)
from app.services.site_settings import HOME_KIND_PROJECT, reset_homepage_target_if_needed
from app.storage import get_storage
from app.themes.service import get_theme_service

MAX_SLUG_ATTEMPTS = 100


def _audit(action: str, project: Project, details: str) -> None:
    """Record an administrative action against a project."""
    db.session.add(
        AdminAuditLog(
            actor_id=current_user.id,
            action=action,
            target_id=project.id,
            target_type="project",
            details=details,
            ip_address=request.remote_addr,
        )
    )


def _theme_choices() -> list:
    """Return the theme descriptors the project editor can offer."""
    try:
        registry = get_theme_service().get_registry()
        return registry.list_themes()
    except Exception:
        return []


def _existing_media_keys() -> list[str]:
    """Return the media keys that are actually stored.

    A submitted key that is not in storage is dropped: a project may only
    point at a file this site holds.
    """
    try:
        storage = get_storage()
    except Exception:
        return []
    try:
        return [info.name for info in storage.list_file_info()]
    except Exception:
        return []


def _resolve_media_keys(submitted: list[str], stored: list[str]) -> list[str]:
    """Keep only the submitted keys that exist in storage."""
    available = set(stored)
    return [key for key in submitted if key in available]


def _apply_uploads(files) -> tuple[dict, list[str]]:
    """Store the uploaded hero image and screenshots.

    Returns the media fields to merge into the project and the list of
    upload errors.
    """
    media: dict = {}
    errors: list[str] = []

    hero = files.get("hero_image_file")
    if hero is not None and hero.filename:
        key, error = _save_image(hero)
        if error:
            errors.append(error)
        elif key:
            media["hero_image"] = key

    screenshots = files.getlist("screenshots_file") if hasattr(files, "getlist") else []
    stored_screenshots: list[str] = []
    for upload in screenshots:
        if not upload.filename:
            continue
        key, error = _save_image(upload)
        if error:
            errors.append(error)
        elif key:
            stored_screenshots.append(key)
    if stored_screenshots:
        media["screenshots"] = stored_screenshots[:MAX_SCREENSHOTS]

    return media, errors


@admin.route("/projects")
@admin_required
def projects_list() -> ResponseReturnValue:
    """
    List every project.

    Methods: GET
    GET: Renders the projects management page.
    Requires: Admin authentication.
    """
    projects = (
        db.session.execute(select(Project).order_by(Project.sort_order.asc(), Project.title.asc()))
        .scalars()
        .all()
    )
    return render_template("admin/projects.html", projects=projects)


@admin.route("/projects/new", methods=["GET", "POST"])
@admin_required
def new_project() -> ResponseReturnValue:
    """
    Create a project.

    Methods: GET, POST
    GET: Renders the project editor.
    POST: Creates the project from the submitted form.
    Requires: Admin authentication.
    Form params: title, slug, summary, body, landing_style, repo_url,
    sort_order, published, show_in_nav, nav_label, theme_dark_name,
    theme_light_name, hero_image, hero_image_alt, screenshots and the
    optional hero_image_file / screenshots_file uploads.
    """
    if request.method == "GET":
        return render_template(
            "admin/project_editor.html",
            project=None,
            errors=None,
            landing_styles=LANDING_STYLES,
            themes=_theme_choices(),
        )

    payload, errors = _read_project_form()
    if errors:
        return render_template(
            "admin/project_editor.html",
            project=None,
            errors=errors,
            landing_styles=LANDING_STYLES,
            themes=_theme_choices(),
        ), 400

    project = Project(
        title=payload.title,
        slug=project_service.generate_unique_project_slug(payload.title, slug=payload.slug),
        summary=payload.summary,
        body=payload.body,
        published=payload.published,
        sort_order=payload.sort_order,
        repo_url=payload.repo_url,
        landing_style=payload.landing_style,
        theme_dark_name=payload.theme_dark_name,
        theme_light_name=payload.theme_light_name,
        show_in_nav=payload.show_in_nav,
        nav_label=payload.nav_label,
        hero_image=payload.hero_image,
        hero_image_alt=payload.hero_image_alt,
        screenshots=list(payload.screenshots),
    )
    db.session.add(project)

    for attempt in range(MAX_SLUG_ATTEMPTS):
        try:
            db.session.flush()
            db.session.commit()
            break
        except IntegrityError:
            db.session.rollback()
            if attempt == MAX_SLUG_ATTEMPTS - 1:
                raise
            project.slug = project_service.generate_unique_project_slug(
                payload.title, exclude_id=project.id, slug=payload.slug
            )
            db.session.add(project)
        except OperationalError:
            db.session.rollback()
            flash("Database error occurred. Please try again.", "error")
            return redirect(url_for("admin.projects_list"))

    _audit("project.create", project, f"Project '{project.title}' created")
    db.session.commit()

    flash(f"Project '{project.title}' created.", "success")
    return redirect(url_for("admin.projects_list"))


@admin.route("/projects/edit/<int:project_id>", methods=["GET", "POST"])
@admin_required
def edit_project(project_id: int) -> ResponseReturnValue:
    """
    Edit a project.

    Methods: GET, POST
    GET: Renders the project editor with the stored values.
    POST: Updates the project from the submitted form.
    Requires: Admin authentication.
    Path params: project_id (int) - ID of the project to edit.
    """
    project = db.session.get(Project, project_id)
    if not project:
        abort(404)

    if request.method == "GET":
        return render_template(
            "admin/project_editor.html",
            project=project,
            errors=None,
            landing_styles=LANDING_STYLES,
            themes=_theme_choices(),
        )

    payload, errors = _read_project_form()
    if errors:
        return render_template(
            "admin/project_editor.html",
            project=project,
            errors=errors,
            landing_styles=LANDING_STYLES,
            themes=_theme_choices(),
        ), 400

    title_changed = payload.title != project.title

    project.title = payload.title
    project.summary = payload.summary
    project.body = payload.body
    project.published = payload.published
    project.sort_order = payload.sort_order
    project.repo_url = payload.repo_url
    project.landing_style = payload.landing_style
    project.theme_dark_name = payload.theme_dark_name
    project.theme_light_name = payload.theme_light_name
    project.show_in_nav = payload.show_in_nav
    project.nav_label = payload.nav_label
    project.hero_image = payload.hero_image
    project.hero_image_alt = payload.hero_image_alt
    project.screenshots = list(payload.screenshots)

    if payload.slug and payload.slug != project.slug:
        project.slug = project_service.generate_unique_project_slug(
            payload.title, exclude_id=project.id, slug=payload.slug
        )
    elif not payload.slug and title_changed:
        project.slug = project_service.generate_unique_project_slug(
            payload.title, exclude_id=project.id
        )

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        project = db.session.get(Project, project_id)
        if not project:
            flash("Project not found.", "error")
            return redirect(url_for("admin.projects_list"))
        project.slug = project_service.generate_unique_project_slug(
            payload.title, exclude_id=project_id, slug=payload.slug
        )
        project.title = payload.title
        db.session.commit()
    except OperationalError:
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.projects_list"))

    _audit("project.update", project, f"Project '{project.title}' updated")
    db.session.commit()

    flash(f"Project '{project.title}' updated.", "success")
    return redirect(url_for("admin.projects_list"))


@admin.route("/projects/preview/<int:project_id>")
@admin_required
def preview_project(project_id: int) -> ResponseReturnValue:
    """
    Preview a project landing page.

    Methods: GET
    GET: Renders the landing page of a project, published or not.
    Requires: Admin authentication.
    Path params: project_id (int) - ID of the project to preview.
    """
    project = db.session.get(Project, project_id)
    if not project:
        abort(404)

    return render_project(project, is_preview=not project.published)


@admin.route("/projects/delete/<int:project_id>", methods=["POST"])
@admin_required
def delete_project(project_id: int) -> ResponseReturnValue:
    """
    Delete a project.

    Methods: POST
    POST: Deletes the project.
    Requires: Admin authentication.
    Path params: project_id (int) - ID of the project to delete.
    """
    project = db.session.get(Project, project_id)
    if not project:
        abort(404)

    title = project.title
    target_id = project.id
    reset_homepage_target_if_needed(HOME_KIND_PROJECT, project_id)
    db.session.delete(project)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.projects_list"))

    db.session.add(
        AdminAuditLog(
            actor_id=current_user.id,
            action="project.delete",
            target_id=target_id,
            target_type="project",
            details=f"Project '{title}' deleted",
            ip_address=request.remote_addr,
        )
    )
    db.session.commit()

    flash(f"Project '{title}' deleted.", "success")
    return redirect(url_for("admin.projects_list"))


@admin.route("/projects/<int:project_id>/publish", methods=["POST"])
@admin_required
def set_project_published(project_id: int) -> ResponseReturnValue:
    """
    Publish or unpublish a project.

    Methods: POST
    POST: Sets the published flag of the project.
    Requires: Admin authentication.
    Path params: project_id (int) - ID of the project to update.
    Form params: published - "on" when the project should be published.
    """
    project = db.session.get(Project, project_id)
    if not project:
        abort(404)

    project.published = request.form.get("published") == "on"
    if not project.published:
        reset_homepage_target_if_needed(HOME_KIND_PROJECT, project_id)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.projects_list"))

    _audit(
        "project.publish" if project.published else "project.unpublish",
        project,
        f"Project '{project.title}' {'published' if project.published else 'unpublished'}",
    )
    db.session.commit()

    if project.published:
        flash(f"Project '{project.title}' is now published.", "success")
    else:
        flash(f"Project '{project.title}' is no longer published.", "success")
    return redirect(url_for("admin.projects_list"))


def _read_project_form():
    """Validate the submitted project form.

    Returns the payload and a list of error messages. The uploaded media is
    stored first, so an upload that fails is reported before the payload is
    validated.
    """
    errors: list[str] = []

    try:
        payload = project_service.validate_project_form(request.form)
    except ProjectValidationError as exc:
        return None, list(exc.messages)

    stored_keys = _existing_media_keys()

    uploads, upload_errors = _apply_uploads(request.files)
    errors.extend(upload_errors)

    hero_image = payload.hero_image
    if "hero_image" in uploads:
        hero_image = uploads["hero_image"]
    elif hero_image:
        hero_image = hero_image if hero_image in set(stored_keys) else None
        if hero_image is None:
            errors.append("The hero image is not a file this site holds.")

    screenshots = list(payload.screenshots)
    if "screenshots" in uploads:
        screenshots = list(uploads["screenshots"])
    elif screenshots:
        resolved = _resolve_media_keys(screenshots, stored_keys)
        if len(resolved) != len(screenshots):
            errors.append("One or more screenshots are not files this site holds.")
        screenshots = resolved

    if len(screenshots) > MAX_SCREENSHOTS:
        errors.append(f"A project can carry at most {MAX_SCREENSHOTS} screenshots.")
        screenshots = screenshots[:MAX_SCREENSHOTS]

    if errors:
        return None, errors

    from dataclasses import replace

    return replace(payload, hero_image=hero_image, screenshots=tuple(screenshots)), []
