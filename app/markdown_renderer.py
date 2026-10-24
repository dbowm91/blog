"""Markdown rendering pipeline with CSS-driven code block line numbering.

Python-Markdown renders a code block as a single text node inside
``<pre><code>``. CSS cannot enumerate the lines of a text node, so the
renderer wraps every line in a ``<span class="code-line">`` element and lets
the stylesheet number those spans with a CSS counter.

The numbering is therefore done entirely in CSS: no JavaScript and no
client-side library is involved, and the code text itself is untouched — the
line breaks stay between the spans, so ``textContent`` (and therefore
copy and paste) is byte-for-byte what the author wrote.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

import markdown
import nh3

from app.markdown_config import MARKDOWN_ALLOWED_ATTRIBUTES, MARKDOWN_ALLOWED_TAGS
from app.markdown_extensions import StrikethroughExtension

CODE_LINE_CLASS = "code-line"

DEFAULT_EXTENSIONS: tuple[str, ...] = ("fenced_code", "tables", "footnotes")

FEED_EXTENSIONS: tuple[str, ...] = ("fenced_code", "tables")

_CODE_BLOCK_RE = re.compile(r"(<pre>\s*<code\b[^>]*>)(.*?)(</code>\s*</pre>)", re.DOTALL)


def wrap_code_lines(html: str) -> str:
    """Wrap every line of every code block in a ``code-line`` span.

    The newline characters stay between the spans rather than inside them, so
    the rendered text is identical to the input and an empty trailing line is
    not turned into a numbered line of its own.

    Code blocks that contain raw HTML are left untouched: splitting them per
    line could cut a tag in half.
    """
    if not html:
        return html

    def _replace(match: re.Match[str]) -> str:
        open_tag, content, close_tag = match.group(1), match.group(2), match.group(3)
        if not content or "<" in content:
            return match.group(0)

        lines = content.split("\n")
        tail = lines.pop()
        parts: list[str] = []
        for line in lines:
            parts.append(f'<span class="{CODE_LINE_CLASS}">{line}</span>\n')
        if tail:
            parts.append(f'<span class="{CODE_LINE_CLASS}">{tail}</span>')
        return open_tag + "".join(parts) + close_tag

    return _CODE_BLOCK_RE.sub(_replace, html)


def render_markdown(text: str, extensions: Sequence[str] = DEFAULT_EXTENSIONS) -> str:
    """Render markdown to sanitized HTML with numbered code lines.

    Args:
        text: Markdown source.
        extensions: Python-Markdown extensions to enable.

    Returns:
        Sanitized HTML in which every code block line is wrapped in a
        ``<span class="code-line">`` element.
    """
    if not text:
        return ""

    html = markdown.markdown(text, extensions=[*extensions, StrikethroughExtension()])
    return nh3.clean(
        wrap_code_lines(html),
        tags=MARKDOWN_ALLOWED_TAGS,
        attributes=MARKDOWN_ALLOWED_ATTRIBUTES,
    )
