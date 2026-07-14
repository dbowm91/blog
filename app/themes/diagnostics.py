from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

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

    def to_dict(self) -> dict[str, object]:
        return {
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
    def advisory_warnings(self) -> list[AccessibilityFinding]:
        return [f for f in self.findings if f.severity == Severity.ADVISORY]

    @property
    def passed(self) -> bool:
        return len(self.mandatory_failures) == 0

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "theme_name": self.theme_name,
            "source": self.source,
            "is_dark": self.is_dark,
            "passed": self.passed,
            "mandatory_failures": len(self.mandatory_failures),
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
        "bg_page",
        "success-fg on bg-page",
        4.5,
        Severity.MANDATORY,
        "success indicator text",
    ),
    ("error_fg", "bg_page", "error-fg on bg-page", 4.5, Severity.MANDATORY, "error indicator text"),
    (
        "warning_fg",
        "bg_page",
        "warning-fg on bg-page",
        3.0,
        Severity.ADVISORY,
        "warning indicator text",
    ),
    ("info_fg", "bg_page", "info-fg on bg-page", 3.0, Severity.ADVISORY, "info indicator text"),
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
]


def check_blog_theme_contrast(blog_theme: BlogTheme) -> list[ContrastWarning]:
    checks: list[tuple[RGB | RGBA, RGB | RGBA, str, str, float]] = [
        (
            blog_theme.text_primary,
            blog_theme.bg_page,
            "--blog-text-primary",
            "text-primary on bg-page",
            4.5,
        ),
        (
            blog_theme.text_primary,
            blog_theme.surface_default,
            "--blog-text-primary",
            "text-primary on surface-default",
            4.5,
        ),
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

    warnings: list[ContrastWarning] = []
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
