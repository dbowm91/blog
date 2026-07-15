"""Configuration version migration support."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config.model import CONFIG_VERSION


@dataclass(frozen=True)
class MigrationStep:
    from_version: int
    to_version: int
    description: str


MIGRATION_REGISTRY: list[MigrationStep] = []


def detect_version(raw: dict[str, Any]) -> int | None:
    v = raw.get("config_version")
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def needs_migration(raw: dict[str, Any]) -> bool:
    v = detect_version(raw)
    if v is None:
        return True
    return v < CONFIG_VERSION


def get_migration_plan(raw: dict[str, Any]) -> list[MigrationStep]:
    current = detect_version(raw)
    if current is None:
        current = 0
    return [s for s in MIGRATION_REGISTRY if s.from_version >= current]


def dry_run_migration(raw: dict[str, Any]) -> dict[str, Any]:
    current = detect_version(raw)
    steps = get_migration_plan(raw)
    return {
        "current_version": current,
        "target_version": CONFIG_VERSION,
        "steps": [
            {"from": s.from_version, "to": s.to_version, "desc": s.description} for s in steps
        ],
        "needs_migration": needs_migration(raw),
    }


def backup_config(config_path: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = config_path.parent / f"{config_path.name}.backup.{timestamp}"
    shutil.copy2(config_path, backup_path)
    return backup_path


def apply_migration(raw: dict[str, Any], config_path: Path | None = None) -> dict[str, Any]:
    """Apply migration steps to raw config dict. Returns updated dict."""
    result = dict(raw)
    steps = get_migration_plan(raw)
    for step in steps:
        if step.from_version == 0 and step.to_version == 1:
            result["config_version"] = 1
    return result
