from __future__ import annotations

from app.config.model import (
    AppConfig,
    DevLogConfig,
    HealthConfig,
    MetricsConfig,
    ServerConfig,
    SiteConfig,
)
from app.config.validation import (
    Severity,
    validate_all,
    validate_schema,
)


def _base_raw(*, config_version: int | None = None) -> dict:
    raw: dict = {
        "app": {"title": "Test"},
        "admin": {"username": "admin"},
        "server": {"host": "0.0.0.0", "port": 5000, "debug": False},
        "author": {"name": ""},
        "site": {"base_url": "http://localhost:5000"},
        "email": {"smtp_host": ""},
        "newsletter": {"send_time": "08:00"},
        "themes": {
            "default_dark": "Catppuccin Mocha",
            "default_light": "Catppuccin Latte",
            "default_scheme": "system",
        },
    }
    if config_version is not None:
        raw["config_version"] = config_version
    return raw


def _make_valid_config(
    *,
    secret_key: str = "a" * 32,
    admin_password: str = "strong-password-123",
    flask_env: str = "",
) -> DevLogConfig:
    return DevLogConfig(
        secret_key=secret_key,
        admin_password=admin_password,
        app=AppConfig(login_failure_delay=0.1),
        server=ServerConfig(debug=False),
        site=SiteConfig(base_url="http://localhost:5000"),
        session_cookie_secure=True,
        metrics=MetricsConfig(enabled=False),
        health=HealthConfig(check_secret=""),
        flask_env=flask_env,
    )


class TestUnknownKeyPolicy:
    def test_unknown_field_in_versioned_config_is_error(self) -> None:
        raw = _base_raw(config_version=1)
        raw["app"]["typo_field"] = "oops"
        findings = validate_schema(raw)
        field_findings = [f for f in findings if f.code == "schema.unknown_field"]
        assert len(field_findings) == 1
        assert field_findings[0].field == "app.typo_field"
        assert field_findings[0].severity == Severity.ERROR

    def test_unknown_section_in_versioned_config_is_error(self) -> None:
        raw = _base_raw(config_version=1)
        raw["typo_section"] = {"key": "value"}
        findings = validate_schema(raw)
        section_findings = [f for f in findings if f.code == "schema.unknown_section"]
        assert len(section_findings) == 1
        assert section_findings[0].field == "typo_section"
        assert section_findings[0].severity == Severity.ERROR

    def test_unknown_field_in_unversioned_config_is_warning(self) -> None:
        raw = _base_raw()
        raw["app"]["typo_field"] = "oops"
        findings = validate_schema(raw)
        field_findings = [f for f in findings if f.code == "schema.unknown_field"]
        assert len(field_findings) == 1
        assert field_findings[0].field == "app.typo_field"
        assert field_findings[0].severity == Severity.WARNING

    def test_strict_mode_always_errors(self) -> None:
        raw = _base_raw()
        raw["app"]["typo_field"] = "oops"
        findings = validate_schema(raw, strict=True)
        field_findings = [f for f in findings if f.code == "schema.unknown_field"]
        assert len(field_findings) == 1
        assert field_findings[0].severity == Severity.ERROR

    def test_production_mode_is_strict(self) -> None:
        config = _make_valid_config(flask_env="production")
        raw = _base_raw(config_version=1)
        raw["app"]["typo_field"] = "oops"
        result = validate_all(
            config,
            production=True,
            check_filesystem=False,
            raw_toml=raw,
        )
        field_findings = [f for f in result.findings if f.code == "schema.unknown_field"]
        assert len(field_findings) == 1
        assert field_findings[0].severity == Severity.ERROR

    def test_unknown_keys_never_influence_defaults(self) -> None:
        raw = _base_raw(config_version=1)
        raw["app"]["unknown_key"] = "some_value"
        findings = validate_schema(raw)
        defaults = DevLogConfig()
        assert defaults.app.title == "DevLog"
        assert defaults.app.posts_per_page == 10
        unknown_findings = [f for f in findings if "unknown" in f.code]
        assert all(f.severity == Severity.ERROR for f in unknown_findings)
