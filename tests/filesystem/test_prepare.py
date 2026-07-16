from __future__ import annotations

from pathlib import Path

import pytest

from app.filesystem.layout import InstallMode, RuntimePaths
from app.filesystem.prepare import DirectorySpec, get_directory_specs, prepare_directories


class TestGetDirectorySpecs:
    @pytest.mark.parametrize(
        "mode",
        [
            InstallMode.SYSTEM,
            InstallMode.USER,
            InstallMode.DOCKER,
            InstallMode.DEVELOPMENT,
        ],
    )
    def test_returns_all_seven_specs(self, mode):
        specs = get_directory_specs(mode)
        assert set(specs.keys()) == {
            "data_dir",
            "uploads_dir",
            "themes_dir",
            "backups_dir",
            "exports_dir",
            "log_dir",
            "runtime_dir",
        }

    @pytest.mark.parametrize(
        "mode",
        [
            InstallMode.SYSTEM,
            InstallMode.USER,
            InstallMode.DOCKER,
            InstallMode.DEVELOPMENT,
        ],
    )
    def test_specs_are_directory_spec(self, mode):
        specs = get_directory_specs(mode)
        for spec in specs.values():
            assert isinstance(spec, DirectorySpec)

    def test_system_specs_owner(self):
        specs = get_directory_specs(InstallMode.SYSTEM)
        assert specs["data_dir"].owner == "devlog"
        assert specs["data_dir"].group == "devlog"

    def test_system_specs_mode_bits(self):
        specs = get_directory_specs(InstallMode.SYSTEM)
        assert specs["data_dir"].mode == 0o750
        assert specs["runtime_dir"].mode == 0o755

    def test_system_no_symlinks(self):
        specs = get_directory_specs(InstallMode.SYSTEM)
        for spec in specs.values():
            assert spec.symlinks_allowed is False

    def test_docker_no_owner(self):
        specs = get_directory_specs(InstallMode.DOCKER)
        assert specs["data_dir"].owner is None
        assert specs["data_dir"].group is None

    def test_docker_specs_mode(self):
        specs = get_directory_specs(InstallMode.DOCKER)
        for spec in specs.values():
            assert spec.mode == 0o755

    def test_user_mode_bits(self):
        specs = get_directory_specs(InstallMode.USER)
        for spec in specs.values():
            assert spec.mode == 0o700

    def test_user_no_owner(self):
        specs = get_directory_specs(InstallMode.USER)
        for spec in specs.values():
            assert spec.owner is None

    def test_development_no_owner(self):
        specs = get_directory_specs(InstallMode.DEVELOPMENT)
        for spec in specs.values():
            assert spec.owner is None

    @pytest.mark.parametrize(
        "mode",
        [
            InstallMode.SYSTEM,
            InstallMode.USER,
            InstallMode.DOCKER,
            InstallMode.DEVELOPMENT,
        ],
    )
    def test_no_spec_contains_secrets(self, mode):
        specs = get_directory_specs(mode)
        for spec in specs.values():
            assert spec.contains_secrets is False

    def test_development_paths_relative_to_cwd(self):
        specs = get_directory_specs(InstallMode.DEVELOPMENT)
        cwd = Path.cwd()
        assert specs["data_dir"].path == cwd / "data"
        assert specs["uploads_dir"].path == cwd / "data" / "uploads"
        assert specs["log_dir"].path == cwd / "logs"
        assert specs["runtime_dir"].path == cwd / "instance"

    def test_system_paths_are_absolute(self):
        specs = get_directory_specs(InstallMode.SYSTEM)
        for spec in specs.values():
            assert spec.path.is_absolute()

    def test_docker_paths_are_absolute(self):
        specs = get_directory_specs(InstallMode.DOCKER)
        for spec in specs.values():
            assert spec.path.is_absolute()

    def test_created_during_values(self):
        specs = get_directory_specs(InstallMode.DEVELOPMENT)
        assert specs["data_dir"].created_during == "onboarding"
        assert specs["uploads_dir"].created_during == "runtime"
        assert specs["themes_dir"].created_during == "runtime"
        assert specs["log_dir"].created_during == "onboarding"


class TestDirectorySpec:
    def test_frozen(self):
        spec = DirectorySpec(
            path=Path("/test"),
            owner=None,
            group=None,
            mode=0o755,
            created_during="onboarding",
            contains_secrets=False,
            symlinks_allowed=False,
        )
        with pytest.raises(AttributeError):
            spec.mode = 0o700


class TestPrepareDirectories:
    def test_creates_directories(self, tmp_path):
        data = tmp_path / "data"
        uploads = tmp_path / "uploads"
        paths = RuntimePaths.resolve(
            InstallMode.DEVELOPMENT,
            data_dir=data,
            uploads_dir=uploads,
            themes_dir=tmp_path / "themes",
            backups_dir=tmp_path / "backups",
            exports_dir=tmp_path / "exports",
            log_dir=tmp_path / "logs",
            runtime_dir=tmp_path / "runtime",
            config_file=tmp_path / "config.toml",
            env_file=tmp_path / ".env",
        )
        created = prepare_directories(paths, mode=InstallMode.DEVELOPMENT)
        assert len(created) > 0
        for p in created:
            assert p.exists()

    def test_dry_run_does_not_create(self, tmp_path):
        data = tmp_path / "data"
        uploads = tmp_path / "uploads"
        paths = RuntimePaths.resolve(
            InstallMode.DEVELOPMENT,
            data_dir=data,
            uploads_dir=uploads,
            themes_dir=tmp_path / "themes",
            backups_dir=tmp_path / "backups",
            exports_dir=tmp_path / "exports",
            log_dir=tmp_path / "logs",
            runtime_dir=tmp_path / "runtime",
            config_file=tmp_path / "config.toml",
            env_file=tmp_path / ".env",
        )
        created = prepare_directories(paths, mode=InstallMode.DEVELOPMENT, dry_run=True)
        assert len(created) > 0
        for p in created:
            assert not p.exists()

    def test_existing_directories_not_in_result(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        uploads = tmp_path / "uploads"
        paths = RuntimePaths.resolve(
            InstallMode.DEVELOPMENT,
            data_dir=data,
            uploads_dir=uploads,
            themes_dir=tmp_path / "themes",
            backups_dir=tmp_path / "backups",
            exports_dir=tmp_path / "exports",
            log_dir=tmp_path / "logs",
            runtime_dir=tmp_path / "runtime",
            config_file=tmp_path / "config.toml",
            env_file=tmp_path / ".env",
        )
        created = prepare_directories(paths, mode=InstallMode.DEVELOPMENT)
        assert data not in created

    def test_all_managed_dirs_covered(self, tmp_path):
        paths = RuntimePaths.resolve(
            InstallMode.DEVELOPMENT,
            data_dir=tmp_path / "data",
            uploads_dir=tmp_path / "data" / "uploads",
            themes_dir=tmp_path / "data" / "themes",
            backups_dir=tmp_path / "data" / "backups",
            exports_dir=tmp_path / "data" / "exports",
            log_dir=tmp_path / "logs",
            runtime_dir=tmp_path / "runtime",
            config_file=tmp_path / "config.toml",
            env_file=tmp_path / ".env",
        )
        created = prepare_directories(paths, mode=InstallMode.DEVELOPMENT)
        expected_dirs = {
            paths.data_dir.path,
            paths.uploads_dir.path,
            paths.themes_dir.path,
            paths.backups_dir.path,
            paths.exports_dir.path,
            paths.log_dir.path,
            paths.runtime_dir.path,
        }
        assert set(created) == expected_dirs

    def test_returns_path_objects(self, tmp_path):
        paths = RuntimePaths.resolve(
            InstallMode.DEVELOPMENT,
            data_dir=tmp_path / "data",
            uploads_dir=tmp_path / "uploads",
            themes_dir=tmp_path / "themes",
            backups_dir=tmp_path / "backups",
            exports_dir=tmp_path / "exports",
            log_dir=tmp_path / "logs",
            runtime_dir=tmp_path / "runtime",
            config_file=tmp_path / "config.toml",
            env_file=tmp_path / ".env",
        )
        created = prepare_directories(paths, mode=InstallMode.DEVELOPMENT)
        for item in created:
            assert isinstance(item, Path)

    def test_created_dirs_are_writable(self, tmp_path):
        paths = RuntimePaths.resolve(
            InstallMode.DEVELOPMENT,
            data_dir=tmp_path / "data",
            uploads_dir=tmp_path / "data" / "uploads",
            themes_dir=tmp_path / "data" / "themes",
            backups_dir=tmp_path / "data" / "backups",
            exports_dir=tmp_path / "data" / "exports",
            log_dir=tmp_path / "logs",
            runtime_dir=tmp_path / "runtime",
            config_file=tmp_path / "config.toml",
            env_file=tmp_path / ".env",
        )
        prepare_directories(paths, mode=InstallMode.DEVELOPMENT)
        for _, p in paths.all_paths():
            if p.parent.exists() and p.parent != p:
                test_file = p.parent / ".write-test"
                try:
                    test_file.write_text("ok")
                    test_file.unlink()
                except OSError:
                    pytest.fail(f"Parent of {p} is not writable")


class TestValidatePathSafety:
    def test_traversal_rejected(self, tmp_path):
        from app.filesystem.prepare import _validate_path_safety

        with pytest.raises(ValueError, match="Path traversal rejected"):
            _validate_path_safety(tmp_path, tmp_path / ".." / "escape")

    def test_nested_path_accepted(self, tmp_path):
        from app.filesystem.prepare import _validate_path_safety

        _validate_path_safety(tmp_path, tmp_path / "a" / "b" / "c")
