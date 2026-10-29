"""The application must never write into its own installation directory.

The container image copies the source tree into a root-owned directory and
runs the application as an unprivileged user, with DEVLOG_DATA_DIR,
DEVLOG_LOG_DIR and DEVLOG_RUNTIME_DIR pointing at writable volumes. Before
the fix the factory created ``<source>/instance``, ``<source>/logs`` and
``<source>/app/static/uploads``, which raised PermissionError in the
container and restarted the service in a loop.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture()
def runtime_dirs(tmp_path, monkeypatch):
    """Point the application at writable directories outside the source tree."""
    data = tmp_path / "data"
    logs = tmp_path / "var-log"
    runtime = tmp_path / "run"
    for directory in (data, logs, runtime):
        directory.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("SECRET_KEY", "runtime-directories-secret-key-32-chars")
    monkeypatch.setenv("ADMIN_PASSWORD", "runtime-directories-password")
    monkeypatch.setenv("DEVLOG_DATA_DIR", str(data))
    monkeypatch.setenv("DEVLOG_LOG_DIR", str(logs))
    monkeypatch.setenv("DEVLOG_RUNTIME_DIR", str(runtime))
    return data, logs, runtime


def test_instance_path_follows_the_runtime_directory(runtime_dirs):
    """Lock files and the legacy database fallback belong to the runtime dir."""
    from app import create_app

    _, _, runtime = runtime_dirs
    app = create_app()

    assert Path(app.instance_path) == runtime


def test_upload_folder_follows_the_data_directory(runtime_dirs):
    """Uploaded media belongs beside the database, not in the source tree."""
    from app import create_app

    data, _, _ = runtime_dirs
    app = create_app()

    assert Path(app.config["UPLOAD_FOLDER"]) == data / "uploads"
    assert Path(app.config["UPLOAD_FOLDER"]).is_dir()


def test_log_directory_follows_the_configured_directory(runtime_dirs):
    """The log file is written to the configured log directory."""
    from app import configure_logging, create_app

    _, logs, _ = runtime_dirs
    app = create_app()

    configure_logging(app)

    assert (logs / "blog.log").exists()


def test_no_directory_is_created_inside_the_source_tree(runtime_dirs):
    """The factory must not create anything next to the application code."""
    from app import create_app

    source_root = Path(__file__).resolve().parent.parent
    before = {p.name for p in source_root.iterdir()}

    create_app()

    after = {p.name for p in source_root.iterdir()}
    assert after == before, "the factory created a directory in the source tree"


def test_defaults_are_unchanged_without_configuration(monkeypatch):
    """Without the environment variables the legacy locations still apply."""
    from flask import Flask

    from app import create_app

    for name in ("DEVLOG_DATA_DIR", "DEVLOG_LOG_DIR", "DEVLOG_RUNTIME_DIR"):
        monkeypatch.delenv(name, raising=False)

    app = create_app()

    assert Path(app.instance_path) == Path(Flask("app").instance_path)
    assert app.config["UPLOAD_FOLDER"].endswith(os.path.join("app", "static", "uploads"))
