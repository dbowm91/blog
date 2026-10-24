from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class InstallState(Enum):
    UNKNOWN = "unknown"
    FRESH = "fresh"
    PARTIAL = "partial"
    COMPLETE = "complete"


@dataclass
class InstallationInfo:
    state: InstallState
    config_exists: bool
    env_exists: bool
    database_exists: bool
    metadata_exists: bool
    admin_exists: bool
    config_path: Path | None = None
    data_path: Path | None = None


def _find_config(config_path: Path | None) -> Path | None:
    if config_path is not None:
        return config_path if config_path.exists() else None

    env_val = os.environ.get("DEVLOG_CONFIG")
    if env_val:
        p = Path(env_val)
        if p.exists():
            return p

    candidates = [
        Path("config.toml"),
        Path.home() / ".config" / "devlog" / "config.toml",
    ]
    for c in candidates:
        if c.exists():
            return c

    return None


def _find_env_file(env_path: Path | None = None) -> Path | None:
    if env_path is not None:
        return env_path if env_path.exists() else None

    env_val = os.environ.get("DEVLOG_ENV_FILE")
    if env_val:
        p = Path(env_val)
        if p.exists():
            return p

    candidates = [
        Path(".env"),
        Path.home() / ".config" / "devlog" / "devlog.env",
    ]
    for c in candidates:
        if c.exists():
            return c

    return None


def _find_database(data_path: Path | None) -> Path | None:
    candidates: list[Path]
    if data_path is not None:
        # An explicit data directory is authoritative. Looking outside it
        # would report the developer's own working copy as the installation
        # being detected.
        candidates = [
            data_path / "blog.db",
            data_path / "devlog.sqlite3",
        ]
    else:
        candidates = [
            Path("data/blog.db"),
            Path("data/devlog.sqlite3"),
            Path("blog.db"),
            Path("devlog.sqlite3"),
        ]

    for c in candidates:
        if c.exists():
            return c

    return None


def detect_installation(
    config_path: Path | None = None,
    data_path: Path | None = None,
    env_path: Path | None = None,
) -> InstallationInfo:
    if config_path is None and data_path is None:
        try:
            from app.filesystem.layout import RuntimePaths, detect_mode

            mode_result = detect_mode()
            runtime_paths = RuntimePaths.for_mode(mode_result.detected_mode)
            config_path = runtime_paths.config_file.path
            data_path = runtime_paths.data_dir.path
        except ImportError:
            pass

    resolved_config = _find_config(config_path)
    env_file = _find_env_file(env_path)
    resolved_data = _find_database(data_path)

    config_exists = resolved_config is not None
    env_exists = env_file is not None
    database_exists = resolved_data is not None
    metadata_exists = False
    admin_exists = False

    metadata_dir = data_path or Path("data")
    if metadata_dir.exists():
        meta_path = metadata_dir / "onboarding-metadata.json"
        if meta_path.exists():
            metadata_exists = True

    if database_exists and resolved_data:
        try:
            import sqlite3

            conn = sqlite3.connect(str(resolved_data))
            cursor = conn.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
            count = cursor.fetchone()[0]
            conn.close()
            admin_exists = count > 0
        except Exception:
            pass

    if config_exists and database_exists and admin_exists:
        state = InstallState.COMPLETE
    elif config_exists or database_exists:
        state = InstallState.PARTIAL
    else:
        state = InstallState.FRESH

    return InstallationInfo(
        state=state,
        config_exists=config_exists,
        env_exists=env_exists,
        database_exists=database_exists,
        metadata_exists=metadata_exists,
        admin_exists=admin_exists,
        config_path=resolved_config,
        data_path=resolved_data,
    )


def load_metadata(data_path: Path | None = None) -> dict | None:
    target = data_path or Path("data")
    meta_file = target / "onboarding-metadata.json"
    if not meta_file.exists():
        return None
    try:
        with open(meta_file) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def save_metadata(data_path: Path | None = None, metadata: dict | None = None) -> None:
    if metadata is None:
        return
    target = data_path or Path("data")
    target.mkdir(parents=True, exist_ok=True)
    meta_file = target / "onboarding-metadata.json"
    tmp = meta_file.with_suffix(".tmp")
    try:
        with open(tmp, "w") as f:
            json.dump(metadata, f, indent=2)
            f.write("\n")
        os.replace(tmp, meta_file)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
