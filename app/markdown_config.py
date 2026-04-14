"""Shared nh3.clean() configuration for markdown sanitization."""

MARKDOWN_ALLOWED_TAGS = {
    "p", "br", "strong", "em", "u", "s", "code", "pre", "blockquote",
    "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "a", "img",
    "table", "thead", "tbody", "tr", "th", "td", "hr", "span", "div",
}

MARKDOWN_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    "span": {"class"},
    "div": {"class"},
    "*": {"class"},
}
