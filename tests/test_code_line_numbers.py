"""Contracts for the CSS-driven code block line numbers.

The numbering is produced by a CSS counter: the renderer wraps every code line
in a ``<span class="code-line">`` element and the stylesheet numbers those
spans. No JavaScript takes part, so these tests assert the markup contract,
the stylesheet contract, and the absence of any client-side participation.
"""

from __future__ import annotations

import html as html_module
import re
from pathlib import Path

import markdown

from app.markdown_renderer import CODE_LINE_CLASS, render_markdown, wrap_code_lines

REPO_ROOT = Path(__file__).resolve().parent.parent
CSS_DIR = REPO_ROOT / "app" / "static" / "css"
JS_DIR = REPO_ROOT / "app" / "static" / "js"

_TAG_RE = re.compile(r"<[^>]+>")

CODE_SOURCE = "def hello(name):\n    print(f'hello {name}')\n\n# a comment\nx = 1  # trailing\n"


def _text(markup: str) -> str:
    """Return the text content of a markup fragment."""
    return html_module.unescape(_TAG_RE.sub("", markup))


def _code_blocks(markup: str) -> list[str]:
    return re.findall(r"<pre>.*?</pre>", markup, re.DOTALL)


def _spans(markup: str) -> list[str]:
    return re.findall(rf'<span class="{CODE_LINE_CLASS}">(.*?)</span>', markup, re.DOTALL)


class TestLineSpans:
    def test_every_code_line_gets_a_span(self):
        markup = render_markdown(f"```python\n{CODE_SOURCE}```")
        assert len(_spans(markup)) == len(CODE_SOURCE.rstrip("\n").split("\n"))

    def test_span_carries_the_code_line_class(self):
        markup = render_markdown(f"```python\n{CODE_SOURCE}```")
        assert f'<span class="{CODE_LINE_CLASS}">' in markup

    def test_line_content_is_kept_verbatim(self):
        markup = render_markdown(f"```python\n{CODE_SOURCE}```")
        assert _spans(markup) == CODE_SOURCE.rstrip("\n").split("\n")

    def test_empty_line_gets_its_own_span(self):
        markup = render_markdown("```\na\n\nb\n```")
        assert _spans(markup) == ["a", "", "b"]

    def test_trailing_newline_does_not_add_a_numbered_line(self):
        markup = render_markdown("```\na\nb\n```")
        assert _spans(markup) == ["a", "b"]

    def test_last_line_without_a_newline_is_kept(self):
        markup = wrap_code_lines("<pre><code>a\nb</code></pre>")
        assert _spans(markup) == ["a", "b"]

    def test_inline_code_is_not_wrapped(self):
        markup = render_markdown("Some `inline` code.")
        assert f'<span class="{CODE_LINE_CLASS}">' not in markup
        assert "<code>inline</code>" in markup

    def test_indented_code_block_is_numbered(self):
        markup = render_markdown("Text\n\n    indented one\n    indented two\n")
        assert _spans(markup) == ["indented one", "indented two"]

    def test_entities_are_preserved(self):
        markup = render_markdown("```\nif a < b && c > d: pass\n```")
        assert "&lt;" in markup
        assert _spans(markup) == ["if a &lt; b &amp;&amp; c &gt; d: pass"]

    def test_code_block_with_raw_html_is_left_alone(self):
        raw = "<pre><code>one\n<span>two</span></code></pre>"
        assert wrap_code_lines(raw) == raw

    def test_sanitizer_keeps_the_class_attribute(self):
        markup = render_markdown("```\na\n```")
        assert f'<span class="{CODE_LINE_CLASS}">a</span>' in markup

    def test_rendered_text_matches_plain_markdown_output(self):
        source = f"Intro\n\n```python\n{CODE_SOURCE}```\n\nOutro"
        plain = markdown.markdown(source, extensions=["fenced_code", "tables", "footnotes"])
        assert _text(render_markdown(source)) == _text(plain)

    def test_empty_input_renders_nothing(self):
        assert render_markdown("") == ""

    def test_multiple_code_blocks_are_numbered_independently(self):
        markup = render_markdown("```\na\n```\n\n```\nb\nc\n```")
        assert len(_code_blocks(markup)) == 2
        assert _spans(markup) == ["a", "b", "c"]


class TestRenderedSurfaces:
    def test_template_filter_emits_line_spans(self, app):
        with app.app_context():
            markup = app.jinja_env.filters["markdown_safe"](f"```python\n{CODE_SOURCE}```")
        assert f'<span class="{CODE_LINE_CLASS}">' in markup

    def test_post_page_renders_line_spans(self, client, db):
        from app.models import Post
        from app.utils import utc_now

        post = Post(
            title="Code Lines",
            slug="code-lines",
            body=f"```python\n{CODE_SOURCE}```",
            published=True,
            published_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()

        page = client.get("/post/code-lines").get_data(as_text=True)
        assert f'<span class="{CODE_LINE_CLASS}">' in page

    def test_preview_endpoint_emits_line_spans(self, authenticated_client):
        response = authenticated_client.post(
            "/admin/preview-markdown",
            json={"text": f"```python\n{CODE_SOURCE}```"},
        )
        assert response.status_code == 200
        markup = response.get_json()["html"]
        assert f'<span class="{CODE_LINE_CLASS}">' in markup
        assert len(_spans(markup)) == len(CODE_SOURCE.rstrip("\n").split("\n"))

    def test_feed_stays_valid_xml(self, client, db):
        import xml.etree.ElementTree as ElementTree

        from app.models import Post
        from app.routes.rss import invalidate_rss_cache
        from app.utils import utc_now

        post = Post(
            title="Code Lines Feed",
            slug="code-lines-feed",
            body=f"```python\n{CODE_SOURCE}```",
            published=True,
            published_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()

        # The feed caches its post list for the whole session, so the cache is
        # invalidated on both sides: a stale list would hide later posts from
        # every other test that reads a feed.
        invalidate_rss_cache()
        try:
            for path in ("/rss", "/atom"):
                response = client.get(path)
                assert response.status_code == 200
                ElementTree.fromstring(response.get_data(as_text=True))
        finally:
            invalidate_rss_cache()


class TestStylesheetContract:
    def _css(self, name: str) -> str:
        return (CSS_DIR / name).read_text()

    def test_base_css_resets_the_counter_per_block(self):
        assert "counter-reset: code-line" in self._css("base.css")

    def test_base_css_increments_the_counter_per_line(self):
        assert "counter-increment: code-line" in self._css("base.css")

    def test_base_css_renders_the_counter(self):
        assert "content: counter(code-line)" in self._css("base.css")

    def test_line_numbers_are_not_selectable(self):
        assert "user-select: none" in self._css("base.css")

    def test_number_column_uses_a_theme_token(self):
        css = self._css("base.css")
        block = css.split(".prose pre code .code-line::before")[1].split("}")[0]
        assert "var(--text-dim)" in block

    def test_public_css_does_not_own_the_numbering(self):
        assert "counter(code-line)" not in self._css("public.css")

    def test_numbering_rules_live_in_a_stylesheet_both_shells_load(self):
        for template in ("base.html", "admin/base.html"):
            markup = (REPO_ROOT / "app" / "templates" / template).read_text()
            assert "css/base.css" in markup

    def test_no_javascript_takes_part_in_the_numbering(self):
        for path in JS_DIR.rglob("*.js"):
            if path.name == "prism.min.js":
                continue
            assert CODE_LINE_CLASS not in path.read_text(), path
