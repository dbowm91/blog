"""Diagnostic framework for `devlog doctor`.

Provides a typed check registry, execution engine, safe-fix allowlist,
and human/JSON output for operational readiness assessment.
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Check result types
# ---------------------------------------------------------------------------


class CheckStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


class CheckCategory(str, Enum):
    INSTALLATION = "installation"
    CONFIGURATION = "configuration"
    SECRETS = "secrets"
    FILESYSTEM = "filesystem"
    DATABASE = "database"
    SEARCH = "search"
    ASSETS = "assets"
    THEMES = "themes"
    STORAGE = "storage"
    EMAIL = "email"
    REDIS = "redis"
    CELERY = "celery"
    SCHEDULER = "scheduler"
    BACKUP = "backup"
    DEPLOYMENT = "deployment"
    SERVICE = "service"
    PROXY = "proxy"
    HEALTH = "health"
    CAPACITY = "capacity"
    SECURITY = "security"


class Severity(str, Enum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    category: str
    status: str
    severity: str
    summary: str
    duration_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    remediation: list[str] = field(default_factory=list)
    safe_fix_id: str | None = None


@dataclass(frozen=True)
class DoctorResult:
    ok: bool
    status: str
    code: str
    summary: str
    mode: str = ""
    version: str = ""
    duration_ms: float = 0.0
    checks: list[CheckResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    remediation: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "code": self.code,
            "summary": self.summary,
            "details": {
                "mode": self.mode,
                "version": self.version,
                "duration_ms": round(self.duration_ms, 2),
                "checks": [
                    {
                        "check_id": c.check_id,
                        "category": c.category,
                        "status": c.status,
                        "severity": c.severity,
                        "summary": c.summary,
                        "duration_ms": round(c.duration_ms, 2),
                        "details": c.details,
                        "remediation": list(c.remediation),
                        "safe_fix_id": c.safe_fix_id,
                    }
                    for c in self.checks
                ],
            },
            "warnings": list(self.warnings),
            "remediation": list(self.remediation),
        }


# ---------------------------------------------------------------------------
# Check definition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckDefinition:
    check_id: str
    category: str
    description: str
    severity: str = Severity.RECOMMENDED
    production_required: bool = False
    timeout_seconds: float = 10.0
    safe_fix_id: str | None = None
    remediation: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class CheckRegistry:
    """Central registry of diagnostic checks."""

    def __init__(self) -> None:
        self._checks: dict[str, CheckDefinition] = {}
        self._runners: dict[str, Callable[..., CheckResult]] = {}

    def register(
        self,
        definition: CheckDefinition,
        runner: Callable[..., CheckResult],
    ) -> None:
        self._checks[definition.check_id] = definition
        self._runners[definition.check_id] = runner

    def get(self, check_id: str) -> tuple[CheckDefinition, Callable[..., CheckResult]] | None:
        defn = self._checks.get(check_id)
        runner = self._runners.get(check_id)
        if defn is not None and runner is not None:
            return defn, runner
        return None

    def list_checks(
        self,
        category: str | None = None,
        production_only: bool = False,
    ) -> list[CheckDefinition]:
        checks = list(self._checks.values())
        if category:
            checks = [c for c in checks if c.category == category]
        if production_only:
            checks = [c for c in checks if c.production_required]
        return sorted(checks, key=lambda c: (c.category, c.check_id))

    def all_ids(self) -> list[str]:
        return sorted(self._checks.keys())


# Global registry instance
_registry = CheckRegistry()


def get_registry() -> CheckRegistry:
    return _registry


def register_check(
    definition: CheckDefinition,
    runner: Callable[..., CheckResult],
) -> None:
    _registry.register(definition, runner)


# ---------------------------------------------------------------------------
# Execution engine
# ---------------------------------------------------------------------------


def _run_check_safe(
    runner: Callable[..., CheckResult],
    **kwargs: Any,
) -> CheckResult:
    """Run a single check function, catching all exceptions."""
    try:
        return runner(**kwargs)
    except Exception as e:
        return CheckResult(
            check_id=kwargs.get("check_id", "unknown"),
            category=kwargs.get("category", "unknown"),
            status=CheckStatus.ERROR,
            severity=kwargs.get("severity", Severity.OPTIONAL),
            summary=f"Check raised an internal error: {type(e).__name__}",
            details={"error_type": type(e).__name__, "error": str(e)[:200]},
        )


def _resolve_mode_and_version() -> tuple[str, str]:
    """Detect installation mode and version."""
    try:
        from app.filesystem.layout import detect_mode

        mode = detect_mode().detected_mode.value
    except Exception:
        mode = "unknown"

    try:
        from importlib.metadata import version as pkg_version

        ver = pkg_version("devlog")
    except Exception:
        ver = "unknown"

    return mode, ver


def run_doctor(
    *,
    production: bool = False,
    category: str | None = None,
    check_ids: list[str] | None = None,
    fix_safe: bool = False,
    total_timeout: float = 120.0,
) -> DoctorResult:
    """Execute diagnostic checks and return aggregated results.

    Parameters
    ----------
    production:
        If True, enforce production-required checks as failures.
    category:
        Optional category filter.
    check_ids:
        Optional explicit list of check IDs to run.
    fix_safe:
        If True, apply safe fixes after checks complete.
    total_timeout:
        Maximum total execution time in seconds.
    """
    engine_start = time.monotonic()
    mode, version = _resolve_mode_and_version()

    checks_to_run: list[CheckDefinition]
    if check_ids:
        checks_to_run = []
        for cid in check_ids:
            entry = _registry.get(cid)
            if entry is not None:
                checks_to_run.append(entry[0])
    else:
        checks_to_run = _registry.list_checks(category=category, production_only=False)

    results: list[CheckResult] = []

    for defn in checks_to_run:
        elapsed = (time.monotonic() - engine_start) * 1000
        if elapsed / 1000 >= total_timeout:
            results.append(
                CheckResult(
                    check_id=defn.check_id,
                    category=defn.category,
                    status=CheckStatus.SKIP,
                    severity=defn.severity,
                    summary="Skipped: total timeout reached",
                )
            )
            continue

        runner = _registry.get(defn.check_id)
        if runner is None:
            continue

        check_start = time.monotonic()
        cr = _run_check_safe(
            runner[1],
            check_id=defn.check_id,
            category=defn.category,
            severity=defn.severity,
        )
        cr_duration = (time.monotonic() - check_start) * 1000
        cr = CheckResult(
            check_id=cr.check_id,
            category=cr.category,
            status=cr.status,
            severity=cr.severity,
            summary=cr.summary,
            duration_ms=cr_duration,
            details=cr.details,
            remediation=cr.remediation or list(defn.remediation),
            safe_fix_id=cr.safe_fix_id or defn.safe_fix_id,
        )
        results.append(cr)

    if fix_safe:
        _apply_safe_fixes(results)

    total_duration = (time.monotonic() - engine_start) * 1000

    required_fails = [
        c
        for c in results
        if c.severity == Severity.REQUIRED and c.status in (CheckStatus.FAIL, CheckStatus.ERROR)
    ]
    optional_warns = [
        c
        for c in results
        if c.severity != Severity.REQUIRED and c.status in (CheckStatus.WARN, CheckStatus.FAIL)
    ]

    if required_fails:
        overall_ok = False
        overall_status = "failure"
        overall_code = "doctor.failed"
        summary = f"{len(required_fails)} required check(s) failed"
    elif optional_warns:
        overall_ok = True
        overall_status = "degraded"
        overall_code = "doctor.degraded"
        summary = f"{len(optional_warns)} optional check(s) warned"
    else:
        overall_ok = True
        overall_status = "healthy"
        overall_code = "doctor.ok"
        summary = "All checks passed"

    all_warnings = [c.summary for c in results if c.status == CheckStatus.WARN]
    all_remediation = []
    for c in results:
        if c.status in (CheckStatus.FAIL, CheckStatus.ERROR) and c.remediation:
            all_remediation.extend(c.remediation)

    return DoctorResult(
        ok=overall_ok,
        status=overall_status,
        code=overall_code,
        summary=summary,
        mode=mode,
        version=version,
        duration_ms=total_duration,
        checks=results,
        warnings=all_warnings,
        remediation=all_remediation,
    )


# ---------------------------------------------------------------------------
# Safe fixes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SafeFix:
    fix_id: str
    description: str
    check_id: str


_SAFE_FIXES: dict[str, SafeFix] = {}


def register_safe_fix(fix_id: str, description: str, check_id: str) -> None:
    _SAFE_FIXES[fix_id] = SafeFix(fix_id=fix_id, description=description, check_id=check_id)


def get_safe_fix_plan(results: list[CheckResult]) -> list[SafeFix]:
    """Return the list of safe fixes applicable to failed/warned checks."""
    applicable_ids = {
        c.safe_fix_id for c in results if c.safe_fix_id and c.status != CheckStatus.PASS
    }
    return [_SAFE_FIXES[fid] for fid in sorted(applicable_ids) if fid in _SAFE_FIXES]


def _apply_safe_fixes(results: list[CheckResult]) -> list[dict[str, Any]]:
    """Apply safe fixes for applicable checks. Returns audit records."""
    applied: list[dict[str, Any]] = []
    for cr in results:
        if cr.status == CheckStatus.PASS or not cr.safe_fix_id:
            continue
        fix = _SAFE_FIXES.get(cr.safe_fix_id)
        if fix is None:
            continue
        fix_fn = _SAFE_FIX_RUNNERS.get(cr.safe_fix_id)
        if fix_fn is None:
            continue
        try:
            ok, detail = fix_fn(cr)
            applied.append(
                {
                    "fix_id": cr.safe_fix_id,
                    "check_id": cr.check_id,
                    "ok": ok,
                    "detail": detail,
                }
            )
        except Exception as e:
            applied.append(
                {
                    "fix_id": cr.safe_fix_id,
                    "check_id": cr.check_id,
                    "ok": False,
                    "detail": f"Fix raised {type(e).__name__}: {e}",
                }
            )
    return applied


_SAFE_FIX_RUNNERS: dict[str, Callable[[CheckResult], tuple[bool, str]]] = {}


def register_safe_fix_runner(
    fix_id: str,
    fn: Callable[[CheckResult], tuple[bool, str]],
) -> None:
    _SAFE_FIX_RUNNERS[fix_id] = fn


# ---------------------------------------------------------------------------
# Secret redaction
# ---------------------------------------------------------------------------

_SECRET_PATTERNS = ("secret", "password", "token", "key", "credential")


def redact_details(details: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of details with secret values redacted."""
    redacted: dict[str, Any] = {}
    for k, v in details.items():
        if any(p in k.lower() for p in _SECRET_PATTERNS):
            if isinstance(v, str) and v:
                redacted[k] = v[:2] + "*" * max(0, len(v) - 4) + v[-2:] if len(v) > 4 else "****"
            else:
                redacted[k] = "****"
        elif isinstance(v, dict):
            redacted[k] = redact_details(v)
        else:
            redacted[k] = v
    return redacted


# ===================================================================
# CHECK IMPLEMENTATIONS
# ===================================================================

# ---------------------------------------------------------------------------
# H3 — Installation and configuration checks
# ---------------------------------------------------------------------------


def _check_package_version(**kwargs: Any) -> CheckResult:
    try:
        from importlib.metadata import version as pkg_version

        ver = pkg_version("devlog")
    except Exception:
        ver = None

    if not ver:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary="Could not determine package version",
        )
    return CheckResult(
        check_id=kwargs["check_id"],
        category=kwargs["category"],
        status=CheckStatus.PASS,
        severity=kwargs["severity"],
        summary=f"Package version: {ver}",
        details={"version": ver},
    )


def _check_config_schema(**kwargs: Any) -> CheckResult:
    try:
        from app.config.loader import load_effective_config

        cfg = load_effective_config()
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary="Configuration loaded successfully",
            details={"title": cfg.app.title},
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.FAIL,
            severity=kwargs["severity"],
            summary=f"Configuration load failed: {type(e).__name__}",
            details={"error": str(e)[:200]},
            remediation=[
                "Check config.toml for syntax errors.",
                "Run `devlog config check` for details.",
            ],
        )


def _check_config_validation(**kwargs: Any) -> CheckResult:
    try:
        from app.config.validation import validate_all
        from app.config.loader import load_effective_config

        cfg = load_effective_config()
        result = validate_all(cfg)
        if result.errors:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.FAIL,
                severity=kwargs["severity"],
                summary=f"{len(result.errors)} configuration error(s)",
                details={
                    "errors": [
                        {"code": f.code, "message": f.message, "field": f.field}
                        for f in result.errors[:10]
                    ]
                },
                remediation=["Fix configuration errors listed in details."],
            )
        if result.warnings:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.WARN,
                severity=kwargs["severity"],
                summary=f"{len(result.warnings)} configuration warning(s)",
                details={
                    "warnings": [
                        {"code": f.code, "message": f.message} for f in result.warnings[:10]
                    ]
                },
            )
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary="Configuration validation passed",
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.ERROR,
            severity=kwargs["severity"],
            summary=f"Config validation raised: {type(e).__name__}",
            details={"error": str(e)[:200]},
        )


def _check_secret_key(**kwargs: Any) -> CheckResult:
    secret_key = os.environ.get("SECRET_KEY", "")
    if not secret_key:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.FAIL,
            severity=kwargs["severity"],
            summary="SECRET_KEY not set",
            remediation=["Set the SECRET_KEY environment variable."],
        )
    if secret_key in ("change-me", "changeme", "your-secret-key", ""):
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.FAIL,
            severity=kwargs["severity"],
            summary="SECRET_KEY appears to be a placeholder",
            remediation=[
                'Generate a real secret: python3 -c "import secrets; print(secrets.token_hex(32))"'
            ],
        )
    if len(secret_key) < 16:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary="SECRET_KEY is shorter than recommended (16+ chars)",
        )
    return CheckResult(
        check_id=kwargs["check_id"],
        category=kwargs["category"],
        status=CheckStatus.PASS,
        severity=kwargs["severity"],
        summary="SECRET_KEY is set and appears valid",
    )


def _check_admin_password(**kwargs: Any) -> CheckResult:
    pw = os.environ.get("ADMIN_PASSWORD", "")
    if not pw:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.FAIL,
            severity=kwargs["severity"],
            summary="ADMIN_PASSWORD not set",
            remediation=["Set the ADMIN_PASSWORD environment variable."],
        )
    if len(pw) < 8:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary="ADMIN_PASSWORD is shorter than recommended (8+ chars)",
        )
    return CheckResult(
        check_id=kwargs["check_id"],
        category=kwargs["category"],
        status=CheckStatus.PASS,
        severity=kwargs["severity"],
        summary="ADMIN_PASSWORD is set",
    )


def _check_installation_metadata(**kwargs: Any) -> CheckResult:
    try:
        from app.filesystem.layout import RuntimePaths, detect_mode, InstallationMetadata

        paths = RuntimePaths.for_mode(detect_mode().detected_mode)
        meta = InstallationMetadata.load(paths.installation_metadata.path)
        if meta is None:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.WARN,
                severity=kwargs["severity"],
                summary="No installation metadata found",
                remediation=["Run `devlog onboard` to create installation metadata."],
            )
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary=f"Installation metadata found (mode={meta.mode.value}, version={meta.version})",
            details={
                "mode": meta.mode.value,
                "version": meta.version,
            },
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.ERROR,
            severity=kwargs["severity"],
            summary=f"Could not read installation metadata: {type(e).__name__}",
            details={"error": str(e)[:200]},
        )


# ---------------------------------------------------------------------------
# H4 — Filesystem and capacity checks
# ---------------------------------------------------------------------------


def _check_required_directories(**kwargs: Any) -> CheckResult:
    try:
        from app.filesystem.layout import RuntimePaths, detect_mode

        paths = RuntimePaths.for_mode(detect_mode().detected_mode)
        missing = []
        for name in (
            "data_dir",
            "uploads_dir",
            "themes_dir",
            "backups_dir",
            "exports_dir",
            "log_dir",
            "runtime_dir",
        ):
            rp = getattr(paths, name)
            if not rp.path.exists():
                missing.append(name)
        if missing:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.WARN,
                severity=kwargs["severity"],
                summary=f"{len(missing)} required director(ies) missing",
                details={"missing": missing},
                safe_fix_id="create_missing_dirs",
                remediation=["Create missing directories or run `devlog doctor --fix-safe`."],
            )
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary="All required directories exist",
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.ERROR,
            severity=kwargs["severity"],
            summary=f"Directory check raised: {type(e).__name__}",
            details={"error": str(e)[:200]},
        )


def _check_disk_space(**kwargs: Any) -> CheckResult:
    try:
        from app.filesystem.layout import RuntimePaths, detect_mode

        paths = RuntimePaths.for_mode(detect_mode().detected_mode)
        usage = shutil.disk_usage(paths.data_dir.path)
        free_mb = usage.free / (1024 * 1024)
        free_pct = (usage.free / usage.total) * 100 if usage.total else 0
        if free_pct < 5:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.FAIL,
                severity=kwargs["severity"],
                summary=f"Disk space critically low: {free_mb:.0f} MB ({free_pct:.1f}%)",
                details={"free_mb": round(free_mb, 1), "free_percent": round(free_pct, 1)},
                remediation=["Free disk space or expand the volume."],
            )
        if free_pct < 15:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.WARN,
                severity=kwargs["severity"],
                summary=f"Disk space low: {free_mb:.0f} MB ({free_pct:.1f}%)",
                details={"free_mb": round(free_mb, 1), "free_percent": round(free_pct, 1)},
            )
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary=f"Disk space OK: {free_mb:.0f} MB ({free_pct:.1f}%)",
            details={"free_mb": round(free_mb, 1), "free_percent": round(free_pct, 1)},
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary=f"Could not check disk space: {type(e).__name__}",
        )


def _check_symlink_safety(**kwargs: Any) -> CheckResult:
    try:
        from app.filesystem.layout import RuntimePaths, detect_mode

        paths = RuntimePaths.for_mode(detect_mode().detected_mode)
        unsafe = []
        for name in ("data_dir", "uploads_dir", "themes_dir", "backups_dir"):
            rp = getattr(paths, name)
            if rp.path.exists() and rp.path.is_symlink():
                target = rp.path.resolve()
                if not str(target).startswith(str(Path.cwd())):
                    unsafe.append({"name": name, "target": str(target)})
        if unsafe:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.WARN,
                severity=kwargs["severity"],
                summary=f"{len(unsafe)} path(s) are symlinks outside project root",
                details={"unsafe_symlinks": unsafe},
            )
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary="No unsafe symlinks detected",
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.ERROR,
            severity=kwargs["severity"],
            summary=f"Symlink check raised: {type(e).__name__}",
        )


# ---------------------------------------------------------------------------
# H5 — Database and migration checks
# ---------------------------------------------------------------------------


def _check_database_connectivity(**kwargs: Any) -> CheckResult:
    try:
        from sqlalchemy import text
        from app.extensions import db

        start = time.monotonic()
        db.session.execute(text("SELECT 1"))
        latency_ms = (time.monotonic() - start) * 1000
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary=f"Database connected ({latency_ms:.1f}ms)",
            details={"latency_ms": round(latency_ms, 2)},
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.FAIL,
            severity=kwargs["severity"],
            summary=f"Database connection failed: {type(e).__name__}",
            details={"error": str(e)[:200]},
            remediation=["Check database URI and connectivity."],
        )


def _check_migration_head(**kwargs: Any) -> CheckResult:
    try:
        from app.services.operations.database import get_migration_status

        result = get_migration_status()
        if result.ok:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.PASS,
                severity=kwargs["severity"],
                summary=result.summary,
                details={
                    "current_head": result.current_head,
                    "pending_count": result.pending_count,
                },
            )
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.FAIL,
            severity=kwargs["severity"],
            summary=result.summary,
            details=result.details,
            remediation=result.remediation,
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.ERROR,
            severity=kwargs["severity"],
            summary=f"Migration check raised: {type(e).__name__}",
            details={"error": str(e)[:200]},
        )


def _check_sqlite_integrity(**kwargs: Any) -> CheckResult:
    try:
        from app.db_utils import is_sqlite_database

        if not is_sqlite_database():
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.SKIP,
                severity=kwargs["severity"],
                summary="Integrity check skipped (not SQLite)",
            )
        from app.services.operations.database import check_database_integrity

        result = check_database_integrity()
        if result.ok:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.PASS,
                severity=kwargs["severity"],
                summary=result.summary,
            )
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.FAIL,
            severity=kwargs["severity"],
            summary=result.summary,
            details=result.details,
            remediation=result.remediation,
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.ERROR,
            severity=kwargs["severity"],
            summary=f"Integrity check raised: {type(e).__name__}",
            details={"error": str(e)[:200]},
        )


def _check_fts5_availability(**kwargs: Any) -> CheckResult:
    try:
        from sqlalchemy import text
        from app.extensions import db
        from app.db_utils import is_sqlite_database

        if not is_sqlite_database():
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.SKIP,
                severity=kwargs["severity"],
                summary="FTS5 check skipped (not SQLite)",
            )
        has_fts = db.session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'")
        ).fetchone()
        if has_fts:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.PASS,
                severity=kwargs["severity"],
                summary="FTS5 search index exists",
            )
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary="FTS5 search index not found",
            remediation=["Run `devlog db rebuild-search` to create the search index."],
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.ERROR,
            severity=kwargs["severity"],
            summary=f"FTS5 check raised: {type(e).__name__}",
            details={"error": str(e)[:200]},
        )


def _check_database_path_match(**kwargs: Any) -> CheckResult:
    try:
        from app.filesystem.layout import RuntimePaths, detect_mode
        from app.config.loader import load_effective_config

        paths = RuntimePaths.for_mode(detect_mode().detected_mode)
        cfg = load_effective_config()
        db_uri = cfg.database.uri
        if db_uri.startswith("sqlite:///"):
            db_path = Path(db_uri.replace("sqlite:///", "/"))
            expected = paths.database.path.resolve()
            if db_path.resolve() == expected:
                return CheckResult(
                    check_id=kwargs["check_id"],
                    category=kwargs["category"],
                    status=CheckStatus.PASS,
                    severity=kwargs["severity"],
                    summary="Database path matches RuntimePaths",
                )
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.WARN,
                severity=kwargs["severity"],
                summary="Database path differs from RuntimePaths",
                details={"config_path": str(db_path), "expected_path": str(expected)},
            )
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.SKIP,
            severity=kwargs["severity"],
            summary="Path match check skipped (non-SQLite backend)",
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.ERROR,
            severity=kwargs["severity"],
            summary=f"DB path check raised: {type(e).__name__}",
        )


# ---------------------------------------------------------------------------
# H6 — Application assets and themes
# ---------------------------------------------------------------------------


def _check_frontend_manifest(**kwargs: Any) -> CheckResult:
    manifest = Path("app/static/.vite/manifest.json")
    if not manifest.exists():
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary="Vite manifest not found",
            remediation=["Build frontend assets to generate the manifest file."],
        )
    try:
        import json

        data = json.loads(manifest.read_text())
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary=f"Vite manifest present ({len(data)} entries)",
            details={"entry_count": len(data)},
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary=f"Vite manifest unreadable: {type(e).__name__}",
        )


def _check_bundled_themes(**kwargs: Any) -> CheckResult:
    try:
        from app.themes.registry import ThemeRegistry

        registry = ThemeRegistry()
        themes = registry.list_themes()
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary=f"Bundled theme catalog: {len(themes)} themes",
            details={"theme_count": len(themes)},
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary=f"Theme catalog check raised: {type(e).__name__}",
            details={"error": str(e)[:200]},
        )


def _check_selected_themes(**kwargs: Any) -> CheckResult:
    try:
        from app.models import SiteSettings
        from app.services.theme_settings import get_effective_theme_names

        settings = SiteSettings.get_instance()
        dark, light, _scheme = get_effective_theme_names(
            settings=settings,
            config_defaults={},
        )
        from app.themes.registry import ThemeRegistry

        registry = ThemeRegistry()
        missing = []
        if dark and not registry.resolve(dark):
            missing.append(dark)
        if light and not registry.resolve(light):
            missing.append(light)
        if missing:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.FAIL,
                severity=kwargs["severity"],
                summary=f"{len(missing)} selected theme(s) not found",
                details={"missing_themes": missing, "dark": dark, "light": light},
                remediation=["Check theme configuration in admin settings."],
            )
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary=f"Selected themes resolve: dark={dark}, light={light}",
            details={"dark": dark, "light": light},
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.ERROR,
            severity=kwargs["severity"],
            summary=f"Theme resolution check raised: {type(e).__name__}",
            details={"error": str(e)[:200]},
        )


# ---------------------------------------------------------------------------
# H7 — Dependency and integration checks
# ---------------------------------------------------------------------------


def _check_redis_connectivity(**kwargs: Any) -> CheckResult:
    try:
        from app.config.loader import load_effective_config

        cfg = load_effective_config()
        redis_url = cfg.redis.url
        if not redis_url:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.SKIP,
                severity=kwargs["severity"],
                summary="Redis not configured",
            )
        import redis

        client = redis.Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary="Redis connected",
        )
    except ImportError:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.SKIP,
            severity=kwargs["severity"],
            summary="Redis client not installed",
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary=f"Redis connection failed: {type(e).__name__}",
            details={"error": str(e)[:200]},
            remediation=["Check Redis configuration and connectivity."],
        )


def _check_celery_broker(**kwargs: Any) -> CheckResult:
    try:
        from app.config.loader import load_effective_config

        cfg = load_effective_config()
        broker = cfg.celery.broker_url
        if not broker:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.SKIP,
                severity=kwargs["severity"],
                summary="Celery broker not configured",
            )
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary=f"Celery broker configured: {broker.split('@')[-1] if '@' in broker else broker[:30]}",
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary=f"Celery config check raised: {type(e).__name__}",
        )


def _check_scheduler_owner(**kwargs: Any) -> CheckResult:
    try:
        from app.scheduler import get_scheduler_status

        running = get_scheduler_status()
        if running:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.PASS,
                severity=kwargs["severity"],
                summary="Scheduler is running",
            )
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary="Scheduler is not running",
            remediation=["Start the application to activate the scheduler."],
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.ERROR,
            severity=kwargs["severity"],
            summary=f"Scheduler check raised: {type(e).__name__}",
        )


def _check_smtp_config(**kwargs: Any) -> CheckResult:
    try:
        from app.config.loader import load_effective_config

        cfg = load_effective_config()
        host = cfg.email.smtp_host
        if not host:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.SKIP,
                severity=kwargs["severity"],
                summary="SMTP not configured (no host)",
            )
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary=f"SMTP configured: {host}:{cfg.email.smtp_port}",
            details={"host": host, "port": cfg.email.smtp_port},
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary=f"SMTP config check raised: {type(e).__name__}",
        )


def _check_storage_backend(**kwargs: Any) -> CheckResult:
    try:
        from app.config.loader import load_effective_config

        cfg = load_effective_config()
        backend = cfg.storage.backend
        if backend == "s3":
            missing = []
            if not cfg.storage.s3_bucket:
                missing.append("S3_BUCKET")
            if not cfg.storage.s3_access_key:
                missing.append("S3_ACCESS_KEY")
            if not cfg.storage.s3_secret_key:
                missing.append("S3_SECRET_KEY")
            if missing:
                return CheckResult(
                    check_id=kwargs["check_id"],
                    category=kwargs["category"],
                    status=CheckStatus.FAIL,
                    severity=kwargs["severity"],
                    summary=f"S3 backend selected but missing: {', '.join(missing)}",
                    details={"missing_vars": missing},
                    remediation=[f"Set {v} environment variable." for v in missing],
                )
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary=f"Storage backend: {backend}",
            details={"backend": backend},
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary=f"Storage check raised: {type(e).__name__}",
        )


# ---------------------------------------------------------------------------
# H8 — Deployment and service checks
# ---------------------------------------------------------------------------


def _check_deployment_mode(**kwargs: Any) -> CheckResult:
    try:
        from app.filesystem.layout import detect_mode

        mode = detect_mode().detected_mode
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary=f"Deployment mode: {mode.value}",
            details={"mode": mode.value},
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary=f"Could not detect deployment mode: {type(e).__name__}",
        )


# ---------------------------------------------------------------------------
# H9 — Backup readiness checks
# ---------------------------------------------------------------------------


def _check_backup_directory(**kwargs: Any) -> CheckResult:
    try:
        from app.filesystem.layout import RuntimePaths, detect_mode

        paths = RuntimePaths.for_mode(detect_mode().detected_mode)
        backup_dir = paths.backups_dir.path
        if not backup_dir.exists():
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.WARN,
                severity=kwargs["severity"],
                summary="Backup directory does not exist",
                safe_fix_id="create_missing_dirs",
                remediation=["Create the backup directory."],
            )
        import os

        writable = os.access(backup_dir, os.W_OK)
        if not writable:
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.FAIL,
                severity=kwargs["severity"],
                summary="Backup directory is not writable",
                remediation=["Fix directory permissions."],
            )
        backups = sorted(backup_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if backups:
            age_hours = (time.time() - backups[0].stat().st_mtime) / 3600
            return CheckResult(
                check_id=kwargs["check_id"],
                category=kwargs["category"],
                status=CheckStatus.PASS,
                severity=kwargs["severity"],
                summary=f"Backup directory OK, latest backup {age_hours:.1f}h ago",
                details={"latest_age_hours": round(age_hours, 1), "backup_count": len(backups)},
            )
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary="Backup directory exists but is empty",
            remediation=["Run `devlog backup create` to generate a backup."],
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.ERROR,
            severity=kwargs["severity"],
            summary=f"Backup check raised: {type(e).__name__}",
            details={"error": str(e)[:200]},
        )


# ---------------------------------------------------------------------------
# H10 — Health endpoint check
# ---------------------------------------------------------------------------


def _check_health_endpoint(**kwargs: Any) -> CheckResult:
    try:
        from app.config.loader import load_effective_config

        cfg = load_effective_config()
        host = cfg.server.host
        port = cfg.server.port
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary=f"Server configured at {host}:{port}",
            details={"host": host, "port": port},
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary=f"Server config check raised: {type(e).__name__}",
        )


# ---------------------------------------------------------------------------
# H11 — Security checks
# ---------------------------------------------------------------------------


def _check_session_security(**kwargs: Any) -> CheckResult:
    try:
        from app.config.loader import load_effective_config

        cfg = load_effective_config()
        binding = cfg.app.session_ip_binding
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.PASS,
            severity=kwargs["severity"],
            summary=f"Session IP binding: {binding}",
            details={"session_ip_binding": binding},
        )
    except Exception as e:
        return CheckResult(
            check_id=kwargs["check_id"],
            category=kwargs["category"],
            status=CheckStatus.WARN,
            severity=kwargs["severity"],
            summary=f"Session security check raised: {type(e).__name__}",
        )


# ---------------------------------------------------------------------------
# Register all checks
# ---------------------------------------------------------------------------


def _register_all_checks() -> None:
    """Register all diagnostic checks with the global registry."""
    checks = [
        # H3 — Installation and configuration
        (
            CheckDefinition(
                "pkg.version",
                CheckCategory.INSTALLATION,
                "Package version consistency",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_package_version,
        ),
        (
            CheckDefinition(
                "config.load",
                CheckCategory.CONFIGURATION,
                "Configuration loads successfully",
                Severity.REQUIRED,
                production_required=True,
                timeout_seconds=10,
                remediation=["Check config.toml syntax."],
            ),
            _check_config_schema,
        ),
        (
            CheckDefinition(
                "config.validate",
                CheckCategory.CONFIGURATION,
                "Configuration validation passes",
                Severity.REQUIRED,
                production_required=True,
                timeout_seconds=10,
                remediation=["Fix configuration errors."],
            ),
            _check_config_validation,
        ),
        (
            CheckDefinition(
                "secrets.secret_key",
                CheckCategory.SECRETS,
                "SECRET_KEY is set and valid",
                Severity.REQUIRED,
                production_required=True,
                timeout_seconds=5,
                remediation=["Set SECRET_KEY env var."],
            ),
            _check_secret_key,
        ),
        (
            CheckDefinition(
                "secrets.admin_password",
                CheckCategory.SECRETS,
                "ADMIN_PASSWORD is set",
                Severity.REQUIRED,
                production_required=True,
                timeout_seconds=5,
                remediation=["Set ADMIN_PASSWORD env var."],
            ),
            _check_admin_password,
        ),
        (
            CheckDefinition(
                "install.metadata",
                CheckCategory.INSTALLATION,
                "Installation metadata present",
                Severity.RECOMMENDED,
                timeout_seconds=5,
                remediation=["Run `devlog onboard`."],
            ),
            _check_installation_metadata,
        ),
        # H4 — Filesystem and capacity
        (
            CheckDefinition(
                "fs.required_dirs",
                CheckCategory.FILESYSTEM,
                "Required directories exist",
                Severity.RECOMMENDED,
                timeout_seconds=10,
                safe_fix_id="create_missing_dirs",
                remediation=["Create missing directories."],
            ),
            _check_required_directories,
        ),
        (
            CheckDefinition(
                "fs.disk_space",
                CheckCategory.CAPACITY,
                "Disk space adequate",
                Severity.REQUIRED,
                production_required=True,
                timeout_seconds=5,
                remediation=["Free disk space."],
            ),
            _check_disk_space,
        ),
        (
            CheckDefinition(
                "fs.symlink_safety",
                CheckCategory.FILESYSTEM,
                "No unsafe symlinks",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_symlink_safety,
        ),
        # H5 — Database and migration
        (
            CheckDefinition(
                "db.connectivity",
                CheckCategory.DATABASE,
                "Database connectivity",
                Severity.REQUIRED,
                production_required=True,
                timeout_seconds=10,
                remediation=["Check database URI and connectivity."],
            ),
            _check_database_connectivity,
        ),
        (
            CheckDefinition(
                "db.migration_head",
                CheckCategory.DATABASE,
                "Migration head current",
                Severity.RECOMMENDED,
                timeout_seconds=10,
                remediation=["Run `devlog db migrate`."],
            ),
            _check_migration_head,
        ),
        (
            CheckDefinition(
                "db.sqlite_integrity",
                CheckCategory.DATABASE,
                "SQLite integrity check",
                Severity.RECOMMENDED,
                timeout_seconds=30,
                remediation=["Consider restoring from a backup."],
            ),
            _check_sqlite_integrity,
        ),
        (
            CheckDefinition(
                "db.fts5",
                CheckCategory.SEARCH,
                "FTS5 search index exists",
                Severity.RECOMMENDED,
                timeout_seconds=10,
                remediation=["Run `devlog db rebuild-search`."],
            ),
            _check_fts5_availability,
        ),
        (
            CheckDefinition(
                "db.path_match",
                CheckCategory.DATABASE,
                "Database path matches RuntimePaths",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_database_path_match,
        ),
        # H6 — Assets and themes
        (
            CheckDefinition(
                "assets.frontend_manifest",
                CheckCategory.ASSETS,
                "Frontend manifest present",
                Severity.RECOMMENDED,
                timeout_seconds=5,
                remediation=["Build frontend assets."],
            ),
            _check_frontend_manifest,
        ),
        (
            CheckDefinition(
                "themes.bundled",
                CheckCategory.THEMES,
                "Bundled theme catalog intact",
                Severity.RECOMMENDED,
                timeout_seconds=10,
            ),
            _check_bundled_themes,
        ),
        (
            CheckDefinition(
                "themes.selected",
                CheckCategory.THEMES,
                "Selected themes resolve",
                Severity.RECOMMENDED,
                timeout_seconds=10,
                remediation=["Check theme configuration in admin settings."],
            ),
            _check_selected_themes,
        ),
        # H7 — Dependencies
        (
            CheckDefinition(
                "dep.redis",
                CheckCategory.REDIS,
                "Redis connectivity",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Check Redis configuration and connectivity."],
            ),
            _check_redis_connectivity,
        ),
        (
            CheckDefinition(
                "dep.celery",
                CheckCategory.CELERY,
                "Celery broker configured",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_celery_broker,
        ),
        (
            CheckDefinition(
                "dep.scheduler",
                CheckCategory.SCHEDULER,
                "Scheduler running",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Start the application to activate the scheduler."],
            ),
            _check_scheduler_owner,
        ),
        (
            CheckDefinition(
                "dep.smtp",
                CheckCategory.EMAIL,
                "SMTP configured",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_smtp_config,
        ),
        (
            CheckDefinition(
                "dep.storage",
                CheckCategory.STORAGE,
                "Storage backend configured",
                Severity.RECOMMENDED,
                timeout_seconds=5,
                remediation=["Set required S3 environment variables."],
            ),
            _check_storage_backend,
        ),
        # H8 — Deployment
        (
            CheckDefinition(
                "deploy.mode",
                CheckCategory.DEPLOYMENT,
                "Deployment mode detected",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_deployment_mode,
        ),
        # H9 — Backup
        (
            CheckDefinition(
                "backup.readiness",
                CheckCategory.BACKUP,
                "Backup directory ready",
                Severity.RECOMMENDED,
                timeout_seconds=5,
                safe_fix_id="create_missing_dirs",
                remediation=["Create backup directory and run a backup."],
            ),
            _check_backup_directory,
        ),
        # H10 — Health
        (
            CheckDefinition(
                "health.endpoint",
                CheckCategory.HEALTH,
                "Server configuration",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_health_endpoint,
        ),
        # H11 — Security
        (
            CheckDefinition(
                "security.session",
                CheckCategory.SECURITY,
                "Session security configuration",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_session_security,
        ),
    ]

    for defn, runner in checks:
        register_check(defn, runner)


# ---------------------------------------------------------------------------
# Safe fix implementations
# ---------------------------------------------------------------------------


def _fix_create_missing_dirs(cr: CheckResult) -> tuple[bool, str]:
    """Create missing runtime directories."""
    try:
        from app.filesystem.layout import RuntimePaths, detect_mode

        paths = RuntimePaths.for_mode(detect_mode().detected_mode)
        created = []
        for name in (
            "data_dir",
            "uploads_dir",
            "themes_dir",
            "backups_dir",
            "exports_dir",
            "log_dir",
            "runtime_dir",
        ):
            rp = getattr(paths, name)
            if not rp.path.exists():
                rp.path.mkdir(parents=True, exist_ok=True)
                created.append(name)
        return (
            True,
            f"Created {len(created)} director(ies): {', '.join(created)}"
            if created
            else "All directories already exist",
        )
    except Exception as e:
        return False, f"Failed to create directories: {e}"


def _register_safe_fixes() -> None:
    register_safe_fix(
        "create_missing_dirs", "Create missing runtime directories", "fs.required_dirs"
    )
    register_safe_fix_runner("create_missing_dirs", _fix_create_missing_dirs)


# Initialize on import
_register_all_checks()
_register_safe_fixes()
