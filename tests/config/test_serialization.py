from __future__ import annotations

import json

import pytest

from app.config.model import AiConfig, DevLogConfig
from app.config.serialization import (
    config_summary,
    config_to_dict,
    config_to_json,
    config_to_toml,
)


@pytest.fixture
def sample_config() -> DevLogConfig:
    return DevLogConfig(
        secret_key="my-super-secret-key-12345678",
        admin_password="admin-pass-123",
        ai=AiConfig(api_key="private-ai-key"),
    )


class TestConfigToDict:
    def test_returns_dict(self, sample_config: DevLogConfig) -> None:
        result = config_to_dict(sample_config)
        assert isinstance(result, dict)

    def test_secrets_redacted_by_default(self, sample_config: DevLogConfig) -> None:
        result = config_to_dict(sample_config)
        assert result["secret_key"] != "my-super-secret-key-12345678"
        assert result["admin_password"] != "admin-pass-123"
        assert result["ai"]["api_key"] != "private-ai-key"

    def test_secrets_not_redacted(self, sample_config: DevLogConfig) -> None:
        result = config_to_dict(sample_config, redact_secrets=False)
        assert result["secret_key"] == "my-super-secret-key-12345678"
        assert result["admin_password"] == "admin-pass-123"

    def test_contains_expected_keys(self, sample_config: DevLogConfig) -> None:
        result = config_to_dict(sample_config)
        assert "version" in result
        assert "app" in result
        assert "server" in result
        assert "site" in result
        assert "email" in result

    def test_nested_sections_are_dicts(self, sample_config: DevLogConfig) -> None:
        result = config_to_dict(sample_config)
        assert isinstance(result["app"], dict)
        assert isinstance(result["server"], dict)
        assert isinstance(result["site"], dict)

    def test_dict_values_preserved(self) -> None:
        config = DevLogConfig(
            search=__import__("app.config.model", fromlist=["SearchConfig"]).SearchConfig(
                config={"key": "value"},
            ),
        )
        result = config_to_dict(config)
        assert result["search"]["config"] == {"key": "value"}


class TestConfigToJson:
    def test_valid_json(self, sample_config: DevLogConfig) -> None:
        json_str = config_to_json(sample_config)
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_secrets_redacted(self, sample_config: DevLogConfig) -> None:
        json_str = config_to_json(sample_config)
        assert "my-super-secret-key" not in json_str
        assert "admin-pass-123" not in json_str
        assert "private-ai-key" not in json_str

    def test_indentation(self, sample_config: DevLogConfig) -> None:
        json_str = config_to_json(sample_config, indent=4)
        assert "\n" in json_str

    def test_no_indent(self, sample_config: DevLogConfig) -> None:
        json_str = config_to_json(sample_config, indent=None)
        assert "\n" not in json_str


class TestConfigToToml:
    def test_valid_toml_structure(self, sample_config: DevLogConfig) -> None:
        toml_str = config_to_toml(sample_config)
        assert "[app]" in toml_str
        assert "[server]" in toml_str
        assert "[site]" in toml_str
        assert "[email]" in toml_str

    def test_starts_with_version(self, sample_config: DevLogConfig) -> None:
        toml_str = config_to_toml(sample_config)
        assert toml_str.startswith("config_version = ")

    def test_secrets_redacted(self, sample_config: DevLogConfig) -> None:
        toml_str = config_to_toml(sample_config)
        assert "my-super-secret-key" not in toml_str
        assert "admin-pass-123" not in toml_str

    def test_ends_with_newline(self, sample_config: DevLogConfig) -> None:
        toml_str = config_to_toml(sample_config)
        assert toml_str.endswith("\n")

    def test_bool_formatting(self) -> None:
        config = DevLogConfig()
        toml_str = config_to_toml(config)
        assert "true" in toml_str
        assert "false" in toml_str


class TestConfigSummary:
    def test_returns_dict(self, sample_config: DevLogConfig) -> None:
        result = config_summary(sample_config)
        assert isinstance(result, dict)

    def test_contains_expected_keys(self, sample_config: DevLogConfig) -> None:
        result = config_summary(sample_config)
        expected_keys = {
            "version",
            "title",
            "base_url",
            "debug",
            "database",
            "storage",
            "scheduler",
            "themes_dark",
            "themes_light",
            "email_configured",
        }
        assert set(result.keys()) == expected_keys

    def test_no_secrets_in_summary(self, sample_config: DevLogConfig) -> None:
        result = config_summary(sample_config)
        result_str = json.dumps(result)
        assert "my-super-secret-key" not in result_str
        assert "admin-pass-123" not in result_str

    def test_email_configured_true(self) -> None:
        from app.config.model import EmailConfig

        config = DevLogConfig(email=EmailConfig(smtp_host="smtp.example.com"))
        result = config_summary(config)
        assert result["email_configured"] is True

    def test_email_configured_false(self) -> None:
        config = DevLogConfig()
        result = config_summary(config)
        assert result["email_configured"] is False

    def test_database_sqlite_default(self) -> None:
        config = DevLogConfig()
        result = config_summary(config)
        assert result["database"] == "sqlite"

    def test_database_scheme_extracted(self) -> None:
        from app.config.model import DatabaseConfig

        config = DevLogConfig(database=DatabaseConfig(uri="postgresql://host/db"))
        result = config_summary(config)
        assert result["database"] == "postgresql"
