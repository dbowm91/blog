"""Stable exit codes for the DevLog CLI."""

from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    GENERAL_FAILURE = 1
    INVALID_USAGE = 2
    INVALID_CONFIG = 3
    MISSING_DEPENDENCY = 4
    DATABASE_ERROR = 5
    SERVICE_ERROR = 6
    BACKUP_ERROR = 7
    DEGRADED = 8
