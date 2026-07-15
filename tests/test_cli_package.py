import importlib
import os
import sys

from click.testing import CliRunner


def test_command_registration_import_safety():
    import devlog_cli.main

    assert not hasattr(devlog_cli.main, "app")


def test_no_import_time_app_construction():
    modules_before = set(sys.modules.keys())
    importlib.import_module("devlog_cli")
    importlib.import_module("devlog_cli.main")
    importlib.import_module("devlog_cli.context")
    importlib.import_module("devlog_cli.result")
    importlib.import_module("devlog_cli.output")
    importlib.import_module("devlog_cli.errors")
    importlib.import_module("devlog_cli.exit_codes")
    importlib.import_module("devlog_cli.commands")
    new_modules = set(sys.modules.keys()) - modules_before
    for mod in new_modules:
        assert not mod.startswith("app."), f"devlog_cli imported app module at import time: {mod}"


def test_no_secret_values_in_cli_output():
    secret_key = os.environ.get("SECRET_KEY", "")
    admin_password = os.environ.get("ADMIN_PASSWORD", "")

    runner = CliRunner()
    from devlog_cli.main import main

    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    if secret_key:
        assert secret_key not in result.output
    if admin_password:
        assert admin_password not in result.output

    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    if secret_key:
        assert secret_key not in result.output
    if admin_password:
        assert admin_password not in result.output


def test_typed_result_serialization():
    from app.services.operations.results import (
        OperationResult,
        AdminCreatedResult,
        AdminPromotedResult,
        BackupCreateResult,
        DatabaseCheckResult,
        ExportResult,
        ImportResult,
        MediaCleanupResult,
        MigrationStatusResult,
        SearchRebuildResult,
        ThemeListResult,
        ThemeValidationResult,
    )

    subclasses = [
        OperationResult(ok=True, code="test.op", summary="test"),
        AdminCreatedResult(ok=True, code="admin.created", summary="created", username="admin"),
        AdminPromotedResult(ok=True, code="admin.promoted", summary="promoted", username="admin"),
        BackupCreateResult(ok=True, code="backup.created", summary="created", path="/tmp/bak"),
        DatabaseCheckResult(ok=True, code="db.check", summary="healthy", backend="sqlite"),
        ExportResult(ok=True, code="export", summary="done", posts=5),
        ImportResult(ok=True, code="import", summary="done", tags=3),
        MediaCleanupResult(ok=True, code="media.cleanup", summary="done", orphaned_deleted=2),
        MigrationStatusResult(ok=True, code="migration.status", summary="current"),
        SearchRebuildResult(ok=True, code="search.rebuild", summary="rebuilt", indexed_count=10),
        ThemeListResult(ok=True, code="themes.list", summary="listed", total=50),
        ThemeValidationResult(ok=True, code="themes.validate", summary="valid"),
    ]

    for result in subclasses:
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "ok" in d
        assert "code" in d
        assert "summary" in d
        assert isinstance(d["ok"], bool)
        assert isinstance(d["code"], str)
        assert isinstance(d["summary"], str)
