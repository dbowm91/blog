import pytest

from app.models import Project, ProjectDocument
from app.services.project_docs import DocumentPathError, normalize_document_path


@pytest.mark.parametrize(
    "path",
    [
        "../x.md",
        "a/../x.md",
        "%2e%2e/x.md",
        "%252e%252e/x.md",
        "a\\b.md",
        "/x.md",
        "a//b.md",
        "x.txt",
        "a/./x.md",
    ],
)
def test_document_paths_reject_traversal_and_malformed(path):
    with pytest.raises(DocumentPathError):
        normalize_document_path(path)


def test_document_path_accepts_nested_markdown():
    assert normalize_document_path("guide/setup.md") == "guide/setup.md"


def test_public_project_docs_gate_and_render(app, client, db):
    project = Project(
        title="Docs", slug="docs", body="Landing", summary="", published=True, docs_enabled=False
    )
    db.session.add(project)
    db.session.flush()
    document = ProjectDocument(
        project_id=project.id, path="index.md", title="Home", body="hello", published=True
    )
    db.session.add(document)
    db.session.commit()

    assert client.get("/projects/docs/docs").status_code == 404
    project.docs_enabled = True
    db.session.commit()
    response = client.get("/projects/docs/docs")
    assert response.status_code == 200
    assert "hello" in response.get_data(as_text=True)


def test_admin_docs_routes_render_editor(authenticated_client, db):
    project = Project(
        title="Managed docs", slug="managed-docs", body="", summary="", published=True
    )
    db.session.add(project)
    db.session.commit()

    response = authenticated_client.get(f"/admin/projects/{project.id}/docs/new")
    assert response.status_code == 200
    assert b"Markdown" in response.data


def test_admin_can_create_edit_and_delete_project_doc(authenticated_client, db):
    project = Project(
        title="Managed docs", slug="managed-docs", body="", summary="", published=True
    )
    db.session.add(project)
    db.session.commit()

    response = authenticated_client.post(
        f"/admin/projects/{project.id}/docs/new",
        data={
            "path": "guide/start.md",
            "title": "Start",
            "body": "# Start",
            "nav_order": "10",
            "published": "1",
        },
    )
    assert response.status_code == 302
    document = db.session.execute(
        db.select(ProjectDocument).where(ProjectDocument.project_id == project.id)
    ).scalar_one()
    assert document.published is True

    response = authenticated_client.get(f"/admin/projects/{project.id}/docs/{document.id}/edit")
    assert response.status_code == 200
    assert b"guide/start.md" in response.data

    response = authenticated_client.post(f"/admin/projects/{project.id}/docs/{document.id}/delete")
    assert response.status_code == 302
    assert db.session.get(ProjectDocument, document.id) is None


def test_github_docs_sync_activates_complete_snapshot_and_preserves_local_docs(db):
    import base64

    from app.services.project_docs_sync import sync_project_docs

    project = Project(
        title="Remote docs",
        slug="remote-docs",
        body="",
        summary="",
        published=True,
        docs_enabled=True,
        github_owner="example",
        github_repository="sample",
        github_docs_root="docs",
    )
    local_document = ProjectDocument(
        project=project,
        version_key="current",
        path="local.md",
        title="Local",
        body="Local authored",
        published=True,
    )
    db.session.add_all([project, local_document])
    db.session.commit()
    commit_sha = "a" * 40
    files = {
        "README.md": "# Readme",
        "docs/index.md": "# Guide",
    }

    class FakeClient:
        def get_json(self, path_segments, *, params=None, etag=None):
            if path_segments[-2:] == ("commits", "HEAD"):
                return type(
                    "Response",
                    (),
                    {"data": {"sha": commit_sha}, "etag": '"v1"', "not_modified": False},
                )()
            if path_segments[-2:] == ("trees", commit_sha):
                return type(
                    "Response",
                    (),
                    {
                        "data": {
                            "tree": [
                                {
                                    "path": path,
                                    "type": "blob",
                                    "mode": "100644",
                                    "size": len(body.encode()),
                                }
                                for path, body in files.items()
                            ],
                            "truncated": False,
                        },
                        "etag": None,
                        "not_modified": False,
                    },
                )()
            upstream_path = "/".join(path_segments[4:])
            body = files[upstream_path]
            payload = base64.b64encode(body.encode()).decode()
            return type(
                "Response",
                (),
                {
                    "data": {"encoding": "base64", "content": payload},
                    "etag": None,
                    "not_modified": False,
                },
            )()

    snapshot = sync_project_docs(project.id, client=FakeClient())
    assert snapshot.commit_sha == commit_sha
    assert snapshot.file_count == 2
    assert project.active_docs_snapshot_id == snapshot.id
    assert project.docs_source_kind == "github"
    assert {doc.path for doc in project.documents if doc.snapshot_id == snapshot.id} == {
        "README.md",
        "index.md",
    }
    assert local_document.snapshot_id is None
    assert local_document.body == "Local authored"


def test_unpublished_project_docs_are_hidden(client, db):
    project = Project(
        title="Draft",
        slug="draft-docs",
        body="Landing",
        summary="",
        published=False,
        docs_enabled=True,
    )
    db.session.add(project)
    db.session.flush()
    db.session.add(
        ProjectDocument(project_id=project.id, path="index.md", title="Secret", published=True)
    )
    db.session.commit()
    assert client.get("/projects/draft-docs/docs").status_code == 404


@pytest.mark.parametrize(
    ("base_path", "relative", "expected"),
    [
        ("guides/setup.md", "../README.md", "README.md"),
        ("guides/setup.md", "./other.md", "guides/other.md"),
        ("guides/setup.md", "other.md", "guides/other.md"),
        ("guides/deep/setup.md", "../../README.md", "README.md"),
        ("README.md", "./guides/setup.md", "guides/setup.md"),
        ("guides/setup.md", "notes.md#section", "guides/notes.md"),
    ],
)
def test_relative_links_resolve_inside_the_documentation_root(base_path, relative, expected):
    from app.services.project_docs import resolve_document_path

    assert resolve_document_path(base_path, relative) == expected


@pytest.mark.parametrize(
    ("base_path", "relative"),
    [
        ("guides/setup.md", "../../README.md"),
        ("README.md", "../README.md"),
        ("guides/setup.md", "../../../README.md"),
    ],
)
def test_relative_links_that_escape_the_documentation_root_are_rejected(base_path, relative):
    from app.services.project_docs import resolve_document_path

    assert resolve_document_path(base_path, relative) is None


def test_relative_asset_links_resolve_inside_the_documentation_root():
    from app.services.project_docs import resolve_asset_path

    assert resolve_asset_path("guides/setup.md", "../images/logo.png") == "images/logo.png"
    assert resolve_asset_path("guides/setup.md", "./logo.png") == "guides/logo.png"
    assert resolve_asset_path("guides/setup.md", "../../logo.png") is None
    assert resolve_asset_path("guides/setup.md", "../notes.md") is None


def test_rendered_document_links_resolve_relative_references(app, db):
    from app.services.project_docs import render_document

    project = Project(
        title="Linked docs",
        slug="linked-docs",
        body="",
        summary="",
        published=True,
        docs_enabled=True,
    )
    db.session.add(project)
    db.session.flush()
    readme = ProjectDocument(
        project_id=project.id, path="README.md", title="Readme", body="root", published=True
    )
    setup = ProjectDocument(
        project_id=project.id, path="guides/setup.md", title="Setup", body="", published=True
    )
    sibling = ProjectDocument(
        project_id=project.id, path="guides/other.md", title="Other", body="", published=True
    )
    db.session.add_all([readme, setup, sibling])
    db.session.commit()

    setup.body = "[up](../README.md) [same](./other.md) [escape](../../README.md)"
    db.session.commit()

    with app.test_request_context():
        html = render_document(project, setup)

    assert "/projects/linked-docs/docs/README.md" in html
    assert "/projects/linked-docs/docs/guides/other.md" in html
    assert "../" not in html


def test_docs_sync_reports_a_client_that_cannot_address_the_documentation_depth(db):
    from app.services.project_docs_sync import ProjectDocsSyncError, sync_project_docs

    project = Project(
        title="Deep docs",
        slug="deep-docs",
        body="",
        summary="",
        published=True,
        docs_enabled=True,
        github_owner="example",
        github_repository="sample",
    )
    db.session.add(project)
    db.session.commit()

    class ShallowClient:
        max_path_segments = 8

        def get_json(self, path_segments, *, params=None, etag=None):
            raise AssertionError("the client must not reach the network")

    with pytest.raises(ProjectDocsSyncError, match="path limit"):
        sync_project_docs(project.id, client=ShallowClient())

    assert project.docs_sync_status == "failed"
