"""Shared operational result types for service functions.

Domain payloads with stable operation codes, status, counts, warnings,
and remediation — never leaking secrets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OperationResult:
    ok: bool
    code: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    remediation: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "ok": self.ok,
            "code": self.code,
            "summary": self.summary,
            "details": self.details,
            "warnings": list(self.warnings),
        }
        if self.remediation:
            d["remediation"] = list(self.remediation)
        return d


@dataclass(frozen=True)
class AdminCreatedResult(OperationResult):
    username: str = ""


@dataclass(frozen=True)
class AdminPromotedResult(OperationResult):
    username: str = ""


@dataclass(frozen=True)
class AdminPasswordResetResult(OperationResult):
    username: str = ""


@dataclass(frozen=True)
class AdminListResult(OperationResult):
    admins: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class DatabaseCheckResult(OperationResult):
    backend: str = "sqlite"
    healthy: bool = True


@dataclass(frozen=True)
class SearchRebuildResult(OperationResult):
    indexed_count: int = 0


@dataclass(frozen=True)
class MigrationStatusResult(OperationResult):
    current_head: str = ""
    pending_count: int = 0


@dataclass(frozen=True)
class MediaCleanupResult(OperationResult):
    orphaned_deleted: int = 0
    missing_cleared: int = 0


@dataclass(frozen=True)
class ExportResult(OperationResult):
    posts: int = 0
    subscribers: int = 0
    tags: int = 0
    pages: int = 0
    path: str = ""


@dataclass(frozen=True)
class ImportResult(OperationResult):
    posts: int = 0
    subscribers: int = 0
    tags: int = 0
    pages: int = 0


@dataclass(frozen=True)
class ThemeListResult(OperationResult):
    themes: list[dict[str, Any]] = field(default_factory=list)
    total: int = 0


@dataclass(frozen=True)
class ThemeValidationResult(OperationResult):
    valid: bool = True
    theme_name: str = ""


@dataclass(frozen=True)
class ThemeInspectResult(OperationResult):
    theme_name: str = ""
    css_vars: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ThemeRefreshResult(OperationResult):
    old_count: int = 0
    new_count: int = 0
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ThemePathsResult(OperationResult):
    paths: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AccessibilityReportResult(OperationResult):
    total_themes: int = 0
    passed_exact: int = 0
    passed_with_exceptions: int = 0
    failed: int = 0
    reports: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class BackupCreateResult(OperationResult):
    path: str = ""
    verified: bool = False


@dataclass(frozen=True)
class BackupVerifyResult(OperationResult):
    path: str = ""
    valid: bool = True


@dataclass(frozen=True)
class BackupInspectResult(OperationResult):
    path: str = ""
    file_size: int = 0
    is_sqlite: bool = False
    is_compressed: bool = False
    is_encrypted: bool = False


@dataclass(frozen=True)
class OnboardDetectResult(OperationResult):
    state: str = ""
    config_exists: bool = False
    database_exists: bool = False
    admin_exists: bool = False


@dataclass(frozen=True)
class OnboardPlanResult(OperationResult):
    actions: list[dict[str, Any]] = field(default_factory=list)
    action_count: int = 0


@dataclass(frozen=True)
class OnboardApplyResult(OperationResult):
    config_path: str = ""
    data_path: str = ""
    admin_username: str = ""
    migration_head: str = ""
    steps_completed: int = 0
    steps_total: int = 0
    next_command: str = ""
