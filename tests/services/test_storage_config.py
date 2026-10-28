"""The storage backend must follow the typed configuration.

``[storage]`` in config.toml used to be inert: ``app/storage.py`` read the
environment at import time and ignored the configuration entirely.
"""

from __future__ import annotations

import pytest

from app.config.model import StorageConfig
from app.storage import _storage_settings, _upload_folder, get_storage_backend


class TestStorageSettings:
    def test_reads_the_configured_backend(self, app_with_config) -> None:
        app, configure = app_with_config
        configure(storage=StorageConfig(backend="s3", s3_bucket="blog-bucket"))

        with app.app_context():
            settings = _storage_settings()

        assert settings["backend"] == "s3"
        assert settings["s3_bucket"] == "blog-bucket"

    def test_falls_back_to_local_when_s3_is_incomplete(self, app_with_config) -> None:
        app, configure = app_with_config
        configure(storage=StorageConfig(backend="s3"))

        with app.app_context():
            backend = get_storage_backend()

        assert type(backend).__name__ == "LocalStorageBackend"

    def test_upload_folder_follows_the_app_configuration(self, app_with_config) -> None:
        app, _ = app_with_config
        app.config["UPLOAD_FOLDER"] = "/srv/uploads"

        with app.app_context():
            assert _upload_folder() == "/srv/uploads"

    def test_upload_folder_defaults_to_the_package_directory(self, app_with_config) -> None:
        app, _ = app_with_config

        with app.app_context():
            assert _upload_folder().endswith("app/static/uploads")

    def test_create_app_honours_the_configured_uploads_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        from app import create_app

        uploads = tmp_path / "uploads"
        monkeypatch.setenv("DEVLOG_UPLOADS_DIR", str(uploads))

        app = create_app()

        assert app.config["UPLOAD_FOLDER"] == str(uploads)


@pytest.fixture
def app_with_config():
    from dataclasses import replace

    from app import create_app

    app = create_app()

    def configure(**sections) -> None:
        cfg = replace(app.devlog_config, **sections)
        app.config["DEVLOG_CONFIG"] = cfg

    return app, configure
