"""Tests for path lifecycle categories.

Plan: F12 — backup and uninstall integration contracts.
"""

from __future__ import annotations

from app.filesystem.lifecycle import (
    CATEGORY_POLICIES,
    RUNTIME_PATH_CATEGORIES,
    LifecyclePolicy,
    PathCategory,
)


class TestPathCategory:
    def test_all_categories_defined(self):
        expected = {
            "code",
            "configuration",
            "secrets",
            "persistent_data",
            "user_content",
            "backups",
            "logs",
            "runtime",
            "installation_metadata",
        }
        assert {c.value for c in PathCategory} == expected

    def test_category_count(self):
        assert len(PathCategory) == 9


class TestLifecyclePolicy:
    def test_all_categories_have_policies(self):
        for cat in PathCategory:
            assert cat in CATEGORY_POLICIES, f"Missing policy for {cat}"

    def test_policy_fields(self):
        for policy in CATEGORY_POLICIES.values():
            assert isinstance(policy, LifecyclePolicy)
            assert isinstance(policy.included_in_backup, bool)
            assert isinstance(policy.preserved_on_uninstall, bool)
            assert isinstance(policy.removed_on_purge, bool)
            assert isinstance(policy.safe_to_regenerate, bool)
            assert isinstance(policy.ownership_note, str)

    def test_code_not_in_backup(self):
        assert CATEGORY_POLICIES[PathCategory.CODE].included_in_backup is False

    def test_code_safe_to_regenerate(self):
        assert CATEGORY_POLICIES[PathCategory.CODE].safe_to_regenerate is True

    def test_configuration_in_backup(self):
        assert CATEGORY_POLICIES[PathCategory.CONFIGURATION].included_in_backup is True

    def test_configuration_preserved_on_uninstall(self):
        assert CATEGORY_POLICIES[PathCategory.CONFIGURATION].preserved_on_uninstall is True

    def test_secrets_in_backup(self):
        assert CATEGORY_POLICIES[PathCategory.SECRETS].included_in_backup is True

    def test_persistent_data_in_backup(self):
        assert CATEGORY_POLICIES[PathCategory.PERSISTENT_DATA].included_in_backup is True

    def test_user_content_in_backup(self):
        assert CATEGORY_POLICIES[PathCategory.USER_CONTENT].included_in_backup is True

    def test_backups_not_in_backup(self):
        assert CATEGORY_POLICIES[PathCategory.BACKUPS].included_in_backup is False

    def test_backups_preserved_on_uninstall(self):
        assert CATEGORY_POLICIES[PathCategory.BACKUPS].preserved_on_uninstall is True

    def test_logs_not_in_backup(self):
        assert CATEGORY_POLICIES[PathCategory.LOGS].included_in_backup is False

    def test_logs_not_preserved_on_uninstall(self):
        assert CATEGORY_POLICIES[PathCategory.LOGS].preserved_on_uninstall is False

    def test_runtime_not_in_backup(self):
        assert CATEGORY_POLICIES[PathCategory.RUNTIME].included_in_backup is False

    def test_runtime_safe_to_regenerate(self):
        assert CATEGORY_POLICIES[PathCategory.RUNTIME].safe_to_regenerate is True

    def test_metadata_in_backup(self):
        assert CATEGORY_POLICIES[PathCategory.INSTALLATION_METADATA].included_in_backup is True

    def test_everything_removed_on_purge(self):
        for cat, policy in CATEGORY_POLICIES.items():
            assert policy.removed_on_purge is True, f"{cat} should be removed on purge"


class TestRuntimePathCategories:
    def test_all_mapped(self):
        expected_fields = {
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
        }
        assert set(RUNTIME_PATH_CATEGORIES.keys()) == expected_fields

    def test_database_is_persistent_data(self):
        assert RUNTIME_PATH_CATEGORIES["database"] == PathCategory.PERSISTENT_DATA

    def test_uploads_is_user_content(self):
        assert RUNTIME_PATH_CATEGORIES["uploads_dir"] == PathCategory.USER_CONTENT

    def test_backups_is_backups(self):
        assert RUNTIME_PATH_CATEGORIES["backups_dir"] == PathCategory.BACKUPS

    def test_config_is_configuration(self):
        assert RUNTIME_PATH_CATEGORIES["config_file"] == PathCategory.CONFIGURATION

    def test_env_is_secrets(self):
        assert RUNTIME_PATH_CATEGORIES["env_file"] == PathCategory.SECRETS

    def test_log_is_logs(self):
        assert RUNTIME_PATH_CATEGORIES["log_dir"] == PathCategory.LOGS

    def test_runtime_is_runtime(self):
        assert RUNTIME_PATH_CATEGORIES["runtime_dir"] == PathCategory.RUNTIME
