"""End-to-end browser tests for visitor color-scheme behavior (Phase 08).

Tests that the bootstrap script, toggle control, localStorage persistence,
and CSS selectors work correctly in a real browser.
"""

import pytest

pytestmark = pytest.mark.e2e


class TestColorSchemeBootstrap:
    """Verify bootstrap sets data-color-scheme before first paint."""

    def test_html_gets_data_color_scheme_attribute(self, page, app_server):
        page.goto(f"{app_server}/")
        scheme = page.evaluate("document.documentElement.getAttribute('data-color-scheme')")
        assert scheme in ("system", "dark", "light")

    def test_default_without_stored_preference(self, page, app_server):
        page.goto(f"{app_server}/")
        page.evaluate("localStorage.removeItem('blog-color-scheme')")
        page.reload()
        page.wait_for_load_state("domcontentloaded")
        scheme = page.evaluate("document.documentElement.getAttribute('data-color-scheme')")
        assert scheme in ("dark", "light")

    def test_bootstrap_runs_before_domcontentloaded(self, page, app_server):
        page.goto(f"{app_server}/")
        has_bootstrap = page.evaluate(
            "typeof window.__colorSchemeBootstrap !== 'undefined' "
            "|| document.documentElement.hasAttribute('data-color-scheme')"
        )
        assert has_bootstrap


class TestColorSchemeToggle:
    """Verify the toggle button cycles through schemes."""

    def test_toggle_exists(self, page, app_server):
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        toggle = page.locator("button.theme-toggle")
        assert toggle.count() > 0

    def test_toggle_aria_label(self, page, app_server):
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        toggle = page.locator("button.theme-toggle")
        label = toggle.get_attribute("aria-label")
        assert label and "Color scheme:" in label

    def test_toggle_cycles_system_to_dark(self, page, app_server):
        page.evaluate("localStorage.setItem('blog-color-scheme', 'system')")
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)

        page.locator("button.theme-toggle").click()
        page.wait_for_timeout(200)

        stored = page.evaluate("localStorage.getItem('blog-color-scheme')")
        assert stored == "dark"

    def test_toggle_cycles_dark_to_light(self, page, app_server):
        page.evaluate("localStorage.setItem('blog-color-scheme', 'dark')")
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)

        page.locator("button.theme-toggle").click()
        page.wait_for_timeout(200)

        stored = page.evaluate("localStorage.getItem('blog-color-scheme')")
        assert stored == "light"

    def test_toggle_cycles_light_to_system(self, page, app_server):
        page.evaluate("localStorage.setItem('blog-color-scheme', 'light')")
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)

        page.locator("button.theme-toggle").click()
        page.wait_for_timeout(200)

        stored = page.evaluate("localStorage.getItem('blog-color-scheme')")
        assert stored == "system"

    def test_toggle_updates_aria_label(self, page, app_server):
        page.evaluate("localStorage.setItem('blog-color-scheme', 'system')")
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)

        toggle = page.locator("button.theme-toggle")
        initial_label = toggle.get_attribute("aria-label")

        toggle.click()
        page.wait_for_timeout(200)

        new_label = toggle.get_attribute("aria-label")
        assert new_label != initial_label


class TestColorSchemePersistence:
    """Verify preference persists across reloads."""

    def test_dark_preference_survives_reload(self, page, app_server):
        page.goto(f"{app_server}/")
        page.evaluate("localStorage.setItem('blog-color-scheme', 'dark')")
        page.reload()
        page.wait_for_load_state("domcontentloaded")

        stored = page.evaluate("localStorage.getItem('blog-color-scheme')")
        assert stored == "dark"
        scheme = page.evaluate("document.documentElement.getAttribute('data-color-scheme')")
        assert scheme == "dark"

    def test_light_preference_survives_reload(self, page, app_server):
        page.goto(f"{app_server}/")
        page.evaluate("localStorage.setItem('blog-color-scheme', 'light')")
        page.reload()
        page.wait_for_load_state("domcontentloaded")

        stored = page.evaluate("localStorage.getItem('blog-color-scheme')")
        assert stored == "light"
        scheme = page.evaluate("document.documentElement.getAttribute('data-color-scheme')")
        assert scheme == "light"


class TestColorSchemeInvalidStorage:
    """Verify recovery from invalid or legacy localStorage values."""

    def test_invalid_value_defaults_to_system(self, page, app_server):
        page.goto(f"{app_server}/")
        page.evaluate("localStorage.setItem('blog-color-scheme', 'garbage-value')")
        page.reload()
        page.wait_for_load_state("domcontentloaded")

        scheme = page.evaluate("document.documentElement.getAttribute('data-color-scheme')")
        assert scheme in ("dark", "light")

    def test_legacy_theme_dark_migrates(self, page, app_server):
        page.goto(f"{app_server}/")
        page.evaluate("localStorage.setItem('theme', 'dark')")
        page.evaluate("localStorage.removeItem('blog-color-scheme')")
        page.reload()
        page.wait_for_load_state("domcontentloaded")

        scheme = page.evaluate("document.documentElement.getAttribute('data-color-scheme')")
        assert scheme in ("dark", "light")


class TestColorSchemeStorageException:
    """Verify graceful handling when localStorage throws."""

    def test_storage_exception_does_not_crash(self, page, app_server):
        page.goto(f"{app_server}/")
        page.evaluate("""
            Object.defineProperty(window, 'localStorage', {
                value: {
                    getItem: () => { throw new Error('QuotaExceededError'); },
                    setItem: () => { throw new Error('QuotaExceededError'); },
                    removeItem: () => {},
                    clear: () => {}
                },
                writable: false
            });
        """)
        page.reload()
        page.wait_for_load_state("domcontentloaded")

        scheme = page.evaluate("document.documentElement.getAttribute('data-color-scheme')")
        assert scheme in ("dark", "light")


class TestColorSchemeCSS:
    """Verify CSS uses data-color-scheme selectors, not data-theme."""

    def test_no_data_theme_in_css(self, page, app_server):
        resp = page.goto(f"{app_server}/css/base.css")
        css = resp.text()
        assert "data-theme" not in css

    def test_inline_styles_use_data_color_scheme(self, page, app_server):
        page.goto(f"{app_server}/")
        html = page.content()
        assert '[data-color-scheme="dark"]' in html
        assert '[data-color-scheme="light"]' in html

    def test_dark_palette_on_root(self, page, app_server):
        page.goto(f"{app_server}/")
        html = page.content()
        assert ":root," in html or ":root {" in html
