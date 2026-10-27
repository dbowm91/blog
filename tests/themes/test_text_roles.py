"""Contracts for the two derived text roles.

``--text-muted`` was doing two jobs at once: it styled the separators and the
disabled states, and it styled the text a reader has to read. The first is
decoration. The second is content, and in most of the bundled catalogue it
measured below the floor for the size it was used at.

The catalogue now carries two derived roles:

``text_caption``
    The muted colour moved toward the primary colour until it clears 4.5:1 on
    the page, on a card and on an elevated panel.

``accent_text``
    The accent moved until it clears 4.5:1 on the chip it tints.

Both are derived, never authored, so a theme cannot opt out of them and a
theme cannot hand-author a caption that the gate then has to trust.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.themes.colors import RGBA, alpha_composite, contrast_ratio
from app.themes.model import ALIASES, CSS_VARS, BlogTheme
from app.themes.registry import ThemeRegistry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AUTHORING_DIR = REPO_ROOT / "themes"
BUNDLED_DIR = REPO_ROOT / "app" / "themes" / "bundled"

CONTRAST_FLOOR = 4.5

# The eight themes whose code surface was indistinguishable from the card
# surface. Phase 02 repaired them in the catalogue.
REPAIRED_CODE_SURFACE = (
    "Flexor Dark",
    "Noctis Lilac",
    "Tokyo Night Storm",
    "VESPER",
    "Dark Green",
    "Rose Pine Dawn",
    "bam",
    "vanimo",
)


@pytest.fixture(scope="module")
def registry() -> ThemeRegistry:
    return ThemeRegistry()


@pytest.fixture(scope="module")
def theme_names(registry: ThemeRegistry) -> list[str]:
    return [descriptor.canonical_name for descriptor in registry.list_themes()]


@pytest.fixture(scope="module")
def themes(registry: ThemeRegistry, theme_names: list[str]) -> dict[str, BlogTheme]:
    return {name: registry.load(name).blog_theme for name in theme_names}


def _chip(accent: BlogTheme, surface) -> object:
    return alpha_composite(RGBA(accent.red, accent.green, accent.blue, 0.10), surface)


class TestTheCaptionRole:
    def test_every_bundled_theme_clears_the_floor(self, themes: dict[str, BlogTheme]) -> None:
        failures = []
        for name, theme in themes.items():
            for surface in (theme.bg_page, theme.surface_default, theme.surface_elevated):
                ratio = contrast_ratio(theme.text_caption, surface)
                if ratio < CONTRAST_FLOOR:
                    failures.append((name, round(ratio, 2)))
        assert failures == [], failures

    def test_the_emergency_default_clears_the_floor(self) -> None:
        from app.themes.model import EMERGENCY_DEFAULT

        theme = EMERGENCY_DEFAULT
        for surface in (theme.bg_page, theme.surface_default, theme.surface_elevated):
            assert contrast_ratio(theme.text_caption, surface) >= CONTRAST_FLOOR

    def test_the_caption_is_never_worse_than_the_muted_it_replaces(
        self, themes: dict[str, BlogTheme]
    ) -> None:
        for name, theme in themes.items():
            for surface in (theme.bg_page, theme.surface_default, theme.surface_elevated):
                assert contrast_ratio(theme.text_caption, surface) >= contrast_ratio(
                    theme.text_muted, surface
                ), name

    def test_a_theme_that_already_clears_the_floor_keeps_its_muted(
        self, themes: dict[str, BlogTheme]
    ) -> None:
        for name, theme in themes.items():
            surfaces = (theme.bg_page, theme.surface_default, theme.surface_elevated)
            if all(
                contrast_ratio(theme.text_muted, surface) >= CONTRAST_FLOOR for surface in surfaces
            ):
                assert theme.text_caption == theme.text_muted, name

    def test_no_theme_hand_authored_a_caption(self, theme_names: list[str]) -> None:
        """The caption is derived, so no theme file declares one."""
        for name in theme_names:
            for directory in (AUTHORING_DIR, BUNDLED_DIR):
                path = directory / f"{name}.toml"
                if path.exists():
                    text = path.read_text()
                    assert "text_caption" not in text, path
                    assert "accent_text" not in text, path


class TestTheAccentTextRole:
    def test_every_bundled_theme_clears_the_floor_on_the_chip(
        self, themes: dict[str, BlogTheme]
    ) -> None:
        failures = []
        for name, theme in themes.items():
            for surface in (theme.bg_page, theme.surface_default, theme.surface_elevated):
                chip = _chip(theme.accent_text, surface)
                ratio = contrast_ratio(theme.accent_text, chip)
                if ratio < CONTRAST_FLOOR:
                    failures.append((name, round(ratio, 2)))
        assert failures == [], failures

    def test_the_accent_text_is_never_worse_than_the_accent(
        self, themes: dict[str, BlogTheme]
    ) -> None:
        for name, theme in themes.items():
            for surface in (theme.bg_page, theme.surface_default, theme.surface_elevated):
                assert contrast_ratio(theme.accent_text, surface) >= contrast_ratio(
                    theme.accent, surface
                ), name

    def test_the_emergency_default_clears_the_floor(self) -> None:
        from app.themes.model import EMERGENCY_DEFAULT

        theme = EMERGENCY_DEFAULT
        for surface in (theme.bg_page, theme.surface_default, theme.surface_elevated):
            assert contrast_ratio(theme.accent_text, _chip(theme.accent_text, surface)) >= (
                CONTRAST_FLOOR
            )


class TestTheTokenCounts:
    def test_the_model_carries_the_two_new_roles(self) -> None:
        import dataclasses

        fields = dataclasses.fields(BlogTheme)
        assert len(fields) == 52
        assert sum(1 for f in fields if f.type == "RGB") == 43
        assert sum(1 for f in fields if f.type == "RGBA") == 9

    def test_the_css_variables_carry_the_two_new_roles(self) -> None:
        assert len(CSS_VARS) == 52
        assert CSS_VARS["text_caption"] == "--blog-text-caption"
        assert CSS_VARS["accent_text"] == "--blog-accent-text"

    def test_the_aliases_carry_the_two_new_roles(self) -> None:
        assert len(ALIASES) == 40
        assert ALIASES["text-caption"] == "--blog-text-caption"
        assert ALIASES["accent-text"] == "--blog-accent-text"

    def test_the_theme_service_emits_both_roles(self, themes: dict[str, BlogTheme]) -> None:
        from app.themes.translate import to_legacy_vars

        vars_ = to_legacy_vars(next(iter(themes.values())))
        assert "text-caption" in vars_
        assert "accent-text" in vars_


class TestTheCodeSurface:
    def test_every_bundled_theme_distinguishes_its_code_surface(
        self, themes: dict[str, BlogTheme]
    ) -> None:
        failures = []
        for name, theme in themes.items():
            delta = max(
                abs(getattr(theme.code_bg, channel) - getattr(theme.surface_default, channel))
                for channel in ("red", "green", "blue")
            )
            if delta < 8:
                failures.append((name, delta))
        assert failures == [], failures

    def test_the_repaired_themes_now_differ(self, themes: dict[str, BlogTheme]) -> None:
        for name in REPAIRED_CODE_SURFACE:
            theme = themes[name]
            assert theme.code_bg != theme.surface_default, name

    def test_the_code_text_shortfall_is_a_declared_exception(
        self, themes: dict[str, BlogTheme]
    ) -> None:
        """The code text is the primary text.

        A theme whose code text falls below the floor on its own code surface
        has to declare that failure in the exception manifest, so the gate
        reports it instead of the theme silently shipping it.
        """
        import json

        manifest = json.loads(
            (REPO_ROOT / "app" / "themes" / "ACCESSIBILITY_EXCEPTIONS.json").read_text()
        )
        declared = {
            name
            for name, entry in manifest["exceptions"].items()
            if any(
                pair["token"] == "--blog-code-text" and "code-bg" in pair["description"]
                for pair in entry["pairs"]
            )
        }
        for name, theme in themes.items():
            ratio = contrast_ratio(theme.code_text, theme.code_bg)
            if ratio < CONTRAST_FLOOR:
                assert name in declared, f"{name} is {ratio:.2f}:1 and not declared"
            else:
                assert name not in declared, f"{name} declares a failure it no longer has"


class TestTheThemeCatalogue:
    def test_the_authoring_and_runtime_copies_are_byte_identical(
        self, theme_names: list[str]
    ) -> None:
        for name in theme_names:
            authoring = AUTHORING_DIR / f"{name}.toml"
            bundled = BUNDLED_DIR / f"{name}.toml"
            assert authoring.exists(), authoring
            assert bundled.exists(), bundled
            assert authoring.read_bytes() == bundled.read_bytes(), name


class TestTheGate:
    def test_the_gate_has_the_mandatory_caption_checks(self) -> None:
        from app.themes.diagnostics import _CONTRAST_PAIRS, Severity

        pairs = {
            (token, surface): (floor, severity)
            for token, surface, _label, floor, severity, _note in _CONTRAST_PAIRS
        }
        for surface in ("bg_page", "surface_default", "surface_elevated"):
            entry = pairs.get(("text_caption", surface))
            assert entry is not None, surface
            floor, severity = entry
            assert floor == CONTRAST_FLOOR
            assert severity == Severity.MANDATORY

    def test_the_gate_has_the_mandatory_accent_text_check(self) -> None:
        from app.themes.diagnostics import _CONTRAST_PAIRS, Severity

        pairs = {
            (token, surface): (floor, severity)
            for token, surface, _label, floor, severity, _note in _CONTRAST_PAIRS
        }
        entry = pairs.get(("accent_text", "surface_default"))
        assert entry is not None
        floor, severity = entry
        assert floor == CONTRAST_FLOOR
        assert severity == Severity.MANDATORY

    def test_the_exception_manifest_is_unchanged(self) -> None:
        """Phase 02 adds checks that pass everywhere, so the manifest stands."""
        import json

        manifest = json.loads(
            (REPO_ROOT / "app" / "themes" / "ACCESSIBILITY_EXCEPTIONS.json").read_text()
        )
        assert manifest["schema_version"] == 2
        assert len(manifest["exceptions"]) == 45
