from __future__ import annotations

import json
import os
import tempfile
import tomllib
from dataclasses import fields
from pathlib import Path
from typing import Any

import click

from devlog_cli.context import CliContext
from devlog_cli.exit_codes import ExitCode
from devlog_cli.output import render
from devlog_cli.result import Result


_ENV_OVERRIDE_MAP: dict[str, str] = {
    "SECRET_KEY": "secret_key",
    "ADMIN_PASSWORD": "admin_password",
    "ADMIN_USERNAME": "admin_username",
    "SESSION_COOKIE_SECURE": "session_cookie_secure",
    "PROXY_COUNT": "proxy_count",
    "FLASK_ENV": "flask_env",
    "FLASK_DEBUG": "server.debug",
    "TESTING": "testing",
    "APP_TITLE": "app.title",
    "APP_DESCRIPTION": "app.description",
    "POSTS_PER_PAGE": "app.posts_per_page",
    "MAX_VIEWED_POSTS": "app.max_viewed_posts",
    "SESSION_LIFETIME_HOURS": "app.session_lifetime_hours",
    "SESSION_IP_BINDING": "app.session_ip_binding",
    "TAG_CACHE_TTL_SECONDS": "app.tag_cache_ttl_seconds",
    "DASHBOARD_PER_PAGE": "app.dashboard_per_page",
    "SUBSCRIBERS_PER_PAGE": "app.subscribers_per_page",
    "MEDIA_PER_PAGE": "app.media_per_page",
    "MEDIA_MAX_FILES": "app.media_max_files",
    "MAX_UPLOAD_SIZE": "app.max_upload_size",
    "EXPORT_BATCH_SIZE": "app.export_batch_size",
    "FTS_RESULT_LIMIT": "app.fts_result_limit",
    "PAGE_VIEW_BUFFER_SIZE": "app.page_view_buffer_size",
    "TOKEN_ENUMERATION_DELAY": "app.token_enumeration_delay",
    "LOGIN_FAILURE_DELAY": "app.login_failure_delay",
    "PREVIEW_TOKEN_EXPIRY_DAYS": "app.preview_token_expiry_days",
    "ANALYTICS_DAYS_MIN": "app.analytics_days_min",
    "ANALYTICS_DAYS_MAX": "app.analytics_days_max",
    "BASE_URL": "site.base_url",
    "CDN_URL": "site.cdn_url",
    "RELATED_POSTS_COUNT": "site.related_posts_count",
    "SERVER_HOST": "server.host",
    "SERVER_PORT": "server.port",
    "DEBUG": "server.debug",
    "AUTHOR_NAME": "author.name",
    "AUTHOR_ROLE": "author.role",
    "AUTHOR_AVATAR": "author.avatar",
    "SMTP_HOST": "email.smtp_host",
    "SMTP_PORT": "email.smtp_port",
    "SMTP_USER": "email.smtp_user",
    "SMTP_PASSWORD": "email.smtp_password",
    "FROM_ADDRESS": "email.from_address",
    "SMTP_TIMEOUT": "email.smtp_timeout",
    "NEWSLETTER_SEND_TIME": "newsletter.send_time",
    "CONFIRMATION_EXPIRY_HOURS": "newsletter.confirmation_expiry_hours",
    "NEWSLETTER_MAX_RETRY_ATTEMPTS": "newsletter.max_retry_attempts",
    "ENABLE_SCHEDULER": "scheduler.enabled",
    "HEALTH_CHECK_SECRET": "health.check_secret",
    "METRICS_SECRET": "metrics.secret",
    "ENABLE_METRICS": "metrics.enabled",
    "RATE_LIMIT_STORAGE_URI": "redis.rate_limit_url",
    "REDIS_URL": "redis.url",
    "CACHE_REDIS_URL": "redis.cache_url",
    "CELERY_BROKER_URL": "celery.broker_url",
    "DATA_BACKUP_DIR": "backup.data_backup_dir",
    "WEBHOOK_TIMEOUT": "webhook.timeout",
    "WEBHOOK_ENCRYPTION_KEY": "webhook.encryption_key",
    "BACKUP_ENCRYPTION_KEY": "backup.encryption_key",
    "COMMENT_MIN_LENGTH": "comments.min_length",
    "COMMENT_MAX_LENGTH": "comments.max_length",
    "COMMENT_RATE_LIMIT_PER_IP": "comments.rate_limit_per_ip",
    "COMMENT_RATE_LIMIT_PER_POST": "comments.rate_limit_per_post",
    "COMMENT_NOTIFY_PENDING": "comments.notify_pending",
    "COMMENT_SPAM_WORDS": "comments.spam_words",
    "SEARCH_PROVIDER": "search.provider",
    "SEARCH_CONFIG": "search.config",
    "THEME_EXTERNAL_DIR": "themes.external_dir",
    "THEME_ALLOW_EXTERNAL": "themes.allow_external",
    "THEME_STRICT_VALIDATION": "themes.strict_validation",
    "THEME_DEFAULT_DARK": "themes.default_dark",
    "THEME_DEFAULT_LIGHT": "themes.default_light",
    "THEME_DEFAULT_SCHEME": "themes.default_scheme",
    "MAX_FAILED_ATTEMPTS": "security.max_failed_attempts",
    "LOCKOUT_DURATION_MINUTES": "security.lockout_duration_minutes",
    "SQLALCHEMY_DATABASE_URI": "database.uri",
    "DATABASE_URL": "database.uri",
    "S3_BUCKET": "storage.s3_bucket",
    "S3_REGION": "storage.s3_region",
    "S3_ACCESS_KEY": "storage.s3_access_key",
    "S3_SECRET_KEY": "storage.s3_secret_key",
    "S3_ENDPOINT": "storage.s3_endpoint",
    "S3_PUBLIC_URL": "storage.s3_public_url",
    "STORAGE_BACKEND": "storage.backend",
}

_ENV_BY_FIELD: dict[str, str] = {v: k for k, v in _ENV_OVERRIDE_MAP.items()}

_SECTION_DEFAULTS: dict[str, Any] = {
    "app": {
        "title": "DevLog",
        "description": "A place for thoughts on code",
        "posts_per_page": 10,
        "max_viewed_posts": 100,
        "session_lifetime_hours": 24,
        "session_ip_binding": "warn",
        "tag_cache_ttl_seconds": 60,
        "dashboard_per_page": 20,
        "subscribers_per_page": 50,
        "media_per_page": 50,
        "media_max_files": 1000,
        "max_upload_size": 10485760,
        "export_batch_size": 500,
        "fts_result_limit": 100,
        "page_view_buffer_size": 0,
        "token_enumeration_delay": 0.1,
        "login_failure_delay": 0.05,
        "preview_token_expiry_days": 7,
        "analytics_days_min": 7,
        "analytics_days_max": 365,
    },
    "admin": {"username": "admin"},
    "server": {"host": "0.0.0.0", "port": 5000, "debug": False},
    "author": {"name": "", "role": "", "avatar": ""},
    "site": {"base_url": "http://localhost:5000", "cdn_url": "", "related_posts_count": 3},
    "email": {
        "smtp_host": "",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_password": "",
        "from_address": "blog@example.com",
        "smtp_timeout": 30,
    },
    "newsletter": {"send_time": "08:00", "confirmation_expiry_hours": 1, "max_retry_attempts": 5},
    "comments": {
        "min_length": 3,
        "max_length": 5000,
        "rate_limit_per_ip": "5 per minute",
        "rate_limit_per_post": "3 per minute",
        "notify_pending": False,
        "spam_words": "",
    },
    "themes": {
        "external_dir": "",
        "allow_external": True,
        "strict_validation": False,
        "default_dark": "Catppuccin Mocha",
        "default_light": "Catppuccin Latte",
        "default_scheme": "system",
    },
    "database": {"uri": "", "pool_size": 10, "max_overflow": 20, "pool_recycle": 3600},
    "redis": {
        "url": "redis://localhost:6379/0",
        "cache_url": "",
        "rate_limit_url": "",
    },
    "celery": {"broker_url": ""},
    "scheduler": {"enabled": False},
    "storage": {
        "backend": "local",
        "s3_bucket": "",
        "s3_region": "",
        "s3_access_key": "",
        "s3_secret_key": "",
        "s3_endpoint": "",
        "s3_public_url": "",
    },
    "health": {"check_secret": ""},
    "metrics": {"enabled": False, "secret": ""},
    "backup": {"data_backup_dir": "backups", "encryption_key": ""},
    "security": {"max_failed_attempts": 5, "lockout_duration_minutes": 15},
    "webhook": {"timeout": 10, "encryption_key": ""},
    "logging": {"level": "INFO"},
    "search": {"provider": "sqlite", "config": {}},
}

_SECRET_FIELDS = frozenset(
    {
        "secret_key",
        "admin_password",
        "email.smtp_user",
        "email.smtp_password",
        "health.check_secret",
        "metrics.secret",
        "webhook.encryption_key",
        "backup.encryption_key",
        "storage.s3_access_key",
        "storage.s3_secret_key",
    }
)

_PRODUCTION_NOTES: dict[str, str] = {
    "server.debug": "Must be false in production",
    "session_cookie_secure": "Must be true for HTTPS deployments",
    "health.check_secret": "Required for detailed health checks in production",
    "metrics.secret": "Required when metrics.enabled=true in production",
    "app.login_failure_delay": "Minimum 0.1s recommended",
    "app.session_ip_binding": "Use 'enforce' in production",
    "email.smtp_host": "Required for newsletter delivery",
    "scheduler.enabled": "Enable on exactly one container to avoid duplicate jobs",
    "themes.strict_validation": "Recommended for production to catch theme errors early",
}


def _get_field_meta(field_path: str) -> dict[str, Any] | None:
    parts = field_path.split(".")
    if len(parts) != 2:
        return None
    section, field_name = parts
    section_defaults = _SECTION_DEFAULTS.get(section)
    if section_defaults is None or field_name not in section_defaults:
        return None
    default = section_defaults[field_name]
    env_var = _ENV_BY_FIELD.get(field_path)
    is_secret = field_path in _SECRET_FIELDS
    type_name = type(default).__name__ if default is not None else "NoneType"
    if isinstance(default, bool):
        type_name = "bool"
    elif isinstance(default, int):
        type_name = "int"
    elif isinstance(default, float):
        type_name = "float"
    return {
        "type": type_name,
        "default": default,
        "env_var": env_var,
        "is_secret": is_secret,
        "production_note": _PRODUCTION_NOTES.get(field_path),
    }


def _serialize_config_to_toml(config: Any) -> str:
    lines = [f"config_version = {config.version}"]

    sections = [
        ("app", config.app),
        ("admin", config.admin),
        ("server", config.server),
        ("author", config.author),
        ("site", config.site),
        ("email", config.email),
        ("newsletter", config.newsletter),
        ("comments", config.comments),
        ("themes", config.themes),
        ("database", config.database),
        ("redis", config.redis),
        ("celery", config.celery),
        ("scheduler", config.scheduler),
        ("storage", config.storage),
        ("health", config.health),
        ("metrics", config.metrics),
        ("backup", config.backup),
        ("security", config.security),
        ("webhook", config.webhook),
        ("logging", config.logging),
        ("search", config.search),
    ]

    for section_name, section_obj in sections:
        lines.append("")
        lines.append(f"[{section_name}]")
        d: dict[str, Any] = {}
        for f in fields(section_obj):
            if f.name.startswith("_"):
                continue
            value = getattr(section_obj, f.name)
            if hasattr(value, "__dataclass_fields__"):
                d[f.name] = {}
            elif isinstance(value, dict):
                d[f.name] = value
            else:
                d[f.name] = value
        for key, value in d.items():
            if isinstance(value, str):
                escaped = value.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{key} = "{escaped}"')
            elif isinstance(value, bool):
                lines.append(f"{key} = {'true' if value else 'false'}")
            elif isinstance(value, dict):
                for k, v in value.items():
                    lines.append(f"{k} = {v!r}")
            else:
                lines.append(f"{key} = {value}")

    return "\n".join(lines) + "\n"


def _write_config_atomic(path: Path, content: str) -> None:
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp", prefix=".config-")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.parent / f"{path.name}.backup.{ts}"
    import shutil

    shutil.copy2(path, backup)
    return backup


def _build_provenance(
    config_path: Path | None,
) -> dict[str, dict[str, Any]]:
    from app.config.paths import resolve_config_path, resolve_env_file_path

    config_resolution = resolve_config_path(config_path)
    env_resolution = resolve_env_file_path()

    raw: dict[str, Any] = {}
    toml_raw: dict[str, Any] = {}
    if config_resolution.selected and config_resolution.selected.exists:
        with open(config_resolution.selected.path, "rb") as f:
            toml_raw = tomllib.load(f)
        for section_name, section_data in toml_raw.items():
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    raw[key] = value
                    if section_name != "app":
                        raw[f"{section_name}_{key}"] = value
            else:
                raw[section_name] = section_data

    env_file_vars: dict[str, str] = {}
    if env_resolution.selected and env_resolution.selected.exists:
        with open(env_resolution.selected.path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                    value = value[1:-1]
                elif len(value) >= 2 and value[0] == "'" and value[-1] == "'":
                    value = value[1:-1]
                env_file_vars[key] = value

    os_env_vars: dict[str, str] = {}
    for env_key in _ENV_OVERRIDE_MAP:
        val = os.environ.get(env_key)
        if val is not None:
            os_env_vars[env_key] = val

    provenance: dict[str, dict[str, Any]] = {}

    for section, section_fields in _SECTION_DEFAULTS.items():
        for field_name, default_val in section_fields.items():
            field_path = f"{section}.{field_name}"
            env_var = _ENV_BY_FIELD.get(field_path)
            is_secret = field_path in _SECRET_FIELDS

            source = "default"
            env_source = None

            if env_var and env_var in os_env_vars:
                source = "env"
                env_source = "process"
            elif env_var and env_var in env_file_vars:
                source = "env"
                env_source = "env_file"
            elif field_name in raw:
                source = "config_file"
            elif f"{section}_{field_name}" in raw:
                source = "config_file"

            provenance[field_path] = {
                "default": default_val,
                "source": source,
                "env_var": env_var,
                "env_source": env_source,
                "is_secret": is_secret,
            }

    return provenance


def _format_value(value: Any, *, redact: bool = False) -> str:
    if redact:
        s = str(value)
        if not s:
            return '""'
        if len(s) <= 4:
            return '"****"'
        return f'"{s[:2]}****{s[-2:]}"'
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value)


@click.group()
def config() -> None:
    """Manage DevLog configuration."""


@config.command("check")
@click.option(
    "--production", is_flag=True, default=False, help="Elevate unsafe warnings to errors."
)
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path),
    help="Path to config file.",
)
@click.option(
    "--env-file",
    "env_file",
    type=click.Path(path_type=Path),
    help="Path to .env file.",
)
@click.option(
    "--no-filesystem",
    is_flag=True,
    default=False,
    help="Skip filesystem checks.",
)
@click.pass_context
def config_check(
    ctx: click.Context,
    production: bool,
    json_mode: bool,
    config_path: Path | None,
    env_file: Path | None,
    no_filesystem: bool,
) -> None:
    cli_ctx: CliContext = ctx.obj
    json_mode = json_mode or cli_ctx.json_mode

    from app.config.loader import load_effective_config
    from app.config.validation import Severity, validate_all

    effective = load_effective_config(config_path=config_path, env_file=env_file)
    result = validate_all(
        effective,
        production=production,
        config_path=config_path,
        check_filesystem=not no_filesystem,
    )

    errors = [f for f in result.findings if f.severity == Severity.ERROR]
    warnings = [f for f in result.findings if f.severity == Severity.WARNING]
    infos = [f for f in result.findings if f.severity == Severity.INFO]

    findings_dicts = [
        {
            "severity": f.severity.value,
            "code": f.code,
            "message": f.message,
            **({"field": f.field} if f.field is not None else {}),
            **({"remediation": f.remediation} if f.remediation is not None else {}),
        }
        for f in result.findings
    ]

    summary_parts = []
    if errors:
        summary_parts.append(f"{len(errors)} error(s)")
    if warnings:
        summary_parts.append(f"{len(warnings)} warning(s)")
    if infos:
        summary_parts.append(f"{len(infos)} info(s)")
    summary = ", ".join(summary_parts) if summary_parts else "Configuration OK"

    warning_msgs = [f.message for f in warnings]
    remediation_msgs = [f.remediation for f in result.findings if f.remediation]

    r: Result
    if not result.ok:
        r = Result.failure(
            code="config.check.failed",
            summary=summary,
            exit_code=ExitCode.INVALID_CONFIG,
            details={"findings": findings_dicts},
            warnings=warning_msgs,
            remediation=remediation_msgs,
        )
    elif warnings or infos:
        r = Result.degraded(
            code="config.check.warnings",
            summary=summary,
            details={"findings": findings_dicts},
            warnings=warning_msgs,
            remediation=remediation_msgs,
        )
    else:
        r = Result.success(
            code="config.check.ok",
            summary=summary,
            details={"findings": findings_dicts},
        )

    render(r, json_mode=json_mode, verbose=cli_ctx.verbose)


@config.command("show")
@click.option("--effective", is_flag=True, default=False, help="Show resolved values and sources.")
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
@click.pass_context
def config_show(ctx: click.Context, effective: bool, json_mode: bool) -> None:
    cli_ctx: CliContext = ctx.obj
    json_mode = json_mode or cli_ctx.json_mode

    from app.config.loader import load_effective_config
    from app.config.serialization import config_to_dict

    config_path = cli_ctx.config_path
    env_file = cli_ctx.env_file
    cfg = load_effective_config(config_path=config_path, env_file=env_file)

    if effective:
        provenance = _build_provenance(config_path)
        config_dict = config_to_dict(cfg, redact_secrets=True)
        output_fields: dict[str, Any] = {}
        for section_name, section_val in config_dict.items():
            if isinstance(section_val, dict):
                output_fields[section_name] = {}
                for fname, fval in section_val.items():
                    fp = f"{section_name}.{fname}"
                    prov = provenance.get(fp, {})
                    output_fields[section_name][fname] = {
                        "value": fval,
                        "source": prov.get("source", "unknown"),
                        "env_var": prov.get("env_var"),
                        "env_source": prov.get("env_source"),
                        "default": prov.get("default"),
                    }
            else:
                output_fields[section_name] = section_val

        r = Result.success(
            code="config.show.effective",
            summary="Effective configuration with provenance",
            details=output_fields,
        )
    else:
        config_dict = config_to_dict(cfg, redact_secrets=True)
        r = Result.success(
            code="config.show",
            summary="Current configuration (secrets redacted)",
            details=config_dict,
        )

    render(r, json_mode=json_mode, verbose=cli_ctx.verbose)


@config.command("explain")
@click.argument("field")
@click.pass_context
def config_explain(ctx: click.Context, field: str) -> None:
    cli_ctx: CliContext = ctx.obj

    from app.config.loader import load_effective_config
    from app.config.serialization import config_to_dict

    parts = field.split(".")
    if len(parts) != 2:
        r = Result.failure(
            code="config.explain.invalid_field",
            summary=f"Invalid field path: {field!r}. Expected format: section.field (e.g., email.smtp_host)",
            exit_code=ExitCode.INVALID_USAGE,
        )
        render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
        return

    meta = _get_field_meta(field)
    if meta is None:
        r = Result.failure(
            code="config.explain.unknown_field",
            summary=f"Unknown config field: {field!r}",
            exit_code=ExitCode.INVALID_USAGE,
        )
        render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
        return

    cfg = load_effective_config(config_path=cli_ctx.config_path, env_file=cli_ctx.env_file)
    config_dict = config_to_dict(cfg, redact_secrets=True)

    section_name, field_name = parts
    section_data = config_dict.get(section_name, {})
    effective_value = section_data.get(field_name) if isinstance(section_data, dict) else None

    details: dict[str, Any] = {
        "field": field,
        "type": meta["type"],
        "default": meta["default"],
        "effective_value": "<redacted>" if meta["is_secret"] else effective_value,
        "source": "env" if os.environ.get(meta["env_var"]) else "config_file",
        "env_var": meta["env_var"],
        "is_secret": meta["is_secret"],
        "restart_required": field in _PRODUCTION_NOTES,
    }
    if meta["production_note"]:
        details["production_note"] = meta["production_note"]

    summary = f"{field}: {_format_value(effective_value, redact=meta['is_secret'])}"
    r = Result.success(
        code="config.explain",
        summary=summary,
        details=details,
    )
    render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)


@config.command("paths")
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
@click.pass_context
def config_paths(ctx: click.Context, json_mode: bool) -> None:
    cli_ctx: CliContext = ctx.obj
    json_mode = json_mode or cli_ctx.json_mode

    from app.config.paths import resolve_config_path, resolve_env_file_path

    config_res = resolve_config_path(cli_ctx.config_path)
    env_res = resolve_env_file_path(cli_ctx.env_file)

    def _format_candidate(c: Any) -> dict[str, Any]:
        return {
            "path": str(c.path),
            "source": c.source,
            "exists": c.exists,
            "is_file": c.is_file,
            "readable": c.readable,
        }

    config_selected = str(config_res.selected.path) if config_res.selected else None
    config_reason = config_res.reason
    config_candidates = [_format_candidate(c) for c in config_res.candidates]

    env_selected = str(env_res.selected.path) if env_res.selected else None
    env_reason = env_res.reason
    env_candidates = [_format_candidate(c) for c in env_res.candidates]

    details: dict[str, Any] = {
        "config_file": {
            "selected": config_selected,
            "reason": config_reason,
            "candidates": config_candidates,
        },
        "env_file": {
            "selected": env_selected,
            "reason": env_reason,
            "candidates": env_candidates,
        },
    }

    summary_parts = []
    if config_selected:
        summary_parts.append(f"Config: {config_selected}")
    else:
        summary_parts.append("Config: none found")
    if env_selected:
        summary_parts.append(f"Env: {env_selected}")
    else:
        summary_parts.append("Env: none found")
    summary = " | ".join(summary_parts)

    r = Result.success(
        code="config.paths",
        summary=summary,
        details=details,
    )
    render(r, json_mode=json_mode, verbose=cli_ctx.verbose)


@config.command("init")
@click.option(
    "--profile",
    type=click.Choice(["development", "native-production", "docker-production", "minimal", "full"]),
    required=True,
    help="Configuration profile to use.",
)
@click.option("--force", is_flag=True, default=False, help="Overwrite existing file (with backup).")
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Output path for config file (default: config.toml).",
)
@click.pass_context
def config_init(ctx: click.Context, profile: str, force: bool, output_path: Path | None) -> None:
    cli_ctx: CliContext = ctx.obj
    from app.config.profiles import get_profile

    prof = get_profile(profile)
    if prof is None:
        r = Result.failure(
            code="config.init.unknown_profile",
            summary=f"Unknown profile: {profile!r}",
            exit_code=ExitCode.INVALID_USAGE,
        )
        render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
        return

    target = output_path or Path("config.toml")

    if target.exists() and not force:
        r = Result.failure(
            code="config.init.exists",
            summary=f"File already exists: {target}",
            exit_code=ExitCode.GENERAL_FAILURE,
            remediation="Use --force to overwrite (existing file will be backed up), or specify --output PATH",
        )
        render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
        return

    backup_path = None
    if target.exists() and force:
        backup_path = _backup_file(target)

    toml_content = _serialize_config_to_toml(prof.config)
    _write_config_atomic(target, toml_content)

    details: dict[str, Any] = {
        "profile": profile,
        "path": str(target),
    }
    if backup_path:
        details["backup"] = str(backup_path)

    summary = f"Created {target} from profile '{profile}'"
    if backup_path:
        summary += f" (backup: {backup_path.name})"
    r = Result.success(
        code="config.init.ok",
        summary=summary,
        details=details,
    )
    render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)


@config.command("migrate")
@click.option(
    "--dry-run", is_flag=True, default=False, help="Show migration plan without applying."
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to config file.",
)
@click.pass_context
def config_migrate(ctx: click.Context, dry_run: bool, config_path: Path | None) -> None:
    cli_ctx: CliContext = ctx.obj
    config_path = config_path or cli_ctx.config_path

    if config_path is None:
        r = Result.failure(
            code="config.migrate.no_config",
            summary="No config file specified. Use --config PATH.",
            exit_code=ExitCode.INVALID_USAGE,
        )
        render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
        return

    if not config_path.exists():
        r = Result.failure(
            code="config.migrate.not_found",
            summary=f"Config file not found: {config_path}",
            exit_code=ExitCode.INVALID_CONFIG,
        )
        render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
        return

    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    from app.config.migration import (
        apply_migration,
        backup_config,
        dry_run_migration,
        needs_migration,
    )

    if not needs_migration(raw):
        r = Result.success(
            code="config.migrate.current",
            summary=f"Config is already at version {raw.get('config_version', '?')}; no migration needed",
        )
        render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
        return

    plan = dry_run_migration(raw)

    if dry_run:
        summary = (
            f"Migration plan: v{plan['current_version'] or '?'} -> v{plan['target_version']} "
            f"({len(plan['steps'])} step(s))"
        )
        r = Result.success(
            code="config.migrate.dry_run",
            summary=summary,
            details=plan,
        )
        render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
        return

    backup_path = backup_config(config_path)
    updated = apply_migration(raw, config_path)

    lines = [f"config_version = {updated['config_version']}"]
    for section_name, section_data in updated.items():
        if section_name == "config_version":
            continue
        if isinstance(section_data, dict):
            lines.append("")
            lines.append(f"[{section_name}]")
            for key, value in section_data.items():
                if isinstance(value, str):
                    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
                    lines.append(f'{key} = "{escaped}"')
                elif isinstance(value, bool):
                    lines.append(f"{key} = {'true' if value else 'false'}")
                elif isinstance(value, dict):
                    for k, v in value.items():
                        lines.append(f"{k} = {v!r}")
                else:
                    lines.append(f"{key} = {value}")

    _write_config_atomic(config_path, "\n".join(lines) + "\n")

    summary = (
        f"Migrated config from v{plan['current_version'] or '?'} to v{plan['target_version']} "
        f"({len(plan['steps'])} step(s))"
    )
    details: dict[str, Any] = {
        "path": str(config_path),
        "backup": str(backup_path),
        **plan,
    }
    r = Result.success(
        code="config.migrate.ok",
        summary=summary,
        details=details,
    )
    render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)


def register_config_commands(config_group: click.Group) -> None:
    for cmd in [
        config_check,
        config_show,
        config_explain,
        config_paths,
        config_init,
        config_migrate,
    ]:
        config_group.add_command(cmd)
