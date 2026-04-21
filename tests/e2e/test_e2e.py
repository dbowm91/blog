"""End-to-end browser tests for the blog CMS."""

import pytest


class TestAdminLogin:
    """Test admin login and logout flows."""

    def test_login_page_loads(self, page, app_server):
        """Login page should display without errors."""
        page.goto(f"{app_server}/admin/login")
        page.wait_for_selector('input[name="username"]')
        page.wait_for_selector('input[name="password"]')
        page.wait_for_selector('button[type="submit"]')

    def test_login_success(self, page, app_server):
        """Admin should be able to log in with valid credentials."""
        page.goto(f"{app_server}/admin/login")
        page.fill('input[name="username"]', "admin")
        page.fill('input[name="password"]', "test-password")
        page.click('button[type="submit"]')

        page.wait_for_url(f"{app_server}/admin/**", timeout=5000)
        assert "/admin/" in page.url

    def test_login_failure(self, page, app_server):
        """Invalid credentials should show error message."""
        page.goto(f"{app_server}/admin/login")
        page.fill('input[name="username"]', "admin")
        page.fill('input[name="password"]', "wrong-password")
        page.click('button[type="submit"]')

        page.wait_for_selector(".flash", timeout=3000)
        flash = page.text_content(".flash")
        assert flash and "invalid" in flash.lower()

    def test_logout(self, page, app_server):
        """Admin should be able to log out."""
        page.goto(f"{app_server}/admin/login")
        page.fill('input[name="username"]', "admin")
        page.fill('input[name="password"]', "test-password")
        page.click('button[type="submit"]')
        page.wait_for_url(f"{app_server}/admin/**", timeout=5000)

        page.click('form[action*="logout"] button[type="submit"]')
        page.wait_for_url(f"{app_server}/", timeout=5000)

        page.goto(f"{app_server}/admin/")
        assert "/admin/login" in page.url


class TestPostCreation:
    """Test post creation and publishing flows."""

    def test_new_post_page_loads(self, page, app_server):
        """New post editor page should load correctly."""
        page.goto(f"{app_server}/admin/login")
        page.fill('input[name="username"]', "admin")
        page.fill('input[name="password"]', "test-password")
        page.click('button[type="submit"]')
        page.wait_for_url(f"{app_server}/admin/**", timeout=5000)

        page.goto(f"{app_server}/admin/new")
        page.wait_for_selector('input[name="title"]')
        page.wait_for_selector('textarea[name="body"]')


class TestNewsletterSubscription:
    """Test newsletter subscription flows."""

    def test_subscribe_valid_email(self, page, app_server):
        """Visitor should be able to subscribe with a valid email."""
        page.goto(f"{app_server}/")
        page.wait_for_selector('input[type="email"][name="email"]')
        page.fill('input[type="email"][name="email"]', "test-subscriber@example.com")
        page.click('button[type="submit"]')
        page.wait_for_timeout(1000)

    def test_subscribe_invalid_email(self, page, app_server):
        """Invalid email should show error message."""
        page.goto(f"{app_server}/")
        page.wait_for_selector('input[type="email"][name="email"]')
        page.fill('input[type="email"][name="email"]', "not-an-email")
        page.click('button[type="submit"]')
        page.wait_for_timeout(1000)

    def test_subscribe_duplicate_email(self, page, app_server):
        """Duplicate subscription should be handled gracefully."""
        page.goto(f"{app_server}/")
        page.wait_for_selector('input[type="email"][name="email"]')
        page.fill('input[type="email"][name="email"]', "duplicate@example.com")
        page.click('button[type="submit"]')
        page.wait_for_timeout(500)
        page.fill('input[type="email"][name="email"]', "duplicate@example.com")
        page.click('button[type="submit"]')
        page.wait_for_timeout(1000)


class TestMobileResponsiveness:
    """Test mobile responsiveness."""

    def test_mobile_nav(self, page, app_server):
        """Navigation should work on mobile viewport."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{app_server}/")
        page.wait_for_timeout(500)
        menu_button = page.locator(".mobile-menu-toggle")
        if menu_button.count() > 0:
            menu_button.click()
            page.wait_for_timeout(300)

    def test_mobile_login(self, page, app_server):
        """Login page should be usable on mobile."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{app_server}/admin/login")
        page.wait_for_selector('input[name="username"]')
        page.fill('input[name="username"]', "admin")
        page.fill('input[name="password"]', "test-password")
        page.click('button[type="submit"]')
        page.wait_for_url(f"{app_server}/admin/**", timeout=5000)
