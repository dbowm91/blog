import os

from flask import render_template, redirect, url_for, request, flash, abort, current_app
from flask_login import login_required

from app.extensions import db
from app.routes.admin import (
    admin,
    admin_required,
    _save_image,
    safe_delete_file,
)
from app.config import MEDIA_PER_PAGE, MEDIA_MAX_FILES
from datetime import datetime, timezone
from werkzeug.utils import secure_filename


@admin.route("/media")
@admin_required
def media():
    page = request.args.get("page", 1, type=int)
    per_page = MEDIA_PER_PAGE
    max_files = MEDIA_MAX_FILES
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    all_files = []
    with os.scandir(upload_dir) as entries:
        for entry in entries:
            if not entry.is_file():
                continue
            stat = entry.stat()
            all_files.append(
                {
                    "name": entry.name,
                    "size": stat.st_size,
                    "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                }
            )
        all_files.sort(key=lambda f: f["mtime"], reverse=True)
    if len(all_files) > max_files:
        all_files = all_files[:max_files]
    truncated = len(all_files) >= max_files
    total = len(all_files)
    start = (page - 1) * per_page
    end = start + per_page
    files = all_files[start:end]
    total_pages = (total + per_page - 1) // per_page
    return render_template(
        "admin/media.html",
        files=files,
        page=page,
        total_pages=total_pages,
        truncated=truncated,
    )


@admin.route("/media/upload", methods=["POST"])
@admin_required
def upload_media():
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
        flash(f"Uploaded {filename}.", "success")

    return redirect(url_for("admin.media"))


@admin.route("/media/delete/<filename>", methods=["POST"])
@admin_required
def delete_media(filename):
    filename = secure_filename(filename)
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
    flash(f"Deleted {filename}.", "success")
    return redirect(url_for("admin.media"))
