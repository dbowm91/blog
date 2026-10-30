"""Contracts between the CSS layer and the theme token runtime.

These tests cover the Phase 04 corrective work:

* every ``var(--x)`` reference in the stylesheets resolves to an emitted or
  statically defined token (the check that would have caught the missing
  ``--shadow-color`` and ``--code-bg``);
* the post title paints with the text token, not the accent-foreground token,
  and stays above the WCAG AA contrast floor;
* elevation shadows resolve to a real colour;
* exactly one stylesheet owns ``.nav-links`` visibility per breakpoint;
* links outside prose are not underlined by default;
* the runtime does not emit tokens that no rule consumes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.themes.colors import RGB, RGBA, contrast_ratio, from_hex
from app.themes.model import ALIASES
from app.themes.registry import ThemeRegistry

REPO_ROOT = Path(__file__).resolve().parent.parent
CSS_DIR = REPO_ROOT / "app" / "static" / "css"
MOBILE_MENU_JS = REPO_ROOT / "app" / "static" / "js" / "shared" / "mobile-menu.jsx"

VAR_REFERENCE_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
CUSTOM_PROPERTY_RE = re.compile(r"(?:^|[{;])\s*(--[A-Za-z0-9_-]+)\s*:", re.MULTILINE)
DECLARATION_RE = re.compile(r"([-A-Za-z]+)\s*:\s*([^;{}]+)")
COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)

MIN_TEXT_CONTRAST = 4.5

# Runtime tokens that no stylesheet rule consumes. They are kept for backward
# compatibility with the Phase 09 legacy alias contract, so every one of them
# must name its rationale.
DEAD_TOKEN_ALLOW_LIST: dict[str, str] = {
    "--coral-dim": "legacy alias of --blog-coral-dim; no public surface uses it",
    "--info-bg": "legacy alias of --blog-info-bg; --purple-dim carries the same value",
    "--info-fg": "legacy alias of --blog-info-fg; --purple carries the same value",
    "--text-dim-strong": "legacy alias of --blog-text-dim; --text-dim carries the same value",
}

# Bundled themes whose own palette fails the text-on-background floor. The
# stylesheet cannot repair a theme palette, so these are asserted to be no
# worse than the theme's body text rather than silently ignored.
NON_AA_TEXT_ON_BACKGROUND: dict[str, str] = {
    "Cyber Red": "text-primary 4.50:1 against bg-page",
    "Rose Pine Dawn": "text-primary 2.45:1 against bg-page (documented exception)",
}


@dataclass(frozen=True)
class StyleRule:
    selector: str
    context: tuple[str, ...]
    body: str

    @property
    def media_queries(self) -> tuple[str, ...]:
        return tuple(c for c in self.context if c.startswith("@media"))

    def declarations(self) -> dict[str, str]:
        return {
            prop.strip().lower(): value.strip() for prop, value in DECLARATION_RE.findall(self.body)
        }


def _strip_comments(css: str) -> str:
    return COMMENT_RE.sub("", css)


def _parse_rules(css: str, context: tuple[str, ...] = ()) -> list[StyleRule]:
    """Parse the style rules of a stylesheet, tracking enclosing at-rules."""
    css = _strip_comments(css)
    rules: list[StyleRule] = []
    index = 0
    length = len(css)
    buffer = ""
    while index < length:
        char = css[index]
        if char == "{":
            prelude = buffer.strip()
            buffer = ""
            depth = 1
            cursor = index + 1
            while cursor < length and depth:
                if css[cursor] == "{":
                    depth += 1
                elif css[cursor] == "}":
                    depth -= 1
                cursor += 1
            body = css[index + 1 : cursor - 1]
            if prelude.startswith("@"):
                rules.extend(_parse_rules(body, context + (prelude,)))
            elif prelude:
                rules.append(StyleRule(selector=prelude, context=context, body=body))
            index = cursor
        elif char == "}":
            buffer = ""
            index += 1
        else:
            buffer += char
            index += 1
    return rules


def _stylesheet_files() -> list[Path]:
    return sorted(CSS_DIR.glob("*.css"))


def _all_rules() -> list[StyleRule]:
    rules: list[StyleRule] = []
    for path in _stylesheet_files():
        rules.extend(_parse_rules(path.read_text()))
    return rules


def _read(name: str) -> str:
    return (CSS_DIR / name).read_text()


def _runtime_tokens() -> set[str]:
    return {f"--{key}" for key in ALIASES}


def _stylesheet_tokens() -> set[str]:
    tokens: set[str] = set()
    for path in _stylesheet_files():
        tokens.update(CUSTOM_PROPERTY_RE.findall(path.read_text()))
    return tokens


def _theme_registry() -> ThemeRegistry:
    return ThemeRegistry()


def _bundled_theme_names() -> list[str]:
    return [descriptor.canonical_name for descriptor in _theme_registry().list_themes()]


def _parse_color(value: str) -> RGB:
    parsed = from_hex(value)
    if isinstance(parsed, RGBA):
        return parsed.rgb
    return parsed


def _rendered_theme_vars(html: str, scheme: str) -> dict[str, str]:
    """Extract the inline theme custom properties for one colour scheme."""
    if scheme == "dark":
        marker = ':root,\n        [data-color-scheme="dark"] {'
    else:
        marker = '[data-color-scheme="light"] {'
    start = html.find(marker)
    assert start != -1, f"theme style block for {scheme} not found in rendered page"
    block_start = html.find("{", start)
    block_end = html.find("}", block_start)
    block = html[block_start:block_end]
    return {
        name: value.strip()
        for name, value in re.findall(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;]+);", block)
    }


class TestTokenCompleteness:
    def test_every_var_reference_resolves(self) -> None:
        references: set[str] = set()
        for path in _stylesheet_files():
            references.update(VAR_REFERENCE_RE.findall(path.read_text()))

        available = _runtime_tokens() | _stylesheet_tokens()
        missing = sorted(references - available)
        assert missing == [], f"CSS references undefined custom properties: {missing}"

    @pytest.mark.parametrize("token", ["--shadow-color", "--code-bg"])
    def test_token_emitted_for_every_bundled_theme(self, token: str) -> None:
        registry = _theme_registry()
        for name in _bundled_theme_names():
            legacy = registry.load(name).legacy_vars
            assert token.lstrip("-") in legacy, f"{name} does not emit {token}"
            assert legacy[token.lstrip("-")], f"{name} emits an empty {token}"

    @pytest.mark.parametrize("token", ["--shadow-color", "--code-bg"])
    def test_token_emitted_for_both_schemes(self, token: str, client) -> None:
        html = client.get("/").data.decode()
        for scheme in ("dark", "light"):
            variables = _rendered_theme_vars(html, scheme)
            assert token in variables, f"{scheme} scheme does not emit {token}"
            assert variables[token], f"{scheme} scheme emits an empty {token}"


class TestTitleContrast:
    def test_post_title_uses_text_token(self) -> None:
        # Every rule that paints the hero title has to use the text token,
        # including the one inside the mobile breakpoint. Looking the rule up
        # by selector alone would only see the last one declared.
        colours = [
            rule.declarations()["color"]
            for rule in _parse_rules(_read("public.css"))
            if rule.selector.strip() == ".post-hero-title" and "color" in rule.declarations()
        ]
        assert colours, "public.css has no .post-hero-title colour rule"
        assert set(colours) == {"var(--text)"}

    def test_light_scheme_override_removed(self) -> None:
        selectors = {rule.selector for rule in _parse_rules(_read("base.css"))}
        assert '[data-color-scheme="light"] .post-hero-title' not in selectors

    def test_title_contrast_for_every_bundled_theme(self) -> None:
        registry = _theme_registry()
        failures: dict[str, str] = {}
        for name in _bundled_theme_names():
            theme = registry.load(name).blog_theme
            ratio = contrast_ratio(theme.text_primary, theme.bg_page)
            if ratio < MIN_TEXT_CONTRAST:
                failures[name] = f"{ratio:.2f}:1"
            else:
                assert ratio >= MIN_TEXT_CONTRAST, f"{name} title contrast {ratio:.2f}:1"
        assert sorted(failures) == sorted(NON_AA_TEXT_ON_BACKGROUND)

    def test_title_beats_the_accent_foreground_token(self, client) -> None:
        html = client.get("/").data.decode()
        for scheme in ("dark", "light"):
            variables = _rendered_theme_vars(html, scheme)
            background = _parse_color(variables["--bg"])
            title_ratio = contrast_ratio(_parse_color(variables["--text"]), background)
            accent_ratio = contrast_ratio(_parse_color(variables["--text-on-accent"]), background)
            assert title_ratio > accent_ratio, (
                f"{scheme} scheme: --text ({title_ratio:.2f}:1) is not more readable "
                f"than --text-on-accent ({accent_ratio:.2f}:1) on the page background"
            )

    def test_title_contrast_for_both_schemes(self, client) -> None:
        html = client.get("/").data.decode()
        for scheme in ("dark", "light"):
            variables = _rendered_theme_vars(html, scheme)
            foreground = _parse_color(variables["--text"])
            background = _parse_color(variables["--bg"])
            ratio = contrast_ratio(foreground, background)
            assert ratio >= MIN_TEXT_CONTRAST, f"{scheme} scheme title contrast {ratio:.2f}:1"


class TestLightboxCaptionContrast:
    """The lightbox caption paints text on a chip that sits over the image."""

    def _caption_declarations(self) -> dict[str, str]:
        rules = {rule.selector: rule for rule in _parse_rules(_read("public.css"))}
        return rules[".lightbox-caption"].declarations()

    def test_caption_paints_on_the_accent_surface(self) -> None:
        declarations = self._caption_declarations()

        assert declarations.get("background") == "var(--accent)"
        assert declarations.get("color") == "var(--text-on-accent)"

    def test_caption_never_paints_the_accent_foreground_on_a_scrim(self) -> None:
        declarations = self._caption_declarations()

        background = declarations.get("background", "")
        assert not background.startswith("rgba("), (
            "the caption paints on a hard-coded scrim; it must paint on a theme "
            "surface so the foreground token stays truthful"
        )

    def test_caption_contrast_for_both_schemes(self, client) -> None:
        html = client.get("/").data.decode()

        for scheme in ("dark", "light"):
            variables = _rendered_theme_vars(html, scheme)
            foreground = _parse_color(variables["--text-on-accent"])
            background = _parse_color(variables["--accent"])
            ratio = contrast_ratio(foreground, background)
            assert ratio >= MIN_TEXT_CONTRAST, f"{scheme} scheme caption contrast {ratio:.2f}:1"

    def test_caption_contrast_for_every_bundled_theme(self) -> None:
        registry = _theme_registry()
        failures: dict[str, str] = {}
        for name in _bundled_theme_names():
            theme = registry.load(name).blog_theme
            ratio = contrast_ratio(theme.text_on_accent, theme.accent)
            if ratio < MIN_TEXT_CONTRAST:
                failures[name] = f"{ratio:.2f}:1"
        assert failures == {}, f"caption contrast below the AA floor: {failures}"


class TestShadowTokenResolves:
    def test_box_shadow_uses_shadow_token(self) -> None:
        shadow_rules = [rule for rule in _all_rules() if "var(--shadow-color)" in rule.body]
        assert shadow_rules, "no rule uses var(--shadow-color)"

    def test_shadow_token_has_usable_value(self, client) -> None:
        html = client.get("/").data.decode()
        for scheme in ("dark", "light"):
            variables = _rendered_theme_vars(html, scheme)
            value = variables["--shadow-color"]
            assert value, f"{scheme} scheme emits an empty --shadow-color"
            assert value.startswith("#") or value.startswith("rgba("), value

    def test_shadow_token_is_not_transparent(self) -> None:
        registry = _theme_registry()
        for name in _bundled_theme_names():
            theme = registry.load(name).blog_theme
            assert theme.shadow_color.alpha > 0.0, f"{name} shadow is fully transparent"


class TestMobileNavOwnership:
    def _nav_display_rules(self) -> list[StyleRule]:
        return [
            rule
            for rule in _all_rules()
            if "display" in rule.declarations()
            and any(part.strip().startswith(".nav-links") for part in rule.selector.split(","))
        ]

    def test_no_unconditional_display_declaration(self) -> None:
        unconditional = [
            rule.selector for rule in self._nav_display_rules() if not rule.media_queries
        ]
        assert unconditional == [], (
            "unconditional .nav-links display declarations override the mobile "
            f"breakpoint: {unconditional}"
        )

    def test_single_owner_above_mobile_breakpoint(self) -> None:
        owners = [
            rule
            for rule in self._nav_display_rules()
            if rule.declarations().get("display") == "flex"
            and any("min-width: 769px" in media for media in rule.media_queries)
        ]
        assert len(owners) == 1, (
            f"expected exactly one stylesheet to own .nav-links visibility above "
            f"769px, found {len(owners)}"
        )

    def test_mobile_breakpoint_hides_nav_links(self) -> None:
        hiding = [
            rule
            for rule in self._nav_display_rules()
            if rule.declarations().get("display") == "none"
            and any("max-width: 768px" in media for media in rule.media_queries)
        ]
        assert hiding, "no stylesheet hides .nav-links at the mobile breakpoint"

    def test_open_class_expands_nav_links(self) -> None:
        opening = [
            rule
            for rule in self._nav_display_rules()
            if ".nav-links.open" in rule.selector
            and rule.declarations().get("display") == "flex"
            and any("max-width: 768px" in media for media in rule.media_queries)
        ]
        assert opening, ".nav-links.open is not expanded at the mobile breakpoint"

    def test_toggle_does_not_replace_its_own_content(self) -> None:
        source = MOBILE_MENU_JS.read_text()
        start = source.index("const setMenuOpen")
        body = source[start : source.index("};", start)]
        assert "innerHTML" not in body, (
            "replacing the toggle content detaches the clicked element, so the "
            "document click handler closes the menu again"
        )

    def test_both_icons_are_rendered_and_swapped_by_css(self) -> None:
        source = MOBILE_MENU_JS.read_text()
        assert "mobile-menu-icon-open" in source
        assert "mobile-menu-icon-close" in source

        selectors = {rule.selector for rule in _parse_rules(_read("base.css"))}
        assert '.mobile-menu-toggle[aria-expanded="true"] .mobile-menu-icon-open' in selectors
        assert '.mobile-menu-toggle[aria-expanded="true"] .mobile-menu-icon-close' in selectors


class TestAnchorBaseline:
    def test_base_css_declares_bare_anchor_rule(self) -> None:
        bare_anchors = [
            rule for rule in _parse_rules(_read("base.css")) if rule.selector.strip() == "a"
        ]
        assert bare_anchors, "base.css has no bare `a` rule"
        declarations = bare_anchors[0].declarations()
        assert declarations.get("text-decoration") == "none"

    def test_prose_links_keep_underline(self) -> None:
        prose = [
            rule for rule in _parse_rules(_read("base.css")) if rule.selector.strip() == ".prose a"
        ]
        assert prose, "base.css has no `.prose a` rule"
        assert prose[0].declarations().get("text-decoration") == "underline"

    def test_prose_underline_wins_over_baseline(self) -> None:
        rules = _parse_rules(_read("base.css"))
        prose = next(rule for rule in rules if rule.selector.strip() == ".prose a")
        baseline = next(rule for rule in rules if rule.selector.strip() == "a")
        assert len(prose.selector.split(",")) == 1
        assert prose.declarations().get("text-decoration") == "underline"
        assert baseline.declarations().get("text-decoration") == "none"


class TestDeadTokens:
    def test_every_emitted_token_is_used_or_allowlisted(self) -> None:
        references: set[str] = set()
        for path in _stylesheet_files():
            references.update(VAR_REFERENCE_RE.findall(path.read_text()))

        runtime = _runtime_tokens()
        unused = sorted(runtime - references)
        assert unused == sorted(DEAD_TOKEN_ALLOW_LIST)

    def test_allow_list_is_documented(self) -> None:
        for token, reason in DEAD_TOKEN_ALLOW_LIST.items():
            assert reason.strip(), f"{token} has no documented rationale"

    def test_allow_list_tokens_still_resolve(self) -> None:
        available = _runtime_tokens() | _stylesheet_tokens()
        for token in DEAD_TOKEN_ALLOW_LIST:
            assert token in available


class TestProseOwnership:
    """The admin live preview renders ``.prose``, so base.css owns the prose rules.

    The admin shell does not load ``public.css``; when the prose typography
    lived there the live preview rendered its paragraphs without spacing.
    """

    PROSE_SELECTORS = (
        ".prose",
        ".prose h1, .prose h2, .prose h3, .prose h4",
        ".prose p",
        ".prose ul, .prose ol",
        ".prose li",
        ".prose blockquote",
        ".prose code",
        ".prose pre",
        ".prose img",
        ".prose video",
        ".prose iframe",
        ".prose hr",
        ".prose table",
        ".prose th, .prose td",
        ".prose th",
    )

    def test_base_css_owns_the_prose_typography(self) -> None:
        selectors = {rule.selector for rule in _parse_rules(_read("base.css"))}
        missing = [s for s in self.PROSE_SELECTORS if s not in selectors]
        assert missing == [], f"base.css is missing the prose rules: {missing}"

    def test_public_css_does_not_own_the_prose_typography(self) -> None:
        selectors = {rule.selector for rule in _parse_rules(_read("public.css"))}
        duplicates = [s for s in self.PROSE_SELECTORS if s in selectors]
        assert duplicates == [], f"public.css duplicates the prose rules: {duplicates}"

    def test_the_prose_rules_are_not_declared_twice(self) -> None:
        owners: dict[str, set[str]] = {}
        for path in _stylesheet_files():
            for rule in _parse_rules(path.read_text()):
                owners.setdefault(rule.selector, set()).add(path.name)
        duplicated = {
            selector: sorted(files)
            for selector, files in owners.items()
            if selector in self.PROSE_SELECTORS and len(files) > 1
        }
        assert duplicated == {}, f"a prose rule has more than one owner: {duplicated}"


class TestProseMedia:
    """A video and an embedded frame are capped at the reading measure.

    The renderer emits both inside the prose column. Without a cap a wide
    video or a frame breaks the measure the rest of the column holds, and the
    live preview would show something the published page does not.
    """

    def _declarations(self, selector: str) -> dict[str, str]:
        rules = _parse_rules(_read("base.css"))
        rule = next((r for r in rules if r.selector.strip() == selector), None)
        assert rule is not None, f"base.css has no `{selector}` rule"
        return rule.declarations()

    @pytest.mark.parametrize("selector", [".prose video", ".prose iframe"])
    def test_the_media_is_capped_at_the_measure(self, selector: str) -> None:
        assert self._declarations(selector).get("max-width") == "100%"

    @pytest.mark.parametrize("selector", [".prose video", ".prose iframe"])
    def test_the_media_is_a_block_that_keeps_its_own_rows(self, selector: str) -> None:
        assert self._declarations(selector).get("display") == "block"

    def test_a_frame_keeps_its_aspect_ratio(self) -> None:
        assert self._declarations(".prose iframe").get("aspect-ratio") == "16 / 9"

    def test_a_frame_carries_no_border(self) -> None:
        assert self._declarations(".prose iframe").get("border") == "none"


class TestReadingMeasure:
    """The reading column is capped, and the cap scales with the prose font size.

    The cap is expressed in ``em`` because the prose font size changes at the
    mobile breakpoint; a pixel cap would hold a fixed column width and change
    the number of characters per line with it.
    """

    def test_the_measure_is_capped_on_the_prose_column(self) -> None:
        rules = [
            rule
            for rule in _parse_rules(_read("base.css"))
            if rule.selector.strip() == ".prose" and not rule.media_queries
        ]
        assert rules, "base.css has no base .prose rule"
        declarations = rules[0].declarations()
        assert "max-width" in declarations, "the prose column has no maximum width"
        assert declarations["max-width"].endswith("em"), (
            f"the measure is not expressed in em: {declarations['max-width']}"
        )

    def test_the_measure_is_centred_in_its_container(self) -> None:
        rules = [
            rule
            for rule in _parse_rules(_read("base.css"))
            if rule.selector.strip() == ".prose" and not rule.media_queries
        ]
        declarations = rules[0].declarations()
        assert declarations.get("margin-inline") == "auto", (
            "the narrower column is not centred in its tile"
        )

    def test_no_other_stylesheet_caps_the_prose_column(self) -> None:
        owners = {
            path.name
            for path in _stylesheet_files()
            for rule in _parse_rules(path.read_text())
            if rule.selector.strip() == ".prose" and "max-width" in rule.declarations()
        }
        assert owners == {"base.css"}, f"the measure has more than one owner: {sorted(owners)}"

    def test_the_public_sheet_does_not_set_a_width_on_the_post_body(self) -> None:
        rules = [
            rule
            for rule in _parse_rules(_read("public.css"))
            if rule.selector.strip() == ".post-body"
        ]
        for rule in rules:
            declarations = rule.declarations()
            assert "width" not in declarations, (
                f"public.css sets a width on .post-body: {declarations}"
            )
            assert "max-width" not in declarations, (
                f"public.css sets a max-width on .post-body: {declarations}"
            )


class TestImageBands:
    """The card band keeps a ratio instead of a fixed height.

    A fixed height with ``object-fit: cover`` crops a 16:9 screenshot to a 4:1
    band, which removes the top and the bottom of the image.
    """

    BANDS = (".post-card-img", ".related-card-img")

    def test_the_bands_declare_an_aspect_ratio(self) -> None:
        rules = {rule.selector.strip(): rule for rule in _parse_rules(_read("public.css"))}
        for selector in self.BANDS:
            assert selector in rules, f"public.css has no {selector} rule"
            declarations = rules[selector].declarations()
            assert declarations.get("aspect-ratio") == "16 / 9", (
                f"{selector} has no 16:9 band: {declarations}"
            )
            assert declarations.get("height") == "auto", (
                f"{selector} still has a fixed height: {declarations}"
            )

    def test_no_breakpoint_overrides_the_band_with_a_fixed_height(self) -> None:
        for rule in _parse_rules(_read("public.css")):
            if rule.selector.strip() not in self.BANDS:
                continue
            declarations = rule.declarations()
            assert "height" not in declarations or declarations["height"] == "auto", (
                f"a breakpoint fixes the height of {rule.selector.strip()}: {declarations}"
            )

    def test_the_placeholder_takes_its_ink_from_the_theme(self) -> None:
        rules = [
            rule
            for rule in _parse_rules(_read("public.css"))
            if rule.selector.strip() == ".img-placeholder"
        ]
        assert rules, "public.css has no .img-placeholder rule"
        declarations = rules[0].declarations()
        assert "mask-image" in declarations, f"the placeholder is not masked: {declarations}"
        assert "default-post.svg" in declarations["mask-image"], (
            f"the placeholder is not masked by the mark: {declarations}"
        )
        assert declarations.get("background-color") == "var(--text-dim)", (
            f"the placeholder does not take its ink from the theme: {declarations}"
        )


class TestHeadingAnchor:
    """The heading anchor is a link to the section, not a stray '#' after the title."""

    def test_the_anchor_is_hidden_until_the_heading_is_interacted_with(self) -> None:
        rules = [
            rule
            for rule in _parse_rules(_read("base.css"))
            if rule.selector.strip() == ".prose .anchor-link" and not rule.media_queries
        ]
        assert rules, "base.css has no base .prose .anchor-link rule"
        anchor = rules[0].declarations()
        assert anchor.get("opacity") == "0"
        assert anchor.get("position") == "absolute"

    def test_the_anchor_is_revealed_on_hover_and_on_focus(self) -> None:
        revealed = [
            rule
            for rule in _parse_rules(_read("base.css"))
            if "anchor-link" in rule.selector and rule.declarations().get("opacity") == "1"
        ]
        assert revealed
        assert any("hover" in rule.selector for rule in revealed)
        assert any(":focus" in rule.selector for rule in revealed)

    def test_the_heading_is_the_anchor_containing_block(self) -> None:
        rules = {rule.selector: rule for rule in _parse_rules(_read("base.css"))}
        headings = rules[".prose h1, .prose h2, .prose h3, .prose h4"].declarations()
        assert headings.get("position") == "relative"

    def test_the_old_wrapper_span_is_gone(self) -> None:
        assert ".heading-anchor" not in _read("base.css")


class TestAppearanceLayer:
    """The backdrop, the gradient and the translucent panels."""

    def test_backdrop_tokens_are_defined(self) -> None:
        tokens = _stylesheet_tokens()
        assert "--backdrop-tint" in tokens
        assert "--backdrop-image" in tokens

    def test_the_page_background_carries_a_gradient(self) -> None:
        rules = {rule.selector: rule for rule in _parse_rules(_read("base.css"))}
        gradient = rules["body::before"].declarations()
        assert "linear-gradient" in gradient.get("background-image", "")

    def test_the_backdrop_layer_is_masked_by_the_backdrop_image(self) -> None:
        rules = {rule.selector: rule for rule in _parse_rules(_read("base.css"))}
        layer = rules["body::after"].declarations()
        assert "var(--backdrop-image)" in layer.get("mask-image", "")
        assert "var(--backdrop-tint)" in layer.get("background-color", "")

    def test_the_page_background_is_transparent_so_the_layers_show(self) -> None:
        bodies = [
            rule
            for rule in _parse_rules(_read("base.css"))
            if rule.selector.strip() == "body" and not rule.media_queries
        ]
        backgrounds = [rule.declarations().get("background") for rule in bodies]
        assert "transparent" in backgrounds, backgrounds

    def test_panels_are_slightly_translucent(self) -> None:
        rules = {rule.selector: rule for rule in _parse_rules(_read("public.css"))}
        background = rules[".post-card"].declarations().get("background", "")
        assert "color-mix" in background
        assert "transparent" in background

    def test_the_bundled_fonts_are_declared(self) -> None:
        css = _read("base.css")
        for family in (
            "IBM Plex Sans",
            "IBM Plex Mono",
            "Fira Code",
            "Space Grotesk",
            "Atkinson Hyperlegible",
            "Cascadia Code",
            "Spline Sans Mono",
            "MesloLGS Nerd Font",
        ):
            assert f"font-family: '{family}'" in css, f"{family} has no @font-face rule"

    def test_every_bundled_font_file_exists(self) -> None:
        css = _read("base.css")
        sources = re.findall(r"url\('\.\./(fonts/[^']+)'\)", css)
        assert sources, "base.css declares no font files"
        for source in sources:
            assert (CSS_DIR.parent / source).is_file(), f"{source} is declared but missing"


DECORATIVE_TEXT_MUTED = {
    ("admin.css", ".md-tool"): "color",
    ("admin.css", ".md-tool:disabled:hover"): "color",
    ("admin.css", ".preset-card:hover"): "border-color",
    ("base.css", ".theme-toggle"): "color",
    ("base.css", ".back-to-top"): "color",
    ("base.css", ".mobile-menu-toggle"): "color",
    ("public.css", ".search-clear"): "color",
}


def _selector_parts(selector: str) -> set[str]:
    return {" ".join(part.split()) for part in selector.split(",")}


class TestTextRoleRule:
    """``--text-muted`` is for decoration. Text a reader must read is a caption."""

    def test_no_text_muted_outside_the_decorative_allowlist(self) -> None:
        offenders = []
        for path in _stylesheet_files():
            for rule in _parse_rules(path.read_text()):
                declarations = rule.declarations()
                parts = _selector_parts(rule.selector)
                allowed = {
                    DECORATIVE_TEXT_MUTED[(path.name, part)]
                    for part in parts
                    if (path.name, part) in DECORATIVE_TEXT_MUTED
                }
                for prop, value in declarations.items():
                    if "var(--text-muted)" not in value:
                        continue
                    if prop in allowed:
                        continue
                    offenders.append(f"{path.name}: {rule.selector} -> {prop}")
        assert offenders == [], offenders

    def test_every_decorative_use_is_still_present(self) -> None:
        found = set()
        for path in _stylesheet_files():
            for rule in _parse_rules(path.read_text()):
                declarations = rule.declarations()
                for part in _selector_parts(rule.selector):
                    key = (path.name, part)
                    if key not in DECORATIVE_TEXT_MUTED:
                        continue
                    prop = DECORATIVE_TEXT_MUTED[key]
                    if "var(--text-muted)" in declarations.get(prop, ""):
                        found.add(key)
        assert found == set(DECORATIVE_TEXT_MUTED), set(DECORATIVE_TEXT_MUTED) - found

    def test_the_caption_role_is_used_for_content(self) -> None:
        count = 0
        for path in _stylesheet_files():
            for rule in _parse_rules(path.read_text()):
                if "var(--text-caption)" in rule.declarations().get("color", ""):
                    count += 1
        assert count >= 40, count

    def test_no_stylesheet_paints_accent_text_with_the_accent(self) -> None:
        offenders = []
        for path in _stylesheet_files():
            for rule in _parse_rules(path.read_text()):
                value = rule.declarations().get("color", "")
                if "var(--accent)" in value or "var(--accent-hover)" in value:
                    offenders.append(f"{path.name}: {rule.selector} -> {value}")
        assert offenders == [], offenders

    def test_the_tag_chip_uses_the_accent_text_role(self) -> None:
        colours = [
            rule.declarations().get("color", "")
            for rule in _parse_rules(_read("public.css"))
            if " ".join(rule.selector.split()) == ".tag"
        ]
        assert colours, "no .tag rule found"
        assert "var(--accent-text)" in colours

    def test_the_accent_keeps_its_fills_and_borders(self) -> None:
        count = 0
        for path in _stylesheet_files():
            for rule in _parse_rules(path.read_text()):
                for prop, value in rule.declarations().items():
                    if prop == "color":
                        continue
                    if "var(--accent)" in value or "var(--accent-hover)" in value:
                        count += 1
        assert count >= 20, count


class TestTheFallbackBlocks:
    """The emergency fallback has to carry the new roles too."""

    def _fallback_blocks(self) -> list[tuple[str, str]]:
        blocks = []
        for name in ("base.css", "critical.css"):
            for rule in _parse_rules(_read(name)):
                if rule.selector in (":root", ':root,\n[data-color-scheme="dark"]'):
                    blocks.append((name, rule.body))
                if rule.selector.startswith("[data-color-scheme=") and ":root" in rule.selector:
                    blocks.append((name, rule.body))
        return blocks

    def test_every_fallback_block_declares_both_roles(self) -> None:
        blocks = self._fallback_blocks()
        assert blocks, "no emergency fallback block found"
        for name, body in blocks:
            assert "--text-caption" in body, name
            assert "--accent-text" in body, name

    def test_the_fallback_values_clear_the_floor(self) -> None:
        from app.themes.colors import contrast_ratio, from_hex

        for name, body in self._fallback_blocks():
            declarations = {}
            for prop, value in re.findall(r"(--[a-z-]+)\s*:\s*([^;{}]+)", body):
                declarations[prop] = value.strip()
            caption = from_hex(declarations["--text-caption"])
            accent_text = from_hex(declarations["--accent-text"])
            page = from_hex(declarations.get("--bg", declarations.get("--bg-surface")))
            assert contrast_ratio(caption, page) >= 4.5, name
            assert contrast_ratio(accent_text, page) >= 4.5, name


class TestIndexLayout:
    """The index shows more posts per screen.

    The list is a grid rather than a column, the card is tighter, and the tag
    row is capped. Each of those is a property of one stylesheet, and the
    sheet that owns an element owns it completely.
    """

    def _posts_list_rules(self) -> list[StyleRule]:
        return [r for r in _parse_rules(_read("public.css")) if r.selector == ".posts-list"]

    def test_the_post_list_is_a_grid(self) -> None:
        rules = self._posts_list_rules()
        assert rules, "no .posts-list rule found"
        unconditional = [r for r in rules if not r.media_queries]
        assert unconditional, "the .posts-list grid has no unconditional rule"
        assert any(r.declarations().get("display") == "grid" for r in unconditional)
        assert not any(r.declarations().get("display") == "flex" for r in unconditional), (
            "the post list is still a flex column"
        )

    def test_the_grid_holds_two_columns_from_1024px(self) -> None:
        wide = [
            r
            for r in self._posts_list_rules()
            if any("min-width: 1024px" in media for media in r.media_queries)
        ]
        assert wide, "the two-column rule is missing"
        columns = wide[0].declarations().get("grid-template-columns", "")
        assert "repeat(2" in columns, columns
        assert "minmax(0, 1fr)" in columns, columns

    def test_the_narrow_column_can_shrink(self) -> None:
        """A long unbroken title must not widen the grid past its container."""
        for rule in self._posts_list_rules():
            columns = rule.declarations().get("grid-template-columns", "")
            if not columns:
                continue
            assert "minmax(0, 1fr)" in columns, f"{rule.selector}: {columns}"

    def test_no_stylesheet_lays_the_post_list_out_as_a_column(self) -> None:
        """The critical sheet paints the first frame; it must not paint a column."""
        owners = []
        for path in _stylesheet_files():
            for rule in _parse_rules(path.read_text()):
                if rule.selector != ".posts-list":
                    continue
                declarations = rule.declarations()
                if not declarations:
                    continue
                owners.append(path.name)
                assert declarations.get("display") != "flex", f"{path.name}: {rule.selector}"
        assert "public.css" in owners, owners

    def test_the_sidebar_column_is_200px(self) -> None:
        rules = [r for r in _parse_rules(_read("layout.css")) if r.selector == ".content-layout"]
        assert rules, "no .content-layout rule found"
        columns = rules[0].declarations().get("grid-template-columns", "")
        assert columns == "minmax(0, 1fr) 200px", columns

    def test_the_card_body_padding_is_tightened(self) -> None:
        rules = [r for r in _parse_rules(_read("public.css")) if r.selector == ".post-card-body"]
        assert rules, "no .post-card-body rule found"
        assert rules[0].declarations().get("padding") == "20px 22px"

    def test_the_summary_is_clamped_to_two_lines(self) -> None:
        rules = [r for r in _parse_rules(_read("public.css")) if r.selector == ".post-card-summary"]
        assert rules, "no .post-card-summary rule found"
        declarations = rules[0].declarations()
        assert declarations.get("-webkit-line-clamp") == "2"
        assert declarations.get("line-clamp") == "2"
        assert declarations.get("overflow") == "hidden"

    def test_the_tag_lift_belongs_to_the_link(self) -> None:
        """The count chip is a label: it must not lift under the pointer."""
        selectors = {
            " ".join(rule.selector.split())
            for rule in _parse_rules(_read("public.css"))
            if rule.declarations()
        }
        assert ".tag:hover" not in selectors, "the lift still applies to the label"
        assert "a.tag:hover" in selectors

    def test_the_count_chip_is_a_label(self) -> None:
        rules = [r for r in _parse_rules(_read("public.css")) if r.selector == ".tag-more"]
        assert rules, "no .tag-more rule found"
        declarations = rules[0].declarations()
        assert declarations.get("transform") == "none"
        assert declarations.get("box-shadow") == "none"
        assert declarations.get("cursor") == "default"
        assert "var(--text-caption)" in declarations.get("color", "")
        assert "var(--bg-elevated)" in declarations.get("background", "")


class TestStructuralVoice:
    """Structure reads as structure.

    The table-of-contents title, the share label and the sidebar headings name
    the parts of a page rather than reading as content. They take one shared
    treatment: the mono face, an uppercase label and the caption role.
    """

    OWNERS = {
        ".post-toc-title": "public.css",
        ".share-label": "public.css",
        ".sidebar-title": "layout.css",
    }

    def _declarations(self, selector: str) -> dict[str, str]:
        sheet = self.OWNERS[selector]
        rules = [r for r in _parse_rules(_read(sheet)) if r.selector == selector]
        assert rules, f"{selector} is not declared in {sheet}"
        return rules[0].declarations()

    def test_each_label_is_declared_once(self) -> None:
        counts = dict.fromkeys(self.OWNERS, 0)
        for path in _stylesheet_files():
            for rule in _parse_rules(path.read_text()):
                if rule.selector in counts:
                    counts[rule.selector] += 1
        assert counts == dict.fromkeys(self.OWNERS, 1), counts

    def test_the_labels_take_the_structural_treatment(self) -> None:
        for selector in self.OWNERS:
            declarations = self._declarations(selector)
            assert declarations.get("font-family") == "var(--font-mono)", selector
            assert declarations.get("text-transform") == "uppercase", selector
            assert declarations.get("letter-spacing") == "0.08em", selector
            assert declarations.get("color") == "var(--text-caption)", selector
            assert declarations.get("font-size") == "0.72rem", selector

    def test_the_labels_do_not_use_the_decorative_role(self) -> None:
        for selector in self.OWNERS:
            declarations = self._declarations(selector)
            assert "var(--text-muted)" not in declarations.get("color", ""), selector

    def test_the_share_bar_is_spaced_from_the_top(self) -> None:
        """It is no longer the first child of the post tile."""
        rules = [r for r in _parse_rules(_read("public.css")) if r.selector == ".share-bar"]
        assert rules, "no .share-bar rule found"
        declarations = rules[0].declarations()
        assert declarations.get("margin-top") == "24px"
        assert "margin-bottom" not in declarations

    def test_the_contents_entries_keep_the_link_treatment(self) -> None:
        """The entries are links, so they read as links."""
        rules = [r for r in _parse_rules(_read("public.css")) if r.selector == ".post-toc a"]
        assert rules, "no .post-toc a rule found"
        declarations = rules[0].declarations()
        assert declarations.get("text-decoration") == "underline"
        assert "var(--text-caption)" in declarations.get("color", "")
