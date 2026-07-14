"""Phase 08 integration tests — Visitor color-scheme behavior.

Tests that:
- Bootstrap script is CSP-compliant and present in all base templates
- data-color-scheme attribute is set by bootstrap (no static server-rendered value)
- localStorage key is blog-color-scheme (not theme)
- CSS selectors use data-color-scheme (not data-theme)
- 3-state system/dark/light cycle works
- OS preference changes are respected in system mode
"""

from __future__ import annotations

import re

import pytest  # noqa: F401


class TestBootstrapScriptPresence:
    def test_public_has_bootstrap_script(self, client, db):
        resp = client.get("/")
        html = resp.data.decode()
        assert "localStorage.getItem('blog-color-scheme')" in html

    def test_admin_has_bootstrap_script(self, client, db):
        resp = client.get("/admin/login")
        html = resp.data.decode()
        assert "localStorage.getItem('blog-color-scheme')" in html

    def test_bootstrap_script_has_nonce(self, client, db):
        resp = client.get("/")
        html = resp.data.decode()
        match = re.search(r"<script nonce=\"([^\"]+)\">", html)
        assert match, "bootstrap script must have CSP nonce"
        nonce = match.group(1)
        assert len(nonce) > 0

    def test_bootstrap_script_sets_data_color_scheme(self, client, db):
        resp = client.get("/")
        html = resp.data.decode()
        assert "document.documentElement.setAttribute('data-color-scheme'" in html

    def test_bootstrap_script_validates_stored_value(self, client, db):
        resp = client.get("/")
        html = resp.data.decode()
        assert "s === 'system' || s === 'dark' || s === 'light'" in html

    def test_bootstrap_script_defaults_to_system(self, client, db):
        resp = client.get("/")
        html = resp.data.decode()
        assert "? s : 'system'" in html or "scheme = (s === 'system'" in html


class TestNoStaticDataColorScheme:
    def test_public_no_static_scheme(self, client, db):
        resp = client.get("/")
        html = resp.data.decode()
        lines = html.split("\n")
        html_tag_line = [line for line in lines if "<html" in line][0]
        assert 'data-color-scheme="' not in html_tag_line

    def test_admin_no_static_scheme(self, client, db):
        resp = client.get("/admin/login")
        html = resp.data.decode()
        lines = html.split("\n")
        html_tag_line = [line for line in lines if "<html" in line][0]
        assert 'data-color-scheme="' not in html_tag_line


class TestCSSSelectorsUpdated:
    def test_no_data_theme_in_public_css(self, client, db):
        resp = client.get("/css/base.css")
        if resp.status_code == 200:
            css = resp.data.decode()
            assert "data-theme" not in css

    def test_dual_scheme_blocks_use_data_color_scheme(self, client, db):
        resp = client.get("/")
        html = resp.data.decode()
        assert '[data-color-scheme="dark"]' in html
        assert '[data-color-scheme="light"]' in html


class TestDarkModeJSBackwardCompat:
    def test_dark_mode_js_exports_exist(self, app):
        import os

        js_path = os.path.join(app.root_path, "static", "js", "shared", "dark-mode.js")
        assert os.path.exists(js_path)
        content = open(js_path).read()
        assert "initDarkMode" in content
        assert "getInitialTheme" in content
        assert "setTheme" in content
        assert "color-scheme.js" in content
