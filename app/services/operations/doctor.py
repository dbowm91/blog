"""Diagnostic framework for `devlog doctor`.

Provides a typed check registry, execution engine, safe-fix allowlist,
and human/JSON output for operational readiness assessment.
"""

from __future__ import annotations

import logging
import os
import shutil
import stat
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

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
    paths: dict[str, str] = field(default_factory=dict)
    safe_fix_plan: list[dict[str, Any]] = field(default_factory=list)

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
                "paths": dict(self.paths),
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
            "safe_fix_plan": list(self.safe_fix_plan),
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
    deep: bool = False


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
        deep: bool = False,
    ) -> list[CheckDefinition]:
        checks = list(self._checks.values())
        if category:
            checks = [c for c in checks if c.category == category]
        if production_only:
            checks = [c for c in checks if c.production_required]
        if not deep:
            checks = [c for c in checks if not c.deep]
        return sorted(checks, key=lambda c: (c.category, c.check_id))

    def all_ids(self) -> list[str]:
        return sorted(self._checks.keys())


_registry = CheckRegistry()


def get_registry() -> CheckRegistry:
    return _registry


def register_check(
    definition: CheckDefinition,
    runner: Callable[..., CheckResult],
) -> None:
    _registry.register(definition, runner)


# ---------------------------------------------------------------------------
# Doctor context — loaded once per run_doctor invocation
# ---------------------------------------------------------------------------


class DoctorContext:
    """Shared context pre-loaded once per doctor run."""

    __slots__ = ("mode", "version", "_config", "_config_loaded", "_paths", "_paths_loaded")

    def __init__(self, mode: str, version: str) -> None:
        self.mode = mode
        self.version = version
        self._config: Optional[Any] = None
        self._config_loaded = False
        self._paths: Optional[Any] = None
        self._paths_loaded = False

    @property
    def config(self) -> Any:
        if not self._config_loaded:
            try:
                from app.config.loader import load_effective_config

                self._config = load_effective_config()
            except Exception:
                pass
            self._config_loaded = True
        return self._config

    @property
    def paths(self) -> Any:
        if not self._paths_loaded:
            try:
                from app.filesystem.layout import RuntimePaths, InstallMode

                self._paths = RuntimePaths.for_mode(InstallMode(self.mode))
            except Exception:
                pass
            self._paths_loaded = True
        return self._paths


_ctx: threading.local = threading.local()


def _get_ctx() -> DoctorContext | None:
    return getattr(_ctx, "doctor_context", None)


def _set_ctx(ctx: DoctorContext) -> None:
    _ctx.doctor_context = ctx


# ---------------------------------------------------------------------------
# Execution engine
# ---------------------------------------------------------------------------


def _topological_sort(checks: list[CheckDefinition]) -> list[CheckDefinition]:
    id_to_defn = {c.check_id: c for c in checks}
    graph: dict[str, list[str]] = {}
    for c in checks:
        graph[c.check_id] = [p for p in c.prerequisites if p in id_to_defn]

    visited: set[str] = set()
    in_stack: set[str] = set()
    order: list[str] = []

    def dfs(node: str) -> None:
        if node in visited:
            return
        if node in in_stack:
            order.append(node)
            visited.add(node)
            return
        in_stack.add(node)
        for dep in graph.get(node, []):
            dfs(dep)
        in_stack.discard(node)
        visited.add(node)
        order.append(node)

    for c in checks:
        if c.check_id not in visited:
            dfs(c.check_id)

    seen: set[str] = set()
    unique: list[str] = []
    for cid in order:
        if cid not in seen:
            seen.add(cid)
            unique.append(cid)
    for c in checks:
        if c.check_id not in seen:
            unique.append(c.check_id)
    return [id_to_defn[cid] for cid in unique if cid in id_to_defn]


def _batch_by_level(checks: list[CheckDefinition]) -> list[list[CheckDefinition]]:
    id_to_defn = {c.check_id: c for c in checks}
    prereqs: dict[str, set[str]] = {}
    for c in checks:
        prereqs[c.check_id] = {p for p in c.prerequisites if p in id_to_defn}

    level: dict[str, int] = {}
    for c in checks:
        if not prereqs[c.check_id]:
            level[c.check_id] = 0

    changed = True
    while changed:
        changed = False
        for c in checks:
            if c.check_id in level:
                continue
            prereq_levels = [level[p] for p in prereqs[c.check_id] if p in level]
            if len(prereq_levels) == len(prereqs[c.check_id]):
                level[c.check_id] = max(prereq_levels) + 1
                changed = True

    for c in checks:
        if c.check_id not in level:
            level[c.check_id] = 0

    batches: dict[int, list[CheckDefinition]] = {}
    for c in checks:
        batches.setdefault(level[c.check_id], []).append(c)
    return [batches[k] for k in sorted(batches)]


_TIMEOUT_RESULT = object()


def _run_check_with_timeout(
    runner: Callable[..., CheckResult],
    timeout: float,
    app: Any = None,
    doctor_ctx: Any = None,
    **kwargs: Any,
) -> CheckResult:
    """Run a check function in a thread with per-check timeout."""
    result_holder: list[Any] = []

    def _target() -> None:
        if doctor_ctx is not None:
            _set_ctx(doctor_ctx)
        ctx_manager = app.app_context() if app is not None else None
        try:
            if ctx_manager is not None:
                ctx_manager.push()
            try:
                result_holder.append(runner(**kwargs))
            except Exception as e:
                result_holder.append(
                    CheckResult(
                        check_id=kwargs.get("check_id", "unknown"),
                        category=kwargs.get("category", "unknown"),
                        status=CheckStatus.ERROR,
                        severity=kwargs.get("severity", Severity.OPTIONAL),
                        summary=f"Check raised an internal error: {type(e).__name__}",
                        details={"error_type": type(e).__name__, "error": str(e)[:200]},
                    )
                )
        finally:
            if ctx_manager is not None:
                ctx_manager.pop()

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if t.is_alive():
        return CheckResult(
            check_id=kwargs.get("check_id", "unknown"),
            category=kwargs.get("category", "unknown"),
            status=CheckStatus.ERROR,
            severity=kwargs.get("severity", Severity.OPTIONAL),
            summary=f"Check timed out after {timeout:.0f}s",
        )

    if result_holder:
        return result_holder[0]
    return CheckResult(
        check_id=kwargs.get("check_id", "unknown"),
        category=kwargs.get("category", "unknown"),
        status=CheckStatus.ERROR,
        severity=kwargs.get("severity", Severity.OPTIONAL),
        summary="Check produced no result",
    )


def run_doctor(
    *,
    production: bool = False,
    category: str | None = None,
    check_ids: list[str] | None = None,
    fix_safe: bool = False,
    dry_run: bool = False,
    deep: bool = False,
    total_timeout: float = 120.0,
    parallel: bool = True,
) -> DoctorResult:
    engine_start = time.monotonic()

    try:
        from app.filesystem.layout import detect_mode

        mode = detect_mode().detected_mode.value
    except Exception as exc:
        return DoctorResult(
            ok=False,
            status="error",
            code="doctor.engine_error",
            summary=f"Engine error: {type(exc).__name__}",
            duration_ms=(time.monotonic() - engine_start) * 1000,
        )

    try:
        from importlib.metadata import version as pkg_version

        ver = pkg_version("devlog")
    except Exception:
        ver = "unknown"

    try:
        ctx = DoctorContext(mode, ver)
        _set_ctx(ctx)
    except Exception as exc:
        return DoctorResult(
            ok=False,
            status="error",
            code="doctor.engine_error",
            summary=f"Engine error: {type(exc).__name__}",
            mode=mode,
            version=ver,
            duration_ms=(time.monotonic() - engine_start) * 1000,
        )

    checks_to_run: list[CheckDefinition]
    if check_ids:
        checks_to_run = []
        for cid in check_ids:
            entry = _registry.get(cid)
            if entry is not None:
                checks_to_run.append(entry[0])
    else:
        checks_to_run = _registry.list_checks(category=category, production_only=False, deep=deep)

    checks_to_run = _topological_sort(checks_to_run)

    flask_app = None
    try:
        from flask import current_app

        flask_app = current_app._get_current_object()  # type: ignore[attr-defined]
    except Exception:
        pass

    results: list[CheckResult] = []

    def _run_single_check(defn: CheckDefinition) -> CheckResult:
        elapsed = time.monotonic() - engine_start
        if elapsed >= total_timeout:
            return CheckResult(
                check_id=defn.check_id,
                category=defn.category,
                status=CheckStatus.SKIP,
                severity=defn.severity,
                summary="Skipped: total timeout reached",
            )
        runner = _registry.get(defn.check_id)
        if runner is None:
            return CheckResult(
                check_id=defn.check_id,
                category=defn.category,
                status=CheckStatus.SKIP,
                severity=defn.severity,
                summary="Skipped: not registered",
            )
        remaining = total_timeout - elapsed
        per_check_timeout = min(defn.timeout_seconds, remaining)
        check_start = time.monotonic()
        cr = _run_check_with_timeout(
            runner[1],
            timeout=per_check_timeout,
            app=flask_app,
            doctor_ctx=ctx,
            check_id=defn.check_id,
            category=defn.category,
            severity=defn.severity,
        )
        cr_duration = (time.monotonic() - check_start) * 1000
        return CheckResult(
            check_id=cr.check_id,
            category=cr.category,
            status=cr.status,
            severity=cr.severity,
            summary=cr.summary,
            duration_ms=cr_duration,
            details=redact_details(cr.details),
            remediation=cr.remediation or list(defn.remediation),
            safe_fix_id=cr.safe_fix_id or defn.safe_fix_id,
        )

    if parallel and len(checks_to_run) > 1:
        batches = _batch_by_level(checks_to_run)
        for batch in batches:
            elapsed = time.monotonic() - engine_start
            if elapsed >= total_timeout:
                for defn in batch:
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
            threads: list[threading.Thread] = []
            batch_results: list[CheckResult | None] = [None] * len(batch)

            def _worker(idx: int, defn: CheckDefinition) -> None:
                batch_results[idx] = _run_single_check(defn)

            for i, defn in enumerate(batch):
                t = threading.Thread(target=_worker, args=(i, defn), daemon=True)
                threads.append(t)
                t.start()
            for t in threads:
                t.join(timeout=total_timeout - (time.monotonic() - engine_start))
            for i, defn in enumerate(batch):
                if batch_results[i] is not None:
                    results.append(batch_results[i])  # type: ignore[arg-type]
                else:
                    results.append(
                        CheckResult(
                            check_id=defn.check_id,
                            category=defn.category,
                            status=CheckStatus.ERROR,
                            severity=defn.severity,
                            summary="Check timed out or failed to complete",
                        )
                    )
    else:
        for defn in checks_to_run:
            elapsed = time.monotonic() - engine_start
            if elapsed >= total_timeout:
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
            results.append(_run_single_check(defn))

    paths_info: dict[str, str] = {}
    if ctx.paths:
        paths_info["data_dir"] = str(ctx.paths.data_dir.path)
        paths_info["database"] = str(ctx.paths.database.path)
        paths_info["config_file"] = str(ctx.paths.config_file.path)

    plan: list[dict[str, Any]] = []
    if fix_safe:
        if dry_run:
            fixes = get_safe_fix_plan(results)
            plan = [
                {"fix_id": f.fix_id, "description": f.description, "check_id": f.check_id}
                for f in fixes
            ]
        else:
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
        version=ver,
        duration_ms=total_duration,
        checks=results,
        warnings=all_warnings,
        remediation=all_remediation,
        paths=paths_info,
        safe_fix_plan=plan,
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
_SAFE_FIX_RUNNERS: dict[str, Callable[[CheckResult], tuple[bool, str]]] = {}


def register_safe_fix(fix_id: str, description: str, check_id: str) -> None:
    _SAFE_FIXES[fix_id] = SafeFix(fix_id=fix_id, description=description, check_id=check_id)


def register_safe_fix_runner(
    fix_id: str,
    fn: Callable[[CheckResult], tuple[bool, str]],
) -> None:
    _SAFE_FIX_RUNNERS[fix_id] = fn


def get_safe_fix_plan(results: list[CheckResult]) -> list[SafeFix]:
    applicable_ids = {
        c.safe_fix_id for c in results if c.safe_fix_id and c.status != CheckStatus.PASS
    }
    return [_SAFE_FIXES[fid] for fid in sorted(applicable_ids) if fid in _SAFE_FIXES]


def _apply_safe_fixes(results: list[CheckResult]) -> list[dict[str, Any]]:
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


# ---------------------------------------------------------------------------
# Secret redaction
# ---------------------------------------------------------------------------

_SECRET_PATTERNS = ("secret", "password", "token", "key", "credential")


def redact_details(details: dict[str, Any]) -> dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(**kw: Any) -> CheckResult:
    return CheckResult(**kw)


def _error_result(check_id: str, category: str, severity: str, exc: Exception) -> CheckResult:
    return _make_result(
        check_id=check_id,
        category=category,
        status=CheckStatus.ERROR,
        severity=severity,
        summary=f"Check raised: {type(exc).__name__}",
        details={"error": str(exc)[:200]},
    )


def _ctx_config() -> Any | None:
    ctx = _get_ctx()
    return ctx.config if ctx else None


def _ctx_paths() -> Any | None:
    ctx = _get_ctx()
    return ctx.paths if ctx else None


def _service_account() -> tuple[str, str] | None:
    """Return the account the service runs as, for a system installation.

    A system install runs under a dedicated unprivileged account; a user,
    Docker or development install runs as the account that owns the data.
    """
    ctx = _get_ctx()
    if ctx is None or ctx.mode != "system":
        return None
    return ("devlog", "devlog")


def _service_account_ids() -> tuple[int, int] | None:
    """Return the uid/gid of the service account, or None if it is absent."""
    account = _service_account()
    if account is None:
        return None
    try:
        import grp
        import pwd

        user, group = account
        return pwd.getpwnam(user).pw_uid, grp.getgrnam(group).gr_gid
    except (KeyError, ImportError):
        return None


def _writable_by(path: Path, uid: int, gid: int) -> bool:
    """Return whether an account can write to a path, judged by mode bits."""
    try:
        st = path.stat()
    except OSError:
        return False
    if st.st_uid == uid:
        return bool(st.st_mode & stat.S_IWUSR)
    if st.st_gid == gid:
        return bool(st.st_mode & stat.S_IWGRP)
    return bool(st.st_mode & stat.S_IWOTH)


def _is_sqlite() -> bool:
    try:
        from app.db_utils import is_sqlite_database

        return is_sqlite_database()
    except Exception:
        return False


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
        return _make_result(
            **kwargs, status=CheckStatus.WARN, summary="Could not determine package version"
        )
    return _make_result(
        **kwargs,
        status=CheckStatus.PASS,
        summary=f"Package version: {ver}",
        details={"version": ver},
    )


def _check_config_schema(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(
            **kwargs,
            status=CheckStatus.FAIL,
            summary="Configuration failed to load",
            remediation=["Check config.toml for syntax errors.", "Run `devlog config check`."],
        )
    return _make_result(
        **kwargs,
        status=CheckStatus.PASS,
        summary="Configuration loaded successfully",
        details={"title": cfg.app.title},
    )


def _check_config_validation(**kwargs: Any) -> CheckResult:
    try:
        from app.config.validation import validate_all

        cfg = _ctx_config()
        if cfg is None:
            return _make_result(
                **kwargs, status=CheckStatus.ERROR, summary="Config unavailable for validation"
            )
        result = validate_all(cfg)
        if result.errors:
            return _make_result(
                **kwargs,
                status=CheckStatus.FAIL,
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
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"{len(result.warnings)} configuration warning(s)",
                details={
                    "warnings": [
                        {"code": f.code, "message": f.message} for f in result.warnings[:10]
                    ]
                },
            )
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary="Configuration validation passed"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_secret_key(**kwargs: Any) -> CheckResult:
    secret_key = os.environ.get("SECRET_KEY", "")
    if not secret_key:
        return _make_result(
            **kwargs,
            status=CheckStatus.FAIL,
            summary="SECRET_KEY not set",
            remediation=["Set the SECRET_KEY environment variable."],
        )
    if secret_key in ("change-me", "changeme", "your-secret-key"):
        return _make_result(
            **kwargs,
            status=CheckStatus.FAIL,
            summary="SECRET_KEY appears to be a placeholder",
            remediation=[
                'Generate a real secret: python3 -c "import secrets; print(secrets.token_hex(32))"'
            ],
        )
    if len(secret_key) < 16:
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary="SECRET_KEY is shorter than recommended (16+ chars)",
        )
    return _make_result(
        **kwargs, status=CheckStatus.PASS, summary="SECRET_KEY is set and appears valid"
    )


def _check_admin_password(**kwargs: Any) -> CheckResult:
    pw = os.environ.get("ADMIN_PASSWORD", "")
    if not pw:
        return _make_result(
            **kwargs,
            status=CheckStatus.FAIL,
            summary="ADMIN_PASSWORD not set",
            remediation=["Set the ADMIN_PASSWORD environment variable."],
        )
    if len(pw) < 8:
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary="ADMIN_PASSWORD is shorter than recommended (8+ chars)",
        )
    return _make_result(**kwargs, status=CheckStatus.PASS, summary="ADMIN_PASSWORD is set")


def _check_installation_metadata(**kwargs: Any) -> CheckResult:
    try:
        from app.filesystem.layout import InstallationMetadata

        paths = _ctx_paths()
        if paths is None:
            return _make_result(
                **kwargs, status=CheckStatus.WARN, summary="Cannot resolve paths for metadata check"
            )
        meta = InstallationMetadata.load(paths.installation_metadata.path)
        if meta is None:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary="No installation metadata found",
                remediation=["Run `devlog onboard` to create installation metadata."],
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Installation metadata found (mode={meta.mode.value}, version={meta.version})",
            details={"mode": meta.mode.value, "version": meta.version},
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_release_symlink(**kwargs: Any) -> CheckResult:
    try:
        from app.filesystem.layout import detect_mode

        mode = detect_mode().detected_mode
        if mode.value not in ("system", "user"):
            return _make_result(
                **kwargs,
                status=CheckStatus.SKIP,
                summary=f"Release symlink check skipped (mode={mode.value})",
            )
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        release_dir = getattr(paths, "release_dir", None)
        if release_dir is None or not release_dir.path:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary="Release directory not configured",
                remediation=["Run `devlog deploy install` to set up the release directory."],
            )
        rd = release_dir.path
        if not rd.exists():
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary="Release directory does not exist",
                remediation=["Run `devlog deploy install` to create the release directory."],
            )
        if rd.is_symlink():
            target = rd.resolve()
            if not target.exists():
                return _make_result(
                    **kwargs,
                    status=CheckStatus.FAIL,
                    summary=f"Release symlink points to missing target: {target}",
                    remediation=["Reinstall with `devlog deploy install`."],
                )
            return _make_result(
                **kwargs,
                status=CheckStatus.PASS,
                summary=f"Release symlink valid: {rd} -> {target}",
            )
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary="Release directory exists (not a symlink)"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_config_path(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        cfg = _ctx_config()
        if paths is None or cfg is None:
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="Config/paths unavailable"
            )
        config_path = paths.config_file.path
        if not config_path.exists():
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"Config file not found at {config_path}",
                remediation=["Create a config.toml or run `devlog config init`."],
            )
        env_path = paths.env_file.path
        env_exists = env_path.exists()
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Config: {config_path}" + (f", env: {env_path}" if env_exists else ""),
            details={
                "config_path": str(config_path),
                "env_path": str(env_path),
                "env_exists": env_exists,
            },
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_deprecated_keys(**kwargs: Any) -> CheckResult:
    try:
        cfg = _ctx_config()
        if cfg is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
        from app.config.model import DevLogConfig

        valid_fields = {f.name for f in DevLogConfig.__dataclass_fields__.values()}
        valid_sections = {f.name for f in DevLogConfig.__dataclass_fields__.values()}
        raw_path = Path("config.toml")
        if not raw_path.exists():
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="config.toml not found on disk"
            )
        try:
            import tomllib

            with open(raw_path, "rb") as f:
                raw = tomllib.load(f)
        except Exception:
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="config.toml not parseable"
            )
        unknown = [k for k in raw if k not in valid_sections and k not in valid_fields]
        if unknown:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"{len(unknown)} unknown config key(s): {', '.join(unknown[:5])}",
                details={"unknown_keys": unknown},
                remediation=["Remove or rename unknown keys from config.toml."],
            )
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary="No unknown config keys detected"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_secret_permissions(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        env_path = paths.env_file.path
        if not env_path.exists():
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="No .env file to check permissions"
            )
        mode = env_path.stat().st_mode
        permissive = bool(mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH))
        if permissive:
            perms = oct(mode & 0o777)
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f".env file has permissive permissions: {perms}",
                remediation=["Run: chmod 600 " + str(env_path)],
            )
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary=".env file permissions are restrictive"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_stale_metadata(**kwargs: Any) -> CheckResult:
    try:
        from app.filesystem.layout import InstallationMetadata, detect_mode

        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        meta = InstallationMetadata.load(paths.installation_metadata.path)
        if meta is None:
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="No metadata to check for staleness"
            )
        detected = detect_mode().detected_mode
        if meta.mode != detected:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"Metadata mode ({meta.mode.value}) differs from detected ({detected.value})",
                remediation=["Re-run `devlog onboard` to update installation metadata."],
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Metadata mode consistent: {meta.mode.value}",
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


# ---------------------------------------------------------------------------
# H4 — Filesystem and capacity checks
# ---------------------------------------------------------------------------


def _check_required_directories(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.ERROR, summary="Cannot resolve paths")
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
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"{len(missing)} required director(ies) missing",
                details={"missing": missing},
                safe_fix_id="create_missing_dirs",
                remediation=["Create missing directories or run `devlog doctor --fix-safe`."],
            )
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary="All required directories exist"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


DISK_CRITICAL_FREE_MB = 500
DISK_LOW_FREE_MB = 5000


def _check_disk_space(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(
                **kwargs, status=CheckStatus.WARN, summary="Cannot resolve paths for disk check"
            )
        usage = shutil.disk_usage(paths.data_dir.path)
        free_mb = usage.free / (1024 * 1024)
        free_pct = (usage.free / usage.total) * 100 if usage.total else 0
        if free_mb < DISK_CRITICAL_FREE_MB or (free_pct < 5 and free_mb < DISK_LOW_FREE_MB):
            return _make_result(
                **kwargs,
                status=CheckStatus.FAIL,
                summary=f"Disk space critically low: {free_mb:.0f} MB ({free_pct:.1f}%)",
                details={"free_mb": round(free_mb, 1), "free_percent": round(free_pct, 1)},
                remediation=["Free disk space or expand the volume."],
            )
        if free_pct < 15 or free_mb < DISK_LOW_FREE_MB:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"Disk space low: {free_mb:.0f} MB ({free_pct:.1f}%)",
                details={"free_mb": round(free_mb, 1), "free_percent": round(free_pct, 1)},
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Disk space OK: {free_mb:.0f} MB ({free_pct:.1f}%)",
            details={"free_mb": round(free_mb, 1), "free_percent": round(free_pct, 1)},
        )
    except Exception as e:
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary=f"Could not check disk space: {type(e).__name__}",
        )


def _check_symlink_safety(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.ERROR, summary="Cannot resolve paths")
        project_root = Path.cwd()
        unsafe = []
        for name in ("data_dir", "uploads_dir", "themes_dir", "backups_dir"):
            rp = getattr(paths, name)
            if rp.path.exists() and rp.path.is_symlink():
                target = rp.path.resolve()
                if not str(target).startswith(str(project_root)):
                    unsafe.append({"name": name, "target": str(target)})
        if unsafe:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"{len(unsafe)} path(s) are symlinks outside project root",
                details={"unsafe_symlinks": unsafe},
            )
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary="No unsafe symlinks detected"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_dir_ownership(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        service_ids = _service_account_ids()
        expected_uid = service_ids[0] if service_ids else os.getuid()
        issues = []
        for name in ("data_dir", "uploads_dir", "backups_dir", "log_dir", "runtime_dir"):
            rp = getattr(paths, name)
            if rp.path.exists():
                try:
                    file_uid = rp.path.stat().st_uid
                    if file_uid != expected_uid:
                        issues.append(
                            {"name": name, "owner_uid": file_uid, "expected_uid": expected_uid}
                        )
                except OSError:
                    pass
        if issues:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"{len(issues)} directory(ies) owned by different user",
                details={"ownership_issues": issues},
                remediation=["Fix directory ownership with chown."],
            )
        return _make_result(**kwargs, status=CheckStatus.PASS, summary="Directory ownership OK")
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_service_account(**kwargs: Any) -> CheckResult:
    """Verify the account the systemd unit runs as exists on this host.

    The rendered units run as ``devlog``. Nothing in the installer or in
    onboarding creates a system account, so a missing one is the single most
    common reason a freshly installed service will not start.
    """
    account = _service_account()
    if account is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Not a system installation")
    user, group = account
    try:
        import pwd

        pwd.getpwnam(user)
    except (KeyError, ImportError):
        return _make_result(
            **kwargs,
            status=CheckStatus.FAIL,
            summary=f"Service account '{user}' does not exist",
            details={"user": user, "group": group},
            remediation=[
                f"useradd --system --home-dir /var/lib/devlog --shell /usr/sbin/nologin {user}",
                f"chown -R {user}:{group} /var/lib/devlog /var/log/devlog",
            ],
        )
    return _make_result(
        **kwargs, status=CheckStatus.PASS, summary=f"Service account '{user}' exists"
    )


def _check_dir_writable(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        service_ids = _service_account_ids()
        not_writable = []
        for name in (
            "data_dir",
            "uploads_dir",
            "backups_dir",
            "exports_dir",
            "log_dir",
            "runtime_dir",
        ):
            rp = getattr(paths, name)
            if not rp.path.exists():
                continue
            if service_ids:
                writable = _writable_by(rp.path, service_ids[0], service_ids[1])
            else:
                writable = os.access(rp.path, os.W_OK)
            if not writable:
                not_writable.append(name)
        if not_writable:
            return _make_result(
                **kwargs,
                status=CheckStatus.FAIL,
                summary=f"{len(not_writable)} directory(ies) not writable",
                details={"not_writable": not_writable},
                remediation=["Fix directory permissions."],
            )
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary="All runtime directories are writable"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_inodes(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        stat_result = os.statvfs(str(paths.data_dir.path))
        free_inodes = stat_result.f_favail
        if free_inodes < 1000:
            return _make_result(
                **kwargs,
                status=CheckStatus.FAIL,
                summary=f"Inode availability critically low: {free_inodes}",
                details={"free_inodes": free_inodes},
                remediation=["Free inodes or expand the volume."],
            )
        if free_inodes < 10000:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"Inode availability low: {free_inodes}",
                details={"free_inodes": free_inodes},
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Inode availability OK: {free_inodes}",
            details={"free_inodes": free_inodes},
        )
    except Exception as e:
        return _make_result(
            **kwargs, status=CheckStatus.WARN, summary=f"Could not check inodes: {type(e).__name__}"
        )


def _check_fs_type(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        if not _is_sqlite():
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="FS type check skipped (not SQLite)"
            )
        db_path = paths.database.path
        if not db_path.exists():
            return _make_result(
                **kwargs,
                status=CheckStatus.SKIP,
                summary="Database file not found for FS type check",
            )
        try:
            result = os.statvfs(str(db_path))
            f_type = getattr(result, "f_type", 0)
            known_problematic = {
                0x65735546: "FUSE",
                0x5346544E: "NTFS",
                0x4D44: "FAT32",
                0xEF53: "ext4",
                0x58465342: "XFS",
                0x9123683E: "Btrfs",
                0xFF534D42: "CIFS/SMB",
            }
            fs_name = known_problematic.get(f_type, f"unknown({hex(f_type)})")
            warnings_list = []
            if f_type in (0x65735546, 0x5346544E, 0x4D44, 0xFF534D42):
                warnings_list.append(
                    f"Filesystem {fs_name} may not support SQLite locking properly"
                )
            if warnings_list:
                return _make_result(
                    **kwargs,
                    status=CheckStatus.WARN,
                    summary=f"FS: {fs_name} — potential SQLite issue",
                    details={"fs_type": fs_name, "f_type_hex": hex(f_type)},
                    remediation=warnings_list,
                )
            return _make_result(
                **kwargs,
                status=CheckStatus.PASS,
                summary=f"Filesystem: {fs_name}",
                details={"fs_type": fs_name},
            )
        except Exception:
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="Could not determine filesystem type"
            )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_docker_uid(**kwargs: Any) -> CheckResult:
    try:
        cgroup_path = Path("/proc/self/cgroup")
        if not cgroup_path.exists():
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="Not in Docker (no cgroup)"
            )
        try:
            content = cgroup_path.read_text()
            if "docker" not in content and "kubepods" not in content:
                return _make_result(
                    **kwargs, status=CheckStatus.SKIP, summary="Not in Docker container"
                )
        except Exception:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Could not read cgroup")
        host_uid_file = Path("/proc/1/uid_map")
        if not host_uid_file.exists():
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="Cannot determine host UID mapping"
            )
        try:
            uid_map = host_uid_file.read_text().strip()
            return _make_result(
                **kwargs,
                status=CheckStatus.PASS,
                summary=f"Docker UID mapping: {uid_map}",
                details={"uid_map": uid_map},
            )
        except Exception:
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="Could not read UID mapping"
            )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_stale_files(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        stale = []
        runtime_dir = paths.runtime_dir.path
        if runtime_dir.exists():
            now = time.time()
            for f in runtime_dir.iterdir():
                if f.is_file():
                    age_hours = (now - f.stat().st_mtime) / 3600
                    if age_hours > 72:
                        stale.append({"name": f.name, "age_hours": round(age_hours, 1)})
        if stale:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"{len(stale)} stale runtime file(s) older than 72h",
                details={"stale_files": stale[:10]},
                remediation=["Remove stale runtime files manually."],
            )
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary="No stale runtime files detected"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_legacy_remnants(**kwargs: Any) -> CheckResult:
    try:
        from app.filesystem.discovery import discover_legacy_layout, classify_discovery

        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        try:
            discovery = discover_legacy_layout(Path.cwd())
            classified = classify_discovery(discovery, paths)
            unmanaged = {k: v for k, v in classified.items() if v == "likely_devlog"}
            if unmanaged:
                return _make_result(
                    **kwargs,
                    status=CheckStatus.WARN,
                    summary=f"{len(unmanaged)} legacy file(s) detected",
                    details={"legacy_items": list(unmanaged.keys())[:10]},
                    remediation=["Review legacy files and migrate or remove."],
                )
        except Exception:
            pass
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary="No legacy remnants detected"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


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
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Database connected ({latency_ms:.1f}ms)",
            details={"latency_ms": round(latency_ms, 2)},
        )
    except Exception as e:
        return _make_result(
            **kwargs,
            status=CheckStatus.FAIL,
            summary=f"Database connection failed: {type(e).__name__}",
            details={"error": str(e)[:200]},
            remediation=["Check database URI and connectivity."],
        )


def _check_migration_head(**kwargs: Any) -> CheckResult:
    try:
        from app.services.operations.database import get_migration_status

        result = get_migration_status()
        if result.ok:
            return _make_result(
                **kwargs,
                status=CheckStatus.PASS,
                summary=result.summary,
                details={
                    "current_head": result.current_head,
                    "pending_count": result.pending_count,
                },
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.FAIL,
            summary=result.summary,
            details=result.details,
            remediation=result.remediation,
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_sqlite_integrity(**kwargs: Any) -> CheckResult:
    if not _is_sqlite():
        return _make_result(
            **kwargs, status=CheckStatus.SKIP, summary="Integrity check skipped (not SQLite)"
        )
    try:
        from app.services.operations.database import check_database_integrity

        result = check_database_integrity()
        if result.ok:
            return _make_result(**kwargs, status=CheckStatus.PASS, summary=result.summary)
        return _make_result(
            **kwargs,
            status=CheckStatus.FAIL,
            summary=result.summary,
            details=result.details,
            remediation=result.remediation,
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_fts5_availability(**kwargs: Any) -> CheckResult:
    if not _is_sqlite():
        return _make_result(
            **kwargs, status=CheckStatus.SKIP, summary="FTS5 check skipped (not SQLite)"
        )
    try:
        from sqlalchemy import text
        from app.extensions import db

        has_fts = db.session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'")
        ).fetchone()
        if has_fts:
            return _make_result(
                **kwargs, status=CheckStatus.PASS, summary="FTS5 search index exists"
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary="FTS5 search index not found",
            safe_fix_id="rebuild_fts",
            remediation=["Run `devlog db rebuild-search` to create the search index."],
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_database_path_match(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        cfg = _ctx_config()
        if paths is None or cfg is None:
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="Config/paths unavailable"
            )
        db_uri = cfg.database.uri
        if db_uri.startswith("sqlite:///"):
            db_path = Path(db_uri.replace("sqlite:///", "/"))
            expected = paths.database.path.resolve()
            if db_path.resolve() == expected:
                return _make_result(
                    **kwargs, status=CheckStatus.PASS, summary="Database path matches RuntimePaths"
                )
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary="Database path differs from RuntimePaths",
                details={"config_path": str(db_path), "expected_path": str(expected)},
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.SKIP,
            summary="Path match check skipped (non-SQLite backend)",
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_wal_checkpoint(**kwargs: Any) -> CheckResult:
    if not _is_sqlite():
        return _make_result(
            **kwargs, status=CheckStatus.SKIP, summary="WAL check skipped (not SQLite)"
        )
    try:
        from sqlalchemy import text
        from app.extensions import db

        result = db.session.execute(text("PRAGMA wal_checkpoint(PASS)")).fetchone()
        if result and result[0] == 0:
            return _make_result(**kwargs, status=CheckStatus.PASS, summary="WAL checkpoint OK")
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary="WAL checkpoint returned non-zero",
            details={"result": list(result) if result else None},
            remediation=["Run `PRAGMA wal_checkpoint(TRUNCATE)` to force a checkpoint."],
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_db_ownership(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        db_path = paths.database.path
        if not db_path.exists():
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="Database file not found"
            )
        my_uid = os.getuid()
        file_uid = db_path.stat().st_uid
        if file_uid != my_uid:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"Database owned by UID {file_uid}, expected {my_uid}",
                remediation=["Fix database file ownership."],
            )
        return _make_result(**kwargs, status=CheckStatus.PASS, summary="Database file ownership OK")
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_fts_health(**kwargs: Any) -> CheckResult:
    if not _is_sqlite():
        return _make_result(
            **kwargs, status=CheckStatus.SKIP, summary="FTS health check skipped (not SQLite)"
        )
    try:
        from sqlalchemy import text
        from app.extensions import db

        has_fts = db.session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'")
        ).fetchone()
        if not has_fts:
            return _make_result(
                **kwargs,
                status=CheckStatus.SKIP,
                summary="FTS table does not exist (checked by fts5)",
            )
        row_count = db.session.execute(text("SELECT COUNT(*) FROM posts_fts")).scalar() or 0
        post_count = (
            db.session.execute(
                text("SELECT COUNT(*) FROM posts WHERE published IS NOT NULL")
            ).scalar()
            or 0
        )
        if post_count > 0 and row_count == 0:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"FTS index empty but {post_count} published posts exist",
                remediation=["Run `devlog db rebuild-search` to repopulate the FTS index."],
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"FTS index has {row_count} rows",
            details={"fts_rows": row_count, "published_posts": post_count},
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_migration_orphaned(**kwargs: Any) -> CheckResult:
    try:
        from sqlalchemy import text
        from app.extensions import db

        result = db.session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
        ).fetchone()
        if not result:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary="Alembic version table missing — migrations may not have run",
                remediation=["Run `flask db upgrade` to initialize migrations."],
            )
        head = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if not head:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary="Alembic version table is empty",
                remediation=["Run `flask db upgrade` to apply migrations."],
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Migration head: {head}",
            details={"head": head},
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_backend_features(**kwargs: Any) -> CheckResult:
    try:
        from app.db_utils import get_database_dialect

        dialect = get_database_dialect()
        if dialect == "sqlite":
            return _make_result(
                **kwargs,
                status=CheckStatus.PASS,
                summary="Backend: SQLite (all features supported)",
                details={"dialect": dialect},
            )
        if dialect in ("postgresql", "mysql"):
            return _make_result(
                **kwargs,
                status=CheckStatus.PASS,
                summary=f"Backend: {dialect}",
                details={"dialect": dialect},
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary=f"Backend: {dialect} — some features may not work",
            details={"dialect": dialect},
            remediation=["Consider using SQLite or PostgreSQL for full feature support."],
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


# ---------------------------------------------------------------------------
# H6 — Application assets and themes
# ---------------------------------------------------------------------------


def _check_frontend_manifest(**kwargs: Any) -> CheckResult:
    manifest = Path("app/static/.vite/manifest.json")
    if not manifest.exists():
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary="Vite manifest not found",
            remediation=["Build frontend assets to generate the manifest file."],
        )
    try:
        import json

        data = json.loads(manifest.read_text())
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Vite manifest present ({len(data)} entries)",
            details={"entry_count": len(data)},
        )
    except Exception as e:
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary=f"Vite manifest unreadable: {type(e).__name__}",
        )


def _check_bundled_themes(**kwargs: Any) -> CheckResult:
    try:
        from app.themes.registry import ThemeRegistry

        registry = ThemeRegistry()
        themes = registry.list_themes()
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Bundled theme catalog: {len(themes)} themes",
            details={"theme_count": len(themes)},
        )
    except Exception as e:
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary=f"Theme catalog check raised: {type(e).__name__}",
            details={"error": str(e)[:200]},
        )


def _check_selected_themes(**kwargs: Any) -> CheckResult:
    try:
        from app.models import SiteSettings
        from app.services.theme_settings import get_effective_theme_names

        try:
            settings = SiteSettings.get_instance()
        except Exception:
            return _make_result(
                **kwargs,
                status=CheckStatus.SKIP,
                summary="Theme selection check skipped (site_settings table unavailable)",
            )
        dark, light, _scheme = get_effective_theme_names(settings=settings, config_defaults={})
        from app.themes.registry import ThemeRegistry

        registry = ThemeRegistry()
        missing = []
        if dark and not registry.resolve(dark):
            missing.append(dark)
        if light and not registry.resolve(light):
            missing.append(light)
        if missing:
            return _make_result(
                **kwargs,
                status=CheckStatus.FAIL,
                summary=f"{len(missing)} selected theme(s) not found",
                details={"missing_themes": missing, "dark": dark, "light": light},
                remediation=["Check theme configuration in admin settings."],
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Selected themes resolve: dark={dark}, light={light}",
            details={"dark": dark, "light": light},
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_referenced_assets(**kwargs: Any) -> CheckResult:
    try:
        manifest = Path("app/static/.vite/manifest.json")
        if not manifest.exists():
            return _make_result(
                **kwargs,
                status=CheckStatus.SKIP,
                summary="Vite manifest not found (checked by assets.frontend_manifest)",
            )
        import json

        data = json.loads(manifest.read_text())
        missing_assets = []
        for entry_key, entry_val in data.items():
            if isinstance(entry_val, dict) and "file" in entry_val:
                asset_path = Path("app/static") / entry_val["file"]
                if not asset_path.exists():
                    missing_assets.append(entry_val["file"])
        if missing_assets:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"{len(missing_assets)} referenced asset(s) missing",
                details={"missing_assets": missing_assets[:10]},
                remediation=["Rebuild frontend assets to regenerate missing files."],
            )
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary="All referenced assets exist"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_theme_accessibility(**kwargs: Any) -> CheckResult:
    try:
        from app.themes.registry import ThemeRegistry

        registry = ThemeRegistry()
        themes = registry.list_themes()
        if not themes:
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="No themes to check accessibility"
            )
        try:
            _loaded = registry.load(themes[0].canonical_name)
            return _make_result(
                **kwargs,
                status=CheckStatus.PASS,
                summary=f"Theme catalog accessible ({len(themes)} themes)",
                details={"theme_count": len(themes), "sample_theme": themes[0]},
            )
        except Exception:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary="Theme catalog accessibility check failed",
            )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_theme_attribution(**kwargs: Any) -> CheckResult:
    try:
        from app.themes import bundled as bundled_pkg

        bundled_dir = Path(bundled_pkg.__file__).parent
        attribution = bundled_dir / "ATTRIBUTION.md"
        manifest = bundled_dir / "catalog_manifest.json"
        issues = []
        if not attribution.exists():
            issues.append("ATTRIBUTION.md missing")
        if not manifest.exists():
            issues.append("catalog_manifest.json missing")
        if issues:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"Theme packaging issues: {', '.join(issues)}",
                remediation=[
                    "Ensure ATTRIBUTION.md and catalog_manifest.json are present in bundled themes."
                ],
            )
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary="Theme attribution and manifest present"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_upload_serving(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        cfg = _ctx_config()
        if paths is None or cfg is None:
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="Config/paths unavailable"
            )
        issues = []
        uploads_dir = paths.uploads_dir.path
        static_dir = Path("app/static")
        if not uploads_dir.exists():
            issues.append("uploads_dir missing")
        if not static_dir.exists():
            issues.append("static_dir missing")
        if issues:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"Asset serving assumptions unmet: {', '.join(issues)}",
                details={"issues": issues},
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary="Upload and static directories present",
            details={"uploads_dir": str(uploads_dir), "static_dir": str(static_dir)},
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_external_theme_dir(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
    ext_dir = cfg.themes.external_dir
    if not ext_dir:
        return _make_result(
            **kwargs, status=CheckStatus.SKIP, summary="No external theme directory configured"
        )
    try:
        ext_path = Path(ext_dir)
        if not ext_path.exists():
            return _make_result(
                **kwargs,
                status=CheckStatus.FAIL,
                summary=f"External theme directory does not exist: {ext_dir}",
                remediation=["Create the directory or remove themes.external_dir from config."],
            )
        if not os.access(ext_path, os.R_OK):
            return _make_result(
                **kwargs,
                status=CheckStatus.FAIL,
                summary=f"External theme directory not readable: {ext_dir}",
                remediation=["Fix directory permissions."],
            )
        theme_count = len(list(ext_path.glob("*.toml")))
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"External theme directory OK ({theme_count} themes)",
            details={"external_dir": str(ext_path), "theme_count": theme_count},
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


# ---------------------------------------------------------------------------
# H7 — Dependency and integration checks
# ---------------------------------------------------------------------------


def _check_redis_connectivity(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
    redis_url = cfg.redis.url
    if not redis_url:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Redis not configured")
    try:
        import redis as redis_lib

        client = redis_lib.Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        return _make_result(**kwargs, status=CheckStatus.PASS, summary="Redis connected")
    except ImportError:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Redis client not installed")
    except Exception as e:
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary=f"Redis connection failed: {type(e).__name__}",
            details={"error": str(e)[:200]},
            remediation=["Check Redis configuration and connectivity."],
        )


def _check_redis_auth(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
    redis_url = cfg.redis.url
    if not redis_url:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Redis not configured")
    try:
        import redis as redis_lib

        client = redis_lib.Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        info = client.info("server")
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Redis {info.get('redis_version', 'unknown')} — auth OK",
            details={"redis_version": info.get("redis_version", "unknown")},
        )
    except ImportError:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Redis client not installed")
    except redis_lib.AuthenticationError:
        return _make_result(
            **kwargs,
            status=CheckStatus.FAIL,
            summary="Redis authentication failed",
            remediation=["Check Redis password configuration."],
        )
    except Exception as e:
        err_str = str(e).lower()
        if "auth" in err_str or "password" in err_str:
            return _make_result(
                **kwargs,
                status=CheckStatus.FAIL,
                summary="Redis authentication failed",
                remediation=["Check Redis password configuration."],
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary=f"Redis auth check failed: {type(e).__name__}",
        )


def _check_celery_broker(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
    broker = cfg.celery.broker_url
    if not broker:
        return _make_result(
            **kwargs, status=CheckStatus.SKIP, summary="Celery broker not configured"
        )
    return _make_result(
        **kwargs,
        status=CheckStatus.PASS,
        summary=f"Celery broker configured: {broker.split('@')[-1] if '@' in broker else broker[:30]}",
    )


def _check_celery_workers(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
    broker = cfg.celery.broker_url
    if not broker:
        return _make_result(
            **kwargs, status=CheckStatus.SKIP, summary="Celery broker not configured"
        )
    try:
        import redis as redis_lib

        broker_url = broker
        if broker_url.startswith("redis://"):
            client = redis_lib.Redis.from_url(
                broker_url, socket_connect_timeout=2, socket_timeout=2
            )
            try:
                keys = client.keys("celery*")
                return _make_result(
                    **kwargs,
                    status=CheckStatus.PASS,
                    summary=f"Celery broker accessible, {len(keys)} celery key(s)",
                    details={"celery_keys": len(keys)},
                )
            except Exception:
                return _make_result(
                    **kwargs, status=CheckStatus.WARN, summary="Cannot inspect Celery broker keys"
                )
        return _make_result(
            **kwargs,
            status=CheckStatus.SKIP,
            summary="Celery worker check only supports Redis broker",
        )
    except ImportError:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Redis client not installed")
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_scheduler_running(**kwargs: Any) -> CheckResult:
    try:
        from app.scheduler import get_scheduler_status

        running = get_scheduler_status()
        if running:
            return _make_result(**kwargs, status=CheckStatus.PASS, summary="Scheduler is running")
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary="Scheduler is not running",
            remediation=["Start the application to activate the scheduler."],
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_scheduler_stale(**kwargs: Any) -> CheckResult:
    try:
        cfg = _ctx_config()
        if cfg is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
        if not cfg.scheduler.enabled:
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="Scheduler disabled in config"
            )
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        lock_file = paths.runtime_dir.path / "scheduler.lock"
        if lock_file.exists():
            age_hours = (time.time() - lock_file.stat().st_mtime) / 3600
            if age_hours > 24:
                return _make_result(
                    **kwargs,
                    status=CheckStatus.WARN,
                    summary=f"Scheduler lock file is {age_hours:.0f}h old — may be stale",
                    details={"lock_age_hours": round(age_hours, 1)},
                    remediation=["Check if the scheduler process is running."],
                )
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary="Scheduler lock file OK or absent"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_smtp_config(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
    host = cfg.email.smtp_host
    if not host:
        return _make_result(
            **kwargs, status=CheckStatus.SKIP, summary="SMTP not configured (no host)"
        )
    return _make_result(
        **kwargs,
        status=CheckStatus.PASS,
        summary=f"SMTP configured: {host}:{cfg.email.smtp_port}",
        details={"host": host, "port": cfg.email.smtp_port},
    )


def _check_smtp_connect(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
    host = cfg.email.smtp_host
    if not host:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="SMTP not configured")
    try:
        import socket

        sock = socket.create_connection((host, cfg.email.smtp_port), timeout=5)
        sock.close()
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"SMTP connection to {host}:{cfg.email.smtp_port} succeeded",
        )
    except socket.timeout:
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary=f"SMTP connection to {host} timed out",
            remediation=["Check SMTP host and port, and verify network connectivity."],
        )
    except OSError as e:
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary=f"SMTP connection failed: {e}",
            remediation=["Check SMTP host, port, and DNS resolution."],
        )


def _check_storage_backend(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
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
            return _make_result(
                **kwargs,
                status=CheckStatus.FAIL,
                summary=f"S3 backend selected but missing: {', '.join(missing)}",
                details={"missing_vars": missing},
                remediation=[f"Set {v} environment variable." for v in missing],
            )
    return _make_result(
        **kwargs,
        status=CheckStatus.PASS,
        summary=f"Storage backend: {backend}",
        details={"backend": backend},
    )


def _check_storage_writable(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        uploads = paths.uploads_dir.path
        if not uploads.exists():
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary="Uploads directory does not exist",
                safe_fix_id="create_missing_dirs",
            )
        try:
            test_file = uploads / ".doctor_write_test"
            test_file.write_text("test")
            test_file.unlink()
            return _make_result(
                **kwargs, status=CheckStatus.PASS, summary="Uploads directory is writable"
            )
        except OSError:
            return _make_result(
                **kwargs,
                status=CheckStatus.FAIL,
                summary="Uploads directory is not writable",
                remediation=["Fix directory permissions."],
            )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_redis_db(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
    redis_url = cfg.redis.url
    if not redis_url:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Redis not configured")
    try:
        import redis as redis_lib

        client = redis_lib.Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        actual_db = client.connection_pool.connection_kwargs.get("db", 0)
        client.select(actual_db)
        test_key = "_devlog_doctor_db_verify"
        client.set(test_key, "1", ex=10)
        val = client.get(test_key)
        client.delete(test_key)
        if val is None:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"Redis DB {actual_db} — write/read test failed",
                details={"db": actual_db},
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Redis DB {actual_db} verified (write/read OK)",
            details={
                "db": actual_db,
                "redis_version": client.info("server").get("redis_version", "unknown"),
            },
        )
    except ImportError:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Redis client not installed")
    except Exception as e:
        return _make_result(
            **kwargs, status=CheckStatus.WARN, summary=f"Redis DB check failed: {type(e).__name__}"
        )


def _check_celery_routing(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
    broker = cfg.celery.broker_url
    if not broker:
        return _make_result(
            **kwargs, status=CheckStatus.SKIP, summary="Celery broker not configured"
        )
    from urllib.parse import urlparse

    parsed = urlparse(broker)
    supported = {"redis", "amqp", "sqs", "s3", "file"}
    if not parsed.scheme:
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary="Celery broker URL has no scheme",
            details={"broker_url": broker[:40]},
        )
    if parsed.scheme in supported:
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Celery routing scheme OK: {parsed.scheme}",
            details={"scheme": parsed.scheme},
        )
    return _make_result(
        **kwargs,
        status=CheckStatus.WARN,
        summary=f"Celery routing uses unusual scheme: {parsed.scheme}",
        details={"scheme": parsed.scheme},
    )


def _check_celery_version(**kwargs: Any) -> CheckResult:
    try:
        from celery import __version__ as celery_version

        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Celery version: {celery_version}",
            details={"celery_version": celery_version},
        )
    except ImportError:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Celery not installed")
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_scheduler_runs(**kwargs: Any) -> CheckResult:
    try:
        from app.scheduler import get_scheduler_status

        running = get_scheduler_status()
        if not running:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary="Scheduler is not running",
                remediation=["Start the application to activate the scheduler."],
            )
        try:
            from app import scheduler as sched_mod

            apscheduler = getattr(sched_mod, "_scheduler", None)
            if apscheduler is not None:
                jobs = apscheduler.get_jobs()
                job_info = []
                for job in jobs[:5]:
                    next_run = job.next_run_time
                    job_info.append(
                        {
                            "id": job.id,
                            "next_run": str(next_run) if next_run else "none",
                        }
                    )
                return _make_result(
                    **kwargs,
                    status=CheckStatus.PASS,
                    summary=f"Scheduler running with {len(jobs)} job(s)",
                    details={"job_count": len(jobs), "jobs": job_info},
                )
        except Exception:
            pass
        return _make_result(**kwargs, status=CheckStatus.PASS, summary="Scheduler is running")
    except Exception:
        return _make_result(
            **kwargs, status=CheckStatus.SKIP, summary="Scheduler status not determinable"
        )


def _check_storage_s3_probe(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
    if cfg.storage.backend != "s3":
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="S3 backend not configured")
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError

        kwargs_client: dict[str, Any] = {
            "aws_access_key_id": cfg.storage.s3_access_key,
            "aws_secret_access_key": cfg.storage.s3_secret_key,
        }
        if cfg.storage.s3_region:
            kwargs_client["region_name"] = cfg.storage.s3_region
        if cfg.storage.s3_endpoint:
            kwargs_client["endpoint_url"] = cfg.storage.s3_endpoint
        client = boto3.client("s3", **kwargs_client)
        client.head_bucket(Bucket=cfg.storage.s3_bucket)
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"S3 bucket accessible: {cfg.storage.s3_bucket}",
            details={"bucket": cfg.storage.s3_bucket},
        )
    except ImportError:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="boto3 not installed")
    except NoCredentialsError:
        return _make_result(
            **kwargs,
            status=CheckStatus.FAIL,
            summary="S3 credentials not configured",
            remediation=["Check S3_ACCESS_KEY and S3_SECRET_KEY."],
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary=f"S3 probe failed: {code}",
            details={"error_code": code},
            remediation=["Check S3 bucket name and permissions."],
        )
    except Exception as e:
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary=f"S3 probe failed: {type(e).__name__}",
            details={"error": str(e)[:200]},
        )


# ---------------------------------------------------------------------------
# H8 — Deployment and service checks
# ---------------------------------------------------------------------------


def _check_deployment_mode(**kwargs: Any) -> CheckResult:
    try:
        from app.filesystem.layout import detect_mode

        mode = detect_mode().detected_mode
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Deployment mode: {mode.value}",
            details={"mode": mode.value},
        )
    except Exception as e:
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary=f"Could not detect deployment mode: {type(e).__name__}",
        )


def _check_deploy_drift(**kwargs: Any) -> CheckResult:
    try:
        from app.services.operations.deploy import deploy_check

        try:
            result = deploy_check("system")
        except (KeyError, ValueError):
            return _make_result(
                **kwargs,
                status=CheckStatus.SKIP,
                summary="Deployment drift check skipped (missing env vars)",
            )
        if result.ok:
            return _make_result(
                **kwargs, status=CheckStatus.PASS, summary="No deployment drift detected"
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary=result.summary,
            details=result.details,
            remediation=result.remediation,
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_service_state(**kwargs: Any) -> CheckResult:
    try:
        from app.services.operations.deploy import lifecycle_status

        result = lifecycle_status()
        if result.ok:
            return _make_result(
                **kwargs, status=CheckStatus.PASS, summary=result.summary, details=result.details
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary=result.summary,
            details=result.details,
            remediation=result.remediation,
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_deploy_files(**kwargs: Any) -> CheckResult:
    try:
        from app.filesystem.layout import detect_mode

        mode = detect_mode().detected_mode
        if mode.value not in ("system", "user"):
            return _make_result(
                **kwargs,
                status=CheckStatus.SKIP,
                summary=f"Deploy file check skipped (mode={mode.value})",
            )
        manifest_path = (
            Path("/etc/devlog/.devlog-manifest.json")
            if mode.value == "system"
            else Path.home() / ".config/devlog/.devlog-manifest.json"
        )
        if not manifest_path.exists():
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary="No deployment manifest found",
                remediation=["Run `devlog deploy install` to create deployment files."],
            )
        return _make_result(**kwargs, status=CheckStatus.PASS, summary="Deployment manifest found")
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_health_endpoint(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
    host = cfg.server.host
    port = cfg.server.port
    try:
        import socket

        sock = socket.create_connection((host, port), timeout=3)
        sock.close()
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Health endpoint reachable at {host}:{port}",
            details={"host": host, "port": port},
        )
    except Exception:
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary=f"Health endpoint not reachable at {host}:{port} (app may not be running)",
            details={"host": host, "port": port},
        )


def _check_proxy_config(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
    proxy_count = cfg.proxy_count
    host = cfg.server.host
    if host in ("0.0.0.0", "::"):
        if proxy_count == 0:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary="Binding to all interfaces with proxy_count=0 — X-Forwarded-For may not work",
                remediation=["Set PROXY_COUNT if behind a reverse proxy."],
            )
    return _make_result(
        **kwargs, status=CheckStatus.PASS, summary=f"Proxy config: count={proxy_count}, host={host}"
    )


def _check_bind_address(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
    host = cfg.server.host
    port = cfg.server.port
    if host in ("0.0.0.0", "::"):
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary=f"Binding to all interfaces ({host}:{port}) — not suitable for direct public exposure",
            remediation=["Bind to 127.0.0.1 if not behind a reverse proxy."],
        )
    return _make_result(**kwargs, status=CheckStatus.PASS, summary=f"Binding to {host}:{port}")


def _check_stale_pid(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        runtime_dir = paths.runtime_dir.path
        if not runtime_dir.exists():
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="Runtime directory does not exist"
            )
        pid_files = list(runtime_dir.glob("*.pid"))
        if not pid_files:
            return _make_result(
                **kwargs, status=CheckStatus.PASS, summary="No PID files in runtime directory"
            )
        stale_pids = []
        for pf in pid_files:
            try:
                pid = int(pf.read_text().strip())
                try:
                    os.kill(pid, 0)
                except OSError:
                    stale_pids.append({"file": pf.name, "pid": pid})
            except (ValueError, OSError):
                pass
        if stale_pids:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"{len(stale_pids)} stale PID file(s) found",
                details={"stale_pids": stale_pids},
                safe_fix_id="cleanup_stale_pid",
                remediation=["Remove stale PID files for dead processes."],
            )
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary="All PID files reference running processes"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_restart_loop(**kwargs: Any) -> CheckResult:
    try:
        from app.services.operations.deploy import lifecycle_status

        result = lifecycle_status()
        if not result.ok:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"Service not running: {result.summary}",
                remediation=result.remediation or ["Check service logs for failure details."],
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary="Service is running (no restart loop detected)",
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_systemd_syntax(**kwargs: Any) -> CheckResult:
    try:
        import subprocess

        try:
            from app.deployment import systemd as systemd_mod

            unit_dir = Path(systemd_mod.__file__).parent
            unit_files = list(unit_dir.glob("*.service")) + list(unit_dir.glob("*.timer"))
            if not unit_files:
                return _make_result(
                    **kwargs, status=CheckStatus.SKIP, summary="No systemd unit files found"
                )
        except (ImportError, AttributeError):
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="Deployment module not available"
            )

        try:
            result = subprocess.run(
                ["systemd-analyze", "verify", "--no-pager", str(unit_files[0])],
                capture_output=True,
                text=True,
                timeout=8,
            )
            if result.returncode == 0:
                return _make_result(
                    **kwargs,
                    status=CheckStatus.PASS,
                    summary=f"systemd unit syntax OK: {unit_files[0].name}",
                )
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"systemd syntax issues in {unit_files[0].name}",
                details={"stderr": result.stderr[:300]},
                remediation=["Fix systemd unit syntax."],
            )
        except FileNotFoundError:
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="systemd-analyze not available"
            )
        except subprocess.TimeoutExpired:
            return _make_result(
                **kwargs, status=CheckStatus.WARN, summary="systemd-analyze timed out"
            )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_process_version(**kwargs: Any) -> CheckResult:
    try:
        import os

        if os.path.exists("/.dockerenv"):
            return _make_result(
                **kwargs,
                status=CheckStatus.SKIP,
                summary="Version check skipped (Docker container)",
            )
        try:
            import subprocess

            result = subprocess.run(
                ["systemctl", "show", "devlog", "--property=Environment", "--value"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return _make_result(
                    **kwargs,
                    status=CheckStatus.PASS,
                    summary="systemd service environment available",
                    details={"env_output": result.stdout.strip()[:200]},
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return _make_result(
            **kwargs, status=CheckStatus.SKIP, summary="Process version not determinable"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_image_match(**kwargs: Any) -> CheckResult:
    try:
        from importlib.metadata import version as pkg_version

        ver = pkg_version("devlog")
        if not ver:
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="Cannot determine package version"
            )
        try:
            from app.filesystem.layout import InstallationMetadata

            paths = _ctx_paths()
            if paths is None:
                return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
            meta = InstallationMetadata.load(paths.installation_metadata.path)
            if meta is None:
                return _make_result(
                    **kwargs, status=CheckStatus.SKIP, summary="No installation metadata"
                )
            if meta.version and meta.version != ver:
                return _make_result(
                    **kwargs,
                    status=CheckStatus.WARN,
                    summary=f"Installed version ({ver}) differs from metadata ({meta.version})",
                    details={"installed": ver, "metadata_version": meta.version},
                )
            return _make_result(
                **kwargs,
                status=CheckStatus.PASS,
                summary=f"Version matches metadata: {ver}",
                details={"version": ver},
            )
        except Exception:
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="Cannot compare with deployment metadata"
            )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


# ---------------------------------------------------------------------------
# H9 — Backup readiness checks
# ---------------------------------------------------------------------------


def _check_backup_directory(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.ERROR, summary="Cannot resolve paths")
        backup_dir = paths.backups_dir.path
        if not backup_dir.exists():
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary="Backup directory does not exist",
                safe_fix_id="create_missing_dirs",
                remediation=["Create the backup directory."],
            )
        writable = os.access(backup_dir, os.W_OK)
        if not writable:
            return _make_result(
                **kwargs,
                status=CheckStatus.FAIL,
                summary="Backup directory is not writable",
                remediation=["Fix directory permissions."],
            )
        backups = sorted(backup_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if backups:
            age_hours = (time.time() - backups[0].stat().st_mtime) / 3600
            return _make_result(
                **kwargs,
                status=CheckStatus.PASS,
                summary=f"Backup directory OK, latest backup {age_hours:.1f}h ago",
                details={"latest_age_hours": round(age_hours, 1), "backup_count": len(backups)},
            )
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary="Backup directory exists but is empty",
            remediation=["Run `devlog backup create` to generate a backup."],
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_backup_manifest(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        backup_dir = paths.backups_dir.path
        if not backup_dir.exists():
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="Backup directory does not exist"
            )
        manifest_files = list(backup_dir.glob("*.manifest.json"))
        if not manifest_files:
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="No backup manifest files found"
            )
        import json

        latest = sorted(manifest_files, key=lambda p: p.stat().st_mtime, reverse=True)[0]
        try:
            data = json.loads(latest.read_text())
            return _make_result(
                **kwargs,
                status=CheckStatus.PASS,
                summary=f"Latest backup manifest parseable: {latest.name}",
                details={"manifest_file": latest.name, "keys": list(data.keys())[:5]},
            )
        except Exception:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"Backup manifest is not parseable: {latest.name}",
                remediation=["Check backup integrity."],
            )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_backup_encryption(**kwargs: Any) -> CheckResult:
    try:
        cfg = _ctx_config()
        if cfg is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
        encryption_key = getattr(cfg.backup, "encryption_key", "")
        if not encryption_key:
            return _make_result(
                **kwargs,
                status=CheckStatus.PASS,
                summary="Backup encryption not configured (no key)",
            )
        try:
            import cryptography  # noqa: F401

            return _make_result(
                **kwargs,
                status=CheckStatus.PASS,
                summary="Backup encryption enabled, cryptography available",
            )
        except ImportError:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary="Backup encryption configured but cryptography library not available",
                remediation=["Install cryptography: pip install cryptography"],
            )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_backup_retention(**kwargs: Any) -> CheckResult:
    try:
        keep_str = os.environ.get("BACKUP_KEEP", "7")
        try:
            keep = int(keep_str)
        except ValueError:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"BACKUP_KEEP is not a valid integer: {keep_str}",
                remediation=["Set BACKUP_KEEP to a positive integer."],
            )
        if keep < 1:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"Backup retention set to {keep} — no backups will be kept",
                remediation=["Set BACKUP_KEEP to a positive integer."],
            )
        if keep > 100:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"Backup retention set to {keep} — very high, may consume significant disk",
                remediation=["Consider reducing BACKUP_KEEP."],
            )
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary=f"Backup retention: keep {keep} backups"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_backup_verification(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        backup_dir = paths.backups_dir.path
        if not backup_dir.exists():
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="Backup directory does not exist"
            )
        all_backups = [p for p in backup_dir.iterdir() if p.is_dir()]
        if not all_backups:
            return _make_result(
                **kwargs, status=CheckStatus.SKIP, summary="No backup directories found"
            )
        verified = [p for p in all_backups if (p / ".verified").exists()]
        return _make_result(
            **kwargs,
            status=CheckStatus.PASS,
            summary=f"Backup verification: {len(verified)}/{len(all_backups)} verified",
            details={"total": len(all_backups), "verified": len(verified)},
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_backup_path_nesting(**kwargs: Any) -> CheckResult:
    try:
        paths = _ctx_paths()
        if paths is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        backup_dir = paths.backups_dir.path.resolve()
        source_dirs = []
        for name in ("data_dir", "uploads_dir"):
            rp = getattr(paths, name)
            source_dirs.append((name, rp.path.resolve()))
        nesting = []
        for name, src in source_dirs:
            try:
                backup_dir.relative_to(src)
                nesting.append(
                    {"backup_dir": str(backup_dir), "nested_inside": name, "source": str(src)}
                )
            except ValueError:
                continue
        if nesting:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary="Backup directory is nested inside a source directory — recursion risk",
                details={"nesting": nesting},
                remediation=["Move the backup directory outside source paths."],
            )
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary="Backup path not nested inside source paths"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


# ---------------------------------------------------------------------------
# H10 — Security checks
# ---------------------------------------------------------------------------


def _check_session_security(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
    binding = cfg.app.session_ip_binding
    return _make_result(
        **kwargs,
        status=CheckStatus.PASS,
        summary=f"Session IP binding: {binding}",
        details={"session_ip_binding": binding},
    )


def _check_production_secrets(**kwargs: Any) -> CheckResult:
    try:
        from app.config.validation import validate_security

        cfg = _ctx_config()
        if cfg is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
        findings = validate_security(cfg)
        errors = [f for f in findings if f.severity.value == "error"]
        warnings = [f for f in findings if f.severity.value == "warning"]
        if errors:
            return _make_result(
                **kwargs,
                status=CheckStatus.FAIL,
                summary=f"{len(errors)} security error(s)",
                details={"errors": [{"code": f.code, "message": f.message} for f in errors[:5]]},
                remediation=[f.message for f in errors[:3] if f.message],
            )
        if warnings:
            return _make_result(
                **kwargs,
                status=CheckStatus.WARN,
                summary=f"{len(warnings)} security warning(s)",
                details={
                    "warnings": [{"code": f.code, "message": f.message} for f in warnings[:5]]
                },
            )
        return _make_result(**kwargs, status=CheckStatus.PASS, summary="Security validation passed")
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


def _check_cookie_security(**kwargs: Any) -> CheckResult:
    cfg = _ctx_config()
    if cfg is None:
        return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Config unavailable")
    secure = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true"
    if not secure:
        return _make_result(
            **kwargs,
            status=CheckStatus.WARN,
            summary="SESSION_COOKIE_SECURE is false — cookies sent over HTTP",
            remediation=["Set SESSION_COOKIE_SECURE=true for production."],
        )
    return _make_result(
        **kwargs, status=CheckStatus.PASS, summary="Session cookie security enabled"
    )


def _check_scheduler_owner(**kwargs: Any) -> CheckResult:
    try:
        import os

        runtime_dir = _ctx_paths()
        if runtime_dir is None:
            return _make_result(**kwargs, status=CheckStatus.SKIP, summary="Paths unavailable")
        lock_file = runtime_dir.runtime_dir.path / "scheduler.lock"
        if not lock_file.exists():
            return _make_result(
                **kwargs,
                status=CheckStatus.PASS,
                summary="No scheduler lock file (single owner assumed)",
            )
        try:
            import json

            lock_data = json.loads(lock_file.read_text())
            pid = lock_data.get("pid") if isinstance(lock_data, dict) else None
            if pid:
                try:
                    os.kill(int(pid), 0)
                    hostname = lock_data.get("hostname", "unknown")
                    return _make_result(
                        **kwargs,
                        status=CheckStatus.PASS,
                        summary=f"Scheduler owned by PID {pid} on {hostname}",
                        details={"pid": pid, "hostname": hostname},
                    )
                except OSError:
                    return _make_result(
                        **kwargs,
                        status=CheckStatus.WARN,
                        summary=f"Scheduler lock references dead PID {pid}",
                        remediation=["Remove stale lock file."],
                    )
        except (json.JSONDecodeError, ValueError):
            pass
        return _make_result(
            **kwargs, status=CheckStatus.PASS, summary="Scheduler lock file present"
        )
    except Exception as e:
        return _error_result(kwargs["check_id"], kwargs["category"], kwargs["severity"], e)


# ---------------------------------------------------------------------------
# Register all checks
# ---------------------------------------------------------------------------


def _register_all_checks() -> None:
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
        (
            CheckDefinition(
                "install.release_symlink",
                CheckCategory.INSTALLATION,
                "Release symlink correctness",
                Severity.RECOMMENDED,
                timeout_seconds=5,
                remediation=["Run `devlog deploy install`."],
            ),
            _check_release_symlink,
        ),
        (
            CheckDefinition(
                "install.config_path",
                CheckCategory.INSTALLATION,
                "Config path and env-file selection",
                Severity.RECOMMENDED,
                timeout_seconds=5,
                remediation=["Create config.toml or run `devlog config init`."],
            ),
            _check_config_path,
        ),
        (
            CheckDefinition(
                "install.deprecated_keys",
                CheckCategory.CONFIGURATION,
                "Unknown/deprecated config keys",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Remove unknown keys from config.toml."],
            ),
            _check_deprecated_keys,
        ),
        (
            CheckDefinition(
                "install.secret_permissions",
                CheckCategory.SECRETS,
                "Secret file permissions",
                Severity.RECOMMENDED,
                timeout_seconds=5,
                remediation=["Run: chmod 600 .env"],
            ),
            _check_secret_permissions,
        ),
        (
            CheckDefinition(
                "install.stale_metadata",
                CheckCategory.INSTALLATION,
                "Stale installation metadata",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Re-run `devlog onboard`."],
            ),
            _check_stale_metadata,
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
        (
            CheckDefinition(
                "fs.service_account",
                CheckCategory.FILESYSTEM,
                "Service account exists",
                Severity.RECOMMENDED,
                timeout_seconds=5,
                remediation=[
                    "useradd --system --home-dir /var/lib/devlog --shell /usr/sbin/nologin devlog",
                    "chown -R devlog:devlog /var/lib/devlog /var/log/devlog",
                ],
            ),
            _check_service_account,
        ),
        (
            CheckDefinition(
                "fs.ownership",
                CheckCategory.FILESYSTEM,
                "Directory ownership",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_dir_ownership,
        ),
        (
            CheckDefinition(
                "fs.writable",
                CheckCategory.FILESYSTEM,
                "Runtime directories writable",
                Severity.RECOMMENDED,
                timeout_seconds=5,
                remediation=["Fix directory permissions."],
            ),
            _check_dir_writable,
        ),
        (
            CheckDefinition(
                "fs.inodes",
                CheckCategory.CAPACITY,
                "Inode availability",
                Severity.RECOMMENDED,
                production_required=True,
                timeout_seconds=5,
                remediation=["Free inodes or expand the volume."],
            ),
            _check_inodes,
        ),
        (
            CheckDefinition(
                "fs.type",
                CheckCategory.FILESYSTEM,
                "Filesystem type compatibility",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Use a POSIX-compatible filesystem for SQLite."],
            ),
            _check_fs_type,
        ),
        (
            CheckDefinition(
                "fs.docker_uid",
                CheckCategory.FILESYSTEM,
                "Docker UID/GID mapping",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Ensure container UID matches host volume ownership."],
            ),
            _check_docker_uid,
        ),
        (
            CheckDefinition(
                "fs.stale_files",
                CheckCategory.FILESYSTEM,
                "Stale runtime files",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Remove stale files from the runtime directory."],
            ),
            _check_stale_files,
        ),
        (
            CheckDefinition(
                "fs.legacy_remnants",
                CheckCategory.FILESYSTEM,
                "Legacy checkout remnants",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Review and remove legacy files."],
            ),
            _check_legacy_remnants,
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
                deep=True,
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
        (
            CheckDefinition(
                "db.wal_checkpoint",
                CheckCategory.DATABASE,
                "WAL checkpoint status",
                Severity.OPTIONAL,
                timeout_seconds=10,
                deep=True,
            ),
            _check_wal_checkpoint,
        ),
        (
            CheckDefinition(
                "db.ownership",
                CheckCategory.DATABASE,
                "Database file ownership",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_db_ownership,
        ),
        (
            CheckDefinition(
                "db.fts_health",
                CheckCategory.SEARCH,
                "FTS schema and index health",
                Severity.RECOMMENDED,
                timeout_seconds=10,
                remediation=["Run `devlog db rebuild-search`."],
            ),
            _check_fts_health,
        ),
        (
            CheckDefinition(
                "db.orphaned_migration",
                CheckCategory.DATABASE,
                "Orphaned migration state",
                Severity.RECOMMENDED,
                timeout_seconds=5,
                remediation=["Run `flask db upgrade`."],
            ),
            _check_migration_orphaned,
        ),
        (
            CheckDefinition(
                "db.backend_features",
                CheckCategory.DATABASE,
                "Backend feature compatibility",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_backend_features,
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
                "assets.referenced",
                CheckCategory.ASSETS,
                "Referenced static assets exist",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Rebuild frontend assets."],
            ),
            _check_referenced_assets,
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
        (
            CheckDefinition(
                "themes.accessibility",
                CheckCategory.THEMES,
                "Theme accessibility policy",
                Severity.OPTIONAL,
                timeout_seconds=10,
            ),
            _check_theme_accessibility,
        ),
        (
            CheckDefinition(
                "themes.attribution",
                CheckCategory.THEMES,
                "Theme packaging metadata",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_theme_attribution,
        ),
        (
            CheckDefinition(
                "assets.upload_serving",
                CheckCategory.ASSETS,
                "Upload and static serving assumptions",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_upload_serving,
        ),
        (
            CheckDefinition(
                "themes.external_dir",
                CheckCategory.THEMES,
                "External theme directory validity",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_external_theme_dir,
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
                "dep.redis_auth",
                CheckCategory.REDIS,
                "Redis authentication",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Check Redis password configuration."],
            ),
            _check_redis_auth,
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
                "dep.celery_workers",
                CheckCategory.CELERY,
                "Celery broker accessible",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_celery_workers,
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
            _check_scheduler_running,
        ),
        (
            CheckDefinition(
                "dep.scheduler_stale",
                CheckCategory.SCHEDULER,
                "Scheduler lock staleness",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_scheduler_stale,
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
                "dep.smtp_connect",
                CheckCategory.EMAIL,
                "SMTP reachable",
                Severity.OPTIONAL,
                timeout_seconds=8,
                remediation=["Check SMTP host and port."],
            ),
            _check_smtp_connect,
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
        (
            CheckDefinition(
                "dep.storage_writable",
                CheckCategory.STORAGE,
                "Storage writable",
                Severity.RECOMMENDED,
                timeout_seconds=5,
                remediation=["Fix directory permissions."],
            ),
            _check_storage_writable,
        ),
        (
            CheckDefinition(
                "dep.redis_db",
                CheckCategory.REDIS,
                "Redis selected database",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_redis_db,
        ),
        (
            CheckDefinition(
                "dep.celery_routing",
                CheckCategory.CELERY,
                "Celery queue routing consistency",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_celery_routing,
        ),
        (
            CheckDefinition(
                "dep.celery_version",
                CheckCategory.CELERY,
                "Celery version compatibility",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_celery_version,
        ),
        (
            CheckDefinition(
                "dep.scheduler_runs",
                CheckCategory.SCHEDULER,
                "Scheduler next/last run status",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_scheduler_runs,
        ),
        (
            CheckDefinition(
                "dep.scheduler_owner",
                CheckCategory.SCHEDULER,
                "Scheduler single-owner verification",
                Severity.RECOMMENDED,
                timeout_seconds=5,
                remediation=["Ensure only one scheduler instance runs."],
            ),
            _check_scheduler_owner,
        ),
        (
            CheckDefinition(
                "dep.storage_s3_probe",
                CheckCategory.STORAGE,
                "S3 non-destructive probe",
                Severity.RECOMMENDED,
                timeout_seconds=8,
            ),
            _check_storage_s3_probe,
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
        (
            CheckDefinition(
                "deploy.drift",
                CheckCategory.DEPLOYMENT,
                "Deployment drift check",
                Severity.RECOMMENDED,
                timeout_seconds=10,
                remediation=["Reinstall deployment files with `devlog deploy install`."],
            ),
            _check_deploy_drift,
        ),
        (
            CheckDefinition(
                "deploy.service_state",
                CheckCategory.SERVICE,
                "Service enabled and running",
                Severity.RECOMMENDED,
                production_required=True,
                timeout_seconds=10,
                remediation=["Start the service."],
            ),
            _check_service_state,
        ),
        (
            CheckDefinition(
                "deploy.files",
                CheckCategory.DEPLOYMENT,
                "Managed deployment files present",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Run `devlog deploy install`."],
            ),
            _check_deploy_files,
        ),
        (
            CheckDefinition(
                "deploy.health_endpoint",
                CheckCategory.HEALTH,
                "Health endpoint reachable",
                Severity.RECOMMENDED,
                production_required=True,
                timeout_seconds=8,
                remediation=["Ensure the application is running."],
            ),
            _check_health_endpoint,
        ),
        (
            CheckDefinition(
                "deploy.proxy",
                CheckCategory.PROXY,
                "Reverse proxy configuration",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Set PROXY_COUNT if behind a reverse proxy."],
            ),
            _check_proxy_config,
        ),
        (
            CheckDefinition(
                "deploy.bind",
                CheckCategory.DEPLOYMENT,
                "Bind address safety",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Bind to 127.0.0.1 if not behind a reverse proxy."],
            ),
            _check_bind_address,
        ),
        (
            CheckDefinition(
                "deploy.pid",
                CheckCategory.DEPLOYMENT,
                "Stale PID files",
                Severity.OPTIONAL,
                timeout_seconds=5,
                safe_fix_id="cleanup_stale_pid",
                remediation=["Remove stale PID files."],
            ),
            _check_stale_pid,
        ),
        (
            CheckDefinition(
                "deploy.restart_loop",
                CheckCategory.SERVICE,
                "Restart loop detection",
                Severity.OPTIONAL,
                timeout_seconds=10,
                remediation=["Check service logs for failure details."],
            ),
            _check_restart_loop,
        ),
        (
            CheckDefinition(
                "deploy.systemd_syntax",
                CheckCategory.DEPLOYMENT,
                "systemd/Compose syntax validity",
                Severity.OPTIONAL,
                timeout_seconds=10,
            ),
            _check_systemd_syntax,
        ),
        (
            CheckDefinition(
                "deploy.process_version",
                CheckCategory.DEPLOYMENT,
                "Process/container version match",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_process_version,
        ),
        (
            CheckDefinition(
                "deploy.image_match",
                CheckCategory.DEPLOYMENT,
                "Executable/image matches installed metadata",
                Severity.OPTIONAL,
                timeout_seconds=5,
            ),
            _check_image_match,
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
        (
            CheckDefinition(
                "backup.manifest",
                CheckCategory.BACKUP,
                "Backup manifest parseable",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Check backup integrity."],
            ),
            _check_backup_manifest,
        ),
        (
            CheckDefinition(
                "backup.encryption",
                CheckCategory.BACKUP,
                "Backup encryption dependency",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Install cryptography: pip install cryptography"],
            ),
            _check_backup_encryption,
        ),
        (
            CheckDefinition(
                "backup.retention",
                CheckCategory.BACKUP,
                "Backup retention policy",
                Severity.OPTIONAL,
                timeout_seconds=5,
                remediation=["Set BACKUP_KEEP to a positive integer."],
            ),
            _check_backup_retention,
        ),
        (
            CheckDefinition(
                "backup.verification",
                CheckCategory.BACKUP,
                "Backup verification state",
                Severity.RECOMMENDED,
                timeout_seconds=5,
            ),
            _check_backup_verification,
        ),
        (
            CheckDefinition(
                "backup.path_nesting",
                CheckCategory.BACKUP,
                "Backup path nesting risk",
                Severity.RECOMMENDED,
                timeout_seconds=5,
            ),
            _check_backup_path_nesting,
        ),
        # Security
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
        (
            CheckDefinition(
                "security.secrets",
                CheckCategory.SECURITY,
                "Secret validation",
                Severity.RECOMMENDED,
                production_required=True,
                timeout_seconds=5,
            ),
            _check_production_secrets,
        ),
        (
            CheckDefinition(
                "security.cookie",
                CheckCategory.SECURITY,
                "Cookie security",
                Severity.RECOMMENDED,
                timeout_seconds=5,
                remediation=["Set SESSION_COOKIE_SECURE=true for production."],
            ),
            _check_cookie_security,
        ),
    ]
    for defn, runner in checks:
        register_check(defn, runner)


# ---------------------------------------------------------------------------
# Safe fix implementations
# ---------------------------------------------------------------------------


def _fix_create_missing_dirs(cr: CheckResult) -> tuple[bool, str]:
    try:
        paths = _ctx_paths()
        if paths is None:
            return False, "Cannot resolve paths"
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


def _fix_cleanup_stale_pid(cr: CheckResult) -> tuple[bool, str]:
    try:
        paths = _ctx_paths()
        if paths is None:
            return False, "Cannot resolve paths"
        runtime_dir = paths.runtime_dir.path
        if not runtime_dir.exists():
            return False, "Runtime directory does not exist"
        removed = []
        for pf in runtime_dir.glob("*.pid"):
            try:
                pid = int(pf.read_text().strip())
                try:
                    os.kill(pid, 0)
                    continue
                except OSError:
                    pf.unlink()
                    removed.append(pf.name)
            except (ValueError, OSError):
                pass
        return (
            True,
            f"Removed {len(removed)} stale PID file(s)" if removed else "No stale PID files found",
        )
    except Exception as e:
        return False, f"Failed to clean up PID files: {e}"


def _fix_rebuild_fts(cr: CheckResult) -> tuple[bool, str]:
    try:
        from app.services.operations.database import rebuild_search_index

        result = rebuild_search_index()
        return (
            True,
            f"FTS index rebuilt: {result.indexed_count} posts indexed"
            if result.ok
            else f"FTS rebuild failed: {result.summary}",
        )
    except Exception as e:
        return False, f"Failed to rebuild FTS: {e}"


def _fix_correct_permissions(cr: CheckResult) -> tuple[bool, str]:
    try:
        paths = _ctx_paths()
        if paths is None:
            return False, "Cannot resolve paths"
        env_path = paths.env_file.path
        if not env_path.exists():
            return False, ".env file not found"
        env_path.chmod(0o600)
        return True, f"Set permissions to 600 on {env_path}"
    except Exception as e:
        return False, f"Failed to correct permissions: {e}"


def _register_safe_fixes() -> None:
    register_safe_fix(
        "create_missing_dirs", "Create missing runtime directories", "fs.required_dirs"
    )
    register_safe_fix_runner("create_missing_dirs", _fix_create_missing_dirs)
    register_safe_fix("cleanup_stale_pid", "Remove stale PID files", "deploy.pid")
    register_safe_fix_runner("cleanup_stale_pid", _fix_cleanup_stale_pid)
    register_safe_fix("rebuild_fts", "Rebuild FTS search index", "db.fts5")
    register_safe_fix_runner("rebuild_fts", _fix_rebuild_fts)
    register_safe_fix(
        "correct_permissions", "Correct .env file permissions", "install.secret_permissions"
    )
    register_safe_fix_runner("correct_permissions", _fix_correct_permissions)


# Initialize on import
_register_all_checks()
_register_safe_fixes()
