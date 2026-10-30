"""Serve uploaded media and safe public downloads for Markdown attachments."""

from __future__ import annotations

import io
import re

from flask import Blueprint, abort, current_app, send_file, send_from_directory
from flask.typing import ResponseReturnValue
from werkzeug.utils import secure_filename

from app.routes.admin.helpers.media import classify_media
from app.storage import get_storage

_ATTACHMENT_RE = re.compile(r"^[0-9a-f]{32}-(.+)\.attachment$")


def register_media_routes(blueprint: Blueprint) -> None:
    """Register the public media routes."""

    @blueprint.route("/static/uploads/<path:filename>")
    def uploaded_file(filename: str) -> ResponseReturnValue:
        upload_folder = current_app.config.get("UPLOAD_FOLDER")
        if not upload_folder:
            return ("Not Found", 404)
        return send_from_directory(upload_folder, filename)

    @blueprint.get("/media/download/<path:filename>")
    def download_media(filename: str) -> ResponseReturnValue:
        if "/" in filename or "\\" in filename:
            abort(404)
        if filename in {"", ".", ".."} or secure_filename(filename) != filename:
            abort(404)
        match = _ATTACHMENT_RE.fullmatch(filename)
        storage = get_storage()
        if not storage.exists(filename):
            abort(404)
        content = storage.load(filename)
        if content is None:
            abort(404)
        if match is None and classify_media(filename, content[:32]) not in {"image", "video"}:
            abort(404)
        display_name = secure_filename(match.group(1)) if match else secure_filename(filename)
        if not display_name:
            abort(404)
        response = send_file(
            io.BytesIO(content),
            mimetype="application/octet-stream",
            as_attachment=True,
            download_name=display_name,
            max_age=0,
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "private, no-store"
        return response
