from __future__ import annotations

from pathlib import Path

from app.config.model import CONFIG_VERSION
from app.config.migration import (
    MIGRATION_REGISTRY,
    MigrationStep,
    apply_migration,
    backup_config,
    detect_version,
    dry_run_migration,
    get_migration_plan,
    needs_migration,
)


class TestDetectVersion:
    def test_with_version(self) -> None:
        assert detect_version({"config_version": 1}) == 1

    def test_without_version(self) -> None:
        assert detect_version({}) is None

    def test_non_integer_version(self) -> None:
        assert detect_version({"config_version": "abc"}) is None

    def test_float_version(self) -> None:
        assert detect_version({"config_version": 1.5}) == 1

    def test_zero_version(self) -> None:
        assert detect_version({"config_version": 0}) == 0


class TestNeedsMigration:
    def test_no_version_needs_migration(self) -> None:
        assert needs_migration({}) is True

    def test_old_version_needs_migration(self) -> None:
        assert needs_migration({"config_version": 0}) is True

    def test_current_version_no_migration(self) -> None:
        assert needs_migration({"config_version": CONFIG_VERSION}) is False

    def test_future_version_no_migration(self) -> None:
        assert needs_migration({"config_version": CONFIG_VERSION + 1}) is False


class TestGetMigrationPlan:
    def test_no_version_starts_from_zero(self) -> None:
        plan = get_migration_plan({})
        for step in plan:
            assert step.from_version >= 0

    def test_current_version_empty_plan(self) -> None:
        plan = get_migration_plan({"config_version": CONFIG_VERSION})
        assert plan == []

    def test_registry_steps_are_migration_steps(self) -> None:
        for step in MIGRATION_REGISTRY:
            assert isinstance(step, MigrationStep)


class TestDryRunMigration:
    def test_returns_expected_keys(self) -> None:
        result = dry_run_migration({})
        assert "current_version" in result
        assert "target_version" in result
        assert "steps" in result
        assert "needs_migration" in result

    def test_current_version_is_none_when_missing(self) -> None:
        result = dry_run_migration({})
        assert result["current_version"] is None

    def test_target_version_matches_config_version(self) -> None:
        result = dry_run_migration({})
        assert result["target_version"] == CONFIG_VERSION

    def test_steps_are_dicts(self) -> None:
        result = dry_run_migration({})
        for step in result["steps"]:
            assert "from" in step
            assert "to" in step
            assert "desc" in step


class TestBackupConfig:
    def test_creates_backup_file(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text("[app]\ntitle = 'test'\n")
        backup_path = backup_config(config_file)
        assert backup_path.exists()
        assert backup_path != config_file
        assert backup_path.name.startswith("config.toml.backup.")
        assert backup_path.read_text() == config_file.read_text()

    def test_backup_in_same_directory(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text("test")
        backup_path = backup_config(config_file)
        assert backup_path.parent == tmp_path

    def test_backup_filename_contains_timestamp(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text("test")
        backup_path = backup_config(config_file)
        assert "T" in backup_path.name
        assert "Z" in backup_path.name


class TestApplyMigration:
    def test_returns_copy_of_raw(self) -> None:
        raw: dict = {"app": {"title": "Test"}}
        result = apply_migration(raw)
        assert result == raw

    def test_preserves_existing_data(self) -> None:
        raw: dict = {"app": {"title": "Test"}, "config_version": 0}
        result = apply_migration(raw)
        assert result["app"] == {"title": "Test"}

    def test_does_not_mutate_input(self) -> None:
        raw: dict = {"config_version": 0}
        original = dict(raw)
        result = apply_migration(raw)
        assert raw == original
        assert result["config_version"] == 0

    def test_current_version_unchanged(self) -> None:
        raw: dict = {"config_version": CONFIG_VERSION}
        result = apply_migration(raw)
        assert result["config_version"] == CONFIG_VERSION

    def test_empty_registry_returns_unchanged(self) -> None:
        raw: dict = {}
        result = apply_migration(raw)
        assert result == {}
