"""End-to-end test: clean installed artifact with production-style state paths.

Proves that a clean installed artifact can onboard and run outside the source
checkout using production-style state paths (acceptance criterion 11).

Simulates:
1. Installer creates metadata file in target location
2. Onboarding reads metadata and resolves paths
3. Directories are prepared with correct structure
4. verify_production_ready confirms layout integrity
5. App can resolve database path from layout
"""

from __future__ import annotations

import json
import sqlite3

from app.filesystem.layout import (
    InstallMode,
    InstallationMetadata,
    RuntimePaths,
)
from app.filesystem.lifecycle import RUNTIME_PATH_CATEGORIES, PathCategory
from app.filesystem.prepare import prepare_directories
from app.filesystem.verification import (
    check_path,
    verify_database_accessible,
    verify_migration,
    verify_production_ready,
)


class TestCleanInstalledArtifact:
    def test_system_mode_full_lifecycle(self, tmp_path):
        """Simulate a clean system-mode install from scratch."""
        install_root = tmp_path / "opt" / "devlog"
        data_root = tmp_path / "var" / "lib" / "devlog"
        log_root = tmp_path / "var" / "log" / "devlog"
        runtime_root = tmp_path / "run" / "devlog"
        config_dir = tmp_path / "etc" / "devlog"

        install_root.mkdir(parents=True)
        config_dir.mkdir(parents=True)
        data_root.mkdir(parents=True)
        log_root.mkdir(parents=True)
        runtime_root.mkdir(parents=True)

        config_file = config_dir / "config.toml"
        config_file.write_text("[site]\ntitle = 'Test Blog'\n")
        env_file = config_dir / ".env"
        env_file.write_text("SECRET_KEY=test-secret-key-1234567890abcdef\n")

        meta_path = data_root / ".devlog-installation.json"
        meta_path.write_text(
            json.dumps(
                {
                    "mode": "system",
                    "version": "1.0.0",
                    "data_dir": str(data_root),
                    "config_file": str(config_file),
                    "env_file": str(env_file),
                }
            )
        )

        meta = InstallationMetadata.load(meta_path)
        assert meta is not None
        assert meta.mode == InstallMode.SYSTEM
        assert meta.data_dir == data_root

        paths = RuntimePaths.from_metadata(
            meta_path,
            log_dir=log_root,
            runtime_dir=runtime_root,
        )
        assert paths is not None
        assert paths.config_file.path == config_file.resolve()
        assert paths.env_file.path == env_file.resolve()
        assert paths.data_dir.path == data_root.resolve()
        assert paths.database.path == data_root.resolve() / "devlog.sqlite3"

        prepare_directories(paths, mode=InstallMode.SYSTEM)

        db_path = paths.database.path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        result = verify_migration(paths)
        assert result.success is True

        prod_result = verify_production_ready(paths)
        assert prod_result.success is True

        assert verify_database_accessible(db_path) is True

        for field_name, category in RUNTIME_PATH_CATEGORIES.items():
            if category in (PathCategory.LOGS, PathCategory.RUNTIME):
                continue
            rp = getattr(paths, field_name, None)
            if rp is not None and hasattr(rp, "path"):
                check = check_path(rp.path)
                assert check.exists, f"{field_name} should exist"

    def test_docker_mode_volume_layout(self, tmp_path):
        """Simulate Docker named volume initialization."""
        data_dir = tmp_path / "data"
        log_dir = tmp_path / "logs"
        runtime_dir = tmp_path / "run"
        config_dir = tmp_path / "config"

        data_dir.mkdir()
        log_dir.mkdir()
        runtime_dir.mkdir()
        config_dir.mkdir()

        paths = RuntimePaths.resolve(
            InstallMode.DOCKER,
            data_dir=data_dir,
            log_dir=log_dir,
            runtime_dir=runtime_dir,
        )

        created = prepare_directories(paths, mode=InstallMode.DOCKER)
        assert len(created) > 0

        db_path = paths.database.path
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        result = verify_production_ready(paths)
        assert result.success is True

        assert (data_dir / "uploads").is_dir()
        assert (data_dir / "themes").is_dir()
        assert (data_dir / "backups").is_dir()
        assert (data_dir / "exports").is_dir()

    def test_user_mode_xdg_layout(self, tmp_path, monkeypatch):
        """Simulate user-mode XDG layout."""
        xdg_config = tmp_path / ".config"
        xdg_data = tmp_path / ".local" / "share"
        xdg_state = tmp_path / ".local" / "state"

        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config))
        monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data))
        monkeypatch.setenv("XDG_STATE_HOME", str(xdg_state))

        paths = RuntimePaths.for_mode(InstallMode.USER)

        assert paths.config_file.path.parent == xdg_config / "devlog"
        assert paths.data_dir.path == (xdg_data / "devlog").resolve()
        assert paths.log_dir.path == (xdg_state / "devlog" / "logs").resolve()

        for _, p in paths.all_paths():
            assert p.is_absolute()

    def test_development_mode_uses_cwd(self, tmp_path, monkeypatch):
        """Simulate development mode using current directory."""
        monkeypatch.chdir(tmp_path)

        paths = RuntimePaths.for_mode(InstallMode.DEVELOPMENT)

        assert paths.data_dir.path == (tmp_path / "data").resolve()
        assert paths.config_file.path == (tmp_path / "config.toml").resolve()
        assert paths.database.path == (tmp_path / "data" / "devlog.sqlite3").resolve()

    def test_metadata_driven_mode_detection(self, tmp_path):
        """Verify mode detection reads metadata correctly."""
        from app.filesystem.layout import detect_mode_from_metadata

        meta_path = tmp_path / ".devlog-installation.json"
        meta_path.write_text(json.dumps({"mode": "docker", "version": "2.0.0"}))

        result = detect_mode_from_metadata(tmp_path)
        assert result is not None
        assert result.detected_mode == InstallMode.DOCKER

    def test_explicit_overrides_precede_metadata(self, tmp_path):
        """Explicit overrides should take precedence over metadata values."""
        data_dir = tmp_path / "custom-data"
        meta_path = tmp_path / ".devlog-installation.json"
        meta_path.write_text(
            json.dumps(
                {
                    "mode": "system",
                    "version": "1.0.0",
                    "data_dir": str(tmp_path / "metadata-data"),
                }
            )
        )

        paths = RuntimePaths.from_metadata(meta_path, data_dir=data_dir)
        assert paths is not None
        assert paths.data_dir.path == data_dir.resolve()

    def test_all_paths_provenance_tracked(self, tmp_path):
        """Every resolved path should have provenance information."""
        paths = RuntimePaths.for_mode(InstallMode.DEVELOPMENT)
        for name in (
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
        ):
            provenance = paths.provenance_for(name)
            assert provenance != "unknown", f"{name} should have known provenance"

    def test_lifecycle_categories_cover_all_paths(self):
        """Every RuntimePaths field should have a lifecycle category."""
        for name in (
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
        ):
            assert name in RUNTIME_PATH_CATEGORIES, (
                f"RuntimePaths field '{name}' has no lifecycle category"
            )
