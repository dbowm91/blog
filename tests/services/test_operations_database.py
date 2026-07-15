"""Tests for app.services.operations.database — database and search service functions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from sqlalchemy.exc import OperationalError

from app.services.operations.database import (
    check_database_integrity,
    rebuild_search_index,
    get_migration_status,
    run_migrations,
)
from app.services.operations.results import (
    DatabaseCheckResult,
    SearchRebuildResult,
    MigrationStatusResult,
)


class TestCheckDatabaseIntegrity:
    """Tests for check_database_integrity()."""

    def test_sqlite_healthy(self, app, db):
        """Integrity check passes on a clean SQLite database."""
        with app.app_context():
            result = check_database_integrity()

        assert isinstance(result, DatabaseCheckResult)
        assert result.ok is True
        assert result.healthy is True
        assert result.code == "db.integrity.ok"
        assert result.backend == "sqlite"
        assert "passed" in result.summary.lower()

    def test_sqlite_corruption(self, app, db):
        """Integrity check returns failure when PRAGMA reports corruption."""
        with app.app_context():
            with patch("app.services.operations.database.db") as mock_db:
                mock_result = MagicMock()
                mock_result.scalar.return_value = "corruption error"
                mock_db.session.execute.return_value = mock_result
                mock_db.session.remove = MagicMock()

                result = check_database_integrity()

        assert isinstance(result, DatabaseCheckResult)
        assert result.ok is False
        assert result.healthy is False
        assert result.code == "db.integrity.failed"
        assert "corruption" in result.summary.lower()
        assert result.details["result"] == "corruption error"
        assert any("backup" in r.lower() for r in result.remediation)

    def test_sqlite_execute_error(self, app, db):
        """Integrity check returns failure when PRAGMA raises an exception."""
        with app.app_context():
            with patch("app.services.operations.database.db") as mock_db:
                mock_db.session.execute.side_effect = OperationalError(
                    "database is locked", None, None
                )
                mock_db.session.remove = MagicMock()

                result = check_database_integrity()

        assert isinstance(result, DatabaseCheckResult)
        assert result.ok is False
        assert result.healthy is False
        assert result.code == "db.integrity.error"
        assert "database is locked" in result.summary

    def test_non_sqlite_unsupported(self, app, db):
        """Non-SQLite databases return unsupported status."""
        with app.app_context():
            with patch("app.services.operations.database.is_sqlite_database", return_value=False):
                with patch(
                    "app.services.operations.database.get_database_dialect",
                    return_value="postgresql",
                ):
                    result = check_database_integrity()

        assert isinstance(result, DatabaseCheckResult)
        assert result.ok is False
        assert result.healthy is False
        assert result.code == "db.integrity.unsupported"
        assert result.backend == "postgresql"
        assert "postgresql" in result.summary.lower()
        assert len(result.remediation) > 0


class TestRebuildSearchIndex:
    """Tests for rebuild_search_index()."""

    def test_rebuild_success(self, app, db, sample_post):
        """Search rebuild succeeds and returns indexed post count."""
        with app.app_context():
            result = rebuild_search_index()

        assert isinstance(result, SearchRebuildResult)
        assert result.ok is True
        assert result.code == "db.search.rebuilt"
        assert result.indexed_count >= 1
        assert "rebuilt" in result.summary.lower()

    def test_rebuild_no_posts(self, app, db):
        """Search rebuild succeeds with zero posts."""
        with app.app_context():
            result = rebuild_search_index()

        assert isinstance(result, SearchRebuildResult)
        assert result.ok is True
        assert result.indexed_count == 0
        assert "0 post(s)" in result.summary

    def test_rebuild_failure(self, app, db):
        """Search rebuild handles rebuild_fts failure gracefully."""
        with app.app_context():
            with patch(
                "app.services.operations.database.rebuild_fts",
                side_effect=Exception("FTS init failed"),
            ):
                result = rebuild_search_index()

        assert isinstance(result, SearchRebuildResult)
        assert result.ok is False
        assert result.code == "db.search.rebuild_error"
        assert result.indexed_count == 0
        assert "FTS init failed" in result.summary

    def test_rebuild_count_error(self, app, db, sample_post):
        """Search rebuild handles post-count failure after FTS rebuild."""
        with app.app_context():
            with patch("app.services.operations.database.db") as mock_db:
                mock_db.session.execute.side_effect = OperationalError(
                    "table not found", None, None
                )
                mock_db.session.remove = MagicMock()

                result = rebuild_search_index()

        assert isinstance(result, SearchRebuildResult)
        assert result.indexed_count == 0


class TestGetMigrationStatus:
    def test_get_status_success(self, app, db):
        with app.app_context():
            result = get_migration_status()

        assert isinstance(result, MigrationStatusResult)
        assert result.ok is True
        assert result.code == "db.migration.status"

    def test_get_status_failure(self, app, db):
        with app.app_context():
            with patch(
                "flask_migrate.current",
                side_effect=Exception("No migration context"),
            ):
                result = get_migration_status()

        assert isinstance(result, MigrationStatusResult)
        assert result.ok is False
        assert result.code == "db.migration.status_error"


class TestRunMigrations:
    def test_run_migrations_success(self, app, db):
        with app.app_context():
            with patch("flask_migrate.upgrade") as mock_upgrade:
                with patch("flask_migrate.current", return_value="abc123"):
                    result = run_migrations()

        assert isinstance(result, MigrationStatusResult)
        assert result.ok is True
        assert result.code == "db.migration.applied"
        mock_upgrade.assert_called_once()

    def test_run_migrations_failure(self, app, db):
        with app.app_context():
            with patch(
                "flask_migrate.upgrade",
                side_effect=Exception("Migration failed"),
            ):
                result = run_migrations()

        assert isinstance(result, MigrationStatusResult)
        assert result.ok is False
        assert result.code == "db.migration.failed"
        assert "Migration failed" in result.summary
