"""Regression tests for the first-run onboarding flow.

Onboarding has to work on a machine that has neither a config file nor a
secret yet, so the validation step must accept the secrets onboarding is
about to write and must not demand a config file that the next step creates.
"""

from __future__ import annotations

from pathlib import Path

from app.onboarding.model import OnboardingInput, build_config_from_input
from app.onboarding.steps import (
    StepContext,
    step_build_config,
    step_create_directories,
    step_resolve_secrets,
    step_validate_proposal,
    step_verify_assets,
)


def _context(tmp_path: Path, **kwargs) -> StepContext:
    inp = OnboardingInput(mode="native", profile="development", **kwargs)
    ctx = StepContext(
        input=inp,
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
        env_file=tmp_path / "config" / ".env",
    )
    ctx.config_dir.mkdir(parents=True, exist_ok=True)
    ctx.data_dir.mkdir(parents=True, exist_ok=True)
    return ctx


class TestValidateProposal:
    def test_passes_without_a_config_file_or_written_secrets(self, tmp_path: Path) -> None:
        ctx = _context(tmp_path, admin_password="a-long-enough-password")
        step_build_config(ctx)
        step_resolve_secrets(ctx)

        result = step_validate_proposal(ctx)

        assert result.ok is True, result.message
        assert "SECRET_KEY is not set" not in result.message
        assert "Config file does not exist" not in result.message

    def test_uses_the_pending_admin_password(self, tmp_path: Path) -> None:
        ctx = _context(tmp_path, admin_password="a-long-enough-password")
        step_build_config(ctx)
        step_resolve_secrets(ctx)

        result = step_validate_proposal(ctx)

        assert result.ok is True, result.message

    def test_still_rejects_a_config_that_is_invalid(self, tmp_path: Path) -> None:
        ctx = _context(tmp_path)
        step_build_config(ctx)
        step_resolve_secrets(ctx)
        ctx.config = ctx.config.__class__(
            version=1,
            server=ctx.config.server.__class__(host="127.0.0.1", port=99999, debug=False),
        )

        result = step_validate_proposal(ctx)

        assert result.ok is False
        assert "Validation failed" in result.message


class TestVerifyAssets:
    def test_finds_the_packaged_assets(self) -> None:
        ctx = StepContext(input=OnboardingInput(mode="native", profile="development"))

        result = step_verify_assets(ctx)

        assert result.details["migrations"] is True
        assert result.details["themes_bundled"] is True
        assert result.details["base_template"] is True

    def test_the_vite_manifest_is_looked_for_under_dot_vite(self) -> None:
        ctx = StepContext(input=OnboardingInput(mode="native", profile="development"))

        result = step_verify_assets(ctx)

        assert "vite_manifest" in result.details


class TestBuildConfig:
    def test_database_uri_points_into_the_data_directory(self, tmp_path: Path) -> None:
        inp = OnboardingInput(mode="native", profile="development")

        config = build_config_from_input(inp, data_dir=tmp_path)

        assert config.database.uri.startswith("sqlite:///")
        assert config.database.uri.endswith("devlog.sqlite3")
        assert str(tmp_path.resolve()) in config.database.uri

    def test_docker_database_uri_uses_the_container_path(self) -> None:
        inp = OnboardingInput(mode="docker", profile="docker-production")

        config = build_config_from_input(inp)

        assert config.database.uri == "sqlite:////data/devlog.sqlite3"


class TestCreateDirectories:
    def _fake_paths(self, tmp_path: Path, mode) -> object:
        from types import SimpleNamespace

        return SimpleNamespace(
            mode=mode,
            log_dir=SimpleNamespace(path=tmp_path / "log"),
            runtime_dir=SimpleNamespace(path=tmp_path / "run"),
        )

    def _system_context(self, tmp_path: Path) -> StepContext:
        from dataclasses import replace

        from app.filesystem.layout import InstallMode

        ctx = _context(tmp_path)
        ctx.runtime_paths = self._fake_paths(tmp_path, InstallMode.DEVELOPMENT)
        ctx.input = replace(ctx.input, backup_dir=str(tmp_path / "backups"))
        return ctx

    def test_creates_the_log_and_runtime_directories(self, tmp_path: Path) -> None:
        """The rendered unit checks both directories before it starts."""
        from app.filesystem.layout import InstallMode

        ctx = self._system_context(tmp_path)
        ctx.runtime_paths = self._fake_paths(tmp_path, InstallMode.DEVELOPMENT)

        result = step_create_directories(ctx)

        assert result.ok is True, result.message
        assert (tmp_path / "log").is_dir()
        assert (tmp_path / "run").is_dir()
        assert (tmp_path / "backups").is_dir()

    def test_warns_when_the_service_account_is_missing(self, tmp_path: Path) -> None:
        """A system install runs as ``devlog``; onboarding cannot create it."""
        from app.filesystem.layout import InstallMode

        ctx = self._system_context(tmp_path)
        ctx.runtime_paths = self._fake_paths(tmp_path, InstallMode.SYSTEM)

        step_create_directories(ctx)

        account_warnings = [w for w in ctx.warnings if "devlog" in w]
        assert account_warnings, ctx.warnings
        assert "useradd" in account_warnings[0]

    def test_a_user_install_does_not_ask_for_a_service_account(self, tmp_path: Path) -> None:
        from app.filesystem.layout import InstallMode

        ctx = self._system_context(tmp_path)
        ctx.runtime_paths = self._fake_paths(tmp_path, InstallMode.USER)

        step_create_directories(ctx)

        assert not [w for w in ctx.warnings if "useradd" in w]
