"""Browser-level checks for the article furniture.

Two contracts are asserted here:

* the share panel stands below the article rather than between the hero and
  the first paragraph, so the article starts where the reader expects it;
* the structural elements — the table-of-contents title, the share label and
  the sidebar headings — take one shared voice that separates them from the
  content without competing with it.

Both are properties of the rendered page rather than of the stylesheet.
"""

from __future__ import annotations

import pytest

from tests.e2e.contrast_helpers import MEASURE_JS, contrast_ratio, parse_rgb

pytestmark = pytest.mark.e2e

MIN_TEXT_CONTRAST = 4.5

# The panel's own block: its height plus the margin that used to follow it.
# The plan's target was 100px against a 76px panel; the panel measures 70px,
# so the article gains 94px.
MIN_ARTICLE_LIFT = 90

FURNITURE_JS = """() => {
  const rect = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { top: r.top, bottom: r.bottom, height: r.height, width: r.width };
  };
  const bar = document.querySelector('.share-bar');
  const body = document.querySelector('.post-body');
  const content = document.querySelector('.post-content');
  const tldr = document.querySelector('.tldr');
  const first = document.querySelector('.post-body p');
  const barStyle = bar ? getComputedStyle(bar) : null;
  return {
    bar: rect(bar),
    body: rect(body),
    content: rect(content),
    tldr: rect(tldr),
    firstParagraph: rect(first),
    barMarginTop: barStyle ? parseFloat(barStyle.marginTop) : null,
    barMarginBottom: barStyle ? parseFloat(barStyle.marginBottom) : null,
    barControls: bar ? bar.querySelectorAll('.share-btn').length : 0,
    barNetworks: bar ? bar.querySelectorAll('a.share-btn').length : 0,
    barCopy: bar ? bar.querySelectorAll('.share-copy').length : 0,
    label: (() => {
      const el = document.querySelector('.share-label');
      if (!el) return null;
      const s = getComputedStyle(el);
      return {
        fontFamily: s.fontFamily,
        fontSize: s.fontSize,
        letterSpacing: s.letterSpacing,
        textTransform: s.textTransform,
        color: s.color,
      };
    })(),
    tocTitle: (() => {
      const el = document.querySelector('.post-toc-title');
      if (!el) return null;
      const s = getComputedStyle(el);
      return {
        fontFamily: s.fontFamily,
        fontSize: s.fontSize,
        letterSpacing: s.letterSpacing,
        textTransform: s.textTransform,
        color: s.color,
      };
    })(),
    sidebarTitle: (() => {
      const el = document.querySelector('.sidebar-title');
      if (!el) return null;
      const s = getComputedStyle(el);
      return {
        fontFamily: s.fontFamily,
        fontSize: s.fontSize,
        letterSpacing: s.letterSpacing,
        textTransform: s.textTransform,
        color: s.color,
      };
    })(),
    tocEntry: (() => {
      const el = document.querySelector('.post-toc a');
      if (!el) return null;
      const s = getComputedStyle(el);
      return {
        textDecorationLine: s.textDecorationLine,
        color: s.color,
        fontSize: s.fontSize,
      };
    })(),
    footerTags: document.querySelectorAll('.post-footer-tags .tag').length,
  };
}"""

FOCUS_JS = """() => {
  const el = document.activeElement;
  if (!el || el === document.body) return null;
  const style = getComputedStyle(el);
  return {
    tag: el.tagName,
    className: typeof el.className === 'string' ? el.className : '',
    inToc: !!el.closest('.post-toc'),
    outlineStyle: style.outlineStyle,
    outlineWidth: style.outlineWidth,
    outlineColor: style.outlineColor,
    focusVisible: el.matches(':focus-visible'),
  };
}"""


@pytest.fixture(scope="session")
def article_post(app, app_server):
    """A published post with a summary and enough headings for a contents list."""
    from app.extensions import db
    from app.models import Post
    from app.utils import utc_now

    body = (
        "An opening paragraph, so the article's first block of text is a\nparagraph and\nthe measurement of where the article starts is a measurement of the prose.\n\n"
        + "\n\n".join(
            f"## Section {index}\n\nParagraph {index}, long enough that the article has the "
            "length a real piece has, so the measurements below are of a real page."
            for index in range(1, 4)
        )
    )

    with app.app_context():
        post = Post(
            title="Article Furniture Post",
            slug="article-furniture-post",
            body=body,
            summary="A post with a summary, so the article has a TL;DR above it.",
            published=True,
            published_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()

    yield "article-furniture-post"


def _open(browser, app_server, path: str, width: int = 1280):
    context = browser.new_context(viewport={"width": width, "height": 900})
    page = context.new_page()
    page.goto(f"{app_server}{path}", wait_until="networkidle")
    return context, page


def test_the_share_panel_stands_below_the_article(browser, app_server, article_post) -> None:
    """The reader finishes the article and is offered sharing."""
    context, page = _open(browser, app_server, f"/post/{article_post}")
    try:
        page.wait_for_selector(".share-bar", timeout=10_000)
        furniture = page.evaluate(FURNITURE_JS)
        assert furniture["bar"] is not None
        assert furniture["body"] is not None
        assert furniture["bar"]["top"] >= furniture["body"]["bottom"], furniture
    finally:
        context.close()


def test_the_article_starts_higher(browser, app_server, article_post) -> None:
    """The panel's block is no longer between the hero and the article."""
    context, page = _open(browser, app_server, f"/post/{article_post}")
    try:
        page.wait_for_selector(".post-body", timeout=10_000)
        furniture = page.evaluate(FURNITURE_JS)
        assert furniture["firstParagraph"] is not None, furniture
        assert furniture["tldr"] is not None, furniture

        panel_block = furniture["bar"]["height"] + 24
        assert panel_block >= MIN_ARTICLE_LIFT, furniture

        gap = furniture["firstParagraph"]["top"] - furniture["tldr"]["bottom"]
        assert gap <= 40, f"something still stands between the summary and the article: {gap}px"

        assert furniture["firstParagraph"]["top"] < furniture["bar"]["top"], furniture
    finally:
        context.close()


def test_the_share_panel_keeps_every_control(browser, app_server, article_post) -> None:
    """Only its position changed."""
    context, page = _open(browser, app_server, f"/post/{article_post}")
    try:
        page.wait_for_selector(".share-bar", timeout=10_000)
        furniture = page.evaluate(FURNITURE_JS)
        assert furniture["barNetworks"] == 6, furniture
        assert furniture["barCopy"] == 1, furniture
        assert furniture["barControls"] == 7, furniture
    finally:
        context.close()


def test_the_share_label_takes_the_structural_voice(browser, app_server, article_post) -> None:
    """It names the group of controls; it does not read as content."""
    context, page = _open(browser, app_server, f"/post/{article_post}")
    try:
        page.wait_for_selector(".share-label", timeout=10_000)
        furniture = page.evaluate(FURNITURE_JS)
        label = furniture["label"]
        assert label is not None
        assert "mono" in label["fontFamily"].lower(), label
        assert label["textTransform"] == "uppercase", label
        assert float(label["letterSpacing"].replace("px", "")) > 0, label
    finally:
        context.close()


def test_the_contents_title_takes_the_structural_voice(browser, app_server, article_post) -> None:
    """The contents list is built by the page, and its title is a label."""
    context, page = _open(browser, app_server, f"/post/{article_post}")
    try:
        page.wait_for_selector(".post-toc-title", timeout=10_000)
        furniture = page.evaluate(FURNITURE_JS)
        title = furniture["tocTitle"]
        assert title is not None
        assert "mono" in title["fontFamily"].lower(), title
        assert title["textTransform"] == "uppercase", title
        assert float(title["letterSpacing"].replace("px", "")) > 0, title
    finally:
        context.close()


def test_the_sidebar_heading_takes_the_structural_voice(browser, app_server) -> None:
    """The sidebar headings are labels too."""
    context, page = _open(browser, app_server, "/")
    try:
        page.wait_for_selector(".sidebar-title", timeout=10_000)
        furniture = page.evaluate(FURNITURE_JS)
        title = furniture["sidebarTitle"]
        assert title is not None
        assert "mono" in title["fontFamily"].lower(), title
        assert title["textTransform"] == "uppercase", title
    finally:
        context.close()


def test_the_contents_entries_still_look_like_links(browser, app_server, article_post) -> None:
    """They are links, so they read as links and they clear the contrast floor."""
    context, page = _open(browser, app_server, f"/post/{article_post}")
    try:
        page.wait_for_selector(".post-toc a", timeout=10_000)
        furniture = page.evaluate(FURNITURE_JS)
        entry = furniture["tocEntry"]
        assert entry is not None
        assert entry["textDecorationLine"] == "underline", entry

        measured = page.evaluate(MEASURE_JS, ".post-toc a")
        assert measured is not None
        ratio = contrast_ratio(parse_rgb(measured["color"]), measured["background"])
        assert ratio >= MIN_TEXT_CONTRAST, f"{ratio:.2f}:1 — {measured}"
    finally:
        context.close()


def test_the_contents_entries_keep_a_focus_ring(browser, app_server, article_post) -> None:
    """A keyboard reader has to see where they are."""
    context, page = _open(browser, app_server, f"/post/{article_post}")
    try:
        page.wait_for_selector(".post-toc a", timeout=10_000)
        page.evaluate("() => document.body.focus()")

        focused = None
        for _ in range(80):
            page.keyboard.press("Tab")
            focused = page.evaluate(FOCUS_JS)
            if focused and focused["inToc"]:
                break

        assert focused is not None and focused["inToc"], "no contents entry took the focus"
        assert focused["focusVisible"] is True, focused
        assert focused["outlineStyle"] != "none", focused
        assert float(focused["outlineWidth"].replace("px", "")) >= 2, focused
    finally:
        context.close()


def test_the_post_page_does_not_overflow(browser, app_server, article_post) -> None:
    """A phone has no horizontal scrollbar."""
    context, page = _open(browser, app_server, f"/post/{article_post}", width=390)
    try:
        page.wait_for_selector(".post-body", timeout=10_000)
        overflow = page.evaluate(
            "() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth })"
        )
        assert overflow["scrollWidth"] <= overflow["innerWidth"], overflow
    finally:
        context.close()


def test_the_share_panel_wraps_on_a_phone(browser, app_server, article_post) -> None:
    """The controls wrap inside the panel rather than overflow it."""
    context, page = _open(browser, app_server, f"/post/{article_post}", width=390)
    try:
        page.wait_for_selector(".share-bar", timeout=10_000)
        furniture = page.evaluate(FURNITURE_JS)
        bar = furniture["bar"]
        assert bar is not None
        assert bar["width"] <= 390, bar
        assert furniture["barControls"] == 7, furniture
    finally:
        context.close()


def test_the_post_lists_every_tag(browser, app_server, app, article_post) -> None:
    """A card counts the tags it does not show; the post holds the whole list."""
    from app.extensions import db
    from app.models import Post, Tag

    with app.app_context():
        target = db.session.execute(
            db.select(Post).filter_by(slug="article-furniture-post")
        ).scalar_one()
        for index in range(3):
            target.tags.append(Tag(name=f"Furniture Tag {index}", slug=f"furniture-tag-{index}"))
        db.session.commit()

    context, page = _open(browser, app_server, f"/post/{article_post}")
    try:
        page.wait_for_selector(".post-footer-tags", timeout=10_000)
        furniture = page.evaluate(FURNITURE_JS)
        assert furniture["footerTags"] == 3, furniture
    finally:
        context.close()
