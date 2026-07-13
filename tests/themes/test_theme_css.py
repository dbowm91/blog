from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.themes.colors import to_hex
from app.themes.halloy import parse_halloy_theme
from app.themes.model import ALIASES, CSS_VARS, EMERGENCY_DEFAULT
from app.themes.translate import (
    to_css_variables,
    to_legacy_vars,
    to_theme_vars,
    translate_halloy_theme,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CATALOG = Path(__file__).resolve().parent.parent.parent / "themes"


def _load(name: str):
    return parse_halloy_theme(FIXTURES / name)


def _translate(name: str):
    return translate_halloy_theme(_load(name))


def _css(name: str) -> str:
    return to_css_variables(_translate(name).theme)


class TestCssVariablesBasic:
    def test_starts_with_selector(self) -> None:
        assert _css("minimal.toml").startswith(":root {")

    def test_ends_with_closing_brace(self) -> None:
        assert _css("minimal.toml").rstrip().endswith("}")

    def test_has_trailing_newline(self) -> None:
        assert _css("minimal.toml").endswith("\n")

    def test_all_css_vars_present(self) -> None:
        css = _css("minimal.toml")
        for css_var in CSS_VARS.values():
            assert f"{css_var}:" in css

    def test_no_empty_values(self) -> None:
        css = _css("minimal.toml")
        for line in css.strip().split("\n")[1:-1]:
            prop, value = line.strip().rstrip(";").split(": ", 1)
            assert len(value) > 0, f"{prop} has empty value"

    def test_valid_hex_values(self) -> None:
        hex_re = re.compile(r"#[0-9a-f]{6}(?:[0-9a-f]{2})?")
        css = _css("minimal.toml")
        for line in css.strip().split("\n")[1:-1]:
            _, value = line.strip().rstrip(";").split(": ", 1)
            if value.startswith("#"):
                assert hex_re.match(value), f"Invalid hex value: {value}"

    def test_valid_rgba_values(self) -> None:
        rgba_re = re.compile(r"rgba\(\d+, \d+, \d+, [\d.]+\)")
        css = _css("minimal.toml")
        for line in css.strip().split("\n")[1:-1]:
            _, value = line.strip().rstrip(";").split(": ", 1)
            if value.startswith("rgba"):
                assert rgba_re.match(value), f"Invalid rgba value: {value}"


class TestCssOrdering:
    def test_deterministic_output(self) -> None:
        result = translate_halloy_theme(_load("minimal.toml"))
        first = to_css_variables(result.theme)
        second = to_css_variables(result.theme)
        assert first == second

    def test_order_matches_css_vars(self) -> None:
        css = _css("minimal.toml")
        lines = css.strip().split("\n")[1:-1]
        expected_vars = list(CSS_VARS.values())
        actual_vars = [line.strip().rstrip(";").split(": ", 1)[0] for line in lines]
        assert actual_vars == expected_vars


class TestCssSelector:
    def test_custom_selector(self) -> None:
        result = translate_halloy_theme(_load("minimal.toml"))
        css = to_css_variables(result.theme, selector=".dark")
        assert css.startswith(".dark {")

    def test_default_selector_is_root(self) -> None:
        result = translate_halloy_theme(_load("minimal.toml"))
        css = to_css_variables(result.theme)
        assert css.startswith(":root {")


class TestCssValues:
    def test_bg_page_value(self) -> None:
        result = _translate("minimal.toml")
        theme = result.theme
        expected = to_hex(theme.bg_page)
        css = _css("minimal.toml")
        for line in css.strip().split("\n")[1:-1]:
            prop, value = line.strip().rstrip(";").split(": ", 1)
            if prop == "--blog-bg-page":
                assert value == expected
                break

    def test_accent_dim_has_alpha(self) -> None:
        css = _css("minimal.toml")
        for line in css.strip().split("\n")[1:-1]:
            prop, value = line.strip().rstrip(";").split(": ", 1)
            if prop == "--blog-accent-dim":
                assert len(value) == 9
                assert value.startswith("#")
                break

    def test_overlay_bg_has_alpha(self) -> None:
        css = _css("minimal.toml")
        for line in css.strip().split("\n")[1:-1]:
            prop, value = line.strip().rstrip(";").split(": ", 1)
            if prop == "--blog-overlay-bg":
                assert len(value) == 9
                assert value.startswith("#")
                break

    def test_shadow_color_has_alpha(self) -> None:
        css = _css("minimal.toml")
        for line in css.strip().split("\n")[1:-1]:
            prop, value = line.strip().rstrip(";").split(": ", 1)
            if prop == "--blog-shadow-color":
                assert len(value) == 9
                assert value.startswith("#")
                break


class TestCssEmergencyDefault:
    def test_emergency_default_serializes(self) -> None:
        css = to_css_variables(EMERGENCY_DEFAULT)
        assert css.startswith(":root {")
        assert css.rstrip().endswith("}")
        assert css.endswith("\n")

    def test_emergency_default_has_all_vars(self) -> None:
        css = to_css_variables(EMERGENCY_DEFAULT)
        for css_var in CSS_VARS.values():
            assert f"{css_var}:" in css


class TestThemeVars:
    def test_returns_dict(self) -> None:
        result = translate_halloy_theme(_load("minimal.toml"))
        tv = to_theme_vars(result.theme)
        assert isinstance(tv, dict)

    def test_keys_are_css_var_names(self) -> None:
        result = translate_halloy_theme(_load("minimal.toml"))
        tv = to_theme_vars(result.theme)
        for key in tv:
            assert key.startswith("--blog-")

    def test_values_match_css(self) -> None:
        result = translate_halloy_theme(_load("minimal.toml"))
        theme = result.theme
        tv = to_theme_vars(theme)
        css = to_css_variables(theme)
        for field_name, css_var in CSS_VARS.items():
            expected = tv[css_var]
            found = False
            for line in css.strip().split("\n")[1:-1]:
                prop, value = line.strip().rstrip(";").split(": ", 1)
                if prop == css_var:
                    assert value == expected, f"Mismatch for {css_var}"
                    found = True
                    break
            assert found, f"{css_var} not found in CSS output"

    def test_all_tokens_present(self) -> None:
        result = translate_halloy_theme(_load("minimal.toml"))
        tv = to_theme_vars(result.theme)
        assert len(tv) == len(CSS_VARS)


class TestLegacyVars:
    def test_returns_dict(self) -> None:
        result = translate_halloy_theme(_load("minimal.toml"))
        lv = to_legacy_vars(result.theme)
        assert isinstance(lv, dict)

    def test_keys_are_legacy_names(self) -> None:
        result = translate_halloy_theme(_load("minimal.toml"))
        lv = to_legacy_vars(result.theme)
        for key in lv:
            assert not key.startswith("--")

    def test_all_legacy_keys_present(self) -> None:
        result = translate_halloy_theme(_load("minimal.toml"))
        lv = to_legacy_vars(result.theme)
        assert len(lv) == len(ALIASES)

    def test_bg_matches_bg_page(self) -> None:
        result = translate_halloy_theme(_load("minimal.toml"))
        theme = result.theme
        lv = to_legacy_vars(theme)
        assert lv["bg"] == to_hex(theme.bg_page)

    def test_accent_matches_accent(self) -> None:
        result = translate_halloy_theme(_load("minimal.toml"))
        theme = result.theme
        lv = to_legacy_vars(theme)
        assert lv["accent"] == to_hex(theme.accent)

    def test_green_matches_success_fg(self) -> None:
        result = translate_halloy_theme(_load("minimal.toml"))
        theme = result.theme
        lv = to_legacy_vars(theme)
        assert lv["green"] == to_hex(theme.success_fg)


class TestCatalogCss:
    @pytest.mark.parametrize(
        "path",
        [p for p in sorted(CATALOG.glob("*.toml")) if not p.name.startswith("._")],
        ids=[p.stem for p in sorted(CATALOG.glob("*.toml")) if not p.name.startswith("._")],
    )
    def test_each_catalog_theme_serializes_to_valid_css(self, path: Path) -> None:
        theme = parse_halloy_theme(path)
        result = translate_halloy_theme(theme)
        css = to_css_variables(result.theme)
        assert css.startswith(":root {")
        assert css.rstrip().endswith("}")
        for line in css.strip().split("\n")[1:-1]:
            assert ":" in line
            prop, value = line.strip().rstrip(";").split(": ", 1)
            assert prop.startswith("--blog-")
            assert len(value) > 0


class TestNoCoupling:
    def test_translate_imports_no_flask(self) -> None:
        translate_path = (
            Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "translate.py"
        )
        source = translate_path.read_text()
        assert "flask" not in source.lower()
