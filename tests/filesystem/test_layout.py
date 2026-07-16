from __future__ import annotations

from pathlib import Path

import pytest

from app.filesystem.layout import (
    InstallMode,
    PathProvenance,
    ResolvedPath,
    RuntimePaths,
    _xdg_config_home,
    _xdg_data_home,
    _xdg_runtime_dir,
    _xdg_state_home,
)


class TestInstallMode:
    def test_all_modes_exist(self):
        modes = list(InstallMode)
        assert len(modes) == 4
        assert {m.value for m in modes} == {"system", "user", "docker", "development"}

    @pytest.mark.parametrize(
        "mode,expected",
        [
            (InstallMode.SYSTEM, "system"),
            (InstallMode.USER, "user"),
            (InstallMode.DOCKER, "docker"),
            (InstallMode.DEVELOPMENT, "development"),
        ],
    )
    def test_mode_value(self, mode, expected):
        assert mode.value == expected


class TestPathProvenance:
    def test_all_provenances_exist(self):
        provenances = {p.value for p in PathProvenance}
        assert provenances == {
            "explicit",
            "metadata",
            "env_var",
            "system_default",
            "xdg_default",
            "docker_default",
            "development_fallback",
        }


class TestResolvedPath:
    def test_frozen(self, tmp_path):
        rp = ResolvedPath(
            path=tmp_path / "test",
            provenance=PathProvenance.EXPLICIT,
            source="test",
        )
        with pytest.raises(AttributeError):
            rp.path = tmp_path / "other"


class TestRuntimePathsSystem:
    def test_default_paths(self):
        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)
        assert paths.config_file.path == Path("/etc/devlog/config.toml")
        assert paths.env_file.path == Path("/etc/devlog/.env")
        assert paths.data_dir.path == Path("/var/lib/devlog")
        assert paths.database.path == Path("/var/lib/devlog/devlog.sqlite3")
        assert paths.uploads_dir.path == Path("/var/lib/devlog/uploads")
        assert paths.themes_dir.path == Path("/var/lib/devlog/themes")
        assert paths.backups_dir.path == Path("/var/lib/devlog/backups")
        assert paths.exports_dir.path == Path("/var/lib/devlog/exports")
        assert paths.log_dir.path == Path("/var/log/devlog")
        assert paths.runtime_dir.path == Path("/run/devlog")
        assert paths.installation_metadata.path == Path("/var/lib/devlog/.devlog-installation.json")

    def test_explicit_overrides(self, tmp_path):
        custom_config = tmp_path / "custom-config.toml"
        custom_data = tmp_path / "custom-data"
        custom_env = tmp_path / "custom.env"
        custom_log = tmp_path / "custom-logs"
        custom_runtime = tmp_path / "custom-runtime"

        paths = RuntimePaths.resolve(
            InstallMode.SYSTEM,
            config_file=custom_config,
            data_dir=custom_data,
            env_file=custom_env,
            log_dir=custom_log,
            runtime_dir=custom_runtime,
        )
        assert paths.config_file.path == custom_config.resolve()
        assert paths.data_dir.path == custom_data.resolve()
        assert paths.env_file.path == custom_env.resolve()
        assert paths.log_dir.path == custom_log.resolve()
        assert paths.runtime_dir.path == custom_runtime.resolve()

    def test_explicit_subdirs(self, tmp_path):
        custom_uploads = tmp_path / "my-uploads"
        custom_themes = tmp_path / "my-themes"
        custom_backups = tmp_path / "my-backups"
        custom_exports = tmp_path / "my-exports"
        custom_db = tmp_path / "my-db.sqlite3"

        paths = RuntimePaths.resolve(
            InstallMode.SYSTEM,
            uploads_dir=custom_uploads,
            themes_dir=custom_themes,
            backups_dir=custom_backups,
            exports_dir=custom_exports,
            database_path=custom_db,
        )
        assert paths.uploads_dir.path == custom_uploads.resolve()
        assert paths.themes_dir.path == custom_themes.resolve()
        assert paths.backups_dir.path == custom_backups.resolve()
        assert paths.exports_dir.path == custom_exports.resolve()
        assert paths.database.path == custom_db.resolve()

    def test_explicit_provenance(self, tmp_path):
        paths = RuntimePaths.resolve(
            InstallMode.SYSTEM,
            config_file=tmp_path / "cfg.toml",
        )
        assert paths.config_file.provenance == PathProvenance.EXPLICIT
        assert paths.config_file.source == "explicit override"

    def test_default_provenance(self):
        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)
        assert paths.config_file.provenance == PathProvenance.SYSTEM_DEFAULT
        assert "system default" in paths.config_file.source

    def test_devlog_env_var_override(self, tmp_path, monkeypatch):
        custom_data = tmp_path / "env-data"
        monkeypatch.setenv("DEVLOG_DATA_DIR", str(custom_data))

        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)
        assert paths.data_dir.path == custom_data.resolve()
        assert paths.data_dir.provenance == PathProvenance.ENV_VAR
        assert "DEVLOG_DATA_DIR" in paths.data_dir.source

    @pytest.mark.parametrize(
        "env_var,attr",
        [
            ("DEVLOG_CONFIG_FILE", "config_file"),
            ("DEVLOG_ENV_FILE", "env_file"),
            ("DEVLOG_DATA_DIR", "data_dir"),
            ("DEVLOG_LOG_DIR", "log_dir"),
            ("DEVLOG_RUNTIME_DIR", "runtime_dir"),
        ],
    )
    def test_env_var_overrides_per_field(self, tmp_path, monkeypatch, env_var, attr):
        custom = tmp_path / f"custom-{attr}"
        monkeypatch.setenv(env_var, str(custom))

        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)
        rp = getattr(paths, attr)
        assert rp.path == custom.resolve()
        assert rp.provenance == PathProvenance.ENV_VAR

    def test_explicit_wins_over_env_var(self, tmp_path, monkeypatch):
        explicit = tmp_path / "explicit"
        env_path = tmp_path / "from-env"
        monkeypatch.setenv("DEVLOG_DATA_DIR", str(env_path))

        paths = RuntimePaths.resolve(
            InstallMode.SYSTEM,
            data_dir=explicit,
        )
        assert paths.data_dir.path == explicit.resolve()
        assert paths.data_dir.provenance == PathProvenance.EXPLICIT

    def test_install_root_override(self, tmp_path):
        root = tmp_path / "etc-devlog"
        paths = RuntimePaths.resolve(InstallMode.SYSTEM, install_root=root)
        assert paths.config_file.path == (root / "config.toml").resolve()
        assert paths.env_file.path == (root / ".env").resolve()

    def test_all_paths_returns_12(self):
        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)
        all_p = paths.all_paths()
        assert len(all_p) == 12
        assert all(isinstance(n, str) and isinstance(p, Path) for n, p in all_p)

    def test_all_paths_names(self):
        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)
        names = [n for n, _ in paths.all_paths()]
        expected = [
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
            "release_dir",
        ]
        assert names == expected

    def test_as_dict_returns_strings(self):
        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)
        d = paths.as_dict()
        assert len(d) == 12
        for v in d.values():
            assert isinstance(v, str)

    def test_as_dict_keys(self):
        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)
        d = paths.as_dict()
        expected_keys = {
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
            "release_dir",
        }
        assert set(d.keys()) == expected_keys

    def test_provenance_for_valid(self):
        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)
        prov = paths.provenance_for("config_file")
        assert "system_default" in prov

    def test_provenance_for_unknown_field(self):
        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)
        assert paths.provenance_for("nonexistent") == "unknown"

    def test_all_paths_are_absolute(self):
        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)
        for _, p in paths.all_paths():
            assert p.is_absolute()

    def test_derived_subpaths_from_data_dir(self, tmp_path):
        data = tmp_path / "mydata"
        paths = RuntimePaths.resolve(InstallMode.SYSTEM, data_dir=data)
        assert paths.database.path == (data / "devlog.sqlite3").resolve()
        assert paths.uploads_dir.path == (data / "uploads").resolve()
        assert paths.themes_dir.path == (data / "themes").resolve()
        assert paths.backups_dir.path == (data / "backups").resolve()
        assert paths.exports_dir.path == (data / "exports").resolve()
        assert paths.installation_metadata.path == (data / ".devlog-installation.json").resolve()


class TestRuntimePathsUser:
    def test_default_xdg_paths(self, tmp_path, monkeypatch):
        xdg_config = tmp_path / "config"
        xdg_data = tmp_path / "data"
        xdg_state = tmp_path / "state"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config))
        monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data))
        monkeypatch.setenv("XDG_STATE_HOME", str(xdg_state))
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)

        paths = RuntimePaths.for_mode(InstallMode.USER)
        assert paths.config_file.path == (xdg_config / "devlog" / "config.toml").resolve()
        assert paths.env_file.path == (xdg_config / "devlog" / ".env").resolve()
        assert paths.data_dir.path == (xdg_data / "devlog").resolve()
        assert paths.database.path == (xdg_data / "devlog" / "devlog.sqlite3").resolve()
        assert paths.log_dir.path == (xdg_state / "devlog" / "logs").resolve()

    def test_xdg_runtime_dir_fallback_to_state(self, tmp_path, monkeypatch):
        xdg_config = tmp_path / "config"
        xdg_data = tmp_path / "data"
        xdg_state = tmp_path / "state"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config))
        monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data))
        monkeypatch.setenv("XDG_STATE_HOME", str(xdg_state))
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)

        paths = RuntimePaths.for_mode(InstallMode.USER)
        assert paths.runtime_dir.path == (xdg_state / "devlog").resolve()

    def test_xdg_runtime_dir_used_when_set(self, tmp_path, monkeypatch):
        xdg_config = tmp_path / "config"
        xdg_data = tmp_path / "data"
        xdg_state = tmp_path / "state"
        xdg_runtime = tmp_path / "runtime"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config))
        monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data))
        monkeypatch.setenv("XDG_STATE_HOME", str(xdg_state))
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(xdg_runtime))

        paths = RuntimePaths.for_mode(InstallMode.USER)
        assert paths.runtime_dir.path == (xdg_runtime / "devlog").resolve()
        assert paths.runtime_dir.provenance == PathProvenance.XDG_DEFAULT

    def test_user_explicit_overrides(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

        custom = tmp_path / "custom-data"
        paths = RuntimePaths.resolve(InstallMode.USER, data_dir=custom)
        assert paths.data_dir.path == custom.resolve()

    def test_user_provenances(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

        paths = RuntimePaths.for_mode(InstallMode.USER)
        assert paths.config_file.provenance == PathProvenance.XDG_DEFAULT
        assert paths.data_dir.provenance == PathProvenance.XDG_DEFAULT

    def test_user_subdirs_derived(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

        paths = RuntimePaths.for_mode(InstallMode.USER)
        data = paths.data_dir.path
        assert paths.uploads_dir.path == (data / "uploads").resolve()
        assert paths.themes_dir.path == (data / "themes").resolve()
        assert paths.backups_dir.path == (data / "backups").resolve()
        assert paths.exports_dir.path == (data / "exports").resolve()


class TestRuntimePathsDocker:
    def test_default_paths(self):
        paths = RuntimePaths.for_mode(InstallMode.DOCKER)
        assert paths.config_file.path == Path("/etc/devlog/config.toml")
        assert paths.env_file.path == Path("/etc/devlog/.env")
        assert paths.data_dir.path == Path("/data")
        assert paths.database.path == Path("/data/devlog.sqlite3")
        assert paths.uploads_dir.path == Path("/data/uploads")
        assert paths.themes_dir.path == Path("/data/themes")
        assert paths.backups_dir.path == Path("/data/backups")
        assert paths.exports_dir.path == Path("/data/exports")
        assert paths.log_dir.path == Path("/var/log/devlog")
        assert paths.runtime_dir.path == Path("/run/devlog")

    def test_docker_provenances(self):
        paths = RuntimePaths.for_mode(InstallMode.DOCKER)
        assert paths.config_file.provenance == PathProvenance.DOCKER_DEFAULT
        assert paths.data_dir.provenance == PathProvenance.DOCKER_DEFAULT

    def test_docker_explicit_overrides(self, tmp_path):
        custom_data = tmp_path / "docker-data"
        paths = RuntimePaths.resolve(InstallMode.DOCKER, data_dir=custom_data)
        assert paths.data_dir.path == custom_data.resolve()

    def test_docker_all_paths_absolute(self):
        paths = RuntimePaths.for_mode(InstallMode.DOCKER)
        for _, p in paths.all_paths():
            assert p.is_absolute()


class TestRuntimePathsDevelopment:
    def test_default_paths(self):
        cwd = Path.cwd()
        paths = RuntimePaths.for_mode(InstallMode.DEVELOPMENT)
        assert paths.config_file.path == (cwd / "config.toml").resolve()
        assert paths.env_file.path == (cwd / ".env").resolve()
        assert paths.data_dir.path == (cwd / "data").resolve()
        assert paths.database.path == (cwd / "data" / "devlog.sqlite3").resolve()
        assert paths.uploads_dir.path == (cwd / "data" / "uploads").resolve()
        assert paths.themes_dir.path == (cwd / "data" / "themes").resolve()
        assert paths.backups_dir.path == (cwd / "data" / "backups").resolve()
        assert paths.exports_dir.path == (cwd / "data" / "exports").resolve()
        assert paths.log_dir.path == (cwd / "logs").resolve()
        assert paths.runtime_dir.path == (cwd / "instance").resolve()

    def test_development_provenances(self):
        paths = RuntimePaths.for_mode(InstallMode.DEVELOPMENT)
        assert paths.config_file.provenance == PathProvenance.DEVELOPMENT_FALLBACK
        assert paths.data_dir.provenance == PathProvenance.DEVELOPMENT_FALLBACK
        assert paths.log_dir.provenance == PathProvenance.DEVELOPMENT_FALLBACK
        assert paths.runtime_dir.provenance == PathProvenance.DEVELOPMENT_FALLBACK

    def test_development_explicit_overrides(self, tmp_path):
        custom_data = tmp_path / "dev-data"
        paths = RuntimePaths.resolve(InstallMode.DEVELOPMENT, data_dir=custom_data)
        assert paths.data_dir.path == custom_data.resolve()
        assert paths.data_dir.provenance == PathProvenance.EXPLICIT

    def test_development_subdirs_derived(self):
        paths = RuntimePaths.for_mode(InstallMode.DEVELOPMENT)
        data = paths.data_dir.path
        assert paths.database.path == (data / "devlog.sqlite3").resolve()
        assert paths.uploads_dir.path == (data / "uploads").resolve()
        assert paths.themes_dir.path == (data / "themes").resolve()
        assert paths.backups_dir.path == (data / "backups").resolve()
        assert paths.exports_dir.path == (data / "exports").resolve()


class TestXDGHelpers:
    def test_xdg_config_home_override(self, tmp_path):
        assert _xdg_config_home(tmp_path) == tmp_path

    def test_xdg_config_home_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        assert _xdg_config_home() == tmp_path

    def test_xdg_config_home_default(self, monkeypatch):
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        assert _xdg_config_home() == Path.home() / ".config"

    def test_xdg_data_home_override(self, tmp_path):
        assert _xdg_data_home(tmp_path) == tmp_path

    def test_xdg_data_home_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        assert _xdg_data_home() == tmp_path

    def test_xdg_data_home_default(self, monkeypatch):
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        assert _xdg_data_home() == Path.home() / ".local" / "share"

    def test_xdg_state_home_override(self, tmp_path):
        assert _xdg_state_home(tmp_path) == tmp_path

    def test_xdg_state_home_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        assert _xdg_state_home() == tmp_path

    def test_xdg_state_home_default(self, monkeypatch):
        monkeypatch.delenv("XDG_STATE_HOME", raising=False)
        assert _xdg_state_home() == Path.home() / ".local" / "state"

    def test_xdg_runtime_dir_override(self, tmp_path):
        assert _xdg_runtime_dir(tmp_path) == tmp_path

    def test_xdg_runtime_dir_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        assert _xdg_runtime_dir() == tmp_path

    def test_xdg_runtime_dir_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        assert _xdg_runtime_dir() is None

    def test_xdg_runtime_dir_none_with_override(self, tmp_path):
        assert _xdg_runtime_dir(tmp_path) == tmp_path


class TestForModeAlias:
    @pytest.mark.parametrize(
        "mode",
        [
            InstallMode.SYSTEM,
            InstallMode.USER,
            InstallMode.DOCKER,
            InstallMode.DEVELOPMENT,
        ],
    )
    def test_for_mode_equals_resolve(self, mode):
        direct = RuntimePaths.resolve(mode)
        via_for_mode = RuntimePaths.for_mode(mode)
        assert direct == via_for_mode


class TestInstallationMetadata:
    def test_load_valid(self, tmp_path):
        from app.filesystem.layout import InstallationMetadata

        meta_file = tmp_path / ".devlog-installation.json"
        meta_file.write_text('{"mode": "system", "version": "1.0.0", "data_dir": "/data"}')
        meta = InstallationMetadata.load(meta_file)
        assert meta is not None
        assert meta.mode == InstallMode.SYSTEM
        assert meta.version == "1.0.0"
        assert meta.data_dir == Path("/data")

    def test_load_nonexistent(self, tmp_path):
        from app.filesystem.layout import InstallationMetadata

        meta = InstallationMetadata.load(tmp_path / "missing.json")
        assert meta is None

    def test_load_invalid_json(self, tmp_path):
        from app.filesystem.layout import InstallationMetadata

        meta_file = tmp_path / ".devlog-installation.json"
        meta_file.write_text("not json")
        meta = InstallationMetadata.load(meta_file)
        assert meta is None

    def test_load_missing_mode(self, tmp_path):
        from app.filesystem.layout import InstallationMetadata

        meta_file = tmp_path / ".devlog-installation.json"
        meta_file.write_text('{"version": "1.0.0"}')
        meta = InstallationMetadata.load(meta_file)
        assert meta is None


class TestReleaseDir:
    def test_system_has_release_dir(self):
        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)
        assert paths.release_dir is not None
        assert paths.release_dir.path.name == "current"
        assert paths.release_dir.provenance == PathProvenance.SYSTEM_DEFAULT

    def test_development_no_release_dir(self):
        paths = RuntimePaths.for_mode(InstallMode.DEVELOPMENT)
        assert paths.release_dir is None

    def test_docker_no_release_dir(self):
        paths = RuntimePaths.for_mode(InstallMode.DOCKER)
        assert paths.release_dir is None

    def test_user_no_release_dir(self):
        paths = RuntimePaths.for_mode(InstallMode.USER)
        assert paths.release_dir is None

    def test_all_paths_includes_release_for_system(self):
        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)
        all_p = paths.all_paths()
        names = [n for n, _ in all_p]
        assert "release_dir" in names

    def test_all_paths_excludes_release_for_dev(self):
        paths = RuntimePaths.for_mode(InstallMode.DEVELOPMENT)
        all_p = paths.all_paths()
        names = [n for n, _ in all_p]
        assert "release_dir" not in names

    def test_as_dict_includes_release_for_system(self):
        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)
        d = paths.as_dict()
        assert "release_dir" in d

    def test_as_dict_excludes_release_for_dev(self):
        paths = RuntimePaths.for_mode(InstallMode.DEVELOPMENT)
        d = paths.as_dict()
        assert "release_dir" not in d


class TestFromMetadata:
    def test_from_metadata_loads_mode(self, tmp_path):
        meta_file = tmp_path / ".devlog-installation.json"
        meta_file.write_text('{"mode": "system", "version": "1.0.0"}')
        paths = RuntimePaths.from_metadata(meta_file)
        assert paths is not None
        assert paths.config_file.path == Path("/etc/devlog/config.toml")

    def test_from_metadata_returns_none_for_missing(self, tmp_path):
        paths = RuntimePaths.from_metadata(tmp_path / "missing.json")
        assert paths is None

    def test_from_metadata_applies_overrides(self, tmp_path):
        custom_data = tmp_path / "custom-data"
        meta_file = tmp_path / ".devlog-installation.json"
        meta_file.write_text('{"mode": "system", "version": "1.0.0"}')
        paths = RuntimePaths.from_metadata(meta_file, data_dir=custom_data)
        assert paths is not None
        assert paths.data_dir.path == custom_data.resolve()


class TestDetectMode:
    def test_detect_from_metadata(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from app.filesystem.layout import detect_mode

        meta_file = tmp_path / ".devlog-installation.json"
        meta_file.write_text('{"mode": "docker", "version": "1.0.0"}')
        result = detect_mode(tmp_path)
        assert result.detected_mode == InstallMode.DOCKER
        assert "metadata" in result.source

    def test_detect_default_development(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("DEVLOG_DOCKER", raising=False)
        monkeypatch.delenv("DEVLOG_MODE", raising=False)
        from app.filesystem.layout import detect_mode

        result = detect_mode(tmp_path)
        assert result.detected_mode == InstallMode.DEVELOPMENT

    def test_detect_docker_env(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DEVLOG_DOCKER", "1")
        from app.filesystem.layout import detect_mode

        result = detect_mode(tmp_path)
        assert result.detected_mode == InstallMode.DOCKER

    def test_detect_mode_env(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DEVLOG_MODE", "user")
        from app.filesystem.layout import detect_mode

        result = detect_mode(tmp_path)
        assert result.detected_mode == InstallMode.USER

    def test_detect_ambiguous(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from app.filesystem.layout import detect_mode

        meta_file = tmp_path / ".devlog-installation.json"
        meta_file.write_text('{"mode": "system", "version": "1.0.0"}')
        monkeypatch.setenv("DEVLOG_DOCKER", "1")
        result = detect_mode(tmp_path)
        assert result.ambiguous is True
        assert result.candidates is not None
        assert len(result.candidates) >= 2


class TestDockerVolumeMigration:
    def test_docker_volume_paths_resolve_to_container_paths(self):
        paths = RuntimePaths.for_mode(InstallMode.DOCKER)
        assert str(paths.data_dir.path) == "/data"
        assert str(paths.database.path) == "/data/devlog.sqlite3"
        assert str(paths.uploads_dir.path) == "/data/uploads"
        assert str(paths.themes_dir.path) == "/data/themes"
        assert str(paths.backups_dir.path) == "/data/backups"
        assert str(paths.exports_dir.path) == "/data/exports"

    def test_docker_volume_subdirs_are_consistent(self):
        paths = RuntimePaths.for_mode(InstallMode.DOCKER)
        for name in ("uploads_dir", "themes_dir", "backups_dir", "exports_dir"):
            rp = getattr(paths, name)
            assert str(rp.path).startswith("/data/"), f"Docker volume {name} should be under /data"

    def test_docker_database_under_data_dir(self):
        paths = RuntimePaths.for_mode(InstallMode.DOCKER)
        assert paths.database.path.parent == paths.data_dir.path

    def test_docker_explicit_data_dir_propagates(self, tmp_path):
        custom = tmp_path / "custom-data"
        paths = RuntimePaths.resolve(InstallMode.DOCKER, data_dir=custom)
        assert paths.data_dir.path == custom.resolve()
        assert paths.database.path == custom.resolve() / "devlog.sqlite3"
        assert paths.uploads_dir.path == custom.resolve() / "uploads"
        assert paths.themes_dir.path == custom.resolve() / "themes"
        assert paths.backups_dir.path == custom.resolve() / "backups"
        assert paths.exports_dir.path == custom.resolve() / "exports"

    def test_docker_named_volume_initialization(self, tmp_path):
        """Verify prepare_directories creates the expected Docker layout."""
        from app.filesystem.prepare import prepare_directories

        data_dir = tmp_path / "data"
        log_dir = tmp_path / "logs"
        runtime_dir = tmp_path / "run"
        paths = RuntimePaths.resolve(
            InstallMode.DOCKER,
            data_dir=data_dir,
            log_dir=log_dir,
            runtime_dir=runtime_dir,
        )
        created = prepare_directories(paths, mode=InstallMode.DOCKER)
        assert len(created) > 0
        assert data_dir.exists()
        assert (data_dir / "uploads").exists()
        assert (data_dir / "themes").exists()
        assert (data_dir / "backups").exists()
        assert (data_dir / "exports").exists()

    def test_docker_uid_gid_documented_in_dockerfile(self):
        """Verify Dockerfile defines UID/GID 1000:1000 explicitly."""
        dockerfile = Path(__file__).resolve().parent.parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "--uid 1000" in content, "Dockerfile should use explicit UID 1000"
        assert "--gid 1000" in content or "--gid blog" in content, (
            "Dockerfile should use explicit GID 1000 or named group"
        )
