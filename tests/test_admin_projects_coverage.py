"""Coverage tests for the admin project routes.

Every test drives the real route handlers in ``app/routes/admin/projects.py``.
The boundaries that would otherwise reach the filesystem, the theme registry
or the database are stubbed, but the route logic itself — validation, slug
handling, media resolution and the audit trail — is exercised for real.
"""

from __future__ import annotations

import inspect
import io
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from app.models import AdminAuditLog, Project, SiteSettings


def _make_project(db, **kwargs) -> Project:
    values = {
        "title": "DevLog",
        "slug": "devlog",
        "summary": "A blog engine",
        "body": "Hello",
        "published": False,
    }
    values.update(kwargs)
    project = Project(**values)
    db.session.add(project)
    db.session.commit()
    return project


class _FakeStorage:
    """A storage backend that reports a fixed list of media keys."""

    def __init__(self, names=(), error=None) -> None:
        self._names = list(names)
        self._error = error

    def list_file_info(self):
        if self._error is not None:
            raise self._error
        return [SimpleNamespace(name=name) for name in self._names]


def _storage_with(monkeypatch, names=(), error=None) -> None:
    monkeypatch.setattr(
        "app.routes.admin.projects.get_storage",
        lambda: _FakeStorage(names=names, error=error),
    )


def _integrity_error() -> IntegrityError:
    return IntegrityError("INSERT", {}, Exception("duplicate key"))


def _operational_error() -> OperationalError:
    return OperationalError("SELECT", {}, Exception("database is locked"))


PROJECTS_MODULE = "app.routes.admin.projects"


def _called_from_projects() -> bool:
    """Report whether the caller is the admin project route module."""
    caller = inspect.currentframe().f_back.f_back
    return caller.f_globals.get("__name__") == PROJECTS_MODULE


def _fail_session_call(monkeypatch, db, method, error_factory, failures=1):
    """Fail a session method only when the project routes call it.

    The application refreshes the admin session row in a ``before_request``
    hook, so an unconditional patch would be consumed before the route under
    test ever runs. Returns the list of the failed calls.
    """
    original = getattr(db.session, method)
    calls = []

    def replacement(*args, **kwargs):
        if _called_from_projects():
            calls.append(1)
            if len(calls) <= failures:
                raise error_factory()
        return original(*args, **kwargs)

    monkeypatch.setattr(db.session, method, replacement)
    return calls


class TestThemeChoices:
    def test_it_lists_the_registry_themes(self):
        from app.routes.admin.projects import _theme_choices

        themes = _theme_choices()

        assert isinstance(themes, list)

    def test_it_returns_an_empty_list_when_the_service_fails(self, monkeypatch):
        def boom():
            raise RuntimeError("no theme service")

        monkeypatch.setattr("app.routes.admin.projects.get_theme_service", boom)

        from app.routes.admin.projects import _theme_choices

        assert _theme_choices() == []


class TestExistingMediaKeys:
    def test_it_lists_the_stored_keys(self, monkeypatch):
        _storage_with(monkeypatch, names=["hero.png", "shot.png"])

        from app.routes.admin.projects import _existing_media_keys

        assert _existing_media_keys() == ["hero.png", "shot.png"]

    def test_it_returns_an_empty_list_when_the_storage_fails(self, monkeypatch):
        def boom():
            raise RuntimeError("no storage")

        monkeypatch.setattr("app.routes.admin.projects.get_storage", boom)

        from app.routes.admin.projects import _existing_media_keys

        assert _existing_media_keys() == []

    def test_it_returns_an_empty_list_when_the_listing_fails(self, monkeypatch):
        _storage_with(monkeypatch, error=OSError("cannot list"))

        from app.routes.admin.projects import _existing_media_keys

        assert _existing_media_keys() == []


class TestResolveMediaKeys:
    def test_it_keeps_only_the_stored_keys(self):
        from app.routes.admin.projects import _resolve_media_keys

        resolved = _resolve_media_keys(["a.png", "b.png", "c.png"], ["b.png", "c.png", "d.png"])

        assert resolved == ["b.png", "c.png"]


class TestProjectList:
    def test_it_requires_authentication(self, client):
        response = client.get("/admin/projects")

        assert response.status_code in (302, 401, 403)

    def test_it_lists_every_project(self, authenticated_client, db):
        _make_project(db, title="Listed", slug="listed")

        response = authenticated_client.get("/admin/projects")

        assert response.status_code == 200
        assert "Listed" in response.get_data(as_text=True)


class TestNewProject:
    def test_it_renders_the_editor(self, authenticated_client):
        response = authenticated_client.get("/admin/projects/new")

        assert response.status_code == 200
        assert "New Project" in response.get_data(as_text=True)

    def test_it_creates_a_project(self, authenticated_client, db):
        response = authenticated_client.post(
            "/admin/projects/new",
            data={"title": "DevLog", "summary": "A blog engine", "body": "Hello"},
        )

        assert response.status_code == 302
        project = db.session.execute(db.select(Project).filter_by(slug="devlog")).scalar_one()
        assert project.title == "DevLog"
        assert project.published is False

    def test_it_records_the_creation_in_the_audit_log(self, authenticated_client, db):
        authenticated_client.post(
            "/admin/projects/new",
            data={"title": "Audited", "body": "Hello"},
        )

        entry = db.session.execute(db.select(AdminAuditLog)).scalar_one()
        assert entry.action == "project.create"
        assert entry.target_type == "project"
        assert "Audited" in entry.details

    def test_it_retries_when_the_slug_collides(self, authenticated_client, db, monkeypatch):
        calls = _fail_session_call(monkeypatch, db, "flush", _integrity_error, failures=1)

        response = authenticated_client.post(
            "/admin/projects/new",
            data={"title": "Colliding", "slug": "colliding", "body": "Hello"},
        )

        assert response.status_code == 302
        assert len(calls) == 2
        project = db.session.execute(db.select(Project)).scalar_one()
        assert project.title == "Colliding"

    def test_it_gives_up_after_the_retry_budget(self, authenticated_client, db, monkeypatch):
        calls = _fail_session_call(monkeypatch, db, "flush", _integrity_error, failures=1000)

        with pytest.raises(IntegrityError):
            authenticated_client.post(
                "/admin/projects/new",
                data={"title": "Doomed", "slug": "doomed", "body": "Hello"},
            )

        assert len(calls) == 100

    def test_it_reports_a_database_error(self, authenticated_client, db, monkeypatch):
        calls = _fail_session_call(monkeypatch, db, "flush", _operational_error, failures=1000)

        response = authenticated_client.post(
            "/admin/projects/new",
            data={"title": "Broken", "body": "Hello"},
        )

        assert response.status_code == 302
        assert len(calls) == 1
        assert "/admin/projects" in response.headers["Location"]
        assert db.session.execute(db.select(Project)).scalars().all() == []

    def test_it_rejects_a_form_without_a_title(self, authenticated_client, db):
        response = authenticated_client.post(
            "/admin/projects/new",
            data={"title": "", "body": "Hello"},
        )

        assert response.status_code == 400
        assert "The title is required." in response.get_data(as_text=True)


class TestEditProject:
    def test_it_404s_for_a_missing_project(self, authenticated_client):
        response = authenticated_client.get("/admin/projects/edit/999999")

        assert response.status_code == 404

    def test_it_renders_the_editor_with_the_project(self, authenticated_client, db):
        project = _make_project(db)

        response = authenticated_client.get(f"/admin/projects/edit/{project.id}")

        assert response.status_code == 200
        assert "DevLog" in response.get_data(as_text=True)

    def test_it_renders_the_errors_of_an_invalid_form(self, authenticated_client, db):
        project = _make_project(db)

        response = authenticated_client.post(
            f"/admin/projects/edit/{project.id}",
            data={"title": "", "body": "Hello"},
        )

        assert response.status_code == 400
        assert "The title is required." in response.get_data(as_text=True)

    def test_it_changes_the_slug_when_one_is_submitted(self, authenticated_client, db):
        project = _make_project(db, title="DevLog", slug="devlog")

        response = authenticated_client.post(
            f"/admin/projects/edit/{project.id}",
            data={"title": "DevLog", "slug": "renamed", "body": "Hello"},
        )

        assert response.status_code == 302
        assert db.session.get(Project, project.id).slug == "renamed"

    def test_a_title_change_without_a_slug_regenerates_the_slug(self, authenticated_client, db):
        project = _make_project(db, title="DevLog", slug="devlog")

        response = authenticated_client.post(
            f"/admin/projects/edit/{project.id}",
            data={"title": "Fresh Name", "body": "Hello"},
        )

        assert response.status_code == 302
        updated = db.session.get(Project, project.id)
        assert updated.title == "Fresh Name"
        assert updated.slug == "fresh-name"

    def test_an_unchanged_title_without_a_slug_keeps_the_slug(self, authenticated_client, db):
        project = _make_project(db, title="DevLog", slug="devlog")

        response = authenticated_client.post(
            f"/admin/projects/edit/{project.id}",
            data={"title": "DevLog", "body": "Hello"},
        )

        assert response.status_code == 302
        updated = db.session.get(Project, project.id)
        assert updated.slug == "devlog"

    def test_it_recovers_from_a_unique_violation(self, authenticated_client, db, monkeypatch):
        project = _make_project(db)
        calls = _fail_session_call(monkeypatch, db, "commit", _integrity_error, failures=1)

        response = authenticated_client.post(
            f"/admin/projects/edit/{project.id}",
            data={"title": "Recovered", "body": "Hello"},
        )

        assert response.status_code == 302
        # The route commits the update, the recovered update and the audit row.
        assert len(calls) == 3
        assert db.session.get(Project, project.id).title == "Recovered"

    def test_it_reports_a_missing_project_after_a_unique_violation(
        self, authenticated_client, db, monkeypatch
    ):
        project = _make_project(db)
        _fail_session_call(monkeypatch, db, "commit", _integrity_error, failures=1)

        original_get = db.session.get
        get_calls = []

        def get(model, ident):
            if _called_from_projects():
                get_calls.append(ident)
                if len(get_calls) == 2:
                    return None
            return original_get(model, ident)

        monkeypatch.setattr(db.session, "get", get)

        response = authenticated_client.post(
            f"/admin/projects/edit/{project.id}",
            data={"title": "Recovered", "body": "Hello"},
        )

        assert response.status_code == 302
        assert "/admin/projects" in response.headers["Location"]

    def test_it_reports_a_database_error(self, authenticated_client, db, monkeypatch):
        project = _make_project(db)
        calls = _fail_session_call(monkeypatch, db, "commit", _operational_error, failures=1000)

        response = authenticated_client.post(
            f"/admin/projects/edit/{project.id}",
            data={"title": "Broken", "body": "Hello"},
        )

        assert response.status_code == 302
        assert len(calls) == 1
        assert "/admin/projects" in response.headers["Location"]


class TestPreviewProject:
    def test_it_404s_for_a_missing_project(self, authenticated_client):
        response = authenticated_client.get("/admin/projects/preview/999999")

        assert response.status_code == 404

    def test_it_renders_a_published_project(self, authenticated_client, db):
        project = _make_project(db, published=True)

        response = authenticated_client.get(f"/admin/projects/preview/{project.id}")

        assert response.status_code == 200
        assert "DevLog" in response.get_data(as_text=True)


class TestDeleteProject:
    def test_it_404s_for_a_missing_project(self, authenticated_client):
        response = authenticated_client.post("/admin/projects/delete/999999")

        assert response.status_code == 404

    def test_it_deletes_the_project(self, authenticated_client, db):
        project = _make_project(db)

        response = authenticated_client.post(f"/admin/projects/delete/{project.id}")

        assert response.status_code == 302
        assert db.session.get(Project, project.id) is None

    def test_it_records_the_deletion_in_the_audit_log(self, authenticated_client, db):
        project = _make_project(db)

        authenticated_client.post(f"/admin/projects/delete/{project.id}")

        entry = db.session.execute(db.select(AdminAuditLog)).scalar_one()
        assert entry.action == "project.delete"
        assert entry.target_id == project.id

    def test_it_reports_a_database_error(self, authenticated_client, db, monkeypatch):
        project = _make_project(db)
        calls = _fail_session_call(monkeypatch, db, "commit", _integrity_error, failures=1000)

        response = authenticated_client.post(f"/admin/projects/delete/{project.id}")

        assert len(calls) == 1

        assert response.status_code == 302
        assert "/admin/projects" in response.headers["Location"]
        assert db.session.get(Project, project.id) is not None


class TestSetProjectPublished:
    def test_it_404s_for_a_missing_project(self, authenticated_client):
        response = authenticated_client.post("/admin/projects/999999/publish")

        assert response.status_code == 404

    def test_it_publishes_the_project(self, authenticated_client, db):
        project = _make_project(db, published=False)

        response = authenticated_client.post(
            f"/admin/projects/{project.id}/publish", data={"published": "on"}
        )

        assert response.status_code == 302
        assert db.session.get(Project, project.id).published is True

    def test_it_records_the_publication_in_the_audit_log(self, authenticated_client, db):
        project = _make_project(db, published=False)

        authenticated_client.post(f"/admin/projects/{project.id}/publish", data={"published": "on"})

        entry = db.session.execute(db.select(AdminAuditLog)).scalar_one()
        assert entry.action == "project.publish"

    def test_it_unpublishes_the_project(self, authenticated_client, db):
        project = _make_project(db, published=True)

        response = authenticated_client.post(f"/admin/projects/{project.id}/publish")

        assert response.status_code == 302
        assert db.session.get(Project, project.id).published is False

    def test_it_records_the_unpublication_in_the_audit_log(self, authenticated_client, db):
        project = _make_project(db, published=True)

        authenticated_client.post(f"/admin/projects/{project.id}/publish")

        entry = db.session.execute(db.select(AdminAuditLog)).scalar_one()
        assert entry.action == "project.unpublish"

    def test_it_resets_the_homepage_when_the_project_is_unpublished(self, authenticated_client, db):
        project = _make_project(db, published=True)
        settings = SiteSettings.get_instance()
        settings.homepage_kind = "project"
        settings.homepage_target_id = project.id
        db.session.commit()

        authenticated_client.post(f"/admin/projects/{project.id}/publish")

        db.session.expire_all()
        refreshed = db.session.execute(db.select(SiteSettings)).scalar_one()
        assert refreshed.homepage_kind == "blog"
        assert refreshed.homepage_target_id is None

    def test_it_reports_a_database_error(self, authenticated_client, db, monkeypatch):
        project = _make_project(db, published=False)
        calls = _fail_session_call(monkeypatch, db, "commit", _operational_error, failures=1000)

        response = authenticated_client.post(
            f"/admin/projects/{project.id}/publish", data={"published": "on"}
        )

        assert len(calls) == 1

        assert response.status_code == 302
        assert "/admin/projects" in response.headers["Location"]


class TestProjectMedia:
    def _form(self, **extra):
        data = {"title": "Media", "body": "Hello"}
        data.update(extra)
        return data

    def test_it_stores_the_hero_upload(self, authenticated_client, db, monkeypatch):
        monkeypatch.setattr(
            "app.routes.admin.projects._save_image", lambda upload: ("hero.png", None)
        )
        _storage_with(monkeypatch)

        response = authenticated_client.post(
            "/admin/projects/new",
            data=self._form(hero_image_file=(io.BytesIO(b"png"), "hero.png")),
            content_type="multipart/form-data",
        )

        assert response.status_code == 302
        project = db.session.execute(db.select(Project)).scalar_one()
        assert project.hero_image == "hero.png"

    def test_it_reports_a_failed_hero_upload(self, authenticated_client, db, monkeypatch):
        monkeypatch.setattr(
            "app.routes.admin.projects._save_image",
            lambda upload: (None, "Uploaded file is not a valid image."),
        )
        _storage_with(monkeypatch)

        response = authenticated_client.post(
            "/admin/projects/new",
            data=self._form(hero_image_file=(io.BytesIO(b"png"), "hero.png")),
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        assert "Uploaded file is not a valid image." in response.get_data(as_text=True)

    def test_it_drops_an_upload_that_stores_nothing(self, authenticated_client, db, monkeypatch):
        monkeypatch.setattr("app.routes.admin.projects._save_image", lambda upload: (None, None))
        _storage_with(monkeypatch)

        response = authenticated_client.post(
            "/admin/projects/new",
            data=self._form(hero_image_file=(io.BytesIO(b"png"), "hero.png")),
            content_type="multipart/form-data",
        )

        assert response.status_code == 302
        project = db.session.execute(db.select(Project)).scalar_one()
        assert project.hero_image is None

    def test_it_keeps_a_hero_key_the_site_holds(self, authenticated_client, db, monkeypatch):
        _storage_with(monkeypatch, names=["hero.png"])

        response = authenticated_client.post(
            "/admin/projects/new", data=self._form(hero_image="hero.png")
        )

        assert response.status_code == 302
        project = db.session.execute(db.select(Project)).scalar_one()
        assert project.hero_image == "hero.png"

    def test_it_rejects_a_hero_key_the_site_does_not_hold(
        self, authenticated_client, db, monkeypatch
    ):
        _storage_with(monkeypatch, names=["other.png"])

        response = authenticated_client.post(
            "/admin/projects/new", data=self._form(hero_image="missing.png")
        )

        assert response.status_code == 400
        assert "The hero image is not a file this site holds." in response.get_data(as_text=True)

    def test_it_stores_the_screenshot_uploads(self, authenticated_client, db, monkeypatch):
        monkeypatch.setattr(
            "app.routes.admin.projects._save_image", lambda upload: ("shot.png", None)
        )
        _storage_with(monkeypatch)

        response = authenticated_client.post(
            "/admin/projects/new",
            data=self._form(
                screenshots_file=[
                    (io.BytesIO(b"one"), "one.png"),
                    (io.BytesIO(b"two"), "two.png"),
                ]
            ),
            content_type="multipart/form-data",
        )

        assert response.status_code == 302
        project = db.session.execute(db.select(Project)).scalar_one()
        assert list(project.screenshots) == ["shot.png", "shot.png"]

    def test_it_reports_a_failed_screenshot_upload(self, authenticated_client, db, monkeypatch):
        monkeypatch.setattr(
            "app.routes.admin.projects._save_image",
            lambda upload: (None, "File too large. Maximum size is 5MB."),
        )
        _storage_with(monkeypatch)

        response = authenticated_client.post(
            "/admin/projects/new",
            data=self._form(screenshots_file=(io.BytesIO(b"one"), "one.png")),
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        assert "File too large. Maximum size is 5MB." in response.get_data(as_text=True)

    def test_it_skips_a_screenshot_without_a_filename(self, authenticated_client, db, monkeypatch):
        monkeypatch.setattr(
            "app.routes.admin.projects._save_image", lambda upload: ("shot.png", None)
        )
        _storage_with(monkeypatch)

        response = authenticated_client.post(
            "/admin/projects/new",
            data=self._form(screenshots_file=(io.BytesIO(b""), "")),
            content_type="multipart/form-data",
        )

        assert response.status_code == 302
        project = db.session.execute(db.select(Project)).scalar_one()
        assert list(project.screenshots) == []

    def test_it_drops_a_screenshot_upload_that_stores_nothing(
        self, authenticated_client, db, monkeypatch
    ):
        monkeypatch.setattr("app.routes.admin.projects._save_image", lambda upload: (None, None))
        _storage_with(monkeypatch)

        response = authenticated_client.post(
            "/admin/projects/new",
            data=self._form(screenshots_file=(io.BytesIO(b"one"), "one.png")),
            content_type="multipart/form-data",
        )

        assert response.status_code == 302
        project = db.session.execute(db.select(Project)).scalar_one()
        assert list(project.screenshots) == []

    def test_it_keeps_the_screenshot_keys_the_site_holds(
        self, authenticated_client, db, monkeypatch
    ):
        _storage_with(monkeypatch, names=["one.png", "two.png"])

        response = authenticated_client.post(
            "/admin/projects/new", data=self._form(screenshots="one.png\ntwo.png")
        )

        assert response.status_code == 302
        project = db.session.execute(db.select(Project)).scalar_one()
        assert list(project.screenshots) == ["one.png", "two.png"]

    def test_it_rejects_a_screenshot_key_the_site_does_not_hold(
        self, authenticated_client, db, monkeypatch
    ):
        _storage_with(monkeypatch, names=["one.png"])

        response = authenticated_client.post(
            "/admin/projects/new", data=self._form(screenshots="one.png\nmissing.png")
        )

        assert response.status_code == 400
        assert "One or more screenshots are not files this site holds." in response.get_data(
            as_text=True
        )

    def test_it_rejects_more_screenshots_than_the_limit(
        self, authenticated_client, db, monkeypatch
    ):
        monkeypatch.setattr(
            "app.routes.admin.projects._apply_uploads",
            lambda files: ({"screenshots": [f"shot-{index}.png" for index in range(7)]}, []),
        )
        _storage_with(monkeypatch)

        response = authenticated_client.post(
            "/admin/projects/new", data=self._form(hero_image="hero.png")
        )

        assert response.status_code == 400
        assert "A project can carry at most 6 screenshots." in response.get_data(as_text=True)
