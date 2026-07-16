from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from devlog_cli.main import main

_TEST_ENV = {
    "SECRET_KEY": "test-secret-key-for-cli-testing-1234567890",
    "ADMIN_PASSWORD": "test-admin-password-1234567890",
}


@pytest.fixture
def runner():
    return CliRunner(env=_TEST_ENV)


class TestPathsStatus:
    def test_status_development(self, runner):
        result = runner.invoke(main, ["paths", "status", "--mode", "development"])
        assert result.exit_code == 0
        assert "Mode: development" in result.output

    def test_status_system(self, runner):
        result = runner.invoke(main, ["paths", "status", "--mode", "system"])
        assert result.exit_code == 0
        assert "Mode: system" in result.output

    def test_status_docker(self, runner):
        result = runner.invoke(main, ["paths", "status", "--mode", "docker"])
        assert result.exit_code == 0
        assert "Mode: docker" in result.output

    def test_status_user(self, runner):
        result = runner.invoke(main, ["paths", "status", "--mode", "user"])
        assert result.exit_code == 0
        assert "Mode: user" in result.output

    def test_status_json_output(self, runner):
        result = runner.invoke(main, ["--json", "paths", "status", "--mode", "development"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["code"] == "paths.status"
        assert "paths" in data["details"]
        assert isinstance(data["details"]["paths"], list)

    def test_status_json_has_path_entries(self, runner):
        result = runner.invoke(main, ["--json", "paths", "status", "--mode", "development"])
        data = json.loads(result.output)
        paths = data["details"]["paths"]
        assert len(paths) == 11
        for entry in paths:
            assert "name" in entry
            assert "path" in entry
            assert "provenance" in entry
            assert "exists" in entry

    def test_status_default_mode_is_development(self, runner):
        result = runner.invoke(main, ["paths", "status"])
        assert result.exit_code == 0
        assert "Mode: development" in result.output

    def test_status_json_mode_field(self, runner):
        result = runner.invoke(main, ["--json", "paths", "status", "--mode", "docker"])
        data = json.loads(result.output)
        assert data["details"]["mode"] == "docker"

    def test_status_json_path_count(self, runner):
        result = runner.invoke(main, ["--json", "paths", "status", "--mode", "development"])
        data = json.loads(result.output)
        assert "path(s) resolved" in data["summary"]

    def test_status_help(self, runner):
        result = runner.invoke(main, ["paths", "status", "--help"])
        assert result.exit_code == 0
        assert "--mode" in result.output
        assert "--json" in result.output


class TestPathsDiscoverLegacy:
    def test_discover_empty_dir(self, runner, tmp_path):
        result = runner.invoke(main, ["paths", "discover-legacy", "--search-root", str(tmp_path)])
        assert result.exit_code == 0
        assert "0 item(s) found" in result.output

    def test_discover_with_database(self, runner, tmp_path):
        (tmp_path / "blog.sqlite3").touch()
        result = runner.invoke(main, ["paths", "discover-legacy", "--search-root", str(tmp_path)])
        assert result.exit_code == 0
        assert "1 item(s) found" in result.output

    def test_discover_json_output(self, runner, tmp_path):
        (tmp_path / "test.db").touch()
        (tmp_path / "config.toml").touch()
        result = runner.invoke(
            main, ["--json", "paths", "discover-legacy", "--search-root", str(tmp_path)]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["code"] == "paths.discover_legacy"
        assert "confirmed" in data["details"]
        assert "likely" in data["details"]
        assert "search_root" in data["details"]

    def test_discover_json_confirmed_items(self, runner, tmp_path):
        (tmp_path / "config.toml").touch()
        (tmp_path / ".env").touch()
        result = runner.invoke(
            main, ["--json", "paths", "discover-legacy", "--search-root", str(tmp_path)]
        )
        data = json.loads(result.output)
        confirmed = data["details"]["confirmed"]
        types = {item["type"] for item in confirmed}
        assert "config" in types
        assert "env" in types

    def test_discover_json_likely_items(self, runner, tmp_path):
        (tmp_path / "uploads").mkdir()
        (tmp_path / "blog.sqlite3").touch()
        result = runner.invoke(
            main, ["--json", "paths", "discover-legacy", "--search-root", str(tmp_path)]
        )
        data = json.loads(result.output)
        likely = data["details"]["likely"]
        types = {item["type"] for item in likely}
        assert "uploads" in types
        assert "database" in types

    def test_discover_comprehensive(self, runner, tmp_path):
        (tmp_path / "config.toml").touch()
        (tmp_path / ".env").touch()
        (tmp_path / "blog.sqlite3").touch()
        (tmp_path / "uploads").mkdir()
        (tmp_path / "backups").mkdir()
        (tmp_path / "themes").mkdir()
        (tmp_path / "logs").mkdir()
        result = runner.invoke(
            main, ["--json", "paths", "discover-legacy", "--search-root", str(tmp_path)]
        )
        data = json.loads(result.output)
        total = len(data["details"]["confirmed"]) + len(data["details"]["likely"])
        assert total == 7

    def test_discover_help(self, runner):
        result = runner.invoke(main, ["paths", "discover-legacy", "--help"])
        assert result.exit_code == 0
        assert "--search-root" in result.output
        assert "--json" in result.output


class TestPathsMigrate:
    def test_migrate_plan_output(self, runner):
        result = runner.invoke(
            main,
            ["paths", "migrate", "--from-mode", "development", "--to-mode", "system"],
        )
        assert result.exit_code == 0
        assert "Migration plan" in result.output

    def test_migrate_json_output(self, runner):
        result = runner.invoke(
            main,
            [
                "--json",
                "paths",
                "migrate",
                "--from-mode",
                "development",
                "--to-mode",
                "system",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["code"] == "paths.migrate.plan"
        assert "steps" in data["details"]
        assert isinstance(data["details"]["steps"], list)

    def test_migrate_json_steps_structure(self, runner):
        result = runner.invoke(
            main,
            [
                "--json",
                "paths",
                "migrate",
                "--from-mode",
                "development",
                "--to-mode",
                "docker",
            ],
        )
        data = json.loads(result.output)
        steps = data["details"]["steps"]
        assert len(steps) > 0
        for step in steps:
            assert "action" in step
            assert "target" in step
            assert "description" in step

    def test_migrate_json_modes(self, runner):
        result = runner.invoke(
            main,
            [
                "--json",
                "paths",
                "migrate",
                "--from-mode",
                "development",
                "--to-mode",
                "system",
            ],
        )
        data = json.loads(result.output)
        assert data["details"]["source_mode"] == "development"
        assert data["details"]["target_mode"] == "system"

    def test_migrate_requires_downtime_field(self, runner):
        result = runner.invoke(
            main,
            [
                "--json",
                "paths",
                "migrate",
                "--from-mode",
                "development",
                "--to-mode",
                "system",
            ],
        )
        data = json.loads(result.output)
        assert "requires_downtime" in data["details"]
        assert isinstance(data["details"]["requires_downtime"], bool)

    def test_migrate_dry_run_always(self, runner):
        result = runner.invoke(
            main,
            [
                "--json",
                "paths",
                "migrate",
                "--from-mode",
                "development",
                "--to-mode",
                "system",
            ],
        )
        data = json.loads(result.output)
        assert data["details"]["dry_run"] is True

    def test_migrate_missing_from_mode(self, runner):
        result = runner.invoke(
            main,
            ["paths", "migrate", "--to-mode", "system"],
        )
        assert result.exit_code != 0

    def test_migrate_missing_to_mode(self, runner):
        result = runner.invoke(
            main,
            ["paths", "migrate", "--from-mode", "development"],
        )
        assert result.exit_code != 0

    def test_migrate_same_mode_warning(self, runner):
        result = runner.invoke(
            main,
            [
                "--json",
                "paths",
                "migrate",
                "--from-mode",
                "development",
                "--to-mode",
                "development",
            ],
        )
        data = json.loads(result.output)
        assert any("identical" in w.lower() for w in data["details"]["warnings"])

    def test_migrate_help(self, runner):
        result = runner.invoke(main, ["paths", "migrate", "--help"])
        assert result.exit_code == 0
        assert "--from-mode" in result.output
        assert "--to-mode" in result.output


class TestPathsCheck:
    def test_check_development(self, runner):
        result = runner.invoke(main, ["paths", "check", "--mode", "development"])
        assert result.exit_code in (0, 8)
        assert "error(s)" in result.output

    def test_check_json_output(self, runner):
        result = runner.invoke(main, ["--json", "paths", "check", "--mode", "development"])
        assert result.exit_code in (0, 8)
        data = json.loads(result.output)
        assert "success" in data["details"]
        assert "errors" in data["details"]
        assert "warnings" in data["details"]
        assert "path_checks" in data["details"]

    def test_check_json_path_checks(self, runner):
        result = runner.invoke(main, ["--json", "paths", "check", "--mode", "development"])
        data = json.loads(result.output)
        path_checks = data["details"]["path_checks"]
        assert isinstance(path_checks, dict)
        assert len(path_checks) == 11

    def test_check_json_success_field(self, runner):
        result = runner.invoke(main, ["--json", "paths", "check", "--mode", "development"])
        data = json.loads(result.output)
        assert isinstance(data["details"]["success"], bool)

    def test_check_json_errors_list(self, runner):
        result = runner.invoke(main, ["--json", "paths", "check", "--mode", "development"])
        data = json.loads(result.output)
        assert isinstance(data["details"]["errors"], list)

    def test_check_json_warnings_list(self, runner):
        result = runner.invoke(main, ["--json", "paths", "check", "--mode", "development"])
        data = json.loads(result.output)
        assert isinstance(data["details"]["warnings"], list)

    def test_check_help(self, runner):
        result = runner.invoke(main, ["paths", "check", "--help"])
        assert result.exit_code == 0
        assert "--mode" in result.output
        assert "--json" in result.output

    def test_check_default_mode(self, runner):
        result = runner.invoke(main, ["paths", "check"])
        assert result.exit_code in (0, 8)


class TestPathsHelp:
    def test_paths_help(self, runner):
        result = runner.invoke(main, ["paths", "--help"])
        assert result.exit_code == 0
        assert "status" in result.output
        assert "discover-legacy" in result.output
        assert "migrate" in result.output
        assert "check" in result.output

    def test_all_subcommands_registered(self, runner):
        result = runner.invoke(main, ["paths", "--help"])
        output = result.output
        assert "status" in output
        assert "discover-legacy" in output
        assert "migrate" in output
        assert "check" in output
