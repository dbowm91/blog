from __future__ import annotations

from pathlib import Path

from app.config.model import (
    AppConfig,
    DevLogConfig,
    EmailConfig,
    HealthConfig,
    MetricsConfig,
    SchedulerConfig,
    ServerConfig,
    SiteConfig,
    StorageConfig,
    ThemesConfig,
)
from app.config.validation import (
    Finding,
    Severity,
    ValidationResult,
    finding_to_dict,
    validate_all,
    validate_compatibility,
    validate_dependencies,
    validate_filesystem,
    validate_schema,
    validate_security,
    validate_toml_string,
)


def _make_valid_config(
    *,
    secret_key: str = "a" * 32,
    admin_password: str = "strong-password-123",
    app: AppConfig | None = None,
    server: ServerConfig | None = None,
    site: SiteConfig | None = None,
    session_cookie_secure: bool = True,
    metrics: MetricsConfig | None = None,
    health: HealthConfig | None = None,
    flask_env: str = "",
) -> DevLogConfig:
    return DevLogConfig(
        secret_key=secret_key,
        admin_password=admin_password,
        app=app or AppConfig(login_failure_delay=0.1),
        server=server or ServerConfig(debug=False),
        site=site or SiteConfig(base_url="http://localhost:5000"),
        session_cookie_secure=session_cookie_secure,
        metrics=metrics or MetricsConfig(enabled=False),
        health=health or HealthConfig(check_secret=""),
        flask_env=flask_env,
    )


class TestValidateTomlString:
    def test_valid_toml(self) -> None:
        raw, findings = validate_toml_string("[app]\ntitle = 'test'\n")
        assert raw is not None
        assert findings == []

    def test_invalid_toml(self) -> None:
        raw, findings = validate_toml_string("[broken\ncan't parse")
        assert raw is None
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].code == "schema.toml_parse_error"


class TestValidateSchema:
    def test_valid_raw_passes(self) -> None:
        raw = {
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
        findings = validate_schema(raw)
        errors = [f for f in findings if f.severity == Severity.ERROR]
        assert errors == []

    def test_missing_version(self) -> None:
        raw: dict = {
            "app": {},
            "admin": {},
            "server": {},
            "author": {},
            "site": {},
            "email": {},
            "newsletter": {},
            "themes": {},
        }
        findings = validate_schema(raw)
        codes = [f.code for f in findings]
        assert "schema.missing_version" in codes

    def test_wrong_type_detected(self) -> None:
        raw = {
            "app": {"posts_per_page": "not_an_int"},
            "admin": {},
            "server": {},
            "author": {},
            "site": {},
            "email": {},
            "newsletter": {},
            "themes": {},
        }
        findings = validate_schema(raw)
        wrong_type = [f for f in findings if f.code == "schema.wrong_type"]
        assert len(wrong_type) >= 1
        assert wrong_type[0].field is not None
        assert "posts_per_page" in wrong_type[0].field

    def test_invalid_enum_value(self) -> None:
        raw = {
            "app": {"session_ip_binding": "invalid"},
            "admin": {},
            "server": {},
            "author": {},
            "site": {},
            "email": {},
            "newsletter": {},
            "themes": {},
        }
        findings = validate_schema(raw)
        enum_findings = [f for f in findings if f.code == "schema.invalid_enum"]
        assert len(enum_findings) == 1
        assert enum_findings[0].field == "app.session_ip_binding"

    def test_invalid_storage_backend(self) -> None:
        raw = {
            "app": {},
            "admin": {},
            "server": {},
            "author": {},
            "site": {},
            "email": {},
            "newsletter": {},
            "themes": {},
            "storage": {"backend": "ftp"},
        }
        findings = validate_schema(raw)
        enum_findings = [f for f in findings if f.code == "schema.invalid_enum"]
        assert any(f.field == "storage.backend" for f in enum_findings)

    def test_invalid_logging_level(self) -> None:
        raw = {
            "app": {},
            "admin": {},
            "server": {},
            "author": {},
            "site": {},
            "email": {},
            "newsletter": {},
            "themes": {},
            "logging": {"level": "TRACE"},
        }
        findings = validate_schema(raw)
        enum_findings = [f for f in findings if f.code == "schema.invalid_enum"]
        assert any(f.field == "logging.level" for f in enum_findings)

    def test_out_of_range_value(self) -> None:
        raw = {
            "app": {"posts_per_page": 0},
            "admin": {},
            "server": {},
            "author": {},
            "site": {},
            "email": {},
            "newsletter": {},
            "themes": {},
        }
        findings = validate_schema(raw)
        range_findings = [f for f in findings if f.code == "schema.out_of_range"]
        assert len(range_findings) >= 1

    def test_invalid_base_url(self) -> None:
        raw = {
            "app": {},
            "admin": {},
            "server": {},
            "author": {},
            "site": {"base_url": "not-a-url"},
            "email": {},
            "newsletter": {},
            "themes": {},
        }
        findings = validate_schema(raw)
        url_findings = [f for f in findings if f.code == "schema.invalid_base_url"]
        assert len(url_findings) == 1

    def test_invalid_send_time(self) -> None:
        raw = {
            "app": {},
            "admin": {},
            "server": {},
            "author": {},
            "site": {},
            "email": {},
            "newsletter": {"send_time": "25:00"},
            "themes": {},
        }
        findings = validate_schema(raw)
        time_findings = [f for f in findings if f.code == "schema.invalid_send_time"]
        assert len(time_findings) == 1

    def test_valid_send_time(self) -> None:
        raw = {
            "app": {},
            "admin": {},
            "server": {},
            "author": {},
            "site": {},
            "email": {},
            "newsletter": {"send_time": "23:59"},
            "themes": {},
        }
        findings = validate_schema(raw)
        time_findings = [f for f in findings if f.code == "schema.invalid_send_time"]
        assert time_findings == []


class TestValidateSecurity:
    def test_missing_secret_key(self) -> None:
        config = _make_valid_config(secret_key="")
        findings = validate_security(config)
        codes = [f.code for f in findings]
        assert "security.secret_key_missing" in codes

    def test_short_secret_key(self) -> None:
        config = _make_valid_config(secret_key="short")
        findings = validate_security(config)
        codes = [f.code for f in findings]
        assert "security.secret_key_short" in codes

    def test_valid_secret_key(self) -> None:
        config = _make_valid_config(secret_key="a" * 32)
        findings = validate_security(config)
        secret_findings = [f for f in findings if "secret_key" in (f.code or "")]
        assert secret_findings == []

    def test_missing_admin_password(self) -> None:
        config = _make_valid_config(admin_password="")
        findings = validate_security(config)
        codes = [f.code for f in findings]
        assert "security.admin_password_missing" in codes

    def test_debug_in_production(self) -> None:
        config = _make_valid_config(
            flask_env="production",
            server=ServerConfig(debug=True),
        )
        findings = validate_security(config)
        codes = [f.code for f in findings]
        assert "security.debug_in_production" in codes

    def test_debug_not_production_warning(self) -> None:
        config = _make_valid_config(
            server=ServerConfig(debug=True),
        )
        findings = validate_security(config)
        debug_findings = [f for f in findings if f.code == "security.debug_enabled"]
        assert len(debug_findings) == 1
        assert debug_findings[0].severity == Severity.WARNING

    def test_insecure_cookies_https(self) -> None:
        config = _make_valid_config(
            site=SiteConfig(base_url="https://example.com"),
            session_cookie_secure=False,
        )
        findings = validate_security(config)
        cookie_findings = [f for f in findings if f.code == "security.insecure_cookies"]
        assert len(cookie_findings) == 1

    def test_metrics_no_secret_production(self) -> None:
        config = _make_valid_config(
            flask_env="production",
            metrics=MetricsConfig(enabled=True, secret=""),
        )
        findings = validate_security(config)
        codes = [f.code for f in findings]
        assert "security.metrics_no_secret" in codes

    def test_health_secret_missing_production(self) -> None:
        config = _make_valid_config(
            flask_env="production",
            health=HealthConfig(check_secret=""),
        )
        findings = validate_security(config)
        codes = [f.code for f in findings]
        assert "security.health_secret_missing" in codes

    def test_login_failure_delay_low(self) -> None:
        config = _make_valid_config(
            app=AppConfig(login_failure_delay=0.01),
        )
        findings = validate_security(config)
        codes = [f.code for f in findings]
        assert "security.login_failure_delay_low" in codes


class TestValidateFilesystem:
    def test_missing_config_file(self, tmp_path: Path) -> None:
        config = _make_valid_config()
        missing = tmp_path / "nonexistent.toml"
        findings = validate_filesystem(config, config_path=missing)
        codes = [f.code for f in findings]
        assert "filesystem.config_unreadable" in codes

    def test_existing_config_file(self, tmp_path: Path) -> None:
        config = _make_valid_config()
        config_file = tmp_path / "config.toml"
        config_file.write_text("[app]\n")
        findings = validate_filesystem(config, config_path=config_file)
        config_errors = [f for f in findings if f.code == "filesystem.config_unreadable"]
        assert config_errors == []

    def test_no_config_path(self) -> None:
        config = _make_valid_config()
        findings = validate_filesystem(config, config_path=None)
        config_errors = [f for f in findings if f.code == "filesystem.config_unreadable"]
        assert config_errors == []


class TestValidateDependencies:
    def test_s3_without_bucket(self) -> None:
        config = DevLogConfig(
            secret_key="a" * 32,
            admin_password="pass",
            storage=StorageConfig(backend="s3", s3_bucket=""),
        )
        findings = validate_dependencies(config)
        codes = [f.code for f in findings]
        assert "dependencies.s3_fields_missing" in codes

    def test_s3_with_all_fields(self) -> None:
        config = DevLogConfig(
            secret_key="a" * 32,
            admin_password="pass",
            storage=StorageConfig(
                backend="s3",
                s3_bucket="my-bucket",
                s3_access_key="key",
                s3_secret_key="secret",
            ),
        )
        findings = validate_dependencies(config)
        s3_errors = [f for f in findings if f.code == "dependencies.s3_fields_missing"]
        assert s3_errors == []

    def test_smtp_without_from_address(self) -> None:
        config = DevLogConfig(
            secret_key="a" * 32,
            admin_password="pass",
            email=EmailConfig(smtp_host="smtp.example.com", from_address=""),
        )
        findings = validate_dependencies(config)
        codes = [f.code for f in findings]
        assert "dependencies.smtp_fields_missing" in codes

    def test_smtp_with_all_fields(self) -> None:
        config = DevLogConfig(
            secret_key="a" * 32,
            admin_password="pass",
            email=EmailConfig(smtp_host="smtp.example.com", from_address="blog@example.com"),
        )
        findings = validate_dependencies(config)
        smtp_errors = [f for f in findings if f.code == "dependencies.smtp_fields_missing"]
        assert smtp_errors == []

    def test_scheduler_no_broker(self) -> None:
        from app.config.model import CeleryConfig

        config = DevLogConfig(
            secret_key="a" * 32,
            admin_password="pass",
            scheduler=SchedulerConfig(enabled=True),
            celery=CeleryConfig(broker_url=""),
        )
        findings = validate_dependencies(config)
        codes = [f.code for f in findings]
        assert "dependencies.scheduler_no_broker" in codes

    def test_celery_unknown_broker_scheme(self) -> None:
        from app.config.model import CeleryConfig

        config = DevLogConfig(
            secret_key="a" * 32,
            admin_password="strong-password-123",
            celery=CeleryConfig(broker_url="ftp://broker:1234"),
        )
        findings = validate_dependencies(config)
        codes = [f.code for f in findings]
        assert "dependencies.celery_broker_unknown" in codes


class TestValidateCompatibility:
    def test_unsupported_version(self) -> None:
        config = DevLogConfig(version=999)
        findings = validate_compatibility(config)
        codes = [f.code for f in findings]
        assert "compatibility.unsupported_version" in codes

    def test_valid_version(self) -> None:
        config = DevLogConfig()
        findings = validate_compatibility(config)
        version_errors = [f for f in findings if f.code == "compatibility.unsupported_version"]
        assert version_errors == []

    def test_invalid_theme_name(self) -> None:
        config = DevLogConfig(
            themes=ThemesConfig(default_dark="<>invalid|name"),
        )
        findings = validate_compatibility(config)
        theme_findings = [f for f in findings if f.code == "compatibility.theme_name_invalid"]
        assert len(theme_findings) >= 1

    def test_empty_theme_name_valid(self) -> None:
        config = DevLogConfig(
            themes=ThemesConfig(default_dark=""),
        )
        findings = validate_compatibility(config)
        theme_findings = [f for f in findings if f.code == "compatibility.theme_name_invalid"]
        assert theme_findings == []


class TestValidateAll:
    def test_runs_all_layers(self) -> None:
        config = _make_valid_config()
        result = validate_all(config, check_filesystem=False)
        assert isinstance(result, ValidationResult)

    def test_production_elevates_warnings(self) -> None:
        config = _make_valid_config(
            server=ServerConfig(debug=True),
        )
        result = validate_all(config, production=True, check_filesystem=False)
        debug_findings = [f for f in result.findings if f.code == "security.debug_enabled"]
        assert debug_findings
        assert debug_findings[0].severity == Severity.ERROR

    def test_non_production_keeps_warning(self) -> None:
        config = _make_valid_config(
            server=ServerConfig(debug=True),
        )
        result = validate_all(config, production=False, check_filesystem=False)
        debug_findings = [f for f in result.findings if f.code == "security.debug_enabled"]
        assert debug_findings
        assert debug_findings[0].severity == Severity.WARNING


class TestValidationResult:
    def test_ok_with_no_errors(self) -> None:
        result = ValidationResult(
            findings=[
                Finding(
                    severity=Severity.WARNING,
                    code="test",
                    field=None,
                    message="warn",
                )
            ]
        )
        assert result.ok is True

    def test_not_ok_with_errors(self) -> None:
        result = ValidationResult(
            findings=[
                Finding(
                    severity=Severity.ERROR,
                    code="test",
                    field=None,
                    message="error",
                )
            ]
        )
        assert result.ok is False

    def test_errors_property(self) -> None:
        result = ValidationResult(
            findings=[
                Finding(severity=Severity.ERROR, code="e1", field=None, message="e"),
                Finding(severity=Severity.WARNING, code="w1", field=None, message="w"),
                Finding(severity=Severity.INFO, code="i1", field=None, message="i"),
            ]
        )
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert len(result.infos) == 1


class TestFindingToDict:
    def test_minimal(self) -> None:
        f = Finding(severity=Severity.ERROR, code="test.code", field=None, message="msg")
        d = finding_to_dict(f)
        assert d["severity"] == "error"
        assert d["code"] == "test.code"
        assert d["message"] == "msg"
        assert "field" not in d
        assert "remediation" not in d

    def test_with_field_and_remediation(self) -> None:
        f = Finding(
            severity=Severity.WARNING,
            code="test",
            field="some.field",
            message="msg",
            remediation="fix it",
        )
        d = finding_to_dict(f)
        assert d["field"] == "some.field"
        assert d["remediation"] == "fix it"
