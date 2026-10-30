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


def test_every_landing_layout_fits_every_width(app, app_server, page):
    slugs = {}
    with app.app_context():
        for style in ("product", "showcase", "documentation", "minimal", "terminal"):
            slug = f"layout-{style}-{uuid4().hex[:8]}"
            slugs[style] = slug
            db.session.add(
                Project(
                    title=f"{style.title()} Layout",
                    slug=slug,
                    summary="A project landing page",
                    body="Readable project content.",
                    published=True,
                    landing_style=style,
                    repo_url="https://github.com/dbowm91/blog",
                )
            )
        db.session.commit()
        project_ids = [
            project.id
            for project in db.session.execute(
                db.select(Project).where(Project.slug.in_(list(slugs.values())))
            ).scalars()
        ]

    try:
        for style, slug in slugs.items():
            for width in (390, 768, 1280):
                page.set_viewport_size({"width": width, "height": 900})
                page.goto(f"{app_server}/projects/{slug}")
                page.get_by_role("heading", level=1, name=f"{style.title()} Layout").wait_for()
                dimensions = page.evaluate(
                    "({ viewport: document.documentElement.clientWidth, "
                    "content: document.documentElement.scrollWidth })"
                )
                assert dimensions["content"] <= dimensions["viewport"] + 1, (
                    f"{style} overflows at {width}px"
                )
    finally:
        with app.app_context():
            for project_id in project_ids:
                project = db.session.get(Project, project_id)
                if project is not None:
                    db.session.delete(project)
            db.session.commit()


def test_the_documentation_layout_keeps_the_body_in_the_wide_column(app, app_server, page):
    slug = f"docs-layout-{uuid4().hex[:10]}"
    with app.app_context():
        db.session.add(
            Project(
                title="Docs Layout",
                slug=slug,
                body="Readable project content.",
                published=True,
                landing_style="documentation",
                repo_url="https://github.com/dbowm91/blog",
            )
        )
        db.session.commit()
        project_ids = [
            project.id
            for project in db.session.execute(
                db.select(Project).where(Project.slug == slug)
            ).scalars()
        ]

    try:
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{app_server}/projects/{slug}")
        page.get_by_role("heading", level=1, name="Docs Layout").wait_for()
        widths = page.evaluate(
            "(() => {"
            " const main = document.querySelector('.project-docs-main');"
            " const rail = document.querySelector('.project-docs-rail');"
            " return { main: main ? main.getBoundingClientRect().width : 0,"
            "         rail: rail ? rail.getBoundingClientRect().width : 0 };"
            "})()"
        )
        assert widths["rail"] > 0
        assert widths["main"] > widths["rail"]
    finally:
        with app.app_context():
            for project_id in project_ids:
                project = db.session.get(Project, project_id)
                if project is not None:
                    db.session.delete(project)
            db.session.commit()


def test_the_product_layout_renders_the_feature_grid(app, app_server, page):
    slug = f"feature-grid-{uuid4().hex[:10]}"
    with app.app_context():
        db.session.add(
            Project(
                title="Feature Grid",
                slug=slug,
                summary="A project landing page",
                body="Readable project content.",
                published=True,
                landing_style="product",
                features=[
                    {"title": "Single-writer scheduling", "text": "One process owns the queue."},
                    {"title": "Typed configuration", "text": "Every value has an origin."},
                ],
            )
        )
        db.session.commit()
        project_ids = [
            project.id
            for project in db.session.execute(
                db.select(Project).where(Project.slug == slug)
            ).scalars()
        ]

    try:
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{app_server}/projects/{slug}")
        page.get_by_role("heading", name="Single-writer scheduling").wait_for()
        assert page.get_by_role("heading", name="Typed configuration").is_visible()
    finally:
        with app.app_context():
            for project_id in project_ids:
                project = db.session.get(Project, project_id)
                if project is not None:
                    db.session.delete(project)
            db.session.commit()
