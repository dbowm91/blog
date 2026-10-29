"""Secret field identification and redaction."""

from __future__ import annotations

from typing import Any

from app.config.model import SECRET_FIELDS, DevLogConfig


def is_secret_field(field_path: str) -> bool:
    """Check if a dotted field path refers to a secret."""
    parts = field_path.split(".")
    return any(p in SECRET_FIELDS for p in parts)


def redact_value(value: str) -> str:
    """Return a redacted representation of a secret value."""
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


def redact_config(config: DevLogConfig) -> dict[str, str]:
    """Return a dict of all secret field paths with redacted values."""
    from dataclasses import fields

    result: dict[str, str] = {}

    def _check(obj: Any, prefix: str = "") -> None:
        for f in fields(obj):
            value = getattr(obj, f.name)
            full_path = f"{prefix}{f.name}" if prefix else f.name
            if f.name in SECRET_FIELDS:
                result[full_path] = redact_value(str(value))
            elif hasattr(value, "__dataclass_fields__"):
                _check(value, f"{full_path}.")

    _check(config)
    return result
