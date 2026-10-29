"""Unified backup service for CLI, scheduler, and cron jobs.

Centralizes backup logic from root backup.py and app/scheduler.py.
Supports compression, AES-256-GCM encryption, and retention policy using sqlite3.backup() API.
"""

import glob as glob_module
import gzip
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from typing import Optional, Any


logger = logging.getLogger(__name__)

BACKUP_RETENTION_COUNT = 7


def resolve_database_file(app: Any) -> str | None:
    """Resolve the SQLite database file the running app actually uses.

    The app resolves its database to ``<data_dir>/devlog.sqlite3``; it is not
    at ``instance/blog.db``. ``create_app`` records the live URI in
    ``SQLALCHEMY_DATABASE_URI``, so that is the authoritative answer.

    Returns ``None`` when the database is not a SQLite file, because there is
    then nothing for ``sqlite3.backup()`` to copy.
    """
    uri = ""
    try:
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "") or ""
    except (AttributeError, RuntimeError):
        uri = ""

    if not isinstance(uri, str):
        return None

    if uri.startswith("sqlite:///"):
        return uri[len("sqlite:///") :]

    if uri:
        logger.warning("Database is not a SQLite file (%s) — skipping file backup", uri)
    return None


def resolve_backup_dir(app: Any) -> str:
    """Resolve the directory that holds database backups.

    A relative ``backup.data_backup_dir`` is resolved against the data
    directory, so backups land beside the database rather than in whichever
    directory the service happened to start in.
    """
    from app.config import DATA_BACKUP_DIR

    configured = DATA_BACKUP_DIR or "backups"
    if os.path.isabs(configured):
        return configured

    db_file = resolve_database_file(app)
    base = os.path.dirname(db_file) if db_file else ""
    if not base:
        instance_path = getattr(app, "instance_path", "")
        base = instance_path if isinstance(instance_path, str) else ""
    return os.path.join(base, configured)


def restore_database(db_path: str, backup_path: str) -> None:
    source = sqlite3.connect(backup_path)
    destination = None
    try:
        destination = sqlite3.connect(db_path)
        source.backup(destination)
        destination.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        if destination is not None:
            destination.close()
        source.close()


def create_backup(
    db_path: str,
    backup_dir: str,
    compress: bool = False,
    keep: int = 7,
    encrypt: bool = False,
) -> Optional[str]:
    """Create a backup of the SQLite database.

    Args:
        db_path: Path to the source database
        backup_dir: Directory to store backups
        compress: Whether to compress the backup with gzip
        keep: Number of backups to retain (default: 7)
        encrypt: Whether to encrypt the backup with AES-256-GCM

    Returns:
        Path to the created backup file, or None on failure
    """
    if not os.path.exists(db_path):
        logger.error("Database not found at %s", db_path)
        return None

    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_name = f"blog_{timestamp}.db"
    if compress:
        backup_name += ".gz"
    if encrypt:
        backup_name += ".gpg"
    backup_path = os.path.join(backup_dir, backup_name)

    try:
        source = sqlite3.connect(db_path)
        dest = sqlite3.connect(backup_path)

        try:
            source.backup(dest)
        finally:
            dest.close()
            source.close()

        if compress:
            tmp_path = backup_path + ".tmp"
            try:
                with open(backup_path, "rb") as f_in:
                    with gzip.open(tmp_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.replace(tmp_path, backup_path)
            except OSError:
                raise
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        if encrypt:
            if not _encrypt_backup_file(backup_path):
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                logger.error("Backup encryption failed, discarding unencrypted backup")
                return None

        logger.info("Backup created: %s", backup_path)

        cleanup_old_backups(backup_dir, keep)

        return backup_path

    except (sqlite3.Error, OSError) as e:
        logger.error("Error creating backup: %s", e)
        if os.path.exists(backup_path):
            os.remove(backup_path)
        return None


def _encrypt_backup_file(filepath: str) -> bool:
    """Encrypt a backup file using AES-256-GCM.

    Requires BACKUP_ENCRYPTION_KEY environment variable.
    """
    from app.backup_encryption import encrypt_backup_file, is_encryption_available

    if not is_encryption_available():
        logger.warning(
            "BACKUP_ENCRYPTION_KEY is set but encryption is not available (cryptography library missing or key invalid)"
        )
        return False

    tmp_path = filepath + ".enc.tmp"
    try:
        encrypt_backup_file(filepath, tmp_path)
        os.replace(tmp_path, filepath)
        return True
    except (OSError, ValueError, RuntimeError) as e:
        logger.error("Encryption error for %s: %s", filepath, e)
        return False
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def decrypt_backup_file(input_path: str, output_path: Optional[str] = None) -> bool:
    """Decrypt an AES-256-GCM-encrypted backup file.

    Args:
        input_path: Path to the encrypted backup file
        output_path: Path to write the decrypted output (default: input_path without .gpg extension)

    Returns:
        True on success, False on failure
    """
    try:
        from app.backup_encryption import decrypt_backup_file as _decrypt

        if output_path is None:
            if input_path.endswith(".gpg"):
                output_path = input_path[:-4]
            else:
                output_path = input_path + ".decrypted"
        return _decrypt(input_path, output_path)
    except (OSError, ValueError, RuntimeError) as e:
        logger.error("Decryption error for %s: %s", input_path, e)
        return False


def cleanup_old_backups(backup_dir: str, keep: int) -> None:
    """Remove old backups, keeping only the most recent ones."""
    backup_files = []
    for f in os.listdir(backup_dir):
        if f.startswith("blog_") and (
            f.endswith(".db") or f.endswith(".db.gz") or f.endswith(".db.gpg")
        ):
            full_path = os.path.join(backup_dir, f)
            backup_files.append((os.path.getmtime(full_path), full_path))

    backup_files.sort(reverse=True)

    for _, path in backup_files[keep:]:
        os.remove(path)
        logger.info("Removed old backup: %s", path)


def run_daily_backup(app: Any) -> None:
    """Run daily database backup with retention cleanup.

    Designed to be called from scheduler or CLI.

    Note:
        This uses `blog_*.db` naming pattern.
        Unlike `create_backup()`, this does NOT support encryption
        or compression. For encrypted/compressed backups, use the
        Celery task `run_backup_task` which calls `create_backup()`.
    """
    from app.config import DATA_BACKUP_DIR  # noqa: F401

    backup_dir = resolve_backup_dir(app)
    os.makedirs(backup_dir, exist_ok=True)

    db_path = resolve_database_file(app)

    if not db_path or not os.path.exists(db_path):
        app.logger.warning("Database file not found at %s, skipping backup", db_path)
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"blog_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    # Use sqlite3.backup() for WAL mode consistency (captures WAL/SHM files)
    source = sqlite3.connect(db_path)
    backup = sqlite3.connect(backup_path)
    source.backup(backup)
    backup.commit()
    source.close()
    backup.close()
    app.logger.info("Created backup: %s", backup_filename)

    backup_pattern = os.path.join(backup_dir, "blog_*.db")
    backups = sorted(glob_module.glob(backup_pattern), key=os.path.getmtime, reverse=True)

    retention = BACKUP_RETENTION_COUNT
    for old_backup in backups[retention:]:
        try:
            os.remove(old_backup)
            app.logger.info("Removed old backup: %s", os.path.basename(old_backup))
        except OSError as e:
            app.logger.warning("Failed to remove old backup %s: %s", old_backup, e)
