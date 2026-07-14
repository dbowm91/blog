"""Tests for preserve_legacy_scheme migration.

Verifies upgrade and downgrade behavior on the site_settings table
by executing the same SQL that the migration runs.
"""

from __future__ import annotations

from sqlalchemy import text

from app.extensions import db
from app.models import SiteSettings


_UPGRADE_DARK = text(
    "UPDATE site_settings SET theme_default_scheme = 'dark' "
    "WHERE theme_preset IN ('github-dark', 'solarized-dark', 'monokai') "
    "AND theme_default_scheme = 'system'"
)
_UPGRADE_LIGHT = text(
    "UPDATE site_settings SET theme_default_scheme = 'light' "
    "WHERE theme_preset = 'github-light' "
    "AND theme_default_scheme = 'system'"
)
_DOWNGRADE = text("UPDATE site_settings SET theme_default_scheme = 'system'")


def _run_upgrade():
    db.session.execute(_UPGRADE_DARK)
    db.session.execute(_UPGRADE_LIGHT)
    db.session.commit()


def _run_downgrade():
    db.session.execute(_DOWNGRADE)
    db.session.commit()


def _set_preset_and_scheme(preset: str, scheme: str = "system") -> None:
    settings = SiteSettings.get_instance()
    settings.theme_preset = preset
    settings.theme_default_scheme = scheme
    db.session.commit()


class TestPreserveLegacySchemeUpgrade:
    def test_github_dark_sets_dark(self, db):
        _set_preset_and_scheme("github-dark")
        _run_upgrade()

        settings = SiteSettings.query.filter_by(id=1).one()
        assert settings.theme_default_scheme == "dark"

    def test_solarized_dark_sets_dark(self, db):
        _set_preset_and_scheme("solarized-dark")
        _run_upgrade()

        settings = SiteSettings.query.filter_by(id=1).one()
        assert settings.theme_default_scheme == "dark"

    def test_monokai_sets_dark(self, db):
        _set_preset_and_scheme("monokai")
        _run_upgrade()

        settings = SiteSettings.query.filter_by(id=1).one()
        assert settings.theme_default_scheme == "dark"

    def test_github_light_sets_light(self, db):
        _set_preset_and_scheme("github-light")
        _run_upgrade()

        settings = SiteSettings.query.filter_by(id=1).one()
        assert settings.theme_default_scheme == "light"

    def test_unknown_preset_stays_system(self, db):
        _set_preset_and_scheme("unknown-preset")
        _run_upgrade()

        settings = SiteSettings.query.filter_by(id=1).one()
        assert settings.theme_default_scheme == "system"

    def test_already_non_system_not_changed(self, db):
        _set_preset_and_scheme("github-dark", scheme="light")
        _run_upgrade()

        settings = SiteSettings.query.filter_by(id=1).one()
        assert settings.theme_default_scheme == "light"

    def test_multiple_presets_in_mixed_state(self, db):
        db.session.execute(text("DELETE FROM site_settings"))

        for preset in ["github-dark", "solarized-dark", "monokai", "github-light", "unknown"]:
            settings = SiteSettings()
            settings.theme_preset = preset
            settings.theme_default_scheme = "system"
            db.session.add(settings)
        db.session.commit()

        _run_upgrade()

        rows = db.session.execute(
            text("SELECT theme_preset, theme_default_scheme FROM site_settings ORDER BY id")
        ).fetchall()
        results = {row[0]: row[1] for row in rows}
        assert results["github-dark"] == "dark"
        assert results["solarized-dark"] == "dark"
        assert results["monokai"] == "dark"
        assert results["github-light"] == "light"
        assert results["unknown"] == "system"


class TestPreserveLegacySchemeDowngrade:
    def test_downgrade_resets_all_to_system(self, db):
        _set_preset_and_scheme("github-dark")
        _run_upgrade()

        settings = SiteSettings.query.filter_by(id=1).one()
        assert settings.theme_default_scheme == "dark"

        _run_downgrade()

        settings = SiteSettings.query.filter_by(id=1).one()
        assert settings.theme_default_scheme == "system"

    def test_downgrade_resets_light_to_system(self, db):
        _set_preset_and_scheme("github-light")
        _run_upgrade()

        _run_downgrade()

        settings = SiteSettings.query.filter_by(id=1).one()
        assert settings.theme_default_scheme == "system"

    def test_upgrade_downgrade_roundtrip(self, db):
        for preset in ["github-dark", "solarized-dark", "monokai", "github-light"]:
            _set_preset_and_scheme(preset)
            _run_upgrade()

            settings = SiteSettings.query.filter_by(id=1).one()
            assert settings.theme_default_scheme in ("dark", "light")

            _run_downgrade()
            settings = SiteSettings.query.filter_by(id=1).one()
            assert settings.theme_default_scheme == "system"
