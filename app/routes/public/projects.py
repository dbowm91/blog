"""Public routes for the project directory and the project landing pages."""

from __future__ import annotations

import logging
from typing import Any

from flask import abort, render_template
from flask.typing import ResponseReturnValue

from app import limiter
from app.services import projects as project_service

logger = logging.getLogger(__name__)

_REGISTERED_BLUEPRINTS: set[str] = set()


def render_project(
    project: Any,
    is_homepage: bool = False,
    is_preview: bool = False,
) -> ResponseReturnValue:
    """Render the landing page of a project.

    The renderer is shared by the project route, the homepage dispatcher and
    the administrator preview, so there is one Markdown and theme path.
    """
    theme_scope = project_service.resolve_project_theme_scope(project)
    return render_template(
        "projects/landing.html",
        project=project,
        theme_scope=theme_scope,
        is_preview=is_preview,
        is_homepage=is_homepage,
    )


def register_project_routes(public: Any) -> None:
    """Register the public project routes on the Blueprint.

    Registration is idempotent, matching the other public route modules.
    """
    if public.name in _REGISTERED_BLUEPRINTS:
        return
    _REGISTERED_BLUEPRINTS.add(public.name)

    @public.route("/projects")
    @limiter.limit("60 per minute")
    def projects_index() -> ResponseReturnValue:
        """Directory of every published project.

        The projection is owned by the project service; the route only
        renders it. The directory always lists every published project,
        including the ones that are promoted into the navigation.
        """
        entries = [
            project_service.project_directory_entry(project)
            for project in project_service.list_published_projects()
        ]
        return render_template("projects/index.html", projects=entries)

    @public.route("/projects/<slug>")
    @limiter.limit("60 per minute")
    def project(slug: str) -> ResponseReturnValue:
        """The landing page of a single published project.

        A draft is a 404 here for everybody. The preview of an unpublished
        project lives on an authenticated admin route.
        """
        found = project_service.get_published_project(slug)
        if found is None:
            abort(404)

        return render_project(found)
