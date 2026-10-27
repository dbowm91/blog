"""Regression tests for the post image rendering pipeline.

Covers FE-IMG-01 (double-prefixed URLs), FE-IMG-02 (``srcset="None"``),
FE-IMG-03 (permanently invisible lazy images) and FE-IMG-04 (broken admin
editor preview).
"""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from app.models import Post, Tag
from app.storage import get_storage
from app.utils import utc_now

STATIC_DIR = Path(__file__).resolve().parents[1] / "app" / "static"
PUBLIC_CSS = STATIC_DIR / "css" / "public.css"
LAZY_LOAD_JS = STATIC_DIR / "js" / "shared" / "lazy-load.js"
PLACEHOLDER_SVG = STATIC_DIR / "img" / "default-post.svg"

SVG_NS = "{http://www.w3.org/2000/svg}"
CONTAINER_TAGS = ("svg", "g", "defs", "title", "desc")

DOUBLE_PREFIX = "/static/uploads//static/uploads/"
IMAGE_NAME = "test-image-rendering.png"
VARIANT_WIDTHS = (400, 800, 1200)


@pytest.fixture
def stored_image():
    """Store a real file in the storage backend and remove it afterwards."""
    storage = get_storage()
    storage.save(IMAGE_NAME, b"\x89PNG\r\n\x1a\n")
    yield IMAGE_NAME
    storage.delete(IMAGE_NAME)
    for width in VARIANT_WIDTHS:
        storage.delete(f"{width}_{IMAGE_NAME}")


@pytest.fixture
def post_with_image(db, stored_image):
    """Published post that owns a cover image present in storage."""
    post = Post(
        title="Post With Image",
        slug="post-with-image",
        body="# Image\n\nBody of the post.",
        summary="A post that has a cover image.",
        published=True,
        published_at=utc_now(),
        image=stored_image,
    )
    db.session.add(post)
    db.session.commit()
    return post


@pytest.fixture
def tagged_post(db, post_with_image):
    """Post with a tag so the tag archive renders its card."""
    tag = Tag(name="Imagery", slug="imagery")
    db.session.add(tag)
    db.session.commit()
    post_with_image.tags.append(tag)
    db.session.commit()
    return post_with_image


def _src_values(html):
    """All ``src`` attribute values in the rendered markup."""
    return re.findall(r'\ssrc="([^"]*)"', html)


def _meta_content(html, attribute, value):
    """Content of a ``<meta>`` tag matched by attribute/value."""
    pattern = rf'<meta\s+{attribute}="{re.escape(value)}"\s+content="([^"]*)"'
    match = re.search(pattern, html)
    assert match is not None, f"meta {attribute}={value} not found"
    return match.group(1)


def _parse_svg(path: Path) -> ET.ElementTree:
    return ET.parse(path)


def _paint_elements(path: Path) -> list[dict]:
    """Every drawn element with its effective fill and stroke.

    ``fill`` and ``stroke`` are inherited, so the values are resolved by
    walking the tree rather than read off the element.
    """
    root = _parse_svg(path).getroot()
    elements: list[dict] = []

    def walk(node, inherited: dict) -> None:
        attrs = node.attrib
        fill = attrs.get("fill", inherited["fill"])
        stroke = attrs.get("stroke", inherited["stroke"])
        for child in node:
            walk(child, {"fill": fill, "stroke": stroke})
        tag = node.tag.replace(SVG_NS, "")
        if tag in CONTAINER_TAGS:
            return
        elements.append({**attrs, "tag": tag, "fill": fill, "stroke": stroke})

    walk(root, {"fill": "black", "stroke": "none"})
    return elements


def _rule_body(css: str, selector: str) -> str:
    """The declaration body of the first rule with exactly this selector."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        if match.group(1).strip() == selector:
            return match.group(2)
    raise AssertionError(f"no rule for {selector}")


def test_no_double_prefix_in_rendered_pages(client, db, tagged_post):
    """No rendered page may contain a double /static/uploads/ prefix."""
    pages = {
        "index": "/",
        "tag": "/tag/imagery",
        "search": "/search?q=image",
        "post": "/post/post-with-image",
    }

    for name, url in pages.items():
        response = client.get(url)
        assert response.status_code == 200, f"{name} page returned {response.status_code}"
        html = response.get_data(as_text=True)
        assert DOUBLE_PREFIX not in html, f"{name} page contains a double upload prefix"
        assert f"/static/uploads/{IMAGE_NAME}" in html, f"{name} page does not show the image"

    src = f"/static/uploads/{IMAGE_NAME}"
    assert client.get(src).status_code == 200


def test_no_srcset_none_in_rendered_pages(client, db, tagged_post):
    """``srcset="None"`` must never be emitted; the attribute is dropped instead."""
    pages = {
        "index": "/",
        "tag": "/tag/imagery",
        "search": "/search?q=image",
        "post": "/post/post-with-image",
    }

    for name, url in pages.items():
        html = client.get(url).get_data(as_text=True)
        assert 'srcset="None"' not in html, f'{name} page emits srcset="None"'
        assert "srcset=" not in html, f"{name} page emits a srcset without variants"


def test_srcset_rendered_when_variants_exist(client, db, tagged_post):
    """Responsive variants on disk produce a valid srcset with the expected widths."""
    storage = get_storage()
    for width in VARIANT_WIDTHS:
        storage.save(f"{width}_{IMAGE_NAME}", b"\x89PNG\r\n\x1a\n")

    html = client.get("/").get_data(as_text=True)

    match = re.search(r'\ssrcset="([^"]*)"', html)
    assert match is not None, "no srcset rendered although variants exist"
    srcset = match.group(1)
    assert "None" not in srcset
    for width in VARIANT_WIDTHS:
        assert f"/static/uploads/{width}_{IMAGE_NAME} {width}w" in srcset
    assert srcset.count(",") == len(VARIANT_WIDTHS) - 1


def test_lazy_image_class_contract():
    """The CSS rule that hides an image has a restoration path the JS applies."""
    css = PUBLIC_CSS.read_text()
    js = LAZY_LOAD_JS.read_text()

    rules = re.findall(r"([^{}]+)\{([^{}]*)\}", css)

    hiding_selectors = [
        selector.strip()
        for selector, body in rules
        if "opacity: 0" in body and 'img[loading="lazy"]' in selector
    ]
    assert hiding_selectors, "no CSS rule hides lazy images"

    restoring_classes = set()
    for selector, body in rules:
        if "opacity: 1" not in body:
            continue
        for selector_part in selector.split(","):
            marker = 'img[loading="lazy"]'
            if marker not in selector_part:
                continue
            state = selector_part.split(marker, 1)[1]
            restoring_classes.update(re.findall(r"\.([A-Za-z_][\w-]*)", state))
    assert restoring_classes, "no CSS rule restores lazy images"

    for class_name in restoring_classes:
        assert f"classList.add('{class_name}')" in js or f'classList.add("{class_name}")' in js, (
            f"lazy-load.js never applies the .{class_name} class"
        )

    native_check = js.index("'loading' in HTMLImageElement.prototype")
    assert js.index("classList.add('loaded')") < native_check, (
        "lazy-load.js returns before the .loaded class can be applied"
    )


def test_admin_editor_preview_src(authenticated_client, db, post_with_image):
    """The editor cover-image preview resolves to the stored image, not a 404."""
    response = authenticated_client.get(f"/admin/edit/{post_with_image.id}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    match = re.search(r'<img[^>]*id="image-preview-img"[^>]*>', html)
    assert match is not None, "editor did not render the image preview"
    tag = match.group(0)

    src = re.search(r'\ssrc="([^"]*)"', tag)
    assert src is not None, "editor image preview has no src"
    src = src.group(1)

    assert DOUBLE_PREFIX not in src
    assert src == f"/static/uploads/{IMAGE_NAME}"
    assert authenticated_client.get(src).status_code == 200


def test_social_metadata_uses_absolute_urls(client, db, post_with_image):
    """og:image / twitter:image / JSON-LD image are absolute and agree."""
    html = client.get("/post/post-with-image").get_data(as_text=True)

    og_image = _meta_content(html, "property", "og:image")
    twitter_image = _meta_content(html, "name", "twitter:image")

    for value in (og_image, twitter_image):
        assert value.startswith("http://") or value.startswith("https://")
        assert DOUBLE_PREFIX not in value
        assert "/static/uploads/" + IMAGE_NAME in value
        assert value.count("/static/uploads/") == 1

    schema = html.split('<script type="application/ld+json"', 1)[1]
    schema = schema.split(">", 1)[1].split("</script>", 1)[0]
    data = json.loads(schema)
    assert data["image"] == og_image


def test_social_metadata_default_image(client, db, sample_post):
    """A post without a cover image falls back to the default image."""
    html = client.get("/post/test-post").get_data(as_text=True)

    og_image = _meta_content(html, "property", "og:image")
    twitter_image = _meta_content(html, "name", "twitter:image")

    assert og_image.endswith("/static/img/default-post-social.png")
    assert twitter_image == og_image


def test_the_social_preview_target_is_a_raster_image(client, db, sample_post):
    """A social platform does not render an SVG, so the metadata needs a raster."""
    html = client.get("/post/test-post").get_data(as_text=True)
    og_image = _meta_content(html, "property", "og:image")

    target = STATIC_DIR / "img" / "default-post-social.png"
    assert target.exists(), "the social preview image does not exist"
    assert og_image.endswith("/static/img/default-post-social.png")
    assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", "the social preview image is not a PNG"


def test_the_placeholder_mark_has_no_palette():
    """The mark carries no colour of its own; the stylesheet supplies the ink."""
    text = PLACEHOLDER_SVG.read_text()

    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", text), "the placeholder contains a hex colour"
    assert "rgb(" not in text and "hsl(" not in text, "the placeholder contains a colour function"

    for element in _paint_elements(PLACEHOLDER_SVG):
        assert element["fill"] in ("currentColor", "none"), (
            f"<{element['tag']}> fills with {element['fill']}"
        )
        assert element["stroke"] in ("currentColor", "none"), (
            f"<{element['tag']}> strokes with {element['stroke']}"
        )


def test_the_placeholder_mark_is_transparent():
    """Nothing paints the whole canvas, so the tile shows through the mark."""
    root = _parse_svg(PLACEHOLDER_SVG).getroot()
    view_box = [float(value) for value in root.get("viewBox").split()]

    for element in _paint_elements(PLACEHOLDER_SVG):
        if element["fill"] == "none" or element["tag"] != "rect":
            continue
        geometry = (
            float(element.get("x", 0)),
            float(element.get("y", 0)),
            float(element.get("width", 0)),
            float(element.get("height", 0)),
        )
        assert geometry != tuple(view_box), f"a filled rect covers the whole canvas: {geometry}"


def test_the_placeholder_is_themed_by_the_stylesheet():
    """The mark is applied as a mask, so the ink comes from the theme token."""
    css = PUBLIC_CSS.read_text()

    assert ".img-placeholder" in css, "public.css has no placeholder rule"
    assert "default-post.svg" in css, "the placeholder is not masked by the mark"
    assert "mask-image" in css, "the placeholder is not masked"

    rule = _rule_body(css, ".img-placeholder")
    assert "var(--text-dim)" in rule, "the placeholder does not take its ink from the theme"
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", rule), (
        "the placeholder rule contains a colour literal"
    )


def test_a_post_without_a_cover_renders_the_themed_placeholder(client, db, sample_post):
    """The card renders the themed placeholder instead of a fixed image."""
    html = client.get("/").get_data(as_text=True)

    assert 'class="post-card-img img-placeholder"' in html, (
        "the index card does not render the themed placeholder"
    )
    assert 'role="img"' in html, "the placeholder carries no image role"
    assert "default-post.svg" not in html, "the placeholder is still loaded as an image"
