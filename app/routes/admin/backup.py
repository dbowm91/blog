from __future__ import annotations

import os
import shutil
import gzip
import tempfile
from datetime import datetime, timezone

from flask import render_template, redirect, url_for, request, flash, send_file, abort
from flask.typing import ResponseReturnValue

from app.extensions import db
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import _get_backup_dir, _resolve_database_path
from app.utils import safe_delete_file
from app.routes.admin.helpers.shared import validate_backup_filename
from sqlalchemy.exc import SQLAlchemyError


@admin.route("/backup")
@admin_required
def backup() -> ResponseReturnValue:
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
                fname.endswith(".db") or fname.endswith(".db.gz") or fname.endswith(".db.gpg")
            ):
                fpath = os.path.join(backup_dir, fname)
                stat = os.stat(fpath)
                backups.append(
                    {
                        "name": fname,
                        "size": stat.st_size,
                        "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                        "encrypted": fname.endswith(".gpg"),
                    }
                )
    return render_template("admin/backup.html", backups=backups)


@admin.route("/backup/create", methods=["POST"])
@admin_required
def create_backup() -> ResponseReturnValue:
    """
    Create a new database backup.

    Methods: POST
    POST: Creates a timestamped database backup. Optional gzip compression.
    Requires: Admin authentication.
    Form params:
        compress (checkbox) - Enable gzip compression
        encrypt (checkbox) - Enable AES-256-GCM encryption (requires BACKUP_ENCRYPTION_KEY env var)
    """
    from app.services.backup import create_backup as _create_backup

    compress = "compress" in request.form
    encrypt = "encrypt" in request.form
    db_path = _resolve_database_path()
    backup_dir = _get_backup_dir()
    result = _create_backup(db_path, backup_dir, compress=compress, keep=10, encrypt=encrypt)
    if result:
        flash("Backup created successfully.", "success")
    else:
        flash("Backup failed.", "error")
    return redirect(url_for("admin.backup"))


@admin.route("/backup/download/<filename>")
@admin_required
def download_backup(filename) -> ResponseReturnValue:
    """
    Download a backup file.

    Methods: GET
    GET: Streams the backup file as an attachment.
    Requires: Admin authentication.
    Path params: filename - Name of backup file (validated against regex).
    """
    if not validate_backup_filename(filename):
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
def restore_backup(filename) -> ResponseReturnValue:
    """
    Restore database from a backup.

    Methods: POST
    POST: Restores database from backup file. Handles gzip decompression and AES-256-GCM decryption.
          Closes existing connections before overwriting.
    Requires: Admin authentication.
    Path params: filename - Name of backup file to restore.
    Warning: Requires app restart for full effect.
    """
    if not validate_backup_filename(filename):
        abort(400)
    backup_dir = _get_backup_dir()
    filepath = os.path.join(backup_dir, filename)
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(os.path.realpath(backup_dir) + os.sep):
        abort(400)
    if not os.path.exists(real_path):
        abort(404)
    db_path = _resolve_database_path()
    db.engine.dispose()

    is_encrypted = filename.endswith(".gpg")
    is_compressed = filename.endswith(".gz")

    tmp_restored = None
    try:
        if is_encrypted:
            from app.backup_encryption import decrypt_backup_file

            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp_path = tmp.name
            success = decrypt_backup_file(real_path, tmp_path)
            if not success:
                flash("Failed to decrypt backup file.", "error")
                return redirect(url_for("admin.backup"))
            from pathlib import Path

            from app.backup_integrity import verify_backup_integrity

            is_valid, message = verify_backup_integrity(Path(tmp_path))
            if not is_valid:
                os.unlink(tmp_path)
                flash(f"Backup integrity check failed: {message}", "error")
                return redirect(url_for("admin.backup"))
            tmp_restored = tmp_path
            shutil.copy2(tmp_path, db_path)
            os.unlink(tmp_path)
        elif is_compressed:
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp_path = tmp.name
            with gzip.open(real_path, "rb") as f_in:
                with open(tmp_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            from pathlib import Path

            from app.backup_integrity import verify_backup_integrity

            is_valid, message = verify_backup_integrity(Path(tmp_path))
            if not is_valid:
                os.unlink(tmp_path)
                flash(f"Backup integrity check failed: {message}", "error")
                return redirect(url_for("admin.backup"))
            tmp_restored = tmp_path
            shutil.copy2(tmp_path, db_path)
            os.unlink(tmp_path)
        else:
            from pathlib import Path

            from app.backup_integrity import verify_backup_integrity

            is_valid, message = verify_backup_integrity(Path(real_path))
            if not is_valid:
                flash(f"Backup integrity check failed: {message}", "error")
                return redirect(url_for("admin.backup"))
            shutil.copy2(real_path, db_path)
    except (OSError, ValueError, SQLAlchemyError) as e:
        if tmp_restored and os.path.exists(tmp_restored):
            os.unlink(tmp_restored)
        flash(f"Restore failed: {e}", "error")
        return redirect(url_for("admin.backup"))

    flash(
        f"Database restored from {filename}. You may need to restart the app for all changes to take effect.",
        "success",
    )
    return redirect(url_for("admin.backup"))


@admin.route("/backup/delete/<filename>", methods=["POST"])
@admin_required
def delete_backup(filename) -> ResponseReturnValue:
    """
    Delete a backup file.

    Methods: POST
    POST: Deletes the backup file from instance/backups/.
    Requires: Admin authentication.
    Path params: filename - Name of backup file to delete.
    """
    if not validate_backup_filename(filename):
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


@admin.route("/backup/verify/<filename>")
@admin_required
def verify_backup(filename) -> ResponseReturnValue:
    """
    Verify the integrity of a backup file.

    Methods: GET
    GET: Verifies backup file integrity and returns result as JSON.
    Requires: Admin authentication.
    Path params: filename - Name of backup file to verify.
    """
    from pathlib import Path
    from app.backup_integrity import verify_backup_integrity

    if not validate_backup_filename(filename):
        abort(400)
    backup_dir = _get_backup_dir()
    filepath = os.path.join(backup_dir, filename)
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(os.path.realpath(backup_dir) + os.sep):
        abort(400)
    if not os.path.exists(real_path):
        abort(404)

    is_valid, message = verify_backup_integrity(Path(real_path))
    return {"valid": is_valid, "message": message}


@admin.route("/backup/verify-all")
@admin_required
def verify_all_backups() -> ResponseReturnValue:
    """
    Verify integrity of all backups in the backup directory.

    Methods: GET
    GET: Verifies all backup files and returns summary as JSON.
    Requires: Admin authentication.
    """
    from pathlib import Path
    from app.backup_integrity import verify_backup_set

    backup_dir = _get_backup_dir()
    results = verify_backup_set(Path(backup_dir))
    return results
