"""Markdown extensions used by the blog renderer.

Python-Markdown ships no strikethrough syntax, so the blog provides its own
inline pattern for ``~~struck~~`` text. The renderer emits ``<s>`` elements,
which the sanitiser already allows.
"""

from __future__ import annotations

from xml.etree import ElementTree as etree

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor

STRIKETHROUGH_PATTERN = r"(~{2})(.+?)(~{2})"


class StrikethroughInlineProcessor(InlineProcessor):
    """Turn ``~~text~~`` into a ``<s>`` element."""

    def handleMatch(self, m, data):
        element = etree.Element("s")
        element.text = m.group(2)
        return element, m.start(0), m.end(0)


class StrikethroughExtension(Extension):
    """Register the strikethrough inline pattern."""

    def extendMarkdown(self, md):
        md.inlinePatterns.register(
            StrikethroughInlineProcessor(STRIKETHROUGH_PATTERN, md),
            "strikethrough",
            175,
        )
