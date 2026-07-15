from __future__ import annotations

import logging
import os
import tomllib
from dataclasses import fields
from pathlib import Path
from typing import Any

from app.config.model import (
    AppConfig,
    AdminConfig,
    AuthorConfig,
    BackupConfig,
    CeleryConfig,
    CommentsConfig,
    DatabaseConfig,
    DevLogConfig,
    EmailConfig,
    HealthConfig,
    LoggingConfig,
    MetricsConfig,
    NewsletterConfig,
    RedisConfig,
    SchedulerConfig,
    SearchConfig,
    SecurityConfig,
    ServerConfig,
    SiteConfig,
    StorageConfig,
    ThemesConfig,
    WebhookConfig,
)
from app.config.paths import resolve_config_path, resolve_env_file_path


logger = logging.getLogger(__name__)

_TOML_SECTION_MAP: dict[str, type] = {
    "app": AppConfig,
    "admin": AdminConfig,
    "server": ServerConfig,
    "author": AuthorConfig,
    "site": SiteConfig,
    "email": EmailConfig,
    "newsletter": NewsletterConfig,
    "comments": CommentsConfig,
    "themes": ThemesConfig,
    "database": DatabaseConfig,
    "redis": RedisConfig,
    "celery": CeleryConfig,
    "scheduler": SchedulerConfig,
    "storage": StorageConfig,
    "health": HealthConfig,
    "metrics": MetricsConfig,
    "backup": BackupConfig,
    "security": SecurityConfig,
    "webhook": WebhookConfig,
    "logging": LoggingConfig,
    "search": SearchConfig,
}

_TOML_TO_DATACLASS_FIELD: dict[str, dict[str, str]] = {
    "app": {
        "title": "title",
        "description": "description",
        "posts_per_page": "posts_per_page",
        "max_viewed_posts": "max_viewed_posts",
        "session_lifetime_hours": "session_lifetime_hours",
        "session_ip_binding": "session_ip_binding",
        "tag_cache_ttl_seconds": "tag_cache_ttl_seconds",
        "dashboard_per_page": "dashboard_per_page",
        "subscribers_per_page": "subscribers_per_page",
        "media_per_page": "media_per_page",
        "media_max_files": "media_max_files",
        "max_upload_size": "max_upload_size",
        "export_batch_size": "export_batch_size",
        "fts_result_limit": "fts_result_limit",
        "page_view_buffer_size": "page_view_buffer_size",
        "token_enumeration_delay": "token_enumeration_delay",
        "login_failure_delay": "login_failure_delay",
        "preview_token_expiry_days": "preview_token_expiry_days",
        "analytics_days_min": "analytics_days_min",
        "analytics_days_max": "analytics_days_max",
    },
    "admin": {"username": "username"},
    "server": {"host": "host", "port": "port", "debug": "debug"},
    "author": {"name": "name", "role": "role", "avatar": "avatar"},
    "site": {
        "base_url": "base_url",
        "cdn_url": "cdn_url",
        "related_posts_count": "related_posts_count",
    },
    "email": {
        "smtp_host": "smtp_host",
        "smtp_port": "smtp_port",
        "smtp_user": "smtp_user",
        "smtp_password": "smtp_password",
        "from_address": "from_address",
        "smtp_timeout": "smtp_timeout",
    },
    "newsletter": {
        "send_time": "send_time",
        "confirmation_expiry_hours": "confirmation_expiry_hours",
        "max_retry_attempts": "max_retry_attempts",
    },
    "comments": {
        "min_length": "min_length",
        "max_length": "max_length",
        "rate_limit_per_ip": "rate_limit_per_ip",
        "rate_limit_per_post": "rate_limit_per_post",
        "notify_pending": "notify_pending",
        "spam_words": "spam_words",
    },
    "themes": {
        "external_dir": "external_dir",
        "allow_external": "allow_external",
        "strict_validation": "strict_validation",
        "default_dark": "default_dark",
        "default_light": "default_light",
        "default_scheme": "default_scheme",
    },
    "database": {
        "uri": "uri",
        "pool_size": "pool_size",
        "max_overflow": "max_overflow",
        "pool_recycle": "pool_recycle",
    },
    "redis": {"url": "url", "cache_url": "cache_url", "rate_limit_url": "rate_limit_url"},
    "celery": {"broker_url": "broker_url"},
    "scheduler": {"enabled": "enabled"},
    "storage": {
        "backend": "backend",
        "s3_bucket": "s3_bucket",
        "s3_region": "s3_region",
        "s3_access_key": "s3_access_key",
        "s3_secret_key": "s3_secret_key",
        "s3_endpoint": "s3_endpoint",
        "s3_public_url": "s3_public_url",
    },
    "health": {"check_secret": "check_secret"},
    "metrics": {"enabled": "enabled", "secret": "secret"},
    "backup": {"data_backup_dir": "data_backup_dir", "encryption_key": "encryption_key"},
    "security": {
        "max_failed_attempts": "max_failed_attempts",
        "lockout_duration_minutes": "lockout_duration_minutes",
    },
    "webhook": {"timeout": "timeout", "encryption_key": "encryption_key"},
    "logging": {"level": "level"},
    "search": {"provider": "provider", "config": "config"},
}

_ENV_OVERRIDE_MAP: dict[str, str] = {
    "SECRET_KEY": "secret_key",
    "ADMIN_PASSWORD": "admin_password",
    "ADMIN_USERNAME": "admin_username",
    "SESSION_COOKIE_SECURE": "session_cookie_secure",
    "PROXY_COUNT": "proxy_count",
    "FLASK_ENV": "flask_env",
    "FLASK_DEBUG": "flask_debug",
    "TESTING": "testing",
    "APP_TITLE": "app_title",
    "APP_DESCRIPTION": "app_description",
    "POSTS_PER_PAGE": "app_posts_per_page",
    "MAX_VIEWED_POSTS": "app_max_viewed_posts",
    "SESSION_LIFETIME_HOURS": "app_session_lifetime_hours",
    "SESSION_IP_BINDING": "app_session_ip_binding",
    "TAG_CACHE_TTL_SECONDS": "app_tag_cache_ttl_seconds",
    "DASHBOARD_PER_PAGE": "app_dashboard_per_page",
    "SUBSCRIBERS_PER_PAGE": "app_subscribers_per_page",
    "MEDIA_PER_PAGE": "app_media_per_page",
    "MEDIA_MAX_FILES": "app_media_max_files",
    "MAX_UPLOAD_SIZE": "app_max_upload_size",
    "EXPORT_BATCH_SIZE": "app_export_batch_size",
    "FTS_RESULT_LIMIT": "app_fts_result_limit",
    "PAGE_VIEW_BUFFER_SIZE": "app_page_view_buffer_size",
    "TOKEN_ENUMERATION_DELAY": "app_token_enumeration_delay",
    "LOGIN_FAILURE_DELAY": "app_login_failure_delay",
    "PREVIEW_TOKEN_EXPIRY_DAYS": "app_preview_token_expiry_days",
    "ANALYTICS_DAYS_MIN": "app_analytics_days_min",
    "ANALYTICS_DAYS_MAX": "app_analytics_days_max",
    "BASE_URL": "site_base_url",
    "CDN_URL": "site_cdn_url",
    "RELATED_POSTS_COUNT": "site_related_posts_count",
    "SERVER_HOST": "server_host",
    "SERVER_PORT": "server_port",
    "DEBUG": "server_debug",
    "AUTHOR_NAME": "author_name",
    "AUTHOR_ROLE": "author_role",
    "AUTHOR_AVATAR": "author_avatar",
    "SMTP_HOST": "email_smtp_host",
    "SMTP_PORT": "email_smtp_port",
    "SMTP_USER": "email_smtp_user",
    "SMTP_PASSWORD": "email_smtp_password",
    "FROM_ADDRESS": "email_from_address",
    "SMTP_TIMEOUT": "email_smtp_timeout",
    "NEWSLETTER_SEND_TIME": "newsletter_send_time",
    "CONFIRMATION_EXPIRY_HOURS": "newsletter_confirmation_expiry_hours",
    "NEWSLETTER_MAX_RETRY_ATTEMPTS": "newsletter_max_retry_attempts",
    "ENABLE_SCHEDULER": "scheduler_enabled",
    "HEALTH_CHECK_SECRET": "health_check_secret",
    "METRICS_SECRET": "metrics_secret",
    "ENABLE_METRICS": "metrics_enabled",
    "RATE_LIMIT_STORAGE_URI": "redis_rate_limit_url",
    "REDIS_URL": "redis_url",
    "CACHE_REDIS_URL": "redis_cache_url",
    "CELERY_BROKER_URL": "celery_broker_url",
    "DATA_BACKUP_DIR": "backup_data_backup_dir",
    "WEBHOOK_TIMEOUT": "webhook_timeout",
    "WEBHOOK_ENCRYPTION_KEY": "webhook_encryption_key",
    "BACKUP_ENCRYPTION_KEY": "backup_encryption_key",
    "COMMENT_MIN_LENGTH": "comments_min_length",
    "COMMENT_MAX_LENGTH": "comments_max_length",
    "COMMENT_RATE_LIMIT_PER_IP": "comments_rate_limit_per_ip",
    "COMMENT_RATE_LIMIT_PER_POST": "comments_rate_limit_per_post",
    "COMMENT_NOTIFY_PENDING": "comments_notify_pending",
    "COMMENT_SPAM_WORDS": "comments_spam_words",
    "SEARCH_PROVIDER": "search_provider",
    "SEARCH_CONFIG": "search_config",
    "THEME_EXTERNAL_DIR": "themes_external_dir",
    "THEME_ALLOW_EXTERNAL": "themes_allow_external",
    "THEME_STRICT_VALIDATION": "themes_strict_validation",
    "THEME_DEFAULT_DARK": "themes_default_dark",
    "THEME_DEFAULT_LIGHT": "themes_default_light",
    "THEME_DEFAULT_SCHEME": "themes_default_scheme",
    "MAX_FAILED_ATTEMPTS": "security_max_failed_attempts",
    "LOCKOUT_DURATION_MINUTES": "security_lockout_duration_minutes",
    "SQLALCHEMY_DATABASE_URI": "database_uri",
    "DATABASE_URL": "database_uri",
    "S3_BUCKET": "storage_s3_bucket",
    "S3_REGION": "storage_s3_region",
    "S3_ACCESS_KEY": "storage_s3_access_key",
    "S3_SECRET_KEY": "storage_s3_secret_key",
    "S3_ENDPOINT": "storage_s3_endpoint",
    "S3_PUBLIC_URL": "storage_s3_public_url",
    "STORAGE_BACKEND": "storage_backend",
}

_SECRET_FIELDS = frozenset(
    {
        "secret_key",
        "admin_password",
        "email_smtp_user",
        "email_smtp_password",
        "health_check_secret",
        "metrics_secret",
        "webhook_encryption_key",
        "backup_encryption_key",
        "storage_s3_access_key",
        "storage_s3_secret_key",
    }
)

_DEFAULT_SECRETS: dict[str, str] = {
    "secret_key": "",
    "admin_password": "",
    "email_smtp_user": "",
    "email_smtp_password": "",
    "health_check_secret": "",
    "metrics_secret": "",
    "webhook_encryption_key": "",
    "backup_encryption_key": "",
    "storage_s3_access_key": "",
    "storage_s3_secret_key": "",
}


def _load_toml(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def _load_env_file(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    seen_keys: set[str] = set()
    with open(path) as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                logger.warning("Skipping malformed line %d in %s (no '=')", line_no, path)
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            if not key:
                logger.warning("Skipping empty key on line %d in %s", line_no, path)
                continue

            if key in seen_keys:
                logger.warning("Duplicate key '%s' on line %d in %s", key, line_no, path)
            seen_keys.add(key)

            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
            elif len(value) >= 2 and value[0] == "'" and value[-1] == "'":
                value = value[1:-1]

            result[key] = value
    return result


def _apply_env_overrides(raw: dict, env_file_vars: dict[str, str]) -> dict:
    merged = {k: v for k, v in raw.items()}
    for env_key, field_path in _ENV_OVERRIDE_MAP.items():
        if env_key in env_file_vars:
            merged[field_path] = env_file_vars[env_key]
    return merged


def _apply_cli_overrides(raw: dict, cli_overrides: dict | None) -> dict:
    if not cli_overrides:
        return raw
    merged = {k: v for k, v in raw.items()}
    for field_path, value in cli_overrides.items():
        merged[field_path] = value
    return merged


def _coerce_value(value: str, target_type: type) -> Any:
    if target_type is bool:
        return value.lower() in ("true", "1", "yes")
    if target_type is int:
        try:
            return int(value)
        except (ValueError, TypeError):
            return value
    if target_type is float:
        try:
            return float(value)
        except (ValueError, TypeError):
            return value
    return value


def _resolve_database_uri(raw: dict) -> str:
    for key in ("database_uri", "SQLALCHEMY_DATABASE_URI", "DATABASE_URL"):
        val = raw.get(key)
        if val:
            return str(val)
    sqlite_dir = Path(os.environ.get("DATA_BACKUP_DIR", "data")).parent
    return f"sqlite:///{sqlite_dir}/blog.db"


def _resolve_cache_redis_url(raw: dict) -> str:
    for key in ("redis_cache_url", "CACHE_REDIS_URL", "REDIS_URL"):
        val = raw.get(key)
        if val:
            return str(val)
    return "redis://localhost:6379/0"


def _resolve_celery_broker_url(raw: dict) -> str:
    for key in ("celery_broker_url", "CELERY_BROKER_URL", "REDIS_URL"):
        val = raw.get(key)
        if val:
            return str(val)
    return "redis://localhost:6379/0"


def _resolve_redis_url(raw: dict) -> str:
    val = raw.get("redis_url")
    if val:
        return str(val)
    val = raw.get("REDIS_URL")
    if val:
        return str(val)
    return "redis://localhost:6379/0"


def _build_section(dataclass_type: type, field_map: dict[str, str], raw: dict) -> Any:
    kwargs: dict[str, Any] = {}
    dc_fields = {f.name: f for f in fields(dataclass_type)}
    for toml_key, dc_field_name in field_map.items():
        if dc_field_name not in dc_fields:
            continue
        if toml_key in raw:
            value = raw[toml_key]
            target_type = dc_fields[dc_field_name].type
            if isinstance(target_type, str):
                kwargs[dc_field_name] = value
            else:
                kwargs[dc_field_name] = (
                    _coerce_value(str(value), target_type)
                    if not isinstance(value, target_type)
                    else value
                )
    return dataclass_type(**kwargs)


def _build_config(raw: dict, secrets: dict) -> DevLogConfig:
    db_uri = _resolve_database_uri(raw)
    cache_url = _resolve_cache_redis_url(raw)
    celery_url = _resolve_celery_broker_url(raw)
    redis_url = _resolve_redis_url(raw)

    app_section = _build_section(AppConfig, _TOML_TO_DATACLASS_FIELD["app"], raw)
    admin_section = _build_section(AdminConfig, _TOML_TO_DATACLASS_FIELD["admin"], raw)
    server_section = _build_section(ServerConfig, _TOML_TO_DATACLASS_FIELD["server"], raw)
    author_section = _build_section(AuthorConfig, _TOML_TO_DATACLASS_FIELD["author"], raw)
    site_section = _build_section(SiteConfig, _TOML_TO_DATACLASS_FIELD["site"], raw)
    email_section = _build_section(EmailConfig, _TOML_TO_DATACLASS_FIELD["email"], raw)
    newsletter_section = _build_section(
        NewsletterConfig, _TOML_TO_DATACLASS_FIELD["newsletter"], raw
    )
    comments_section = _build_section(CommentsConfig, _TOML_TO_DATACLASS_FIELD["comments"], raw)
    themes_section = _build_section(ThemesConfig, _TOML_TO_DATACLASS_FIELD["themes"], raw)
    storage_section = _build_section(StorageConfig, _TOML_TO_DATACLASS_FIELD["storage"], raw)
    health_section = _build_section(HealthConfig, _TOML_TO_DATACLASS_FIELD["health"], raw)
    metrics_section = _build_section(MetricsConfig, _TOML_TO_DATACLASS_FIELD["metrics"], raw)
    backup_section = _build_section(BackupConfig, _TOML_TO_DATACLASS_FIELD["backup"], raw)
    security_section = _build_section(SecurityConfig, _TOML_TO_DATACLASS_FIELD["security"], raw)
    webhook_section = _build_section(WebhookConfig, _TOML_TO_DATACLASS_FIELD["webhook"], raw)
    logging_section = _build_section(LoggingConfig, _TOML_TO_DATACLASS_FIELD["logging"], raw)
    search_section = _build_section(SearchConfig, _TOML_TO_DATACLASS_FIELD["search"], raw)

    database_section = DatabaseConfig(
        uri=db_uri,
        pool_size=_coerce_value(str(raw.get("database_pool_size", 10)), int),
        max_overflow=_coerce_value(str(raw.get("database_max_overflow", 20)), int),
        pool_recycle=_coerce_value(str(raw.get("database_pool_recycle", 3600)), int),
    )

    redis_section = RedisConfig(
        url=redis_url,
        cache_url=cache_url,
        rate_limit_url=raw.get("redis_rate_limit_url", ""),
    )

    celery_section = CeleryConfig(broker_url=celery_url)

    scheduler_section = _build_section(SchedulerConfig, _TOML_TO_DATACLASS_FIELD["scheduler"], raw)
    if not scheduler_section.enabled and "scheduler_enabled" in raw:
        scheduler_section = SchedulerConfig(
            enabled=_coerce_value(str(raw["scheduler_enabled"]), bool)
        )

    secret_key = secrets.get("SECRET_KEY", raw.get("secret_key", ""))
    admin_password = secrets.get("ADMIN_PASSWORD", raw.get("admin_password", ""))

    session_cookie_secure = True
    if "session_cookie_secure" in raw:
        session_cookie_secure = _coerce_value(str(raw["session_cookie_secure"]), bool)
    elif "SESSION_COOKIE_SECURE" in raw:
        session_cookie_secure = _coerce_value(str(raw["SESSION_COOKIE_SECURE"]), bool)

    proxy_count = 1
    if "proxy_count" in raw:
        proxy_count = _coerce_value(str(raw["proxy_count"]), int)
    elif "PROXY_COUNT" in raw:
        proxy_count = _coerce_value(str(raw["PROXY_COUNT"]), int)

    flask_env = raw.get("flask_env", raw.get("FLASK_ENV", ""))
    testing = False
    if "testing" in raw:
        testing = _coerce_value(str(raw["testing"]), bool)

    return DevLogConfig(
        version=1,
        app=app_section,
        admin=admin_section,
        server=server_section,
        author=author_section,
        site=site_section,
        email=email_section,
        newsletter=newsletter_section,
        comments=comments_section,
        themes=themes_section,
        database=database_section,
        redis=redis_section,
        celery=celery_section,
        scheduler=scheduler_section,
        storage=storage_section,
        health=health_section,
        metrics=metrics_section,
        backup=backup_section,
        security=security_section,
        webhook=webhook_section,
        logging=logging_section,
        search=search_section,
        secret_key=secret_key,
        admin_password=admin_password,
        session_cookie_secure=session_cookie_secure,
        proxy_count=proxy_count,
        flask_env=flask_env,
        testing=testing,
    )


def load_effective_config(
    config_path: Path | None = None,
    env_file: Path | None = None,
    *,
    skip_env_file: bool = False,
    cli_overrides: dict | None = None,
    system_mode: bool = False,
) -> DevLogConfig:
    config_resolution = resolve_config_path(config_path, system_mode=system_mode)
    env_resolution = resolve_env_file_path(env_file, system_mode=system_mode)

    raw: dict[str, Any] = {}
    if config_resolution.selected and config_resolution.selected.exists:
        toml_data = _load_toml(config_resolution.selected.path)
        for section_name, section_data in toml_data.items():
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    raw[key] = value
                    if section_name == "app":
                        pass
                    else:
                        raw[f"{section_name}_{key}"] = value
            else:
                raw[section_name] = section_data

    env_file_vars: dict[str, str] = {}
    if not skip_env_file and env_resolution.selected and env_resolution.selected.exists:
        env_file_vars = _load_env_file(env_resolution.selected.path)

    os_env_vars: dict[str, str] = {}
    for env_key in _ENV_OVERRIDE_MAP:
        val = os.environ.get(env_key)
        if val is not None:
            os_env_vars[env_key] = val

    merged = _apply_env_overrides(raw, env_file_vars)
    merged = _apply_env_overrides(merged, os_env_vars)
    merged = _apply_cli_overrides(merged, cli_overrides)

    secrets = {k: v for k, v in merged.items() if k in _SECRET_FIELDS}

    return _build_config(merged, secrets)
