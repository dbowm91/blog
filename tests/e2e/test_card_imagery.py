"""Browser-level checks for the imagery.

Two contracts are asserted here, and both are properties of the rendered page
rather than of the stylesheet:

* the card image band is 16:9 at every viewport width, so a 16:9 screenshot is
  not cropped by ``object-fit: cover``;
* the placeholder mark takes its colour from the theme. An SVG loaded through
  ``<img>`` cannot read the page's colour, so the mark is applied as a CSS mask
  and the ink comes from the element's own background. The test asserts that
  the background changes with the colour scheme, which is the observable
  consequence of that contract.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

DIST_DIR = Path(__file__).resolve().parents[2] / "app" / "static" / "dist"
MANIFEST_PATH = DIST_DIR / ".vite" / "manifest.json"

requires_frontend_build = pytest.mark.skipif(
    not MANIFEST_PATH.exists(),
    reason="frontend bundle not built (run `npm run build`)",
)

SOURCE_FILENAME = "e2e-card-imagery.png"
SOURCE_WIDTH = 1600
SOURCE_HEIGHT = 900

BAND_RATIO_MIN = 1.76
BAND_RATIO_MAX = 1.80

BAND_JS = """(selector) => {
  const el = document.querySelector(selector);
  if (!el) return null;
  const rect = el.getBoundingClientRect();
  const style = getComputedStyle(el);
  return {
    width: rect.width,
    height: rect.height,
    ratio: rect.height > 0 ? rect.width / rect.height : 0,
    backgroundColor: style.backgroundColor,
    maskImage: style.maskImage || style.webkitMaskImage,
    isImage: el.tagName === 'IMG',
    naturalWidth: el.tagName === 'IMG' ? el.naturalWidth : null,
    naturalHeight: el.tagName === 'IMG' ? el.naturalHeight : null,
  };
}"""


def _sixteen_by_nine_png() -> bytes:
    """A real 16:9 PNG, so the browser has a real image to lay out."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (SOURCE_WIDTH, SOURCE_HEIGHT), (32, 48, 64))
    draw = ImageDraw.Draw(image)
    for y in range(0, SOURCE_HEIGHT, 160):
        for x in range(0, SOURCE_WIDTH, 160):
            if (x // 160 + y // 160) % 2 == 0:
                draw.rectangle([x, y, x + 159, y + 159], fill=(72, 104, 128))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture(scope="session")
def post_with_cover(app, app_server):
    """A published post whose cover image is a real 16:9 file."""
    from app.extensions import db
    from app.models import Post
    from app.storage import get_storage
    from app.utils import utc_now

    storage = get_storage()
    storage.save(SOURCE_FILENAME, _sixteen_by_nine_png())

    with app.app_context():
        post = Post(
            title="Card Imagery Post",
            slug="card-imagery-post",
            body="# Card Imagery\n\nA post with a 16:9 cover image.",
            summary="A post with a 16:9 cover image.",
            published=True,
            published_at=utc_now(),
            image=SOURCE_FILENAME,
        )
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    yield post_id


@pytest.fixture(scope="session")
def post_without_cover(app, app_server):
    """A published post with no cover image, so the placeholder is rendered."""
    from app.extensions import db
    from app.models import Post
    from app.utils import utc_now

    with app.app_context():
        post = Post(
            title="Card Imagery Placeholder",
            slug="card-imagery-placeholder",
            body="# Card Imagery\n\nA post with no cover image.",
            summary="A post with no cover image.",
            published=True,
            published_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    yield post_id


@pytest.mark.parametrize("width", [1280, 768, 390])
def test_the_card_band_is_sixteen_by_nine(browser, app_server, post_without_cover, width) -> None:
    """The band keeps its ratio at every viewport width."""
    context = browser.new_context(viewport={"width": width, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/", wait_until="networkidle")
        page.wait_for_selector(".post-card-img", timeout=10_000)

        band = page.evaluate(BAND_JS, ".post-card-img")
        assert band is not None
        assert BAND_RATIO_MIN <= band["ratio"] <= BAND_RATIO_MAX, (
            f"the card band is {band['ratio']:.3f} at {width}px: {band}"
        )
    finally:
        context.close()


def test_a_sixteen_by_nine_source_is_not_cropped(browser, app_server, post_with_cover) -> None:
    """`cover` crops when the box and the source disagree; at 16:9 they do not."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/", wait_until="networkidle")
        page.wait_for_selector(f'.post-card-img[src*="{SOURCE_FILENAME}"]', timeout=10_000)
        page.wait_for_function(
            f"() => {{ const i = document.querySelector('.post-card-img[src*=\"{SOURCE_FILENAME}\"]');"
            " return i && i.complete && i.naturalWidth > 0; }",
            timeout=10_000,
        )

        band = page.evaluate(BAND_JS, f'.post-card-img[src*="{SOURCE_FILENAME}"]')
        assert band is not None

        natural_ratio = band["naturalWidth"] / band["naturalHeight"]
        assert abs(band["ratio"] - natural_ratio) / natural_ratio < 0.02, (
            f"the band {band['ratio']:.3f} crops the {natural_ratio:.3f} source: {band}"
        )
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["dark", "light"])
def test_the_placeholder_takes_its_colour_from_the_theme(
    browser, app_server, post_without_cover, scheme
) -> None:
    """The placeholder ink comes from the theme, not from the asset."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.add_init_script(
            f"try {{ localStorage.setItem('blog-color-scheme', '{scheme}'); }} catch (e) {{}}"
        )
        page.goto(f"{app_server}/", wait_until="networkidle")
        page.wait_for_selector(".img-placeholder", timeout=10_000)

        placeholder = page.evaluate(BAND_JS, ".img-placeholder")
        assert placeholder is not None
        assert placeholder["maskImage"], "the placeholder is not masked by the mark"
        assert placeholder["backgroundColor"] not in ("rgba(0, 0, 0, 0)", "transparent"), (
            f"the placeholder has no ink of its own: {placeholder}"
        )
    finally:
        context.close()


def test_the_placeholder_colour_differs_between_the_schemes(
    browser, app_server, post_without_cover
) -> None:
    """The same asset renders differently in the dark and the light scheme."""
    inks = {}
    for scheme in ("dark", "light"):
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        try:
            page = context.new_page()
            page.add_init_script(
                f"try {{ localStorage.setItem('blog-color-scheme', '{scheme}'); }} catch (e) {{}}"
            )
            page.goto(f"{app_server}/", wait_until="networkidle")
            page.wait_for_selector(".img-placeholder", timeout=10_000)
            placeholder = page.evaluate(BAND_JS, ".img-placeholder")
            inks[scheme] = placeholder["backgroundColor"]
        finally:
            context.close()

    assert inks["dark"] != inks["light"], (
        f"the placeholder is the same colour in both schemes: {inks}"
    )


def test_the_placeholder_is_visible(browser, app_server, post_without_cover) -> None:
    """The placeholder has a rendered box and is not painted in its own colour."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/", wait_until="networkidle")
        page.wait_for_selector(".img-placeholder", timeout=10_000)

        placeholder = page.evaluate(BAND_JS, ".img-placeholder")
        assert placeholder is not None
        assert placeholder["width"] > 0 and placeholder["height"] > 0, (
            f"the placeholder has no rendered size: {placeholder}"
        )

        surface = page.evaluate(
            """() => {
              const card = document.querySelector('.post-card');
              if (!card) return null;
              const style = getComputedStyle(card);
              return style.backgroundColor;
            }"""
        )
        assert placeholder["backgroundColor"] != surface, (
            f"the placeholder is invisible against its tile: {placeholder} on {surface}"
        )
    finally:
        context.close()


def test_the_hero_height_is_unchanged(browser, app_server, post_without_cover) -> None:
    """A hero is a banner; this phase does not resize it."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/post/card-imagery-placeholder", wait_until="networkidle")
        page.wait_for_selector(".post-hero-img", timeout=10_000)

        hero = page.evaluate(BAND_JS, ".post-hero-img")
        assert hero is not None
        assert round(hero["height"]) == 400, f"the hero is {hero['height']}px tall: {hero}"
    finally:
        context.close()


def test_the_related_thumbnail_is_sixteen_by_nine(browser, app_server, app) -> None:
    """The related-post thumbnail follows the same band as the card."""
    from app.extensions import db
    from app.models import Post, Tag
    from app.utils import utc_now

    with app.app_context():
        tag = Tag(name="Related Band", slug="related-band")
        db.session.add(tag)
        for index in range(2):
            post = Post(
                title=f"Related Band {index}",
                slug=f"related-band-{index}",
                body="# Related Band\n\nA post in the related band group.",
                summary="A post in the related band group.",
                published=True,
                published_at=utc_now(),
            )
            post.tags.append(tag)
            db.session.add(post)
        db.session.commit()

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/post/related-band-0", wait_until="networkidle")
        page.wait_for_selector(".related-card-img", timeout=10_000)

        band = page.evaluate(BAND_JS, ".related-card-img")
        assert band is not None
        assert BAND_RATIO_MIN <= band["ratio"] <= BAND_RATIO_MAX, (
            f"the related thumbnail is {band['ratio']:.3f}: {band}"
        )
    finally:
        context.close()
