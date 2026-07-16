from __future__ import annotations

import sqlite3

from app.filesystem.layout import InstallMode, RuntimePaths
from app.filesystem.verification import (
    PathCheckResult,
    VerificationResult,
    check_path,
    checkpoint_database,
    verify_database_accessible,
    verify_directory_writable,
    verify_migration,
    verify_production_ready,
)


class TestVerifyDatabaseAccessible:
    def test_existing_sqlite(self, tmp_path):
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        conn.execute("SELECT 1")
        conn.close()
        assert verify_database_accessible(db) is True

    def test_nonexistent_parent_dir(self, tmp_path):
        db = tmp_path / "no-parent" / "nonexistent.db"
        assert verify_database_accessible(db) is False

    def test_valid_database(self, tmp_path):
        db = tmp_path / "valid.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()
        assert verify_database_accessible(db) is True

    def test_empty_file_still_accessible(self, tmp_path):
        db = tmp_path / "empty.db"
        db.touch()
        assert verify_database_accessible(db) is True


class TestVerifyDirectoryWritable:
    def test_writable_directory(self, tmp_path):
        assert verify_directory_writable(tmp_path) is True

    def test_creates_nonexistent_directory(self, tmp_path):
        target = tmp_path / "new-dir"
        assert verify_directory_writable(target) is True
        assert target.exists()

    def test_cleanup_write_test_file(self, tmp_path):
        verify_directory_writable(tmp_path)
        test_files = list(tmp_path.glob(".devlog-write-test"))
        assert len(test_files) == 0


class TestVerificationResult:
    def test_success_true(self):
        r = VerificationResult(success=True)
        assert r.success is True
        assert r.errors == []
        assert r.warnings == []
        assert r.path_checks == {}

    def test_success_false(self):
        r = VerificationResult(success=False, errors=["err1"])
        assert r.success is False
        assert r.errors == ["err1"]

    def test_mutable(self):
        r = VerificationResult(success=True)
        r.warnings.append("warn1")
        assert "warn1" in r.warnings


class TestVerifyMigration:
    def _make_paths(self, tmp_path, *, create_all=True):
        data = tmp_path / "data"
        uploads = data / "uploads"
        themes = data / "themes"
        backups = data / "backups"
        exports = data / "exports"
        logs = tmp_path / "logs"
        runtime = tmp_path / "runtime"
        config = tmp_path / "config.toml"
        env = tmp_path / ".env"

        if create_all:
            data.mkdir(parents=True, exist_ok=True)
            uploads.mkdir(parents=True, exist_ok=True)
            themes.mkdir(parents=True, exist_ok=True)
            backups.mkdir(parents=True, exist_ok=True)
            exports.mkdir(parents=True, exist_ok=True)
            logs.mkdir(parents=True, exist_ok=True)
            runtime.mkdir(parents=True, exist_ok=True)
            config.touch()
            env.touch()

        return RuntimePaths.resolve(
            InstallMode.DEVELOPMENT,
            data_dir=data,
            uploads_dir=uploads,
            themes_dir=themes,
            backups_dir=backups,
            exports_dir=exports,
            log_dir=logs,
            runtime_dir=runtime,
            config_file=config,
            env_file=env,
        )

    def test_all_existing_paths(self, tmp_path):
        paths = self._make_paths(tmp_path, create_all=True)
        paths.database.path.write_bytes(b"sqlite data")
        paths.installation_metadata.path.write_text("{}")
        result = verify_migration(paths)
        assert result.success is True
        assert result.errors == []
        assert all(result.path_checks.values())

    def test_missing_data_dir(self, tmp_path):
        paths = self._make_paths(tmp_path, create_all=False)
        result = verify_migration(paths)
        assert result.success is False
        assert any("Data directory" in e for e in result.errors)

    def test_missing_log_dir_warning(self, tmp_path):
        paths = self._make_paths(tmp_path, create_all=True)
        paths.log_dir.path.rmdir()
        result = verify_migration(paths)
        assert any("Log directory" in w for w in result.warnings)

    def test_missing_runtime_dir_warning(self, tmp_path):
        paths = self._make_paths(tmp_path, create_all=True)
        paths.runtime_dir.path.rmdir()
        result = verify_migration(paths)
        assert any("Runtime directory" in w for w in result.warnings)

    def test_missing_database_warning(self, tmp_path):
        paths = self._make_paths(tmp_path, create_all=True)
        paths.database.path.unlink(missing_ok=True)
        result = verify_migration(paths)
        assert any("Database file" in w for w in result.warnings)

    def test_inaccessible_database_error(self, tmp_path, monkeypatch):
        paths = self._make_paths(tmp_path, create_all=True)
        paths.database.path.write_bytes(b"sqlite data")
        monkeypatch.setattr(
            "app.filesystem.verification.verify_database_accessible", lambda p: False
        )
        result = verify_migration(paths)
        assert any("not accessible" in e for e in result.errors)

    def test_path_checks_include_all_names(self, tmp_path):
        paths = self._make_paths(tmp_path, create_all=True)
        result = verify_migration(paths)
        expected_names = {
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
        assert set(result.path_checks.keys()) == expected_names

    def test_path_checks_reflect_existence(self, tmp_path):
        paths = self._make_paths(tmp_path, create_all=True)
        result = verify_migration(paths)
        assert result.path_checks["config_file"] is True
        assert result.path_checks["data_dir"] is True

    def test_nonexistent_path_check(self, tmp_path):
        paths = self._make_paths(tmp_path, create_all=False)
        result = verify_migration(paths)
        assert result.path_checks["data_dir"] is False
        assert result.path_checks["config_file"] is False

    def test_writable_check_for_managed_dirs(self, tmp_path):
        paths = self._make_paths(tmp_path, create_all=True)
        result = verify_migration(paths)
        assert result.success is True
        writable_errors = [e for e in result.errors if "not writable" in e]
        assert len(writable_errors) == 0

    def test_readonly_dir_error(self, tmp_path):
        paths = self._make_paths(tmp_path, create_all=True)
        uploads = paths.uploads_dir.path
        uploads.chmod(0o444)
        try:
            result = verify_migration(paths)
            assert any("not writable" in e for e in result.errors)
        finally:
            uploads.chmod(0o755)

    def test_empty_result_fields(self):
        r = VerificationResult(success=True)
        assert r.errors == []
        assert r.warnings == []
        assert r.path_checks == {}


class TestCheckPath:
    def test_nonexistent_path(self, tmp_path):
        result = check_path(tmp_path / "nonexistent")
        assert result.exists is False
        assert result.is_symlink is False

    def test_existing_directory(self, tmp_path):
        result = check_path(tmp_path)
        assert result.exists is True
        assert result.writable is True

    def test_symlink_detection(self, tmp_path):
        target = tmp_path / "real"
        target.mkdir()
        link = tmp_path / "link"
        link.symlink_to(target)
        result = check_path(link)
        assert result.is_symlink is True
        assert result.symlink_target == str(target)

    def test_free_space(self, tmp_path):
        result = check_path(tmp_path)
        assert result.free_space_bytes is not None
        assert result.free_space_bytes > 0

    def test_permissions(self, tmp_path):
        result = check_path(tmp_path)
        assert result.permissions != "unknown"

    def test_release_dir_detection(self, tmp_path):
        releases = tmp_path / "releases"
        releases.mkdir()
        current = releases / "current"
        current.symlink_to(tmp_path / "v1.0")
        result = check_path(releases)
        assert result.is_release_dir is True


class TestCheckpointDatabase:
    def test_checkpoint_existing(self, tmp_path):
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()
        assert checkpoint_database(db) is True

    def test_checkpoint_nonexistent(self, tmp_path):
        db = tmp_path / "nonexistent.db"
        assert checkpoint_database(db) is False


class TestVerifyProductionReady:
    def _make_paths(self, tmp_path, *, create_all=True):
        data = tmp_path / "data"
        uploads = data / "uploads"
        themes = data / "themes"
        backups = data / "backups"
        exports = data / "exports"
        logs = tmp_path / "logs"
        runtime = tmp_path / "runtime"
        config = tmp_path / "config.toml"
        env = tmp_path / ".env"

        if create_all:
            data.mkdir(parents=True, exist_ok=True)
            uploads.mkdir(parents=True, exist_ok=True)
            themes.mkdir(parents=True, exist_ok=True)
            backups.mkdir(parents=True, exist_ok=True)
            exports.mkdir(parents=True, exist_ok=True)
            logs.mkdir(parents=True, exist_ok=True)
            runtime.mkdir(parents=True, exist_ok=True)
            config.touch()
            env.touch()

        return RuntimePaths.resolve(
            InstallMode.DEVELOPMENT,
            data_dir=data,
            uploads_dir=uploads,
            themes_dir=themes,
            backups_dir=backups,
            exports_dir=exports,
            log_dir=logs,
            runtime_dir=runtime,
            config_file=config,
            env_file=env,
        )

    def test_missing_database_errors(self, tmp_path):
        paths = self._make_paths(tmp_path, create_all=True)
        result = verify_production_ready(paths)
        assert result.success is False
        assert any("Production database missing" in e for e in result.errors)

    def test_existing_database_ok(self, tmp_path):
        paths = self._make_paths(tmp_path, create_all=True)
        paths.database.path.write_bytes(b"sqlite data")
        result = verify_production_ready(paths)
        assert result.success is True

    def test_path_details_populated(self, tmp_path):
        paths = self._make_paths(tmp_path, create_all=True)
        result = verify_migration(paths)
        assert "data_dir" in result.path_details
        assert isinstance(result.path_details["data_dir"], PathCheckResult)
