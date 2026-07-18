"""Tests for devlog_cli.commands.doctor — CLI doctor command."""

from __future__ import annotations

import json
import re

import pytest
from click.testing import CliRunner

from devlog_cli.main import main


@pytest.fixture
def runner():
    return CliRunner()


def _extract_json(output: str) -> dict:
    """Extract the first JSON object from output that may contain log lines."""
    match = re.search(r"\{.*\}", output, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No JSON found in output: {output[:200]}")


class TestDoctorHelp:
    def test_help_output(self, runner):
        result = runner.invoke(main, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "doctor" in result.output.lower()

    def test_lists_all_commands(self, runner):
        result = runner.invoke(main, ["--help"])
        assert "doctor" in result.output


class TestDoctorListChecks:
    def test_list_checks(self, runner, app):
        result = runner.invoke(main, ["doctor", "--list-checks"])
        assert result.exit_code == 0
        assert "check_id" in result.output or "Available checks" in result.output

    def test_list_checks_json(self, runner, app):
        result = runner.invoke(main, ["--json", "doctor", "--list-checks"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "check_id" in data[0]

    def test_list_checks_by_category(self, runner, app):
        result = runner.invoke(main, ["doctor", "--list-checks", "--category", "database"])
        assert result.exit_code == 0
        assert "db." in result.output

    def test_list_checks_empty_category(self, runner, app):
        result = runner.invoke(main, ["doctor", "--list-checks", "--category", "nonexistent"])
        assert result.exit_code == 0
        assert "No checks" in result.output or "0" in result.output


class TestDoctorBasic:
    def test_basic_run(self, runner, app):
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code in (0, 8)
        assert "Mode:" in result.output or "pass" in result.output.lower()

    def test_json_output(self, runner, app):
        result = runner.invoke(main, ["--json", "doctor"])
        assert result.exit_code in (0, 8)
        data = _extract_json(result.output)
        assert "ok" in data
        assert "status" in data
        assert "details" in data
        assert "checks" in data["details"]

    def test_single_check(self, runner, app):
        result = runner.invoke(main, ["doctor", "--check", "pkg.version"])
        assert result.exit_code == 0

    def test_single_check_json(self, runner, app):
        result = runner.invoke(main, ["--json", "doctor", "--check", "pkg.version"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["details"]["checks"]) == 1
        assert data["details"]["checks"][0]["check_id"] == "pkg.version"


class TestDoctorCategories:
    def test_category_filter(self, runner, app):
        result = runner.invoke(main, ["doctor", "--category", "database"])
        assert result.exit_code in (0, 8)

    def test_category_json(self, runner, app):
        result = runner.invoke(main, ["--json", "doctor", "--category", "database"])
        assert result.exit_code in (0, 8)
        data = _extract_json(result.output)
        for check in data["details"]["checks"]:
            assert check["category"] == "database"


class TestDoctorProduction:
    def test_production_flag(self, runner, app):
        result = runner.invoke(main, ["doctor", "--production"])
        assert result.exit_code in (0, 8)

    def test_production_json(self, runner, app):
        result = runner.invoke(main, ["--json", "doctor", "--production"])
        assert result.exit_code in (0, 8)
        data = _extract_json(result.output)
        assert "ok" in data


class TestDoctorVerbose:
    def test_verbose_output(self, runner, app):
        result = runner.invoke(main, ["--verbose", "doctor", "--check", "config.load"])
        assert result.exit_code == 0


class TestDoctorFixSafe:
    def test_fix_safe_dry_run(self, runner, app):
        result = runner.invoke(main, ["doctor", "--fix-safe", "--check", "fs.required_dirs"])
        assert result.exit_code in (0, 8)


class TestDoctorNonexistentCheck:
    def test_nonexistent_check(self, runner, app):
        result = runner.invoke(main, ["doctor", "--check", "nonexistent.check"])
        assert result.exit_code == 0
