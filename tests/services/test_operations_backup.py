"""Tests for app.services.operations.backup operational service."""

from __future__ import annotations

import os
import sqlite3
from unittest.mock import patch

import pytest

from app.services.operations.results import BackupCreateResult, BackupVerifyResult


@pytest.fixture()
def backup_dir(app):
    """Return a temporary backup directory within the app instance."""
    d = os.path.join(app.instance_path, "backups")
    os.makedirs(d, exist_ok=True)
    return d


@pytest.fixture()
def db_path(app):
    """Return the path to the test database."""
    return os.path.join(app.instance_path, "blog.db")


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
