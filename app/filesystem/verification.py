from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from app.filesystem.layout import RuntimePaths


@dataclass
class VerificationResult:
    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    path_checks: dict[str, bool] = field(default_factory=dict)


def verify_database_accessible(db_path: Path) -> bool:
    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.execute("SELECT 1")
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


def verify_migration(target: RuntimePaths) -> VerificationResult:
    errors: list[str] = []
    warnings: list[str] = []
    path_checks: dict[str, bool] = {}

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
        path_checks[name] = rp.path.exists()

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

    return VerificationResult(
        success=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        path_checks=path_checks,
    )
