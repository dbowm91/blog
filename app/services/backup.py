"""Unified backup service for CLI, scheduler, and cron jobs.

Centralizes backup logic from root backup.py and app/scheduler.py.
Supports compression, GPG encryption, and retention policy using sqlite3.backup() API.
"""

import glob as glob_module
import gzip
import logging
import os
import shutil
import sqlite3
from datetime import datetime
from typing import Optional, Any

from sqlalchemy.exc import SQLAlchemyError


logger = logging.getLogger(__name__)

BACKUP_RETENTION_COUNT = 7


def create_backup(db_path: str, backup_dir: str, compress: bool = False,
                  keep: int = 7, encrypt: bool = False) -> Optional[str]:
    """Create a backup of the SQLite database.

    Args:
        db_path: Path to the source database
        backup_dir: Directory to store backups
        compress: Whether to compress the backup with gzip
        keep: Number of backups to retain (default: 7)
        encrypt: Whether to encrypt the backup with GPG

    Returns:
        Path to the created backup file, or None on failure
    """
    if not os.path.exists(db_path):
        logger.error("Database not found at %s", db_path)
        return None

    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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

        if encrypt:
            if not _encrypt_backup_file(backup_path):
                logger.error("Failed to encrypt backup at %s", backup_path)
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                return None
        elif compress:
            tmp_path = backup_path + ".tmp"
            try:
                with open(backup_path, "rb") as f_in:
                    with gzip.open(tmp_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.replace(tmp_path, backup_path)
            except OSError:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise

        logger.info("Backup created: %s", backup_path)

        cleanup_old_backups(backup_dir, keep)

        return backup_path

    except (sqlite3.Error, OSError) as e:
        logger.error("Error creating backup: %s", e)
        if os.path.exists(backup_path):
            os.remove(backup_path)
        return None


def _encrypt_backup_file(filepath: str) -> bool:
    """Encrypt a backup file using GPG.

    Requires BACKUP_ENCRYPTION_KEY environment variable.
    """
    try:
        from app.backup_encryption import encrypt_backup_file
        return encrypt_backup_file(filepath, filepath)
    except (OSError, ValueError, SQLAlchemyError) as e:
        logger.error("Encryption error for %s: %s", filepath, e)
        return False


def decrypt_backup_file(input_path: str, output_path: Optional[str] = None) -> bool:
    """Decrypt a GPG-encrypted backup file.

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
    except (OSError, ValueError, SQLAlchemyError) as e:
        logger.error("Decryption error for %s: %s", input_path, e)
        return False


def cleanup_old_backups(backup_dir: str, keep: int) -> None:
    """Remove old backups, keeping only the most recent ones."""
    backup_files = []
    for f in os.listdir(backup_dir):
        if f.startswith("blog_") and (f.endswith(".db") or f.endswith(".db.gz") or f.endswith(".db.gpg")):
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
        This uses `backup_*.db` naming pattern (not `blog_*.db`).
        Unlike `create_backup()`, this does NOT support encryption
        or compression. For encrypted/compressed backups, use the
        Celery task `run_backup_task` which calls `create_backup()`.
    """
    from app.config import DATA_BACKUP_DIR

    backup_dir = os.path.join(app.instance_path, DATA_BACKUP_DIR)
    os.makedirs(backup_dir, exist_ok=True)

    db_path = os.path.join(app.instance_path, "blog.db")

    if not os.path.exists(db_path):
        app.logger.warning("Database file not found at %s, skipping backup", db_path)
        return

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    # Use sqlite3.backup() for WAL mode consistency (captures WAL/SHM files)
    source = sqlite3.connect(db_path)
    backup = sqlite3.connect(backup_path)
    source.backup(backup)
    backup.commit()
    source.close()
    backup.close()
    app.logger.info("Created backup: %s", backup_filename)

    backup_pattern = os.path.join(backup_dir, "backup_*.db")
    backups = sorted(
        glob_module.glob(backup_pattern),
        key=os.path.getmtime,
        reverse=True
    )

    retention = BACKUP_RETENTION_COUNT
    for old_backup in backups[retention:]:
        try:
            os.remove(old_backup)
            app.logger.info("Removed old backup: %s", os.path.basename(old_backup))
        except OSError as e:
            app.logger.warning("Failed to remove old backup %s: %s", old_backup, e)
