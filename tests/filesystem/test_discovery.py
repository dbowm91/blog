from __future__ import annotations

from pathlib import Path

from app.filesystem.discovery import (
    LegacyDiscovery,
    classify_discovery,
    discover_legacy_layout,
)
from app.filesystem.layout import InstallMode, RuntimePaths


class TestDiscoverLegacyLayout:
    def test_finds_database_files(self, tmp_path):
        (tmp_path / "test.sqlite3").touch()
        (tmp_path / "blog.db").touch()
        (tmp_path / "data.sqlite").touch()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.database_files) == 3

    def test_finds_database_in_subdirectory(self, tmp_path):
        sub = tmp_path / "instance"
        sub.mkdir()
        (sub / "devlog.sqlite3").touch()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.database_files) == 1

    def test_ignores_hidden_subdirs_for_database(self, tmp_path):
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "test.db").touch()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.database_files) == 0

    def test_finds_upload_dirs(self, tmp_path):
        for name in ("uploads", "media", "files", "images"):
            (tmp_path / name).mkdir()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.upload_dirs) == 4
        found_names = {d.name for d in discovery.upload_dirs}
        assert found_names == {"uploads", "media", "files", "images"}

    def test_finds_backup_dirs(self, tmp_path):
        (tmp_path / "backups").mkdir()
        (tmp_path / "backup").mkdir()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.backup_dirs) == 2

    def test_finds_theme_dirs(self, tmp_path):
        (tmp_path / "themes").mkdir()
        (tmp_path / "theme").mkdir()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.theme_dirs) == 2

    def test_finds_log_dirs(self, tmp_path):
        (tmp_path / "logs").mkdir()
        (tmp_path / "log").mkdir()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.log_dirs) == 2

    def test_finds_config_files(self, tmp_path):
        for name in ("config.toml", "config.yaml", "config.json", "config.ini"):
            (tmp_path / name).touch()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.config_files) == 4

    def test_finds_config_toml(self, tmp_path):
        (tmp_path / "config.toml").touch()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.config_files) == 1
        assert discovery.config_files[0].name == "config.toml"

    def test_finds_env_files(self, tmp_path):
        (tmp_path / ".env").touch()
        (tmp_path / ".env.local").touch()
        (tmp_path / ".env.production").touch()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.env_files) == 3

    def test_finds_metadata_files(self, tmp_path):
        (tmp_path / ".devlog-installation.json").touch()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.metadata_files) == 1

    def test_finds_metadata_in_subdir(self, tmp_path):
        sub = tmp_path / "instance"
        sub.mkdir()
        (sub / ".devlog-installation.json").touch()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.metadata_files) == 1

    def test_finds_metadata_json(self, tmp_path):
        (tmp_path / "devlog-installation.json").touch()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.metadata_files) == 1

    def test_empty_directory(self, tmp_path):
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.database_files) == 0
        assert len(discovery.upload_dirs) == 0
        assert len(discovery.backup_dirs) == 0
        assert len(discovery.theme_dirs) == 0
        assert len(discovery.log_dirs) == 0
        assert len(discovery.config_files) == 0
        assert len(discovery.env_files) == 0
        assert len(discovery.metadata_files) == 0

    def test_ignores_hidden_dirs(self, tmp_path):
        hidden = tmp_path / ".devlog"
        hidden.mkdir()
        (hidden / "uploads").mkdir()
        (hidden / "config.toml").touch()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.upload_dirs) == 0

    def test_case_insensitive_dir_names(self, tmp_path):
        (tmp_path / "Uploads").mkdir()
        (tmp_path / "BACKUPS").mkdir()
        (tmp_path / "Themes").mkdir()
        (tmp_path / "LOGS").mkdir()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.upload_dirs) == 1
        assert len(discovery.backup_dirs) == 1
        assert len(discovery.theme_dirs) == 1
        assert len(discovery.log_dirs) == 1

    def test_non_matching_dirs_ignored(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "node_modules").mkdir()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.upload_dirs) == 0
        assert len(discovery.backup_dirs) == 0
        assert len(discovery.theme_dirs) == 0
        assert len(discovery.log_dirs) == 0

    def test_only_root_level_dirs_counted(self, tmp_path):
        sub = tmp_path / "nested"
        sub.mkdir()
        (sub / "uploads").mkdir()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.upload_dirs) == 0

    def test_comprehensive_layout(self, tmp_path):
        (tmp_path / "config.toml").touch()
        (tmp_path / ".env").touch()
        (tmp_path / "blog.sqlite3").touch()
        (tmp_path / "uploads").mkdir()
        (tmp_path / "backups").mkdir()
        (tmp_path / "themes").mkdir()
        (tmp_path / "logs").mkdir()
        discovery = discover_legacy_layout(tmp_path)
        assert len(discovery.config_files) == 1
        assert len(discovery.env_files) == 1
        assert len(discovery.database_files) == 1
        assert len(discovery.upload_dirs) == 1
        assert len(discovery.backup_dirs) == 1
        assert len(discovery.theme_dirs) == 1
        assert len(discovery.log_dirs) == 1


class TestLegacyDiscoveryDataclass:
    def test_default_empty_lists(self):
        d = LegacyDiscovery()
        assert d.database_files == []
        assert d.upload_dirs == []
        assert d.backup_dirs == []
        assert d.theme_dirs == []
        assert d.log_dirs == []
        assert d.config_files == []
        assert d.env_files == []
        assert d.metadata_files == []

    def test_mutable(self):
        d = LegacyDiscovery()
        d.database_files.append(Path("/test"))
        assert len(d.database_files) == 1


class TestClassifyDiscovery:
    def _make_target(self, tmp_path):
        return RuntimePaths.resolve(
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

    def test_managed_database(self, tmp_path):
        target = self._make_target(tmp_path)
        db_path = target.database.path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()
        discovery = LegacyDiscovery(database_files=[db_path])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(db_path)] == "managed"

    def test_likely_devlog_database(self, tmp_path):
        target = self._make_target(tmp_path)
        db_file = tmp_path / "other.sqlite3"
        db_file.touch()
        discovery = LegacyDiscovery(database_files=[db_file])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(db_file)] == "likely_devlog"

    def test_managed_upload_dir(self, tmp_path):
        target = self._make_target(tmp_path)
        upload_path = target.uploads_dir.path
        upload_path.mkdir(parents=True, exist_ok=True)
        discovery = LegacyDiscovery(upload_dirs=[upload_path])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(upload_path)] == "managed"

    def test_likely_devlog_upload_dir(self, tmp_path):
        target = self._make_target(tmp_path)
        upload_dir = tmp_path / "devlog-uploads"
        upload_dir.mkdir()
        discovery = LegacyDiscovery(upload_dirs=[upload_dir])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(upload_dir)] == "likely_devlog"

    def test_unknown_upload_dir(self, tmp_path):
        target = self._make_target(tmp_path)
        upload_dir = tmp_path / "random-uploads"
        upload_dir.mkdir()
        discovery = LegacyDiscovery(upload_dirs=[upload_dir])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(upload_dir)] == "unknown"

    def test_managed_config(self, tmp_path):
        target = self._make_target(tmp_path)
        config_path = target.config_file.path
        config_path.touch()
        discovery = LegacyDiscovery(config_files=[config_path])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(config_path)] == "managed"

    def test_likely_devlog_config(self, tmp_path):
        target = self._make_target(tmp_path)
        config = tmp_path / "old-config.toml"
        config.touch()
        discovery = LegacyDiscovery(config_files=[config])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(config)] == "likely_devlog"

    def test_managed_env(self, tmp_path):
        target = self._make_target(tmp_path)
        env_path = target.env_file.path
        env_path.touch()
        discovery = LegacyDiscovery(env_files=[env_path])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(env_path)] == "managed"

    def test_metadata_always_managed(self, tmp_path):
        target = self._make_target(tmp_path)
        meta = tmp_path / ".devlog-installation.json"
        meta.touch()
        discovery = LegacyDiscovery(metadata_files=[meta])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(meta)] == "managed"

    def test_managed_backups(self, tmp_path):
        target = self._make_target(tmp_path)
        backup_path = target.backups_dir.path
        backup_path.mkdir(parents=True, exist_ok=True)
        discovery = LegacyDiscovery(backup_dirs=[backup_path])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(backup_path)] == "managed"

    def test_managed_themes(self, tmp_path):
        target = self._make_target(tmp_path)
        theme_path = target.themes_dir.path
        theme_path.mkdir(parents=True, exist_ok=True)
        discovery = LegacyDiscovery(theme_dirs=[theme_path])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(theme_path)] == "managed"

    def test_likely_devlog_theme_dir(self, tmp_path):
        target = self._make_target(tmp_path)
        theme_dir = tmp_path / "devlog-themes"
        theme_dir.mkdir()
        discovery = LegacyDiscovery(theme_dirs=[theme_dir])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(theme_dir)] == "likely_devlog"

    def test_unknown_theme_dir(self, tmp_path):
        target = self._make_target(tmp_path)
        theme_dir = tmp_path / "other-themes"
        theme_dir.mkdir()
        discovery = LegacyDiscovery(theme_dirs=[theme_dir])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(theme_dir)] == "unknown"

    def test_likely_devlog_log_dir(self, tmp_path):
        target = self._make_target(tmp_path)
        log_dir = tmp_path / "devlog-logs"
        log_dir.mkdir()
        discovery = LegacyDiscovery(log_dirs=[log_dir])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(log_dir)] == "likely_devlog"

    def test_unknown_log_dir(self, tmp_path):
        target = self._make_target(tmp_path)
        log_dir = tmp_path / "nginx-logs"
        log_dir.mkdir()
        discovery = LegacyDiscovery(log_dirs=[log_dir])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(log_dir)] == "unknown"

    def test_empty_discovery(self, tmp_path):
        target = self._make_target(tmp_path)
        discovery = LegacyDiscovery()
        classifications = classify_discovery(discovery, target)
        assert classifications == {}

    def test_likely_devlog_backup_dir(self, tmp_path):
        target = self._make_target(tmp_path)
        backup_dir = tmp_path / "devlog-backups"
        backup_dir.mkdir()
        discovery = LegacyDiscovery(backup_dirs=[backup_dir])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(backup_dir)] == "likely_devlog"

    def test_unknown_backup_dir(self, tmp_path):
        target = self._make_target(tmp_path)
        backup_dir = tmp_path / "system-backups"
        backup_dir.mkdir()
        discovery = LegacyDiscovery(backup_dirs=[backup_dir])
        classifications = classify_discovery(discovery, target)
        assert classifications[str(backup_dir)] == "unknown"
