"""Browser-level checks for the public frontend interaction contracts.

These live under ``tests/e2e/`` rather than alongside the fast template and
source assertions on purpose: a live server thread shares its database with the
test that starts it, and the migration round-trip tests later run DDL against
the session database. Keeping the browser tests on the e2e application's own
database keeps the two suites independent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DIST_DIR = Path(__file__).resolve().parents[2] / "app" / "static" / "dist"
MANIFEST_PATH = DIST_DIR / ".vite" / "manifest.json"

requires_frontend_build = pytest.mark.skipif(
    not MANIFEST_PATH.exists(),
    reason="frontend bundle not built (run `npm run build`)",
)


def _make_post(app, title: str, slug: str, body: str = "# Heading\n\nSome body text.\n"):
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


@requires_frontend_build
def test_configured_default_scheme_survives_the_controller(browser, app_server, app):
    from app.context_processors import invalidate_settings_cache
    from app.extensions import db
    from app.models import SiteSettings

    slug = _make_post(app, "Scheme Post", "scheme-post")

    with app.app_context():
        settings = SiteSettings.get_instance()
        settings.theme_default_scheme = "light"
        db.session.commit()
        invalidate_settings_cache()

    context = browser.new_context(color_scheme="dark")
    page = context.new_page()
    try:
        page.goto(f"{app_server}/post/{slug}")
        page.wait_for_selector(".theme-toggle", timeout=15000)

        assert page.evaluate("document.documentElement.dataset.colorScheme") == "light"
        label = page.get_attribute(".theme-toggle", "aria-label")
        assert label and "Light" in label

        page.evaluate("localStorage.setItem('blog-color-scheme', 'dark')")
        page.reload()
        page.wait_for_selector(".theme-toggle", timeout=15000)

        assert page.evaluate("document.documentElement.dataset.colorScheme") == "dark"
        label = page.get_attribute(".theme-toggle", "aria-label")
        assert label and "Dark" in label
    finally:
        context.close()


@requires_frontend_build
def test_color_scheme_control_is_reachable_at_a_mobile_viewport(browser, app_server, app):
    slug = _make_post(app, "Mobile Scheme Post", "mobile-scheme-post")

    context = browser.new_context(viewport={"width": 375, "height": 800})
    page = context.new_page()
    try:
        page.goto(f"{app_server}/post/{slug}")
        page.wait_for_selector(".theme-toggle", timeout=15000)

        assert page.locator(".theme-toggle").is_visible()
        assert not page.evaluate("!!document.querySelector('.nav-links .theme-toggle')")
    finally:
        context.close()


@requires_frontend_build
def test_lightbox_opens_and_restores_page_scroll(browser, app_server, app):
    slug = _make_post(
        app,
        "Lightbox Post",
        "lightbox-post",
        body="# Heading\n\n![An image](/static/img/default-post-social.png)\n",
    )

    context = browser.new_context()
    page = context.new_page()
    try:
        page.goto(f"{app_server}/post/{slug}")
        page.wait_for_selector(".prose img", timeout=15000)

        assert page.evaluate("document.getElementById('lightbox').classList.contains('hidden')")

        page.locator(".prose img").first.click()
        page.wait_for_function(
            "() => !document.getElementById('lightbox').classList.contains('hidden')",
            timeout=10000,
        )

        assert page.evaluate("document.body.style.overflow") == "hidden"
        assert page.is_visible("#lightbox")

        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => document.getElementById('lightbox').classList.contains('hidden')",
            timeout=10000,
        )

        assert page.evaluate("document.body.style.overflow") == ""
    finally:
        context.close()
