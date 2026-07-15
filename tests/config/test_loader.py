from __future__ import annotations

from pathlib import Path

import pytest

from app.config.loader import (
    _apply_cli_overrides,
    _apply_env_overrides,
    _coerce_value,
    _load_env_file,
    _resolve_cache_redis_url,
    _resolve_celery_broker_url,
    _resolve_database_uri,
    _resolve_redis_url,
    load_effective_config,
)
from app.config.model import DevLogConfig


class TestCoerceValue:
    def test_bool_true_values(self) -> None:
        assert _coerce_value("true", bool) is True
        assert _coerce_value("1", bool) is True
        assert _coerce_value("yes", bool) is True
        assert _coerce_value("True", bool) is True

    def test_bool_false_values(self) -> None:
        assert _coerce_value("false", bool) is False
        assert _coerce_value("0", bool) is False
        assert _coerce_value("no", bool) is False
        assert _coerce_value("anything", bool) is False

    def test_int_valid(self) -> None:
        assert _coerce_value("42", int) == 42
        assert _coerce_value("0", int) == 0
        assert _coerce_value("-5", int) == -5

    def test_int_invalid(self) -> None:
        result = _coerce_value("not_a_number", int)
        assert result == "not_a_number"

    def test_float_valid(self) -> None:
        assert _coerce_value("3.14", float) == pytest.approx(3.14)
        assert _coerce_value("0", float) == 0.0

    def test_float_invalid(self) -> None:
        result = _coerce_value("not_a_float", float)
        assert result == "not_a_float"

    def test_str_passthrough(self) -> None:
        assert _coerce_value("hello", str) == "hello"


class TestResolveDatabaseUri:
    def test_database_uri_preferred(self) -> None:
        raw = {"database_uri": "sqlite:///test.db"}
        assert _resolve_database_uri(raw) == "sqlite:///test.db"

    def test_sqlalchemy_fallback(self) -> None:
        raw = {"SQLALCHEMY_DATABASE_URI": "sqlite:///legacy.db"}
        assert _resolve_database_uri(raw) == "sqlite:///legacy.db"

    def test_database_url_fallback(self) -> None:
        raw = {"DATABASE_URL": "sqlite:///url.db"}
        assert _resolve_database_uri(raw) == "sqlite:///url.db"

    def test_empty_raw_returns_sqlite_default(self) -> None:
        result = _resolve_database_uri({})
        assert "sqlite" in result


class TestResolveCacheRedisUrl:
    def test_cache_url_preferred(self) -> None:
        raw = {"redis_cache_url": "redis://cache:6379/1"}
        assert _resolve_cache_redis_url(raw) == "redis://cache:6379/1"

    def test_cache_redis_url_fallback(self) -> None:
        raw = {"CACHE_REDIS_URL": "redis://cache:6379/2"}
        assert _resolve_cache_redis_url(raw) == "redis://cache:6379/2"

    def test_redis_url_fallback(self) -> None:
        raw = {"REDIS_URL": "redis://fallback:6379/0"}
        assert _resolve_cache_redis_url(raw) == "redis://fallback:6379/0"

    def test_default(self) -> None:
        assert _resolve_cache_redis_url({}) == "redis://localhost:6379/0"


class TestResolveCeleryBrokerUrl:
    def test_celery_url_preferred(self) -> None:
        raw = {"celery_broker_url": "redis://broker:6379/0"}
        assert _resolve_celery_broker_url(raw) == "redis://broker:6379/0"

    def test_celery_broker_url_fallback(self) -> None:
        raw = {"CELERY_BROKER_URL": "redis://broker:6379/1"}
        assert _resolve_celery_broker_url(raw) == "redis://broker:6379/1"

    def test_redis_url_fallback(self) -> None:
        raw = {"REDIS_URL": "redis://fallback:6379/0"}
        assert _resolve_celery_broker_url(raw) == "redis://fallback:6379/0"

    def test_default(self) -> None:
        assert _resolve_celery_broker_url({}) == "redis://localhost:6379/0"


class TestResolveRedisUrl:
    def test_redis_url_preferred(self) -> None:
        raw = {"redis_url": "redis://custom:6379/0"}
        assert _resolve_redis_url(raw) == "redis://custom:6379/0"

    def test_env_redis_url_fallback(self) -> None:
        raw = {"REDIS_URL": "redis://env:6379/0"}
        assert _resolve_redis_url(raw) == "redis://env:6379/0"

    def test_default(self) -> None:
        assert _resolve_redis_url({}) == "redis://localhost:6379/0"


class TestApplyEnvOverrides:
    def test_env_overrides_raw(self) -> None:
        raw = {"secret_key": "old"}
        env = {"SECRET_KEY": "new"}
        result = _apply_env_overrides(raw, env)
        assert result["secret_key"] == "new"

    def test_unknown_env_keys_ignored(self) -> None:
        raw: dict = {"secret_key": "old"}
        env = {"UNKNOWN_KEY": "val"}
        result = _apply_env_overrides(raw, env)
        assert result["secret_key"] == "old"

    def test_no_env_vars(self) -> None:
        raw = {"secret_key": "val"}
        result = _apply_env_overrides(raw, {})
        assert result["secret_key"] == "val"


class TestApplyCliOverrides:
    def test_cli_overrides_raw(self) -> None:
        raw = {"secret_key": "old"}
        cli = {"secret_key": "cli_value"}
        result = _apply_cli_overrides(raw, cli)
        assert result["secret_key"] == "cli_value"

    def test_none_cli(self) -> None:
        raw = {"secret_key": "val"}
        result = _apply_cli_overrides(raw, None)
        assert result["secret_key"] == "val"

    def test_empty_cli(self) -> None:
        raw = {"secret_key": "val"}
        result = _apply_cli_overrides(raw, {})
        assert result["secret_key"] == "val"


class TestLoadEnvFile:
    def test_parse_key_value(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value\nOTHER=123\n")
        result = _load_env_file(env_file)
        assert result["KEY"] == "value"
        assert result["OTHER"] == "123"

    def test_skip_comments(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\nKEY=value\n# another\n")
        result = _load_env_file(env_file)
        assert result == {"KEY": "value"}

    def test_skip_empty_lines(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("\n\nKEY=value\n\n\n")
        result = _load_env_file(env_file)
        assert result == {"KEY": "value"}

    def test_strip_quotes(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("DOUBLE=\"hello\"\nSINGLE='world'\n")
        result = _load_env_file(env_file)
        assert result["DOUBLE"] == "hello"
        assert result["SINGLE"] == "world"

    def test_duplicate_keys_detected(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=first\nKEY=second\n")
        result = _load_env_file(env_file)
        assert result["KEY"] == "second"

    def test_malformed_line_skipped(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("NO_EQUALS_SIGN\nKEY=value\n")
        result = _load_env_file(env_file)
        assert result == {"KEY": "value"}

    def test_empty_key_skipped(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("=value\nKEY=value\n")
        result = _load_env_file(env_file)
        assert result == {"KEY": "value"}


class TestLoadEffectiveConfig:
    def test_with_explicit_path(self, tmp_config_file: Path, patched_env: None) -> None:
        config = load_effective_config(config_path=tmp_config_file, skip_env_file=True)
        assert isinstance(config, DevLogConfig)
        assert config.app.title == "Test Blog"

    def test_toml_wins_over_defaults(self, tmp_config_file: Path, patched_env: None) -> None:
        config = load_effective_config(config_path=tmp_config_file, skip_env_file=True)
        assert config.app.posts_per_page == 10
        assert config.newsletter.send_time == "08:00"

    def test_process_env_wins_over_toml(
        self, tmp_config_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SECRET_KEY", "env-secret-key-12345678901234567890")
        monkeypatch.setenv("ADMIN_PASSWORD", "env-password")
        monkeypatch.delenv("DEVLOG_CONFIG", raising=False)
        monkeypatch.delenv("DEVLOG_ENV_FILE", raising=False)
        config = load_effective_config(config_path=tmp_config_file, skip_env_file=True)
        assert config.secret_key == "env-secret-key-12345678901234567890"
        assert config.admin_password == "env-password"

    def test_env_file_wins_over_toml_for_redis_url(
        self, tmp_config_file: Path, tmp_path: Path, patched_env: None
    ) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("REDIS_URL=redis://env-redis:6379/0\n")
        config = load_effective_config(config_path=tmp_config_file, env_file=env_file)
        assert config.redis.url == "redis://env-redis:6379/0"

    def test_cli_overrides_wins_over_all(self, tmp_config_file: Path, patched_env: None) -> None:
        config = load_effective_config(
            config_path=tmp_config_file,
            skip_env_file=True,
            cli_overrides={"title": "CLI Title"},
        )
        assert config.app.title == "CLI Title"

    def test_no_config_file_returns_defaults(self, patched_env: None) -> None:
        config = load_effective_config(
            config_path=Path("/nonexistent/config.toml"), skip_env_file=True
        )
        assert isinstance(config, DevLogConfig)
        assert config.app.title == "DevLog"

    def test_database_uri_legacy_sqlalchemy_fallback(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", "sqlite:///legacy.db")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("DEVLOG_CONFIG", raising=False)
        monkeypatch.delenv("DEVLOG_ENV_FILE", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[app]\ntitle = 'Test'\n\n[admin]\nusername = 'admin'\n\n"
            "[server]\nhost = '0.0.0.0'\nport = 5000\ndebug = false\n\n"
            "[author]\nname = ''\n\n[site]\nbase_url = 'http://localhost:5000'\n\n"
            "[email]\nsmtp_host = ''\n\n[newsletter]\nsend_time = '08:00'\n\n"
            "[themes]\ndefault_dark = 'Catppuccin Mocha'\ndefault_light = 'Catppuccin Latte'\n"
            "default_scheme = 'system'\n"
        )
        config = load_effective_config(config_path=config_file, skip_env_file=True)
        assert config.database.uri == "sqlite:///legacy.db"

    def test_database_uri_database_url_fallback(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
        monkeypatch.setenv("DATABASE_URL", "sqlite:///from_url.db")
        monkeypatch.delenv("DEVLOG_CONFIG", raising=False)
        monkeypatch.delenv("DEVLOG_ENV_FILE", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[app]\ntitle = 'Test'\n\n[admin]\nusername = 'admin'\n\n"
            "[server]\nhost = '0.0.0.0'\nport = 5000\ndebug = false\n\n"
            "[author]\nname = ''\n\n[site]\nbase_url = 'http://localhost:5000'\n\n"
            "[email]\nsmtp_host = ''\n\n[newsletter]\nsend_time = '08:00'\n\n"
            "[themes]\ndefault_dark = 'Catppuccin Mocha'\ndefault_light = 'Catppuccin Latte'\n"
            "default_scheme = 'system'\n"
        )
        config = load_effective_config(config_path=config_file, skip_env_file=True)
        assert config.database.uri == "sqlite:///from_url.db"

    def test_scheduler_enabled_from_env(
        self, tmp_config_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ENABLE_SCHEDULER", "true")
        monkeypatch.delenv("DEVLOG_CONFIG", raising=False)
        monkeypatch.delenv("DEVLOG_ENV_FILE", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
        config = load_effective_config(config_path=tmp_config_file, skip_env_file=True)
        assert config.scheduler.enabled is True

    def test_session_cookie_secure_from_env(
        self, tmp_config_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
        monkeypatch.delenv("DEVLOG_CONFIG", raising=False)
        monkeypatch.delenv("DEVLOG_ENV_FILE", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
        config = load_effective_config(config_path=tmp_config_file, skip_env_file=True)
        assert config.session_cookie_secure is False
