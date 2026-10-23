"""Contrast coverage for text painted on page surfaces.

The post title sits on the page background, so the theme validator must
check text against the background surfaces -- not only against accent-filled
surfaces.
"""

from __future__ import annotations

import dataclasses

import pytest

from app.themes.colors import RGB, contrast_ratio
from app.themes.diagnostics import (
    Severity,
    _CONTRAST_PAIRS,
    check_blog_theme_contrast,
    check_text_on_background_contrast,
    validate_theme_accessibility,
)
from app.themes.model import EMERGENCY_DEFAULT
from app.themes.registry import ThemeRegistry


def _bundled_themes() -> list[tuple[str, object]]:
    registry = ThemeRegistry()
    return [
        (descriptor.canonical_name, registry.load(descriptor.canonical_name).blog_theme)
        for descriptor in registry.list_themes()
    ]


class TestTextOnBackgroundPairs:
    def test_page_background_pair_is_mandatory(self) -> None:
        pairs = [pair for pair in _CONTRAST_PAIRS if pair[2] == "text-primary on bg-page"]
        assert pairs, "no text-on-background pair is validated"
        fg_field, bg_field, _, min_ratio, severity, _ = pairs[0]
        assert (fg_field, bg_field) == ("text_primary", "bg_page")
        assert min_ratio == 4.5
        assert severity == Severity.MANDATORY

    def test_surface_default_pair_is_mandatory(self) -> None:
        pairs = [pair for pair in _CONTRAST_PAIRS if pair[2] == "text-primary on surface-default"]
        assert pairs, "text on card surfaces is not validated"
        assert pairs[0][4] == Severity.MANDATORY

    def test_surface_elevated_pair_is_advisory(self) -> None:
        pairs = [pair for pair in _CONTRAST_PAIRS if pair[2] == "text-primary on surface-elevated"]
        assert pairs, "text on elevated surfaces is not validated"
        assert pairs[0][4] == Severity.ADVISORY
        assert pairs[0][3] >= 3.0


class TestCheckTextOnBackgroundContrast:
    def test_compliant_theme_has_no_warning(self) -> None:
        assert check_text_on_background_contrast(EMERGENCY_DEFAULT) == []

    def test_low_contrast_background_is_reported(self) -> None:
        theme = dataclasses.replace(
            EMERGENCY_DEFAULT,
            bg_page=RGB(20, 20, 20),
            text_primary=RGB(30, 30, 30),
        )
        warnings = check_text_on_background_contrast(theme)
        warning = next(item for item in warnings if item.description == "text-primary on bg-page")
        assert warning.token == "--blog-text-primary"
        assert warning.ratio < 4.5

    def test_low_contrast_elevated_surface_is_reported(self) -> None:
        theme = dataclasses.replace(
            EMERGENCY_DEFAULT,
            surface_elevated=RGB(20, 20, 20),
            text_primary=RGB(30, 30, 30),
        )
        descriptions = {item.description for item in check_text_on_background_contrast(theme)}
        assert "text-primary on surface-elevated" in descriptions

    def test_ratio_matches_direct_computation(self) -> None:
        theme = dataclasses.replace(EMERGENCY_DEFAULT, bg_page=RGB(200, 200, 210))
        warning = next(
            item
            for item in check_text_on_background_contrast(theme)
            if item.description == "text-primary on bg-page"
        )
        expected = contrast_ratio(theme.text_primary, theme.bg_page)
        assert warning.ratio == pytest.approx(round(expected, 2))

    def test_translation_warnings_include_the_background_pairs(self) -> None:
        theme = dataclasses.replace(
            EMERGENCY_DEFAULT,
            bg_page=RGB(20, 20, 20),
            text_primary=RGB(30, 30, 30),
        )
        background_descriptions = {
            item.description for item in check_text_on_background_contrast(theme)
        }
        translation_descriptions = {item.description for item in check_blog_theme_contrast(theme)}
        assert background_descriptions <= translation_descriptions


class TestCatalogGate:
    def test_elevated_surface_pair_never_blocks_a_theme(self) -> None:
        for name, theme in _bundled_themes():
            report = validate_theme_accessibility(theme, theme_name=name)
            for finding in report.findings:
                if finding.description == "text-primary on surface-elevated":
                    assert finding.severity == Severity.ADVISORY, (
                        f"{name} would be gated by the elevated-surface pair"
                    )

    def test_every_bundled_theme_validates_the_page_background_pair(self) -> None:
        for name, theme in _bundled_themes():
            report = validate_theme_accessibility(theme, theme_name=name)
            findings = [
                finding
                for finding in report.findings
                if finding.description == "text-primary on bg-page"
            ]
            ratio = contrast_ratio(theme.text_primary, theme.bg_page)
            if ratio < 4.5:
                assert findings, f"{name} misses its text-on-background finding"
                assert findings[0].severity == Severity.MANDATORY
            else:
                assert not findings, f"{name} reports a finding above the threshold"
