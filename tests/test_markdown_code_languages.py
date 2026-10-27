"""Contracts for the fence language that has to survive markdown sanitisation.

The sanitiser's allowlist does not permit ``class`` on ``code``, so the fence
language Python-Markdown writes is removed before the markup reaches the page.
The renderer re-attaches it afterwards.

These tests pin that behaviour, and they pin the two properties that keep the
repair honest: the sanitiser allowlist must not be loosened, and a language
that cannot be trusted must be dropped rather than written.
"""

from __future__ import annotations

import pytest

from app.markdown_config import MARKDOWN_ALLOWED_ATTRIBUTES
from app.markdown_renderer import (
    apply_fence_languages,
    extract_fence_languages,
    render_markdown,
)


class TestLanguageSurvivesSanitisation:
    def test_fenced_block_carries_the_language(self) -> None:
        html = render_markdown("```python\nx = 1\n```")
        assert '<pre class="language-python">' in html
        assert '<code class="language-python">' in html

    def test_the_class_is_on_both_the_pre_and_the_code(self) -> None:
        html = render_markdown("```js\nconst x = 1;\n```")
        assert html.count('class="language-js"') == 2

    def test_several_blocks_keep_their_own_language(self) -> None:
        html = render_markdown(
            "```python\na = 1\n```\n\n```rust\nfn main() {}\n```\n\n```sql\nSELECT 1\n```"
        )
        for language in ("python", "rust", "sql"):
            assert html.count(f'class="language-{language}"') == 2, language

    def test_a_block_without_a_fence_tag_has_no_language(self) -> None:
        html = render_markdown("```\nplain\n```")
        assert "language-" not in html

    def test_an_unrecognised_fence_tag_produces_no_language(self) -> None:
        html = render_markdown("```PYTHON\nx = 1\n```")
        assert "language-" not in html

    def test_the_code_text_is_untouched(self) -> None:
        html = render_markdown("```python\nx = 1\n```")
        assert 'class="code-line">x = 1</span>' in html


class TestSanitiserIsUnchanged:
    """The allowlist is the boundary. The renderer owns the markup."""

    def test_the_allowlist_has_no_code_entry(self) -> None:
        assert "code" not in MARKDOWN_ALLOWED_ATTRIBUTES
        assert "pre" not in MARKDOWN_ALLOWED_ATTRIBUTES

    def test_class_is_still_permitted_on_span_and_div(self) -> None:
        assert MARKDOWN_ALLOWED_ATTRIBUTES["span"] == {"class"}
        assert MARKDOWN_ALLOWED_ATTRIBUTES["div"] == {"class"}

    def test_the_sanitiser_still_strips_a_class_on_code(self) -> None:
        import nh3

        from app.markdown_config import MARKDOWN_ALLOWED_TAGS

        cleaned = nh3.clean(
            '<pre><code class="language-python">x</code></pre>',
            tags=MARKDOWN_ALLOWED_TAGS,
            attributes=MARKDOWN_ALLOWED_ATTRIBUTES,
        )
        assert "language-" not in cleaned

    def test_raw_html_cannot_smuggle_a_class_past_the_slug_check(self) -> None:
        html = render_markdown(
            '<pre><code class="language-py&quot; onmouseover=&quot;alert(1)">x</code></pre>'
        )
        assert "onmouseover" not in html
        assert "language-" not in html


class TestSlugIsValidated:
    @pytest.mark.parametrize(
        "language",
        [
            'py"onmouseover="alert(1)',
            "py onmouseover=alert(1)",
            "PYTHON",
            "python/../etc",
            "",
            "a" * 33,
        ],
    )
    def test_an_untrusted_language_is_dropped(self, language: str) -> None:
        cleaned = apply_fence_languages("<pre><code>x</code></pre>", [language])
        assert "language-" not in cleaned
        assert cleaned == "<pre><code>x</code></pre>"

    @pytest.mark.parametrize("language", ["python", "js", "c++", "objective-c", "a_b"])
    def test_a_trusted_language_is_written(self, language: str) -> None:
        cleaned = apply_fence_languages("<pre><code>x</code></pre>", [language])
        assert f'class="language-{language}"' in cleaned

    def test_the_language_is_escaped_into_the_attribute(self) -> None:
        cleaned = apply_fence_languages("<pre><code>x</code></pre>", ["python"])
        assert 'class="language-python"' in cleaned
        assert "onmouseover" not in cleaned


class TestCountMismatchFailsClosed:
    def test_more_blocks_than_languages_leaves_the_markup_alone(self) -> None:
        markup = "<pre><code>a</code></pre><pre><code>b</code></pre>"
        assert apply_fence_languages(markup, ["python"]) == markup

    def test_more_languages_than_blocks_leaves_the_markup_alone(self) -> None:
        markup = "<pre><code>a</code></pre>"
        assert apply_fence_languages(markup, ["python", "js"]) == markup

    def test_no_languages_leaves_the_markup_alone(self) -> None:
        markup = "<pre><code>a</code></pre>"
        assert apply_fence_languages(markup, []) == markup

    def test_the_text_between_the_blocks_is_preserved(self) -> None:
        markup = "<pre><code>a</code></pre><p>text</p><pre><code>b</code></pre>"
        result = apply_fence_languages(markup, ["python", "js"])
        assert "<p>text</p>" in result
        assert result.count('class="language-') == 4


class TestExtraction:
    def test_every_block_is_reported_in_order(self) -> None:
        html = '<pre><code class="language-python">a</code></pre>'
        html += "<pre><code>b</code></pre>"
        html += '<pre><code class="language-rust">c</code></pre>'
        assert extract_fence_languages(html) == ["python", None, "rust"]

    def test_no_blocks_means_no_languages(self) -> None:
        assert extract_fence_languages("<p>text</p>") == []
