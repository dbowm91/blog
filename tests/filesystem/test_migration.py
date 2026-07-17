from __future__ import annotations

from pathlib import Path

import pytest

from app.filesystem.layout import InstallMode, RuntimePaths
from app.filesystem.migration import (
    MigrationAction,
    MigrationStep,
    execute_migration,
    plan_migration,
)


def _make_source(tmp_path):
    data = tmp_path / "source-data"
    data.mkdir()
    (data / "uploads").mkdir()
    (data / "themes").mkdir()
    (data / "backups").mkdir()
    (data / "exports").mkdir()
    (data / "devlog.sqlite3").touch()
    logs = tmp_path / "source-logs"
    logs.mkdir()
    runtime = tmp_path / "source-runtime"
    runtime.mkdir()
    config = tmp_path / "source-config.toml"
    config.touch()
    env = tmp_path / ".env"
    env.touch()
    return RuntimePaths.resolve(
        InstallMode.DEVELOPMENT,
        data_dir=data,
        uploads_dir=data / "uploads",
        themes_dir=data / "themes",
        backups_dir=data / "backups",
        exports_dir=data / "exports",
        log_dir=logs,
        runtime_dir=runtime,
        config_file=config,
        env_file=env,
    )


def _make_target(tmp_path):
    data = tmp_path / "target-data"
    logs = tmp_path / "target-logs"
    runtime = tmp_path / "target-runtime"
    config = tmp_path / "target-config.toml"
    env = tmp_path / "target.env"
    return RuntimePaths.resolve(
        InstallMode.DEVELOPMENT,
        data_dir=data,
        uploads_dir=data / "uploads",
        themes_dir=data / "themes",
        backups_dir=data / "backups",
        exports_dir=data / "exports",
        log_dir=logs,
        runtime_dir=runtime,
        config_file=config,
        env_file=env,
    )


class TestMigrationAction:
    def test_all_actions_exist(self):
        actions = {a.value for a in MigrationAction}
        assert actions == {"copy", "move", "skip", "conflict", "create_dir"}


class TestMigrationStep:
    def test_frozen(self):
        step = MigrationStep(
            action=MigrationAction.SKIP,
            source=Path("/src"),
            target=Path("/dst"),
            description="test",
        )
        with pytest.raises(AttributeError):
            step.action = MigrationAction.MOVE

    def test_source_can_be_none(self):
        step = MigrationStep(
            action=MigrationAction.CREATE_DIR,
            source=None,
            target=Path("/dst"),
            description="create",
        )
        assert step.source is None


class TestPlanMigration:
    def test_skip_when_source_missing(self, tmp_path):
        source = _make_source(tmp_path)
        source.config_file.path.unlink()
        source.env_file.path.unlink()
        target = _make_target(tmp_path)
        plan = plan_migration(source, target)
        config_steps = [s for s in plan.steps if "Config file" in s.description]
        assert len(config_steps) == 1
        assert config_steps[0].action == MigrationAction.SKIP

    def test_move_when_source_exists(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        source.config_file.path.write_text("config content")
        plan = plan_migration(source, target)
        config_steps = [s for s in plan.steps if "Config file" in s.description]
        assert len(config_steps) == 1
        assert config_steps[0].action == MigrationAction.MOVE

    def test_conflict_when_target_exists(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        source.config_file.path.write_text("content")
        target.config_file.path.parent.mkdir(parents=True, exist_ok=True)
        target.config_file.path.write_text("existing")
        plan = plan_migration(source, target)
        config_steps = [s for s in plan.steps if "Config file" in s.description]
        assert config_steps[0].action == MigrationAction.CONFLICT

    def test_create_dir_when_target_parent_missing(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        (source.uploads_dir.path / "photo.jpg").touch()
        plan = plan_migration(source, target)
        create_steps = [s for s in plan.steps if s.action == MigrationAction.CREATE_DIR]
        upload_creates = [s for s in create_steps if "Uploads" in s.description]
        assert len(upload_creates) >= 1

    def test_dir_transfer_copies_files(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        (source.uploads_dir.path / "image.png").touch()
        plan = plan_migration(source, target)
        file_steps = [
            s for s in plan.steps if s.action == MigrationAction.MOVE and "Uploads" in s.description
        ]
        assert len(file_steps) == 1
        assert file_steps[0].source == (source.uploads_dir.path / "image.png")

    def test_requires_downtime_true_when_moves(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        source.config_file.path.write_text("content")
        plan = plan_migration(source, target)
        assert plan.requires_downtime is True

    def test_requires_downtime_false_when_all_skip(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        plan = plan_migration(source, target)
        has_move_or_copy = any(
            s.action in (MigrationAction.MOVE, MigrationAction.COPY) for s in plan.steps
        )
        assert plan.requires_downtime == has_move_or_copy

    def test_identical_data_dir_warning(self, tmp_path):
        shared = tmp_path / "shared"
        shared.mkdir()
        (shared / "uploads").mkdir()
        (shared / "themes").mkdir()
        (shared / "backups").mkdir()
        (shared / "exports").mkdir()
        config = tmp_path / "config.toml"
        env = tmp_path / ".env"
        logs = tmp_path / "logs"
        runtime = tmp_path / "runtime"
        paths = RuntimePaths.resolve(
            InstallMode.DEVELOPMENT,
            data_dir=shared,
            uploads_dir=shared / "uploads",
            themes_dir=shared / "themes",
            backups_dir=shared / "backups",
            exports_dir=shared / "exports",
            log_dir=logs,
            runtime_dir=runtime,
            config_file=config,
            env_file=env,
        )
        plan = plan_migration(paths, paths)
        assert any("identical" in w.lower() for w in plan.warnings)

    def test_conflict_warning(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        source.config_file.path.write_text("content")
        target.config_file.path.parent.mkdir(parents=True, exist_ok=True)
        target.config_file.path.write_text("existing")
        plan = plan_migration(source, target)
        assert any("already exist" in w.lower() for w in plan.warnings)

    def test_source_and_target_modes_set(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        plan = plan_migration(source, target)
        assert plan.source_mode == InstallMode.DEVELOPMENT
        assert plan.target_mode == InstallMode.DEVELOPMENT

    def test_explicit_modes(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        plan = plan_migration(
            source,
            target,
            source_mode=InstallMode.SYSTEM,
            target_mode=InstallMode.DOCKER,
        )
        assert plan.source_mode == InstallMode.SYSTEM
        assert plan.target_mode == InstallMode.DOCKER

    def test_env_file_transfer(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        source.env_file.path.write_text("SECRET_KEY=test")
        plan = plan_migration(source, target)
        env_steps = [s for s in plan.steps if "Env file" in s.description]
        assert len(env_steps) == 1
        assert env_steps[0].action == MigrationAction.MOVE

    def test_database_transfer(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        source.database.path.write_bytes(b"sqlite data")
        plan = plan_migration(source, target)
        db_steps = [s for s in plan.steps if "Database" in s.description]
        assert len(db_steps) == 1
        assert db_steps[0].action == MigrationAction.MOVE

    def test_metadata_transfer(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        source.installation_metadata.path.parent.mkdir(parents=True, exist_ok=True)
        source.installation_metadata.path.write_text("{}")
        plan = plan_migration(source, target)
        meta_steps = [s for s in plan.steps if "Installation metadata" in s.description]
        assert len(meta_steps) == 1

    def test_include_logs(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        (source.log_dir.path / "app.log").touch()
        plan_with = plan_migration(source, target, include_logs=True)
        plan_without = plan_migration(source, target, include_logs=False)
        log_steps_with = [s for s in plan_with.steps if "Logs" in s.description]
        log_steps_without = [s for s in plan_without.steps if "Logs" in s.description]
        assert len(log_steps_with) > 0
        assert len(log_steps_without) == 0

    def test_nested_dir_transfer(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        nested = source.uploads_dir.path / "2024" / "01"
        nested.mkdir(parents=True)
        (nested / "photo.jpg").touch()
        plan = plan_migration(source, target)
        upload_steps = [
            s for s in plan.steps if "Uploads" in s.description and s.source is not None
        ]
        assert any("photo.jpg" in str(s.source) for s in upload_steps)

    def test_steps_list(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        plan = plan_migration(source, target)
        assert isinstance(plan.steps, list)
        assert all(isinstance(s, MigrationStep) for s in plan.steps)

    def test_no_logs_by_default(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        (source.log_dir.path / "app.log").touch()
        plan = plan_migration(source, target, include_logs=False)
        log_steps = [s for s in plan.steps if "Logs" in s.description]
        assert len(log_steps) == 0


class TestExecuteMigration:
    def test_dry_run_no_changes(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        source.config_file.path.write_text("config content")
        plan = plan_migration(source, target)
        result = execute_migration(plan, dry_run=True)
        assert result.ok
        assert result.completed_steps == len(plan.steps)
        assert not target.config_file.path.exists()

    def test_execute_moves_config(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        source.config_file.path.write_text("config content")
        plan = plan_migration(source, target)
        result = execute_migration(plan)
        assert result.ok
        assert target.config_file.path.exists()
        assert target.config_file.path.read_text() == "config content"

    def test_execute_skips_missing_source(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        source.config_file.path.unlink()
        plan = plan_migration(source, target)
        result = execute_migration(plan)
        assert result.ok

    def test_execute_stops_on_conflict(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        source.config_file.path.write_text("new")
        target.config_file.path.parent.mkdir(parents=True, exist_ok=True)
        target.config_file.path.write_text("existing")
        plan = plan_migration(source, target)
        result = execute_migration(plan, stop_on_conflict=True)
        assert not result.ok
        assert len(result.errors) > 0

    def test_execute_continues_on_conflict(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        source.config_file.path.write_text("new")
        target.config_file.path.parent.mkdir(parents=True, exist_ok=True)
        target.config_file.path.write_text("existing")
        (source.env_file.path).write_text("SECRET_KEY=test")
        plan = plan_migration(source, target)
        result = execute_migration(plan, stop_on_conflict=False)
        assert result.ok

    def test_execute_creates_directories(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        (source.uploads_dir.path / "photo.jpg").touch()
        plan = plan_migration(source, target)
        result = execute_migration(plan)
        assert result.ok
        assert (target.uploads_dir.path / "photo.jpg").exists()

    def test_execute_preserves_source_on_skip(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        plan = plan_migration(source, target)
        result = execute_migration(plan)
        assert result.ok
        assert source.data_dir.path.exists()

    def test_execution_result_fields(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        plan = plan_migration(source, target)
        result = execute_migration(plan, dry_run=True)
        assert hasattr(result, "ok")
        assert hasattr(result, "completed_steps")
        assert hasattr(result, "total_steps")
        assert hasattr(result, "errors")
        assert hasattr(result, "completed_paths")

    def test_execute_moves_database(self, tmp_path):
        source = _make_source(tmp_path)
        target = _make_target(tmp_path)
        source.database.path.write_bytes(b"sqlite data")
        plan = plan_migration(source, target)
        result = execute_migration(plan)
        assert result.ok
        assert target.database.path.exists()
        assert target.database.path.read_bytes() == b"sqlite data"
