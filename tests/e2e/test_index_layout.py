"""Browser-level checks for the index layout.

The index is the densest page on the site, and the contracts asserted here are
properties of the rendered page rather than of the stylesheet:

* the post list is a two-column grid on a wide viewport and one column below;
* a card is narrow enough that two of them sit beside the sidebar;
* a card shows at most four tags, and the chip that counts the rest carries a
  name that says what it counts;
* the summary is clamped to two lines;
* the sidebar is 200px wide, keeps its tag cloud and its feed link, and no
  page overflows horizontally.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

DENSITY_TAG = "Layout Density"
DENSITY_TAG_SLUG = "layout-density"
CARD_COUNT = 4
TAGS_PER_POST = 5
VISIBLE_TAGS = 4

LONG_SUMMARY = (
    "A summary long enough that it cannot fit on the two lines a card shows, "
    "so the clamp has something to clamp and the reader is sent to the post "
    "for the rest of it."
)

GRID_JS = """() => {
  const list = document.querySelector('.posts-list');
  if (!list) return null;
  const style = getComputedStyle(list);
  const tracks = style.gridTemplateColumns.split(' ').filter(Boolean);
  return {
    display: style.display,
    columns: style.gridTemplateColumns,
    trackCount: tracks.length,
    tracks: tracks.map((track) => Math.round(parseFloat(track))),
  };
}"""

CARDS_JS = """() => {
  const cards = [...document.querySelectorAll('.post-card')];
  if (!cards.length) return null;
  const rect = cards[0].getBoundingClientRect();
  const second = cards[1] ? cards[1].getBoundingClientRect() : null;
  return {
    count: cards.length,
    width: rect.width,
    height: rect.height,
    top: rect.top,
    left: rect.left,
    right: rect.right,
    secondLeft: second ? second.left : null,
    secondTop: second ? second.top : null,
  };
}"""

TITLE_TOPS_JS = """() => {
  return [...document.querySelectorAll('.post-card-title')].map((title) => {
    const rect = title.getBoundingClientRect();
    return { top: rect.top, left: rect.left, text: title.textContent.trim() };
  });
}"""

TAG_ROW_JS = """() => {
  const row = document.querySelector('.post-card .post-tags');
  if (!row) return null;
  const chip = row.querySelector('.tag-more');
  return {
    links: row.querySelectorAll('a.tag').length,
    chips: row.querySelectorAll('.tag-more').length,
    label: chip ? chip.getAttribute('aria-label') : null,
    text: chip ? chip.textContent.trim() : null,
  };
}"""

SUMMARY_JS = """() => {
  const summary = document.querySelector('.post-card .post-card-summary');
  if (!summary) return null;
  const style = getComputedStyle(summary);
  const rect = summary.getBoundingClientRect();
  const lineHeight = parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.5;
  return {
    height: rect.height,
    lineHeight,
    lines: Math.round((rect.height / lineHeight) * 100) / 100,
    clamp: style.webkitLineClamp || style.lineClamp,
    overflow: style.overflow,
    scrollHeight: summary.scrollHeight,
    clientHeight: summary.clientHeight,
  };
}"""

SIDEBAR_JS = """() => {
  const sidebar = document.querySelector('.sidebar');
  if (!sidebar) return null;
  const rect = sidebar.getBoundingClientRect();
  return {
    width: rect.width,
    titles: [...sidebar.querySelectorAll('.sidebar-title')].map((t) => t.textContent.trim()),
    hasRss: !!sidebar.querySelector('.rss-link'),
    hasTagCloud: !!sidebar.querySelector('.tag-cloud'),
    hasRecentPosts: sidebar.textContent.includes('Recent posts'),
  };
}"""

OVERFLOW_JS = """() => ({
  scrollWidth: document.documentElement.scrollWidth,
  innerWidth: window.innerWidth,
})"""


@pytest.fixture(scope="session")
def layout_posts(app, app_server):
    """Published posts that give the index enough cards to lay out.

    Each one carries five tags and a summary long enough to be clamped, and
    they share a tag so that a tag page shows exactly this set.
    """
    from app.extensions import db
    from app.models import Post, Tag
    from app.utils import utc_now

    with app.app_context():
        shared = Tag(name=DENSITY_TAG, slug=DENSITY_TAG_SLUG)
        db.session.add(shared)
        for index in range(CARD_COUNT):
            post = Post(
                title=f"Layout Density Post {index}",
                slug=f"layout-density-post-{index}",
                body=f"# Layout Density Post {index}\n\nA card for the index layout.",
                summary=LONG_SUMMARY,
                published=True,
                published_at=utc_now(),
            )
            post.tags.append(shared)
            for tag_index in range(TAGS_PER_POST - 1):
                post.tags.append(
                    Tag(
                        name=f"Layout Only {index} {tag_index}",
                        slug=f"layout-only-{index}-{tag_index}",
                    )
                )
            db.session.add(post)
        db.session.commit()

    yield DENSITY_TAG_SLUG


def test_the_index_is_two_columns_at_1280px(browser, app_server, layout_posts) -> None:
    """A wide viewport shows two cards per row."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/", wait_until="networkidle")
        page.wait_for_selector(".posts-list", timeout=10_000)

        grid = page.evaluate(GRID_JS)
        assert grid is not None
        assert grid["display"] == "grid", grid
        assert grid["trackCount"] == 2, grid
    finally:
        context.close()


def test_the_index_is_one_column_at_768px(browser, app_server, layout_posts) -> None:
    """Below the breakpoint the list stays a single column."""
    context = browser.new_context(viewport={"width": 768, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/", wait_until="networkidle")
        page.wait_for_selector(".posts-list", timeout=10_000)

        grid = page.evaluate(GRID_JS)
        assert grid is not None
        assert grid["trackCount"] == 1, grid
    finally:
        context.close()


def test_two_cards_sit_side_by_side(browser, app_server, layout_posts) -> None:
    """The second card starts where the first one ends."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/", wait_until="networkidle")
        page.wait_for_selector(".post-card", timeout=10_000)

        cards = page.evaluate(CARDS_JS)
        assert cards is not None
        assert cards["secondLeft"] is not None, cards
        assert cards["secondLeft"] >= cards["right"] - 1, cards
        assert abs(cards["secondTop"] - cards["top"]) < 2, cards
    finally:
        context.close()


def test_a_card_is_narrower_than_it_was(browser, app_server, layout_posts) -> None:
    """The card used to fill the column; now two of them fit across it."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/", wait_until="networkidle")
        page.wait_for_selector(".post-card", timeout=10_000)

        cards = page.evaluate(CARDS_JS)
        assert cards is not None
        assert 360 <= cards["width"] <= 560, cards
    finally:
        context.close()


def test_the_tag_row_is_capped(browser, app_server, layout_posts) -> None:
    """Four tags and a count; the count says what it counts."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/tag/{layout_posts}", wait_until="networkidle")
        page.wait_for_selector(".post-card .post-tags", timeout=10_000)

        row = page.evaluate(TAG_ROW_JS)
        assert row is not None
        assert row["links"] == VISIBLE_TAGS, row
        assert row["chips"] == 1, row
        assert row["text"] == f"+{TAGS_PER_POST - VISIBLE_TAGS}", row
    finally:
        context.close()


def test_the_count_chip_carries_an_accessible_name(browser, app_server, layout_posts) -> None:
    """A bare "+1" tells a screen reader nothing."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/tag/{layout_posts}", wait_until="networkidle")
        page.wait_for_selector(".post-card .tag-more", timeout=10_000)

        row = page.evaluate(TAG_ROW_JS)
        assert row is not None
        assert row["label"], "the count chip has no accessible name"
        assert str(TAGS_PER_POST) in row["label"], row
        assert "post page" in row["label"], row
    finally:
        context.close()


def test_the_summary_is_clamped_to_two_lines(browser, app_server, layout_posts) -> None:
    """A card is a summary of a post, not the post."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/tag/{layout_posts}", wait_until="networkidle")
        page.wait_for_selector(".post-card .post-card-summary", timeout=10_000)

        summary = page.evaluate(SUMMARY_JS)
        assert summary is not None
        assert summary["clamp"] == "2", summary
        assert summary["overflow"] == "hidden", summary
        assert summary["lines"] <= 2.05, summary
        assert summary["scrollHeight"] > summary["clientHeight"], (
            f"the summary was not clamped at all: {summary}"
        )
    finally:
        context.close()


@pytest.mark.parametrize("width", [1280, 768, 390])
def test_the_index_does_not_overflow(browser, app_server, layout_posts, width) -> None:
    """No horizontal scrollbar at any width."""
    context = browser.new_context(viewport={"width": width, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/", wait_until="networkidle")
        page.wait_for_selector(".posts-list", timeout=10_000)

        overflow = page.evaluate(OVERFLOW_JS)
        assert overflow["scrollWidth"] <= overflow["innerWidth"], overflow
    finally:
        context.close()


def test_the_sidebar_is_two_hundred_pixels(browser, app_server, layout_posts) -> None:
    """The block that needed the width is gone, so the column is narrower."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/", wait_until="networkidle")
        page.wait_for_selector(".sidebar", timeout=10_000)

        sidebar = page.evaluate(SIDEBAR_JS)
        assert sidebar is not None
        assert round(sidebar["width"]) == 200, sidebar
    finally:
        context.close()


def test_the_sidebar_keeps_its_own_sections(browser, app_server, layout_posts) -> None:
    """Only the duplicate list goes."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/", wait_until="networkidle")
        page.wait_for_selector(".sidebar", timeout=10_000)

        sidebar = page.evaluate(SIDEBAR_JS)
        assert sidebar is not None
        assert "Recent posts" not in sidebar["titles"], sidebar
        assert "Tags" in sidebar["titles"], sidebar
        assert sidebar["hasTagCloud"] is True, sidebar
        assert sidebar["hasRss"] is True, sidebar
    finally:
        context.close()


def test_the_index_shows_more_than_one_headline_per_screen(
    browser, app_server, layout_posts
) -> None:
    """The headline count above the fold doubled.

    Before this phase the list was a single column and a 900px window held one
    headline. It now holds the two headlines of the first row, and a second row
    of headlines starts inside the next 300px.
    """
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(f"{app_server}/", wait_until="networkidle")
        page.wait_for_selector(".post-card-title", timeout=10_000)

        titles = page.evaluate(TITLE_TOPS_JS)
        assert titles, "the index rendered no post titles"

        above_the_fold = [title for title in titles if title["top"] < 900]
        assert len(above_the_fold) >= 2, f"only {len(above_the_fold)} headline(s) fit: {titles}"

        within_two_screens = [title for title in titles if title["top"] < 1200]
        assert len(within_two_screens) >= 4, f"only {len(within_two_screens)} fit: {titles}"
    finally:
        context.close()
