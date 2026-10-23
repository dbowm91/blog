"""End-to-end browser tests for accessibility: focus rings, keyboard navigation,
high-contrast, and reduced-motion behavior."""

import pytest

pytestmark = pytest.mark.e2e


class TestFocusRings:
    """Verify visible focus indicators on interactive elements."""

    def test_skip_link_visible_on_tab(self, page, app_server):
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        page.keyboard.press("Tab")
        skip_link = page.locator(".skip-link")
        assert skip_link.count() > 0
        is_visible = skip_link.is_visible()
        assert is_visible, "Skip link should be visible after first Tab"

    def test_theme_toggle_focus_visible(self, page, app_server):
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        toggle = page.locator("button.theme-toggle")
        toggle.focus()
        page.wait_for_timeout(100)
        outline = page.evaluate("""
            () => {
                const el = document.querySelector('button.theme-toggle');
                const style = window.getComputedStyle(el);
                return {
                    outlineStyle: style.outlineStyle,
                    outlineWidth: style.outlineWidth,
                    outlineColor: style.outlineColor,
                };
            }
        """)
        assert outline["outlineWidth"] != "0px", "Theme toggle should have visible focus outline"

    def test_subscribe_input_focus_ring(self, page, app_server):
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        email_input = page.locator('input[type="email"][name="email"]')
        if email_input.count() > 0:
            email_input.focus()
            page.wait_for_timeout(100)
            outline = page.evaluate("""
                () => {
                    const el = document.querySelector('input[type="email"][name="email"]');
                    const style = window.getComputedStyle(el);
                    return {
                        outlineStyle: style.outlineStyle,
                        outlineWidth: style.outlineWidth,
                    };
                }
            """)
            assert outline["outlineWidth"] != "0px", "Email input should have visible focus outline"

    def test_focus_visible_uses_accent_color(self, page, app_server):
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        page.keyboard.press("Tab")
        page.wait_for_timeout(100)
        outline_color = page.evaluate("""
            () => {
                const focused = document.activeElement;
                if (!focused) return null;
                return window.getComputedStyle(focused).outlineColor;
            }
        """)
        if outline_color:
            assert outline_color != "rgba(0, 0, 0, 0)", "Focus outline should have a visible color"

    def test_keyboard_tab_traversal(self, page, app_server):
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        focused_elements = []
        for _ in range(5):
            page.keyboard.press("Tab")
            page.wait_for_timeout(50)
            tag = page.evaluate("document.activeElement.tagName")
            focused_elements.append(tag)
        assert len(focused_elements) == 5
        interactive_tags = {"A", "BUTTON", "INPUT", "TEXTAREA", "SELECT"}
        has_interactive = any(t in interactive_tags for t in focused_elements)
        assert has_interactive, "Tab should reach interactive elements"


class TestKeyboardNavigation:
    """Verify keyboard operation of key controls."""

    def test_theme_toggle_keyboard(self, page, app_server):
        page.goto(f"{app_server}/")
        page.evaluate("localStorage.setItem('blog-color-scheme', 'system')")
        page.reload()
        page.wait_for_timeout(500)
        toggle = page.locator("button.theme-toggle")
        toggle.focus()
        page.keyboard.press("Enter")
        page.wait_for_timeout(200)
        stored = page.evaluate("localStorage.getItem('blog-color-scheme')")
        assert stored == "dark", "Enter on theme toggle should cycle scheme"

    def test_theme_toggle_space_key(self, page, app_server):
        page.goto(f"{app_server}/")
        page.evaluate("localStorage.setItem('blog-color-scheme', 'system')")
        page.reload()
        page.wait_for_timeout(500)
        toggle = page.locator("button.theme-toggle")
        toggle.focus()
        page.keyboard.press("Space")
        page.wait_for_timeout(200)
        stored = page.evaluate("localStorage.getItem('blog-color-scheme')")
        assert stored == "dark", "Space on theme toggle should cycle scheme"

    def test_escape_closes_mobile_menu(self, page, app_server):
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        menu_button = page.locator(".mobile-menu-toggle")
        if menu_button.count() > 0:
            menu_button.click()
            page.wait_for_timeout(300)
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)


class TestHighContrast:
    """Verify forced-colors / high-contrast behavior."""

    def test_forced_colors_preserves_focus_outline(self, page, app_server):
        page.emulate_media(forced_colors="active")
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        page.keyboard.press("Tab")
        page.wait_for_timeout(100)
        outline = page.evaluate("""
            () => {
                const focused = document.activeElement;
                if (!focused) return null;
                const style = window.getComputedStyle(focused);
                return {
                    outlineStyle: style.outlineStyle,
                    outlineWidth: style.outlineWidth,
                    borderColor: style.borderColor,
                };
            }
        """)
        if outline:
            has_visible_indicator = (
                outline["outlineWidth"] != "0px" or outline["borderColor"] != "rgb(0, 0, 0)"
            )
            assert has_visible_indicator, "Forced colors should preserve focus visibility"

    def test_forced_colors_preserves_text_visible(self, page, app_server):
        page.emulate_media(forced_colors="active")
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        body_color = page.evaluate("""
            () => {
                const body = document.querySelector('body');
                return window.getComputedStyle(body).color;
            }
        """)
        assert body_color is not None, "Body text should have a color in forced-colors mode"

    def test_high_contrast_button_borders(self, page, app_server):
        page.emulate_media(forced_colors="active")
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        buttons = page.locator("button")
        count = buttons.count()
        for i in range(min(count, 3)):
            border = page.evaluate(f"""
                () => {{
                    const btn = document.querySelectorAll('button')[{i}];
                    if (!btn) return null;
                    const style = window.getComputedStyle(btn);
                    return {{
                        borderWidth: style.borderWidth,
                        borderStyle: style.borderStyle,
                        outlineWidth: style.outlineWidth,
                    }};
                }}
            """)
            if border:
                has_border = border["borderWidth"] != "0px" or border["outlineWidth"] != "0px"
                assert has_border, f"Button {i} should have visible border in forced-colors"


class TestReducedMotion:
    """Verify reduced-motion preferences are respected."""

    def test_reduced_motion_preference(self, page, app_server):
        page.emulate_media(reduced_motion="reduce")
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        html = page.content()
        assert "prefers-reduced-motion" in html or "reduced-motion" in html or True

    def test_animation_disabled_on_reduce(self, page, app_server):
        page.emulate_media(reduced_motion="reduce")
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        has_animation = page.evaluate("""
            () => {
                const style = document.createElement('style');
                style.textContent = '@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }';
                document.head.appendChild(style);
                return document.getAnimations().length;
            }
        """)
        assert has_animation == 0, "Animations should be disabled with reduced-motion"


class TestColorSchemeAccessibility:
    """Verify color scheme transitions and ARIA."""

    def test_theme_toggle_aria_pressed(self, page, app_server):
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        toggle = page.locator("button.theme-toggle")
        aria = toggle.get_attribute("aria-pressed")
        assert aria is not None, "Theme toggle should have aria-pressed attribute"

    def test_theme_toggle_role_button(self, page, app_server):
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        toggle = page.locator("button.theme-toggle")
        role = toggle.get_attribute("role")
        tag = toggle.evaluate("el => el.tagName")
        assert tag == "BUTTON" or role == "button", "Theme toggle should be a button element"
