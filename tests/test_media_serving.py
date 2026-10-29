"""Uploaded media must be served from the configured upload folder.

The local storage backend publishes uploads as ``/static/uploads/<name>``.
Flask's own static route answers that prefix from the installation directory,
so a deployment that keeps its uploads elsewhere - every container deployment,
where the upload folder is ``/data/uploads`` - answered those URLs with a 404
even though the file existed.
"""

from __future__ import annotations

import pytest

PNG_BYTES = b"\x89PNG\r\n\x1a\nnot-a-real-png"


@pytest.fixture()
def upload_folder(app, tmp_path):
    """Point the application at an upload folder outside the source tree."""
    folder = tmp_path / "uploads"
    folder.mkdir()
    original = app.config.get("UPLOAD_FOLDER")
    app.config["UPLOAD_FOLDER"] = str(folder)
    yield folder
    if original is None:
        app.config.pop("UPLOAD_FOLDER", None)
    else:
        app.config["UPLOAD_FOLDER"] = original


def test_an_uploaded_file_is_served_from_the_upload_folder(app, client, upload_folder):
    """The published URL resolves to the file the storage backend wrote."""
    (upload_folder / "picture.png").write_bytes(PNG_BYTES)

    response = client.get("/static/uploads/picture.png")

    assert response.status_code == 200
    assert response.data == PNG_BYTES


def test_a_missing_upload_is_not_found(app, client, upload_folder):
    """A file that was never uploaded answers with a 404."""
    response = client.get("/static/uploads/missing.png")

    assert response.status_code == 404


def test_the_upload_route_does_not_escape_the_upload_folder(app, client, upload_folder):
    """The route cannot be used to read files outside the upload folder."""
    response = client.get("/static/uploads/..%2f..%2fapp%2f__init__.py")

    assert response.status_code == 404


def test_other_static_files_keep_working(app, client, upload_folder):
    """The application's own static files are still served."""
    response = client.get("/static/css/base.css")

    assert response.status_code == 200
