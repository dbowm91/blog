"""Browser-level checks for the code block.

The highlighter is client-side, so these tests assert what the browser
actually does: that the bundle loads, that the block is tokenised, that the
copy button appears and copies, that the inline-code chip does not leak into
the block, and that the block has a surface of its own.

The line numbering is produced by a CSS counter over the per-line spans the
renderer writes. The highlighter replaces the code element's content, so these
tests also pin that the numbering survives it.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.e2e.contrast_helpers import MEASURE_JS, contrast_ratio, parse_rgb

DIST_DIR = Path(__file__).resolve().parents[2] / "app" / "static" / "dist"
MANIFEST_PATH = DIST_DIR / ".vite" / "manifest.json"

requires_frontend_build = pytest.mark.skipif(
    not MANIFEST_PATH.exists(),
    reason="frontend bundle not built (run `npm run build`)",
)

CODE_SOURCE = 'def hello(name):\n    # a comment\n    return f"hi {name}"\n'
LINE_COUNT = len(CODE_SOURCE.rstrip("\n").split("\n"))

MULTILINE_SOURCE = 'value = """\nfirst line\nsecond line\n"""\n'


def _measure(page, selector: str) -> tuple[float, str, str]:
    result = page.evaluate(MEASURE_JS, selector)
    assert result is not None, f"{selector} is not on the page"
    ratio = contrast_ratio(parse_rgb(result["color"]), result["background"])
    return ratio, result["fontSize"], result["fontWeight"]


def _make_post(app, title: str, slug: str, body: str) -> str:
    from app.extensions import db
    from app.models import Post
    from app.utils import utc_now

    with app.app_context():
        post = Post(
            title=title,
            slug=slug,
            body=body,
            published=True,
            published_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()
        return post.slug


def _open(context, app_server, slug: str, scheme: str):
    page = context.new_page()
    page.add_init_script(
        f"try {{ localStorage.setItem('blog-color-scheme', '{scheme}'); }} catch (e) {{}}"
    )
    page.goto(f"{app_server}/post/{slug}", wait_until="networkidle")
    return page


@requires_frontend_build
def test_the_highlighter_loads_and_tokenises(browser, app_server, app) -> None:
    _make_post(app, "Prism Loads", "prism-loads", f"```python\n{CODE_SOURCE}```")

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = _open(context, app_server, "prism-loads", "dark")
        page.wait_for_selector(".prose pre .token.keyword", timeout=15000)

        state = page.evaluate(
            """() => ({
              prism: typeof window.Prism,
              python: !!(window.Prism && window.Prism.languages.python),
              tokens: document.querySelectorAll('.token').length,
              keywords: document.querySelectorAll('.token.keyword').length,
              preClass: document.querySelector('.prose pre').className,
              codeClass: document.querySelector('.prose pre code').className,
            })"""
        )

        assert state["prism"] == "object"
        assert state["python"] is True
        assert state["tokens"] > 0
        assert state["keywords"] > 0
        assert "language-python" in state["preClass"]
        assert "language-python" in state["codeClass"]
    finally:
        context.close()


@requires_frontend_build
def test_the_copy_button_appears_and_copies(browser, app_server, app) -> None:
    _make_post(app, "Prism Copy", "prism-copy", f"```python\n{CODE_SOURCE}```")

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        context.grant_permissions(["clipboard-read", "clipboard-write"], origin=app_server)
        page = _open(context, app_server, "prism-copy", "dark")
        page.wait_for_selector(".prose pre .copy-code-btn", timeout=15000)
        page.locator(".prose pre").first.hover()
        page.wait_for_timeout(250)

        button = page.locator(".prose pre .copy-code-btn").first
        box = button.bounding_box()
        assert box is not None
        assert box["width"] > 0 and box["height"] > 0

        assert button.inner_text().strip() == "Copy"
        button.click()
        page.wait_for_timeout(400)
        assert button.inner_text().strip() == "Copied!"

        clipboard = page.evaluate("() => navigator.clipboard.readText()")
        assert clipboard == CODE_SOURCE
    finally:
        context.close()


@requires_frontend_build
@pytest.mark.parametrize("scheme", ["dark", "light"])
def test_the_inline_chip_does_not_leak_into_the_block(browser, app_server, app, scheme) -> None:
    _make_post(app, f"Prism Chip {scheme}", f"prism-chip-{scheme}", f"```python\n{CODE_SOURCE}```")

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = _open(context, app_server, f"prism-chip-{scheme}", scheme)
        page.wait_for_selector(".prose pre", timeout=15000)

        chip = page.evaluate(
            "() => getComputedStyle(document.querySelector('.prose pre code')).backgroundColor"
        )
        assert chip in ("rgba(0, 0, 0, 0)", "transparent"), (
            f"{scheme} scheme: the inline-code chip paints inside the block ({chip})"
        )
    finally:
        context.close()


@requires_frontend_build
@pytest.mark.parametrize("scheme", ["dark", "light"])
def test_the_block_has_a_surface_of_its_own(browser, app_server, app, scheme) -> None:
    _make_post(
        app, f"Prism Surface {scheme}", f"prism-surface-{scheme}", f"```python\n{CODE_SOURCE}```"
    )

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = _open(context, app_server, f"prism-surface-{scheme}", scheme)
        page.wait_for_selector(".prose pre", timeout=15000)

        block = page.evaluate(MEASURE_JS, ".prose pre")
        tile = page.evaluate(MEASURE_JS, ".post-full")

        assert block is not None
        assert tile is not None, "the post tile is not on the page"
        delta = max(abs(a - b) for a, b in zip(block["background"], tile["background"]))
        assert delta > 2, (
            f"{scheme} scheme: the code block {block['background']} is not "
            f"measurably distinct from the post tile {tile['background']} "
            f"(largest channel delta {delta})"
        )
    finally:
        context.close()


@requires_frontend_build
def test_the_line_numbering_survives_the_highlighting(browser, app_server, app) -> None:
    _make_post(app, "Prism Lines", "prism-lines", f"```python\n{CODE_SOURCE}```")

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = _open(context, app_server, "prism-lines", "dark")
        page.wait_for_selector(".prose pre .token.keyword", timeout=15000)

        state = page.evaluate(
            """() => {
              const code = document.querySelector('.prose pre code');
              const lines = [...code.querySelectorAll('.code-line')];
              return {
                count: lines.length,
                text: code.textContent,
                counters: lines.map((el) => getComputedStyle(el, '::before').content),
              };
            }"""
        )

        assert state["count"] == LINE_COUNT
        assert state["text"] == CODE_SOURCE
        assert all("counter(code-line)" in content for content in state["counters"])
    finally:
        context.close()


@requires_frontend_build
def test_a_token_that_spans_lines_keeps_its_colour(browser, app_server, app) -> None:
    _make_post(app, "Prism Multiline", "prism-multiline", f"```python\n{MULTILINE_SOURCE}```")

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = _open(context, app_server, "prism-multiline", "dark")
        page.wait_for_selector(".prose pre .token", timeout=15000)

        state = page.evaluate(
            """() => {
              const lines = [...document.querySelectorAll('.prose pre code .code-line')];
              return {
                count: lines.length,
                strings: lines.map((el) => !!el.querySelector('.token.string')),
              };
            }"""
        )

        assert state["count"] == 4
        assert state["strings"] == [True, True, True, True], (
            "a token that spans lines lost its colour on the continuation lines"
        )
    finally:
        context.close()


def _login(page, app_server) -> None:
    page.goto(f"{app_server}/admin/login")
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', os.environ["ADMIN_PASSWORD"])
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


@requires_frontend_build
def test_the_admin_settings_page_offers_no_syntax_theme(browser, app_server) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        _login(page, app_server)
        page.goto(f"{app_server}/admin/settings")
        page.wait_for_load_state("domcontentloaded")

        assert page.locator("#syntax_theme").count() == 0
        assert page.locator('select[name="syntax_theme"]').count() == 0
        html = page.content()
        assert "data-syntax-theme" not in html
    finally:
        context.close()
