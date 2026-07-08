import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")

from unittest.mock import patch

from app.db_utils import get_database_dialect, is_sqlite_database


class TestDatabaseDialectHelpers:
    def test_get_database_dialect_returns_sqlite(self, db):
        assert get_database_dialect() == "sqlite"

    def test_is_sqlite_database_true_for_sqlite(self, db):
        assert is_sqlite_database() is True

    @patch("app.db_utils.db")
    def test_get_database_dialect_returns_postgresql(self, mock_db):
        mock_db.engine.dialect.name = "postgresql"
        assert get_database_dialect() == "postgresql"

    @patch("app.db_utils.db")
    def test_is_sqlite_database_false_for_postgresql(self, mock_db):
        mock_db.engine.dialect.name = "postgresql"
        assert is_sqlite_database() is False

    @patch("app.db_utils.db")
    def test_get_database_dialect_unknown_on_exception(self, mock_db):
        del mock_db.engine
        assert get_database_dialect() == "unknown"
