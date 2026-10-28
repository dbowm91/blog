"""Tests that new hard-coded production paths are not introduced.

Scans app/ and devlog_cli/ source files for patterns that should use
RuntimePaths or config-derived paths instead. Existing violations are
allowlisted; any new violation causes test failure.

Plan: F4 — runtime consumer audit.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
APP_DIR = REPO_ROOT / "app"
CLI_DIR = REPO_ROOT / "devlog_cli"

# Patterns that indicate hard-coded production paths
_DATA_FILENAME = r'(?:"blog\.db"|"backups"|DATA_BACKUP_DIR|"devlog\.sqlite3")'

_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "upload_folder_file",
        re.compile(r'os\.path\.join\(os\.path\.dirname\(__file__\).*"static".*"uploads"'),
        "Upload path derived from __file__; use RuntimePaths or app.config['UPLOAD_FOLDER']",
    ),
    (
        "instance_data_path",
        re.compile(rf"instance_path.*{_DATA_FILENAME}|{_DATA_FILENAME}.*instance_path"),
        "Data path derived from instance_path; use RuntimePaths (database.path, backups_dir.path)",
    ),
    (
        "hardcoded_data_filename",
        re.compile(r'"blog\.db"|"devlog\.sqlite3"'),
        "Hard-coded database filename; use RuntimePaths.database or DatabaseConfig",
    ),
]

# Files allowed to contain violations (allowlist)
_ALLOWLIST: set[str] = {
    # Legacy compat in app factory — config-derived fallback
    "app/__init__.py",
    # Storage backend — UPLOAD_FOLDER env var fallback
    "app/storage.py",
    # Scheduler — lock files in instance (runtime-only, no data)
    "app/scheduler.py",
    # Operations backup service — wraps existing backup logic
    "app/services/operations/backup.py",
    # Legacy backup service — same
    "app/services/backup.py",
    # Celery tasks — upload fallback, DB path, backup dir
    "app/tasks.py",
    # Admin helper — backup dir from instance_path
    "app/routes/admin/helpers/shared.py",
    # Config loader — _resolve_database_uri fallback (reads DATA_BACKUP_DIR)
    "app/config/loader.py",
    # Onboarding — candidate search paths (discovery, not production)
    "app/onboarding/state.py",
    # CLI config init — default output path
    "devlog_cli/commands/config.py",
    # Onboarding model — constructs database URI for config (legitimate: builds DevLogConfig)
    "app/onboarding/model.py",
    # Migration execution — checks DB filename for SQLite checkpoint (legitimate: runtime check)
    "app/filesystem/migration.py",
    # RuntimePaths — the single authority for the canonical database filename
    "app/filesystem/layout.py",
}


def _source_files() -> list[Path]:
    files: list[Path] = []
    for root in (APP_DIR, CLI_DIR):
        if not root.exists():
            continue
        for py in root.rglob("*.py"):
            if "__pycache__" in str(py):
                continue
            files.append(py)
    return files


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


class TestHardcodedPathGuard:
    """Ensure no new hard-coded production paths are introduced."""

    def test_no_unlisted_hardcoded_paths(self):
        violations: list[str] = []
        for py_file in _source_files():
            rel = _relative(py_file)
            if rel in _ALLOWLIST:
                continue
            content = py_file.read_text()
            for line_no, line in enumerate(content.splitlines(), start=1):
                for tag, pattern, description in _PATTERNS:
                    if pattern.search(line):
                        violations.append(
                            f"{rel}:{line_no} [{tag}] {description}\n  -> {line.strip()}"
                        )
        if violations:
            msg = (
                "New hard-coded production paths detected.\n"
                "Use RuntimePaths or config-derived paths instead.\n"
                "If this is intentional, add the file to _ALLOWLIST "
                "with a comment explaining why.\n\n" + "\n\n".join(violations)
            )
            pytest.fail(msg)

    def test_allowlist_covers_known_violations(self):
        """Verify the allowlist actually matches the expected files."""
        for allowed in _ALLOWLIST:
            path = REPO_ROOT / allowed
            assert path.exists(), f"Allowlist entry {allowed} does not exist"

    def test_pattern_effectiveness(self):
        """Verify each pattern matches at least one known violation."""
        all_content = ""
        for py_file in _source_files():
            all_content += py_file.read_text() + "\n"
        for tag, pattern, _ in _PATTERNS:
            assert pattern.search(all_content), (
                f"Pattern {tag} matches nothing in the codebase — remove it or update the regex"
            )
