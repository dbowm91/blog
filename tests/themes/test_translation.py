from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from app.themes.colors import RGB, RGBA, contrast_ratio, is_dark_background
from app.themes.diagnostics import check_blog_theme_contrast
from app.themes.halloy import HalloyTheme, parse_halloy_theme
from app.themes.model import ALIASES, CSS_VARS, EMERGENCY_DEFAULT, BlogTheme
from app.themes.translate import (
    ThemeTranslationResult,
    translate_halloy_theme,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CATALOG = Path(__file__).resolve().parent.parent.parent / "themes"


def _load(name: str) -> HalloyTheme:
    return parse_halloy_theme(FIXTURES / name)


def _translate(name: str) -> ThemeTranslationResult:
    return translate_halloy_theme(_load(name))


class TestBlogThemeModel:
    def test_all_css_vars_covered(self) -> None:
        for key in CSS_VARS:
            assert hasattr(BlogTheme, key), f"BlogTheme has no field for CSS_VARS key {key!r}"

    def test_aliases_cover_legacy_keys(self) -> None:
        expected = {
            "bg",
            "bg-surface",
            "bg-elevated",
            "border",
            "text",
            "text-muted",
            "text-dim",
            "text-dim-strong",
            "text-secondary",
            "accent",
            "accent-hover",
            "accent-dim",
            "green",
            "green-dim",
            "red",
            "red-dim",
            "yellow",
            "purple",
            "purple-dim",
            "coral",
            "coral-dim",
            "amber",
            "amber-dim",
            "bg-hover",
            "noscript-bg",
            "noscript-text",
        }
        assert expected.issubset(set(ALIASES.keys()))

    def test_emergency_default_is_dark(self) -> None:
        assert is_dark_background(EMERGENCY_DEFAULT.bg_page)

    def test_emergency_default_fields_non_none(self) -> None:
        for f in dataclasses.fields(EMERGENCY_DEFAULT):
            value = getattr(EMERGENCY_DEFAULT, f.name)
            assert value is not None, f"EMERGENCY_DEFAULT.{f.name} is None"

    def test_emergency_default_text_on_accent_matches_contract(self) -> None:
        assert EMERGENCY_DEFAULT.text_on_accent == RGB(255, 255, 255)


class TestTranslateMinimal:
    def test_translates_without_error(self) -> None:
        result = _translate("minimal.toml")
        assert isinstance(result, ThemeTranslationResult)

    def test_result_has_theme(self) -> None:
        result = _translate("minimal.toml")
        assert isinstance(result.theme, BlogTheme)

    def test_is_dark(self) -> None:
        result = _translate("minimal.toml")
        assert result.is_dark is True

    def test_all_tokens_present(self) -> None:
        result = _translate("minimal.toml")
        for f in dataclasses.fields(result.theme):
            value = getattr(result.theme, f.name)
            assert value is not None, f"BlogTheme.{f.name} is None"

    def test_bg_page_matches_input(self) -> None:
        result = _translate("minimal.toml")
        theme = _load("minimal.toml")
        expected = theme.general.background
        assert result.theme.bg_page == expected.rgb

    def test_surface_matches_buffer(self) -> None:
        result = _translate("minimal.toml")
        theme = _load("minimal.toml")
        expected = theme.buffer.background
        assert result.theme.surface_default == expected.rgb

    def test_accent_matches_tertiary(self) -> None:
        result = _translate("minimal.toml")
        theme = _load("minimal.toml")
        expected = theme.text.tertiary
        assert result.theme.accent == expected.rgb

    def test_diagnostics_present(self) -> None:
        result = _translate("minimal.toml")
        assert hasattr(result.diagnostics, "warnings")
        assert hasattr(result.diagnostics, "provenance")

    def test_source_name_propagated(self) -> None:
        result = _translate("minimal.toml")
        assert result.source_name == "minimal.toml"


class TestTranslateLightDark:
    def test_dark_theme_classified(self) -> None:
        result = _translate("dark.toml")
        assert result.is_dark is True

    def test_light_theme_classified(self) -> None:
        result = _translate("light.toml")
        assert result.is_dark is False

    def test_dark_shadow_color(self) -> None:
        result = _translate("dark.toml")
        assert isinstance(result.theme.shadow_color, RGBA)
        assert result.theme.shadow_color.alpha == pytest.approx(0.35)

    def test_light_shadow_color(self) -> None:
        result = _translate("light.toml")
        assert isinstance(result.theme.shadow_color, RGBA)
        assert result.theme.shadow_color.alpha == pytest.approx(0.12)

    def test_dark_surface_hover_lighter(self) -> None:
        result = _translate("dark.toml")
        from app.themes.colors import _rgb_to_hsl

        _, _, hover_l = _rgb_to_hsl(result.theme.surface_hover)
        _, _, default_l = _rgb_to_hsl(result.theme.surface_default)
        assert hover_l > default_l

    def test_light_surface_hover_darker(self) -> None:
        result = _translate("light.toml")
        from app.themes.colors import _rgb_to_hsl

        _, _, hover_l = _rgb_to_hsl(result.theme.surface_hover)
        _, _, default_l = _rgb_to_hsl(result.theme.surface_default)
        assert hover_l < default_l


class TestTranslateAlpha:
    def test_alpha_colors_preserved(self) -> None:
        result = _translate("alpha.toml")
        assert isinstance(result.theme.navbar_bg, RGBA)
        assert result.theme.navbar_bg.alpha == pytest.approx(0.85)


class TestDerivations:
    def test_accent_dim_has_alpha(self) -> None:
        result = _translate("minimal.toml")
        assert isinstance(result.theme.accent_dim, RGBA)
        assert result.theme.accent_dim.alpha == pytest.approx(0.10)

    def test_state_bgs_are_opaque(self) -> None:
        result = _translate("minimal.toml")
        assert isinstance(result.theme.success_bg, RGBA)
        assert result.theme.success_bg.alpha == pytest.approx(1.0)
        assert isinstance(result.theme.error_bg, RGBA)
        assert result.theme.error_bg.alpha == pytest.approx(1.0)

    def test_accent_hover_differs_from_accent(self) -> None:
        result = _translate("minimal.toml")
        assert result.theme.accent_hover != result.theme.accent

    def test_surface_hover_differs_from_surface(self) -> None:
        result = _translate("minimal.toml")
        assert result.theme.surface_hover != result.theme.surface_default

    def test_surface_active_differs_from_surface(self) -> None:
        result = _translate("minimal.toml")
        assert result.theme.surface_active != result.theme.surface_default

    def test_border_strong_differs_from_border(self) -> None:
        result = _translate("minimal.toml")
        assert result.theme.border_strong != result.theme.border_primary

    def test_overlay_bg_is_fixed(self) -> None:
        result = _translate("minimal.toml")
        assert result.theme.overlay_bg == RGBA(0, 0, 0, 0.5)

    def test_noscript_bg_matches_emergency(self) -> None:
        result = _translate("minimal.toml")
        assert result.theme.noscript_bg == EMERGENCY_DEFAULT.noscript_bg

    def test_coral_matches_emergency(self) -> None:
        result = _translate("minimal.toml")
        assert result.theme.coral == EMERGENCY_DEFAULT.coral


class TestForegroundSelection:
    def test_text_on_accent_is_rgb(self) -> None:
        result = _translate("minimal.toml")
        assert isinstance(result.theme.text_on_accent, RGB)

    def test_text_on_accent_contrast(self) -> None:
        result = _translate("minimal.toml")
        ratio = contrast_ratio(result.theme.text_on_accent, result.theme.accent)
        assert ratio >= 4.0

    def test_text_on_success_contrast(self) -> None:
        result = _translate("minimal.toml")
        ratio = contrast_ratio(result.theme.text_on_success, result.theme.success_bg)
        assert ratio >= 4.5


class TestEmergencyDefault:
    def test_emergency_default_covers_all_fields(self) -> None:
        assert len(dataclasses.fields(EMERGENCY_DEFAULT)) == 52

    def test_emergency_default_deterministic(self) -> None:
        assert EMERGENCY_DEFAULT == EMERGENCY_DEFAULT

    def test_emergency_default_contrast_warnings_documented(self) -> None:
        warnings = check_blog_theme_contrast(EMERGENCY_DEFAULT)
        warning_tokens = {w.token for w in warnings}
        assert warning_tokens <= {"--blog-accent-focus-ring", "--blog-text-on-accent"}


class TestCatalogTranslation:
    @pytest.mark.parametrize(
        "path",
        [p for p in sorted(CATALOG.glob("*.toml")) if not p.name.startswith("._")],
        ids=[p.stem for p in sorted(CATALOG.glob("*.toml")) if not p.name.startswith("._")],
    )
    def test_each_catalog_theme_translates(self, path: Path) -> None:
        theme = parse_halloy_theme(path)
        result = translate_halloy_theme(theme)
        assert isinstance(result.theme, BlogTheme)
        assert result.source_name == path.name
        assert isinstance(result.is_dark, bool)
        assert len(result.diagnostics.warnings) >= 0

    def test_catalog_size(self) -> None:
        catalog_files = [p for p in sorted(CATALOG.glob("*.toml")) if not p.name.startswith("._")]
        assert len(catalog_files) == 50

    def test_catalog_deterministic(self) -> None:
        catalog = [p for p in sorted(CATALOG.glob("*.toml")) if not p.name.startswith("._")]
        path = catalog[0]
        theme = parse_halloy_theme(path)
        r1 = translate_halloy_theme(theme)
        r2 = translate_halloy_theme(theme)
        assert r1.theme == r2.theme


class TestNoCoupling:
    def test_translate_imports_no_flask(self) -> None:
        source = (
            Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "translate.py"
        ).read_text()
        assert "flask" not in source.lower()

    def test_model_imports_no_flask(self) -> None:
        source = (
            Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "model.py"
        ).read_text()
        assert "flask" not in source.lower()

    def test_diagnostics_imports_no_flask(self) -> None:
        source = (
            Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "diagnostics.py"
        ).read_text()
        assert "flask" not in source.lower()
