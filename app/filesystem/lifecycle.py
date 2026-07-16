"""Path lifecycle categories for backup and uninstall contracts.

Defines how each path category is handled during backup, uninstall, and purge
operations. This module is a contract for later lifecycle phases — it does not
implement backup or uninstall itself.

Plan: F12 — backup and uninstall integration contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PathCategory(Enum):
    CODE = "code"
    CONFIGURATION = "configuration"
    SECRETS = "secrets"
    PERSISTENT_DATA = "persistent_data"
    USER_CONTENT = "user_content"
    BACKUPS = "backups"
    LOGS = "logs"
    RUNTIME = "runtime"
    INSTALLATION_METADATA = "installation_metadata"


@dataclass(frozen=True)
class LifecyclePolicy:
    included_in_backup: bool
    preserved_on_uninstall: bool
    removed_on_purge: bool
    safe_to_regenerate: bool
    ownership_note: str


CATEGORY_POLICIES: dict[PathCategory, LifecyclePolicy] = {
    PathCategory.CODE: LifecyclePolicy(
        included_in_backup=False,
        preserved_on_uninstall=False,
        removed_on_purge=True,
        safe_to_regenerate=True,
        ownership_note="owned by package manager or deployment tool",
    ),
    PathCategory.CONFIGURATION: LifecyclePolicy(
        included_in_backup=True,
        preserved_on_uninstall=True,
        removed_on_purge=True,
        safe_to_regenerate=False,
        ownership_note="root:devlog 0640 (system), user-owned (user)",
    ),
    PathCategory.SECRETS: LifecyclePolicy(
        included_in_backup=True,
        preserved_on_uninstall=True,
        removed_on_purge=True,
        safe_to_regenerate=False,
        ownership_note="root:devlog 0600 (system), user-owned (user)",
    ),
    PathCategory.PERSISTENT_DATA: LifecyclePolicy(
        included_in_backup=True,
        preserved_on_uninstall=True,
        removed_on_purge=True,
        safe_to_regenerate=False,
        ownership_note="devlog:devlog 0750 (system), user-owned (user)",
    ),
    PathCategory.USER_CONTENT: LifecyclePolicy(
        included_in_backup=True,
        preserved_on_uninstall=True,
        removed_on_purge=True,
        safe_to_regenerate=False,
        ownership_note="devlog:devlog 0750 (system), user-owned (user)",
    ),
    PathCategory.BACKUPS: LifecyclePolicy(
        included_in_backup=False,
        preserved_on_uninstall=True,
        removed_on_purge=True,
        safe_to_regenerate=False,
        ownership_note="devlog:devlog 0750 (system), user-owned (user)",
    ),
    PathCategory.LOGS: LifecyclePolicy(
        included_in_backup=False,
        preserved_on_uninstall=False,
        removed_on_purge=True,
        safe_to_regenerate=True,
        ownership_note="devlog:devlog 0750 (system), user-owned (user)",
    ),
    PathCategory.RUNTIME: LifecyclePolicy(
        included_in_backup=False,
        preserved_on_uninstall=False,
        removed_on_purge=True,
        safe_to_regenerate=True,
        ownership_note="devlog:devlog 0700 (system), user-owned (user)",
    ),
    PathCategory.INSTALLATION_METADATA: LifecyclePolicy(
        included_in_backup=True,
        preserved_on_uninstall=True,
        removed_on_purge=True,
        safe_to_regenerate=False,
        ownership_note="devlog:devlog 0640 (system), user-owned (user)",
    ),
}

# Maps RuntimePaths field names to their lifecycle category
RUNTIME_PATH_CATEGORIES: dict[str, PathCategory] = {
    "config_file": PathCategory.CONFIGURATION,
    "env_file": PathCategory.SECRETS,
    "data_dir": PathCategory.PERSISTENT_DATA,
    "database": PathCategory.PERSISTENT_DATA,
    "uploads_dir": PathCategory.USER_CONTENT,
    "themes_dir": PathCategory.USER_CONTENT,
    "backups_dir": PathCategory.BACKUPS,
    "exports_dir": PathCategory.USER_CONTENT,
    "log_dir": PathCategory.LOGS,
    "runtime_dir": PathCategory.RUNTIME,
    "installation_metadata": PathCategory.INSTALLATION_METADATA,
}
