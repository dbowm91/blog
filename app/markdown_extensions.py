"""Markdown extensions used by the blog renderer."""

from __future__ import annotations

import re
from xml.etree import ElementTree as etree

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.preprocessors import Preprocessor

STRIKETHROUGH_PATTERN = r"(~{2})(.+?)(~{2})"
_HTML_BLOCK_OPEN = re.compile(r"^\s*:::html\s*$", re.IGNORECASE)
_HTML_BLOCK_CLOSE = re.compile(r"^\s*:::\s*$")
_FENCE_OPEN = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


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


class HtmlBlockPreprocessor(Preprocessor):
    """Stash explicitly marked HTML blocks for the final shared sanitizer."""

    def run(self, lines):
        output: list[str] = []
        index = 0
        fence_char = ""
        fence_length = 0
        while index < len(lines):
            line = lines[index]
            fence_match = _FENCE_OPEN.match(line)
            if fence_match:
                marker = fence_match.group(1)
                if not fence_char:
                    fence_char = marker[0]
                    fence_length = len(marker)
                elif marker[0] == fence_char and len(marker) >= fence_length:
                    fence_char = ""
                    fence_length = 0
                output.append(line)
                index += 1
                continue

            if not fence_char and _HTML_BLOCK_OPEN.match(line):
                end = index + 1
                while end < len(lines) and not _HTML_BLOCK_CLOSE.match(lines[end]):
                    end += 1
                if end < len(lines):
                    block = "\n".join(lines[index + 1 : end])
                    output.append(self.md.htmlStash.store(block))
                    index = end + 1
                    continue
            output.append(line)
            index += 1
        return output


class HtmlBlockExtension(Extension):
    """Enable the opt-in ``:::html`` block syntax."""

    def extendMarkdown(self, md):
        md.preprocessors.register(HtmlBlockPreprocessor(md), "safe_html_block", 27)
