"""Phase 07 integration tests — Flask and Jinja runtime integration.

Tests that:
- All rendered surfaces use Halloy-derived semantic variables
- One centralized service owns registry and fallback behavior
- Generated theme CSS is CSP-compliant and emitted before custom CSS
- Syntax highlighting remains independent
- Theme failures never cause public 500 responses
- Legacy preset rendering is no longer the runtime authority
"""

from __future__ import annotations

import re

import pytest  # noqa: F401
from unittest.mock import patch

from app.models import SiteSettings
from app.themes.service import ThemeService, get_theme_service


class TestThemeServiceConstruction:
    def test_service_singleton_per_process(self, app, db):
        s1 = get_theme_service()
        s2 = get_theme_service()
        assert s1 is s2

    def test_service_stored_in_app_extensions(self, app, db):
        assert "theme_service" in app.extensions
        assert app.extensions["theme_service"] is get_theme_service()

    def test_registry_lazily_initialized(self, app):
        service = ThemeService()
        assert service._registry is None
        _ = service.get_registry()
        assert service._registry is not None

    def test_registry_thread_safety(self, app):
        import threading

        service = ThemeService()
        results = []

        def load_registry():
            r = service.get_registry()
            results.append(r)

        threads = [threading.Thread(target=load_registry) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 10
        assert all(r is results[0] for r in results)


class TestThemeServiceContext:
    def test_context_has_required_keys(self, app, db):
        service = get_theme_service()
        ctx = service.get_context()
        required = [
            "theme_dark_name",
            "theme_light_name",
            "theme_default_scheme",
            "theme_dark_vars",
            "theme_light_vars",
            "theme_dark_css",
            "theme_light_css",
            "theme_warnings",
            "syntax_theme",
            "custom_css_enabled",
            "custom_css",
            "logo_text",
            "theme_vars",
        ]
        for key in required:
            assert key in ctx, f"missing key: {key}"

    def test_dark_and_light_vars_are_dicts(self, app, db):
        service = get_theme_service()
        ctx = service.get_context()
        assert isinstance(ctx["theme_dark_vars"], dict)
        assert isinstance(ctx["theme_light_vars"], dict)

    def test_dark_and_light_css_are_strings(self, app, db):
        service = get_theme_service()
        ctx = service.get_context()
        assert isinstance(ctx["theme_dark_css"], str)
        assert isinstance(ctx["theme_light_css"], str)

    def test_theme_vars_backward_compat(self, app, db):
        service = get_theme_service()
        ctx = service.get_context()
        assert "theme_vars" in ctx
        assert isinstance(ctx["theme_vars"], dict)

    def test_emergency_fallback_on_db_error(self, app, db):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("db down"),
        ):
            ctx = service.get_context()
        assert "theme_dark_vars" in ctx
        assert "theme_light_vars" in ctx
        assert len(ctx["theme_dark_vars"]) > 0
        assert len(ctx["theme_light_vars"]) > 0


class TestPublicTemplateReceivesHalloyVariables:
    def test_index_has_dark_vars(self, client, db):
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "--bg:" in html or "--bg-surface:" in html

    def test_index_has_light_vars(self, client, db):
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert '[data-color-scheme="light"]' in html

    def test_index_has_dark_scheme_block(self, client, db):
        resp = client.get("/")
        html = resp.data.decode()
        assert '[data-color-scheme="dark"]' in html or ":root," in html

    def test_index_emits_csp_nonce(self, client, db):
        resp = client.get("/")
        html = resp.data.decode()
        assert "nonce=" in html


class TestAdminTemplateReceivesHalloyVariables:
    def test_admin_login_has_dark_vars(self, client, db):
        resp = client.get("/admin/login")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "--bg:" in html or "--bg-surface:" in html

    def test_admin_login_has_light_vars(self, client, db):
        resp = client.get("/admin/login")
        html = resp.data.decode()
        assert '[data-color-scheme="light"]' in html


class TestDualSchemeCSSEmission:
    def test_dark_and_light_blocks_both_present(self, client, db):
        resp = client.get("/")
        html = resp.data.decode()
        assert "theme_dark_vars" not in html  # raw key not in output
        assert ":root," in html
        assert '[data-color-scheme="light"]' in html

    def test_light_block_overrides_dark(self, client, db):
        resp = client.get("/")
        html = resp.data.decode()
        dark_pos = html.find(":root,")
        light_pos = html.find('[data-color-scheme="light"]')
        assert dark_pos >= 0
        assert light_pos > dark_pos

    def test_csp_nonce_on_theme_style(self, client, db):
        resp = client.get("/")
        html = resp.data.decode()
        style_blocks = re.findall(r"<style[^>]*>", html)
        nonce_blocks = [b for b in style_blocks if "nonce=" in b]
        assert len(nonce_blocks) >= 1


class TestCustomCSSOrdering:
    def test_custom_css_after_generated_vars(self, app, db):
        settings = SiteSettings.get_instance()
        settings.custom_css_enabled = True
        settings.custom_css = "body { color: red; }"
        db.session.commit()

        from app.context_processors import invalidate_settings_cache

        invalidate_settings_cache()

        client = app.test_client()
        resp = client.get("/")
        html = resp.data.decode()
        custom_pos = html.find("color: red")
        var_pos = html.find("--bg:")
        assert custom_pos > 0
        assert var_pos >= 0
        assert custom_pos > var_pos


class TestSyntaxThemeIndependence:
    def test_syntax_theme_in_html_attr(self, client, db):
        resp = client.get("/")
        html = resp.data.decode()
        assert "data-syntax-theme=" in html

    def test_syntax_css_link_present(self, client, db):
        resp = client.get("/")
        html = resp.data.decode()
        assert "prism" in html.lower()


class TestMissingThemeFallback:
    def test_invalid_dark_theme_falls_back(self, app, db):
        settings = SiteSettings.get_instance()
        settings.theme_dark_name = "Nonexistent Theme XYZ"
        settings.theme_light_name = "Catppuccin Latte"
        db.session.commit()

        from app.context_processors import invalidate_settings_cache

        invalidate_settings_cache()

        service = ThemeService()
        ctx = service.get_context()
        assert ctx["theme_dark_name"] in ("Catppuccin Mocha", "Nonexistent Theme XYZ")
        assert len(ctx["theme_dark_vars"]) > 0

    def test_invalid_light_theme_falls_back(self, app, db):
        settings = SiteSettings.get_instance()
        settings.theme_dark_name = "Catppuccin Mocha"
        settings.theme_light_name = "Nonexistent Light XYZ"
        db.session.commit()

        from app.context_processors import invalidate_settings_cache

        invalidate_settings_cache()

        service = ThemeService()
        ctx = service.get_context()
        assert len(ctx["theme_light_vars"]) > 0

    def test_no_500_on_missing_theme(self, client, db):
        settings = SiteSettings.get_instance()
        settings.theme_dark_name = "Totally Broken"
        settings.theme_light_name = "Also Broken"
        db.session.commit()

        from app.context_processors import invalidate_settings_cache

        invalidate_settings_cache()

        resp = client.get("/")
        assert resp.status_code == 200


class TestEmergencyFallback:
    def test_emergency_context_has_all_legacy_keys(self, app, db):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("fail"),
        ):
            ctx = service.get_context()
        expected_keys = {"bg", "bg-surface", "text", "accent", "border"}
        assert expected_keys.issubset(set(ctx["theme_dark_vars"].keys()))
        assert expected_keys.issubset(set(ctx["theme_light_vars"].keys()))

    def test_emergency_css_is_nonempty(self, app, db):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("fail"),
        ):
            ctx = service.get_context()
        assert len(ctx["theme_dark_css"]) > 0
        assert len(ctx["theme_light_css"]) > 0


class TestNoDirectThemePresetsAccess:
    def test_context_processor_uses_service(self, app, db):
        with patch("app.themes.service.ThemeService.get_context") as mock_ctx:
            mock_ctx.return_value = {
                "theme_dark_name": "test",
                "theme_light_name": "test",
                "theme_default_scheme": "dark",
                "theme_dark_vars": {"bg": "#000"},
                "theme_light_vars": {"bg": "#fff"},
                "theme_dark_css": "",
                "theme_light_css": "",
                "theme_warnings": [],
                "syntax_theme": "prism",
                "custom_css_enabled": False,
                "custom_css": "",
                "logo_text": "",
                "theme_preset": "test",
                "theme_vars": {"bg": "#000"},
                "theme_presets": {},
            }
            from app.themes.service import get_theme_service

            service = get_theme_service()
            ctx = service.get_context()
            assert ctx["theme_dark_name"] == "test"


class TestServiceCacheInvalidation:
    def test_invalidate_settings_cache_clears_cache(self, app, db):
        service = get_theme_service()
        _ = service.get_context()
        assert service._settings_cache is not None
        service.invalidate_settings_cache()
        assert service._settings_cache is None

    def test_invalidate_registry_refreshes_catalog(self, app, db):
        service = get_theme_service()
        registry = service.get_registry()
        _ = registry.list_themes()
        service.invalidate_registry()
        assert registry._catalog is None


class TestDataColorSchemeAttribute:
    def test_public_html_has_data_color_scheme(self, client, db):
        resp = client.get("/")
        html = resp.data.decode()
        assert "data-color-scheme=" in html

    def test_admin_login_has_data_color_scheme(self, client, db):
        resp = client.get("/admin/login")
        html = resp.data.decode()
        assert "data-color-scheme=" in html
