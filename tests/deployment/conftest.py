from __future__ import annotations

import pytest

from app.config.model import DevLogConfig


@pytest.fixture(autouse=True)
def _app_context(app, db):
    with app.app_context():
        yield


@pytest.fixture
def deployment_config(app):
    config = DevLogConfig()
    app.config["DEVLOG_CONFIG"] = config
    return config


@pytest.fixture
def system_mode_paths(tmp_path):
    dirs = {}
    for name in ["data", "log", "runtime", "config"]:
        d = tmp_path / name
        d.mkdir()
        dirs[name] = d
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET_KEY=test\n")
    config_file = tmp_path / "config.toml"
    config_file.write_text("[server]\nhost = '127.0.0.1'\n")
    dirs["env_file"] = env_file
    dirs["config_file"] = config_file
    return dirs
