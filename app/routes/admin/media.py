import os
import heapq
import threading
import time as _time

from flask import render_template, redirect, url_for, request, flash, abort, current_app
from flask_login import login_required

from app.extensions import db
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import _save_image
from app.utils import safe_delete_file
from app.config import MEDIA_PER_PAGE, MEDIA_MAX_FILES
from datetime import datetime, timezone
from werkzeug.utils import secure_filename


_MEDIA_CACHE = {"files": None, "timestamp": 0}
_MEDIA_CACHE_LOCK = threading.Lock()
_MEDIA_CACHE_TTL = 30


def _invalidate_media_cache():
    with _MEDIA_CACHE_LOCK:
        _MEDIA_CACHE["files"] = None


def _get_cached_media_list(upload_dir, search=None):
    global _MEDIA_CACHE
    with _MEDIA_CACHE_LOCK:
        now = _time.monotonic()
        if (
            _MEDIA_CACHE["files"] is not None
            and (now - _MEDIA_CACHE["timestamp"]) < _MEDIA_CACHE_TTL
        ):
            files = _MEDIA_CACHE["files"]
        else:
            files = _scan_media_directory(upload_dir)
            _MEDIA_CACHE["files"] = files
            _MEDIA_CACHE["timestamp"] = now

    if search:
        files = [(mtime, name, size) for mtime, name, size in files
                 if search.lower() in name.lower()]
    return files


def _scan_media_directory(upload_dir):
    all_files = []
    with os.scandir(upload_dir) as entries:
        for entry in entries:
            if not entry.is_file():
                continue
            stat = entry.stat()
            file_info = (
                stat.st_mtime,
                entry.name,
                stat.st_size,
            )
            all_files.append(file_info)
    all_files = heapq.nlargest(MEDIA_MAX_FILES, all_files, key=lambda f: f[0])
    return [
        {
            "name": f[1],
            "size": f[2],
            "mtime": datetime.fromtimestamp(f[0], tz=timezone.utc),
        }
        for f in all_files
    ]


@admin.route("/media")
@admin_required
def media():
    """
    Media library - list uploaded files.

    Methods: GET
    GET: Renders media gallery with paginated list of uploaded images.
    Query params:
        page: Page number (default 1)
        search: Filter files by name (case-insensitive)
    Requires: Admin authentication.
    """
    page = request.args.get("page", 1, type=int)
    per_page = MEDIA_PER_PAGE
    max_files = MEDIA_MAX_FILES
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    search = request.args.get("search", "", type=str).strip()

    all_files = _get_cached_media_list(upload_dir, search)

    truncated = len(all_files) >= max_files
    total = len(all_files)
    start = (page - 1) * per_page
    end = start + per_page
    files = all_files[start:end]
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    return render_template(
        "admin/media.html",
        files=files,
        page=page,
        total_pages=total_pages,
        truncated=truncated,
        search=search,
    )


@admin.route("/media/upload", methods=["POST"])
@admin_required
def upload_media():
    """
    Upload an image file.

    Methods: POST
    POST: Saves uploaded image to upload folder. Validates via magic bytes.
    Requires: Admin authentication.
    Form params: file - Image file (png, jpg, jpeg, gif, webp, max 10MB)
    """
    if "file" not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("admin.media"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("admin.media"))

    filename, error = _save_image(file)
    if error:
        flash(error, "error")
    else:
        _invalidate_media_cache()
        flash(f"Uploaded {filename}.", "success")

    return redirect(url_for("admin.media"))


@admin.route("/media/delete/<filename>", methods=["POST"])
@admin_required
def delete_media(filename):
    """
    Delete a media file.

    Methods: POST
    POST: Deletes the file from upload folder. Validates path is within upload dir.
    Requires: Admin authentication.
    Path params: filename - Name of the file to delete.
    """
    filename = secure_filename(filename)
    if not filename:
        abort(400)
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    real_path = os.path.realpath(filepath)
    upload_dir = os.path.realpath(current_app.config["UPLOAD_FOLDER"])
    if not real_path.startswith(upload_dir + os.sep):
        abort(400)
    if not os.path.exists(real_path):
        abort(404)
    if not safe_delete_file(real_path):
        flash("Failed to delete file.", "error")
        return redirect(url_for("admin.media"))
    _invalidate_media_cache()
    flash(f"Deleted {filename}.", "success")
    return redirect(url_for("admin.media"))
