"""Browser-level checks for the admin and public UI defects found in review.

These run against the e2e application's own database, so they live under
``tests/e2e/`` rather than next to the fast source assertions in
``tests/test_admin_ui_fixes.py``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

DIST_DIR = Path(__file__).resolve().parents[2] / "app" / "static" / "dist"
MANIFEST_PATH = DIST_DIR / ".vite" / "manifest.json"

requires_frontend_build = pytest.mark.skipif(
    not MANIFEST_PATH.exists(),
    reason="frontend bundle not built (run `npm run build`)",
)


def _make_post(
    app,
    title: str,
    slug: str,
    body: str = "# Heading\n\nSome body text.\n",
    published: bool = True,
):
    from app.extensions import db
    from app.models import Post
    from app.utils import utc_now

    with app.app_context():
        post = Post(
            title=title,
            slug=slug,
            body=body,
            published=published,
            published_at=utc_now() if published else None,
        )
        db.session.add(post)
        db.session.commit()
        return post.slug


def _login(page, app_server):
    page.goto(f"{app_server}/admin/login")
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', os.environ["ADMIN_PASSWORD"])
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


@requires_frontend_build
def test_nav_labels_are_centred_and_underlined_directly_below(browser, app_server, app):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        # The index page is where a nav link carries the active state.
        page.goto(f"{app_server}/")
        page.wait_for_selector(".nav-links a.active", timeout=15000)

        geometry = page.evaluate(
            """() => {
              const a = document.querySelector('.nav-links a.active');
              const label = a.querySelector('.nav-link-text');
              const cs = getComputedStyle(label, '::after');
              const lr = label.getBoundingClientRect();
              const range = document.createRange();
              range.selectNodeContents(label);
              const tr = range.getBoundingClientRect();
              const underlineTop = (lr.bottom - parseFloat(cs.bottom || '0'))
                                   - parseFloat(cs.height || '0');
              const nav = document.querySelector('.navbar').getBoundingClientRect();
              return {
                textMid: (tr.top + tr.bottom) / 2,
                navMid: nav.top + nav.height / 2,
                gap: underlineTop - tr.bottom,
              };
            }"""
        )

        # The label sits on the vertical centre of the bar, not high in it.
        assert abs(geometry["textMid"] - geometry["navMid"]) <= 3
        # The tick sits directly under the text instead of at the bottom of
        # the 44px touch target.
        assert 0 <= geometry["gap"] <= 8
    finally:
        context.close()


@requires_frontend_build
def test_share_icons_are_centred_in_their_buttons(browser, app_server, app):
    slug = _make_post(app, "Share Post", "share-post")

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        page.goto(f"{app_server}/post/{slug}")
        page.wait_for_selector(".share-btn", timeout=15000)

        offsets = page.evaluate(
            """() => [...document.querySelectorAll('.share-btn')].map(b => {
                 const br = b.getBoundingClientRect();
                 const svg = b.querySelector('svg');
                 if (!svg) return null;
                 const sr = svg.getBoundingClientRect();
                 return Math.max(Math.abs((sr.x + sr.width / 2) - (br.x + br.width / 2)),
                                Math.abs((sr.y + sr.height / 2) - (br.y + br.height / 2)));
               }).filter(v => v !== null)"""
        )

        assert offsets, "no share buttons rendered"
        assert max(offsets) <= 1.5, f"share icons off centre by {max(offsets)}px"
    finally:
        context.close()


@requires_frontend_build
def test_dashboard_list_header_lines_up_with_the_rows(browser, app_server, app):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        _login(page, app_server)
        page.goto(f"{app_server}/admin/")
        page.wait_for_selector(".post-list-item", timeout=15000)

        columns = page.evaluate(
            """() => {
              const header = [...document.querySelector('.post-list-header').children]
                  .map(e => Math.round(e.getBoundingClientRect().x));
              const item = [...document.querySelector('.post-list-item').children]
                  .map(e => Math.round(e.getBoundingClientRect().x));
              return {header, item};
            }"""
        )

        assert columns["header"], "no header cells"
        assert columns["header"] == columns["item"][: len(columns["header"])]
    finally:
        context.close()


@requires_frontend_build
def test_users_list_header_lines_up_with_the_rows(browser, app_server, app):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        _login(page, app_server)
        page.goto(f"{app_server}/admin/users")
        page.wait_for_selector(".post-list-item", timeout=15000)

        columns = page.evaluate(
            """() => {
              const header = [...document.querySelector('.post-list-header').children]
                  .map(e => Math.round(e.getBoundingClientRect().x));
              const item = [...document.querySelector('.post-list-item').children]
                  .map(e => Math.round(e.getBoundingClientRect().x));
              return {header, item};
            }"""
        )

        assert columns["header"], "no header cells"
        assert columns["header"] == columns["item"][: len(columns["header"])]
    finally:
        context.close()


@requires_frontend_build
def test_admin_inputs_are_not_browser_default_white(browser, app_server, app):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        _login(page, app_server)
        page.goto(f"{app_server}/admin/users")
        page.wait_for_selector('.create-user-form input[name="username"]', timeout=15000)

        background = page.evaluate(
            """() => getComputedStyle(
                   document.querySelector('.create-user-form input[name="username"]')
               ).backgroundColor"""
        )

        assert background not in ("rgb(255, 255, 255)", "rgba(0, 0, 0, 0)")
    finally:
        context.close()


@requires_frontend_build
def test_filter_links_keep_the_viewport_position(browser, app_server, app):
    # The list has to be long enough that the page scrolls both before and
    # after the filter is applied.
    for i in range(12):
        _make_post(app, f"Published {i}", f"published-{i}")
        _make_post(app, f"Draft {i}", f"draft-{i}", published=False)

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        _login(page, app_server)
        page.goto(f"{app_server}/admin/")
        page.wait_for_selector(".filter-tabs .filter-link", timeout=15000)

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(200)
        before = page.evaluate("window.scrollY")
        assert before > 0, "dashboard is not scrollable"

        page.click(".filter-tabs .filter-link >> text=Draft")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)

        after = page.evaluate("window.scrollY")
        assert after > 0, "the filter navigation threw the reader back to the top"
    finally:
        context.close()


@requires_frontend_build
def test_analytics_page_renders(browser, app_server, app):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        _login(page, app_server)
        response = page.goto(f"{app_server}/admin/analytics")
        assert response.status == 200
        assert page.locator("h1").inner_text().strip() == "Analytics"
    finally:
        context.close()


@requires_frontend_build
def test_theme_preview_renders_the_selected_theme(browser, app_server, app):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        _login(page, app_server)
        page.goto(f"{app_server}/admin/settings")
        page.wait_for_selector("#theme_dark_name", timeout=15000)

        page.select_option("#theme_dark_name", "Nord")
        page.click(".theme-preview-btn >> nth=0")
        page.wait_for_timeout(1500)

        preview = page.evaluate(
            """() => { const c = document.querySelector('#theme-preview-container');
                 const cs = getComputedStyle(c);
                 return {scheme: c.getAttribute('data-color-scheme'),
                         bg: cs.getPropertyValue('--bg').trim(),
                         pageBg: getComputedStyle(document.documentElement)
                                     .getPropertyValue('--bg').trim()}; }"""
        )

        assert preview["scheme"] == "dark"
        assert preview["bg"].lower() == "#2e3440", preview["bg"]
        # The preview is scoped to its container and does not repaint the panel.
        assert preview["pageBg"].lower() != "#2e3440"
    finally:
        context.close()


@requires_frontend_build
def test_theme_preview_does_not_block_the_following_save(browser, app_server, app):
    """The preview used to consume the page's only CSRF token."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        _login(page, app_server)
        page.goto(f"{app_server}/admin/settings")
        page.wait_for_selector("#theme_dark_name", timeout=15000)

        page.select_option("#theme_dark_name", "Nord")
        page.click(".theme-preview-btn >> nth=0")
        page.wait_for_timeout(1500)

        with page.expect_navigation(wait_until="networkidle"):
            page.click("button:has-text('Save Theme Settings')")

        assert page.url.endswith("/admin/settings")
        assert page.query_selector("#theme_dark_name").input_value() == "Nord"
    finally:
        context.close()


@requires_frontend_build
def test_admin_panel_exposes_the_colour_scheme_toggle(browser, app_server, app):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        _login(page, app_server)
        page.goto(f"{app_server}/admin/")
        page.wait_for_selector(".nav-actions button.theme-toggle", timeout=15000)

        toggle = page.locator(".nav-actions button.theme-toggle")
        box = toggle.bounding_box()
        assert box and box["width"] >= 44 and box["height"] >= 44

        before = page.evaluate("localStorage.getItem('blog-color-scheme')")
        toggle.click()
        page.wait_for_timeout(300)
        after = page.evaluate("localStorage.getItem('blog-color-scheme')")
        assert before != after
    finally:
        context.close()
