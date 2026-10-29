from __future__ import annotations

import shutil
import sqlite3
import stat
from dataclasses import dataclass, field
from pathlib import Path

from app.filesystem.layout import RuntimePaths


@dataclass
class PathCheckResult:
    exists: bool
    is_symlink: bool = False
    symlink_target: str | None = None
    writable: bool = False
    permissions: str = "unknown"
    free_space_bytes: int | None = None
    is_release_dir: bool = False


@dataclass
class VerificationResult:
    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    path_checks: dict[str, bool] = field(default_factory=dict)
    path_details: dict[str, PathCheckResult] = field(default_factory=dict)


def verify_database_accessible(db_path: Path) -> bool:
    """Report whether the database file is present and can be opened.

    A SQLite database is opened and queried. A file that opens but is not a
    SQLite database is still accessible on disk; the contents are validated by
    the database integrity checks, not by a layout verification.
    """
    if not db_path.is_file():
        return False
    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.execute("SELECT 1")
        conn.close()
        return True
    except sqlite3.OperationalError:
        return False
    except sqlite3.DatabaseError:
        return True
    except (sqlite3.Error, OSError):
        return False


def checkpoint_database(db_path: Path) -> bool:
    if not db_path.exists():
        return False
    try:
        conn = sqlite3.connect(str(db_path), timeout=10)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        return True
    except (sqlite3.Error, OSError):
        return False


def verify_directory_writable(path: Path) -> bool:
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False
    test_file = path / ".devlog-write-test"
    try:
        test_file.write_text("ok")
        test_file.unlink()
        return True
    except OSError:
        return False


def check_path(path: Path) -> PathCheckResult:
    result = PathCheckResult(exists=path.exists())
    if not path.exists():
        return result
    try:
        if path.is_symlink():
            result.is_symlink = True
            result.symlink_target = str(path.resolve())
    except OSError:
        pass
    try:
        st = path.stat()
        result.permissions = oct(stat.S_IMODE(st.st_mode))
        import os

        result.writable = os.access(path, os.W_OK)
    except OSError:
        pass
    try:
        usage = shutil.disk_usage(path)
        result.free_space_bytes = usage.free
    except OSError:
        pass
    if path.name == "current" and path.parent.name == "releases":
        result.is_release_dir = True
    elif path.is_dir():
        try:
            for item in path.iterdir():
                if item.name == "current" and item.is_symlink():
                    result.is_release_dir = True
                    break
        except OSError:
            pass
    return result


def _check_database_strict(db_path: Path) -> str | None:
    if not db_path.exists():
        return f"Required database file missing: {db_path}"
    if not verify_database_accessible(db_path):
        return f"Database file not accessible: {db_path}"
    return None


def verify_migration(target: RuntimePaths) -> VerificationResult:
    errors: list[str] = []
    warnings: list[str] = []
    path_checks: dict[str, bool] = {}
    path_details: dict[str, PathCheckResult] = {}

    for name in (
        "config_file",
        "env_file",
        "data_dir",
        "database",
        "uploads_dir",
        "themes_dir",
        "backups_dir",
        "exports_dir",
        "log_dir",
        "runtime_dir",
        "installation_metadata",
    ):
        rp = getattr(target, name)
        check = check_path(rp.path)
        path_checks[name] = check.exists
        path_details[name] = check

    if target.release_dir is not None:
        release_check = check_path(target.release_dir.path)
        path_details["release_dir"] = release_check

    if not target.data_dir.path.exists():
        errors.append(f"Data directory does not exist: {target.data_dir.path}")

    if not target.log_dir.path.exists():
        warnings.append(f"Log directory does not exist: {target.log_dir.path}")

    if not target.runtime_dir.path.exists():
        warnings.append(f"Runtime directory does not exist: {target.runtime_dir.path}")

    if target.database.path.exists():
        if not verify_database_accessible(target.database.path):
            errors.append(f"Database file not accessible: {target.database.path}")
    else:
        warnings.append(f"Database file does not exist: {target.database.path}")

    for name in ("uploads_dir", "themes_dir", "backups_dir", "exports_dir"):
        rp = getattr(target, name)
        if rp.path.exists() and not verify_directory_writable(rp.path):
            errors.append(f"Directory not writable: {rp.path}")

    if target.log_dir.path.exists() and not verify_directory_writable(target.log_dir.path):
        errors.append(f"Log directory not writable: {target.log_dir.path}")

    if target.runtime_dir.path.exists() and not verify_directory_writable(target.runtime_dir.path):
        warnings.append(f"Runtime directory not writable: {target.runtime_dir.path}")

    for name, check in path_details.items():
        if check.is_symlink:
            warnings.append(f"Path {name} is a symlink pointing to {check.symlink_target}")

    return VerificationResult(
        success=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        path_checks=path_checks,
        path_details=path_details,
    )


def verify_production_ready(target: RuntimePaths) -> VerificationResult:
    result = verify_migration(target)

    if not target.database.path.exists():
        result.errors.append(
            f"Production database missing: {target.database.path}. "
            "Production mode requires an existing database."
        )
        result.success = False

    if target.database.path.exists():
        if not checkpoint_database(target.database.path):
            result.warnings.append(f"Could not checkpoint database WAL: {target.database.path}")

    for name in ("data_dir", "uploads_dir", "themes_dir", "backups_dir", "exports_dir"):
        detail = result.path_details.get(name)
        if detail is not None and detail.free_space_bytes is not None:
            if detail.free_space_bytes < 100 * 1024 * 1024:
                result.warnings.append(
                    f"Low disk space on {name}: {detail.free_space_bytes / (1024 * 1024):.1f} MB free"
                )

    return result
