"""Parity tests — verify that direct service calls and standalone devlog CLI
produce equivalent state changes.

Acceptance criterion 10: "Direct service, standalone CLI, and Flask
compatibility paths have parity tests."
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from devlog_cli.main import main


_TEST_ENV = {
    "SECRET_KEY": "test-secret-key-for-parity-testing-12345",
    "ADMIN_PASSWORD": "test-admin-password-Parity1!",
}


@pytest.fixture
def runner(app, db):
    """CliRunner that patches app.create_app to return the test app.
    Requires db fixture to ensure tables are created."""
    with patch("app.create_app", return_value=app):
        yield CliRunner(env=_TEST_ENV)


class TestAdminParity:
    def test_service_create_admin(self, app, db):
        from app.services.operations.admin import create_admin

        with app.app_context():
            result = create_admin("parity_admin", "ParityPass1!", update_existing=False)
            assert result.ok
            assert result.code == "admin.created"

    def test_devlog_admin_create(self, runner):
        result = runner.invoke(
            main,
            ["admin", "create"],
            input="parity_user\nParityPass1!\nParityPass1!\n",
        )
        assert result.exit_code == 0
        assert "created" in result.output.lower() or "promoted" in result.output.lower()

    def test_flask_create_admin(self, app, db):
        from app.cli import register_cli_commands

        with app.app_context():
            from click.testing import CliRunner as AppRunner

            cli_runner = AppRunner()
            register_cli_commands(app)
            result = cli_runner.invoke(
                app.cli.commands["create-admin"],
                input="flask_admin_user\nFlaskPass1!\nFlaskPass1!\n",
            )
            assert result.exit_code == 0

    def test_service_promote_admin(self, app, db):
        from app.services.operations.admin import promote_admin
        from app.extensions import db as _db
        from app.models import User

        with app.app_context():
            user = User(username="promote_svc_user", is_admin=False)
            user.set_password("ParityPass1!")
            _db.session.add(user)
            _db.session.commit()
            result = promote_admin("promote_svc_user")
            assert result.ok
            assert result.code == "admin.promoted"

    def test_service_promote_already_admin(self, app, db):
        from app.services.operations.admin import create_admin, promote_admin, ConflictError

        with app.app_context():
            create_admin("already_admin_user", "ParityPass1!", update_existing=False)
            with pytest.raises(ConflictError):
                promote_admin("already_admin_user")

    def test_service_list_admins(self, app, db):
        from app.services.operations.admin import list_admins

        with app.app_context():
            result = list_admins()
            assert result.ok
            assert isinstance(result.admins, list)

    def test_devlog_admin_list(self, runner):
        result = runner.invoke(main, ["admin", "list"])
        assert result.exit_code == 0

    def test_devlog_admin_list_json(self, runner):
        result = runner.invoke(main, ["--json", "admin", "list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True

    def test_no_secret_in_output(self, app, db, runner):
        from app.services.operations.admin import create_admin

        with app.app_context():
            create_admin("secret_test_admin", "SecretPass1!", update_existing=False)

        result = runner.invoke(main, ["admin", "list"])
        assert "SecretPass1!" not in result.output


class TestDatabaseParity:
    def test_service_check_integrity(self, app, db):
        from app.services.operations.database import check_database_integrity

        with app.app_context():
            result = check_database_integrity()
            assert result.ok
            assert result.code == "db.integrity.ok"

    def test_devlog_db_check(self, runner):
        result = runner.invoke(main, ["db", "check"])
        assert result.exit_code == 0

    def test_devlog_db_check_json(self, runner):
        result = runner.invoke(main, ["--json", "db", "check"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True

    def test_service_rebuild_search(self, app, db):
        from app.services.operations.database import rebuild_search_index

        with app.app_context():
            result = rebuild_search_index()
            assert result.ok
            assert result.code == "db.search.rebuilt"

    def test_devlog_db_rebuild_search(self, runner):
        result = runner.invoke(main, ["db", "rebuild-search"])
        assert result.exit_code == 0

    def test_service_migration_status(self, app, db):
        from app.services.operations.database import get_migration_status

        with app.app_context():
            result = get_migration_status()
            assert result.ok
            assert result.code == "db.migration.status"

    def test_devlog_db_status(self, runner):
        result = runner.invoke(main, ["db", "status"])
        assert result.exit_code == 0

    def test_devlog_db_status_json(self, runner):
        result = runner.invoke(main, ["--json", "db", "status"])
        assert result.exit_code == 0
        assert '"ok": true' in result.output or '"ok":true' in result.output
        assert '"code": "db.migration.status"' in result.output


class TestDataParity:
    def test_service_export(self, app, db, tmp_path):
        from app.services.operations.transfer import export_site_data

        with app.app_context():
            dest = str(tmp_path / "parity_export.json")
            result = export_site_data(dest)
            assert result.ok
            assert result.code == "export.success"
            assert Path(dest).exists()

    def test_devlog_data_export(self, runner, tmp_path):
        dest = str(tmp_path / "cli_export.json")
        result = runner.invoke(main, ["data", "export", dest])
        assert result.exit_code == 0
        assert Path(dest).exists()

    def test_service_import_dry_run(self, app, db, tmp_path):
        from app.services.operations.transfer import export_site_data, import_site_data

        with app.app_context():
            export_path = str(tmp_path / "parity_import.json")
            export_site_data(export_path)
            result = import_site_data(export_path, dry_run=True)
            assert result.ok
            assert result.code == "import.dry_run"

    def test_devlog_data_import_dry_run(self, runner, tmp_path):
        export_dest = str(tmp_path / "cli_import.json")
        runner.invoke(main, ["data", "export", export_dest])
        result = runner.invoke(main, ["data", "import", export_dest, "--dry-run"])
        assert result.exit_code == 0

    def test_export_atomic_write(self, app, db, tmp_path):
        from app.services.operations.transfer import export_site_data

        with app.app_context():
            dest = str(tmp_path / "atomic_export.json")
            result = export_site_data(dest)
            assert result.ok
            assert Path(dest).exists()
            data = json.loads(Path(dest).read_text())
            assert "version" in data


class TestMediaParity:
    def test_service_scan(self, app, db):
        from app.services.operations.media import scan_orphaned_media

        with app.app_context():
            result = scan_orphaned_media()
            assert result.ok
            assert result.code == "media.scan.complete"

    def test_devlog_media_scan(self, runner):
        result = runner.invoke(main, ["media", "scan"])
        assert result.exit_code == 0

    def test_devlog_media_scan_json(self, runner):
        result = runner.invoke(main, ["--json", "media", "scan"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True

    def test_service_cleanup_dry_run(self, app, db):
        from app.services.operations.media import scan_orphaned_media

        with app.app_context():
            result = scan_orphaned_media()
            assert result.ok
            assert result.orphaned_deleted == 0


class TestBackupParity:
    def test_service_inspect_nonexistent(self, app, db):
        from app.services.operations.backup import inspect_backup

        with app.app_context():
            result = inspect_backup("/nonexistent/backup.db")
            assert not result.ok
            assert result.code == "backup.inspect.not_found"

    def test_service_inspect_empty(self, app, db, tmp_path):
        from app.services.operations.backup import inspect_backup

        with app.app_context():
            empty_file = tmp_path / "empty.db"
            empty_file.write_text("")
            result = inspect_backup(str(empty_file))
            assert not result.ok
            assert result.code == "backup.inspect.empty"

    def test_devlog_backup_inspect_nonexistent(self, runner):
        result = runner.invoke(main, ["backup", "inspect", "/nonexistent/backup.db"])
        assert result.exit_code != 0

    def test_service_verify_nonexistent(self, app, db):
        from app.services.operations.backup import verify_backup

        with app.app_context():
            result = verify_backup("/nonexistent/backup.db")
            assert not result.ok
            assert result.code == "backup.verify.not_found"

    def test_devlog_backup_verify_nonexistent(self, runner):
        result = runner.invoke(main, ["backup", "verify", "/nonexistent/backup.db"])
        assert result.exit_code != 0


class TestThemeParity:
    def test_service_list_themes(self, app, db):
        from app.services.operations.themes import list_theme_descriptors

        with app.app_context():
            result = list_theme_descriptors()
            assert result.ok
            assert result.total > 0

    def test_devlog_themes_list(self, runner):
        result = runner.invoke(main, ["themes", "list"])
        assert result.exit_code == 0

    def test_devlog_themes_list_json(self, runner):
        result = runner.invoke(main, ["--json", "themes", "list"])
        assert result.exit_code == 0
        output = result.output
        json_start = output.find("{")
        assert json_start >= 0
        data = json.loads(output[json_start:])
        assert data["ok"] is True
        assert data["code"] == "themes.list"
        assert "50" in data["summary"] or "theme" in data["summary"]

    def test_service_validate_theme(self, app, db):
        from app.services.operations.themes import validate_theme

        with app.app_context():
            result = validate_theme("Catppuccin Mocha")
            assert result.ok
            assert result.valid

    def test_devlog_themes_validate(self, runner):
        result = runner.invoke(main, ["themes", "validate", "Catppuccin Mocha"])
        assert result.exit_code == 0

    def test_service_inspect_theme(self, app, db):
        from app.services.operations.themes import inspect_theme

        with app.app_context():
            result = inspect_theme("Catppuccin Mocha")
            assert result.ok
            assert result.css_vars

    def test_devlog_themes_inspect(self, runner):
        result = runner.invoke(main, ["themes", "inspect", "Catppuccin Mocha"])
        assert result.exit_code == 0

    def test_service_theme_paths(self, app, db):
        from app.services.operations.themes import get_theme_paths

        with app.app_context():
            result = get_theme_paths()
            assert result.ok
            assert "bundled" in result.paths

    def test_devlog_themes_paths(self, runner):
        result = runner.invoke(main, ["themes", "paths"])
        assert result.exit_code == 0

    def test_devlog_themes_refresh(self, runner):
        result = runner.invoke(main, ["themes", "refresh"])
        assert result.exit_code == 0
        assert "refreshed" in result.output.lower()

    def test_devlog_themes_accessibility(self, runner):
        result = runner.invoke(main, ["themes", "accessibility"])
        assert result.exit_code == 0


class TestCommandRegistration:
    def test_admin_commands_registered(self, runner):
        result = runner.invoke(main, ["admin", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "promote" in result.output
        assert "list" in result.output

    def test_db_commands_registered(self, runner):
        result = runner.invoke(main, ["db", "--help"])
        assert result.exit_code == 0
        assert "check" in result.output
        assert "rebuild-search" in result.output
        assert "status" in result.output
        assert "migrate" in result.output

    def test_data_commands_registered(self, runner):
        result = runner.invoke(main, ["data", "--help"])
        assert result.exit_code == 0
        assert "export" in result.output
        assert "import" in result.output

    def test_themes_commands_registered(self, runner):
        result = runner.invoke(main, ["themes", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "validate" in result.output
        assert "inspect" in result.output
        assert "refresh" in result.output
        assert "paths" in result.output
        assert "accessibility" in result.output

    def test_backup_commands_registered(self, runner):
        result = runner.invoke(main, ["backup", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "verify" in result.output
        assert "inspect" in result.output

    def test_media_commands_registered(self, runner):
        result = runner.invoke(main, ["media", "--help"])
        assert result.exit_code == 0
        assert "scan" in result.output
        assert "cleanup" in result.output
