"""Regression tests for backup path resolution.

The app stores its database at ``<data_dir>/devlog.sqlite3``. The backup
services used to look for ``instance/blog.db`` and silently skipped the
scheduled backup because the file was never there.
"""

from __future__ import annotations

from pathlib import Path

from app.services.backup import resolve_backup_dir, resolve_database_file


class _FakeApp:
    def __init__(self, uri: str, instance_path: str) -> None:
        self.config = {"SQLALCHEMY_DATABASE_URI": uri}
        self.instance_path = instance_path


class TestResolveDatabaseFile:
    def test_uses_the_configured_sqlite_uri(self, tmp_path: Path) -> None:
        db = tmp_path / "devlog.sqlite3"
        app = _FakeApp(f"sqlite:///{db}", str(tmp_path / "instance"))

        assert resolve_database_file(app) == str(db)

    def test_does_not_fall_back_to_instance_blog_db(self, tmp_path: Path) -> None:
        db = tmp_path / "data" / "devlog.sqlite3"
        app = _FakeApp(f"sqlite:///{db}", str(tmp_path / "instance"))

        resolved = resolve_database_file(app)

        assert resolved is not None
        assert "blog.db" not in resolved

    def test_returns_none_for_a_non_sqlite_database(self) -> None:
        app = _FakeApp("postgresql://user@host/blog", "/tmp/instance")

        assert resolve_database_file(app) is None


class TestResolveBackupDir:
    def test_relative_backup_dir_resolves_beside_the_database(self, tmp_path: Path) -> None:
        db = tmp_path / "data" / "devlog.sqlite3"
        app = _FakeApp(f"sqlite:///{db}", str(tmp_path / "instance"))

        resolved = resolve_backup_dir(app)

        assert resolved == str(tmp_path / "data" / "backups")

    def test_absolute_backup_dir_is_kept(self, tmp_path: Path) -> None:
        db = tmp_path / "data" / "devlog.sqlite3"
        app = _FakeApp(f"sqlite:///{db}", str(tmp_path / "instance"))

        with _patched_backup_dir("/srv/backups"):
            assert resolve_backup_dir(app) == "/srv/backups"


def _patched_backup_dir(value: str):
    from unittest.mock import patch

    return patch("app.config.DATA_BACKUP_DIR", value)
