from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from app.onboarding.steps import StepResult, _ALL_STEPS
from devlog_cli.main import main

_TEST_ENV = {
    "SECRET_KEY": "test-secret-key-test-secret-key-1234",
    "ADMIN_PASSWORD": "test-password-123",
    "TESTING": "True",
    "PAGE_VIEW_BUFFER_SIZE": "0",
}


@pytest.fixture
def runner():
    return CliRunner(env=_TEST_ENV)


@pytest.fixture
def runner_with_app(runner, app, db):
    with patch("devlog_cli.context.CliContext.ensure_app_context", return_value=app):
        yield runner


def _write_password_file(tmp_path: Path, password: str = "SecurePass1!") -> str:
    pw_file = tmp_path / "password.txt"
    pw_file.write_text(password)
    return str(pw_file)


def _make_passing_steps():
    steps = list(_ALL_STEPS)
    validate_idx = next(i for i, s in enumerate(steps) if s.__name__ == "step_validate_proposal")
    assets_idx = next(i for i, s in enumerate(steps) if s.__name__ == "step_verify_assets")
    readiness_idx = next(i for i, s in enumerate(steps) if s.__name__ == "step_readiness_check")

    def _noop_validate(ctx):
        return StepResult(ok=True, message="Validation passed")

    def _noop_assets(ctx):
        return StepResult(ok=True, message="Assets check complete")

    def _noop_readiness(ctx):
        return StepResult(ok=True, message="Readiness check passed")

    steps[validate_idx] = _noop_validate
    steps[assets_idx] = _noop_assets
    steps[readiness_idx] = _noop_readiness
    return steps


class TestOnboardHelp:
    def test_onboard_help(self, runner):
        result = runner.invoke(main, ["onboard", "--help"])

        assert result.exit_code == 0
        assert "onboard" in result.output.lower() or "onboarding" in result.output.lower()

    def test_onboard_detect_help(self, runner):
        result = runner.invoke(main, ["onboard", "detect", "--help"])

        assert result.exit_code == 0

    def test_onboard_plan_help(self, runner):
        result = runner.invoke(main, ["onboard", "plan", "--help"])

        assert result.exit_code == 0
        assert "--mode" in result.output
        assert "--profile" in result.output

    def test_onboard_run_help(self, runner):
        result = runner.invoke(main, ["onboard", "run", "--help"])

        assert result.exit_code == 0
        assert "--mode" in result.output
        assert "--non-interactive" in result.output
        assert "--dry-run" in result.output


class TestOnboardDetect:
    def test_detect_fresh(self, runner_with_app):
        result = runner_with_app.invoke(main, ["onboard", "detect"])

        assert result.exit_code == 0
        output = result.output
        assert "fresh" in output.lower() or "state" in output.lower()

    def test_detect_json_output(self, runner_with_app):
        result = runner_with_app.invoke(main, ["--json", "onboard", "detect"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert "state" in data["details"]


class TestOnboardPlan:
    def test_plan_native(self, runner_with_app):
        result = runner_with_app.invoke(
            main,
            ["onboard", "plan", "--mode", "native", "--profile", "development"],
        )

        assert result.exit_code == 0

    def test_plan_json_output(self, runner_with_app):
        result = runner_with_app.invoke(
            main,
            ["--json", "onboard", "plan", "--mode", "native", "--profile", "development"],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert "action_count" in data["details"]

    def test_plan_docker(self, runner_with_app):
        result = runner_with_app.invoke(
            main,
            ["onboard", "plan", "--mode", "docker", "--profile", "docker-production"],
        )

        assert result.exit_code == 0


class TestOnboardRun:
    def test_run_non_interactive_missing_password(self, runner_with_app):
        result = runner_with_app.invoke(
            main,
            ["onboard", "run", "--non-interactive"],
        )

        assert result.exit_code != 0

    def test_run_dry_run(self, runner_with_app, tmp_path):
        pw_file = _write_password_file(tmp_path)

        with patch("app.onboarding.steps._ALL_STEPS", _make_passing_steps()):
            result = runner_with_app.invoke(
                main,
                [
                    "onboard",
                    "run",
                    "--dry-run",
                    "--non-interactive",
                    "--admin-password-file",
                    pw_file,
                ],
            )

        assert result.exit_code == 0

    def test_run_dry_run_json_output(self, runner_with_app, tmp_path):
        pw_file = _write_password_file(tmp_path)

        with patch("app.onboarding.steps._ALL_STEPS", _make_passing_steps()):
            result = runner_with_app.invoke(
                main,
                [
                    "--json",
                    "onboard",
                    "run",
                    "--dry-run",
                    "--non-interactive",
                    "--admin-password-file",
                    pw_file,
                ],
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True

    def test_run_with_password_file(self, runner_with_app, tmp_path):
        pw_file = _write_password_file(tmp_path)

        with patch("app.onboarding.steps._ALL_STEPS", _make_passing_steps()):
            result = runner_with_app.invoke(
                main,
                [
                    "onboard",
                    "run",
                    "--dry-run",
                    "--non-interactive",
                    "--admin-password-file",
                    pw_file,
                ],
            )

        assert result.exit_code == 0

    def test_run_with_options(self, runner_with_app, tmp_path):
        pw_file = _write_password_file(tmp_path)

        with patch("app.onboarding.steps._ALL_STEPS", _make_passing_steps()):
            result = runner_with_app.invoke(
                main,
                [
                    "onboard",
                    "run",
                    "--dry-run",
                    "--non-interactive",
                    "--admin-password-file",
                    pw_file,
                    "--mode",
                    "native",
                    "--profile",
                    "development",
                    "--site-url",
                    "http://localhost:5000",
                    "--admin-username",
                    "testadmin",
                ],
            )

        assert result.exit_code == 0

    def test_run_invalid_password_file_returns_error(self, runner_with_app):
        result = runner_with_app.invoke(
            main,
            [
                "onboard",
                "run",
                "--non-interactive",
                "--admin-password-file",
                "/nonexistent/file.txt",
            ],
        )

        assert result.exit_code != 0
