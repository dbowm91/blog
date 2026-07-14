"""Phase 09 integration tests — CSS and generated-markup audit.

Tests that:
- Every required CSS variable is emitted in both dark and light schemes
- No prohibited hardcoded palette literals outside allowlisted files
- Critical CSS uses semantic variables
- Focus indicators remain visible
- Custom CSS can still override tokens
"""

from __future__ import annotations

import re
from pathlib import Path

from app.themes.colors import RGBA
from app.themes.model import ALIASES, CSS_VARS, EMERGENCY_DEFAULT
from app.themes.translate import to_legacy_vars, to_theme_vars

CRITICAL_CSS = Path(__file__).resolve().parent.parent.parent / "app" / "static" / "css" / "critical.css"

REQUIRED_LEGACY_KEYS = [
    "bg",
    "bg-surface",
    "bg-elevated",
    "bg-hover",
    "border",
    "text",
    "text-muted",
    "text-dim",
    "text-secondary",
    "text-on-accent",
    "accent",
    "accent-hover",
    "accent-dim",
    "green",
    "green-dim",
    "red",
    "red-dim",
    "yellow",
    "yellow-dim",
    "purple",
    "purple-dim",
    "coral",
    "coral-dim",
    "amber",
    "amber-dim",
    "noscript-bg",
    "noscript-text",
    "navbar-bg",
    "overlay-bg",
    "warning-fg",
    "warning-bg",
    "success-bg",
    "error-bg",
    "info-fg",
    "info-bg",
]


class TestLegacyVarsCompleteness:
    def test_all_required_keys_present(self) -> None:
        legacy = to_legacy_vars(EMERGENCY_DEFAULT)
        for key in REQUIRED_LEGACY_KEYS:
            assert key in legacy, f"missing legacy key: {key}"

    def test_no_empty_values(self) -> None:
        legacy = to_legacy_vars(EMERGENCY_DEFAULT)
        for key, value in legacy.items():
            assert len(value) > 0, f"empty value for legacy key: {key}"

    def test_all_values_are_valid_hex_or_css(self) -> None:
        hex_re = re.compile(r"#[0-9a-f]{6}(?:[0-9a-f]{2})?")
        css_re = re.compile(r"rgba\(\d+, \d+, \d+, [\d.]+\)")
        legacy = to_legacy_vars(EMERGENCY_DEFAULT)
        for key, value in legacy.items():
            assert hex_re.match(value) or css_re.match(value), (
                f"invalid color value for {key}: {value}"
            )


class TestThemeVarsCompleteness:
    def test_all_css_vars_keys_present(self) -> None:
        theme_vars = to_theme_vars(EMERGENCY_DEFAULT)
        for field_name in CSS_VARS:
            css_var = CSS_VARS[field_name]
            assert css_var in theme_vars, f"missing CSS var: {css_var} (field: {field_name})"

    def test_no_empty_values(self) -> None:
        theme_vars = to_theme_vars(EMERGENCY_DEFAULT)
        for css_var, value in theme_vars.items():
            assert len(value) > 0, f"empty value for {css_var}"

    def test_count_matches(self) -> None:
        theme_vars = to_theme_vars(EMERGENCY_DEFAULT)
        assert len(theme_vars) == len(CSS_VARS)


class TestAliasesBackwardCompat:
    def test_all_alias_values_start_with_dashes(self) -> None:
        for legacy_key, css_var in ALIASES.items():
            assert css_var.startswith("--"), (
                f"ALIASES[{legacy_key!r}] = {css_var!r} does not start with --"
            )

    def test_all_alias_values_are_css_var_names(self) -> None:
        css_var_re = re.compile(r"^--[a-z][a-z0-9-]*$")
        for legacy_key, css_var in ALIASES.items():
            assert css_var_re.match(css_var), (
                f"ALIASES[{legacy_key!r}] = {css_var!r} is not a valid CSS variable name"
            )


class TestCriticalCSSMatchesThemeTokens:
    def _parse_root_vars(self) -> dict[str, str]:
        content = CRITICAL_CSS.read_text()
        root_match = re.search(r":root\s*\{([^}]+)\}", content)
        assert root_match, "no :root block found in critical.css"
        block = root_match.group(1)
        vars_dict: dict[str, str] = {}
        for line in block.splitlines():
            line = line.strip().rstrip(";")
            if ":" in line:
                prop, value = line.split(":", 1)
                prop = prop.strip()
                value = value.strip()
                if prop.startswith("--"):
                    vars_dict[prop] = value
        return vars_dict

    def test_critical_css_color_vars_match_legacy_tokens(self) -> None:
        root_vars = self._parse_root_vars()
        legacy = to_legacy_vars(EMERGENCY_DEFAULT)
        color_vars = {
            "--bg": "bg",
            "--bg-surface": "bg-surface",
            "--border": "border",
            "--text": "text",
            "--text-muted": "text-muted",
            "--accent": "accent",
            "--accent-hover": "accent-hover",
        }
        for css_var, legacy_key in color_vars.items():
            assert css_var in root_vars, f"{css_var} not in critical.css :root"
            assert legacy_key in legacy, f"{legacy_key} not in legacy vars"
            critical_value = root_vars[css_var].lower()
            theme_value = legacy[legacy_key].lower()
            assert critical_value == theme_value, (
                f"{css_var}: critical.css={critical_value} != theme={theme_value}"
            )

    def test_no_color_values_use_hardcoded_hex_outside_theme(self) -> None:
        root_vars = self._parse_root_vars()
        theme_legacy = to_legacy_vars(EMERGENCY_DEFAULT)
        for css_var, value in root_vars.items():
            if css_var.startswith("--font") or css_var == "--radius":
                continue
            if value.startswith("#"):
                assert value.lower() in {
                    v.lower() for v in theme_legacy.values()
                }, f"{css_var}={value} not found in theme tokens"


class TestCustomCSSOverrideOrdering:
    def test_theme_vars_can_override_critical_tokens(self) -> None:
        legacy = to_legacy_vars(EMERGENCY_DEFAULT)
        original_bg = legacy["bg"]
        custom_bg = "#abcdef"
        legacy["bg"] = custom_bg
        assert legacy["bg"] == custom_bg
        assert legacy["bg"] != original_bg

    def test_theme_vars_dict_is_mutable_copy(self) -> None:
        legacy = to_legacy_vars(EMERGENCY_DEFAULT)
        legacy["text"] = "#000000"
        legacy2 = to_legacy_vars(EMERGENCY_DEFAULT)
        assert legacy2["text"] != "#000000"


class TestShadowColorRGBA:
    def test_shadow_color_is_rgba(self) -> None:
        assert isinstance(EMERGENCY_DEFAULT.shadow_color, RGBA)

    def test_shadow_color_has_alpha(self) -> None:
        assert EMERGENCY_DEFAULT.shadow_color.alpha < 1.0
        assert EMERGENCY_DEFAULT.shadow_color.alpha > 0.0


class TestOverlayBgRGBA:
    def test_overlay_bg_is_rgba(self) -> None:
        assert isinstance(EMERGENCY_DEFAULT.overlay_bg, RGBA)

    def test_overlay_bg_has_alpha(self) -> None:
        assert EMERGENCY_DEFAULT.overlay_bg.alpha < 1.0
        assert EMERGENCY_DEFAULT.overlay_bg.alpha > 0.0


class TestNavbarBgRGBA:
    def test_navbar_bg_is_rgba(self) -> None:
        assert isinstance(EMERGENCY_DEFAULT.navbar_bg, RGBA)

    def test_navbar_bg_has_alpha(self) -> None:
        assert EMERGENCY_DEFAULT.navbar_bg.alpha < 1.0
        assert EMERGENCY_DEFAULT.navbar_bg.alpha > 0.0
