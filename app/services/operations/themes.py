"""Theme operational facade — CLI-facing service functions for theme management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.operations.results import (
    AccessibilityReportResult,
    ThemeInspectResult,
    ThemeListResult,
    ThemePathsResult,
    ThemeRefreshResult,
    ThemeValidationResult,
)


def _get_theme_service():
    from app.themes.service import get_theme_service

    return get_theme_service()


def _descriptor_to_dict(d: Any, *, verbose: bool = False) -> dict[str, Any]:
    from app.config import THEME_EXTERNAL_DIR

    row: dict[str, Any] = {
        "canonical_name": d.canonical_name,
        "display_name": d.display_name,
        "source": d.source.value,
        "overrides_bundled": d.overrides_bundled,
        "is_dark": d.is_dark,
        "status": d.status,
    }
    if d.source.value == "bundled":
        row["path"] = f"app/themes/bundled/{d.canonical_name}.toml"
    elif THEME_EXTERNAL_DIR:
        row["path"] = f"{THEME_EXTERNAL_DIR}/{d.canonical_name}.toml"
    else:
        row["path"] = ""
    if d.warnings:
        row["warnings"] = list(d.warnings)
    return row


def list_theme_descriptors(*, source: str = "all") -> ThemeListResult:
    """List themes filtered by source (all/bundled/external)."""
    service = _get_theme_service()
    registry = service.get_registry()
    all_themes = registry.list_themes()

    if source == "bundled":
        all_themes = [t for t in all_themes if t.source.value == "bundled"]
    elif source == "external":
        all_themes = [t for t in all_themes if t.source.value == "external"]

    rows = [_descriptor_to_dict(t) for t in all_themes]
    return ThemeListResult(
        ok=True,
        code="themes.list",
        summary=f"Found {len(rows)} theme(s).",
        themes=rows,
        total=len(rows),
        details={"source_filter": source},
    )


def validate_theme(path_or_name: str) -> ThemeValidationResult:
    """Validate a theme file on disk or a registered theme name."""
    file_path = Path(path_or_name)
    is_file = file_path.is_file()

    if is_file:
        return _validate_theme_file(file_path)
    else:
        return _validate_theme_name(path_or_name)


def _validate_theme_file(file_path: Path) -> ThemeValidationResult:
    from app.themes.halloy import parse_halloy_theme, ThemeParseError, ThemeSchemaError
    from app.themes.translate import translate_halloy_theme
    from app.themes.resources import _MAX_EXTERNAL_FILE_SIZE
    from app.themes.diagnostics import check_blog_theme_contrast

    if not file_path.exists():
        return ThemeValidationResult(
            ok=False,
            code="themes.validate.not_found",
            summary=f"File not found: {file_path}",
            valid=False,
            theme_name=file_path.stem,
            remediation=["Check the file path and try again."],
        )

    if not file_path.is_file():
        return ThemeValidationResult(
            ok=False,
            code="themes.validate.not_a_file",
            summary=f"Not a regular file: {file_path}",
            valid=False,
            theme_name=file_path.stem,
        )

    try:
        size = file_path.stat().st_size
    except OSError as e:
        return ThemeValidationResult(
            ok=False,
            code="themes.validate.stat_error",
            summary=f"Cannot stat file: {e}",
            valid=False,
            theme_name=file_path.stem,
        )

    if size > _MAX_EXTERNAL_FILE_SIZE:
        return ThemeValidationResult(
            ok=False,
            code="themes.validate.too_large",
            summary=f"File too large: {size} bytes (max {_MAX_EXTERNAL_FILE_SIZE})",
            valid=False,
            theme_name=file_path.stem,
        )

    if size == 0:
        return ThemeValidationResult(
            ok=False,
            code="themes.validate.empty",
            summary="File is empty",
            valid=False,
            theme_name=file_path.stem,
        )

    try:
        data = file_path.read_bytes()
    except OSError as e:
        return ThemeValidationResult(
            ok=False,
            code="themes.validate.read_error",
            summary=f"Cannot read file: {e}",
            valid=False,
            theme_name=file_path.stem,
        )

    try:
        halloy_theme = parse_halloy_theme(data)
    except (ThemeParseError, ThemeSchemaError) as e:
        return ThemeValidationResult(
            ok=False,
            code="themes.validate.parse_error",
            summary=f"Parse error: {e}",
            valid=False,
            theme_name=file_path.stem,
            warnings=[str(e)],
        )

    try:
        translation = translate_halloy_theme(halloy_theme)
    except Exception as e:
        return ThemeValidationResult(
            ok=False,
            code="themes.validate.translation_error",
            summary=f"Translation error: {e}",
            valid=False,
            theme_name=file_path.stem,
            warnings=[str(e)],
        )

    warnings: list[str] = []
    contrast_warnings = check_blog_theme_contrast(translation.theme)
    if contrast_warnings:
        warnings.extend(f"{w.description} ({w.ratio}:1)" for w in contrast_warnings)

    return ThemeValidationResult(
        ok=True,
        code="themes.validate.ok",
        summary=f"Theme file is valid: {file_path}",
        valid=True,
        theme_name=file_path.stem,
        details={
            "normalized_name": file_path.stem,
            "schema_version": halloy_theme.schema_version,
            "is_dark": translation.is_dark,
            "token_count": len(translation.theme.__dataclass_fields__),
        },
        warnings=warnings,
    )


def _validate_theme_name(name: str) -> ThemeValidationResult:
    from app.themes.registry import (
        ThemeNotFoundError,
        ThemeParseFailure,
        ThemeLoadError,
        ThemeValidationError,
    )

    service = _get_theme_service()
    registry = service.get_registry()

    try:
        loaded = registry.load(name)
    except ThemeNotFoundError:
        return ThemeValidationResult(
            ok=False,
            code="themes.validate.not_found",
            summary=f"Theme '{name}' not found.",
            valid=False,
            theme_name=name,
            remediation=["Check available themes with `devlog themes list`."],
        )
    except ThemeParseFailure as e:
        return ThemeValidationResult(
            ok=False,
            code="themes.validate.parse_failure",
            summary=f"Theme '{name}' failed to parse: {e}",
            valid=False,
            theme_name=name,
        )
    except ThemeLoadError as e:
        return ThemeValidationResult(
            ok=False,
            code="themes.validate.load_error",
            summary=f"Theme '{name}' failed to load: {e}",
            valid=False,
            theme_name=name,
        )
    except ThemeValidationError as e:
        return ThemeValidationResult(
            ok=False,
            code="themes.validate.invalid_name",
            summary=f"Invalid theme name: {e}",
            valid=False,
            theme_name=name,
        )

    warnings: list[str] = []
    if loaded.descriptor.warnings:
        warnings.extend(loaded.descriptor.warnings)

    return ThemeValidationResult(
        ok=True,
        code="themes.validate.ok",
        summary=f"Theme '{name}' is valid.",
        valid=True,
        theme_name=loaded.descriptor.canonical_name,
        details={
            "canonical_name": loaded.descriptor.canonical_name,
            "source": loaded.descriptor.source.value,
            "is_dark": loaded.is_dark,
        },
        warnings=warnings,
    )


def inspect_theme(name: str) -> ThemeInspectResult:
    """Full theme details including CSS vars and accessibility."""
    from app.themes.registry import ThemeNotFoundError
    from app.themes.diagnostics import validate_theme_accessibility

    service = _get_theme_service()
    registry = service.get_registry()

    try:
        loaded = registry.load(name)
    except ThemeNotFoundError:
        return ThemeInspectResult(
            ok=False,
            code="themes.inspect.not_found",
            summary=f"Theme '{name}' not found.",
            theme_name=name,
            remediation=["Check available themes with `devlog themes list`."],
        )

    filename_dark = None
    if loaded.descriptor.is_dark is not None:
        filename_dark = loaded.descriptor.is_dark
    acc_report = validate_theme_accessibility(
        loaded.blog_theme,
        theme_name=loaded.descriptor.canonical_name,
        filename_dark=filename_dark,
    )

    from app.config import THEME_EXTERNAL_DIR

    if loaded.descriptor.source.value == "bundled":
        file_path = f"app/themes/bundled/{loaded.descriptor.canonical_name}.toml"
        source_detail = "app/themes/bundled/"
    elif THEME_EXTERNAL_DIR:
        file_path = f"{THEME_EXTERNAL_DIR}/{loaded.descriptor.canonical_name}.toml"
        source_detail = f"{THEME_EXTERNAL_DIR}/"
    else:
        file_path = ""
        source_detail = ""

    details: dict[str, Any] = {
        "canonical_name": loaded.descriptor.canonical_name,
        "display_name": loaded.descriptor.display_name,
        "source": loaded.descriptor.source.value,
        "is_dark": loaded.is_dark,
        "status": loaded.descriptor.status,
        "overrides_bundled": loaded.descriptor.overrides_bundled,
        "css": loaded.css,
        "file_path": file_path,
        "source_detail": source_detail,
        "accessibility": {
            "passed": acc_report.passed,
            "mandatory_failures": len(acc_report.mandatory_failures),
            "advisory_warnings": len(acc_report.advisory_warnings),
            "findings": [f.to_dict() for f in acc_report.findings],
        },
    }
    if acc_report.classification:
        details["classification"] = {
            "filename_dark": acc_report.classification.filename_dark,
            "computed_dark": acc_report.classification.computed_dark,
            "page_luminance": acc_report.classification.page_luminance,
            "mismatch": acc_report.classification.mismatch,
        }

    warnings: list[str] = []
    if loaded.descriptor.warnings:
        warnings.extend(loaded.descriptor.warnings)
    if loaded.diagnostics.warnings:
        warnings.extend(
            f"{w.token}: {w.description} ({w.ratio}:1)" for w in loaded.diagnostics.warnings
        )

    return ThemeInspectResult(
        ok=True,
        code="themes.inspect.ok",
        summary=f"Theme '{loaded.descriptor.display_name}' ({loaded.descriptor.source.value}).",
        theme_name=loaded.descriptor.canonical_name,
        css_vars=loaded.css_vars,
        details=details,
        warnings=warnings,
    )


def refresh_theme_registry() -> ThemeRefreshResult:
    """Invalidate cache, rebuild catalog, report changes."""
    service = _get_theme_service()
    registry = service.get_registry()

    old_themes = {t.canonical_name for t in registry.list_themes()}
    old_count = len(old_themes)

    service.refresh_registry()

    new_registry = service.get_registry()
    new_themes = {t.canonical_name for t in new_registry.list_themes()}
    new_count = len(new_themes)

    added = sorted(new_themes - old_themes)
    removed = sorted(old_themes - new_themes)

    return ThemeRefreshResult(
        ok=True,
        code="themes.refresh.ok",
        summary=f"Theme registry refreshed: {old_count} -> {new_count} themes.",
        old_count=old_count,
        new_count=new_count,
        added=added,
        removed=removed,
        details={
            "old_count": old_count,
            "new_count": new_count,
            "added": added,
            "removed": removed,
        },
    )


def get_theme_paths() -> ThemePathsResult:
    """Show bundled/external paths and configuration."""
    import os
    from pathlib import Path as P

    from app.config import THEME_EXTERNAL_DIR, THEME_ALLOW_EXTERNAL, THEME_STRICT_VALIDATION

    bundled_dir = P(__file__).resolve().parent.parent.parent / "themes" / "bundled"
    bundled_exists = bundled_dir.is_dir()

    bundled_info: dict[str, Any] = {}
    manifest_path = bundled_dir / "catalog_manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            bundled_info = {
                "package_name": manifest.get("name", "devlog-themes"),
                "package_version": manifest.get("version", "unknown"),
                "theme_count": manifest.get("theme_count", "?"),
            }
        except (OSError, ValueError):
            bundled_info = {"error": "manifest unreadable"}
    if bundled_exists:
        bundled_info["toml_count"] = len(list(bundled_dir.glob("*.toml")))
    else:
        bundled_info["error"] = "directory not found"

    external_info: dict[str, Any] = {}
    if THEME_EXTERNAL_DIR:
        ext_path = P(THEME_EXTERNAL_DIR)
        external_info["configured"] = THEME_EXTERNAL_DIR
        external_info["exists"] = ext_path.is_dir()
        if ext_path.is_dir():
            external_info["readable"] = os.access(ext_path, os.R_OK | os.X_OK)
            if external_info["readable"]:
                external_info["toml_count"] = len(list(ext_path.glob("*.toml")))
        else:
            external_info["readable"] = False
    else:
        external_info["configured"] = ""
        external_info["exists"] = False
        external_info["disabled"] = True

    from app.themes.resources import _MAX_EXTERNAL_FILE_SIZE

    return ThemePathsResult(
        ok=True,
        code="themes.paths",
        summary="Theme paths displayed.",
        paths={
            "bundled": bundled_info,
            "external": external_info,
            "config": {
                "THEME_ALLOW_EXTERNAL": THEME_ALLOW_EXTERNAL,
                "THEME_STRICT_VALIDATION": THEME_STRICT_VALIDATION,
                "max_file_size": _MAX_EXTERNAL_FILE_SIZE,
            },
        },
    )


def run_accessibility_check(
    *, source: str = "all", strict: bool = False
) -> AccessibilityReportResult:
    """WCAG contrast checks with severity classification."""
    from app.themes.diagnostics import validate_theme_accessibility

    service = _get_theme_service()
    registry = service.get_registry()
    all_themes = registry.list_themes()

    if source == "bundled":
        all_themes = [t for t in all_themes if t.source.value == "bundled"]
    elif source == "external":
        all_themes = [t for t in all_themes if t.source.value == "external"]

    reports_data: list[dict[str, Any]] = []
    errors: list[str] = []

    for descriptor in all_themes:
        try:
            loaded = registry.load(descriptor.canonical_name)
            filename_dark = None
            if descriptor.is_dark is not None:
                filename_dark = descriptor.is_dark
            report = validate_theme_accessibility(
                loaded.blog_theme,
                theme_name=descriptor.canonical_name,
                filename_dark=filename_dark,
            )
            report = report.__class__(
                theme_name=report.theme_name,
                source=descriptor.source.value,
                is_dark=report.is_dark,
                findings=report.findings,
                classification=report.classification,
            )
            reports_data.append(
                {
                    "theme_name": report.theme_name,
                    "source": report.source,
                    "is_dark": report.is_dark,
                    "passed": report.passed,
                    "passed_with_exceptions": report.passed_with_exceptions,
                    "mandatory_failures": len(report.mandatory_failures),
                    "unexpected_failures": len(report.unexpected_mandatory_failures),
                    "expected_exceptions": len(report.expected_exceptions),
                    "advisory_warnings": len(report.advisory_warnings),
                    "findings": [f.to_dict() for f in report.findings],
                }
            )
        except Exception as e:
            errors.append(f"{descriptor.display_name}: {e}")

    passed_exact = sum(1 for r in reports_data if r["passed"])
    passed_with_exceptions = sum(
        1 for r in reports_data if r["passed_with_exceptions"] and not r["passed"]
    )
    failed = sum(1 for r in reports_data if not r["passed_with_exceptions"])

    total_mandatory = sum(r["mandatory_failures"] for r in reports_data)
    total_advisory = sum(r["advisory_warnings"] for r in reports_data)

    strict_rejected: list[str] = []
    if strict:
        for r in reports_data:
            if r["source"] == "external" and not r["passed_with_exceptions"]:
                strict_rejected.append(r["theme_name"])

    summary_parts = [
        f"Checked {len(reports_data)} theme(s)",
        f"passed(exact)={passed_exact}",
        f"passed(exceptions)={passed_with_exceptions}",
        f"failed={failed}",
    ]
    if strict_rejected:
        summary_parts.append(f"strict_rejected={len(strict_rejected)}")

    return AccessibilityReportResult(
        ok=not errors and not strict_rejected,
        code="themes.accessibility.ok" if not errors else "themes.accessibility.error",
        summary=" | ".join(summary_parts),
        total_themes=len(reports_data),
        passed_exact=passed_exact,
        passed_with_exceptions=passed_with_exceptions,
        failed=failed,
        reports=reports_data,
        details={
            "source_filter": source,
            "strict": strict,
            "total_mandatory_failures": total_mandatory,
            "total_advisory_warnings": total_advisory,
            "strict_rejected": strict_rejected,
            "errors": errors,
        },
        warnings=errors,
        remediation=(
            [f"Fix mandatory failures in external theme(s): {', '.join(strict_rejected)}"]
            if strict_rejected
            else []
        ),
    )
