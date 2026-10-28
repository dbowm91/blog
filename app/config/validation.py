"""Multi-layered configuration validation with categorized findings."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.config.model import CONFIG_VERSION, DevLogConfig

SUPPORTED_VERSIONS = {CONFIG_VERSION}

REQUIRED_SECTIONS = frozenset(
    {"app", "admin", "server", "author", "site", "email", "newsletter", "themes"}
)

VALID_SESSION_IP_BINDING = frozenset({"off", "warn", "enforce"})
VALID_DEFAULT_SCHEME = frozenset({"system", "dark", "light"})
VALID_SEARCH_PROVIDER = frozenset({"sqlite", "meilisearch", "typesense"})
VALID_AI_PROVIDER = frozenset({"opencode_go"})
VALID_STORAGE_BACKEND = frozenset({"local", "s3"})
VALID_LOGGING_LEVEL = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

SECTION_FIELD_TYPES: dict[str, dict[str, type | tuple[type, ...]]] = {
    "app": {
        "title": str,
        "description": str,
        "posts_per_page": int,
        "max_viewed_posts": int,
        "session_lifetime_hours": int,
        "session_ip_binding": str,
        "tag_cache_ttl_seconds": int,
        "dashboard_per_page": int,
        "subscribers_per_page": int,
        "media_per_page": int,
        "media_max_files": int,
        "max_upload_size": int,
        "export_batch_size": int,
        "fts_result_limit": int,
        "page_view_buffer_size": int,
        "token_enumeration_delay": (int, float),
        "login_failure_delay": (int, float),
        "preview_token_expiry_days": int,
        "analytics_days_min": int,
        "analytics_days_max": int,
    },
    "admin": {
        "username": str,
    },
    "server": {
        "host": str,
        "port": int,
        "debug": bool,
    },
    "author": {
        "name": str,
        "role": str,
        "avatar": str,
    },
    "site": {
        "base_url": str,
        "cdn_url": str,
        "related_posts_count": int,
    },
    "email": {
        "smtp_host": str,
        "smtp_port": int,
        "smtp_user": str,
        "smtp_password": str,
        "from_address": str,
        "smtp_timeout": int,
    },
    "newsletter": {
        "send_time": str,
        "confirmation_expiry_hours": int,
        "max_retry_attempts": int,
    },
    "comments": {
        "min_length": int,
        "max_length": int,
        "rate_limit_per_ip": str,
        "rate_limit_per_post": str,
        "notify_pending": bool,
        "spam_words": str,
    },
    "themes": {
        "external_dir": str,
        "allow_external": bool,
        "strict_validation": bool,
        "default_dark": str,
        "default_light": str,
        "default_scheme": str,
    },
    "database": {
        "uri": str,
        "pool_size": int,
        "max_overflow": int,
        "pool_recycle": int,
    },
    "redis": {
        "url": str,
        "cache_url": str,
        "rate_limit_url": str,
    },
    "celery": {
        "broker_url": str,
    },
    "scheduler": {
        "enabled": bool,
    },
    "storage": {
        "backend": str,
        "s3_bucket": str,
        "s3_region": str,
        "s3_access_key": str,
        "s3_secret_key": str,
        "s3_endpoint": str,
        "s3_public_url": str,
    },
    "health": {
        "check_secret": str,
    },
    "metrics": {
        "enabled": bool,
        "secret": str,
    },
    "backup": {
        "data_backup_dir": str,
        "encryption_key": str,
    },
    "security": {
        "max_failed_attempts": int,
        "lockout_duration_minutes": int,
    },
    "webhook": {
        "timeout": int,
        "encryption_key": str,
    },
    "logging": {
        "level": str,
    },
    "search": {
        "provider": str,
        "config": dict,
    },
    "ai": {
        "provider": str,
        "model": str,
        "api_key": str,
    },
}

NUMERIC_RANGES: dict[str, tuple[int, int]] = {
    "app.posts_per_page": (1, 100),
    "app.max_viewed_posts": (1, 10_000),
    "app.session_lifetime_hours": (1, 8760),
    "app.tag_cache_ttl_seconds": (1, 86400),
    "app.dashboard_per_page": (1, 500),
    "app.subscribers_per_page": (1, 1000),
    "app.media_per_page": (1, 1000),
    "app.media_max_files": (1, 100_000),
    "app.max_upload_size": (1, 1_073_741_824),
    "app.export_batch_size": (1, 10_000),
    "app.fts_result_limit": (1, 10_000),
    "app.analytics_days_min": (1, 365),
    "app.analytics_days_max": (1, 3650),
    "app.preview_token_expiry_days": (1, 365),
    "server.port": (1, 65535),
    "email.smtp_port": (1, 65535),
    "email.smtp_timeout": (1, 300),
    "newsletter.confirmation_expiry_hours": (1, 720),
    "newsletter.max_retry_attempts": (1, 50),
    "comments.min_length": (1, 1000),
    "comments.max_length": (10, 100_000),
    "database.pool_size": (1, 100),
    "database.max_overflow": (0, 100),
    "database.pool_recycle": (60, 86400),
    "webhook.timeout": (1, 120),
    "security.max_failed_attempts": (1, 100),
    "security.lockout_duration_minutes": (1, 1440),
}


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Finding:
    severity: Severity
    code: str
    field: str | None
    message: str
    remediation: str | None = None


@dataclass
class ValidationResult:
    findings: list[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(f.severity == Severity.ERROR for f in self.findings)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == Severity.WARNING]

    @property
    def infos(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == Severity.INFO]


def finding_to_dict(f: Finding) -> dict:
    d: dict[str, Any] = {
        "severity": f.severity.value,
        "code": f.code,
        "message": f.message,
    }
    if f.field is not None:
        d["field"] = f.field
    if f.remediation is not None:
        d["remediation"] = f.remediation
    return d


def validate_toml_string(toml_content: str) -> tuple[dict | None, list[Finding]]:
    try:
        raw = tomllib.loads(toml_content)
        return raw, []
    except tomllib.TOMLDecodeError as e:
        return None, [
            Finding(
                severity=Severity.ERROR,
                code="schema.toml_parse_error",
                field=None,
                message=f"TOML parse error: {e}",
            )
        ]


def validate_schema(raw_toml: dict, *, strict: bool = False) -> list[Finding]:
    findings: list[Finding] = []

    version = raw_toml.get("config_version")
    is_versioned = (
        version is not None and isinstance(version, int) and version in SUPPORTED_VERSIONS
    )

    if strict or is_versioned:
        unknown_severity = Severity.ERROR
    else:
        unknown_severity = Severity.WARNING

    if version is None:
        findings.append(
            Finding(
                severity=Severity.WARNING,
                code="schema.missing_version",
                field="config_version",
                message="config_version not set; assuming version 1",
                remediation=f"Add 'config_version = {CONFIG_VERSION}' to the top of config.toml",
            )
        )
    elif not isinstance(version, int):
        findings.append(
            Finding(
                severity=Severity.ERROR,
                code="schema.invalid_version",
                field="version",
                message=f"config_version must be an integer, got {type(version).__name__}",
            )
        )
    elif version not in SUPPORTED_VERSIONS:
        findings.append(
            Finding(
                severity=Severity.ERROR,
                code="schema.unsupported_version",
                field="version",
                message=f"config_version {version} is not supported; expected one of {sorted(SUPPORTED_VERSIONS)}",
            )
        )

    for req_section in REQUIRED_SECTIONS:
        if req_section not in raw_toml:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    code="schema.missing_section",
                    field=req_section,
                    message=f"Required section '[{req_section}]' is missing",
                )
            )

    known_top_level = set(SECTION_FIELD_TYPES) | {"version", "config_version"}
    for key in raw_toml:
        if key not in known_top_level:
            findings.append(
                Finding(
                    severity=unknown_severity,
                    code="schema.unknown_top_level_key",
                    field=key,
                    message=f"Unrecognized top-level key: {key!r}",
                )
            )

    for section_name in raw_toml:
        if not isinstance(raw_toml[section_name], dict):
            continue
        if section_name not in SECTION_FIELD_TYPES:
            findings.append(
                Finding(
                    severity=unknown_severity,
                    code="schema.unknown_section",
                    field=section_name,
                    message=f"Unrecognized config section: [{section_name}]",
                )
            )

    for section_name, field_types in SECTION_FIELD_TYPES.items():
        section = raw_toml.get(section_name)
        if not isinstance(section, dict):
            continue
        for field_name in section:
            if field_name not in field_types:
                findings.append(
                    Finding(
                        severity=unknown_severity,
                        code="schema.unknown_field",
                        field=f"{section_name}.{field_name}",
                        message=f"Unrecognized field in [{section_name}]: {field_name!r}",
                    )
                )
        for field_name, expected in field_types.items():
            value = section.get(field_name)
            if value is None:
                continue
            if isinstance(expected, tuple):
                if not isinstance(value, expected):
                    expected_names = " or ".join(t.__name__ for t in expected)
                    findings.append(
                        Finding(
                            severity=Severity.ERROR,
                            code="schema.wrong_type",
                            field=f"{section_name}.{field_name}",
                            message=f"{section_name}.{field_name}: expected {expected_names}, got {type(value).__name__}",
                        )
                    )
            elif not isinstance(value, expected):
                findings.append(
                    Finding(
                        severity=Severity.ERROR,
                        code="schema.wrong_type",
                        field=f"{section_name}.{field_name}",
                        message=f"{section_name}.{field_name}: expected {expected.__name__}, got {type(value).__name__}",
                    )
                )

    enum_checks: list[tuple[str, str, frozenset[str]]] = [
        ("app", "session_ip_binding", VALID_SESSION_IP_BINDING),
        ("themes", "default_scheme", VALID_DEFAULT_SCHEME),
        ("search", "provider", VALID_SEARCH_PROVIDER),
        ("ai", "provider", VALID_AI_PROVIDER),
        ("storage", "backend", VALID_STORAGE_BACKEND),
        ("logging", "level", VALID_LOGGING_LEVEL),
    ]
    for enum_section, enum_field, valid_values in enum_checks:
        enum_sec = raw_toml.get(enum_section)
        if not isinstance(enum_sec, dict):
            continue
        enum_val = enum_sec.get(enum_field)
        if enum_val is not None and enum_val not in valid_values:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    code="schema.invalid_enum",
                    field=f"{enum_section}.{enum_field}",
                    message=f"{enum_section}.{enum_field}: {enum_val!r} is not valid; expected one of {sorted(valid_values)}",
                )
            )

    for dotted_path, (lo, hi) in NUMERIC_RANGES.items():
        parts = dotted_path.split(".")
        range_section, range_field = parts[0], parts[1]
        range_sec = raw_toml.get(range_section)
        if not isinstance(range_sec, dict):
            continue
        range_val = range_sec.get(range_field)
        if range_val is None or not isinstance(range_val, (int, float)):
            continue
        if not (lo <= range_val <= hi):
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    code="schema.out_of_range",
                    field=dotted_path,
                    message=f"{dotted_path}: {range_val} is out of range ({lo}-{hi})",
                )
            )

    base_url = ""
    site_section = raw_toml.get("site")
    if isinstance(site_section, dict):
        base_url = str(site_section.get("base_url", ""))
    if base_url:
        parsed = urlparse(base_url)
        if not parsed.scheme or not parsed.netloc:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    code="schema.invalid_base_url",
                    field="site.base_url",
                    message=f"base_url must be a full URL with scheme and domain, got: {base_url!r}",
                )
            )

    send_time: str | None = None
    newsletter_section = raw_toml.get("newsletter")
    if isinstance(newsletter_section, dict):
        send_time = newsletter_section.get("send_time")
    if send_time is not None:
        try:
            parts = send_time.split(":")
            h, m = int(parts[0]), int(parts[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
        except (ValueError, IndexError):
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    code="schema.invalid_send_time",
                    field="newsletter.send_time",
                    message=f"newsletter.send_time must be HH:MM (00:00-23:59), got: {send_time!r}",
                )
            )

    ai_section = raw_toml.get("ai")
    if isinstance(ai_section, dict) and ai_section.get("api_key"):
        findings.append(
            Finding(
                severity=Severity.ERROR,
                code="security.ai_key_in_config_file",
                field="ai.api_key",
                message="AI provider credentials must be supplied through the server environment, not config.toml",
                remediation="Remove ai.api_key and set OPENCODE_GO_API_KEY in the server environment or .env file",
            )
        )

    return findings


def validate_security(config: DevLogConfig) -> list[Finding]:
    findings: list[Finding] = []
    production = config.is_production()

    if not config.secret_key:
        findings.append(
            Finding(
                severity=Severity.ERROR,
                code="security.secret_key_missing",
                field="secret_key",
                message="SECRET_KEY is not set",
                remediation="Set SECRET_KEY environment variable to a random string >= 32 characters",
            )
        )
    elif len(config.secret_key) < 32:
        findings.append(
            Finding(
                severity=Severity.ERROR,
                code="security.secret_key_short",
                field="secret_key",
                message=f"SECRET_KEY is {len(config.secret_key)} characters; minimum is 32",
            )
        )

    if not config.admin_password:
        findings.append(
            Finding(
                severity=Severity.ERROR,
                code="security.admin_password_missing",
                field="admin_password",
                message="ADMIN_PASSWORD is not set",
                remediation="Set ADMIN_PASSWORD environment variable to a strong password",
            )
        )

    if config.server.debug and production:
        findings.append(
            Finding(
                severity=Severity.ERROR,
                code="security.debug_in_production",
                field="server.debug",
                message="debug=true in production is a security risk",
                remediation="Set server.debug = false for production deployments",
            )
        )
    elif config.server.debug:
        findings.append(
            Finding(
                severity=Severity.WARNING,
                code="security.debug_enabled",
                field="server.debug",
                message="debug mode is enabled; ensure this is disabled in production",
            )
        )

    parsed = urlparse(config.site.base_url)
    base_is_https = parsed.scheme == "https"
    if base_is_https and not config.session_cookie_secure:
        severity = Severity.ERROR if production else Severity.WARNING
        findings.append(
            Finding(
                severity=severity,
                code="security.insecure_cookies",
                field="session_cookie_secure",
                message="SESSION_COOKIE_SECURE=false but base_url uses HTTPS; cookies will be sent over insecure connections",
                remediation="Set SESSION_COOKIE_SECURE=true for HTTPS deployments",
            )
        )
    elif not base_is_https and config.session_cookie_secure and production:
        findings.append(
            Finding(
                severity=Severity.WARNING,
                code="security.secure_cookie_http_url",
                field="session_cookie_secure",
                message="SESSION_COOKIE_SECURE=true but base_url uses HTTP; cookies may not be sent",
            )
        )

    if config.metrics.enabled and production and not config.metrics.secret:
        findings.append(
            Finding(
                severity=Severity.ERROR,
                code="security.metrics_no_secret",
                field="metrics.secret",
                message="METRICS_SECRET is required when ENABLE_METRICS=true in production",
                remediation="Set METRICS_SECRET environment variable",
            )
        )

    if production and not config.health.check_secret:
        findings.append(
            Finding(
                severity=Severity.WARNING,
                code="security.health_secret_missing",
                field="health.check_secret",
                message="HEALTH_CHECK_SECRET is not set; detailed health checks will be unavailable in production",
                remediation="Set HEALTH_CHECK_SECRET environment variable",
            )
        )

    if config.app.login_failure_delay < 0.1:
        findings.append(
            Finding(
                severity=Severity.WARNING,
                code="security.login_failure_delay_low",
                field="app.login_failure_delay",
                message=f"login_failure_delay ({config.app.login_failure_delay}s) is below recommended minimum of 0.1s",
            )
        )

    if production and not config.session_cookie_secure:
        findings.append(
            Finding(
                severity=Severity.ERROR,
                code="security.session_cookie_not_secure",
                field="session_cookie_secure",
                message="SESSION_COOKIE_SECURE must be true in production behind HTTPS",
            )
        )

    return findings


def validate_filesystem(
    config: DevLogConfig,
    config_path: Path | None = None,
) -> list[Finding]:
    findings: list[Finding] = []

    if config_path is not None:
        if not config_path.exists():
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    code="filesystem.config_unreadable",
                    field="config_path",
                    message=f"Config file does not exist: {config_path}",
                )
            )
        elif not os.access(config_path, os.R_OK):
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    code="filesystem.config_unreadable",
                    field="config_path",
                    message=f"Config file is not readable: {config_path}",
                )
            )

    upload_dir = Path("app/static/uploads")
    try:
        if upload_dir.exists() and not os.access(upload_dir, os.W_OK):
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    code="filesystem.upload_dir_not_writable",
                    field="upload_dir",
                    message=f"Upload directory is not writable: {upload_dir}",
                )
            )
    except OSError:
        findings.append(
            Finding(
                severity=Severity.WARNING,
                code="filesystem.upload_dir_not_writable",
                field="upload_dir",
                message=f"Cannot check upload directory permissions: {upload_dir}",
            )
        )

    backup_dir = Path(config.backup.data_backup_dir)
    if backup_dir.exists():
        if not os.access(backup_dir, os.W_OK):
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    code="filesystem.backup_dir_not_writable",
                    field="backup.data_backup_dir",
                    message=f"Backup directory is not writable: {backup_dir}",
                )
            )
    else:
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    code="filesystem.backup_dir_not_creatable",
                    field="backup.data_backup_dir",
                    message=f"Cannot create backup directory {backup_dir}: {e}",
                )
            )

    if config.themes.external_dir:
        ext_dir = Path(config.themes.external_dir)
        if not ext_dir.exists():
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    code="filesystem.theme_dir_missing",
                    field="themes.external_dir",
                    message=f"External theme directory does not exist: {ext_dir}",
                )
            )
        elif not ext_dir.is_dir():
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    code="filesystem.theme_dir_not_dir",
                    field="themes.external_dir",
                    message=f"External theme path is not a directory: {ext_dir}",
                )
            )

    manifest = Path("app/static/dist/.vite/manifest.json")
    if not manifest.exists():
        findings.append(
            Finding(
                severity=Severity.INFO,
                code="filesystem.manifest_missing",
                field="manifest",
                message="Vite manifest not found at app/static/dist/.vite/manifest.json; run 'npm run build' for production",
            )
        )

    return findings


def validate_dependencies(config: DevLogConfig) -> list[Finding]:
    findings: list[Finding] = []

    cache_type = "redis" if config.redis.cache_url or config.redis.url else "memory"
    if cache_type == "redis" and not config.redis.url:
        findings.append(
            Finding(
                severity=Severity.ERROR,
                code="dependencies.redis_url_missing",
                field="redis.url",
                message="Redis cache is configured but REDIS_URL is not set",
            )
        )

    if config.celery.broker_url and not config.celery.broker_url.startswith(
        ("redis://", "amqp://", "sqs://")
    ):
        findings.append(
            Finding(
                severity=Severity.WARNING,
                code="dependencies.celery_broker_unknown",
                field="celery.broker_url",
                message=f"Celery broker URL has unrecognized scheme: {config.celery.broker_url!r}",
            )
        )

    if config.storage.backend == "s3":
        missing = []
        if not config.storage.s3_bucket:
            missing.append("s3_bucket")
        if not config.storage.s3_access_key:
            missing.append("s3_access_key")
        if not config.storage.s3_secret_key:
            missing.append("s3_secret_key")
        if missing:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    code="dependencies.s3_fields_missing",
                    field="storage",
                    message=f"S3 storage backend requires: {', '.join(missing)}",
                )
            )

    if config.email.smtp_host:
        missing = []
        if not config.email.from_address:
            missing.append("from_address")
        if missing:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    code="dependencies.smtp_fields_missing",
                    field="email",
                    message=f"SMTP is configured but required fields are missing: {', '.join(missing)}",
                )
            )

    if config.scheduler.enabled and not config.celery.broker_url:
        findings.append(
            Finding(
                severity=Severity.ERROR,
                code="dependencies.scheduler_no_broker",
                field="scheduler",
                message="Scheduler is enabled but celery broker URL is not configured; "
                "scheduled jobs will not execute without a broker",
                remediation="Set CELERY_BROKER_URL or configure [celery].broker_url in config.toml, "
                "or disable the scheduler with ENABLE_SCHEDULER=false",
            )
        )

    return findings


def validate_compatibility(config: DevLogConfig) -> list[Finding]:
    findings: list[Finding] = []

    db_uri = config.database.uri or ""
    is_sqlite = "sqlite" in db_uri.lower() or db_uri == ""
    if not is_sqlite and "fts" in db_uri.lower():
        findings.append(
            Finding(
                severity=Severity.WARNING,
                code="compatibility.fts_non_sqlite",
                field="database.uri",
                message="FTS5 is SQLite-specific; database URI does not appear to reference SQLite",
            )
        )

    if config.version not in SUPPORTED_VERSIONS:
        findings.append(
            Finding(
                severity=Severity.ERROR,
                code="compatibility.unsupported_version",
                field="version",
                message=f"Config version {config.version} is not supported by this application version",
            )
        )

    if config.themes.default_dark and not _is_plausible_theme_name(config.themes.default_dark):
        findings.append(
            Finding(
                severity=Severity.WARNING,
                code="compatibility.theme_name_invalid",
                field="themes.default_dark",
                message=f"Default dark theme name looks invalid: {config.themes.default_dark!r}",
            )
        )
    if config.themes.default_light and not _is_plausible_theme_name(config.themes.default_light):
        findings.append(
            Finding(
                severity=Severity.WARNING,
                code="compatibility.theme_name_invalid",
                field="themes.default_light",
                message=f"Default light theme name looks invalid: {config.themes.default_light!r}",
            )
        )

    return findings


def _is_plausible_theme_name(name: str) -> bool:
    if not name or not name.strip():
        return False
    if len(name) > 100:
        return False
    if any(c in name for c in "<>{}[]|\\"):
        return False
    return True


_PLACEHOLDER_PATTERNS = (
    "replace-with",
    "your-",
    "change-me",
    "example",
    "placeholder",
    "changeme",
    "password123",
    "admin123",
    "secret123",
)


def _is_placeholder_secret(value: str) -> bool:
    if not value:
        return False
    lower = value.lower().strip()
    for pattern in _PLACEHOLDER_PATTERNS:
        if pattern in lower:
            return True
    if len(value) < 8:
        return True
    return False


def validate_secret_values(config: DevLogConfig) -> list[Finding]:
    findings: list[Finding] = []
    secret_checks = [
        ("secret_key", config.secret_key),
        ("admin_password", config.admin_password),
        ("email.smtp_password", config.email.smtp_password),
        ("health.check_secret", config.health.check_secret),
        ("metrics.secret", config.metrics.secret),
        ("webhook.encryption_key", config.webhook.encryption_key),
        ("backup.encryption_key", config.backup.encryption_key),
    ]
    for field_path, value in secret_checks:
        if value and _is_placeholder_secret(value):
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    code="security.placeholder_secret",
                    field=field_path,
                    message=f"{field_path} appears to be a placeholder or weak value",
                    remediation=f"Set a strong, randomly generated value for {field_path}",
                )
            )
    return findings


def validate_all(
    config: DevLogConfig,
    *,
    production: bool = False,
    config_path: Path | None = None,
    check_filesystem: bool = True,
    raw_toml: dict | None = None,
) -> ValidationResult:
    all_findings: list[Finding] = []

    if config_path is None and hasattr(config, "_config_path"):
        config_path = config._config_path

    if raw_toml is not None:
        all_findings.extend(validate_schema(raw_toml, strict=production))

    all_findings.extend(validate_security(config))
    if check_filesystem:
        all_findings.extend(validate_filesystem(config, config_path=config_path))
    all_findings.extend(validate_dependencies(config))
    all_findings.extend(validate_compatibility(config))
    all_findings.extend(validate_secret_values(config))

    if production:
        elevated: list[Finding] = []
        for f in all_findings:
            if f.code == "security.debug_enabled" and f.severity == Severity.WARNING:
                elevated.append(
                    Finding(
                        severity=Severity.ERROR,
                        code=f.code,
                        field=f.field,
                        message=f.message,
                        remediation=f.remediation,
                    )
                )
            elif f.code == "security.insecure_cookies" and f.severity == Severity.WARNING:
                elevated.append(
                    Finding(
                        severity=Severity.ERROR,
                        code=f.code,
                        field=f.field,
                        message=f.message,
                        remediation=f.remediation,
                    )
                )
            elif f.code == "security.metrics_no_secret" and f.severity == Severity.WARNING:
                elevated.append(
                    Finding(
                        severity=Severity.ERROR,
                        code=f.code,
                        field=f.field,
                        message=f.message,
                        remediation=f.remediation,
                    )
                )
            elif f.severity == Severity.WARNING and f.code in (
                "schema.unknown_section",
                "schema.unknown_field",
                "schema.unknown_top_level_key",
            ):
                elevated.append(
                    Finding(
                        severity=Severity.ERROR,
                        code=f.code,
                        field=f.field,
                        message=f.message,
                        remediation=f.remediation,
                    )
                )
            else:
                elevated.append(f)
        all_findings = elevated

    return ValidationResult(findings=all_findings)
