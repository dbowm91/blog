"""Markdown rendering pipeline with CSS-driven code block line numbering.

Python-Markdown renders a code block as a single text node inside
``<pre><code>``. CSS cannot enumerate the lines of a text node, so the
renderer wraps every line in a ``<span class="code-line">`` element and lets
the stylesheet number those spans with a CSS counter.

The numbering is therefore done entirely in CSS: no JavaScript and no
client-side library is involved, and the code text itself is untouched — the
line breaks stay between the spans, so ``textContent`` (and therefore
copy and paste) is byte-for-byte what the author wrote.

The fence language is a second job of this module. Python-Markdown writes it
into a ``class`` attribute on the ``<code>`` element, but the sanitiser's
allowlist does not permit ``class`` on ``code``, so the attribute is removed
before the markup reaches the page. The language is therefore extracted from
the unsanitised markup and re-attached afterwards, which keeps the sanitiser
allowlist as the single boundary for authored HTML.
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

_FENCE_OPEN_RE = re.compile(r"<pre\b[^>]*>\s*<code\b[^>]*>", re.DOTALL)

_FENCE_LANGUAGE_RE = re.compile(r'class="language-([^"]*)"')

_PRE_TAG_RE = re.compile(r"<pre\b[^>]*>", re.DOTALL)

_PRE_CODE_OPEN_RE = re.compile(r"(<pre\b[^>]*>)(\s*)(<code\b[^>]*>)", re.DOTALL)

_LANGUAGE_SLUG_RE = re.compile(r"^[a-z0-9_+-]{1,32}$")

_CLASS_ATTRIBUTE_RE = re.compile(r'\s+class="[^"]*"')


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


def extract_fence_languages(html: str) -> list[str | None]:
    """Return the fence language of every code block, in document order.

    The markup handed to this function has not been sanitised yet, so the
    ``class="language-..."`` attribute Python-Markdown writes on the ``<code>``
    element is still present. A block with no fence tag yields ``None``.
    """
    languages: list[str | None] = []
    for match in _FENCE_OPEN_RE.finditer(html):
        language = _FENCE_LANGUAGE_RE.search(match.group(0))
        languages.append(language.group(1) if language else None)
    return languages


def _set_language_class(tag: str, language: str) -> str:
    """Return the tag with the fence language as its only class."""
    stripped = _CLASS_ATTRIBUTE_RE.sub("", tag)
    return f'{stripped[:-1]} class="language-{language}">'


def apply_fence_languages(cleaned: str, languages: Sequence[str | None]) -> str:
    """Write the fence language back onto the sanitised code blocks.

    The class is written to both the ``<pre>`` and its ``<code>`` element: the
    highlighter selects on the ``<pre>``, Prism's own selector is on the
    ``<code>``.

    The function fails closed. If the sanitised markup holds a different number
    of code blocks than the unsanitised markup did, the markup is returned
    unchanged — an unhighlighted block is correct, a block labelled with the
    wrong language is not. A language that is not a valid slug is dropped
    rather than escaped.
    """
    if not cleaned or not languages:
        return cleaned
    if len(_PRE_TAG_RE.findall(cleaned)) != len(languages):
        return cleaned

    blocks = list(_PRE_CODE_OPEN_RE.finditer(cleaned))
    if len(blocks) != len(languages):
        return cleaned

    pieces: list[str] = []
    cursor = 0
    for match, language in zip(blocks, languages):
        pre_tag, gap, code_tag = match.group(1), match.group(2), match.group(3)
        if language and _LANGUAGE_SLUG_RE.match(language):
            pre_tag = _set_language_class(pre_tag, language)
            code_tag = _set_language_class(code_tag, language)
        pieces.append(cleaned[cursor : match.start()])
        pieces.append(pre_tag)
        pieces.append(gap)
        pieces.append(code_tag)
        cursor = match.end()
    pieces.append(cleaned[cursor:])
    return "".join(pieces)


def render_markdown(text: str, extensions: Sequence[str] = DEFAULT_EXTENSIONS) -> str:
    """Render markdown to sanitized HTML with numbered code lines.

    Args:
        text: Markdown source.
        extensions: Python-Markdown extensions to enable.

    Returns:
        Sanitized HTML in which every code block line is wrapped in a
        ``<span class="code-line">`` element and every fenced block carries its
        language on both the ``<pre>`` and the ``<code>`` element.
    """
    if not text:
        return ""

    html = markdown.markdown(text, extensions=[*extensions, StrikethroughExtension()])
    languages = extract_fence_languages(html)
    cleaned = nh3.clean(
        wrap_code_lines(html),
        tags=MARKDOWN_ALLOWED_TAGS,
        attributes=MARKDOWN_ALLOWED_ATTRIBUTES,
    )
    return apply_fence_languages(cleaned, languages)
