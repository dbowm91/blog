"""Backup operational service — structured results for backup creation and verification."""

from __future__ import annotations

import os
import sqlite3

from flask import current_app

from app.services.operations.results import (
    BackupCreateResult,
    BackupVerifyResult,
    BackupInspectResult,
)


def create_backup_operation(
    *,
    compress: bool = False,
    encrypt: bool = False,
    keep: int = 7,
) -> BackupCreateResult:
    """Create a database backup with structured result.

    Returns path and verification status. Never prints encryption keys.
    """
    from app.config import DATA_BACKUP_DIR  # noqa: F401
    from app.services.backup import create_backup, resolve_backup_dir, resolve_database_file

    db_path = resolve_database_file(current_app)

    if not db_path or not os.path.exists(db_path):
        return BackupCreateResult(
            ok=False,
            code="backup.create.db_not_found",
            summary=f"Database not found at {db_path}",
            details={"db_path": db_path},
            remediation=["Ensure the database has been initialized before creating backups."],
        )

    backup_dir = resolve_backup_dir(current_app)

    warnings: list[str] = []
    if encrypt:
        from app.backup_encryption import is_encryption_available

        if not is_encryption_available():
            return BackupCreateResult(
                ok=False,
                code="backup.create.encryption_unavailable",
                summary="Encryption requested but not available",
                details={"compress": compress, "encrypt": True, "keep": keep},
                remediation=[
                    "Install the cryptography library: pip install cryptography",
                    "Set the BACKUP_ENCRYPTION_KEY environment variable (minimum 12 characters).",
                ],
            )
        warnings.append("Encryption key is managed via BACKUP_ENCRYPTION_KEY env var.")

    path = create_backup(
        db_path=db_path,
        backup_dir=backup_dir,
        compress=compress,
        keep=keep,
        encrypt=encrypt,
    )

    if path is None:
        return BackupCreateResult(
            ok=False,
            code="backup.create.failed",
            summary="Backup creation failed",
            details={
                "db_path": db_path,
                "backup_dir": backup_dir,
                "compress": compress,
                "encrypt": encrypt,
            },
            remediation=["Check application logs for details."],
        )

    verified = _quick_verify(path)

    return BackupCreateResult(
        ok=True,
        code="backup.create.ok",
        summary=f"Backup created: {os.path.basename(path)}",
        path=path,
        verified=verified,
        details={
            "db_path": db_path,
            "backup_dir": backup_dir,
            "compress": compress,
            "encrypt": encrypt,
            "keep": keep,
        },
        warnings=warnings,
    )


def verify_backup(path: str) -> BackupVerifyResult:
    """Verify a backup file exists and is readable. Basic integrity check."""
    if not os.path.exists(path):
        return BackupVerifyResult(
            ok=False,
            code="backup.verify.not_found",
            summary=f"Backup file not found: {path}",
            path=path,
            valid=False,
            remediation=["Verify the file path is correct and the backup has not been removed."],
        )

    try:
        file_size = os.path.getsize(path)
    except OSError as e:
        return BackupVerifyResult(
            ok=False,
            code="backup.verify.unreadable",
            summary=f"Cannot read backup file: {e}",
            path=path,
            valid=False,
        )

    if file_size == 0:
        return BackupVerifyResult(
            ok=False,
            code="backup.verify.empty",
            summary=f"Backup file is empty: {path}",
            path=path,
            valid=False,
        )

    is_valid = _quick_verify(path)

    if is_valid:
        return BackupVerifyResult(
            ok=True,
            code="backup.verify.ok",
            summary=f"Backup is valid: {os.path.basename(path)} ({file_size} bytes)",
            path=path,
            valid=True,
            details={"file_size": file_size},
        )

    return BackupVerifyResult(
        ok=True,
        code="backup.verify.readable",
        summary=f"Backup file is readable but integrity could not be fully verified: {os.path.basename(path)} ({file_size} bytes)",
        path=path,
        valid=True,
        details={"file_size": file_size},
        warnings=["Could not open as SQLite database; file may be compressed or encrypted."],
    )


def _quick_verify(path: str) -> bool:
    """Attempt to open the file as a SQLite database for basic integrity check."""
    try:
        with open(path, "rb") as f:
            header = f.read(16)
        if header[:6] != b"SQLite":
            return False
        conn = sqlite3.connect(path)
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            return row is not None and row[0] == "ok"
        finally:
            conn.close()
    except (sqlite3.Error, OSError):
        return False


def inspect_backup(path: str) -> BackupInspectResult:
    """Inspect a backup file and report its type and properties.

    Does not perform integrity checks. Reports whether the file is
    SQLite, compressed, or encrypted based on magic bytes.
    """
    if not os.path.exists(path):
        return BackupInspectResult(
            ok=False,
            code="backup.inspect.not_found",
            summary=f"Backup file not found: {path}",
            path=path,
            remediation=["Verify the file path is correct."],
        )

    try:
        file_size = os.path.getsize(path)
    except OSError as e:
        return BackupInspectResult(
            ok=False,
            code="backup.inspect.unreadable",
            summary=f"Cannot read backup file: {e}",
            path=path,
        )

    if file_size == 0:
        return BackupInspectResult(
            ok=False,
            code="backup.inspect.empty",
            summary=f"Backup file is empty: {path}",
            path=path,
        )

    try:
        with open(path, "rb") as f:
            header = f.read(16)
    except OSError as e:
        return BackupInspectResult(
            ok=False,
            code="backup.inspect.read_error",
            summary=f"Cannot read backup header: {e}",
            path=path,
        )

    is_sqlite = header[:6] == b"SQLite"
    is_compressed = header[:2] == b"\x1f\x8b"  # gzip magic bytes
    is_encrypted = not is_sqlite and not is_compressed and file_size > 0

    parts = []
    if is_sqlite:
        parts.append("SQLite database")
    if is_compressed:
        parts.append("gzip compressed")
    if is_encrypted:
        parts.append("possibly encrypted")

    type_desc = ", ".join(parts) if parts else "unknown format"

    return BackupInspectResult(
        ok=True,
        code="backup.inspect.ok",
        summary=f"Backup: {os.path.basename(path)} ({file_size} bytes, {type_desc})",
        path=path,
        file_size=file_size,
        is_sqlite=is_sqlite,
        is_compressed=is_compressed,
        is_encrypted=is_encrypted,
        details={
            "file_size": file_size,
            "is_sqlite": is_sqlite,
            "is_compressed": is_compressed,
            "is_encrypted": is_encrypted,
            "type_description": type_desc,
        },
    )
