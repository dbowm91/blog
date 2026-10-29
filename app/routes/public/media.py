"""Media routes - serve uploaded files from the configured upload folder.

The local storage backend publishes uploads as ``/static/uploads/<name>``.
Flask's own static route answers that prefix from the application's static
folder, which is the installation directory. A deployment that keeps its
uploads outside that directory - every container deployment, where the upload
folder is ``/data/uploads`` - would answer those URLs with a 404 even though
the file exists.

This route serves the configured upload folder under the same prefix, so the
URL the storage backend publishes is the URL that resolves. The nginx
configuration maps the same prefix onto the same directory, so both entry
points serve identical bytes.
"""

from __future__ import annotations

from flask import Blueprint, current_app, send_from_directory
from flask.typing import ResponseReturnValue


def register_media_routes(blueprint: Blueprint) -> None:
    """Register the public media routes."""

    @blueprint.route("/static/uploads/<path:filename>")
    def uploaded_file(filename: str) -> ResponseReturnValue:
        upload_folder = current_app.config.get("UPLOAD_FOLDER")
        if not upload_folder:
            return ("Not Found", 404)
        return send_from_directory(upload_folder, filename)
