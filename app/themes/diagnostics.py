from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from app.themes.colors import (
    RGB,
    RGBA,
    alpha_composite,
    contrast_ratio,
    is_dark_background,
    relative_luminance,
    to_hex,
    wcag_level,
)
from app.themes.model import BlogTheme

_WHITE = RGB(255, 255, 255)

_EXCEPTIONS_PATH = Path(__file__).parent / "ACCESSIBILITY_EXCEPTIONS.json"
_exception_manifest: dict | None = None


def _load_exception_manifest() -> dict:
    global _exception_manifest
    if _exception_manifest is None:
        if _EXCEPTIONS_PATH.exists():
            with open(_EXCEPTIONS_PATH) as f:
                _exception_manifest = json.load(f)
        else:
            _exception_manifest = {"exceptions": {}}
    return _exception_manifest


def is_expected_exception(theme_name: str, description: str) -> str | None:
    manifest = _load_exception_manifest()
    theme_exc = manifest.get("exceptions", {}).get(theme_name, {})
    for pair in theme_exc.get("pairs", []):
        if pair["description"] == description:
            return pair.get("reason", "Documented exception")
    return None


def _resolve_rgb(color: RGB | RGBA) -> RGB:
    if isinstance(color, RGBA):
        return alpha_composite(color, _WHITE)
    return color


class Severity(str, Enum):
    MANDATORY = "mandatory"
    ADVISORY = "advisory"


@dataclass(frozen=True, slots=True)
class ContrastWarning:
    token: str
    description: str
    foreground: str
    background: str
    ratio: float
    wcag: str


@dataclass(frozen=True, slots=True)
class AccessibilityFinding:
    theme_name: str
    token: str
    description: str
    foreground: str
    background: str
    ratio: float
    required: float
    wcag: str
    severity: Severity
    remediation: str
    exception_reason: str | None = None

    @property
    def is_expected(self) -> bool:
        return self.exception_reason is not None

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "theme_name": self.theme_name,
            "token": self.token,
            "description": self.description,
            "foreground": self.foreground,
            "background": self.background,
            "ratio": self.ratio,
            "required": self.required,
            "wcag": self.wcag,
            "severity": self.severity.value,
            "remediation": self.remediation,
        }
        if self.exception_reason:
            result["exception_reason"] = self.exception_reason
        return result


@dataclass(frozen=True, slots=True)
class ClassificationAudit:
    theme_name: str
    filename_dark: bool | None
    computed_dark: bool
    page_luminance: float
    mismatch: bool


@dataclass(frozen=True, slots=True)
class ThemeAccessibilityReport:
    theme_name: str
    source: str
    is_dark: bool
    findings: list[AccessibilityFinding] = field(default_factory=list)
    classification: ClassificationAudit | None = None

    @property
    def mandatory_failures(self) -> list[AccessibilityFinding]:
        return [f for f in self.findings if f.severity == Severity.MANDATORY]

    @property
    def unexpected_mandatory_failures(self) -> list[AccessibilityFinding]:
        return [f for f in self.mandatory_failures if not f.is_expected]

    @property
    def expected_exceptions(self) -> list[AccessibilityFinding]:
        return [f for f in self.mandatory_failures if f.is_expected]

    @property
    def advisory_warnings(self) -> list[AccessibilityFinding]:
        return [f for f in self.findings if f.severity == Severity.ADVISORY]

    @property
    def passed(self) -> bool:
        return len(self.mandatory_failures) == 0

    @property
    def passed_with_exceptions(self) -> bool:
        return len(self.unexpected_mandatory_failures) == 0

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "theme_name": self.theme_name,
            "source": self.source,
            "is_dark": self.is_dark,
            "passed": self.passed,
            "passed_with_exceptions": self.passed_with_exceptions,
            "mandatory_failures": len(self.mandatory_failures),
            "unexpected_failures": len(self.unexpected_mandatory_failures),
            "expected_exceptions": len(self.expected_exceptions),
            "advisory_warnings": len(self.advisory_warnings),
            "findings": [f.to_dict() for f in self.findings],
        }
        if self.classification:
            result["classification"] = {
                "filename_dark": self.classification.filename_dark,
                "computed_dark": self.classification.computed_dark,
                "page_luminance": round(self.classification.page_luminance, 4),
                "mismatch": self.classification.mismatch,
            }
        return result


@dataclass(frozen=True, slots=True)
class CatalogAccessibilityReport:
    reports: list[ThemeAccessibilityReport] = field(default_factory=list)

    @property
    def total_themes(self) -> int:
        return len(self.reports)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.reports if r.passed)

    @property
    def failed_count(self) -> int:
        return self.total_themes - self.passed_count

    @property
    def total_mandatory(self) -> int:
        return sum(len(r.mandatory_failures) for r in self.reports)

    @property
    def total_advisory(self) -> int:
        return sum(len(r.advisory_warnings) for r in self.reports)

    @property
    def worst_findings(self) -> list[AccessibilityFinding]:
        all_findings = []
        for r in self.reports:
            all_findings.extend(r.findings)
        return sorted(all_findings, key=lambda f: f.ratio)[:10]

    @property
    def classification_mismatches(self) -> list[ClassificationAudit]:
        return [
            r.classification for r in self.reports if r.classification and r.classification.mismatch
        ]

    def to_dict(self) -> dict[str, object]:
        return {
            "total_themes": self.total_themes,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "total_mandatory_failures": self.total_mandatory,
            "total_advisory_warnings": self.total_advisory,
            "classification_mismatches": len(self.classification_mismatches),
            "reports": [r.to_dict() for r in self.reports],
        }


@dataclass(frozen=True, slots=True)
class ProvenanceEntry:
    blog_token: str
    halloy_source: str
    derivation: str


@dataclass
class TranslationDiagnostics:
    warnings: list[ContrastWarning] = field(default_factory=list)
    provenance: list[ProvenanceEntry] = field(default_factory=list)
    is_dark: bool = True
    source_name: str = ""

    @property
    def summary(self) -> str:
        lines: list[str] = []
        if self.source_name:
            lines.append(f"Theme: {self.source_name}")
        lines.append(f"Mode: {'dark' if self.is_dark else 'light'}")
        lines.append("")

        if self.warnings:
            lines.append(f"Contrast warnings ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"  - {w.token}: {w.description} ({w.ratio:.2f}:1, WCAG {w.wcag})")
                lines.append(f"    fg={w.foreground} bg={w.background}")
        else:
            lines.append("No contrast warnings.")

        lines.append("")

        if self.provenance:
            lines.append(f"Provenance ({len(self.provenance)}):")
            for p in self.provenance:
                lines.append(f"  - {p.blog_token}: {p.halloy_source} ({p.derivation})")
        else:
            lines.append("No provenance entries.")

        return "\n".join(lines)


def check_contrast(
    fg: RGB | RGBA,
    bg: RGB | RGBA,
    token: str,
    description: str,
    min_ratio: float = 4.5,
) -> ContrastWarning | None:
    ratio = contrast_ratio(fg, bg)
    if ratio < min_ratio:
        return ContrastWarning(
            token=token,
            description=description,
            foreground=to_hex(_resolve_rgb(fg)),
            background=to_hex(_resolve_rgb(bg)),
            ratio=round(ratio, 2),
            wcag=wcag_level(ratio),
        )
    return None


def _remediation(description: str, required: float) -> str:
    return (
        f"Increase contrast for {description} to at least {required}:1. "
        f"Adjust foreground or background color values."
    )


_CONTRAST_PAIRS: list[tuple[str, str, str, float, Severity, str]] = [
    (
        "text_primary",
        "bg_page",
        "text-primary on bg-page",
        4.5,
        Severity.MANDATORY,
        "primary body text",
    ),
    (
        "text_primary",
        "surface_default",
        "text-primary on surface-default",
        4.5,
        Severity.MANDATORY,
        "primary text on cards/surfaces",
    ),
    (
        "text_primary",
        "surface_elevated",
        "text-primary on surface-elevated",
        3.0,
        Severity.ADVISORY,
        "primary text on elevated surfaces (post hero, dropdowns, code chips)",
    ),
    (
        "text_secondary",
        "surface_default",
        "text-secondary on surface-default",
        4.5,
        Severity.MANDATORY,
        "secondary text on surfaces",
    ),
    (
        "text_muted",
        "surface_default",
        "text-muted on surface-default",
        3.0,
        Severity.ADVISORY,
        "muted/secondary text",
    ),
    (
        "text_dim",
        "surface_default",
        "text-dim on surface-default",
        3.0,
        Severity.ADVISORY,
        "dim/decorative text",
    ),
    (
        "text_caption",
        "bg_page",
        "text-caption on bg-page",
        4.5,
        Severity.MANDATORY,
        "caption text on page",
    ),
    (
        "text_caption",
        "surface_default",
        "text-caption on surface-default",
        4.5,
        Severity.MANDATORY,
        "caption text on cards",
    ),
    (
        "text_caption",
        "surface_elevated",
        "text-caption on surface-elevated",
        4.5,
        Severity.MANDATORY,
        "caption text on elevated panels",
    ),
    (
        "accent_text",
        "surface_default",
        "accent-text on surface-default",
        4.5,
        Severity.MANDATORY,
        "accent text on tinted chips",
    ),
    ("text_link", "bg_page", "text-link on bg-page", 4.5, Severity.MANDATORY, "link text on page"),
    (
        "text_link",
        "surface_default",
        "text-link on surface-default",
        4.5,
        Severity.MANDATORY,
        "link text on surfaces",
    ),
    (
        "text_link_hover",
        "bg_page",
        "text-link-hover on bg-page",
        4.5,
        Severity.MANDATORY,
        "link hover state on page",
    ),
    (
        "text_on_accent",
        "accent",
        "text-on-accent on accent",
        4.5,
        Severity.MANDATORY,
        "text on accent-filled controls",
    ),
    (
        "text_on_success",
        "success_bg",
        "text-on-success on success-bg",
        4.5,
        Severity.MANDATORY,
        "text on success backgrounds",
    ),
    (
        "text_on_error",
        "error_bg",
        "text-on-error on error-bg",
        4.5,
        Severity.MANDATORY,
        "text on error backgrounds",
    ),
    (
        "text_on_warning",
        "warning_bg",
        "text-on-warning on warning-bg",
        4.5,
        Severity.MANDATORY,
        "text on warning backgrounds",
    ),
    (
        "text_on_info",
        "info_bg",
        "text-on-info on info-bg",
        4.5,
        Severity.MANDATORY,
        "text on info backgrounds",
    ),
    (
        "input_text",
        "input_bg",
        "input-text on input-bg",
        4.5,
        Severity.MANDATORY,
        "form input text",
    ),
    ("code_text", "code_bg", "code-text on code-bg", 4.5, Severity.MANDATORY, "code block text"),
    (
        "navbar_text",
        "navbar_bg",
        "navbar-text on navbar-bg",
        4.5,
        Severity.MANDATORY,
        "navigation text",
    ),
    (
        "navbar_text_muted",
        "navbar_bg",
        "navbar-text-muted on navbar-bg",
        3.0,
        Severity.ADVISORY,
        "muted navigation text",
    ),
    (
        "success_fg",
        "success_bg",
        "success-fg on success-bg",
        3.0,
        Severity.ADVISORY,
        "success indicator text",
    ),
    (
        "error_fg",
        "error_bg",
        "error-fg on error-bg",
        3.0,
        Severity.ADVISORY,
        "error indicator text",
    ),
    (
        "warning_fg",
        "warning_bg",
        "warning-fg on warning-bg",
        3.0,
        Severity.ADVISORY,
        "warning indicator text",
    ),
    (
        "info_fg",
        "info_bg",
        "info-fg on info-bg",
        3.0,
        Severity.ADVISORY,
        "info indicator text",
    ),
    (
        "accent_focus_ring",
        "bg_page",
        "accent-focus-ring on bg-page",
        3.0,
        Severity.MANDATORY,
        "focus indicator",
    ),
    (
        "accent_focus_ring",
        "surface_default",
        "accent-focus-ring on surface-default",
        3.0,
        Severity.MANDATORY,
        "focus indicator on surfaces",
    ),
    (
        "border_focus",
        "bg_page",
        "border-focus on bg-page",
        3.0,
        Severity.MANDATORY,
        "focus border indicator",
    ),
    (
        "input_border",
        "bg_page",
        "input-border on bg-page",
        3.0,
        Severity.ADVISORY,
        "decorative input border",
    ),
    (
        "input_border",
        "surface_default",
        "input-border on surface-default",
        3.0,
        Severity.ADVISORY,
        "decorative input border on surfaces",
    ),
    (
        "text_primary",
        "selection_bg",
        "text-primary on selection-bg",
        4.5,
        Severity.MANDATORY,
        "selected text readability",
    ),
    (
        "text_muted",
        "input_bg",
        "text-muted on input-bg",
        3.0,
        Severity.ADVISORY,
        "placeholder/muted text in inputs",
    ),
]


_TEXT_ON_BACKGROUND_SURFACES: list[tuple[str, str]] = [
    ("bg_page", "bg-page"),
    ("surface_default", "surface-default"),
    ("surface_elevated", "surface-elevated"),
]


def check_text_on_background_contrast(
    blog_theme: BlogTheme,
    min_ratio: float = 4.5,
) -> list[ContrastWarning]:
    """Contrast of primary body text on every surface the stylesheet paints it on."""
    warnings: list[ContrastWarning] = []
    for bg_field, bg_label in _TEXT_ON_BACKGROUND_SURFACES:
        warning = check_contrast(
            blog_theme.text_primary,
            getattr(blog_theme, bg_field),
            "--blog-text-primary",
            f"text-primary on {bg_label}",
            min_ratio,
        )
        if warning is not None:
            warnings.append(warning)
    return warnings


def check_blog_theme_contrast(blog_theme: BlogTheme) -> list[ContrastWarning]:
    checks: list[tuple[RGB | RGBA, RGB | RGBA, str, str, float]] = [
        (
            blog_theme.text_muted,
            blog_theme.surface_default,
            "--blog-text-muted",
            "text-muted on surface-default",
            3.0,
        ),
        (blog_theme.text_link, blog_theme.bg_page, "--blog-text-link", "text-link on bg-page", 4.5),
        (
            blog_theme.text_link,
            blog_theme.surface_default,
            "--blog-text-link",
            "text-link on surface-default",
            4.5,
        ),
        (
            blog_theme.text_on_accent,
            blog_theme.accent,
            "--blog-text-on-accent",
            "text-on-accent on accent",
            4.5,
        ),
        (
            blog_theme.input_text,
            blog_theme.input_bg,
            "--blog-input-text",
            "input-text on input-bg",
            4.5,
        ),
        (
            blog_theme.accent_focus_ring,
            blog_theme.bg_page,
            "--blog-accent-focus-ring",
            "accent-focus-ring on bg-page",
            3.0,
        ),
        (
            blog_theme.accent_focus_ring,
            blog_theme.surface_default,
            "--blog-accent-focus-ring",
            "accent-focus-ring on surface-default",
            3.0,
        ),
    ]

    warnings: list[ContrastWarning] = check_text_on_background_contrast(blog_theme)
    for fg, bg, token, description, min_ratio in checks:
        warning = check_contrast(fg, bg, token, description, min_ratio)
        if warning is not None:
            warnings.append(warning)
    return warnings


def validate_theme_accessibility(
    blog_theme: BlogTheme,
    theme_name: str = "",
    filename_dark: bool | None = None,
) -> ThemeAccessibilityReport:
    findings: list[AccessibilityFinding] = []

    for fg_field, bg_field, description, min_ratio, severity, remediation_hint in _CONTRAST_PAIRS:
        fg = getattr(blog_theme, fg_field)
        bg = getattr(blog_theme, bg_field)
        token = f"--blog-{fg_field.replace('_', '-')}"

        ratio = contrast_ratio(fg, bg)
        if ratio < min_ratio:
            exception_reason = (
                is_expected_exception(theme_name, description) if theme_name else None
            )
            findings.append(
                AccessibilityFinding(
                    theme_name=theme_name,
                    token=token,
                    description=description,
                    foreground=to_hex(_resolve_rgb(fg)),
                    background=to_hex(_resolve_rgb(bg)),
                    ratio=round(ratio, 2),
                    required=min_ratio,
                    wcag=wcag_level(ratio),
                    severity=severity,
                    remediation=_remediation(remediation_hint, min_ratio),
                    exception_reason=exception_reason,
                )
            )

    computed_dark = is_dark_background(blog_theme.bg_page)
    luminance = relative_luminance(blog_theme.bg_page)
    mismatch = filename_dark is not None and filename_dark != computed_dark
    classification = ClassificationAudit(
        theme_name=theme_name,
        filename_dark=filename_dark,
        computed_dark=computed_dark,
        page_luminance=round(luminance, 4),
        mismatch=mismatch,
    )

    return ThemeAccessibilityReport(
        theme_name=theme_name,
        source="",
        is_dark=computed_dark,
        findings=findings,
        classification=classification,
    )


def classify_theme_eligibility(report: ThemeAccessibilityReport) -> str:
    if len(report.mandatory_failures) == 0 and len(report.expected_exceptions) == 0:
        return "recommended"
    if len(report.unexpected_mandatory_failures) == 0:
        return "compatible-with-exceptions"
    return "experimental"


@dataclass(frozen=True, slots=True)
class CatalogEligibility:
    theme_eligibilities: dict[str, str] = field(default_factory=dict)
    recommended_count: int = 0
    compatible_count: int = 0
    experimental_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "theme_eligibilities": dict(self.theme_eligibilities),
            "recommended_count": self.recommended_count,
            "compatible_count": self.compatible_count,
            "experimental_count": self.experimental_count,
            "total": self.recommended_count + self.compatible_count + self.experimental_count,
        }


def classify_catalog_eligibility(
    catalog_report: CatalogAccessibilityReport,
) -> CatalogEligibility:
    theme_eligibilities: dict[str, str] = {}
    recommended_count = 0
    compatible_count = 0
    experimental_count = 0

    for report in catalog_report.reports:
        eligibility = classify_theme_eligibility(report)
        theme_eligibilities[report.theme_name] = eligibility
        if eligibility == "recommended":
            recommended_count += 1
        elif eligibility == "compatible-with-exceptions":
            compatible_count += 1
        else:
            experimental_count += 1

    return CatalogEligibility(
        theme_eligibilities=theme_eligibilities,
        recommended_count=recommended_count,
        compatible_count=compatible_count,
        experimental_count=experimental_count,
    )


def validate_catalog_accessibility(
    theme_reports: list[ThemeAccessibilityReport],
) -> CatalogAccessibilityReport:
    return CatalogAccessibilityReport(reports=theme_reports)


def build_provenance(mapping: dict[str, str]) -> list[ProvenanceEntry]:
    return [
        ProvenanceEntry(
            blog_token=token,
            halloy_source=source,
            derivation="direct",
        )
        for token, source in mapping.items()
    ]
