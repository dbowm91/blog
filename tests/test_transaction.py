"""Tests for transaction module."""

import pytest


class TestTransactional:
    """Tests for transactional decorator."""

    def test_transactional_calls_function_and_returns_result(self):
        """Test that transactional decorator calls the wrapped function."""
        from app.transaction import transactional

        @transactional
        def sample_function(x, y):
            return x + y

        result = sample_function(1, 2)
        assert result == 3

    def test_transactional_preserves_function_metadata(self):
        """Test that transactional preserves wrapped function metadata."""
        from app.transaction import transactional

        @transactional
        def named_function():
            pass

        assert named_function.__name__ == "named_function"


class TestCommitWithRollback:
    """Tests for commit_with_rollback function."""

    def test_commit_with_rollback_success(self, db, admin_user):
        """Test successful commit with rollback helper."""
        from app.transaction import commit_with_rollback

        admin_user.email = "success@example.com"
        commit_with_rollback()

        db.session.expire(admin_user)
        admin_user = db.session.get(type(admin_user), admin_user.id)
        assert admin_user.email == "success@example.com"


class TestDbTransaction:
    """Tests for db_transaction context manager."""

    def test_db_transaction_commits_on_success(self, db, admin_user):
        """Test db_transaction commits on successful block."""
        from app.transaction import db_transaction

        with db_transaction():
            admin_user.email = "context@example.com"
            db.session.flush()

        db.session.expire(admin_user)
        admin_user = db.session.get(type(admin_user), admin_user.id)
        assert admin_user.email == "context@example.com"

    def test_db_transaction_preserves_exception(self, db):
        """Test db_transaction re-raises the original exception."""
        from app.transaction import db_transaction

        with pytest.raises(ValueError):
            with db_transaction():
                raise ValueError("test error")


class TestCommitWithSlugRetry:
    """Tests for commit_with_slug_retry function."""

    def test_commit_with_slug_retry_success(self, db, admin_user):
        """Test successful commit with slug retry."""
        from app.transaction import commit_with_slug_retry

        admin_user.email = "retry@example.com"
        result = commit_with_slug_retry(admin_user, "admin")

        assert result is True
        db.session.expire(admin_user)
        admin_user = db.session.get(type(admin_user), admin_user.id)
        assert admin_user.email == "retry@example.com"
