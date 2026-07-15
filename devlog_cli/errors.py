"""Domain-specific exception classes for the DevLog CLI."""

from __future__ import annotations

from devlog_cli.exit_codes import ExitCode


class DevlogError(Exception):
    """Base exception for all DevLog CLI errors."""

    exit_code: ExitCode = ExitCode.GENERAL_FAILURE
    code: str = "error.general"

    def __init__(self, message: str, *, remediation: str | None = None) -> None:
        super().__init__(message)
        self.remediation = remediation


class ConfigError(DevlogError):
    exit_code = ExitCode.INVALID_CONFIG
    code = "error.config"


class DatabaseError(DevlogError):
    exit_code = ExitCode.DATABASE_ERROR
    code = "error.database"


class ServiceError(DevlogError):
    exit_code = ExitCode.SERVICE_ERROR
    code = "error.service"


class BackupError(DevlogError):
    exit_code = ExitCode.BACKUP_ERROR
    code = "error.backup"


class MissingDependencyError(DevlogError):
    exit_code = ExitCode.MISSING_DEPENDENCY
    code = "error.missing_dependency"
