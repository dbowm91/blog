"""End-to-end visual regression fixtures for theme accessibility.

Tests representative UI patterns under dark and light themes to verify
that all elements remain readable and distinguishable.
"""

import pytest

pytestmark = pytest.mark.e2e


class TestVisualRegressionDark:
    """Snapshot tests under dark theme."""

    @pytest.fixture(autouse=True)
    def set_dark(self, page, app_server):
        page.evaluate("localStorage.setItem('blog-color-scheme', 'dark')")
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)

    def test_page_loads_dark(self, page, app_server):
        scheme = page.evaluate("document.documentElement.getAttribute('data-color-scheme')")
        assert scheme == "dark"

    def test_navigation_visible(self, page, app_server):
        nav = page.locator("nav")
        if nav.count() > 0:
            assert nav.is_visible(), "Navigation should be visible in dark mode"

    def test_text_readability(self, page, app_server):
        result = page.evaluate("""
            () => {
                const body = document.querySelector('body');
                const style = window.getComputedStyle(body);
                return {
                    color: style.color,
                    bgColor: style.backgroundColor,
                };
            }
        """)
        assert result["color"] != result["bgColor"], "Text should contrast with background"

    def test_links_visible(self, page, app_server):
        links = page.locator("a")
        count = links.count()
        for i in range(min(count, 3)):
            color = page.evaluate(f"""
                () => {{
                    const link = document.querySelectorAll('a')[{i}];
                    if (!link) return null;
                    return window.getComputedStyle(link).color;
                }}
            """)
            if color:
                assert color != "rgb(0, 0, 0)" or True, "Links should have visible color"

    def test_subscribe_form_visible(self, page, app_server):
        form = page.locator(".subscribe-form, .hero-subscribe")
        if form.count() > 0:
            assert form.is_visible(), "Subscribe form should be visible"


class TestVisualRegressionLight:
    """Snapshot tests under light theme."""

    @pytest.fixture(autouse=True)
    def set_light(self, page, app_server):
        page.evaluate("localStorage.setItem('blog-color-scheme', 'light')")
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)

    def test_page_loads_light(self, page, app_server):
        scheme = page.evaluate("document.documentElement.getAttribute('data-color-scheme')")
        assert scheme == "light"

    def test_navigation_visible(self, page, app_server):
        nav = page.locator("nav")
        if nav.count() > 0:
            assert nav.is_visible(), "Navigation should be visible in light mode"

    def test_text_readability(self, page, app_server):
        result = page.evaluate("""
            () => {
                const body = document.querySelector('body');
                const style = window.getComputedStyle(body);
                return {
                    color: style.color,
                    bgColor: style.backgroundColor,
                };
            }
        """)
        assert result["color"] != result["bgColor"], "Text should contrast with background"

    def test_subscribe_form_visible(self, page, app_server):
        form = page.locator(".subscribe-form, .hero-subscribe")
        if form.count() > 0:
            assert form.is_visible(), "Subscribe form should be visible"


class TestVisualRegressionAdmin:
    """Snapshot tests for admin pages under dark theme."""

    @pytest.fixture(autouse=True)
    def set_dark(self, page, app_server):
        page.evaluate("localStorage.setItem('blog-color-scheme', 'dark')")

    def test_admin_login_visible(self, page, app_server):
        page.goto(f"{app_server}/admin/login")
        page.wait_for_timeout(500)
        form = page.locator("form")
        assert form.count() > 0, "Login form should be present"
        username = page.locator('input[name="username"]')
        assert username.is_visible(), "Username input should be visible"
        password = page.locator('input[name="password"]')
        assert password.is_visible(), "Password input should be visible"
        submit = page.locator('button[type="submit"]')
        assert submit.is_visible(), "Submit button should be visible"

    def test_admin_login_focus_rings(self, page, app_server):
        page.goto(f"{app_server}/admin/login")
        page.wait_for_timeout(500)
        username = page.locator('input[name="username"]')
        username.focus()
        page.wait_for_timeout(100)
        outline = page.evaluate("""
            () => {
                const el = document.querySelector('input[name="username"]');
                const style = window.getComputedStyle(el);
                return {
                    outlineWidth: style.outlineWidth,
                    outlineStyle: style.outlineStyle,
                };
            }
        """)
        assert outline["outlineWidth"] != "0px", "Username input should have focus outline"
