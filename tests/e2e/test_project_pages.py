"""End-to-end coverage for project layouts and project navigation."""

from uuid import uuid4

import pytest

from app.extensions import db
from app.models import Project, SiteSettings

pytestmark = pytest.mark.e2e


def test_project_page_responsive_and_projects_disclosure_keyboard(app, app_server, page):
    slug = f"responsive-project-{uuid4().hex[:10]}"
    child_slug = f"dropdown-project-{uuid4().hex[:10]}"

    with app.app_context():
        settings = SiteSettings.get_instance()
        previous_settings = (
            settings.show_projects_in_menu,
            settings.projects_menu_label,
            settings.homepage_kind,
            settings.homepage_target_id,
        )
        settings.show_projects_in_menu = True
        settings.projects_menu_label = "Projects"
        settings.homepage_kind = "blog"
        settings.homepage_target_id = None
        db.session.add_all(
            [
                Project(
                    title="Responsive Project",
                    slug=slug,
                    summary="A project landing page",
                    body="Readable project content.",
                    published=True,
                    landing_style="product",
                    show_in_nav=True,
                ),
                Project(
                    title="Dropdown Project",
                    slug=child_slug,
                    body="Dropdown entry",
                    published=True,
                ),
            ]
        )
        db.session.commit()
        project_ids = [
            project.id
            for project in db.session.execute(
                db.select(Project).where(Project.slug.in_([slug, child_slug]))
            ).scalars()
        ]

    try:
        for width in (390, 768, 1280):
            page.set_viewport_size({"width": width, "height": 900})
            page.goto(f"{app_server}/projects/{slug}")
            page.get_by_role("heading", name="Responsive Project").wait_for()
            dimensions = page.evaluate(
                "({ viewport: document.documentElement.clientWidth, "
                "content: document.documentElement.scrollWidth })"
            )
            assert dimensions["content"] <= dimensions["viewport"] + 1

        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{app_server}/")
        toggle = page.get_by_role("button", name="Show all Projects")
        toggle.focus()
        page.keyboard.press("Enter")
        assert toggle.get_attribute("aria-expanded") == "true"
        page.get_by_role("link", name="Dropdown Project").wait_for(state="visible")
    finally:
        with app.app_context():
            for project_id in project_ids:
                project = db.session.get(Project, project_id)
                if project is not None:
                    db.session.delete(project)
            settings = SiteSettings.get_instance()
            (
                settings.show_projects_in_menu,
                settings.projects_menu_label,
                settings.homepage_kind,
                settings.homepage_target_id,
            ) = previous_settings
            db.session.commit()
