"""Configuration serialization with secret redaction."""

from __future__ import annotations

import json
from typing import Any

from app.config.model import SECRET_FIELDS, DevLogConfig
from app.config.secrets import redact_value


def _dataclass_to_dict(obj: Any, *, redact_secrets: bool = True) -> dict[str, Any]:
    from dataclasses import fields

    result: dict[str, Any] = {}
    for f in fields(obj):
        value = getattr(obj, f.name)
        if f.name.startswith("_"):
            continue
        if redact_secrets and f.name in SECRET_FIELDS:
            result[f.name] = redact_value(str(value))
        elif hasattr(value, "__dataclass_fields__"):
            result[f.name] = _dataclass_to_dict(value, redact_secrets=redact_secrets)
        elif isinstance(value, dict):
            result[f.name] = value
        else:
            result[f.name] = value
    return result


def config_to_dict(config: DevLogConfig, *, redact_secrets: bool = True) -> dict[str, Any]:
    return _dataclass_to_dict(config, redact_secrets=redact_secrets)


def config_to_json(
    config: DevLogConfig, *, redact_secrets: bool = True, indent: int | None = 2
) -> str:
    return json.dumps(
        config_to_dict(config, redact_secrets=redact_secrets), indent=indent, default=str
    )


def config_to_toml(config: DevLogConfig) -> str:
    """Serialize config to TOML string (secrets redacted)."""
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
        ("backup", config.backup),
        ("security", config.security),
        ("webhook", config.webhook),
        ("search", config.search),
    ]

    for section_name, section_obj in sections:
        lines.append("")
        lines.append(f"[{section_name}]")
        d = _dataclass_to_dict(section_obj, redact_secrets=True)
        for key, value in d.items():
            if isinstance(value, str):
                lines.append(f'{key} = "{value}"')
            elif isinstance(value, bool):
                lines.append(f"{key} = {'true' if value else 'false'}")
            elif isinstance(value, dict):
                for k, v in value.items():
                    lines.append(f"{k} = {v!r}")
            else:
                lines.append(f"{key} = {value}")

    return "\n".join(lines) + "\n"


def config_summary(config: DevLogConfig) -> dict[str, Any]:
    """Return a human-readable summary of the config (no secrets)."""
    return {
        "version": config.version,
        "title": config.app.title,
        "base_url": config.site.base_url,
        "debug": config.server.debug,
        "database": "sqlite" if not config.database.uri else config.database.uri.split("://")[0],
        "storage": config.storage.backend,
        "scheduler": config.scheduler.enabled,
        "themes_dark": config.themes.default_dark,
        "themes_light": config.themes.default_light,
        "email_configured": bool(config.email.smtp_host),
    }
