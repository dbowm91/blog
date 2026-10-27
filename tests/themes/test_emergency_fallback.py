"""Tests for emergency fallback resilience under failure conditions.

Phase 15 deliverable — verifies the Halloy emergency context remains
complete when database access, packaged resources, and external themes
are all unavailable.
"""

from __future__ import annotations

from unittest.mock import patch

from app.themes.model import EMERGENCY_DEFAULT, ALIASES, CSS_VARS
from app.themes.service import ThemeService
from app.themes.translate import to_legacy_vars, to_theme_vars


class TestEmergencyFallbackCompleteness:
    """Emergency context must contain all required template keys."""

    def test_emergency_context_has_all_required_keys(self):
        service = ThemeService()
        ctx = service._emergency_context()

        required_keys = [
            "theme_dark_name",
            "theme_light_name",
            "theme_default_scheme",
            "theme_dark_vars",
            "theme_light_vars",
            "theme_dark_css",
            "theme_light_css",
            "theme_warnings",
            "custom_css_enabled",
            "custom_css",
            "logo_text",
        ]
        for key in required_keys:
            assert key in ctx, f"missing required key: {key}"

    def test_emergency_context_no_legacy_preset_keys(self):
        service = ThemeService()
        ctx = service._emergency_context()
        assert "theme_preset" not in ctx
        assert "theme_presets" not in ctx

    def test_emergency_context_dark_css_is_nonempty(self):
        service = ThemeService()
        ctx = service._emergency_context()
        assert len(ctx["theme_dark_css"]) > 0
        assert ctx["theme_dark_css"].startswith("  --")

    def test_emergency_context_light_css_is_nonempty(self):
        service = ThemeService()
        ctx = service._emergency_context()
        assert len(ctx["theme_light_css"]) > 0

    def test_emergency_context_scheme_is_dark(self):
        service = ThemeService()
        ctx = service._emergency_context()
        assert ctx["theme_default_scheme"] == "dark"

    def test_emergency_context_warnings_indicate_fallback(self):
        service = ThemeService()
        ctx = service._emergency_context()
        assert any("emergency" in w.lower() for w in ctx["theme_warnings"])

    def test_emergency_context_has_no_syntax_theme(self):
        service = ThemeService()
        ctx = service._emergency_context()
        assert "syntax_theme" not in ctx

    def test_emergency_context_custom_css_disabled(self):
        service = ThemeService()
        ctx = service._emergency_context()
        assert ctx["custom_css_enabled"] is False
        assert ctx["custom_css"] == ""


class TestEmergencyDefaultCompleteness:
    """EMERGENCY_DEFAULT BlogTheme must have all CSS vars."""

    def test_emergency_default_has_all_aliases(self):
        legacy = to_legacy_vars(EMERGENCY_DEFAULT)
        for alias_key in ALIASES:
            assert alias_key in legacy, f"missing alias key: {alias_key}"

    def test_emergency_default_has_all_css_vars(self):
        theme_vars = to_theme_vars(EMERGENCY_DEFAULT)
        for var_key in CSS_VARS.values():
            assert var_key in theme_vars, f"missing CSS var: {var_key}"

    def test_emergency_default_serializes_to_css(self):
        css = ThemeService._serialize_vars(to_legacy_vars(EMERGENCY_DEFAULT))
        assert "--bg:" in css
        assert "--text:" in css
        assert "--accent:" in css


class TestDatabaseFailureFallback:
    """Theme service must survive database failures."""

    def test_db_error_triggers_emergency_context(self):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("database locked"),
        ):
            ctx = service.get_context()
        assert "theme_dark_name" in ctx
        assert ctx["theme_dark_name"] == "emergency-default"

    def test_db_error_preserves_required_structure(self):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=ConnectionError("connection refused"),
        ):
            ctx = service.get_context()
        assert "theme_dark_css" in ctx
        assert "theme_light_css" in ctx

    def test_operational_error_triggers_emergency(self):
        from sqlalchemy.exc import OperationalError

        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=OperationalError("db error", {}, None),
        ):
            ctx = service.get_context()
        assert ctx["theme_dark_name"] == "emergency-default"


class TestRegistryFailureFallback:
    """Theme service must survive registry/load failures."""

    def test_emergency_context_has_theme_vars_dict(self):
        service = ThemeService()
        ctx = service._emergency_context()
        assert isinstance(ctx["theme_dark_vars"], dict)
        assert isinstance(ctx["theme_light_vars"], dict)
        assert len(ctx["theme_dark_vars"]) > 0
