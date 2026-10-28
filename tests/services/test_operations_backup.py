"""Tests for app.services.operations.backup operational service."""

from __future__ import annotations

import os
import sqlite3
from unittest.mock import patch

import pytest

from app.services.backup import resolve_backup_dir, resolve_database_file
from app.services.operations.results import (
    BackupCreateResult,
    BackupVerifyResult,
    BackupInspectResult,
)


@pytest.fixture()
def backup_dir(app):
    """Return a temporary backup directory within the app instance."""
    d = resolve_backup_dir(app)
    os.makedirs(d, exist_ok=True)
    return d


@pytest.fixture()
def db_path(app):
    """Return the path to the test database."""
    return resolve_database_file(app)


class TestCreateBackupOperation:
    def test_create_backup_success(self, app, db_path, backup_dir):
        from app.services.operations.backup import create_backup_operation

        with app.app_context():
            result = create_backup_operation(keep=7)

        assert isinstance(result, BackupCreateResult)
        assert result.ok is True
        assert result.code == "backup.create.ok"
        assert result.path != ""
        assert os.path.exists(result.path)
        assert result.verified is True

    def test_create_backup_with_compression(self, app, db_path, backup_dir):
        from app.services.operations.backup import create_backup_operation

        with app.app_context():
            result = create_backup_operation(compress=True, keep=7)

        assert isinstance(result, BackupCreateResult)
        assert result.ok is True
        assert result.path.endswith(".db.gz")
        assert result.details["compress"] is True
        assert os.path.exists(result.path)

    def test_create_backup_db_not_found(self, app):
        from app.services.operations.backup import create_backup_operation

        with (
            app.app_context(),
            patch("app.services.operations.backup.os.path.exists", return_value=False),
        ):
            result = create_backup_operation()

        assert isinstance(result, BackupCreateResult)
        assert result.ok is False
        assert result.code == "backup.create.db_not_found"
        assert "Database not found" in result.summary

    def test_create_backup_encryption_dependency_unavailable(self, app, db_path):
        from app.services.operations.backup import create_backup_operation

        with (
            app.app_context(),
            patch("app.backup_encryption.is_encryption_available", return_value=False),
        ):
            result = create_backup_operation(encrypt=True)

        assert isinstance(result, BackupCreateResult)
        assert result.ok is False
        assert result.code == "backup.create.encryption_unavailable"


class TestVerifyBackup:
    def test_verify_backup_valid(self, app, backup_dir):
        from app.services.operations.backup import verify_backup

        import uuid

        backup_path = os.path.join(backup_dir, f"blog_verify_{uuid.uuid4().hex[:8]}.db")
        conn = sqlite3.connect(backup_path)
        conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        result = verify_backup(backup_path)

        assert isinstance(result, BackupVerifyResult)
        assert result.ok is True
        assert result.valid is True
        assert result.path == backup_path
        assert "Backup is valid" in result.summary

    def test_verify_backup_missing(self):
        from app.services.operations.backup import verify_backup

        result = verify_backup("/nonexistent/path/backup.db")

        assert isinstance(result, BackupVerifyResult)
        assert result.ok is False
        assert result.valid is False
        assert result.code == "backup.verify.not_found"

    def test_verify_backup_empty(self, app, backup_dir):
        from app.services.operations.backup import verify_backup

        backup_path = os.path.join(backup_dir, "empty.db")
        with open(backup_path, "w") as f:
            f.write("")

        result = verify_backup(backup_path)

        assert isinstance(result, BackupVerifyResult)
        assert result.ok is False
        assert result.valid is False
        assert result.code == "backup.verify.empty"

    def test_verify_backup_unreadable(self, app, backup_dir):
        from app.services.operations.backup import verify_backup

        backup_path = os.path.join(backup_dir, "unreadable.db")
        with open(backup_path, "w") as f:
            f.write("not a database")

        result = verify_backup(backup_path)

        assert isinstance(result, BackupVerifyResult)
        assert result.path == backup_path
        assert result.valid is True
        assert "could not be fully verified" in result.summary


class TestInspectBackup:
    def test_inspect_nonexistent(self):
        from app.services.operations.backup import inspect_backup

        result = inspect_backup("/nonexistent/backup.db")

        assert isinstance(result, BackupInspectResult)
        assert result.ok is False
        assert result.code == "backup.inspect.not_found"

    def test_inspect_empty_file(self, app, backup_dir):
        from app.services.operations.backup import inspect_backup

        path = os.path.join(backup_dir, "empty_inspect.db")
        with open(path, "w") as f:
            f.write("")

        result = inspect_backup(path)

        assert isinstance(result, BackupInspectResult)
        assert result.ok is False
        assert result.code == "backup.inspect.empty"
        assert result.file_size == 0

    def test_inspect_sqlite_file(self, app, backup_dir):
        from app.services.operations.backup import inspect_backup

        path = os.path.join(backup_dir, "sqlite_inspect.db")
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE IF NOT EXISTS test_inspect (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        result = inspect_backup(path)

        assert isinstance(result, BackupInspectResult)
        assert result.ok is True
        assert result.code == "backup.inspect.ok"
        assert result.is_sqlite is True
        assert result.file_size > 0
        assert "SQLite" in result.summary

    def test_inspect_gzip_file(self, app, backup_dir):
        import gzip

        from app.services.operations.backup import inspect_backup

        path = os.path.join(backup_dir, "compressed_inspect.db.gz")
        with gzip.open(path, "wb") as f:
            f.write(b"not really a db but gzipped")

        result = inspect_backup(path)

        assert isinstance(result, BackupInspectResult)
        assert result.ok is True
        assert result.is_compressed is True
        assert "gzip" in result.summary.lower()

    def test_inspect_unknown_format(self, app, backup_dir):
        from app.services.operations.backup import inspect_backup

        path = os.path.join(backup_dir, "unknown_inspect.dat")
        with open(path, "wb") as f:
            f.write(b"\x00\x01\x02\x03some data")

        result = inspect_backup(path)

        assert isinstance(result, BackupInspectResult)
        assert result.ok is True
        assert result.is_sqlite is False
        assert result.is_compressed is False
        assert result.file_size > 0
