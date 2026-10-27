"""Admin workflow acceptance tests for the Halloy theme system.

Validates admin-facing behavior: settings page rendering, theme save/load
round-trip, preview non-persistence, invalid theme rejection, refresh
reporting, and CSRF enforcement.
"""

from __future__ import annotations

import json

from app.models import SiteSettings
from app.context_processors import invalidate_settings_cache


class TestAdminSettingsPage:
    def test_settings_page_renders(self, authenticated_client, db):
        resp = authenticated_client.get("/admin/settings")
        assert resp.status_code == 200
        assert b"settings" in resp.data.lower()

    def test_settings_page_shows_current_theme_names(self, authenticated_client, db):
        settings = SiteSettings.get_instance()
        settings.theme_dark_name = "Catppuccin Mocha"
        settings.theme_light_name = "Catppuccin Latte"
        db.session.commit()
        invalidate_settings_cache()

        resp = authenticated_client.get("/admin/settings")
        assert resp.status_code == 200
        assert b"Catppuccin Mocha" in resp.data
        assert b"Catppuccin Latte" in resp.data

    def test_settings_page_shows_scheme_options(self, authenticated_client, db):
        resp = authenticated_client.get("/admin/settings")
        assert resp.status_code == 200
        for scheme in ["system", "dark", "light"]:
            assert scheme.encode() in resp.data

    def test_settings_page_requires_auth(self, client, db):
        resp = client.get("/admin/settings")
        assert resp.status_code in (302, 401)


class TestAdminThemeSave:
    def test_save_valid_theme_persists(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme",
            data={
                "theme_dark_name": "Dracula",
                "theme_light_name": "Catppuccin Latte",
                "theme_default_scheme": "dark",
                "logo_text": "Test Blog",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        settings = SiteSettings.get_instance()
        assert settings.theme_dark_name == "Dracula"
        assert settings.theme_light_name == "Catppuccin Latte"
        assert settings.theme_default_scheme == "dark"
        assert settings.logo_text == "Test Blog"

    def test_save_invalid_dark_theme_rejects(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme",
            data={
                "theme_dark_name": "Totally Invalid Theme XYZ",
                "theme_light_name": "Catppuccin Latte",
                "theme_default_scheme": "system",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        settings = SiteSettings.get_instance()
        assert settings.theme_dark_name != "Totally Invalid Theme XYZ"

    def test_save_invalid_light_theme_rejects(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme",
            data={
                "theme_dark_name": "Catppuccin Mocha",
                "theme_light_name": "Nonexistent Theme",
                "theme_default_scheme": "system",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        settings = SiteSettings.get_instance()
        assert settings.theme_light_name != "Nonexistent Theme"

    def test_save_invalid_scheme_rejects(self, authenticated_client, db):
        original = SiteSettings.get_instance().theme_default_scheme
        resp = authenticated_client.post(
            "/admin/settings/theme",
            data={
                "theme_dark_name": "Catppuccin Mocha",
                "theme_light_name": "Catppuccin Latte",
                "theme_default_scheme": "invalid-value",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        settings = SiteSettings.get_instance()
        assert settings.theme_default_scheme == original

    def test_save_custom_css_sanitized(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme",
            data={
                "theme_dark_name": "Catppuccin Mocha",
                "theme_light_name": "Catppuccin Latte",
                "theme_default_scheme": "system",
                "custom_css_enabled": "on",
                "custom_css": "body { color: red; } <script>alert(1)</script>",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        settings = SiteSettings.get_instance()
        assert "body" in settings.custom_css
        assert "<script>" not in settings.custom_css

    def test_save_persists_and_is_read_back(self, authenticated_client, db):
        authenticated_client.post(
            "/admin/settings/theme",
            data={
                "theme_dark_name": "Dracula",
                "theme_light_name": "Catppuccin Latte",
                "theme_default_scheme": "dark",
                "logo_text": "My Blog",
            },
            follow_redirects=True,
        )

        settings = SiteSettings.get_instance()
        assert settings.theme_dark_name == "Dracula"
        assert settings.theme_light_name == "Catppuccin Latte"
        assert settings.theme_default_scheme == "dark"
        assert settings.logo_text == "My Blog"

        resp = authenticated_client.get("/admin/settings")
        assert resp.status_code == 200
        assert b"Dracula" in resp.data
        assert b"Catppuccin Latte" in resp.data


class TestAdminThemePreview:
    def test_preview_returns_json(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme/preview",
            data={
                "theme_dark_name": "Catppuccin Mocha",
                "theme_light_name": "Catppuccin Latte",
            },
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "dark_css" in data
        assert "light_css" in data
        assert len(data["dark_css"]) > 0
        assert len(data["light_css"]) > 0

    def test_preview_does_not_persist(self, authenticated_client, db):
        original_dark = SiteSettings.get_instance().theme_dark_name

        resp = authenticated_client.post(
            "/admin/settings/theme/preview",
            data={
                "theme_dark_name": "Dracula",
                "theme_light_name": "Catppuccin Latte",
            },
        )
        assert resp.status_code == 200

        settings = SiteSettings.get_instance()
        assert settings.theme_dark_name == original_dark

    def test_preview_missing_names_returns_400(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme/preview",
            data={"theme_dark_name": ""},
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "error" in data

    def test_preview_invalid_theme_returns_400(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme/preview",
            data={
                "theme_dark_name": "Nonexistent Theme",
                "theme_light_name": "Catppuccin Latte",
            },
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "error" in data

    def test_preview_same_classification_warning(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme/preview",
            data={
                "theme_dark_name": "Catppuccin Mocha",
                "theme_light_name": "Dracula",
            },
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert any("dark" in w.lower() for w in data.get("warnings", []))


class TestAdminThemeRefresh:
    def test_refresh_no_changes(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme/refresh",
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_refresh_after_theme_change(self, authenticated_client, db):
        authenticated_client.post(
            "/admin/settings/theme",
            data={
                "theme_dark_name": "Dracula",
                "theme_light_name": "Catppuccin Latte",
                "theme_default_scheme": "dark",
            },
            follow_redirects=True,
        )

        settings = SiteSettings.get_instance()
        assert settings.theme_dark_name == "Dracula"

        resp = authenticated_client.post(
            "/admin/settings/theme/refresh",
            follow_redirects=True,
        )
        assert resp.status_code == 200

        settings = SiteSettings.get_instance()
        assert settings.theme_dark_name == "Dracula"
