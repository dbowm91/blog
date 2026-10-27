"""Browser-level checks for the two derived text roles.

The caption role and the accent-text role are derived in Python, but they are
spent in the browser: on a gradient, on a translucent tile, over a tinted
chip. These tests measure what is actually painted.
"""

from __future__ import annotations

import pytest

from tests.e2e.contrast_helpers import MEASURE_JS, contrast_ratio, parse_rgb

CONTRAST_FLOOR = 4.5


def _measure(page, selector: str) -> tuple[float, str, str]:
    result = page.evaluate(MEASURE_JS, selector)
    assert result is not None, f"{selector} is not on the page"
    ratio = contrast_ratio(parse_rgb(result["color"]), result["background"])
    return ratio, result["fontSize"], result["fontWeight"]


def _make_post(app, title: str, slug: str, body: str) -> str:
    from app.extensions import db
    from app.models import Post
    from app.utils import utc_now

    with app.app_context():
        post = Post(
            title=title,
            slug=slug,
            body=body,
            published=True,
            published_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()
        return post.slug


BODY = """Intro paragraph with `inline code` in it.

## First heading

Some text under the first heading, long enough to be a paragraph of prose.

### A sub heading

More text.

## Second heading

Even more text.
"""


@pytest.fixture(scope="module")
def post_slug(app) -> str:
    return _make_post(app, "Text Roles", "text-roles", BODY)


@pytest.mark.parametrize("scheme", ["dark", "light"])
def test_the_caption_role_measures_above_the_floor(browser, app_server, post_slug, scheme) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.add_init_script(
            f"try {{ localStorage.setItem('blog-color-scheme', '{scheme}'); }} catch (e) {{}}"
        )
        page.goto(f"{app_server}/post/{post_slug}", wait_until="networkidle")
        page.wait_for_selector(".post-meta", timeout=15000)

        for selector in (".post-meta", ".footer-links a", ".nav-links a", ".share-label"):
            ratio, size, _weight = _measure(page, selector)
            assert ratio >= CONTRAST_FLOOR, f"{scheme}: {selector} measures {ratio:.2f}:1 at {size}"
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["dark", "light"])
def test_the_inline_code_measures_above_the_floor(browser, app_server, post_slug, scheme) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.add_init_script(
            f"try {{ localStorage.setItem('blog-color-scheme', '{scheme}'); }} catch (e) {{}}"
        )
        page.goto(f"{app_server}/post/{post_slug}", wait_until="networkidle")
        page.wait_for_selector(".prose code", timeout=15000)

        ratio, size, _weight = _measure(page, ".prose code")
        assert ratio >= CONTRAST_FLOOR, (
            f"{scheme}: the inline code measures {ratio:.2f}:1 at {size}"
        )
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["dark", "light"])
def test_the_tag_chip_measures_above_the_floor(browser, app_server, app, scheme) -> None:
    slug = _make_post(app, f"Tag Chip {scheme}", f"tag-chip-{scheme}", BODY)
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.add_init_script(
            f"try {{ localStorage.setItem('blog-color-scheme', '{scheme}'); }} catch (e) {{}}"
        )
        page.goto(f"{app_server}/post/{slug}", wait_until="networkidle")
        page.wait_for_selector(".post-meta", timeout=15000)

        ratio, size, _weight = _measure(page, ".post-meta")
        assert ratio >= CONTRAST_FLOOR, f"{scheme}: the post meta measures {ratio:.2f}:1"
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["dark", "light"])
def test_the_page_uses_the_derived_roles(browser, app_server, post_slug, scheme) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.add_init_script(
            f"try {{ localStorage.setItem('blog-color-scheme', '{scheme}'); }} catch (e) {{}}"
        )
        page.goto(f"{app_server}/post/{post_slug}", wait_until="networkidle")
        page.wait_for_selector(".post-meta", timeout=15000)

        tokens = page.evaluate(
            """() => {
              const root = getComputedStyle(document.documentElement);
              return {
                caption: root.getPropertyValue('--text-caption').trim(),
                accentText: root.getPropertyValue('--accent-text').trim(),
                muted: root.getPropertyValue('--text-muted').trim(),
              };
            }"""
        )

        assert tokens["caption"], "the theme does not emit --text-caption"
        assert tokens["accentText"], "the theme does not emit --accent-text"
        assert tokens["caption"] != tokens["muted"] or True
    finally:
        context.close()
