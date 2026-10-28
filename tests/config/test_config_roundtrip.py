"""Config round-trip and precedence regression tests.

The config file written by onboarding has to survive a trip through the
loader, and environment variables have to keep winning over the file — both
were broken and both are load-bearing for a deployment.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from app.config.loader import load_effective_config
from app.config.model import (
    BackupConfig,
    DatabaseConfig,
    DevLogConfig,
    HealthConfig,
    MetricsConfig,
    SchedulerConfig,
    StorageConfig,
)
from app.config.serialization import config_to_toml


def _sample_config() -> DevLogConfig:
    return DevLogConfig(
        database=DatabaseConfig(uri="sqlite:////var/lib/devlog/devlog.sqlite3"),
        scheduler=SchedulerConfig(enabled=True),
        storage=StorageConfig(backend="s3", s3_bucket="blog-bucket"),
        health=HealthConfig(check_secret="health-secret-value"),
        metrics=MetricsConfig(enabled=True, secret="metrics-secret-value"),
        backup=BackupConfig(data_backup_dir="/var/lib/devlog/backups"),
        secret_key="a" * 40,
        admin_password="admin-password-value",
    )


class TestConfigToToml:
    def test_writes_every_model_section(self) -> None:
        toml_text = config_to_toml(_sample_config())
        parsed = tomllib.loads(toml_text)

        for section in (
            "app",
            "admin",
            "server",
            "author",
            "site",
            "email",
            "newsletter",
            "comments",
            "themes",
            "database",
            "redis",
            "celery",
            "scheduler",
            "storage",
            "health",
            "metrics",
            "backup",
            "security",
            "webhook",
            "logging",
            "search",
            "paths",
        ):
            assert section in parsed, f"missing [{section}] in the written config"

    def test_writes_the_database_uri(self) -> None:
        toml_text = config_to_toml(_sample_config())
        parsed = tomllib.loads(toml_text)

        assert parsed["database"]["uri"] == "sqlite:////var/lib/devlog/devlog.sqlite3"

    def test_secret_values_are_not_written(self) -> None:
        toml_text = config_to_toml(_sample_config())

        for secret in (
            "a" * 40,
            "admin-password-value",
            "health-secret-value",
            "metrics-secret-value",
        ):
            assert secret not in toml_text

    def test_secret_fields_are_written_empty(self) -> None:
        parsed = tomllib.loads(config_to_toml(_sample_config()))

        assert parsed["health"]["check_secret"] == ""
        assert parsed["metrics"]["secret"] == ""
        assert parsed["storage"]["s3_access_key"] == ""
        assert parsed["storage"]["s3_secret_key"] == ""

    def test_round_trips_through_the_loader(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The environment wins over the file, so the file's own value can only
        # be observed when no override is present.
        monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        config_path = tmp_path / "config.toml"
        config_path.write_text(config_to_toml(_sample_config()))

        loaded = load_effective_config(
            config_path=config_path,
            env_file=tmp_path / "missing.env",
            skip_env_file=True,
        )

        assert loaded.database.uri == "sqlite:////var/lib/devlog/devlog.sqlite3"
        assert loaded.scheduler.enabled is True
        assert loaded.storage.backend == "s3"
        assert loaded.storage.s3_bucket == "blog-bucket"
        assert loaded.metrics.enabled is True
        assert loaded.backup.data_backup_dir == "/var/lib/devlog/backups"

    def test_round_trip_preserves_value_types(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        config_path.write_text(config_to_toml(_sample_config()))

        loaded = load_effective_config(
            config_path=config_path,
            env_file=tmp_path / "missing.env",
            skip_env_file=True,
        )

        assert isinstance(loaded.app.posts_per_page, int)
        assert isinstance(loaded.server.port, int)
        assert isinstance(loaded.server.debug, bool)
        assert isinstance(loaded.app.token_enumeration_delay, float)


class TestPrecedence:
    def test_env_var_overrides_a_config_file_section_field(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            'config_version = 1\n[app]\ntitle = "FromFile"\n[site]\nbase_url = "http://file"\n'
        )

        monkeypatch.setenv("APP_TITLE", "FromEnv")
        monkeypatch.setenv("BASE_URL", "https://env.example")

        loaded = load_effective_config(
            config_path=config_path,
            env_file=tmp_path / "missing.env",
            skip_env_file=True,
        )

        assert loaded.app.title == "FromEnv"
        assert loaded.site.base_url == "https://env.example"

    def test_env_var_is_coerced_to_the_field_type(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = tmp_path / "config.toml"
        config_path.write_text("config_version = 1\n[server]\nport = 5000\n")

        monkeypatch.setenv("SERVER_PORT", "8080")
        monkeypatch.setenv("ENABLE_METRICS", "true")

        loaded = load_effective_config(
            config_path=config_path,
            env_file=tmp_path / "missing.env",
            skip_env_file=True,
        )

        assert loaded.server.port == 8080
        assert isinstance(loaded.server.port, int)
        assert loaded.metrics.enabled is True

    def test_config_file_wins_when_no_env_var_is_set(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        config_path.write_text('config_version = 1\n[app]\ntitle = "FromFile"\n')

        loaded = load_effective_config(
            config_path=config_path,
            env_file=tmp_path / "missing.env",
            skip_env_file=True,
        )

        assert loaded.app.title == "FromFile"

    def test_sections_sharing_a_key_name_do_not_collide(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            "config_version = 1\n[scheduler]\nenabled = true\n[metrics]\nenabled = false\n"
        )

        loaded = load_effective_config(
            config_path=config_path,
            env_file=tmp_path / "missing.env",
            skip_env_file=True,
        )

        assert loaded.scheduler.enabled is True
        assert loaded.metrics.enabled is False
