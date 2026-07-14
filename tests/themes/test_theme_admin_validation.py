"""Admin theme validation tests — Workstream B.

Ensures invalid/malicious theme names never produce admin 500 responses.
"""

from __future__ import annotations


class TestAdminSettingsValidation:
    def test_invalid_dark_theme_name_flash(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme",
            data={
                "theme_dark_name": "../../../etc/passwd",
                "theme_light_name": "Catppuccin Latte",
                "theme_default_scheme": "system",
                "syntax_theme": "prism",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "error" in html.lower() or "invalid" in html.lower() or "not found" in html.lower()

    def test_control_chars_in_theme_name(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme",
            data={
                "theme_dark_name": "theme\x00name",
                "theme_light_name": "Catppuccin Latte",
                "theme_default_scheme": "system",
                "syntax_theme": "prism",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_overlong_theme_name(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme",
            data={
                "theme_dark_name": "A" * 500,
                "theme_light_name": "Catppuccin Latte",
                "theme_default_scheme": "system",
                "syntax_theme": "prism",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_preview_invalid_theme_returns_400(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme/preview",
            data={
                "theme_dark_name": "../../../etc/passwd",
                "theme_light_name": "Catppuccin Latte",
            },
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_preview_control_chars_returns_400(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme/preview",
            data={
                "theme_dark_name": "theme\x00name",
                "theme_light_name": "Catppuccin Latte",
            },
        )
        assert resp.status_code == 400

    def test_refresh_handles_registry_error(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme/refresh",
            follow_redirects=True,
        )
        assert resp.status_code == 200
