"""Backup integrity verification module.

Provides functions to verify the integrity of SQLite backups using
 various checksums and validation techniques.
"""

import hashlib
import sqlite3
import zlib
from pathlib import Path
from typing import Optional, Any


def calculate_checksum(backup_path: Path) -> str:
    """Calculate SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(backup_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_backup_integrity(backup_path: Path) -> tuple[bool, str]:
    """Verify the integrity of a SQLite backup.

    Performs the following checks:
    1. File exists and is readable
    2. File is not empty
    3. File is a valid SQLite database (SQLite header check)
    4. SQLite database can be opened and queried
    5. Database is not corrupted (PRAGMA integrity_check)

    Args:
        backup_path: Path to the backup file (.db or .db.gz)

    Returns:
        Tuple of (is_valid, message)
    """
    if not backup_path.exists():
        return False, f"Backup file not found: {backup_path}"

    if backup_path.stat().st_size == 0:
        return False, "Backup file is empty"

    actual_path = backup_path
    if backup_path.suffix == ".gz":
        import gzip
        import tempfile
        import shutil

        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            with gzip.open(backup_path, "rb") as f_in:
                shutil.copyfileobj(f_in, tmp)
            actual_path = Path(tmp.name)

    try:
        with open(actual_path, "rb") as f:
            header = f.read(16)
            if not header.startswith(b"SQLite format 3"):
                return False, "Invalid SQLite header"

        conn = sqlite3.connect(str(actual_path))
        try:
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            if result[0] != "ok":
                return False, f"Database integrity check failed: {result[0]}"

            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            if not tables:
                return False, "Database contains no tables"

        finally:
            conn.close()

    except sqlite3.Error as e:
        return False, f"SQLite error: {e}"
    except Exception as e:
        return False, f"Verification error: {e}"
    finally:
        if actual_path != backup_path and actual_path.exists():
            actual_path.unlink()

    return True, f"Backup is valid ({len(tables)} tables)"


def verify_backup_set(backup_dir: Path, expected_count: Optional[int] = None) -> dict[str, Any]:
    """Verify all backups in a directory.

    Args:
        backup_dir: Directory containing backup files
        expected_count: If provided, verifies this many backups exist

    Returns:
        Dict with verification results
    """
    results: dict[str, Any] = {
        "total": 0,
        "valid": 0,
        "invalid": 0,
        "backups": [],
    }

    if not backup_dir.exists():
        results["error"] = f"Backup directory not found: {backup_dir}"
        return results

    backup_files = sorted(
        [
            f
            for f in backup_dir.iterdir()
            if f.is_file() and (f.name.startswith("blog_") and (f.suffix == ".db" or f.suffixes == [".db", ".gz"]))
        ],
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )

    results["total"] = len(backup_files)

    if expected_count is not None and len(backup_files) < expected_count:
        results["warning"] = f"Expected {expected_count} backups, found {len(backup_files)}"

    for backup_file in backup_files:
        is_valid, message = verify_backup_integrity(backup_file)
        results["backups"].append(
            {
                "name": backup_file.name,
                "valid": is_valid,
                "message": message,
                "size": backup_file.stat().st_size,
                "modified": backup_file.stat().st_mtime,
            }
        )
        if is_valid:
            results["valid"] += 1
        else:
            results["invalid"] += 1

    return results


def calculate_backup_crc(backup_path: Path) -> str:
    """Calculate CRC32 checksum of a backup file.

    Useful for quick comparison between backups.
    """
    if backup_path.suffix == ".gz":
        import gzip

        with gzip.open(backup_path, "rb") as f:
            return hex(zlib.crc32(f.read()) & 0xFFFFFFFF)

    with open(backup_path, "rb") as f:
        return hex(zlib.crc32(f.read()) & 0xFFFFFFFF)


def detect_backup_corruption(backup_path: Path) -> tuple[bool, str]:
    """Detect if a backup might be corrupted.

    Uses multiple heuristics to detect potential corruption:
    - File size anomalies (too small, too large)
    - Missing expected tables
    - SQLite header validation

    Args:
        backup_path: Path to the backup file

    Returns:
        Tuple of (is_corrupted, reason)
    """
    if not backup_path.exists():
        return True, "File does not exist"

    size = backup_path.stat().st_size
    if size < 512:
        return True, f"File too small ({size} bytes)"
    if size > 10 * 1024 * 1024 * 1024:
        return True, f"File suspiciously large ({size} bytes)"

    is_valid, message = verify_backup_integrity(backup_path)
    if not is_valid:
        return True, message

    return False, "No corruption detected"
