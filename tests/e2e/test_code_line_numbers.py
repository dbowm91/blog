"""Browser-level checks for the CSS-driven code block line numbers.

The numbering is produced by a CSS counter, so these tests assert what the
browser actually renders: one numbered element per source line, a gutter that
is identical on every line, a block that is exactly as tall as its lines, and
a code text that is unchanged.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

DIST_DIR = Path(__file__).resolve().parents[2] / "app" / "static" / "dist"
MANIFEST_PATH = DIST_DIR / ".vite" / "manifest.json"

requires_frontend_build = pytest.mark.skipif(
    not MANIFEST_PATH.exists(),
    reason="frontend bundle not built (run `npm run build`)",
)

CODE_SOURCE = "def hello(name):\n    print(f'hello {name}')\n\n# a comment\nx = 1  # trailing\n"
LINE_COUNT = len(CODE_SOURCE.rstrip("\n").split("\n"))

GEOMETRY_JS = """() => {
  const pre = document.querySelector('.prose pre');
  const code = pre.querySelector('code');
  const spans = [...code.querySelectorAll('.code-line')];
  const cs = (el, pseudo) => getComputedStyle(el, pseudo);
  const textX = spans.map(el => {
    const r = document.createRange();
    r.selectNodeContents(el);
    return r.getBoundingClientRect().left;
  });
  return {
    spanCount: spans.length,
    content: code.textContent,
    beforeContent: spans.map(el => cs(el, '::before').content),
    beforeDisplay: spans.length ? cs(spans[0], '::before').display : null,
    lineHeight: parseFloat(cs(pre, null).lineHeight),
    preHeight: pre.getBoundingClientRect().height,
    paddingTop: parseFloat(cs(pre, null).paddingTop),
    paddingBottom: parseFloat(cs(pre, null).paddingBottom),
    textX,
    lineLeft: spans.map(el => el.getBoundingClientRect().left),
  };
}"""


def _make_post(app, title: str, slug: str, body: str):
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


def _login(page, app_server):
    page.goto(f"{app_server}/admin/login")
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', os.environ["ADMIN_PASSWORD"])
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


def test_code_block_lines_are_numbered_by_a_css_counter(browser, app_server, app):
    _make_post(app, "Line Numbers", "code-line-numbers", f"```python\n{CODE_SOURCE}```")

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        page.goto(f"{app_server}/post/code-line-numbers")
        page.wait_for_selector(".prose pre code .code-line", timeout=15000)

        geometry = page.evaluate(GEOMETRY_JS)

        assert geometry["spanCount"] == LINE_COUNT
        assert all("counter(code-line)" in content for content in geometry["beforeContent"]), (
            geometry["beforeContent"]
        )
        assert geometry["beforeDisplay"] == "inline-block"
        assert geometry["content"] == CODE_SOURCE

        expected_height = (
            LINE_COUNT * geometry["lineHeight"] + geometry["paddingTop"] + geometry["paddingBottom"]
        )
        assert abs(geometry["preHeight"] - expected_height) < 2, (
            f"block height {geometry['preHeight']} does not match {LINE_COUNT} lines "
            f"({expected_height})"
        )

        populated = [
            (text, left) for text, left in zip(geometry["textX"], geometry["lineLeft"]) if text > 0
        ]
        assert populated, "no code text was measured"
        assert len({round(text, 1) for text, _ in populated}) == 1, (
            f"the code text is not aligned across lines: {geometry['textX']}"
        )
        assert all(text - left > 10 for text, left in populated), (
            f"the numbers do not sit to the left of the code: {geometry['textX']}"
        )
    finally:
        context.close()


def test_code_text_is_not_numbered_when_copied(browser, app_server, app):
    """The generated numbers are not part of the code text."""
    _make_post(app, "Copy Fidelity", "code-line-copy", f"```python\n{CODE_SOURCE}```")

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        page.goto(f"{app_server}/post/code-line-copy")
        page.wait_for_selector(".prose pre code .code-line", timeout=15000)

        text = page.evaluate("() => document.querySelector('.prose pre code').textContent")
        assert text == CODE_SOURCE
    finally:
        context.close()


@requires_frontend_build
def test_admin_preview_numbers_code_lines(browser, app_server, app):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        _login(page, app_server)
        page.goto(f"{app_server}/admin/new")
        page.fill("#body", f"```python\n{CODE_SOURCE}```")
        page.wait_for_selector(".markdown-preview .code-line", timeout=15000)

        preview = page.evaluate(
            """() => {
              const spans = [...document.querySelectorAll('.markdown-preview .code-line')];
              return {
                count: spans.length,
                beforeContent: spans.map(el => getComputedStyle(el, '::before').content),
                beforeDisplay: spans.length
                  ? getComputedStyle(spans[0], '::before').display
                  : null,
              };
            }"""
        )
        assert preview["count"] == LINE_COUNT
        assert all("counter(code-line)" in c for c in preview["beforeContent"])
        assert preview["beforeDisplay"] == "inline-block"
    finally:
        context.close()
