"""The `flask` compatibility commands.

`app/cli.py` wraps the service layer in Click commands so that an operator
can reach every maintenance task from `flask --app run:app <command>`. The
theme commands report on the registry, and the scheduler command runs the
APScheduler jobs in the foreground.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from app import create_app


@pytest.fixture
def cli_app(db):
    """Create an app with the CLI commands registered."""
    return create_app()


@pytest.fixture
def runner(cli_app):
    return CliRunner()


class TestThemeValidation:
    def test_a_bundled_theme_file_is_valid(self, runner, cli_app, tmp_path):
        from app.themes.registry import discover_bundled_package

        bundled = next(iter(discover_bundled_package()))
        path = tmp_path / "theme.toml"
        path.write_bytes(bundled.read_bytes())

        result = runner.invoke(cli_app.cli, ["themes", "validate", str(path)])

        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_a_valid_theme_file_is_reported_as_json(self, runner, cli_app, tmp_path):
        from app.themes.registry import discover_bundled_package

        bundled = next(iter(discover_bundled_package()))
        path = tmp_path / "theme.toml"
        path.write_bytes(bundled.read_bytes())

        result = runner.invoke(cli_app.cli, ["themes", "validate", str(path), "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["valid"] is True
        assert payload["name"]

    def test_an_invalid_theme_file_is_rejected(self, runner, cli_app, tmp_path):
        path = tmp_path / "broken.toml"
        path.write_text("this is not a theme", encoding="utf-8")

        result = runner.invoke(cli_app.cli, ["themes", "validate", str(path)])

        assert result.exit_code == 1

    def test_an_invalid_theme_file_is_reported_as_json(self, runner, cli_app, tmp_path):
        path = tmp_path / "broken.toml"
        path.write_text("this is not a theme", encoding="utf-8")

        result = runner.invoke(cli_app.cli, ["themes", "validate", str(path), "--json"])

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["valid"] is False
        assert payload["error"]


class TestThemeInspection:
    def test_a_bundled_theme_can_be_inspected(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "inspect", "Catppuccin Mocha"])

        assert result.exit_code == 0
        assert "Catppuccin Mocha" in result.output

    def test_a_bundled_theme_can_be_inspected_as_json(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "inspect", "Catppuccin Mocha", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["canonical_name"] == "Catppuccin Mocha"
        assert payload["is_dark"] is True

    def test_a_bundled_theme_can_be_inspected_as_css(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "inspect", "Catppuccin Mocha", "--css"])

        assert result.exit_code == 0
        assert "--" in result.output

    def test_an_unknown_theme_is_rejected(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "inspect", "No Such Theme"])

        assert result.exit_code == 1


class TestThemeRegistryCommands:
    def test_the_registry_can_be_refreshed(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "refresh"])

        assert result.exit_code == 0
        assert "Catppuccin Mocha" in result.output

    def test_the_registry_paths_are_printed(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "paths"])

        assert result.exit_code == 0
        assert "themes" in result.output.lower()

    def test_the_list_command_names_the_bundled_themes(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "list"])

        assert result.exit_code == 0
        assert "Catppuccin Mocha" in result.output

    def test_the_list_command_can_report_json(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "list", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert any(item["canonical_name"] == "Catppuccin Mocha" for item in payload)

    def test_the_accessibility_report_covers_the_bundled_themes(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "accessibility"])

        assert result.exit_code in (0, 1)
        assert "Catppuccin Mocha" in result.output

    def test_the_accessibility_report_can_report_json(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "accessibility", "--json"])

        assert result.exit_code in (0, 1)
        payload = json.loads(result.output)
        assert payload["code"] == "themes.accessibility.ok"
        assert payload["details"]["source_filter"] == "all"


class TestSchedulerStart:
    def test_the_scheduler_command_starts_and_stops(self, runner, cli_app, monkeypatch, caplog):
        import threading

        from app import scheduler as scheduler_module

        class _Scheduler:
            def shutdown(self, wait: bool = True) -> None:
                pass

        started = threading.Event()

        def _fake_init_scheduler(app):
            started.set()
            return _Scheduler()

        monkeypatch.setattr(scheduler_module, "init_scheduler", _fake_init_scheduler)
        monkeypatch.setattr(
            "app.scheduler.shutdown_scheduler",
            lambda wait=True: None,
        )

        def _deliver_signal(sig, handler):
            handler(sig, None)

        monkeypatch.setattr("signal.signal", _deliver_signal)

        with caplog.at_level("INFO"):
            result = runner.invoke(cli_app.cli, ["scheduler-start"])

        assert result.exit_code == 0
        assert started.is_set()
        assert "Scheduler started" in caplog.text
        assert "Scheduler stopped" in caplog.text

    def test_the_scheduler_command_reports_a_scheduler_that_cannot_start(
        self, runner, cli_app, monkeypatch
    ):
        monkeypatch.setattr("app.scheduler.init_scheduler", lambda app: None)

        result = runner.invoke(cli_app.cli, ["scheduler-start"])

        assert result.exit_code == 1
        assert "could not be started" in result.output


class TestMaintenanceCommands:
    def test_the_search_index_can_be_rebuilt(self, runner, cli_app, sample_post):
        result = runner.invoke(cli_app.cli, ["rebuild-search"])

        assert result.exit_code == 0
        assert "index" in result.output.lower()

    def test_orphaned_images_are_cleaned_up(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["cleanup-orphaned-images"])

        assert result.exit_code == 0
        assert "orphaned image file(s)" in result.output

    def test_a_cleanup_that_clears_missing_references_reports_them(
        self, runner, cli_app, monkeypatch
    ):
        from app.services.operations.media import MediaCleanupResult

        monkeypatch.setattr(
            "app.services.operations.media.apply_orphaned_media_cleanup",
            lambda: MediaCleanupResult(
                ok=True,
                code="media.cleanup.ok",
                summary="cleaned",
                orphaned_deleted=2,
                missing_cleared=3,
            ),
        )

        result = runner.invoke(cli_app.cli, ["cleanup-orphaned-images"])

        assert result.exit_code == 0
        assert "Cleaned up 2 orphaned image file(s)." in result.output
        assert "Cleared 3 missing image reference(s) from posts." in result.output

    def test_the_database_integrity_check_passes(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["check-integrity"])

        assert result.exit_code == 0
        assert "integrity" in result.output.lower()

    def test_a_failed_integrity_check_is_reported_with_remediation(
        self, runner, cli_app, monkeypatch
    ):
        from app.services.operations.database import DatabaseCheckResult

        monkeypatch.setattr(
            "app.services.operations.database.check_database_integrity",
            lambda: DatabaseCheckResult(
                ok=False,
                code="db.integrity.failed",
                summary="Database integrity check failed: disk image is malformed",
                backend="sqlite",
                healthy=False,
                details={"result": "disk image is malformed"},
                remediation=["Consider restoring from a backup."],
            ),
        )

        result = runner.invoke(cli_app.cli, ["check-integrity"])

        assert result.exit_code == 0
        assert "Database integrity check failed: disk image is malformed" in result.output
        assert "Consider restoring from a backup." in result.output


class TestAdminCommands:
    def test_an_admin_user_is_created(self, runner, cli_app, db):
        from app.models import User

        result = runner.invoke(
            cli_app.cli,
            ["create-admin"],
            input="operator\nPassword123!\nPassword123!\n",
        )

        assert result.exit_code == 0
        assert "operator" in result.output
        user = db.session.execute(db.select(User).filter_by(username="operator")).scalar_one()
        assert user.is_admin is True

    def test_a_weak_password_is_refused(self, runner, cli_app, db):
        from app.models import User

        result = runner.invoke(
            cli_app.cli,
            ["create-admin"],
            input="operator\nweak\nweak\n",
        )

        assert result.exit_code == 0
        assert "password" in result.output.lower()
        assert (
            db.session.execute(db.select(User).filter_by(username="operator")).scalar_one_or_none()
            is None
        )

    def test_an_existing_user_is_promoted(self, runner, cli_app, db):
        from app.models import User

        existing = User(username="writer", is_admin=False)
        existing.set_password("Password123!")
        db.session.add(existing)
        db.session.commit()

        result = runner.invoke(cli_app.cli, ["promote-admin", "writer"])

        assert result.exit_code == 0
        assert "writer" in result.output
        db.session.refresh(existing)
        assert existing.is_admin is True

    def test_promoting_a_missing_user_is_reported(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["promote-admin", "nobody"])

        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    def test_promoting_an_existing_admin_is_reported(self, runner, cli_app, db):
        from app.models import User

        existing = User(username="root", is_admin=True)
        existing.set_password("Password123!")
        db.session.add(existing)
        db.session.commit()

        result = runner.invoke(cli_app.cli, ["promote-admin", "root"])

        assert result.exit_code == 0
        assert "already an admin" in result.output.lower()


class TestTransferCommands:
    def test_the_site_data_is_exported(self, runner, cli_app, tmp_path, sample_post):
        destination = tmp_path / "export.json"

        result = runner.invoke(cli_app.cli, ["export-data", str(destination)])

        assert result.exit_code == 0
        assert "Exported" in result.output
        payload = json.loads(destination.read_text(encoding="utf-8"))
        assert any(post["slug"] == "test-post" for post in payload["posts"])

    def test_an_export_to_an_existing_file_is_reported(
        self, runner, cli_app, tmp_path, monkeypatch
    ):
        def _raise(destination, *, force=False):
            raise FileExistsError(f"Destination file already exists: {destination}.")

        monkeypatch.setattr("app.services.operations.transfer.export_site_data", _raise)

        result = runner.invoke(cli_app.cli, ["export-data", str(tmp_path / "export.json")])

        assert result.exit_code == 0
        assert "already exists" in result.output.lower()

    def test_the_site_data_is_imported(self, runner, cli_app, tmp_path, db):
        from app.models import Post

        source = tmp_path / "import.json"
        source.write_text(
            json.dumps(
                {
                    "version": 1,
                    "posts": [
                        {
                            "title": "Imported Post",
                            "slug": "imported-post",
                            "body": "# Imported",
                            "summary": "Imported summary",
                            "published": True,
                            "tags": [],
                        }
                    ],
                    "tags": [],
                    "subscribers": [],
                    "pages": [],
                }
            ),
            encoding="utf-8",
        )

        result = runner.invoke(cli_app.cli, ["import-data", str(source)])

        assert result.exit_code == 0
        assert "Imported" in result.output
        imported = db.session.execute(db.select(Post).filter_by(slug="imported-post")).scalar_one()
        assert imported.title == "Imported Post"


class TestSeedCommand:
    def test_the_database_is_seeded(self, runner, cli_app, db):
        from app.models import Page, Post, Subscriber, Tag

        result = runner.invoke(cli_app.cli, ["seed", "--posts", "2", "--subscribers", "3"])

        assert result.exit_code == 0
        assert "Seed complete!" in result.output
        assert db.session.execute(db.select(Tag)).scalars().all()
        assert len(db.session.execute(db.select(Post)).scalars().all()) == 2
        assert len(db.session.execute(db.select(Subscriber)).scalars().all()) == 3
        assert len(db.session.execute(db.select(Page)).scalars().all()) == 2

    def test_seeding_a_populated_database_is_refused(self, runner, cli_app, db):
        from app.models import Tag

        db.session.add(Tag(name="Existing", slug="existing"))
        db.session.commit()

        result = runner.invoke(cli_app.cli, ["seed"])

        assert result.exit_code == 0
        assert "already contains data" in result.output


class TestThemeCommandVariants:
    def test_the_list_command_reports_an_empty_registry(self, runner, cli_app, monkeypatch):
        from app.services.operations.results import ThemeListResult

        monkeypatch.setattr(
            "app.services.operations.themes.list_theme_descriptors",
            lambda source="all": ThemeListResult(
                ok=True,
                code="themes.list.ok",
                summary="no themes",
                themes=[],
                total=0,
            ),
        )

        result = runner.invoke(cli_app.cli, ["themes", "list"])

        assert result.exit_code == 0
        assert "No themes found." in result.output

    def test_the_list_command_can_show_paths_and_warnings(self, runner, cli_app, monkeypatch):
        from app.services.operations.results import ThemeListResult

        monkeypatch.setattr(
            "app.services.operations.themes.list_theme_descriptors",
            lambda source="all": ThemeListResult(
                ok=True,
                code="themes.list.ok",
                summary="one theme",
                themes=[
                    {
                        "display_name": "Example Theme",
                        "canonical_name": "Example Theme",
                        "source": "external",
                        "is_dark": False,
                        "status": "ok",
                        "overrides_bundled": True,
                        "path": "/tmp/themes/example.toml",
                        "warnings": ["contrast warning"],
                    }
                ],
                total=1,
            ),
        )

        result = runner.invoke(cli_app.cli, ["themes", "list", "--verbose", "--warnings"])

        assert result.exit_code == 0
        assert "/tmp/themes/example.toml" in result.output
        assert "(overrides)" in result.output
        assert "WARNING: contrast warning" in result.output

    def test_the_list_command_drops_warnings_from_its_json_output(
        self, runner, cli_app, monkeypatch
    ):
        from app.services.operations.results import ThemeListResult

        monkeypatch.setattr(
            "app.services.operations.themes.list_theme_descriptors",
            lambda source="all": ThemeListResult(
                ok=True,
                code="themes.list.ok",
                summary="one theme",
                themes=[
                    {
                        "display_name": "Example Theme",
                        "canonical_name": "Example Theme",
                        "source": "bundled",
                        "is_dark": True,
                        "status": "ok",
                        "overrides_bundled": False,
                        "warnings": ["contrast warning"],
                    }
                ],
                total=1,
            ),
        )

        result = runner.invoke(cli_app.cli, ["themes", "list", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert "warnings" not in payload[0]

    def test_the_list_command_keeps_warnings_when_asked_for_them(
        self, runner, cli_app, monkeypatch
    ):
        from app.services.operations.results import ThemeListResult

        monkeypatch.setattr(
            "app.services.operations.themes.list_theme_descriptors",
            lambda source="all": ThemeListResult(
                ok=True,
                code="themes.list.ok",
                summary="one theme",
                themes=[
                    {
                        "display_name": "Example Theme",
                        "canonical_name": "Example Theme",
                        "source": "bundled",
                        "is_dark": True,
                        "status": "ok",
                        "overrides_bundled": False,
                        "warnings": ["contrast warning"],
                    }
                ],
                total=1,
            ),
        )

        result = runner.invoke(cli_app.cli, ["themes", "list", "--json", "--warnings"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload[0]["warnings"] == ["contrast warning"]

    def test_a_theme_that_is_neither_the_active_nor_the_fallback_is_reported(
        self, runner, cli_app, db
    ):
        from app.models import SiteSettings

        settings = SiteSettings.get_instance()
        settings.theme_dark_name = "Nord"
        settings.theme_light_name = "Catppuccin Latte"
        db.session.commit()

        result = runner.invoke(cli_app.cli, ["themes", "inspect", "Dracula"])

        assert result.exit_code == 0
        assert "Active as: neither" in result.output

    def test_the_registry_refresh_reports_added_and_removed_themes(
        self, runner, cli_app, monkeypatch
    ):
        from app.services.operations.results import ThemeRefreshResult

        monkeypatch.setattr(
            "app.services.operations.themes.refresh_theme_registry",
            lambda: ThemeRefreshResult(
                ok=True,
                code="themes.refresh.ok",
                summary="refreshed",
                old_count=50,
                new_count=51,
                added=["New Theme"],
                removed=["Old Theme"],
            ),
        )

        result = runner.invoke(cli_app.cli, ["themes", "refresh"])

        assert result.exit_code == 0
        assert "50 -> 51 themes" in result.output
        assert "Added: New Theme" in result.output
        assert "Removed: Old Theme" in result.output

    def test_the_registry_refresh_warns_about_a_missing_active_theme(
        self, runner, cli_app, db, monkeypatch
    ):
        from app.models import SiteSettings
        from app.services.operations.results import ThemeRefreshResult

        settings = SiteSettings.get_instance()
        settings.theme_dark_name = "Theme That Vanished"
        db.session.commit()

        monkeypatch.setattr(
            "app.services.operations.themes.refresh_theme_registry",
            lambda: ThemeRefreshResult(
                ok=True,
                code="themes.refresh.ok",
                summary="refreshed",
                old_count=50,
                new_count=50,
            ),
        )

        result = runner.invoke(cli_app.cli, ["themes", "refresh"])

        assert result.exit_code == 0
        assert "WARNING: Dark theme 'Theme That Vanished' no longer available." in result.output

    def test_the_theme_paths_report_an_external_directory(self, runner, cli_app, monkeypatch):
        from app.services.operations.results import ThemePathsResult

        monkeypatch.setattr(
            "app.services.operations.themes.get_theme_paths",
            lambda: ThemePathsResult(
                ok=True,
                code="themes.paths.ok",
                summary="paths",
                paths={
                    "bundled": {
                        "package_name": "app.themes.bundled",
                        "package_version": "1.2.3",
                        "theme_count": 50,
                        "toml_count": 50,
                    },
                    "external": {
                        "configured": "/tmp/themes",
                        "exists": True,
                        "readable": True,
                        "toml_count": 3,
                    },
                    "config": {
                        "THEME_ALLOW_EXTERNAL": "true",
                        "THEME_STRICT_VALIDATION": "false",
                        "max_file_size": 102400,
                    },
                },
            ),
        )

        result = runner.invoke(cli_app.cli, ["themes", "paths"])

        assert result.exit_code == 0
        assert "app.themes.bundled" in result.output
        assert "Bundled themes: 50 files" in result.output
        assert "Configured: /tmp/themes" in result.output
        assert "Exists: yes" in result.output
        assert "Readable: yes" in result.output
        assert "Theme files: 3" in result.output

    def test_the_theme_paths_report_a_disabled_external_directory(
        self, runner, cli_app, monkeypatch
    ):
        from app.services.operations.results import ThemePathsResult

        monkeypatch.setattr(
            "app.services.operations.themes.get_theme_paths",
            lambda: ThemePathsResult(
                ok=True,
                code="themes.paths.ok",
                summary="paths",
                paths={
                    "bundled": {},
                    "external": {},
                    "config": {
                        "THEME_ALLOW_EXTERNAL": "false",
                        "THEME_STRICT_VALIDATION": "false",
                        "max_file_size": 102400,
                    },
                },
            ),
        )

        result = runner.invoke(cli_app.cli, ["themes", "paths"])

        assert result.exit_code == 0
        assert "Bundled package: app/themes/bundled/" in result.output
        assert "Bundled themes: directory not found" in result.output
        assert "Configured: (none)" in result.output
        assert "External themes are disabled" in result.output

    def test_the_accessibility_report_lists_the_findings(self, runner, cli_app, monkeypatch):
        from app.services.operations.results import AccessibilityReportResult

        monkeypatch.setattr(
            "app.services.operations.themes.run_accessibility_check",
            lambda source="all", strict=False: AccessibilityReportResult(
                ok=True,
                code="themes.accessibility.ok",
                summary="checked",
                total_themes=1,
                passed_exact=0,
                passed_with_exceptions=0,
                failed=1,
                reports=[
                    {
                        "theme_name": "Example Theme",
                        "source": "bundled",
                        "findings": [
                            {
                                "severity": "mandatory",
                                "is_expected": False,
                                "description": "contrast too low",
                                "ratio": 1.5,
                                "required": 4.5,
                                "wcag": "AA",
                                "foreground": "#000000",
                                "background": "#ffffff",
                            },
                            {
                                "severity": "mandatory",
                                "is_expected": True,
                                "description": "documented exception",
                                "ratio": 2.0,
                                "required": 4.5,
                                "wcag": "AA",
                                "foreground": "#111111",
                                "background": "#eeeeee",
                                "exception_reason": "documented in the exception manifest",
                            },
                            {
                                "severity": "advisory",
                                "description": "border contrast is low",
                                "ratio": 1.2,
                                "required": 3.0,
                                "wcag": "AA",
                                "foreground": "#222222",
                                "background": "#dddddd",
                            },
                        ],
                    }
                ],
            ),
        )

        result = runner.invoke(cli_app.cli, ["themes", "accessibility"])

        assert result.exit_code == 0
        assert "[FAIL] contrast too low" in result.output
        assert "[EXCEPT] documented exception" in result.output
        assert "[WARN] border contrast is low" in result.output
        assert "reason: documented in the exception manifest" in result.output
        assert "1 theme(s) have unexpected mandatory accessibility failures." in result.output

    def test_the_accessibility_report_rejects_a_strict_failure(self, runner, cli_app, monkeypatch):
        from app.services.operations.results import AccessibilityReportResult

        monkeypatch.setattr(
            "app.services.operations.themes.run_accessibility_check",
            lambda source="all", strict=True: AccessibilityReportResult(
                ok=False,
                code="themes.accessibility.strict_failed",
                summary="strict",
                total_themes=1,
                failed=1,
                details={"strict_rejected": ["Broken Theme"]},
            ),
        )

        result = runner.invoke(cli_app.cli, ["themes", "accessibility", "--strict"])

        assert result.exit_code == 1
        assert "REJECTED: Broken Theme" in result.output

    def test_the_accessibility_report_passes_when_no_theme_fails(
        self, runner, cli_app, monkeypatch
    ):
        from app.services.operations.results import AccessibilityReportResult

        monkeypatch.setattr(
            "app.services.operations.themes.run_accessibility_check",
            lambda source="all", strict=False: AccessibilityReportResult(
                ok=True,
                code="themes.accessibility.ok",
                summary="checked",
                total_themes=1,
                passed_exact=1,
                passed_with_exceptions=0,
                failed=0,
            ),
        )

        result = runner.invoke(cli_app.cli, ["themes", "accessibility"])

        assert result.exit_code == 0
        assert "All themes pass mandatory accessibility gates" in result.output
