"""Tests for the project pages: model, service, admin, public routes, layouts,
navigation and the configurable homepage."""

from __future__ import annotations

import pytest
from sqlalchemy import event

from app.config import BASE_URL
from app.extensions import db
from app.models import Page, Project, SiteSettings

PUBLIC_SHELL_ENDPOINTS = ("public.login", "public.account", "public.logout")


def _require_public_shell(app):
    missing = [name for name in PUBLIC_SHELL_ENDPOINTS if name not in app.view_functions]
    if missing:
        pytest.skip(f"public shell endpoints not registered yet: {', '.join(missing)}")


def _make_project(
    title="DevLog",
    slug="devlog",
    body="Project body.",
    published=True,
    show_in_nav=False,
    nav_label=None,
    landing_style="minimal",
    sort_order=0,
    repo_url=None,
    theme_dark_name=None,
    theme_light_name=None,
):
    project = Project(
        title=title,
        slug=slug,
        body=body,
        summary=f"{title} summary",
        published=published,
        show_in_nav=show_in_nav,
        nav_label=nav_label,
        landing_style=landing_style,
        sort_order=sort_order,
        repo_url=repo_url,
        theme_dark_name=theme_dark_name,
        theme_light_name=theme_light_name,
    )
    db.session.add(project)
    db.session.commit()
    return project


def _make_page(title="About", slug="about", published=True, show_in_menu=True):
    page = Page(
        title=title,
        slug=slug,
        body=f"{title} body.",
        published=published,
        show_in_menu=show_in_menu,
    )
    db.session.add(page)
    db.session.commit()
    return page


def _settings_row():
    row = db.session.execute(
        db.select(SiteSettings).order_by(SiteSettings.id).limit(1)
    ).scalar_one_or_none()
    if row is None:
        row = SiteSettings()
        db.session.add(row)
        db.session.commit()
    return row


def _set_projects_menu(enabled=True, label="Projects"):
    row = _settings_row()
    row.show_projects_in_menu = enabled
    row.projects_menu_label = label
    db.session.commit()
    return row


def _nav_section(html: str) -> str:
    return html.split('<div class="nav-links"', 1)[1].split('<div class="nav-actions"', 1)[0]


class TestTheProjectModel:
    def test_the_projects_table_exists_with_its_indexes(self, db):
        inspector = db.inspect(db.engine)
        assert inspector.has_table("projects")

        indexes = {index["name"] for index in inspector.get_indexes("projects")}
        assert "ix_projects_published_slug" in indexes
        assert "ix_projects_published_sort_title" in indexes

        columns = {column["name"] for column in inspector.get_columns("projects")}
        for expected in (
            "title",
            "slug",
            "summary",
            "body",
            "published",
            "sort_order",
            "repo_url",
            "landing_style",
            "theme_dark_name",
            "theme_light_name",
            "show_in_nav",
            "nav_label",
        ):
            assert expected in columns

    def test_a_new_project_is_a_draft(self, db):
        project = Project(title="Draft", slug="draft", body="body")
        db.session.add(project)
        db.session.commit()

        assert project.published is False
        assert project.show_in_nav is False
        assert project.landing_style == "minimal"
        assert project.nav_label is None

    def test_the_slug_is_unique(self, db):
        _make_project(title="One", slug="same")
        with pytest.raises(Exception):
            _make_project(title="Two", slug="same")
        db.session.rollback()


class TestTheProjectService:
    def test_it_generates_a_unique_slug(self, db):
        from app.services.projects import generate_unique_project_slug

        _make_project(title="DevLog", slug="devlog")

        assert generate_unique_project_slug("DevLog") == "devlog-2"
        assert generate_unique_project_slug("Other") == "other"

    def test_it_rejects_a_repo_url_with_credentials(self, db):
        from app.services.projects import ProjectValidationError, validate_repo_url

        with pytest.raises(ProjectValidationError):
            validate_repo_url("https://user:pass@github.com/owner/repo")

    def test_it_rejects_a_repo_url_with_a_fragment(self, db):
        from app.services.projects import ProjectValidationError, validate_repo_url

        with pytest.raises(ProjectValidationError):
            validate_repo_url("https://github.com/owner/repo#readme")

    @pytest.mark.parametrize(
        "url",
        [
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "file:///etc/passwd",
            "http://github.com/owner/repo",
        ],
    )
    def test_it_rejects_an_executable_repo_url(self, db, url):
        from app.services.projects import ProjectValidationError, validate_repo_url

        with pytest.raises(ProjectValidationError):
            validate_repo_url(url)

    def test_it_accepts_a_plain_https_repo_url(self, db):
        from app.services.projects import validate_repo_url

        assert validate_repo_url("https://github.com/owner/repo") == "https://github.com/owner/repo"

    def test_it_reads_the_github_identity(self, db):
        from app.services.projects import github_repository_identity

        assert github_repository_identity("https://github.com/owner/repo") == ("owner", "repo")
        assert github_repository_identity("https://github.com/owner/repo.git") == ("owner", "repo")
        assert github_repository_identity("https://example.com/owner/repo") is None

    def test_a_project_without_a_repo_url_is_valid(self, db):
        from app.services.projects import validate_project_form

        payload = validate_project_form({"title": "Manual", "body": "Written by hand."})

        assert payload.repo_url is None
        assert payload.title == "Manual"

    def test_it_rejects_an_unknown_landing_style(self, db):
        from app.services.projects import ProjectValidationError, validate_project_form

        with pytest.raises(ProjectValidationError):
            validate_project_form({"title": "Bad", "landing_style": "hologram"})

    def test_it_drops_an_unknown_theme_name(self, db):
        from app.services.projects import validate_project_form

        payload = validate_project_form({"title": "Bad", "theme_dark_name": "Not A Theme"})

        assert payload.theme_dark_name is None

    def test_it_keeps_a_known_theme_name(self, db):
        from app.services.projects import validate_project_form

        payload = validate_project_form({"title": "Good", "theme_dark_name": "Catppuccin Mocha"})

        assert payload.theme_dark_name == "Catppuccin Mocha"

    def test_it_caps_the_screenshot_count(self, db):
        from app.services.projects import ProjectValidationError, validate_project_form

        with pytest.raises(ProjectValidationError):
            validate_project_form({"title": "Many", "screenshots": [f"key-{i}" for i in range(7)]})

    def test_it_orders_the_directory(self, db):
        from app.services.projects import list_published_projects

        _make_project(title="Beta", slug="beta", sort_order=1)
        _make_project(title="Alpha", slug="alpha", sort_order=0)
        _make_project(title="Draft", slug="draft", published=False)

        assert [project.slug for project in list_published_projects()] == ["alpha", "beta"]

    def test_it_projects_the_directory_summary(self, db):
        from app.services.projects import project_directory_entry

        project = _make_project(title="DevLog", slug="devlog", repo_url="https://github.com/o/r")
        entry = project_directory_entry(project)

        assert entry.slug == "devlog"
        assert entry.summary == "DevLog summary"
        assert entry.repo_url == "https://github.com/o/r"


class TestProjectAdmin:
    def test_the_admin_list_requires_authentication(self, client):
        response = client.get("/admin/projects")

        assert response.status_code in (302, 401, 403)

    def test_the_admin_list_renders(self, authenticated_client):
        _make_project(title="DevLog", slug="devlog")

        html = authenticated_client.get("/admin/projects").get_data(as_text=True)

        assert "DevLog" in html
        assert "/projects/devlog" in html

    def test_it_creates_a_project(self, authenticated_client, db):
        response = authenticated_client.post(
            "/admin/projects/new",
            data={
                "title": "DevLog",
                "slug": "devlog",
                "summary": "A blog engine",
                "body": "Hello",
                "published": "on",
                "landing_style": "product",
            },
        )

        assert response.status_code == 302
        project = db.session.execute(db.select(Project).filter_by(slug="devlog")).scalar_one()
        assert project.published is True
        assert project.landing_style == "product"

    def test_it_rejects_a_missing_title(self, authenticated_client, db):
        response = authenticated_client.post(
            "/admin/projects/new",
            data={"title": "", "body": "Hello"},
        )

        assert response.status_code == 400
        assert db.session.execute(db.select(Project)).scalars().all() == []

    def test_it_rejects_an_invalid_repo_url(self, authenticated_client, db):
        response = authenticated_client.post(
            "/admin/projects/new",
            data={"title": "Bad", "body": "Hello", "repo_url": "javascript:alert(1)"},
        )

        assert response.status_code == 400
        assert db.session.execute(db.select(Project)).scalars().all() == []

    def test_it_edits_a_project(self, authenticated_client, db):
        project = _make_project(title="DevLog", slug="devlog")

        response = authenticated_client.post(
            f"/admin/projects/edit/{project.id}",
            data={"title": "DevLog 2", "body": "Updated", "published": "on"},
        )

        assert response.status_code == 302
        assert db.session.get(Project, project.id).title == "DevLog 2"

    def test_it_deletes_a_project(self, authenticated_client, db):
        project = _make_project(title="DevLog", slug="devlog")

        response = authenticated_client.post(f"/admin/projects/delete/{project.id}")

        assert response.status_code == 302
        assert db.session.get(Project, project.id) is None

    def test_the_preview_is_authenticated(self, client, db):
        project = _make_project(title="Draft", slug="draft", published=False)

        response = client.get(f"/admin/projects/preview/{project.id}")

        assert response.status_code in (302, 401, 403)

    def test_the_preview_renders_a_draft(self, authenticated_client, db):
        project = _make_project(title="Draft", slug="draft", published=False)

        html = authenticated_client.get(f"/admin/projects/preview/{project.id}").get_data(
            as_text=True
        )

        assert "Draft" in html
        assert "not published yet" in html


class TestThePublicProjectRoutes:
    def test_the_directory_lists_every_published_project(self, app, client, db):
        _require_public_shell(app)
        _make_project(title="Alpha", slug="alpha", sort_order=0)
        _make_project(title="Beta", slug="beta", sort_order=1)
        _make_project(title="Draft", slug="draft", published=False)

        html = client.get("/projects").get_data(as_text=True)

        assert "Alpha" in html
        assert "Beta" in html
        assert "Draft" not in html
        assert "/projects/alpha" in html

    def test_the_directory_uses_the_stored_summary(self, app, client, db):
        _require_public_shell(app)
        project = _make_project(title="Alpha", slug="alpha")
        project.summary = "A short summary"
        db.session.commit()

        html = client.get("/projects").get_data(as_text=True)

        assert "A short summary" in html

    def test_a_published_project_has_a_landing_page(self, app, client, db):
        _require_public_shell(app)
        _make_project(title="Alpha", slug="alpha")

        response = client.get("/projects/alpha")

        assert response.status_code == 200
        assert "Alpha" in response.get_data(as_text=True)

    def test_a_draft_is_a_404(self, app, client, db):
        _require_public_shell(app)
        _make_project(title="Draft", slug="draft", published=False)

        assert client.get("/projects/draft").status_code == 404

    def test_a_missing_slug_is_a_404(self, app, client, db):
        _require_public_shell(app)

        assert client.get("/projects/nothing-here").status_code == 404

    def test_the_directory_survives_without_javascript(self, app, client, db):
        _require_public_shell(app)
        _make_project(title="Alpha", slug="alpha")

        html = client.get("/projects").get_data(as_text=True)

        assert '<a href="/projects/alpha">' in html


class TestTheProjectLayouts:
    @pytest.mark.parametrize("style", ["product", "documentation", "minimal", "terminal"])
    def test_every_preset_layout_renders(self, app, client, db, style):
        _require_public_shell(app)
        _make_project(title="Alpha", slug="alpha", landing_style=style)

        html = client.get("/projects/alpha").get_data(as_text=True)

        assert "Alpha" in html
        assert f"project-landing-{style}" in html

    def test_the_layout_is_a_structural_variant(self, app, client, db):
        _require_public_shell(app)
        _make_project(title="Alpha", slug="alpha", landing_style="product")

        html = client.get("/projects/alpha").get_data(as_text=True)

        assert "project-hero" in html

    def test_the_body_is_rendered_as_markdown(self, app, client, db):
        _require_public_shell(app)
        project = _make_project(title="Alpha", slug="alpha")
        project.body = "## A heading\n\nSome **bold** text."
        db.session.commit()

        html = client.get("/projects/alpha").get_data(as_text=True)

        assert "<h2" in html
        assert "<strong>bold</strong>" in html

    def test_a_project_theme_overrides_only_its_own_container(self, app, client, db):
        _require_public_shell(app)
        _make_project(
            title="Alpha",
            slug="alpha",
            theme_dark_name="Catppuccin Latte",
            theme_light_name="Catppuccin Mocha",
        )

        html = client.get("/projects/alpha").get_data(as_text=True)

        assert '[data-color-scheme="dark"] .project-scope' in html
        assert '[data-color-scheme="light"] .project-scope' in html

    def test_a_project_without_a_theme_leaves_the_site_theme_alone(self, app, client, db):
        _require_public_shell(app)
        _make_project(title="Alpha", slug="alpha")

        html = client.get("/projects/alpha").get_data(as_text=True)

        assert ".project-scope {" not in html

    def test_a_project_theme_does_not_leak_into_a_later_page(self, app, client, db):
        _require_public_shell(app)
        _make_project(title="Alpha", slug="alpha", theme_dark_name="Catppuccin Latte")

        client.get("/projects/alpha")
        html = client.get("/").get_data(as_text=True)

        assert '[data-color-scheme="dark"] .project-scope' not in html


class TestTheProjectsApi:
    def _headers(self):
        return {"X-API-Key": "test-key"}

    def test_it_needs_an_api_key(self, client, db):
        response = client.get("/api/projects")

        assert response.status_code == 401

    def test_it_needs_the_projects_read_scope(self, client, db, monkeypatch):
        monkeypatch.setattr("app.routes.api.auth.API_KEY", "test-key")
        monkeypatch.setattr(
            "app.routes.api.auth.scope_allows",
            lambda granted, required: False,
        )

        response = client.get("/api/projects", headers=self._headers())

        assert response.status_code == 403

    def test_it_lists_projects(self, client, db, monkeypatch):
        monkeypatch.setattr("app.routes.api.auth.API_KEY", "test-key")
        _make_project(title="Alpha", slug="alpha")

        response = client.get("/api/projects", headers=self._headers())

        assert response.status_code == 200
        assert response.get_json()["total"] == 1
        assert response.get_json()["projects"][0]["slug"] == "alpha"

    def test_it_creates_a_project(self, client, db, monkeypatch):
        monkeypatch.setattr("app.routes.api.auth.API_KEY", "test-key")

        response = client.post(
            "/api/projects",
            headers=self._headers(),
            json={"title": "Alpha", "body": "Hello", "published": True},
        )

        assert response.status_code == 201
        assert response.get_json()["slug"] == "alpha"

    def test_it_rejects_an_invalid_repo_url(self, client, db, monkeypatch):
        monkeypatch.setattr("app.routes.api.auth.API_KEY", "test-key")

        response = client.post(
            "/api/projects",
            headers=self._headers(),
            json={"title": "Alpha", "repo_url": "javascript:alert(1)"},
        )

        assert response.status_code == 400

    def test_the_page_scope_does_not_grant_project_access(self, db):
        from app.routes.api.auth import VALID_WILDCARD_SCOPES, scope_allows

        assert "projects:*" in VALID_WILDCARD_SCOPES
        assert scope_allows(["pages:*"], "projects:read") is False
        assert scope_allows(["projects:*"], "projects:read") is True
        assert scope_allows(["admin:*"], "projects:write") is True


class TestTheNavigationModel:
    def test_the_default_upgrade_leaves_the_menu_alone(self, app, client, db):
        _require_public_shell(app)
        _make_page(title="About", slug="about")

        html = client.get("/").get_data(as_text=True)
        nav = _nav_section(html)

        assert "/page/about" in nav
        assert "/projects" not in nav

    def test_the_homepage_is_the_blog_by_default(self, app, client, db):
        _require_public_shell(app)

        response = client.get("/")

        assert response.status_code == 200

    def test_the_posts_index_is_reachable(self, app, client, db):
        _require_public_shell(app)

        response = client.get("/posts")

        assert response.status_code == 200

    def test_the_posts_index_paginates(self, app, client, db, sample_post):
        _require_public_shell(app)

        html = client.get("/posts?page=1").get_data(as_text=True)

        assert "Test Post" in html

    def test_a_promoted_project_appears_in_the_navigation(self, app, client, db):
        _require_public_shell(app)
        _make_project(title="DevLog", slug="devlog", show_in_nav=True)

        nav = _nav_section(client.get("/").get_data(as_text=True))

        assert "/projects/devlog" in nav
        assert ">DevLog<" in nav

    def test_a_promoted_project_uses_its_label(self, app, client, db):
        _require_public_shell(app)
        _make_project(title="DevLog", slug="devlog", show_in_nav=True, nav_label="The Engine")

        nav = _nav_section(client.get("/").get_data(as_text=True))

        assert ">The Engine<" in nav

    def test_the_dropdown_holds_the_projects_that_are_not_promoted(self, app, client, db):
        _require_public_shell(app)
        _set_projects_menu(enabled=True)
        _make_project(title="Promoted", slug="promoted", show_in_nav=True)
        _make_project(title="First", slug="first")
        _make_project(title="Second", slug="second")

        nav = _nav_section(client.get("/").get_data(as_text=True))

        assert "/projects/promoted" in nav
        assert "/projects/first" in nav
        assert "/projects/second" in nav
        # The promoted project is a direct link, not a dropdown entry.
        assert nav.count("/projects/promoted") == 1

    def test_a_draft_project_never_reaches_the_navigation(self, app, client, db):
        _require_public_shell(app)
        _set_projects_menu(enabled=True)
        _make_project(title="Draft", slug="draft", published=False, show_in_nav=True)

        nav = _nav_section(client.get("/").get_data(as_text=True))

        assert "/projects/draft" not in nav

    def test_the_projects_menu_can_be_switched_off(self, app, client, db):
        _require_public_shell(app)
        _set_projects_menu(enabled=False)
        _make_project(title="Promoted", slug="promoted", show_in_nav=True)
        _make_project(title="Other", slug="other")

        nav = _nav_section(client.get("/").get_data(as_text=True))

        assert "/projects/promoted" in nav
        assert "/projects/other" not in nav

    def test_the_directory_stays_reachable_when_the_menu_is_off(self, app, client, db):
        _require_public_shell(app)
        _set_projects_menu(enabled=False)
        _make_project(title="Other", slug="other")

        response = client.get("/projects")

        assert response.status_code == 200
        assert "Other" in response.get_data(as_text=True)

    def test_the_projects_entry_links_to_the_directory(self, app, client, db):
        _require_public_shell(app)
        _set_projects_menu(enabled=True, label="Work")
        _make_project(title="Other", slug="other")

        nav = _nav_section(client.get("/").get_data(as_text=True))

        assert ">Work<" in nav
        assert 'href="/projects"' in nav

    def test_the_projects_entry_opens_the_directory_without_a_dropdown(self, app, client, db):
        _require_public_shell(app)
        _set_projects_menu(enabled=True)
        _make_project(title="Promoted", slug="promoted", show_in_nav=True)

        nav = _nav_section(client.get("/").get_data(as_text=True))

        assert 'href="/projects"' in nav
        assert "nav-dropdown-toggle" not in nav

    def test_page_links_are_not_hidden_by_a_project(self, app, client, db):
        _require_public_shell(app)
        _set_projects_menu(enabled=True)
        _make_page(title="About", slug="about")
        _make_project(title="DevLog", slug="devlog", show_in_nav=True)

        nav = _nav_section(client.get("/").get_data(as_text=True))

        assert "/page/about" in nav
        assert "/projects/devlog" in nav

    def test_the_order_is_posts_then_pages_then_projects(self, app, client, db):
        _require_public_shell(app)
        _set_projects_menu(enabled=True)
        _make_page(title="About", slug="about")
        _make_project(title="DevLog", slug="devlog", show_in_nav=True)

        nav = _nav_section(client.get("/").get_data(as_text=True))

        assert nav.index(">Posts<") < nav.index("/page/about")
        assert nav.index("/page/about") < nav.index("/projects/devlog")

    def test_unpublishing_a_project_removes_its_link(self, app, client, db):
        _require_public_shell(app)
        project = _make_project(title="DevLog", slug="devlog", show_in_nav=True)

        nav = _nav_section(client.get("/").get_data(as_text=True))
        assert "/projects/devlog" in nav

        project.published = False
        db.session.commit()

        nav = _nav_section(client.get("/").get_data(as_text=True))
        assert "/projects/devlog" not in nav

    def test_deleting_a_project_removes_its_link(self, app, client, db):
        _require_public_shell(app)
        project = _make_project(title="DevLog", slug="devlog", show_in_nav=True)

        db.session.delete(project)
        db.session.commit()

        nav = _nav_section(client.get("/").get_data(as_text=True))
        assert "/projects/devlog" not in nav

    def test_renaming_a_project_keeps_its_place_in_the_menu(self, app, client, db):
        _require_public_shell(app)
        project = _make_project(title="Old", slug="old", show_in_nav=True, nav_label="Kept")

        project.title = "New"
        project.slug = "new"
        db.session.commit()

        nav = _nav_section(client.get("/").get_data(as_text=True))
        assert "/projects/new" in nav
        assert ">Kept<" in nav

    def test_the_navigation_reads_the_projects_table_once(self, app, client, db):
        _require_public_shell(app)
        _make_project(title="DevLog", slug="devlog", show_in_nav=True)

        statements = []

        def record(conn, cursor, statement, parameters, context, executemany):
            if "from projects" in statement.lower():
                statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", record)
        try:
            client.get("/")
        finally:
            event.remove(db.engine, "before_cursor_execute", record)

        assert len(statements) == 1


class TestTheHomepageDispatcher:
    def test_it_renders_the_blog_by_default(self, app, client, db, sample_post):
        _require_public_shell(app)

        html = client.get("/").get_data(as_text=True)

        assert "Test Post" in html

    def test_it_renders_a_selected_page(self, app, client, db):
        _require_public_shell(app)
        page = _make_page(title="Colophon", slug="colophon")

        row = _settings_row()
        row.homepage_kind = "page"
        row.homepage_target_id = page.id
        db.session.commit()

        html = client.get("/").get_data(as_text=True)

        assert "Colophon" in html
        assert "Colophon body." in html

    def test_it_renders_a_selected_project(self, app, client, db):
        _require_public_shell(app)
        project = _make_project(title="DevLog", slug="devlog")

        row = _settings_row()
        row.homepage_kind = "project"
        row.homepage_target_id = project.id
        db.session.commit()

        html = client.get("/").get_data(as_text=True)

        assert "DevLog" in html

    def test_the_selected_page_keeps_its_own_route_addressable(self, app, client, db):
        _require_public_shell(app)
        page = _make_page(title="Colophon", slug="colophon")

        row = _settings_row()
        row.homepage_kind = "page"
        row.homepage_target_id = page.id
        db.session.commit()

        response = client.get("/page/colophon")

        assert response.status_code == 200
        assert "Colophon" in response.get_data(as_text=True)

    def test_the_root_is_canonical_for_the_selected_target(self, app, client, db):
        _require_public_shell(app)
        page = _make_page(title="Colophon", slug="colophon")

        row = _settings_row()
        row.homepage_kind = "page"
        row.homepage_target_id = page.id
        db.session.commit()

        html = client.get("/page/colophon").get_data(as_text=True)

        assert f'<link rel="canonical" href="{BASE_URL}/page/colophon">' not in html
        assert f'<link rel="canonical" href="{BASE_URL}/">' in html
        assert f'<meta property="og:url" content="{BASE_URL}/">' in html

    def test_the_posts_route_is_canonical_for_the_root_when_the_blog_is_home(self, app, client, db):
        _require_public_shell(app)

        html = client.get("/posts").get_data(as_text=True)

        assert f'<link rel="canonical" href="{BASE_URL}/">' in html

    def test_there_is_only_one_canonical_link(self, app, client, db):
        _require_public_shell(app)
        page = _make_page(title="Colophon", slug="colophon")

        row = _settings_row()
        row.homepage_kind = "page"
        row.homepage_target_id = page.id
        db.session.commit()

        html = client.get("/").get_data(as_text=True)

        assert html.count('rel="canonical"') == 1

    def test_the_posts_link_points_at_the_posts_route_when_the_home_is_another_page(
        self, app, client, db
    ):
        _require_public_shell(app)
        page = _make_page(title="Colophon", slug="colophon")

        row = _settings_row()
        row.homepage_kind = "page"
        row.homepage_target_id = page.id
        db.session.commit()

        nav = _nav_section(client.get("/").get_data(as_text=True))

        assert 'href="/posts"' in nav

    def test_an_invalid_homepage_falls_back_to_the_blog(self, app, client, db, sample_post):
        _require_public_shell(app)

        row = _settings_row()
        row.homepage_kind = "page"
        row.homepage_target_id = 999999
        db.session.commit()

        html = client.get("/").get_data(as_text=True)

        assert "Test Post" in html

    def test_unpublishing_the_selected_page_falls_back_to_the_blog(
        self, app, client, db, sample_post
    ):
        _require_public_shell(app)
        page = _make_page(title="Colophon", slug="colophon")

        row = _settings_row()
        row.homepage_kind = "page"
        row.homepage_target_id = page.id
        db.session.commit()

        page.published = False
        db.session.commit()

        html = client.get("/").get_data(as_text=True)

        assert "Test Post" in html

    def test_the_sitemap_lists_the_root_and_not_the_selected_page(self, app, client, db):
        _require_public_shell(app)
        page = _make_page(title="Colophon", slug="colophon")

        row = _settings_row()
        row.homepage_kind = "page"
        row.homepage_target_id = page.id
        db.session.commit()

        xml = client.get("/sitemap.xml").get_data(as_text=True)

        assert f"<loc>{BASE_URL}/</loc>" in xml
        assert "/page/colophon" not in xml

    def test_the_sitemap_lists_the_published_projects(self, app, client, db):
        _require_public_shell(app)
        _make_project(title="Alpha", slug="alpha")
        _make_project(title="Draft", slug="draft", published=False)

        xml = client.get("/sitemap.xml").get_data(as_text=True)

        assert "/projects/alpha" in xml
        assert "/projects/draft" not in xml

    def test_the_homepage_never_redirects(self, app, client, db):
        _require_public_shell(app)

        response = client.get("/")

        assert response.status_code == 200


class TestTheHomepageSettings:
    def test_it_stores_the_selection(self, authenticated_client, db):
        page = _make_page(title="Colophon", slug="colophon")

        response = authenticated_client.post(
            "/admin/settings/site",
            data={
                "homepage_kind": "page",
                "homepage_target_id": str(page.id),
                "projects_menu_label": "Projects",
            },
        )

        assert response.status_code == 302
        row = _settings_row()
        assert row.homepage_kind == "page"
        assert row.homepage_target_id == page.id

    def test_it_refuses_an_unpublished_target(self, authenticated_client, db):
        page = _make_page(title="Draft", slug="draft", published=False)

        response = authenticated_client.post(
            "/admin/settings/site",
            data={"homepage_kind": "page", "homepage_target_id": str(page.id)},
        )

        assert response.status_code == 302
        row = _settings_row()
        assert row.homepage_kind == "blog"

    def test_it_refuses_a_blank_projects_label(self, authenticated_client, db):
        response = authenticated_client.post(
            "/admin/settings/site",
            data={"homepage_kind": "blog", "projects_menu_label": "   "},
        )

        assert response.status_code == 302
        row = _settings_row()
        assert row.projects_menu_label == "Projects"

    def test_the_picker_only_offers_published_targets(self, authenticated_client, db):
        _make_page(title="Published", slug="published")
        _make_page(title="Draft", slug="draft", published=False)
        _make_project(title="Live", slug="live")
        _make_project(title="Hidden", slug="hidden", published=False)

        html = authenticated_client.get("/admin/settings").get_data(as_text=True)

        target_picker = html.split('id="homepage_target_id"', 1)[1].split("</select>", 1)[0]
        assert "Published" in target_picker
        assert "Draft" not in target_picker
        assert "Live" in target_picker
        assert "Hidden" not in target_picker

    def test_deleting_the_selected_page_returns_the_home_to_the_blog(
        self, authenticated_client, db, sample_post
    ):
        page = _make_page(title="Colophon", slug="colophon")

        row = _settings_row()
        row.homepage_kind = "page"
        row.homepage_target_id = page.id
        db.session.commit()

        authenticated_client.post(f"/admin/pages/delete/{page.id}")

        row = _settings_row()
        assert row.homepage_kind == "blog"
        assert row.homepage_target_id is None

    def test_unpublishing_the_selected_page_returns_the_home_to_the_blog(
        self, authenticated_client, db
    ):
        page = _make_page(title="Colophon", slug="colophon")

        row = _settings_row()
        row.homepage_kind = "page"
        row.homepage_target_id = page.id
        db.session.commit()

        authenticated_client.post(
            f"/admin/pages/edit/{page.id}",
            data={"title": "Colophon", "body": "Colophon body."},
        )

        row = _settings_row()
        assert row.homepage_kind == "blog"

    def test_deleting_the_selected_project_returns_the_home_to_the_blog(
        self, authenticated_client, db
    ):
        project = _make_project(title="DevLog", slug="devlog")

        row = _settings_row()
        row.homepage_kind = "project"
        row.homepage_target_id = project.id
        db.session.commit()

        authenticated_client.post(f"/admin/projects/delete/{project.id}")

        row = _settings_row()
        assert row.homepage_kind == "blog"
        assert row.homepage_target_id is None


class TestTheDisclosureAccessibility:
    def test_the_disclosure_control_is_wired_for_assistive_technology(self, app, client, db):
        _require_public_shell(app)
        _set_projects_menu(enabled=True)
        _make_project(title="Other", slug="other")

        nav = _nav_section(client.get("/").get_data(as_text=True))

        assert 'aria-expanded="false"' in nav
        assert 'aria-controls="nav-projects-menu"' in nav
        assert 'id="nav-projects-menu"' in nav

    def test_the_disclosure_control_has_a_name(self, app, client, db):
        _require_public_shell(app)
        _set_projects_menu(enabled=True)
        _make_project(title="Other", slug="other")

        nav = _nav_section(client.get("/").get_data(as_text=True))

        assert 'aria-label="Show all Projects"' in nav

    def test_the_projects_link_survives_without_javascript(self, app, client, db):
        _require_public_shell(app)
        _set_projects_menu(enabled=True)
        _make_project(title="Other", slug="other")

        nav = _nav_section(client.get("/").get_data(as_text=True))

        assert 'href="/projects"' in nav

    def test_the_dropdown_module_is_loaded_on_public_routes(self):
        from pathlib import Path

        source = Path("app/static/js/main.js").read_text(encoding="utf-8")
        public_block = source.split("const PUBLIC_MODULES = [", 1)[1].split("]", 1)[0]

        assert "./shared/nav-dropdown.js" in public_block
