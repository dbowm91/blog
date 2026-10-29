"""Coverage tests for the admin project documentation routes."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"

from io import BytesIO  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.extensions import db  # noqa: E402
from app.models import Project, ProjectDocument, ProjectDocumentAsset  # noqa: E402
from app.services.project_docs_sync import ProjectDocsSyncError  # noqa: E402

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00"
    b"\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture()
def project(db):
    record = Project(
        title="Docs project",
        slug="docs-project",
        body="",
        summary="",
        published=True,
    )
    db.session.add(record)
    db.session.commit()
    return record


@pytest.fixture()
def document(db, project):
    record = ProjectDocument(
        project_id=project.id,
        version_key="current",
        path="guide/start.md",
        title="Start",
        body="# Start",
        published=True,
    )
    db.session.add(record)
    db.session.commit()
    return record


class TestDocumentLookup:
    def test_an_unknown_project_is_not_found(self, authenticated_client, db):
        response = authenticated_client.get("/admin/projects/999999/docs")

        assert response.status_code == 404

    def test_an_unknown_document_is_not_found(self, authenticated_client, project):
        response = authenticated_client.get(f"/admin/projects/{project.id}/docs/999999/edit")

        assert response.status_code == 404

    def test_the_documentation_list_is_rendered(self, authenticated_client, db, project, document):
        response = authenticated_client.get(f"/admin/projects/{project.id}/docs")

        assert response.status_code == 200
        assert b"guide/start.md" in response.data


class TestDocumentValidation:
    def test_the_path_must_be_a_safe_markdown_path(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/new",
            data={"path": "../escape.md", "title": "Escape", "body": "b"},
        )

        assert response.status_code == 400
        assert b"Enter a safe Markdown path ending in .md or .markdown." in response.data

    def test_the_path_must_not_collide_with_another_document(
        self, authenticated_client, db, project, document
    ):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/new",
            data={"path": "guide/START.md", "title": "Start", "body": "b"},
        )

        assert response.status_code == 400
        assert (
            b"A document already uses this path, including a case-insensitive match."
            in response.data
        )

    def test_a_title_is_required(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/new",
            data={"path": "guide/other.md", "body": "b"},
        )

        assert response.status_code == 400
        assert b"A document title is required and must be 200 characters or fewer." in response.data

    def test_the_title_must_not_be_too_long(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/new",
            data={"path": "guide/other.md", "title": "t" * 201, "body": "b"},
        )

        assert response.status_code == 400
        assert b"A document title is required and must be 200 characters or fewer." in response.data

    def test_the_body_must_not_be_too_long(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/new",
            data={"path": "guide/other.md", "title": "Other", "body": "b" * 100001},
        )

        assert response.status_code == 400
        assert b"Document Markdown must be 100,000 characters or fewer." in response.data

    def test_the_navigation_title_must_not_be_too_long(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/new",
            data={
                "path": "guide/other.md",
                "title": "Other",
                "body": "b",
                "nav_title": "n" * 121,
            },
        )

        assert response.status_code == 400
        assert b"Navigation titles must be 120 characters or fewer." in response.data

    def test_the_navigation_order_must_be_a_whole_number(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/new",
            data={
                "path": "guide/other.md",
                "title": "Other",
                "body": "b",
                "nav_order": "first",
            },
        )

        assert response.status_code == 400
        assert b"Navigation order must be a whole number." in response.data

    def test_the_navigation_order_must_be_in_range(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/new",
            data={
                "path": "guide/other.md",
                "title": "Other",
                "body": "b",
                "nav_order": "100001",
            },
        )

        assert response.status_code == 400
        assert b"Navigation order must be between -100000 and 100000." in response.data

    def test_a_conflicting_path_is_reported(self, authenticated_client, db, project):
        with patch.object(
            db.session,
            "commit",
            side_effect=IntegrityError("INSERT", {}, Exception("duplicate")),
        ):
            response = authenticated_client.post(
                f"/admin/projects/{project.id}/docs/new",
                data={"path": "guide/other.md", "title": "Other", "body": "b"},
            )

        assert response.status_code == 400
        assert b"A document with that path already exists." in response.data


class TestDocumentEditing:
    def test_a_document_is_created(self, authenticated_client, db, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/new",
            data={
                "path": "guide/other.md",
                "title": "Other",
                "body": "# Other",
                "nav_order": "10",
                "published": "1",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Project document created." in response.data
        stored = db.session.execute(select(ProjectDocument)).scalar_one()
        assert stored.published is True
        assert stored.nav_order == 10

    def test_a_document_is_edited(self, authenticated_client, db, project, document):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/{document.id}/edit",
            data={"path": "guide/start.md", "title": "Renamed", "body": "# Start"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Project document saved." in response.data
        assert db.session.get(ProjectDocument, document.id).title == "Renamed"

    def test_an_invalid_edit_is_reported(self, authenticated_client, project, document):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/{document.id}/edit",
            data={"path": "guide/start.md", "title": "", "body": "b"},
        )

        assert response.status_code == 400
        assert b"A document title is required" in response.data

    def test_the_editor_is_rendered(self, authenticated_client, project, document):
        response = authenticated_client.get(f"/admin/projects/{project.id}/docs/{document.id}/edit")

        assert response.status_code == 200
        assert b"guide/start.md" in response.data

    def test_the_new_document_editor_is_rendered(self, authenticated_client, project):
        response = authenticated_client.get(f"/admin/projects/{project.id}/docs/new")

        assert response.status_code == 200
        assert b"Document path" in response.data

    def test_a_document_is_deleted(self, authenticated_client, db, project, document):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/{document.id}/delete",
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Project document deleted." in response.data
        assert db.session.get(ProjectDocument, document.id) is None


class TestDocumentOrdering:
    def test_a_document_is_moved_down(self, authenticated_client, db, project):
        first = ProjectDocument(
            project_id=project.id,
            version_key="current",
            path="a.md",
            title="A",
            body="b",
            nav_order=0,
        )
        second = ProjectDocument(
            project_id=project.id,
            version_key="current",
            path="b.md",
            title="B",
            body="b",
            nav_order=10,
        )
        db.session.add_all([first, second])
        db.session.commit()

        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/{first.id}/move",
            data={"direction": "down"},
        )

        assert response.status_code == 302
        db.session.refresh(first)
        db.session.refresh(second)
        assert first.nav_order == 10
        assert second.nav_order == 0

    def test_a_document_is_moved_up(self, authenticated_client, db, project):
        first = ProjectDocument(
            project_id=project.id,
            version_key="current",
            path="a.md",
            title="A",
            body="b",
            nav_order=0,
        )
        second = ProjectDocument(
            project_id=project.id,
            version_key="current",
            path="b.md",
            title="B",
            body="b",
            nav_order=10,
        )
        db.session.add_all([first, second])
        db.session.commit()

        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/{second.id}/move",
            data={"direction": "up"},
        )

        assert response.status_code == 302
        db.session.refresh(first)
        db.session.refresh(second)
        assert first.nav_order == 10
        assert second.nav_order == 0

    def test_the_first_document_cannot_move_up(self, authenticated_client, db, project, document):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/{document.id}/move",
            data={"direction": "up"},
        )

        assert response.status_code == 302
        assert db.session.get(ProjectDocument, document.id).nav_order == 0

    def test_an_unknown_direction_is_rejected(self, authenticated_client, project, document):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/{document.id}/move",
            data={"direction": "sideways"},
        )

        assert response.status_code == 400


class TestDocumentationSettings:
    def test_the_settings_are_saved(self, authenticated_client, db, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/settings",
            data={
                "docs_enabled": "1",
                "docs_source_kind": "github",
                "github_owner": "example",
                "github_repository": "sample",
                "github_docs_root": "docs",
                "github_docs_ref": "main",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Documentation settings saved." in response.data
        stored = db.session.get(Project, project.id)
        assert stored.docs_enabled is True
        assert stored.docs_source_kind == "github"
        assert stored.github_owner == "example"
        assert stored.github_repository == "sample"
        assert stored.github_docs_ref == "main"
        assert stored.github_docs_root == "docs"

    def test_a_local_source_needs_no_repository(self, authenticated_client, db, project, document):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/settings",
            data={"docs_source_kind": "local", "docs_home_path": "guide/start.md"},
            follow_redirects=True,
        )

        assert b"Documentation settings saved." in response.data
        stored = db.session.get(Project, project.id)
        assert stored.docs_source_kind == "local"
        assert stored.docs_home_path == "guide/start.md"
        assert stored.github_owner is None
        assert stored.github_repository is None

    def test_the_home_path_must_be_valid(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/settings",
            data={"docs_home_path": "../escape.md"},
            follow_redirects=True,
        )

        assert b"The documentation home must be a valid Markdown path." in response.data

    def test_the_home_path_must_name_a_published_document(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/settings",
            data={"docs_home_path": "missing.md"},
            follow_redirects=True,
        )

        assert b"The documentation home must identify a published document." in response.data

    def test_the_home_path_must_not_name_a_draft(self, authenticated_client, db, project):
        db.session.add(
            ProjectDocument(
                project_id=project.id,
                version_key="current",
                path="draft.md",
                title="Draft",
                body="b",
                published=False,
            )
        )
        db.session.commit()

        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/settings",
            data={"docs_home_path": "draft.md"},
            follow_redirects=True,
        )

        assert b"The documentation home must identify a published document." in response.data

    def test_the_source_kind_must_be_known(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/settings",
            data={"docs_source_kind": "ftp"},
            follow_redirects=True,
        )

        assert b"Choose a valid documentation source." in response.data

    def test_a_github_source_needs_a_repository(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/settings",
            data={"docs_source_kind": "github"},
            follow_redirects=True,
        )

        assert b"A public GitHub owner and repository are required." in response.data

    def test_the_github_identity_must_be_valid(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/settings",
            data={
                "docs_source_kind": "github",
                "github_owner": "not valid!",
                "github_repository": "sample",
            },
            follow_redirects=True,
        )

        assert b"GitHub repository identity is invalid" in response.data

    def test_the_github_ref_must_be_valid(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/settings",
            data={
                "docs_source_kind": "github",
                "github_owner": "example",
                "github_repository": "sample",
                "github_docs_ref": "r" * 257,
            },
            follow_redirects=True,
        )

        assert b"The GitHub ref is invalid." in response.data

    def test_the_documentation_root_must_be_valid(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/settings",
            data={
                "docs_source_kind": "github",
                "github_owner": "example",
                "github_repository": "sample",
                "github_docs_root": "../escape",
            },
            follow_redirects=True,
        )

        assert b"Documentation root is invalid" in response.data


class TestDocumentationSync:
    def test_a_failed_sync_is_reported(self, authenticated_client, project):
        with patch(
            "app.routes.admin.project_docs.sync_project_docs",
            side_effect=ProjectDocsSyncError("boom"),
        ):
            response = authenticated_client.post(
                f"/admin/projects/{project.id}/docs/sync",
                follow_redirects=True,
            )

        assert b"Documentation sync failed: boom" in response.data

    def test_a_successful_sync_is_reported(self, authenticated_client, project):
        snapshot = SimpleNamespace(commit_sha="a" * 40, file_count=3)
        with patch(
            "app.routes.admin.project_docs.sync_project_docs",
            return_value=snapshot,
        ):
            response = authenticated_client.post(
                f"/admin/projects/{project.id}/docs/sync",
                follow_redirects=True,
            )

        assert b"Documentation snapshot aaaaaaaaaaaa is active (3 files)." in response.data

    def test_the_release_settings_are_saved(self, authenticated_client, db, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/releases/settings",
            data={"releases_enabled": "1", "include_prereleases": "1"},
            follow_redirects=True,
        )

        assert b"Release catalog settings saved." in response.data
        stored = db.session.get(Project, project.id)
        assert stored.releases_enabled is True
        assert stored.releases_include_prereleases is True

    def test_a_failed_release_sync_is_reported(self, authenticated_client, project):
        with patch(
            "app.routes.admin.project_docs.sync_project_releases",
            side_effect=ProjectDocsSyncError("boom"),
        ):
            response = authenticated_client.post(
                f"/admin/projects/{project.id}/releases/sync",
                follow_redirects=True,
            )

        assert b"Release metadata sync failed: boom" in response.data

    def test_a_successful_release_sync_is_reported(self, authenticated_client, project):
        with patch(
            "app.routes.admin.project_docs.sync_project_releases",
            return_value=[],
        ):
            response = authenticated_client.post(
                f"/admin/projects/{project.id}/releases/sync",
                follow_redirects=True,
            )

        assert b"Cached 0 published releases." in response.data


class TestDocumentAssets:
    def test_the_asset_path_must_be_valid(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/assets",
            data={"path": "../escape.png", "asset": (BytesIO(PNG_BYTES), "diagram.png")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        assert b"Enter a safe image path ending in PNG, JPG, GIF, or WebP." in response.data

    def test_an_image_is_required(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/assets",
            data={"path": "images/diagram.png"},
            follow_redirects=True,
        )

        assert b"Choose an image to upload." in response.data

    def test_an_empty_image_is_rejected(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/assets",
            data={"path": "images/diagram.png", "asset": (BytesIO(b""), "diagram.png")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        assert b"Images must be between 1 byte and" in response.data

    def test_an_oversized_image_is_rejected(self, authenticated_client, project):
        with patch("app.routes.admin.project_docs.MAX_DOCUMENT_ASSET_BYTES", 8):
            response = authenticated_client.post(
                f"/admin/projects/{project.id}/docs/assets",
                data={"path": "images/diagram.png", "asset": (BytesIO(PNG_BYTES), "diagram.png")},
                content_type="multipart/form-data",
                follow_redirects=True,
            )

        assert b"Images must be between 1 byte and" in response.data

    def test_a_file_that_is_not_an_image_is_rejected(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/assets",
            data={"path": "images/diagram.png", "asset": (BytesIO(b"not an image"), "diagram.png")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        assert b"Uploaded file is not a valid image." in response.data

    def test_the_stored_image_must_pass_the_size_check(self, authenticated_client, project):
        storage = MagicMock()
        storage.load.return_value = None

        with patch("app.routes.admin.project_docs.get_storage", return_value=storage):
            response = authenticated_client.post(
                f"/admin/projects/{project.id}/docs/assets",
                data={"path": "images/diagram.png", "asset": (BytesIO(PNG_BYTES), "diagram.png")},
                content_type="multipart/form-data",
                follow_redirects=True,
            )

        assert b"The stored image did not pass the size check." in response.data
        storage.delete.assert_called_once()

    def test_only_image_types_are_stored(self, authenticated_client, project):
        storage = MagicMock()
        storage.load.return_value = PNG_BYTES

        with patch("app.routes.admin.project_docs._save_image", return_value=("notes.txt", None)):
            with patch("app.routes.admin.project_docs.get_storage", return_value=storage):
                response = authenticated_client.post(
                    f"/admin/projects/{project.id}/docs/assets",
                    data={
                        "path": "images/diagram.png",
                        "asset": (BytesIO(PNG_BYTES), "diagram.png"),
                    },
                    content_type="multipart/form-data",
                    follow_redirects=True,
                )

        assert b"Only PNG, JPG, GIF, and WebP images are supported." in response.data
        storage.delete.assert_called_once()

    def test_an_image_is_uploaded(self, authenticated_client, db, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/assets",
            data={"path": "images/diagram.png", "asset": (BytesIO(PNG_BYTES), "diagram.png")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        assert b"Documentation image uploaded." in response.data
        asset = db.session.execute(select(ProjectDocumentAsset)).scalar_one()
        assert asset.path == "images/diagram.png"
        assert asset.content_type == "image/png"
        assert asset.file_size == len(PNG_BYTES)

    def test_an_uploaded_image_replaces_the_previous_one(self, authenticated_client, db, project):
        storage = MagicMock()
        storage.load.return_value = PNG_BYTES

        with patch("app.routes.admin.project_docs.get_storage", return_value=storage):
            first = authenticated_client.post(
                f"/admin/projects/{project.id}/docs/assets",
                data={"path": "images/diagram.png", "asset": (BytesIO(PNG_BYTES), "diagram.png")},
                content_type="multipart/form-data",
            )
            assert first.status_code == 302
            first_key = db.session.execute(select(ProjectDocumentAsset)).scalar_one().storage_key

            second = authenticated_client.post(
                f"/admin/projects/{project.id}/docs/assets",
                data={"path": "images/diagram.png", "asset": (BytesIO(PNG_BYTES), "diagram.png")},
                content_type="multipart/form-data",
            )
            assert second.status_code == 302

        assets = db.session.execute(select(ProjectDocumentAsset)).scalars().all()
        assert len(assets) == 1
        assert assets[0].storage_key != first_key
        storage.delete.assert_called_once_with(first_key)

    def test_a_conflicting_asset_path_is_reported(self, authenticated_client, project):
        with patch.object(
            db.session,
            "commit",
            side_effect=IntegrityError("INSERT", {}, Exception("duplicate")),
        ):
            response = authenticated_client.post(
                f"/admin/projects/{project.id}/docs/assets",
                data={"path": "images/diagram.png", "asset": (BytesIO(PNG_BYTES), "diagram.png")},
                content_type="multipart/form-data",
                follow_redirects=True,
            )

        assert b"An image at that project documentation path already exists." in response.data

    def test_an_asset_is_deleted(self, authenticated_client, db, project):
        asset = ProjectDocumentAsset(
            project_id=project.id,
            path="images/diagram.png",
            storage_key="diagram.png",
            content_type="image/png",
            file_size=10,
            sha256="0" * 64,
        )
        db.session.add(asset)
        db.session.commit()

        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/assets/{asset.id}/delete",
            follow_redirects=True,
        )

        assert b"Documentation image removed." in response.data
        assert db.session.get(ProjectDocumentAsset, asset.id) is None

    def test_an_unknown_asset_is_not_found(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/assets/999999/delete"
        )

        assert response.status_code == 404


class TestDocumentPreview:
    def test_a_draft_is_previewed(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/preview",
            data={"path": "guide/start.md", "title": "Start", "body": "# Start"},
        )

        assert response.status_code == 200
        assert b"Draft preview" in response.data

    def test_an_invalid_preview_is_reported(self, authenticated_client, project):
        response = authenticated_client.post(
            f"/admin/projects/{project.id}/docs/preview",
            data={"path": "guide/start.md", "title": "", "body": "b"},
        )

        assert response.status_code == 400
        assert b"A document title is required" in response.data
