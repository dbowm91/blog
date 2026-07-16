from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.filesystem.layout import RuntimePaths


@dataclass
class LegacyDiscovery:
    database_files: list[Path] = field(default_factory=list)
    upload_dirs: list[Path] = field(default_factory=list)
    backup_dirs: list[Path] = field(default_factory=list)
    theme_dirs: list[Path] = field(default_factory=list)
    log_dirs: list[Path] = field(default_factory=list)
    config_files: list[Path] = field(default_factory=list)
    env_files: list[Path] = field(default_factory=list)
    metadata_files: list[Path] = field(default_factory=list)


def discover_legacy_layout(search_root: Path | None = None) -> LegacyDiscovery:
    root = (search_root or Path.cwd()).resolve()
    discovery = LegacyDiscovery()

    for pattern in ("*.sqlite3", "*.db", "*.sqlite"):
        discovery.database_files.extend(root.glob(pattern))
        for sub in root.iterdir():
            if sub.is_dir() and not sub.name.startswith("."):
                discovery.database_files.extend(sub.glob(pattern))

    for candidate in root.iterdir():
        if not candidate.is_dir():
            continue
        name = candidate.name.lower()
        if name in ("uploads", "media", "files", "images"):
            discovery.upload_dirs.append(candidate)
        elif name in ("backups", "backup"):
            discovery.backup_dirs.append(candidate)
        elif name in ("themes", "theme"):
            discovery.theme_dirs.append(candidate)
        elif name in ("logs", "log"):
            discovery.log_dirs.append(candidate)

    for config_name in ("config.toml", "config.yaml", "config.json", "config.ini"):
        if (root / config_name).exists():
            discovery.config_files.append(root / config_name)

    for env_name in (".env", ".env.local", ".env.production"):
        if (root / env_name).exists():
            discovery.env_files.append(root / env_name)

    for meta_name in (".devlog-installation.json", "devlog-installation.json"):
        if (root / meta_name).exists():
            discovery.metadata_files.append(root / meta_name)

    for sub in root.iterdir():
        if not sub.is_dir() or sub.name.startswith("."):
            continue
        for meta_name in (".devlog-installation.json", "devlog-installation.json"):
            if (sub / meta_name).exists():
                discovery.metadata_files.append(sub / meta_name)

    return discovery


def classify_discovery(
    discovery: LegacyDiscovery,
    target: RuntimePaths,
) -> dict[str, str]:
    classifications: dict[str, str] = {}

    target_db = target.database.path
    for db_file in discovery.database_files:
        if db_file.resolve() == target_db:
            classifications[str(db_file)] = "managed"
        elif db_file.suffix in (".sqlite3", ".db", ".sqlite"):
            classifications[str(db_file)] = "likely_devlog"
        else:
            classifications[str(db_file)] = "unknown"

    target_uploads = target.uploads_dir.path
    for upload_dir in discovery.upload_dirs:
        if upload_dir.resolve() == target_uploads:
            classifications[str(upload_dir)] = "managed"
        elif "devlog" in upload_dir.name.lower():
            classifications[str(upload_dir)] = "likely_devlog"
        else:
            classifications[str(upload_dir)] = "unknown"

    target_backups = target.backups_dir.path
    for backup_dir in discovery.backup_dirs:
        if backup_dir.resolve() == target_backups:
            classifications[str(backup_dir)] = "managed"
        elif "devlog" in backup_dir.name.lower():
            classifications[str(backup_dir)] = "likely_devlog"
        else:
            classifications[str(backup_dir)] = "unknown"

    target_themes = target.themes_dir.path
    for theme_dir in discovery.theme_dirs:
        if theme_dir.resolve() == target_themes:
            classifications[str(theme_dir)] = "managed"
        elif "devlog" in theme_dir.name.lower():
            classifications[str(theme_dir)] = "likely_devlog"
        else:
            classifications[str(theme_dir)] = "unknown"

    for log_dir in discovery.log_dirs:
        if "devlog" in log_dir.name.lower():
            classifications[str(log_dir)] = "likely_devlog"
        else:
            classifications[str(log_dir)] = "unknown"

    target_config = target.config_file.path
    for config_file in discovery.config_files:
        if config_file.resolve() == target_config:
            classifications[str(config_file)] = "managed"
        else:
            classifications[str(config_file)] = "likely_devlog"

    target_env = target.env_file.path
    for env_file in discovery.env_files:
        if env_file.resolve() == target_env:
            classifications[str(env_file)] = "managed"
        else:
            classifications[str(env_file)] = "likely_devlog"

    for meta_file in discovery.metadata_files:
        classifications[str(meta_file)] = "managed"

    return classifications
