"""Sanitiser for operator supplied SVG backdrops.

Uploaded SVGs are served from the same origin as the site, so a document that
keeps its scripting or its external references would run with the site's
privileges.  The sanitiser parses the document and removes everything that is
not inert drawing markup.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"

_FORBIDDEN_ELEMENTS = frozenset(
    {
        "script",
        "foreignObject",
        "iframe",
        "embed",
        "object",
        "audio",
        "video",
        "handler",
        "listener",
        "animate",
        "animateMotion",
        "animateTransform",
        "set",
        "discard",
        "style",
    }
)

_URL_ATTRIBUTES = frozenset({"href", "src", "xlink:href", "from", "to", "values", "by"})

_DANGEROUS_VALUE_RE = re.compile(
    r"(?:javascript|vbscript|data)\s*:|expression\s*\(|@import|url\s*\(",
    re.IGNORECASE,
)

_DOCTYPE_RE = re.compile(r"<!(?:DOCTYPE|ENTITY)", re.IGNORECASE)


class SvgSanitisationError(ValueError):
    """The supplied document is not a usable SVG."""


def _local_name(tag: object) -> str:
    if not isinstance(tag, str):
        return ""
    if "}" in tag:
        tag = tag.rsplit("}", 1)[1]
    return tag.lower()


def _is_dangerous_attribute(name: str, value: str) -> bool:
    lowered = name.lower()
    if lowered.startswith("on"):
        return True
    if lowered in {"style"}:
        return bool(_DANGEROUS_VALUE_RE.search(value))
    if lowered in _URL_ATTRIBUTES:
        candidate = value.strip()
        if candidate.startswith("#"):
            return False
        if lowered in {"from", "to", "values", "by"}:
            return False
        return True
    if lowered.endswith("href"):
        return not value.strip().startswith("#")
    return False


def _strip_element(element: ET.Element) -> None:
    for key in list(element.attrib):
        if _is_dangerous_attribute(key, element.attrib[key]):
            del element.attrib[key]


def _clean_tree(element: ET.Element) -> None:
    _strip_element(element)
    for child in list(element):
        if _local_name(child.tag) in _FORBIDDEN_ELEMENTS:
            element.remove(child)
            continue
        _clean_tree(child)


def sanitize_svg(svg_text: str) -> str:
    """Return an inert copy of an SVG document.

    Raises :class:`SvgSanitisationError` when the document cannot be parsed,
    declares a doctype, or is not an SVG root element.
    """
    if not svg_text or not svg_text.strip():
        raise SvgSanitisationError("the SVG document is empty")

    if _DOCTYPE_RE.search(svg_text):
        raise SvgSanitisationError("the SVG document must not declare a doctype or entities")

    try:
        parser = ET.XMLParser()
        parser.feed(svg_text)
        root = parser.close()
    except ET.ParseError as exc:
        raise SvgSanitisationError(f"the SVG document could not be parsed: {exc}") from exc

    if _local_name(root.tag) != "svg":
        raise SvgSanitisationError("the document root must be an <svg> element")

    _clean_tree(root)

    ET.register_namespace("", SVG_NAMESPACE)
    ET.register_namespace("xlink", XLINK_NAMESPACE)
    return ET.tostring(root, encoding="unicode", xml_declaration=False)


__all__ = ["SVG_NAMESPACE", "SvgSanitisationError", "sanitize_svg"]
