from __future__ import annotations

from pathlib import Path

from app.config.loader import load_effective_config
from app.config.model import SECRET_FIELDS, AiConfig, DevLogConfig
from app.config.secrets import is_secret_field
from app.config.serialization import config_to_dict, config_to_json, config_to_toml
from app.config.validation import Severity, validate_schema


def test_ai_config_defaults_and_repr_redact_key() -> None:
    assert AiConfig().provider == "openai_compatible"
    assert AiConfig().model == ""
    assert AiConfig().base_url == "http://127.0.0.1:1234/v1"
    assert AiConfig().timeout_seconds == 180
    assert AiConfig().rate_limit_per_user == ""
    assert AiConfig().api_key == ""
    assert "private-ai-key" not in repr(AiConfig(api_key="private-ai-key"))
    assert "api_key" in SECRET_FIELDS
    assert is_secret_field("ai.api_key")


def test_ai_config_serialization_redacts_every_user_visible_surface() -> None:
    config = DevLogConfig(ai=AiConfig(api_key="private-ai-key"))
    assert config_to_dict(config)["ai"]["api_key"] != "private-ai-key"
    assert "private-ai-key" not in config_to_json(config)
    assert "private-ai-key" not in config_to_toml(config)


def test_ai_key_is_loaded_from_env_file_not_toml(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[ai]\nprovider = "opencode_go"\nmodel = "glm-5.3-flash"\napi_key = "toml-key"\n',
        encoding="utf-8",
    )
    env_file = tmp_path / ".env"
    env_file.write_text("OPENCODE_GO_API_KEY=env-key\n", encoding="utf-8")
    monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)

    config = load_effective_config(config_path=config_path, env_file=env_file)

    assert config.ai.api_key == "env-key"


def test_local_compatible_model_settings_load_from_environment(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text('[ai]\nprovider = "openai_compatible"\n', encoding="utf-8")
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AI_PROVIDER=openai_compatible\n"
        "AI_MODEL=google/gemma-4-e2b\n"
        "AI_BASE_URL=http://127.0.0.1:1234/v1\n"
        "AI_TIMEOUT_SECONDS=180\n"
        "AI_RATE_LIMIT_PER_USER=4 per hour\n"
        "AI_API_KEY=local-test-key\n"
        "OPENCODE_GO_API_KEY=opencode-test-key\n",
        encoding="utf-8",
    )
    for name in (
        "AI_PROVIDER",
        "AI_MODEL",
        "AI_BASE_URL",
        "AI_TIMEOUT_SECONDS",
        "AI_RATE_LIMIT_PER_USER",
        "AI_API_KEY",
        "OPENCODE_GO_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    config = load_effective_config(config_path=config_path, env_file=env_file)

    assert config.ai.provider == "openai_compatible"
    assert config.ai.model == "google/gemma-4-e2b"
    assert config.ai.base_url == "http://127.0.0.1:1234/v1"
    assert config.ai.timeout_seconds == 180
    assert config.ai.rate_limit_per_user == "4 per hour"
    assert config.ai.api_key == "local-test-key"


def test_ai_key_in_toml_is_a_validation_error() -> None:
    findings = validate_schema({"config_version": 1, "ai": {"api_key": "not-allowed"}})
    key_findings = [
        finding for finding in findings if finding.code == "security.ai_key_in_config_file"
    ]
    assert len(key_findings) == 1
    assert key_findings[0].severity == Severity.ERROR
    assert "not-allowed" not in key_findings[0].message


def test_compatible_provider_rejects_base_urls_with_credentials_or_query() -> None:
    findings = validate_schema(
        {
            "config_version": 1,
            "ai": {
                "provider": "openai_compatible",
                "base_url": "http://user:password@localhost:1234/v1?token=secret",
            },
        }
    )

    assert any(finding.code == "schema.invalid_ai_base_url" for finding in findings)
