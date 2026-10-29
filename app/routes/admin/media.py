from __future__ import annotations

import heapq
import threading
import time as _time
from datetime import datetime, timezone
from typing import Any, cast

from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from app.config import MAX_UPLOAD_SIZE, MEDIA_MAX_FILES, MEDIA_PER_PAGE
from app.routes.admin import admin, admin_required, author_required
from app.routes.admin.helpers.media import classify_file_info, upload_media_file


_MEDIA_CACHE: dict[str, Any] = {"files": None, "timestamp": 0}
_MEDIA_CACHE_LOCK = threading.Lock()
_MEDIA_CACHE_TTL = 30


def _invalidate_media_cache() -> None:
    with _MEDIA_CACHE_LOCK:
        _MEDIA_CACHE["files"] = None


def _scan_media_directory(upload_dir: str) -> list[dict[str, object]]:
    from app.storage import get_storage

    file_infos = get_storage().list_file_info()
    classified = [classify_file_info(info) for info in file_infos]
    return heapq.nlargest(
        MEDIA_MAX_FILES,
        classified,
        key=lambda info: (
            cast(datetime | None, info["mtime"]) or datetime.min.replace(tzinfo=timezone.utc)
        ),
    )


def _get_cached_media_list(
    upload_dir: str,
    search: str | None = None,
    category: str | None = None,
) -> list[dict[str, object]]:
    with _MEDIA_CACHE_LOCK:
        now = _time.monotonic()
        if (
            _MEDIA_CACHE["files"] is None
            or _MEDIA_CACHE["timestamp"] is None
            or now - _MEDIA_CACHE["timestamp"] >= _MEDIA_CACHE_TTL
        ):
            _MEDIA_CACHE["files"] = _scan_media_directory(upload_dir)
            _MEDIA_CACHE["timestamp"] = now
        all_files = list(_MEDIA_CACHE["files"])

    if search:
        all_files = [
            item for item in all_files if search.casefold() in str(item["display_name"]).casefold()
        ]
    if category in {"image", "video", "other"}:
        all_files = [item for item in all_files if item["category"] == category]
    return all_files


def _api_media_item(item: dict[str, object]) -> dict[str, object]:
    filename = str(item["name"])
    mtime = cast(datetime | None, item["mtime"])
    return {
        "name": item["name"],
        "display_name": item["display_name"],
        "category": item["category"],
        "size": item["size"],
        "mime_type": item["mime_type"],
        "url": item["url"] if item["category"] in {"image", "video"} else item["download_url"],
        "download_url": item["download_url"],
        "mtime": mtime.isoformat() if mtime else None,
        "delete_url": url_for("admin.delete_media", filename=filename),
    }


@admin.route("/media")
@admin_required
def media() -> ResponseReturnValue:
    page = max(1, request.args.get("page", 1, type=int))
    search = request.args.get("search", "", type=str).strip()
    category = request.args.get("category", "all", type=str)
    if category not in {"all", "image", "video", "other"}:
        category = "all"
    all_files = _get_cached_media_list(
        current_app.config["UPLOAD_FOLDER"], search, None if category == "all" else category
    )
    total = len(all_files)
    start = (page - 1) * MEDIA_PER_PAGE
    files = [_api_media_item(item) for item in all_files[start : start + MEDIA_PER_PAGE]]
    total_pages = max(1, (total + MEDIA_PER_PAGE - 1) // MEDIA_PER_PAGE)
    counts = {
        value: sum(
            1
            for item in _get_cached_media_list(current_app.config["UPLOAD_FOLDER"])
            if item["category"] == value
        )
        for value in ("image", "video", "other")
    }
    return render_template(
        "admin/media.html",
        files=files,
        page=page,
        total_pages=total_pages,
        truncated=len(_get_cached_media_list(current_app.config["UPLOAD_FOLDER"]))
        >= MEDIA_MAX_FILES,
        search=search,
        category=category,
        counts=counts,
        total=total,
    )


@admin.route("/media/items")
@author_required
def media_items() -> ResponseReturnValue:
    category = request.args.get("category", "all", type=str)
    if category not in {"all", "image", "video", "other"}:
        return jsonify({"error": "Invalid media category."}), 400
    search = request.args.get("search", "", type=str).strip()[:100]
    items = _get_cached_media_list(
        current_app.config["UPLOAD_FOLDER"], search, None if category == "all" else category
    )
    return jsonify({"items": [_api_media_item(item) for item in items]})


@admin.route("/media/upload", methods=["POST"])
@author_required
def upload_media() -> ResponseReturnValue:
    wants_json = (
        request.accept_mimetypes.best == "application/json"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )
    request.max_content_length = MAX_UPLOAD_SIZE + 1024 * 1024
    try:
        file = request.files.get("file")
    except RequestEntityTooLarge:
        error = f"Upload exceeds the {MAX_UPLOAD_SIZE // (1024 * 1024)}MB limit."
        if wants_json:
            return jsonify({"error": error}), 413
        flash(error, "error")
        return redirect(url_for("admin.media"))
    if file is None or not file.filename:
        error = "Choose a file to upload."
        if wants_json:
            return jsonify({"error": error}), 400
        flash(error, "error")
        return redirect(url_for("admin.media"))

    category = request.form.get("category", "image")
    item, upload_error = upload_media_file(file, category)
    if upload_error or not item:
        if wants_json:
            return jsonify({"error": upload_error or "Upload failed."}), 400
        flash(upload_error or "Upload failed.", "error")
        return redirect(url_for("admin.media", category=category))

    _invalidate_media_cache()
    response_item = {
        "name": item["name"],
        "category": item["category"],
        "mime_type": item.get("mime_type", "application/octet-stream"),
        "url": item["url"],
        "display_name": item.get("display_name", item["name"]),
    }
    if wants_json:
        return jsonify({"item": response_item}), 201
    flash(f"Uploaded {response_item['display_name']}.", "success")
    return redirect(url_for("admin.media", category=category))


@admin.route("/media/delete/<path:filename>", methods=["POST"])
@admin_required
def delete_media(filename: str) -> ResponseReturnValue:
    filename = secure_filename(filename)
    if not filename:
        abort(400)
    from app.storage import get_storage

    storage = get_storage()
    if not storage.exists(filename):
        abort(404)
    if not storage.delete(filename):
        flash("Failed to delete file.", "error")
        return redirect(url_for("admin.media"))
    _invalidate_media_cache()
    flash("File deleted.", "success")
    return redirect(url_for("admin.media"))


def cleanup_orphaned_images(app) -> tuple[int, int]:
    """Clean up image files that are not associated with any post."""
    from app.services.operations.media import apply_orphaned_media_cleanup

    result = apply_orphaned_media_cleanup()
    return result.orphaned_deleted, result.missing_cleared
