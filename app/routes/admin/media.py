from __future__ import annotations

import heapq
import threading
import time as _time
import logging
from datetime import datetime, timezone

from flask import render_template, redirect, url_for, request, flash, abort, current_app
from flask.typing import ResponseReturnValue
from typing import Any
from sqlalchemy import select

from app.extensions import db
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import _save_image
from app.config import MEDIA_PER_PAGE, MEDIA_MAX_FILES
from werkzeug.utils import secure_filename
from app.models import Post


logger = logging.getLogger(__name__)


_MEDIA_CACHE: dict[str, Any] = {"files": None, "timestamp": 0}
_MEDIA_CACHE_LOCK = threading.Lock()
_MEDIA_CACHE_TTL = 30


def _invalidate_media_cache() -> None:
    with _MEDIA_CACHE_LOCK:
        _MEDIA_CACHE["files"] = None


def _get_cached_media_list(
    upload_dir: str,
    search: str | None = None,
) -> list[Any]:
    global _MEDIA_CACHE
    all_files: list[dict[str, object]] = []
    with _MEDIA_CACHE_LOCK:
        now = _time.monotonic()
        if (
            _MEDIA_CACHE["files"] is not None
            and _MEDIA_CACHE["timestamp"] is not None
            and (now - _MEDIA_CACHE["timestamp"]) < _MEDIA_CACHE_TTL
        ):
            all_files = _MEDIA_CACHE["files"]
        else:
            all_files = _scan_media_directory(upload_dir)
            _MEDIA_CACHE["files"] = all_files
            _MEDIA_CACHE["timestamp"] = now

        if search:
            files = [
                (f["mtime"], f["name"], f["size"])
                for f in all_files
                if search.lower() in str(f["name"]).lower()
            ]
            return files
        return [
            {"name": str(f["name"]), "size": int(f["size"]), "mtime": f["mtime"]} for f in all_files
        ]


def _scan_media_directory(upload_dir: str) -> list[dict[str, object]]:
    from app.storage import get_storage

    storage = get_storage()
    all_files = []
    for name in storage.list_files():
        from app.storage import get_storage

        storage = get_storage()
        if storage.exists(name):
            import os as _os

            path = storage.path(name)
            try:
                stat = _os.stat(path)
                file_info = (
                    stat.st_mtime,
                    name,
                    stat.st_size,
                )
                all_files.append(file_info)
            except OSError:
                continue
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
def media() -> ResponseReturnValue:
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

    truncated = len(all_files) > max_files
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
def upload_media() -> ResponseReturnValue:
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
def delete_media(filename: str) -> ResponseReturnValue:
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
    from app.storage import get_storage

    storage = get_storage()
    if not storage.exists(filename):
        abort(404)
    if not storage.delete(filename):
        flash("Failed to delete file.", "error")
        return redirect(url_for("admin.media"))
    _invalidate_media_cache()
    flash(f"Deleted {filename}.", "success")
    return redirect(url_for("admin.media"))


def cleanup_orphaned_images(app) -> tuple[int, int]:
    """Clean up image files that are not associated with any post.

    Returns (orphaned_count, missing_count) tuple:
        - orphaned_count: number of files deleted that weren't in DB
        - missing_count: number of DB entries pointing to missing files (cleared)
    """
    from app.storage import get_storage

    storage = get_storage()
    db_images = set()
    missing_db_entries = []
    posts_with_missing_images = []

    posts = db.session.execute(select(Post.image).where(Post.image.isnot(None))).scalars().all()

    for img in posts:
        if img:
            db_images.add(img)
            if not storage.exists(img):
                missing_db_entries.append(img)
                missing_posts = (
                    db.session.execute(select(Post).filter_by(image=img)).scalars().all()
                )
                for post in missing_posts:
                    posts_with_missing_images.append(post)

    orphaned_count = 0
    missing_count = 0

    try:
        for name in storage.list_files():
            if name not in db_images:
                if storage.delete(name):
                    orphaned_count += 1
                    logger.info("Deleted orphaned image: %s", name)
                else:
                    logger.warning("Failed to delete orphaned image: %s", name)
    except (OSError, AttributeError) as e:
        logger.error("Error scanning upload directory: %s", e)

    for post in posts_with_missing_images:
        post.image = None
        missing_count += 1
        logger.info("Cleared missing image reference from post id=%d", post.id)

    if missing_count > 0:
        db.session.commit()

    logger.info(
        "Orphaned image cleanup complete: %d orphaned files deleted, %d missing DB entries cleared",
        orphaned_count,
        missing_count,
    )
    return orphaned_count, missing_count
