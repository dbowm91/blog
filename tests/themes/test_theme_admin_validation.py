"""Admin theme validation tests — Workstream B.

Ensures invalid/malicious theme names never produce admin 500 responses.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

from app.themes.registry import ThemeParseFailure, ThemeLoadError


class TestAdminSettingsValidation:
    def test_invalid_dark_theme_name_flash(self, authenticated_client, db):
        resp = authenticated_client.post(
            "/admin/settings/theme",
            data={
                "theme_dark_name": "../../../etc/passwd",
                "theme_light_name": "Catppuccin Latte",
                "theme_default_scheme": "system",
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


class TestAdminMalformedExternalOverride:
    def test_save_with_malformed_external_override(self, authenticated_client, db):
        from app.models import SiteSettings

        settings_obj = SiteSettings.get_instance()
        settings_obj.theme_dark_name = "Malformed External"
        settings_obj.theme_light_name = "Catppuccin Latte"
        db.session.commit()

        with patch("app.routes.admin.settings.get_theme_service") as mock_get_svc:
            mock_service = MagicMock()
            mock_registry = MagicMock()
            mock_registry.resolve.side_effect = ThemeParseFailure(
                "Malformed External", "invalid TOML syntax"
            )
            mock_service.get_registry.return_value = mock_registry
            mock_get_svc.return_value = mock_service

            resp = authenticated_client.post(
                "/admin/settings/theme",
                data={
                    "theme_dark_name": "Malformed External",
                    "theme_light_name": "Catppuccin Latte",
                    "theme_default_scheme": "system",
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200
            html = resp.data.decode()
            assert "error" in html.lower() or "invalid" in html.lower()

    def test_preview_with_malformed_external_override(self, authenticated_client, db):
        with patch("app.routes.admin.settings.get_theme_service") as mock_get_svc:
            mock_service = MagicMock()
            mock_registry = MagicMock()
            mock_registry.resolve.side_effect = ThemeParseFailure(
                "Malformed External", "invalid TOML syntax"
            )
            mock_service.get_registry.return_value = mock_registry
            mock_get_svc.return_value = mock_service

            resp = authenticated_client.post(
                "/admin/settings/theme/preview",
                data={
                    "theme_dark_name": "Malformed External",
                    "theme_light_name": "Catppuccin Latte",
                },
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert "error" in data

    def test_save_with_unloadable_external_override(self, authenticated_client, db):
        with patch("app.routes.admin.settings.get_theme_service") as mock_get_svc:
            mock_service = MagicMock()
            mock_registry = MagicMock()
            mock_registry.resolve.return_value = MagicMock(canonical_name="Unloading Theme")
            mock_registry.load.side_effect = ThemeLoadError("Unloading Theme", "permission denied")
            mock_service.get_registry.return_value = mock_registry
            mock_get_svc.return_value = mock_service

            resp = authenticated_client.post(
                "/admin/settings/theme",
                data={
                    "theme_dark_name": "Unloading Theme",
                    "theme_light_name": "Catppuccin Latte",
                    "theme_default_scheme": "system",
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200
            html = resp.data.decode()
            assert "error" in html.lower() or "failed" in html.lower()

    def test_refresh_with_malformed_external_override(self, authenticated_client, db):
        with patch("app.routes.admin.settings.get_theme_service") as mock_get_svc:
            mock_service = MagicMock()
            mock_service.refresh_registry.side_effect = ThemeParseFailure(
                "Broken Theme", "unexpected token"
            )
            mock_get_svc.return_value = mock_service

            resp = authenticated_client.post(
                "/admin/settings/theme/refresh",
                follow_redirects=True,
            )
            assert resp.status_code == 200
            html = resp.data.decode()
            assert "error" in html.lower() or "failed" in html.lower()
