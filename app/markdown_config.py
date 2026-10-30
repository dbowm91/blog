"""Shared nh3.clean() policy for Markdown and authored embed blocks."""

MARKDOWN_ALLOWED_TAGS = {
    "p",
    "br",
    "strong",
    "em",
    "u",
    "s",
    "code",
    "pre",
    "blockquote",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "a",
    "img",
    "video",
    "source",
    "iframe",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "hr",
    "span",
    "div",
}

MARKDOWN_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    "video": {"src", "controls", "preload", "width", "height", "poster"},
    "source": {"src", "type"},
    "iframe": {
        "src",
        "title",
        "width",
        "height",
        "loading",
        "allow",
        "allowfullscreen",
        "referrerpolicy",
        "sandbox",
    },
    "span": {"class"},
    "div": {"class"},
}

YOUTUBE_EMBED_HOST = "www.youtube-nocookie.com"
YOUTUBE_EMBED_SRC = "https://www.youtube-nocookie.com/embed/"
IFRAME_ALLOW = "accelerometer; encrypted-media; picture-in-picture; web-share"
IFRAME_SANDBOX = "allow-scripts allow-same-origin allow-presentation"
