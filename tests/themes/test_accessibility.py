from __future__ import annotations

from pathlib import Path

import pytest

from app.themes.colors import RGB, RGBA
from app.themes.diagnostics import (
    AccessibilityFinding,
    CatalogAccessibilityReport,
    ClassificationAudit,
    Severity,
    ThemeAccessibilityReport,
    _CONTRAST_PAIRS,
    check_blog_theme_contrast,
    check_contrast,
    validate_catalog_accessibility,
    validate_theme_accessibility,
)
from app.themes.model import EMERGENCY_DEFAULT, BlogTheme
from app.themes.translate import translate_halloy_theme
from app.themes.halloy import parse_halloy_theme

CATALOG = Path(__file__).resolve().parent.parent.parent / "themes"


def _rgb(hex_str: str) -> RGB:
    from app.themes.colors import from_hex

    return from_hex(hex_str).rgb


class TestSeverity:
    def test_mandatory_value(self) -> None:
        assert Severity.MANDATORY.value == "mandatory"

    def test_advisory_value(self) -> None:
        assert Severity.ADVISORY.value == "advisory"

    def test_string_comparison(self) -> None:
        assert Severity.MANDATORY == "mandatory"
        assert Severity.ADVISORY == "advisory"


class TestCheckContrast:
    def test_passes_when_ratio_sufficient(self) -> None:
        result = check_contrast(RGB(0, 0, 0), RGB(255, 255, 255), "--test", "test", 4.5)
        assert result is None

    def test_fails_when_ratio_insufficient(self) -> None:
        result = check_contrast(RGB(128, 128, 128), RGB(200, 200, 200), "--test", "test", 4.5)
        assert result is not None
        assert result.ratio < 4.5
        assert result.wcag == "fail"

    def test_returns_contrast_warning(self) -> None:
        result = check_contrast(RGB(128, 128, 128), RGB(200, 200, 200), "--test", "test", 4.5)
        assert isinstance(result, AccessibilityFinding) or result is not None
        assert result.token == "--test"
        assert result.description == "test"

    def test_exact_boundary_passes(self) -> None:
        result = check_contrast(RGB(0, 0, 0), RGB(255, 255, 255), "--test", "test", 21.0)
        assert result is None

    def test_just_below_boundary_fails(self) -> None:
        result = check_contrast(RGB(0, 0, 0), RGB(255, 255, 255), "--test", "test", 21.1)
        assert result is not None


class TestAccessibilityFinding:
    def test_frozen_dataclass(self) -> None:
        finding = AccessibilityFinding(
            theme_name="test",
            token="--blog-text",
            description="test pair",
            foreground="#000000",
            background="#ffffff",
            ratio=21.0,
            required=4.5,
            wcag="AAA",
            severity=Severity.MANDATORY,
            remediation="Fix it",
        )
        assert finding.theme_name == "test"
        assert finding.severity == Severity.MANDATORY

    def test_to_dict(self) -> None:
        finding = AccessibilityFinding(
            theme_name="test",
            token="--blog-text",
            description="test pair",
            foreground="#000000",
            background="#ffffff",
            ratio=21.0,
            required=4.5,
            wcag="AAA",
            severity=Severity.MANDATORY,
            remediation="Fix it",
        )
        d = finding.to_dict()
        assert d["theme_name"] == "test"
        assert d["severity"] == "mandatory"
        assert d["ratio"] == 21.0


class TestContrastPairDefinitions:
    def test_all_pairs_have_required_fields(self) -> None:
        for (
            fg_field,
            bg_field,
            description,
            min_ratio,
            severity,
            remediation_hint,
        ) in _CONTRAST_PAIRS:
            assert isinstance(fg_field, str)
            assert isinstance(bg_field, str)
            assert isinstance(description, str)
            assert isinstance(min_ratio, float)
            assert isinstance(severity, Severity)
            assert isinstance(remediation_hint, str)

    def test_min_ratio_thresholds(self) -> None:
        for _, _, _, min_ratio, severity, _ in _CONTRAST_PAIRS:
            if severity == Severity.MANDATORY and min_ratio < 4.0:
                pair_desc = [p for p in _CONTRAST_PAIRS if p[3] == min_ratio and p[4] == severity]
                for p in pair_desc:
                    if "focus" in p[0] or "border" in p[0]:
                        continue
                    assert min_ratio >= 4.5, (
                        f"Mandatory non-focus pair requires >= 4.5, got {min_ratio}"
                    )
            if severity == Severity.ADVISORY:
                assert min_ratio >= 3.0, f"Advisory pair requires >= 3.0, got {min_ratio}"

    def test_mandatory_pairs_cover_critical_tokens(self) -> None:
        mandatory_fg_fields = {pair[0] for pair in _CONTRAST_PAIRS if pair[4] == Severity.MANDATORY}
        critical = {"text_primary", "text_link", "text_on_accent", "input_text", "code_text"}
        assert critical <= mandatory_fg_fields

    def test_focus_ring_pairs_present(self) -> None:
        focus_pairs = [p for p in _CONTRAST_PAIRS if "focus" in p[0]]
        assert len(focus_pairs) >= 2

    def test_state_pairs_present(self) -> None:
        state_pairs = [p for p in _CONTRAST_PAIRS if "on_" in p[0]]
        assert len(state_pairs) >= 4


class TestValidateThemeAccessibility:
    def test_emergency_default_findings(self) -> None:
        report = validate_theme_accessibility(EMERGENCY_DEFAULT, theme_name="emergency-default")
        assert isinstance(report, ThemeAccessibilityReport)
        assert report.theme_name == "emergency-default"
        assert isinstance(report.findings, list)
        assert report.classification is not None
        assert report.classification.computed_dark is True

    def test_emergency_default_classification(self) -> None:
        report = validate_theme_accessibility(EMERGENCY_DEFAULT, theme_name="emergency-default")
        assert report.classification.page_luminance < 0.5
        assert report.classification.mismatch is False

    def test_perfect_theme_passes(self) -> None:
        theme = BlogTheme(
            bg_page=_rgb("#ffffff"),
            surface_default=_rgb("#f8f8f8"),
            surface_elevated=_rgb("#f0f0f0"),
            surface_hover=_rgb("#e8e8e8"),
            surface_active=_rgb("#e0e0e0"),
            navbar_bg=RGBA(255, 255, 255, 0.85),
            overlay_bg=RGBA(0, 0, 0, 0.5),
            border_primary=_rgb("#cccccc"),
            border_subtle=_rgb("#dddddd"),
            border_strong=_rgb("#bbbbbb"),
            border_focus=_rgb("#0000ff"),
            navbar_border=_rgb("#cccccc"),
            text_primary=_rgb("#000000"),
            text_secondary=_rgb("#333333"),
            text_muted=_rgb("#666666"),
            text_dim=_rgb("#888888"),
            text_on_accent=_rgb("#ffffff"),
            text_on_success=_rgb("#ffffff"),
            text_on_error=_rgb("#ffffff"),
            text_on_warning=_rgb("#ffffff"),
            text_on_info=_rgb("#ffffff"),
            text_link=_rgb("#0000ee"),
            text_link_hover=_rgb("#0000cc"),
            accent=_rgb("#0000ff"),
            accent_hover=_rgb("#0000dd"),
            accent_dim=RGBA(0, 0, 255, 0.1),
            accent_link=_rgb("#0000ee"),
            accent_focus_ring=_rgb("#0000ff"),
            success_fg=_rgb("#006600"),
            success_bg=RGB(0, 80, 0),
            error_fg=_rgb("#cc0000"),
            error_bg=RGB(120, 0, 0),
            warning_fg=_rgb("#996600"),
            warning_bg=RGB(80, 60, 0),
            info_fg=_rgb("#000099"),
            info_bg=RGB(0, 0, 80),
            input_bg=_rgb("#ffffff"),
            input_border=_rgb("#cccccc"),
            input_text=_rgb("#000000"),
            code_bg=_rgb("#f0f0f0"),
            code_border=_rgb("#dddddd"),
            code_text=_rgb("#000000"),
            selection_bg=_rgb("#b0d4ff"),
            navbar_text=_rgb("#000000"),
            navbar_text_muted=_rgb("#666666"),
            shadow_color=RGBA(0, 0, 0, 0.1),
            noscript_bg=_rgb("#ffff00"),
            noscript_text=_rgb("#000000"),
            coral=_rgb("#ff6633"),
            coral_dim=RGBA(255, 102, 51, 0.15),
        )
        report = validate_theme_accessibility(theme, theme_name="perfect-theme")
        mandatory = report.mandatory_failures
        assert len(mandatory) == 0

    def test_low_contrast_detects_failures(self) -> None:
        theme = BlogTheme(
            bg_page=_rgb("#ffffff"),
            surface_default=_rgb("#ffffff"),
            surface_elevated=_rgb("#ffffff"),
            surface_hover=_rgb("#ffffff"),
            surface_active=_rgb("#ffffff"),
            navbar_bg=RGBA(255, 255, 255, 0.85),
            overlay_bg=RGBA(0, 0, 0, 0.5),
            border_primary=_rgb("#cccccc"),
            border_subtle=_rgb("#dddddd"),
            border_strong=_rgb("#bbbbbb"),
            border_focus=_rgb("#cccccc"),
            navbar_border=_rgb("#cccccc"),
            text_primary=_rgb("#cccccc"),
            text_secondary=_rgb("#cccccc"),
            text_muted=_rgb("#cccccc"),
            text_dim=_rgb("#cccccc"),
            text_on_accent=_rgb("#cccccc"),
            text_on_success=_rgb("#cccccc"),
            text_on_error=_rgb("#cccccc"),
            text_on_warning=_rgb("#cccccc"),
            text_on_info=_rgb("#cccccc"),
            text_link=_rgb("#cccccc"),
            text_link_hover=_rgb("#cccccc"),
            accent=_rgb("#cccccc"),
            accent_hover=_rgb("#cccccc"),
            accent_dim=RGBA(204, 204, 204, 0.1),
            accent_link=_rgb("#cccccc"),
            accent_focus_ring=_rgb("#cccccc"),
            success_fg=_rgb("#cccccc"),
            success_bg=RGBA(204, 204, 204, 0.15),
            error_fg=_rgb("#cccccc"),
            error_bg=RGBA(204, 204, 204, 0.15),
            warning_fg=_rgb("#cccccc"),
            warning_bg=RGBA(204, 204, 204, 0.15),
            info_fg=_rgb("#cccccc"),
            info_bg=RGBA(204, 204, 204, 0.15),
            input_bg=_rgb("#ffffff"),
            input_border=_rgb("#cccccc"),
            input_text=_rgb("#cccccc"),
            code_bg=_rgb("#ffffff"),
            code_border=_rgb("#cccccc"),
            code_text=_rgb("#cccccc"),
            selection_bg=_rgb("#cccccc"),
            navbar_text=_rgb("#cccccc"),
            navbar_text_muted=_rgb("#cccccc"),
            shadow_color=RGBA(0, 0, 0, 0.1),
            noscript_bg=_rgb("#ffff00"),
            noscript_text=_rgb("#000000"),
            coral=_rgb("#cccccc"),
            coral_dim=RGBA(204, 204, 204, 0.15),
        )
        report = validate_theme_accessibility(theme, theme_name="low-contrast")
        assert len(report.mandatory_failures) > 0
        assert report.passed is False

    def test_filename_dark_mismatch(self) -> None:
        report = validate_theme_accessibility(
            EMERGENCY_DEFAULT,
            theme_name="test",
            filename_dark=False,
        )
        assert report.classification is not None
        assert report.classification.mismatch is True
        assert report.classification.filename_dark is False
        assert report.classification.computed_dark is True

    def test_filename_dark_match(self) -> None:
        report = validate_theme_accessibility(
            EMERGENCY_DEFAULT,
            theme_name="test",
            filename_dark=True,
        )
        assert report.classification is not None
        assert report.classification.mismatch is False

    def test_no_filename_dark_no_mismatch(self) -> None:
        report = validate_theme_accessibility(
            EMERGENCY_DEFAULT,
            theme_name="test",
            filename_dark=None,
        )
        assert report.classification is not None
        assert report.classification.mismatch is False


class TestThemeAccessibilityReport:
    def test_passed_when_no_mandatory(self) -> None:
        report = ThemeAccessibilityReport(
            theme_name="test",
            source="bundled",
            is_dark=True,
            findings=[
                AccessibilityFinding(
                    theme_name="test",
                    token="--test",
                    description="test",
                    foreground="#000",
                    background="#fff",
                    ratio=3.5,
                    required=3.0,
                    wcag="AA-large",
                    severity=Severity.ADVISORY,
                    remediation="Fix",
                )
            ],
        )
        assert report.passed is True
        assert len(report.mandatory_failures) == 0
        assert len(report.advisory_warnings) == 1

    def test_failed_when_mandatory_present(self) -> None:
        report = ThemeAccessibilityReport(
            theme_name="test",
            source="bundled",
            is_dark=True,
            findings=[
                AccessibilityFinding(
                    theme_name="test",
                    token="--test",
                    description="test",
                    foreground="#888",
                    background="#999",
                    ratio=1.5,
                    required=4.5,
                    wcag="fail",
                    severity=Severity.MANDATORY,
                    remediation="Fix",
                )
            ],
        )
        assert report.passed is False
        assert len(report.mandatory_failures) == 1

    def test_to_dict(self) -> None:
        report = ThemeAccessibilityReport(
            theme_name="test",
            source="bundled",
            is_dark=True,
            classification=ClassificationAudit(
                theme_name="test",
                filename_dark=True,
                computed_dark=True,
                page_luminance=0.1,
                mismatch=False,
            ),
        )
        d = report.to_dict()
        assert d["theme_name"] == "test"
        assert d["passed"] is True
        assert "classification" in d


class TestCatalogAccessibilityReport:
    def test_empty_report(self) -> None:
        report = CatalogAccessibilityReport()
        assert report.total_themes == 0
        assert report.passed_count == 0
        assert report.failed_count == 0

    def test_mixed_reports(self) -> None:
        passed = ThemeAccessibilityReport(
            theme_name="pass", source="bundled", is_dark=True, findings=[]
        )
        failed = ThemeAccessibilityReport(
            theme_name="fail",
            source="bundled",
            is_dark=True,
            findings=[
                AccessibilityFinding(
                    theme_name="fail",
                    token="--test",
                    description="test",
                    foreground="#888",
                    background="#999",
                    ratio=1.5,
                    required=4.5,
                    wcag="fail",
                    severity=Severity.MANDATORY,
                    remediation="Fix",
                )
            ],
        )
        report = CatalogAccessibilityReport(reports=[passed, failed])
        assert report.total_themes == 2
        assert report.passed_count == 1
        assert report.failed_count == 1
        assert report.total_mandatory == 1

    def test_worst_findings(self) -> None:
        report = CatalogAccessibilityReport(
            reports=[
                ThemeAccessibilityReport(
                    theme_name="t",
                    source="bundled",
                    is_dark=True,
                    findings=[
                        AccessibilityFinding(
                            theme_name="t",
                            token="--test",
                            description="test",
                            foreground="#888",
                            background="#999",
                            ratio=1.2,
                            required=4.5,
                            wcag="fail",
                            severity=Severity.MANDATORY,
                            remediation="Fix",
                        ),
                        AccessibilityFinding(
                            theme_name="t",
                            token="--test2",
                            description="test2",
                            foreground="#888",
                            background="#999",
                            ratio=3.0,
                            required=4.5,
                            wcag="AA-large",
                            severity=Severity.MANDATORY,
                            remediation="Fix",
                        ),
                    ],
                )
            ]
        )
        worst = report.worst_findings
        assert worst[0].ratio <= worst[1].ratio

    def test_classification_mismatches(self) -> None:
        report = CatalogAccessibilityReport(
            reports=[
                ThemeAccessibilityReport(
                    theme_name="mismatch",
                    source="bundled",
                    is_dark=True,
                    classification=ClassificationAudit(
                        theme_name="mismatch",
                        filename_dark=False,
                        computed_dark=True,
                        page_luminance=0.1,
                        mismatch=True,
                    ),
                )
            ]
        )
        assert len(report.classification_mismatches) == 1

    def test_to_dict(self) -> None:
        report = CatalogAccessibilityReport(reports=[])
        d = report.to_dict()
        assert d["total_themes"] == 0
        assert d["passed"] == 0
        assert d["failed"] == 0


class TestValidateCatalogAccessibility:
    def test_returns_catalog_report(self) -> None:
        report = validate_catalog_accessibility([])
        assert isinstance(report, CatalogAccessibilityReport)
        assert report.total_themes == 0


class TestBundledThemesAccessibility:
    @pytest.mark.parametrize(
        "path",
        [p for p in sorted(CATALOG.glob("*.toml")) if not p.name.startswith("._")],
        ids=[p.stem for p in sorted(CATALOG.glob("*.toml")) if not p.name.startswith("._")],
    )
    def test_bundled_theme_translates(self, path: Path) -> None:
        theme = parse_halloy_theme(path)
        result = translate_halloy_theme(theme)
        assert isinstance(result.theme, BlogTheme)

    @pytest.mark.parametrize(
        "path",
        [p for p in sorted(CATALOG.glob("*.toml")) if not p.name.startswith("._")],
        ids=[p.stem for p in sorted(CATALOG.glob("*.toml")) if not p.name.startswith("._")],
    )
    def test_bundled_theme_accessibility_validates(self, path: Path) -> None:
        theme = parse_halloy_theme(path)
        result = translate_halloy_theme(theme)
        report = validate_theme_accessibility(
            result.theme,
            theme_name=path.stem,
            filename_dark=result.is_dark,
        )
        assert isinstance(report, ThemeAccessibilityReport)
        assert report.classification is not None
        assert report.classification.computed_dark == result.is_dark

    def test_all_bundled_themes_evaluate(self) -> None:
        toml_files = [p for p in sorted(CATALOG.glob("*.toml")) if not p.name.startswith("._")]
        reports = []
        for path in toml_files:
            theme = parse_halloy_theme(path)
            result = translate_halloy_theme(theme)
            report = validate_theme_accessibility(
                result.theme,
                theme_name=path.stem,
                filename_dark=result.is_dark,
            )
            reports.append(report)
        catalog = validate_catalog_accessibility(reports)
        assert catalog.total_themes == len(toml_files)
        assert catalog.passed_count + catalog.failed_count == catalog.total_themes


class TestLegacyCheckBlogThemeContrast:
    def test_emergency_default_has_known_warnings(self) -> None:
        warnings = check_blog_theme_contrast(EMERGENCY_DEFAULT)
        warning_tokens = {w.token for w in warnings}
        assert warning_tokens <= {"--blog-accent-focus-ring", "--blog-text-on-accent"}

    def test_returns_list_of_contrast_warning(self) -> None:
        warnings = check_blog_theme_contrast(EMERGENCY_DEFAULT)
        assert isinstance(warnings, list)
        for w in warnings:
            assert hasattr(w, "token")
            assert hasattr(w, "ratio")
            assert hasattr(w, "wcag")


class TestClassificationAudit:
    def test_fields(self) -> None:
        audit = ClassificationAudit(
            theme_name="test",
            filename_dark=True,
            computed_dark=False,
            page_luminance=0.6,
            mismatch=True,
        )
        assert audit.theme_name == "test"
        assert audit.mismatch is True
