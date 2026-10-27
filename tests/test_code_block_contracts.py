"""Contracts for the code block: its surface, its palette and its settings.

The code block used to be a paragraph in a font. It had no surface of its own,
its palette was a vendored third-party stylesheet, its copy button was styled
by one of those vendored stylesheets and by no other, and the highlighter that
was supposed to colour it never ran.

These tests pin the replacement: one theme-token stylesheet, one owner for the
code block's layout, one owner for the copy button, and a setting that no
longer exists.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CSS_DIR = REPO_ROOT / "app" / "static" / "css"
JS_DIR = REPO_ROOT / "app" / "static" / "js"

HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
RGB_LITERAL_RE = re.compile(r"\brgba?\(")


def _read(name: str) -> str:
    return (CSS_DIR / name).read_text()


def _rule_blocks(css: str) -> list[tuple[str, str]]:
    """Return (selector, body) for every rule in a stylesheet."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    blocks: list[tuple[str, str]] = []
    index = 0
    while index < len(css):
        start = css.find("{", index)
        if start == -1:
            break
        depth = 1
        cursor = start + 1
        while cursor < len(css) and depth:
            if css[cursor] == "{":
                depth += 1
            elif css[cursor] == "}":
                depth -= 1
            cursor += 1
        blocks.append((css[index:start].strip(), css[start + 1 : cursor - 1]))
        index = cursor
    return blocks


class TestTheCodeBlockHasItsOwnSurface:
    def test_the_block_paints_the_code_surface(self) -> None:
        blocks = [
            body for selector, body in _rule_blocks(_read("base.css")) if selector == ".prose pre"
        ]
        assert blocks, "base.css has no .prose pre rule"
        assert any("var(--code-bg)" in body for body in blocks), (
            "the code block does not paint the theme's code surface"
        )

    def test_no_scheme_override_paints_the_block_with_the_card_surface(self) -> None:
        for selector, body in _rule_blocks(_read("base.css")):
            if selector.startswith('[data-color-scheme="light"]') and "pre" in selector:
                assert "var(--bg-surface)" not in body, (
                    f"{selector} paints the code block with the card surface"
                )

    def test_the_block_is_the_positioning_context_of_its_copy_button(self) -> None:
        blocks = [
            body for selector, body in _rule_blocks(_read("base.css")) if selector == ".prose pre"
        ]
        assert any("position: relative" in body for body in blocks)


class TestTheInlineChipDoesNotLeak:
    def test_the_light_scheme_override_skips_code_inside_a_block(self) -> None:
        selectors = {
            selector
            for selector, _ in _rule_blocks(_read("base.css"))
            if selector.startswith('[data-color-scheme="light"]')
        }
        assert '[data-color-scheme="light"] .prose :not(pre) > code' in selectors
        assert '[data-color-scheme="light"] .prose code' not in selectors


class TestOnePalette:
    def test_the_vendored_palettes_are_gone(self) -> None:
        remaining = sorted(p.name for p in CSS_DIR.glob("prism-*.css"))
        assert remaining == [], f"vendored Prism palettes are still present: {remaining}"

    def test_the_prism_stylesheet_uses_no_colour_literal(self) -> None:
        css = _read("prism.css")
        assert HEX_COLOR_RE.search(css) is None, "prism.css contains a hex colour"
        assert RGB_LITERAL_RE.search(css) is None, "prism.css contains an rgb() literal"

    def test_the_prism_stylesheet_uses_theme_tokens(self) -> None:
        css = _read("prism.css")
        assert "var(--" in css
        for token in re.findall(r"var\((--[A-Za-z0-9_-]+)", css):
            assert token in {
                "--text",
                "--text-dim",
                "--text-muted",
                "--text-caption",
                "--accent",
                "--accent-text",
                "--green",
                "--red",
                "--yellow",
            }, f"prism.css uses an unexpected token: {token}"

    def test_the_token_classes_are_still_covered(self) -> None:
        css = _read("prism.css")
        for token_class in ("comment", "keyword", "string", "number", "deleted"):
            assert f".token.{token_class}" in css, f"prism.css does not style .{token_class}"


class TestOneOwnerForTheCopyButton:
    def test_base_css_styles_the_copy_button(self) -> None:
        selectors = {selector for selector, _ in _rule_blocks(_read("base.css"))}
        assert ".copy-code-btn" in selectors

    def test_no_vendored_palette_styles_the_copy_button(self) -> None:
        offenders = [
            path.name for path in CSS_DIR.glob("prism-*.css") if "copy-code-btn" in path.read_text()
        ]
        assert offenders == [], f"a vendored palette styles the copy button: {offenders}"

    def test_the_copy_button_uses_theme_tokens_only(self) -> None:
        body = next(
            body
            for selector, body in _rule_blocks(_read("base.css"))
            if selector == ".copy-code-btn"
        )
        assert HEX_COLOR_RE.search(body) is None


class TestTheSettingIsGone:
    def test_the_model_has_no_syntax_theme(self) -> None:
        from app.models import SiteSettings

        assert not hasattr(SiteSettings, "syntax_theme")

    def test_the_public_page_has_no_syntax_theme_attribute(self, client) -> None:
        html = client.get("/").data.decode()
        assert "data-syntax-theme" not in html

    def test_the_public_page_links_the_one_prism_stylesheet(self, client) -> None:
        html = client.get("/").data.decode()
        assert "prism.css" in html
        assert "syntax_theme" not in html

    def test_the_admin_settings_page_has_no_syntax_theme_select(self, authenticated_client) -> None:
        html = authenticated_client.get("/admin/settings").data.decode()
        assert "Syntax Highlighting Theme" not in html
        assert 'name="syntax_theme"' not in html


class TestTheHighlighterIsBuilt:
    def test_the_hand_assembled_bundle_is_gone(self) -> None:
        assert not (JS_DIR / "prism-languages.js").exists()
        assert not (JS_DIR / "prism.min.js").exists()

    def test_the_bundle_is_a_vite_entry(self) -> None:
        source = (JS_DIR / "prism.js").read_text()
        assert "from 'prismjs'" in source

    def test_the_vite_config_has_the_prism_entry(self) -> None:
        config = (REPO_ROOT / "vite.config.js").read_text()
        assert "app/static/js/prism.js" in config

    def test_the_prism_dependency_is_declared(self) -> None:
        package = json.loads((REPO_ROOT / "package.json").read_text())
        assert "prismjs" in package.get("devDependencies", {})

    def test_the_loader_does_not_inject_a_second_stylesheet(self) -> None:
        source = (JS_DIR / "main.js").read_text()
        start = source.index("function loadPrismIfNeeded")
        body = source[start : source.index("\n}", start)]
        assert "rel = 'stylesheet'" not in body
        assert "prismLangsUrl" not in body
        assert "dataset.prismJsUrl" in body

    def test_the_prism_data_attributes_are_the_only_ones(self) -> None:
        for rel in (
            "app/templates/base.html",
            "app/templates/admin/base.html",
            "app/templates/admin/login_base.html",
        ):
            html = (REPO_ROOT / rel).read_text()
            assert "data-prism-css-url" not in html, rel
            assert "data-prism-langs-url" not in html, rel
            assert "data-prism-js-url" in html, rel


class TestTheLineNumberingSurvivesHighlighting:
    """The highlighter replaces the code element's content.

    The renderer wraps every line in a span and the stylesheet numbers those
    spans with a CSS counter. The highlighter therefore has to put the
    renderer's line structure back, or the numbering disappears. It restores
    the structure the renderer produced; it does not produce a second one.
    """

    def test_the_highlighter_does_not_create_the_line_spans(self) -> None:
        for path in (JS_DIR / "shared" / "prism-blocks.js", JS_DIR / "prism.js"):
            assert "code-line" not in path.read_text(), path

    def test_the_highlighter_restores_the_rendered_line_structure(self) -> None:
        source = (JS_DIR / "shared" / "prism-blocks.js").read_text()
        assert "splitHighlightedLines" in source
        assert "code.children" in source
        assert "line.innerHTML = fragments[index]" in source

    def test_the_highlighter_keeps_the_line_count(self) -> None:
        source = (JS_DIR / "shared" / "prism-blocks.js").read_text()
        assert "split('\\n')" in source

    def test_the_highlighter_is_called_with_manual_mode(self) -> None:
        source = (JS_DIR / "prism.js").read_text()
        assert "Prism.manual = true" in source
        assert "highlightCodeBlocks(Prism)" in source


@pytest.mark.parametrize("name", ["prism.css"])
def test_the_stylesheet_exists(name: str) -> None:
    assert (CSS_DIR / name).exists()
