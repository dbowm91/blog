import os
import shutil
import gzip
import tempfile

from flask import render_template, redirect, url_for, request, flash, send_file, abort
from flask_login import login_required

from app.extensions import db
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import _get_backup_dir
from app.utils import safe_delete_file
from app.routes.admin.helpers.shared import BACKUP_FILENAME_RE
from flask import current_app
from datetime import datetime, timezone


@admin.route("/backup")
@admin_required
def backup():
    """
    Backup management - list available backups.

    Methods: GET
    GET: Renders backup page listing all database backups in instance/backups/.
    Requires: Admin authentication.
    """
    backup_dir = _get_backup_dir()
    backups = []
    if os.path.isdir(backup_dir):
        for fname in sorted(os.listdir(backup_dir), reverse=True):
            if fname.startswith("blog_") and (
                fname.endswith(".db") or fname.endswith(".db.gz")
            ):
                fpath = os.path.join(backup_dir, fname)
                stat = os.stat(fpath)
                backups.append(
                    {
                        "name": fname,
                        "size": stat.st_size,
                        "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    }
                )
    return render_template("admin/backup.html", backups=backups)


@admin.route("/backup/create", methods=["POST"])
@admin_required
def create_backup():
    """
    Create a new database backup.

    Methods: POST
    POST: Creates a timestamped database backup. Optional gzip compression.
    Requires: Admin authentication.
    Form params: compress (checkbox) - Enable gzip compression.
    """
    from backup import create_backup as _create_backup

    compress = "compress" in request.form
    db_path = os.path.join(current_app.instance_path, "blog.db")
    backup_dir = _get_backup_dir()
    result = _create_backup(db_path, backup_dir, compress=compress, keep=10)
    if result:
        flash("Backup created successfully.", "success")
    else:
        flash("Backup failed.", "error")
    return redirect(url_for("admin.backup"))


@admin.route("/backup/download/<filename>")
@admin_required
def download_backup(filename):
    """
    Download a backup file.

    Methods: GET
    GET: Streams the backup file as an attachment.
    Requires: Admin authentication.
    Path params: filename - Name of backup file (validated against regex).
    """
    if not BACKUP_FILENAME_RE.match(filename):
        abort(400)
    backup_dir = _get_backup_dir()
    filepath = os.path.join(backup_dir, filename)
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(os.path.realpath(backup_dir) + os.sep):
        abort(400)
    if not os.path.exists(real_path):
        abort(404)
    return send_file(real_path, as_attachment=True, download_name=filename)


@admin.route("/backup/restore/<filename>", methods=["POST"])
@admin_required
def restore_backup(filename):
    """
    Restore database from a backup.

    Methods: POST
    POST: Restores database from backup file. Handles gzip decompression.
          Closes existing connections before overwriting.
    Requires: Admin authentication.
    Path params: filename - Name of backup file to restore.
    Warning: Requires app restart for full effect.
    """
    if not BACKUP_FILENAME_RE.match(filename):
        abort(400)
    backup_dir = _get_backup_dir()
    filepath = os.path.join(backup_dir, filename)
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(os.path.realpath(backup_dir) + os.sep):
        abort(400)
    if not os.path.exists(real_path):
        abort(404)
    db_path = os.path.join(current_app.instance_path, "blog.db")
    db.engine.dispose()
    if filename.endswith(".gz"):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name
        with gzip.open(real_path, "rb") as f_in:
            with open(tmp_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        shutil.copy2(tmp_path, db_path)
        os.unlink(tmp_path)
    else:
        shutil.copy2(real_path, db_path)
    flash(
        f"Database restored from {filename}. You may need to restart the app for all changes to take effect.",
        "success",
    )
    return redirect(url_for("admin.backup"))


@admin.route("/backup/delete/<filename>", methods=["POST"])
@admin_required
def delete_backup(filename):
    """
    Delete a backup file.

    Methods: POST
    POST: Deletes the backup file from instance/backups/.
    Requires: Admin authentication.
    Path params: filename - Name of backup file to delete.
    """
    if not BACKUP_FILENAME_RE.match(filename):
        abort(400)
    backup_dir = _get_backup_dir()
    filepath = os.path.join(backup_dir, filename)
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(os.path.realpath(backup_dir) + os.sep):
        abort(400)
    if os.path.exists(real_path):
        if safe_delete_file(real_path):
            flash(f"Backup {filename} deleted.", "success")
        else:
            flash("Failed to delete backup file.", "error")
    else:
        abort(404)
    return redirect(url_for("admin.backup"))
