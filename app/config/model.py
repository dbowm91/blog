"""Typed configuration model for DevLog."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


CONFIG_VERSION = 1


def _env_str(key: str, default: str = "") -> str:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value


def _env_bool(key: str, default: bool = False) -> bool:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value.lower() in ("true", "1", "yes")


def _env_int(key: str, default: int = 0) -> int:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _env_float(key: str, default: float = 0.0) -> float:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


SECRET_FIELDS = frozenset(
    {
        "secret_key",
        "admin_password",
        "smtp_password",
        "smtp_user",
        "health_check_secret",
        "metrics_secret",
        "webhook_encryption_key",
        "check_secret",
        "secret",
        "encryption_key",
        "s3_access_key",
        "s3_secret_key",
    }
)


def _redacted_repr(value: str) -> str:
    if not value:
        return '""'
    if len(value) <= 4:
        return '"****"'
    return f'"{value[:2]}****{value[-2:]}"'


def _safe_repr(obj: object, redact_fields: frozenset[str]) -> str:
    parts: list[str] = []
    for f in obj.__dataclass_fields__.values():
        value = getattr(obj, f.name)
        if f.name in redact_fields:
            parts.append(f"{f.name}={_redacted_repr(str(value))}")
        elif isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            parts.append(f'{f.name}="{escaped}"')
        elif isinstance(value, bool):
            parts.append(f"{f.name}={'True' if value else 'False'}")
        elif isinstance(value, dict):
            parts.append(f"{f.name}={value!r}")
        else:
            parts.append(f"{f.name}={value!r}")
    cls = type(obj).__name__
    return f"{cls}({', '.join(parts)})"


@dataclass(frozen=True)
class AppConfig:
    title: str = "DevLog"
    description: str = "A place for thoughts on code"
    posts_per_page: int = 10
    max_viewed_posts: int = 100
    session_lifetime_hours: int = 24
    session_ip_binding: str = "warn"
    tag_cache_ttl_seconds: int = 60
    dashboard_per_page: int = 20
    subscribers_per_page: int = 50
    media_per_page: int = 50
    media_max_files: int = 1000
    max_upload_size: int = 10485760
    export_batch_size: int = 500
    fts_result_limit: int = 100
    page_view_buffer_size: int = 0
    token_enumeration_delay: float = 0.1
    login_failure_delay: float = 0.05
    preview_token_expiry_days: int = 7
    analytics_days_min: int = 7
    analytics_days_max: int = 365


@dataclass(frozen=True)
class AdminConfig:
    username: str = "admin"


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False


@dataclass(frozen=True)
class AuthorConfig:
    name: str = ""
    role: str = ""
    avatar: str = ""


@dataclass(frozen=True)
class SiteConfig:
    base_url: str = "http://localhost:5000"
    cdn_url: str = ""
    related_posts_count: int = 3


@dataclass(frozen=True)
class EmailConfig:
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_address: str = "blog@example.com"
    smtp_timeout: int = 30

    def __repr__(self) -> str:
        return _safe_repr(self, frozenset({"smtp_password"}))


@dataclass(frozen=True)
class NewsletterConfig:
    send_time: str = "08:00"
    confirmation_expiry_hours: int = 1
    max_retry_attempts: int = 5


@dataclass(frozen=True)
class CommentsConfig:
    min_length: int = 3
    max_length: int = 5000
    rate_limit_per_ip: str = "5 per minute"
    rate_limit_per_post: str = "3 per minute"
    notify_pending: bool = False
    spam_words: str = ""


@dataclass(frozen=True)
class ThemesConfig:
    external_dir: str = ""
    allow_external: bool = True
    strict_validation: bool = False
    default_dark: str = "Catppuccin Mocha"
    default_light: str = "Catppuccin Latte"
    default_scheme: str = "system"


@dataclass(frozen=True)
class DatabaseConfig:
    uri: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    pool_recycle: int = 3600


@dataclass(frozen=True)
class RedisConfig:
    url: str = "redis://localhost:6379/0"
    cache_url: str = ""
    rate_limit_url: str = ""


@dataclass(frozen=True)
class CeleryConfig:
    broker_url: str = ""


@dataclass(frozen=True)
class SchedulerConfig:
    enabled: bool = False


@dataclass(frozen=True)
class StorageConfig:
    backend: str = "local"
    s3_bucket: str = ""
    s3_region: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_endpoint: str = ""
    s3_public_url: str = ""

    def __repr__(self) -> str:
        return _safe_repr(self, frozenset({"s3_access_key", "s3_secret_key"}))


@dataclass(frozen=True)
class HealthConfig:
    check_secret: str = ""

    def __repr__(self) -> str:
        return _safe_repr(self, frozenset({"check_secret"}))


@dataclass(frozen=True)
class MetricsConfig:
    enabled: bool = False
    secret: str = ""

    def __repr__(self) -> str:
        return _safe_repr(self, frozenset({"secret"}))


@dataclass(frozen=True)
class BackupConfig:
    data_backup_dir: str = "backups"
    encryption_key: str = ""

    def __repr__(self) -> str:
        return _safe_repr(self, frozenset({"encryption_key"}))


@dataclass(frozen=True)
class SecurityConfig:
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 15


@dataclass(frozen=True)
class WebhookConfig:
    timeout: int = 10
    encryption_key: str = ""

    def __repr__(self) -> str:
        return _safe_repr(self, frozenset({"encryption_key"}))


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"


@dataclass(frozen=True)
class SearchConfig:
    provider: str = "sqlite"
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PathsConfig:
    data_dir: str = ""
    log_dir: str = ""
    runtime_dir: str = ""
    database_path: str = ""
    uploads_dir: str = ""
    themes_dir: str = ""
    backups_dir: str = ""
    exports_dir: str = ""


@dataclass(frozen=True)
class DevLogConfig:
    """Top-level typed configuration."""

    version: int = CONFIG_VERSION
    app: AppConfig = field(default_factory=AppConfig)
    admin: AdminConfig = field(default_factory=AdminConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    author: AuthorConfig = field(default_factory=AuthorConfig)
    site: SiteConfig = field(default_factory=SiteConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    newsletter: NewsletterConfig = field(default_factory=NewsletterConfig)
    comments: CommentsConfig = field(default_factory=CommentsConfig)
    themes: ThemesConfig = field(default_factory=ThemesConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    celery: CeleryConfig = field(default_factory=CeleryConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    health: HealthConfig = field(default_factory=HealthConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    webhook: WebhookConfig = field(default_factory=WebhookConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)

    secret_key: str = ""
    admin_password: str = ""
    session_cookie_secure: bool = True
    proxy_count: int = 1
    flask_env: str = ""
    testing: bool = False

    def __repr__(self) -> str:
        return _safe_repr(self, frozenset({"secret_key", "admin_password"}))

    def is_production(self) -> bool:
        return self.flask_env == "production"
