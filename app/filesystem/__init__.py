from __future__ import annotations

from app.filesystem.discovery import (
    LegacyDiscovery,
    classify_discovery,
    discover_legacy_layout,
)
from app.filesystem.layout import (
    InstallationMetadata,
    InstallMode,
    ModeDetectionResult,
    PathProvenance,
    ResolvedPath,
    RuntimePaths,
    detect_mode,
    detect_mode_from_metadata,
    resolve_migrations_directory,
)
from app.filesystem.lifecycle import (
    CATEGORY_POLICIES,
    RUNTIME_PATH_CATEGORIES,
    LifecyclePolicy,
    PathCategory,
)
from app.filesystem.migration import (
    MigrationAction,
    MigrationPlan,
    MigrationStep,
    plan_migration,
)
from app.filesystem.prepare import (
    DirectorySpec,
    get_directory_specs,
    prepare_directories,
)
from app.filesystem.verification import (
    PathCheckResult,
    VerificationResult,
    checkpoint_database,
    check_path,
    verify_database_accessible,
    verify_directory_writable,
    verify_migration,
    verify_production_ready,
)

__all__ = [
    "CATEGORY_POLICIES",
    "DirectorySpec",
    "InstallationMetadata",
    "InstallMode",
    "LegacyDiscovery",
    "LifecyclePolicy",
    "MigrationAction",
    "MigrationPlan",
    "MigrationStep",
    "ModeDetectionResult",
    "RUNTIME_PATH_CATEGORIES",
    "PathCategory",
    "PathCheckResult",
    "PathProvenance",
    "ResolvedPath",
    "RuntimePaths",
    "VerificationResult",
    "check_path",
    "checkpoint_database",
    "classify_discovery",
    "detect_mode",
    "detect_mode_from_metadata",
    "discover_legacy_layout",
    "get_directory_specs",
    "plan_migration",
    "prepare_directories",
    "resolve_migrations_directory",
    "verify_database_accessible",
    "verify_directory_writable",
    "verify_migration",
    "verify_production_ready",
]
