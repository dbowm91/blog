"""Projects API endpoints.

The API uses its own ``projects:*`` scopes. The ``pages:*`` scopes never
grant access to a project, and a project never borrows a page scope.
"""

from typing import Any, Optional

from flask import jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app import limiter
from app.extensions import db
from app.models import Project
from app.routes.api import api
from app.routes.api.auth import require_api_key, require_scope
from app.services import projects as project_service
from app.services.projects import ProjectValidationError

DEFAULT_LIMIT = "20 per minute"
WRITE_LIMIT = "10 per minute"
MAX_SLUG_ATTEMPTS = 100


def _project_to_dict(project: Project) -> dict:
    """Serialize a Project model to a dictionary."""
    return {
        "id": project.id,
        "title": project.title,
        "slug": project.slug,
        "summary": project.summary or "",
        "body": project.body or "",
        "published": project.published,
        "sort_order": project.sort_order,
        "repo_url": project.repo_url,
        "landing_style": project.landing_style,
        "theme_dark_name": project.theme_dark_name,
        "theme_light_name": project.theme_light_name,
        "show_in_nav": project.show_in_nav,
        "nav_label": project.nav_label,
        "hero_image": project.hero_image,
        "hero_image_alt": project.hero_image_alt,
        "screenshots": project.screenshot_keys,
        "features": project.feature_items,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }


def _merged_form(project: Optional[Project], data: dict) -> dict:
    """Merge the submitted fields over the stored state of a project.

    The result is a complete form mapping, so the service validates the
    project as a whole rather than field by field.
    """
    merged: dict = {
        "title": "",
        "slug": "",
        "summary": "",
        "body": "",
        "published": False,
        "sort_order": 0,
        "repo_url": "",
        "landing_style": project_service.DEFAULT_LANDING_STYLE,
        "theme_dark_name": "",
        "theme_light_name": "",
        "show_in_nav": False,
        "nav_label": "",
        "hero_image": "",
        "hero_image_alt": "",
        "screenshots": [],
        "features": [],
    }
    if project is not None:
        merged.update(
            {
                "title": project.title,
                "slug": project.slug,
                "summary": project.summary or "",
                "body": project.body or "",
                "published": project.published,
                "sort_order": project.sort_order,
                "repo_url": project.repo_url or "",
                "landing_style": project.landing_style,
                "theme_dark_name": project.theme_dark_name or "",
                "theme_light_name": project.theme_light_name or "",
                "show_in_nav": project.show_in_nav,
                "nav_label": project.nav_label or "",
                "hero_image": project.hero_image or "",
                "hero_image_alt": project.hero_image_alt or "",
                "screenshots": project.screenshot_keys,
                "features": project.feature_items,
            }
        )
    merged.update({key: value for key, value in data.items() if key in merged})
    return merged


@api.route("/projects", methods=["GET"])
@require_api_key
@require_scope("projects:read")
@limiter.limit(DEFAULT_LIMIT)
def list_projects() -> Any:
    """List the projects.

    Query params:
        published: Filter by published status (true/false)

    Returns:
        JSON with a projects array
    """
    published_filter = request.args.get("published")

    query = select(Project).order_by(Project.sort_order.asc(), Project.title.asc())

    if published_filter is not None:
        published_val = published_filter.lower() in ("true", "1", "yes")
        query = query.filter(Project.published == published_val)

    projects = db.session.execute(query).scalars().all()

    return jsonify(
        {
            "projects": [_project_to_dict(project) for project in projects],
            "total": len(projects),
        }
    )


@api.route("/projects/<int:project_id>", methods=["GET"])
@require_api_key
@require_scope("projects:read")
@limiter.limit(DEFAULT_LIMIT)
def get_project(project_id: int) -> Any:
    """Get a single project by ID.

    Returns:
        JSON with the project data or a 404 error
    """
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    return jsonify(_project_to_dict(project))


@api.route("/projects", methods=["POST"])
@require_api_key
@require_scope("projects:write")
@limiter.limit(WRITE_LIMIT)
def create_project() -> Any:
    """Create a project.

    JSON body:
        title: Project title (required)
        slug: URL slug (optional, auto-generated from the title)
        summary: Short plain text for the directory card
        body: Markdown content
        published: Published status (default false)
        sort_order: Position in the directory
        repo_url: Optional https repository link
        landing_style: One of product, showcase, documentation, minimal, terminal
        theme_dark_name: Optional registry theme name
        theme_light_name: Optional registry theme name
        show_in_nav: Promote the project into the site menu
        nav_label: Optional menu label
        hero_image: Optional media key
        hero_image_alt: Optional hero image description
        screenshots: Optional list of media keys
        features: Optional list of {"title": ..., "text": ...} entries

    Returns:
        JSON with the created project data
    """
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        payload = project_service.validate_project_form(_merged_form(None, data))
    except ProjectValidationError as exc:
        return jsonify({"error": "; ".join(exc.messages)}), 400

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
        features=[feature.to_dict() for feature in payload.features],
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
                return jsonify({"error": "Duplicate slug or database constraint violation"}), 409
            project.slug = project_service.generate_unique_project_slug(
                payload.title, exclude_id=project.id, slug=payload.slug
            )
            db.session.add(project)
        except OperationalError:
            db.session.rollback()
            return jsonify({"error": "Database operational error"}), 500

    return jsonify(_project_to_dict(project)), 201


@api.route("/projects/<int:project_id>", methods=["PUT"])
@require_api_key
@require_scope("projects:write")
@limiter.limit(WRITE_LIMIT)
def update_project(project_id: int) -> Any:
    """Update a project.

    Every field is optional; a field that is absent keeps its stored value.

    Returns:
        JSON with the updated project data or a 404 error
    """
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        payload = project_service.validate_project_form(_merged_form(project, data))
    except ProjectValidationError as exc:
        return jsonify({"error": "; ".join(exc.messages)}), 400

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
    project.features = [feature.to_dict() for feature in payload.features]

    if payload.slug != project.slug:
        project.slug = project_service.generate_unique_project_slug(
            payload.title, exclude_id=project_id, slug=payload.slug
        )

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Duplicate slug or database constraint violation"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database operational error"}), 500

    return jsonify(_project_to_dict(project))


@api.route("/projects/<int:project_id>", methods=["DELETE"])
@require_api_key
@require_scope("projects:write")
@limiter.limit(WRITE_LIMIT)
def delete_project(project_id: int) -> Any:
    """Delete a project.

    Returns:
        JSON with a success message or a 404 error
    """
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    title = project.title
    db.session.delete(project)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Database constraint violation"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"error": "Database operational error"}), 500

    return jsonify({"message": f"Project '{title}' deleted successfully"})
