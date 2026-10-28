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


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    if isinstance(value, dict):
        inner = ", ".join(f"{k} = {_toml_value(v)}" for k, v in value.items())
        return "{" + inner + "}"
    if isinstance(value, (int, float)):
        return repr(value)
    return f'"{value}"'


def config_to_toml(config: DevLogConfig) -> str:
    """Serialize the config to a TOML file body.

    Every section of the model is written so the file round-trips through
    ``load_effective_config``. Secret fields are written empty: they are
    supplied by the environment or the env file, never by this file.
    """
    from dataclasses import fields, is_dataclass

    lines = [f"config_version = {config.version}"]

    # Top-level scalars must precede the first section header, otherwise TOML
    # binds them to the section that precedes them.
    for field in fields(config):
        value = getattr(config, field.name)
        if is_dataclass(value) or field.name in SECRET_FIELDS or field.name == "testing":
            continue
        if field.name == "version":
            continue
        lines.append(f"{field.name} = {_toml_value(value)}")

    for field in fields(config):
        section = getattr(config, field.name)
        if not is_dataclass(section):
            continue
        lines.append("")
        lines.append(f"[{field.name}]")
        for section_field in fields(section):
            value = getattr(section, section_field.name)
            if section_field.name in SECRET_FIELDS:
                value = ""
            lines.append(f"{section_field.name} = {_toml_value(value)}")

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
