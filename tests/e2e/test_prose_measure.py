"""Browser-level checks for the reading measure.

A measure is a property of the rendered page, not of the stylesheet. A rule that
says ``max-width: 34em`` only produces the intended number of characters if the
rendered face at the rendered size has the advance width the plan assumed, and
only if the cap binds at all. These tests measure the column in Chromium and
count the characters it actually holds, at every viewport the phase claims to
have fixed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

DIST_DIR = Path(__file__).resolve().parents[2] / "app" / "static" / "dist"
MANIFEST_PATH = DIST_DIR / ".vite" / "manifest.json"

requires_frontend_build = pytest.mark.skipif(
    not MANIFEST_PATH.exists(),
    reason="frontend bundle not built (run `npm run build`)",
)

MIN_CHARACTERS = 65
MAX_CHARACTERS = 75

PARAGRAPH = (
    "A paragraph long enough to wrap several times at every viewport the phase "
    "measures, so that the column width and not the amount of text decides where "
    "the lines break. The comfortable reading range is sixty to seventy-five "
    "characters, and a line of eighty-five is a long return path for the eye."
)

BODY = f"# Measure\n\n{PARAGRAPH}\n\n{PARAGRAPH}\n\n{PARAGRAPH}\n"

MEASURE_JS = """async (selector) => {
  const el = document.querySelector(selector);
  if (!el) return null;
  const rect = el.getBoundingClientRect();
  const style = getComputedStyle(el);

  // The advance is measured from the real rendered face, not from a canvas:
  // a canvas falls back to a generic family when the web font has not
  // finished loading, which would count characters in the wrong font.
  if (document.fonts && document.fonts.ready) {
    await document.fonts.ready;
  }
  const probe = document.createElement('span');
  probe.style.position = 'absolute';
  probe.style.visibility = 'hidden';
  probe.style.whiteSpace = 'pre';
  probe.style.fontFamily = style.fontFamily;
  probe.style.fontSize = style.fontSize;
  probe.style.fontWeight = style.fontWeight;
  probe.style.fontStyle = style.fontStyle;
  probe.style.letterSpacing = style.letterSpacing;
  probe.textContent = 'abcdefghijklmnopqrstuvwxyz';
  document.body.appendChild(probe);
  const advance = probe.getBoundingClientRect().width / 26;
  probe.remove();

  const hero = document.querySelector('.post-hero-img');
  const tile = document.querySelector('.post-full');
  const content = document.querySelector('.post-content');
  let contentWidth = null;
  if (content) {
    const cs = getComputedStyle(content);
    contentWidth = content.clientWidth
      - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  }

  return {
    columnWidth: rect.width,
    contentWidth: contentWidth,
    fontSize: parseFloat(style.fontSize),
    advance: advance,
    characters: advance > 0 ? rect.width / advance : 0,
    emMeasure: rect.width / parseFloat(style.fontSize),
    maxWidth: style.maxWidth,
    heroWidth: hero ? hero.getBoundingClientRect().width : null,
    heroHeight: hero ? hero.getBoundingClientRect().height : null,
    tileWidth: tile ? tile.clientWidth : null,
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  };
}"""


def _make_post(app, title: str, slug: str) -> int:
    from sqlalchemy import select

    from app.extensions import db
    from app.models import Post
    from app.utils import utc_now

    with app.app_context():
        existing = db.session.execute(select(Post).where(Post.slug == slug)).scalar_one_or_none()
        if existing is not None:
            return existing.id
        post = Post(
            title=title,
            slug=slug,
            body=BODY,
            published=True,
            published_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()
        return post.id


def _open(context, app_server, slug: str):
    page = context.new_page()
    page.goto(f"{app_server}/post/{slug}", wait_until="networkidle")
    return page


@pytest.mark.parametrize("width", [1280, 768])
def test_the_measure_holds_sixty_five_to_seventy_five_characters(
    browser, app_server, app, width
) -> None:
    """The reading column carries a comfortable number of characters per line.

    The count depends on the typeface, because the measure is expressed in em
    and the operator chooses the typeface. The four bundled sans families
    measure 61.5 (Space Grotesk), 67.5 (IBM Plex Sans), 70.4 (Atkinson
    Hyperlegible) and 74.1 (Inter) characters at 34em; no single cap puts all
    four inside this band, because the spread between the widest and the
    narrowest face is wider than the band itself. The typeface-independent
    contract is the em measure, which the next test pins.
    """
    _make_post(app, "Measure Check", "measure-check")

    context = browser.new_context(viewport={"width": width, "height": 900})
    try:
        page = _open(context, app_server, "measure-check")
        measured = page.evaluate(MEASURE_JS, ".prose")
        assert measured is not None

        assert MIN_CHARACTERS <= measured["characters"] <= MAX_CHARACTERS, (
            f"at {width}px the column carries {measured['characters']:.1f} characters: {measured}"
        )
    finally:
        context.close()


@pytest.mark.parametrize("width", [1280, 768])
def test_the_measure_is_thirty_four_ems_at_every_breakpoint(
    browser, app_server, app, width
) -> None:
    """The cap is a measure in em, so it holds whatever the typeface is."""
    _make_post(app, "Measure Ems", "measure-ems")

    context = browser.new_context(viewport={"width": width, "height": 900})
    try:
        page = _open(context, app_server, "measure-ems")
        measured = page.evaluate(MEASURE_JS, ".prose")
        assert measured is not None

        assert abs(measured["emMeasure"] - 34) < 0.05, (
            f"at {width}px the column measures {measured['emMeasure']:.2f}em: {measured}"
        )
    finally:
        context.close()


def test_the_measure_is_expressed_in_em(browser, app_server, app) -> None:
    """The cap scales with the prose font size, which changes at the breakpoint."""
    _make_post(app, "Measure Em", "measure-em")

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = _open(context, app_server, "measure-em")
        desktop = page.evaluate(MEASURE_JS, ".prose")
    finally:
        context.close()

    context = browser.new_context(viewport={"width": 768, "height": 900})
    try:
        page = _open(context, app_server, "measure-em")
        mobile = page.evaluate(MEASURE_JS, ".prose")
    finally:
        context.close()

    assert desktop["fontSize"] > mobile["fontSize"], "the breakpoint did not change the prose size"
    assert desktop["maxWidth"] != mobile["maxWidth"], (
        "the cap did not scale with the prose font size: "
        f"{desktop['maxWidth']} at {desktop['fontSize']}px, "
        f"{mobile['maxWidth']} at {mobile['fontSize']}px"
    )


def test_the_phone_layout_is_unchanged(browser, app_server, app) -> None:
    """At 390px the cap does not bind, so the column still fills its container."""
    _make_post(app, "Measure Phone", "measure-phone")

    context = browser.new_context(viewport={"width": 390, "height": 844})
    try:
        page = _open(context, app_server, "measure-phone")
        measured = page.evaluate(MEASURE_JS, ".prose")
        assert measured is not None

        assert measured["columnWidth"] < float(measured["maxWidth"].removesuffix("px")), (
            f"the cap binds at 390px: {measured}"
        )
        assert abs(measured["columnWidth"] - measured["contentWidth"]) < 2, (
            f"the phone column no longer fills the tile: {measured}"
        )
    finally:
        context.close()


def test_the_hero_keeps_the_full_width_of_its_tile(browser, app_server, app) -> None:
    """The measure narrows the text, never the image above it."""
    _make_post(app, "Measure Hero", "measure-hero")

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = _open(context, app_server, "measure-hero")
        measured = page.evaluate(MEASURE_JS, ".prose")
        assert measured is not None

        assert measured["heroWidth"] == measured["tileWidth"], (
            f"the hero is narrower than its tile: {measured}"
        )
        assert measured["heroWidth"] > measured["columnWidth"], (
            f"the hero is narrower than the reading column: {measured}"
        )
    finally:
        context.close()


def test_the_admin_preview_matches_the_published_post(browser, app_server, app) -> None:
    """The preview renders `.prose`, so it must carry the same measure."""
    post_id = _make_post(app, "Measure Preview", "measure-preview")

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/admin/login")
        page.fill('input[name="username"]', "admin")
        page.fill('input[name="password"]', os.environ["ADMIN_PASSWORD"])
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        page.goto(f"{app_server}/admin/edit/{post_id}", wait_until="networkidle")
        preview = page.evaluate(
            """() => {
              const el = document.querySelector('#markdown-preview');
              if (!el) return null;
              const style = getComputedStyle(el);
              return { maxWidth: style.maxWidth, fontSize: style.fontSize };
            }"""
        )
        assert preview is not None, "the admin editor has no markdown preview"

        published = _open(context, app_server, "measure-preview")
        measured = published.evaluate(MEASURE_JS, ".prose")
        published.close()

        assert preview["maxWidth"] == measured["maxWidth"], (
            f"the preview measure is {preview['maxWidth']}, the published measure is "
            f"{measured['maxWidth']}"
        )
    finally:
        context.close()


@pytest.mark.parametrize("width", [390, 768, 1280])
def test_the_post_page_has_no_horizontal_overflow(browser, app_server, app, width) -> None:
    """Narrowing the text must not introduce a horizontal scrollbar."""
    _make_post(app, "Measure Overflow", "measure-overflow")

    context = browser.new_context(viewport={"width": width, "height": 900})
    try:
        page = _open(context, app_server, "measure-overflow")
        measured = page.evaluate(MEASURE_JS, ".prose")
        assert measured is not None

        assert measured["scrollWidth"] <= measured["innerWidth"], (
            f"the page scrolls horizontally at {width}px: {measured}"
        )
    finally:
        context.close()
