from __future__ import annotations

from unittest.mock import MagicMock

from app.models import SiteSettings
from app.services.theme_settings import (
    LEGACY_PRESET_MAP,
    ThemeSettingsValidation,
    get_effective_theme_names,
    migrate_legacy_preset,
    validate_theme_settings,
)


class TestFreshDatabaseDefaults:
    def test_new_instance_has_default_dark_name(self, db):
        settings = SiteSettings.get_instance()
        assert settings.theme_dark_name == "Catppuccin Mocha"

    def test_new_instance_has_default_light_name(self, db):
        settings = SiteSettings.get_instance()
        assert settings.theme_light_name == "Catppuccin Latte"

    def test_new_instance_has_default_scheme(self, db):
        settings = SiteSettings.get_instance()
        assert settings.theme_default_scheme == "system"

    def test_new_instance_preserves_existing_columns(self, db):
        settings = SiteSettings.get_instance()
        assert settings.theme_preset == "github-dark"
        assert settings.syntax_theme == "prism"
        assert settings.custom_css_enabled is False
        assert settings.custom_css == ""

    def test_get_instance_returns_same_row(self, db):
        first = SiteSettings.get_instance()
        second = SiteSettings.get_instance()
        assert first.id == second.id


class TestLegacyPresetMigration:
    def test_github_dark_maps_to_catppuccin_mocha(self):
        assert migrate_legacy_preset("github-dark") == "Catppuccin Mocha"

    def test_github_light_maps_to_catppuccin_latte(self):
        assert migrate_legacy_preset("github-light") == "Catppuccin Latte"

    def test_solarized_dark_maps_to_solarized_dark(self):
        assert migrate_legacy_preset("solarized-dark") == "Solarized Dark"

    def test_monokai_maps_to_sonokai(self):
        assert migrate_legacy_preset("monokai") == "Sonokai"

    def test_all_legacy_keys_are_mapped(self):
        assert set(LEGACY_PRESET_MAP.keys()) == {
            "github-dark",
            "github-light",
            "solarized-dark",
            "monokai",
        }


class TestUnknownLegacyValue:
    def test_unknown_value_passes_through(self):
        assert migrate_legacy_preset("dracula") == "dracula"

    def test_empty_string_passes_through(self):
        assert migrate_legacy_preset("") == ""

    def test_new_theme_name_passes_through(self):
        assert migrate_legacy_preset("Catppuccin Mocha") == "Catppuccin Mocha"


class TestNamesWithSpaces:
    def test_catppuccin_mocha_accepted(self):
        result = validate_theme_settings("Catppuccin Mocha", "Catppuccin Latte", "system")
        assert result.dark_name == "Catppuccin Mocha"
        assert result.light_name == "Catppuccin Latte"
        assert result.warnings == []

    def test_solarized_dark_accepted(self):
        result = validate_theme_settings("Solarized Dark", "Catppuccin Latte", "dark")
        assert result.dark_name == "Solarized Dark"
        assert result.warnings == []

    def test_rose_pine_accepted(self):
        result = validate_theme_settings("Rose Pine", "Rose Pine Dawn", "system")
        assert result.dark_name == "Rose Pine"
        assert result.light_name == "Rose Pine Dawn"


class TestNamesWithParentheses:
    def test_discord_with_parentheses_accepted(self):
        result = validate_theme_settings("Discord (80_ Saturation)", "Catppuccin Latte", "system")
        assert result.dark_name == "Discord (80_ Saturation)"
        assert result.warnings == []


class TestValidSchemeValidation:
    def test_system_scheme_accepted(self):
        result = validate_theme_settings("Catppuccin Mocha", "Catppuccin Latte", "system")
        assert result.scheme == "system"
        assert result.warnings == []

    def test_dark_scheme_accepted(self):
        result = validate_theme_settings("Catppuccin Mocha", "Catppuccin Latte", "dark")
        assert result.scheme == "dark"
        assert result.warnings == []

    def test_light_scheme_accepted(self):
        result = validate_theme_settings("Catppuccin Mocha", "Catppuccin Latte", "light")
        assert result.scheme == "light"
        assert result.warnings == []


class TestInvalidSchemeValidation:
    def test_invalid_scheme_falls_back_to_system(self):
        result = validate_theme_settings("Catppuccin Mocha", "Catppuccin Latte", "auto")
        assert result.scheme == "system"
        assert len(result.warnings) == 1
        assert "invalid scheme" in result.warnings[0]

    def test_empty_scheme_falls_back_to_system(self):
        result = validate_theme_settings("Catppuccin Mocha", "Catppuccin Latte", "")
        assert result.scheme == "system"
        assert len(result.warnings) == 1

    def test_case_sensitive_scheme_rejection(self):
        result = validate_theme_settings("Catppuccin Mocha", "Catppuccin Latte", "Dark")
        assert result.scheme == "system"
        assert len(result.warnings) == 1


class TestRegistryValidation:
    def test_valid_theme_accepted(self):
        registry = MagicMock()
        registry.resolve.return_value = MagicMock()
        result = validate_theme_settings(
            "Catppuccin Mocha", "Catppuccin Latte", "system", registry=registry
        )
        assert result.dark_name == "Catppuccin Mocha"
        assert result.light_name == "Catppuccin Latte"
        assert result.warnings == []

    def test_registry_resolve_called_for_both_themes(self):
        registry = MagicMock()
        registry.resolve.return_value = MagicMock()
        validate_theme_settings("Dracula", "Rose Pine", "system", registry=registry)
        assert registry.resolve.call_count == 2
        registry.resolve.assert_any_call("Dracula")
        registry.resolve.assert_any_call("Rose Pine")


class TestRegistryValidationMissingTheme:
    def test_missing_dark_theme_falls_back(self):
        registry = MagicMock()
        registry.resolve.side_effect = lambda name: (
            MagicMock() if name == "Catppuccin Latte" else None
        )
        result = validate_theme_settings(
            "Nonexistent Dark", "Catppuccin Latte", "system", registry=registry
        )
        assert result.dark_name == "Catppuccin Mocha"
        assert result.light_name == "Catppuccin Latte"
        assert any("dark theme" in w for w in result.warnings)

    def test_missing_light_theme_falls_back(self):
        registry = MagicMock()
        registry.resolve.side_effect = lambda name: (
            MagicMock() if name == "Catppuccin Mocha" else None
        )
        result = validate_theme_settings(
            "Catppuccin Mocha", "Nonexistent Light", "system", registry=registry
        )
        assert result.dark_name == "Catppuccin Mocha"
        assert result.light_name == "Catppuccin Latte"
        assert any("light theme" in w for w in result.warnings)

    def test_both_missing_themes_fall_back(self):
        registry = MagicMock()
        registry.resolve.return_value = None
        result = validate_theme_settings("Bad Dark", "Bad Light", "system", registry=registry)
        assert result.dark_name == "Catppuccin Mocha"
        assert result.light_name == "Catppuccin Latte"
        assert len(result.warnings) == 2

    def test_registry_exception_falls_back(self):
        registry = MagicMock()
        registry.resolve.side_effect = RuntimeError("disk error")
        result = validate_theme_settings(
            "Catppuccin Mocha", "Catppuccin Latte", "system", registry=registry
        )
        assert result.dark_name == "Catppuccin Mocha"
        assert result.light_name == "Catppuccin Latte"
        assert len(result.warnings) == 2
        assert all("failed to validate" in w for w in result.warnings)

    def test_empty_names_use_defaults_with_registry(self):
        registry = MagicMock()
        registry.resolve.return_value = MagicMock()
        result = validate_theme_settings("", "", "system", registry=registry)
        assert result.dark_name == "Catppuccin Mocha"
        assert result.light_name == "Catppuccin Latte"
        assert result.warnings == []


class TestGetEffectiveThemeNames:
    def test_persisted_settings_take_precedence(self, db):
        settings = SiteSettings.get_instance()
        settings.theme_dark_name = "Dracula"
        settings.theme_light_name = "Rose Pine"
        settings.theme_default_scheme = "dark"
        db.session.commit()

        result = get_effective_theme_names(
            settings,
            {
                "THEME_DARK_NAME": "Tokyo Night Storm",
                "THEME_LIGHT_NAME": "Ferra Light",
                "THEME_DEFAULT_SCHEME": "light",
            },
        )
        assert result == ("Dracula", "Rose Pine", "dark")

    def test_config_defaults_used_when_settings_empty(self, db):
        settings = SiteSettings.get_instance()
        settings.theme_dark_name = ""
        settings.theme_light_name = ""
        settings.theme_default_scheme = ""
        db.session.commit()

        result = get_effective_theme_names(
            settings,
            {
                "THEME_DARK_NAME": "Tokyo Night Storm",
                "THEME_LIGHT_NAME": "Ferra Light",
                "THEME_DEFAULT_SCHEME": "light",
            },
        )
        assert result == ("Tokyo Night Storm", "Ferra Light", "light")

    def test_hardcoded_defaults_used_when_all_empty(self, db):
        settings = SiteSettings.get_instance()
        settings.theme_dark_name = ""
        settings.theme_light_name = ""
        settings.theme_default_scheme = ""
        db.session.commit()

        result = get_effective_theme_names(settings, {})
        assert result == ("Catppuccin Mocha", "Catppuccin Latte", "system")


class TestGetEffectiveThemeNamesEmpty:
    def test_empty_persisted_uses_config(self, db):
        settings = SiteSettings.get_instance()
        settings.theme_dark_name = ""
        settings.theme_light_name = ""
        settings.theme_default_scheme = ""
        db.session.commit()

        result = get_effective_theme_names(
            settings,
            {
                "THEME_DARK_NAME": "One Dark",
                "THEME_LIGHT_NAME": "IntelliJ Light",
                "THEME_DEFAULT_SCHEME": "dark",
            },
        )
        assert result[0] == "One Dark"
        assert result[1] == "IntelliJ Light"
        assert result[2] == "dark"

    def test_partial_config_defaults(self, db):
        settings = SiteSettings.get_instance()
        settings.theme_dark_name = ""
        settings.theme_light_name = ""
        settings.theme_default_scheme = ""
        db.session.commit()

        result = get_effective_theme_names(
            settings,
            {"THEME_DARK_NAME": "Dracula"},
        )
        assert result[0] == "Dracula"
        assert result[1] == "Catppuccin Latte"
        assert result[2] == "system"

    def test_none_values_treated_as_empty(self, db):
        settings = SiteSettings.get_instance()
        settings.theme_dark_name = ""
        settings.theme_light_name = ""
        settings.theme_default_scheme = ""
        db.session.commit()

        result = get_effective_theme_names(settings, {})
        assert result == ("Catppuccin Mocha", "Catppuccin Latte", "system")


class TestCustomCssAndSyntaxPreservation:
    def test_custom_css_unaffected_by_theme_settings(self, db):
        settings = SiteSettings.get_instance()
        settings.custom_css = "body { color: red; }"
        settings.custom_css_enabled = True
        settings.syntax_theme = "dracula"
        settings.theme_dark_name = "Solarized Dark"
        db.session.commit()

        reloaded = SiteSettings.get_instance()
        assert reloaded.custom_css == "body { color: red; }"
        assert reloaded.custom_css_enabled is True
        assert reloaded.syntax_theme == "dracula"
        assert reloaded.theme_dark_name == "Solarized Dark"

    def test_theme_preset_independent_of_theme_names(self, db):
        settings = SiteSettings.get_instance()
        settings.theme_preset = "github-dark"
        settings.theme_dark_name = "Dracula"
        settings.theme_light_name = "Rose Pine Dawn"
        db.session.commit()

        reloaded = SiteSettings.get_instance()
        assert reloaded.theme_preset == "github-dark"
        assert reloaded.theme_dark_name == "Dracula"
        assert reloaded.theme_light_name == "Rose Pine Dawn"


class TestThemeSettingsValidationDataclass:
    def test_has_required_fields(self):
        v = ThemeSettingsValidation(
            dark_name="Catppuccin Mocha",
            light_name="Catppuccin Latte",
            scheme="system",
        )
        assert v.dark_name == "Catppuccin Mocha"
        assert v.light_name == "Catppuccin Latte"
        assert v.scheme == "system"

    def test_warnings_default_to_empty_list(self):
        v = ThemeSettingsValidation(
            dark_name="Catppuccin Mocha",
            light_name="Catppuccin Latte",
            scheme="system",
        )
        assert v.warnings == []

    def test_warnings_can_be_provided(self):
        v = ThemeSettingsValidation(
            dark_name="Catppuccin Mocha",
            light_name="Catppuccin Latte",
            scheme="system",
            warnings=["bad theme"],
        )
        assert v.warnings == ["bad theme"]

    def test_equality(self):
        a = ThemeSettingsValidation("Dark", "Light", "system")
        b = ThemeSettingsValidation("Dark", "Light", "system")
        assert a == b

    def test_inequality_on_warnings(self):
        a = ThemeSettingsValidation("Dark", "Light", "system", warnings=["w1"])
        b = ThemeSettingsValidation("Dark", "Light", "system", warnings=["w2"])
        assert a != b
