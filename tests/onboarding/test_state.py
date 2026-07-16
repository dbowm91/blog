from __future__ import annotations

import sqlite3

from app.onboarding.state import (
    InstallState,
    detect_installation,
    load_metadata,
    save_metadata,
)


class TestDetectInstallation:
    def test_fresh_installation(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()

        info = detect_installation(config_path=empty / "config.toml", data_path=empty / "data")

        assert info.state == InstallState.FRESH
        assert info.config_exists is False
        assert info.database_exists is False
        assert info.admin_exists is False

    def test_partial_config_exists(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[app]\ntitle = 'Test'")

        info = detect_installation(config_path=config_file, data_path=tmp_path)

        assert info.state == InstallState.PARTIAL
        assert info.config_exists is True
        assert info.database_exists is False
        assert info.admin_exists is False

    def test_partial_database_exists(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "blog.db"
        conn = sqlite3.connect(str(db_path))
        conn.close()

        info = detect_installation(config_path=tmp_path / "missing.toml", data_path=data_dir)

        assert info.state == InstallState.PARTIAL
        assert info.database_exists is True
        assert info.config_exists is False

    def test_complete_installation(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[app]\ntitle = 'Test'")

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "blog.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE user (id INTEGER PRIMARY KEY, username TEXT, is_admin INTEGER DEFAULT 0)"
        )
        conn.execute("INSERT INTO user (username, is_admin) VALUES ('admin', 1)")
        conn.commit()
        conn.close()

        info = detect_installation(config_path=config_file, data_path=data_dir)

        assert info.state == InstallState.COMPLETE
        assert info.config_exists is True
        assert info.database_exists is True
        assert info.admin_exists is True

    def test_config_path_returned_when_exists(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[app]\ntitle = 'Test'")

        info = detect_installation(config_path=config_file, data_path=tmp_path)

        assert info.config_path == config_file

    def test_config_path_none_when_missing(self, tmp_path):
        info = detect_installation(config_path=tmp_path / "missing.toml", data_path=tmp_path)

        assert info.config_path is None

    def test_database_path_returned_when_exists(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "blog.db"
        conn = sqlite3.connect(str(db_path))
        conn.close()

        info = detect_installation(config_path=tmp_path / "missing.toml", data_path=data_dir)

        assert info.data_path == db_path

    def test_database_path_none_when_missing(self, tmp_path):
        info = detect_installation(config_path=tmp_path / "missing.toml", data_path=tmp_path)

        assert info.data_path is None

    def test_metadata_exists_when_file_present(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "onboarding-metadata.json").write_text('{"version": 1}')

        info = detect_installation(config_path=tmp_path / "missing.toml", data_path=data_dir)

        assert info.metadata_exists is True

    def test_metadata_not_exists_when_no_data_dir(self, tmp_path):
        info = detect_installation(
            config_path=tmp_path / "missing.toml", data_path=tmp_path / "noexist"
        )

        assert info.metadata_exists is False


class TestSaveAndLoadMetadata:
    def test_roundtrip(self, tmp_path):
        data = {"key": "value", "nested": {"a": 1}}
        save_metadata(data_path=tmp_path, metadata=data)
        loaded = load_metadata(data_path=tmp_path)

        assert loaded == data

    def test_save_creates_directory(self, tmp_path):
        target = tmp_path / "subdir" / "data"
        save_metadata(data_path=target, metadata={"x": 1})

        assert (target / "onboarding-metadata.json").exists()

    def test_save_none_metadata_noop(self, tmp_path):
        save_metadata(data_path=tmp_path, metadata=None)

        assert not (tmp_path / "onboarding-metadata.json").exists()

    def test_load_missing_returns_none(self, tmp_path):
        result = load_metadata(data_path=tmp_path / "noexist")

        assert result is None


class TestIsComplete:
    def test_true_with_completed_at(self):
        from app.onboarding.metadata import OnboardingMetadata, is_complete

        meta = OnboardingMetadata(
            version=1,
            mode="native",
            profile="development",
            package_version="1.0.0",
            completed_at="2025-01-01T00:00:00",
            config_path="/config.toml",
            data_path="/data",
            managed_paths=[],
            admin_username="admin",
        )

        assert is_complete(meta) is True

    def test_none_returns_false(self):
        from app.onboarding.metadata import is_complete

        assert is_complete(None) is False

    def test_empty_completed_at_returns_false(self):
        from app.onboarding.metadata import OnboardingMetadata, is_complete

        meta = OnboardingMetadata(
            version=1,
            mode="native",
            profile="development",
            package_version="1.0.0",
            completed_at="",
            config_path="/config.toml",
            data_path="/data",
            managed_paths=[],
            admin_username="admin",
        )

        assert is_complete(meta) is False

    def test_wrong_version_returns_false(self):
        from app.onboarding.metadata import OnboardingMetadata, is_complete

        meta = OnboardingMetadata(
            version=99,
            mode="native",
            profile="development",
            package_version="1.0.0",
            completed_at="2025-01-01T00:00:00",
            config_path="/config.toml",
            data_path="/data",
            managed_paths=[],
            admin_username="admin",
        )

        assert is_complete(meta) is False
