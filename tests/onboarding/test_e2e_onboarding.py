"""End-to-end onboarding tests — full pipeline from clean state.

Tests the complete onboarding flow including config writes, env creation,
metadata persistence, and compensation on failure. Database-dependent steps
(migrations, admin creation, readiness check) are mocked since the test
database has a different schema than production.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import patch


from app.onboarding.metadata import OnboardingMetadata, load_metadata, save_metadata
from app.onboarding.model import OnboardingInput
from app.onboarding.steps import StepResult, _ALL_STEPS, run_steps


def _make_passing_steps(config_dir: Path | None = None, data_dir: Path | None = None):
    steps = list(_ALL_STEPS)
    for name in (
        "step_validate_proposal",
        "step_verify_assets",
        "step_readiness_check",
        "step_run_migrations",
        "step_create_administrator",
    ):
        idx = next(i for i, s in enumerate(steps) if s.__name__ == name)
        steps[idx] = lambda ctx: StepResult(ok=True, message="noop")

    if config_dir or data_dir:
        path_idx = next(i for i, s in enumerate(steps) if s.__name__ == "step_resolve_paths")

        def fixed_resolve_paths(ctx, _config_dir=config_dir, _data_dir=data_dir):
            if _config_dir:
                ctx.config_dir = _config_dir
            if _data_dir:
                ctx.data_dir = _data_dir
            ctx.config_dir.mkdir(parents=True, exist_ok=True)
            ctx.data_dir.mkdir(parents=True, exist_ok=True)
            return StepResult(
                ok=True,
                message=f"Config: {ctx.config_dir}, Data: {ctx.data_dir}",
                details={"config_dir": str(ctx.config_dir), "data_dir": str(ctx.data_dir)},
            )

        steps[path_idx] = fixed_resolve_paths

    return steps


class TestE2EFreshInstall:
    def test_fresh_install_creates_config_and_env(self, tmp_path):
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        config_dir.mkdir()
        data_dir.mkdir()

        steps = _make_passing_steps(config_dir, data_dir)
        inp = OnboardingInput(
            admin_password="SecurePass1!",
            non_interactive=True,
            mode="native",
            profile="development",
            site_title="Test Blog",
            base_url="http://localhost:5000",
        )

        with patch("app.onboarding.steps._ALL_STEPS", steps):
            results = run_steps(inp, config_path=config_dir / "config.toml", data_path=data_dir)

        assert all(r.ok for r in results), f"Failed: {[r.message for r in results if not r.ok]}"

        config_file = config_dir / "config.toml"
        assert config_file.exists()
        content = config_file.read_text()
        assert "Test Blog" in content

        env_file = Path(".env")
        assert env_file.exists()
        env_content = env_file.read_text()
        assert "SECRET_KEY=" in env_content
        assert "ADMIN_PASSWORD=" in env_content

    def test_fresh_install_creates_metadata(self, tmp_path):
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        config_dir.mkdir()
        data_dir.mkdir()

        steps = _make_passing_steps(config_dir, data_dir)
        inp = OnboardingInput(
            admin_password="SecurePass1!",
            non_interactive=True,
        )

        with patch("app.onboarding.steps._ALL_STEPS", steps):
            results = run_steps(inp, config_path=config_dir / "config.toml", data_path=data_dir)

        assert all(r.ok for r in results)

        meta = load_metadata(data_dir)
        assert meta is not None
        assert meta.mode == "native"
        assert meta.profile == "development"
        assert meta.admin_username == "admin"
        assert meta.completed_at != ""

    def test_fresh_install_env_permissions(self, tmp_path):
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        config_dir.mkdir()
        data_dir.mkdir()

        steps = _make_passing_steps(config_dir, data_dir)
        inp = OnboardingInput(admin_password="SecurePass1!", non_interactive=True)

        with patch("app.onboarding.steps._ALL_STEPS", steps):
            results = run_steps(inp, config_path=config_dir / "config.toml", data_path=data_dir)

        assert all(r.ok for r in results)

        env_file = Path(".env")
        assert env_file.exists()
        mode = stat.S_IMODE(os.stat(env_file).st_mode)
        assert mode == 0o600

    def test_fresh_install_idempotent_rerun(self, tmp_path):
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        config_dir.mkdir()
        data_dir.mkdir()

        steps = _make_passing_steps(config_dir, data_dir)
        inp = OnboardingInput(admin_password="SecurePass1!", non_interactive=True)

        with patch("app.onboarding.steps._ALL_STEPS", steps):
            results1 = run_steps(inp, config_path=config_dir / "config.toml", data_path=data_dir)
            results2 = run_steps(inp, config_path=config_dir / "config.toml", data_path=data_dir)

        assert all(r.ok for r in results1)
        assert all(r.ok for r in results2)

    def test_fresh_install_docker_mode(self, tmp_path):
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        config_dir.mkdir()
        data_dir.mkdir()

        steps = _make_passing_steps(config_dir, data_dir)
        inp = OnboardingInput(
            admin_password="SecurePass1!",
            non_interactive=True,
            mode="docker",
            profile="docker-production",
        )

        with patch("app.onboarding.steps._ALL_STEPS", steps):
            results = run_steps(inp, config_path=config_dir / "config.toml", data_path=data_dir)

        assert all(r.ok for r in results)

        config_file = config_dir / "config.toml"
        assert config_file.exists()
        content = config_file.read_text()
        assert "0.0.0.0" in content


class TestE2EResume:
    def test_resume_after_config_write(self, tmp_path):
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        config_dir.mkdir()
        data_dir.mkdir()

        steps = _make_passing_steps(config_dir, data_dir)
        inp = OnboardingInput(admin_password="SecurePass1!", non_interactive=True)

        with patch("app.onboarding.steps._ALL_STEPS", steps):
            results = run_steps(inp, config_path=config_dir / "config.toml", data_path=data_dir)

        assert all(r.ok for r in results)

        meta = load_metadata(data_dir)
        assert meta is not None
        assert meta.last_completed_step >= 0

    def test_resume_no_metadata_returns_error(self, tmp_path):
        from app.services.operations.onboard import resume_onboarding

        result = resume_onboarding(data_path=tmp_path)
        assert result.ok is False
        assert result.code == "onboard.resume.no_metadata"

    def test_resume_already_complete(self, tmp_path):
        from app.services.operations.onboard import resume_onboarding

        meta = OnboardingMetadata(
            version=1,
            mode="native",
            profile="development",
            package_version="",
            completed_at="2026-01-01T00:00:00",
            config_path="config.toml",
            data_path=str(tmp_path),
            managed_paths=[],
            admin_username="admin",
            last_completed_step=16,
        )
        save_metadata(tmp_path, meta)

        result = resume_onboarding(data_path=tmp_path)
        assert result.ok is True
        assert result.completed is True


class TestE2ECompensation:
    def test_failure_compensates_created_files(self, tmp_path):
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        config_dir.mkdir()
        data_dir.mkdir()

        steps = list(_ALL_STEPS)

        def fixed_resolve_paths(ctx):
            ctx.config_dir = config_dir
            ctx.data_dir = data_dir
            ctx.config_dir.mkdir(parents=True, exist_ok=True)
            ctx.data_dir.mkdir(parents=True, exist_ok=True)
            return StepResult(
                ok=True,
                message=f"Config: {ctx.config_dir}, Data: {ctx.data_dir}",
                details={"config_dir": str(ctx.config_dir), "data_dir": str(ctx.data_dir)},
            )

        path_idx = next(i for i, s in enumerate(steps) if s.__name__ == "step_resolve_paths")
        steps[path_idx] = fixed_resolve_paths

        config_idx = next(i for i, s in enumerate(steps) if s.__name__ == "step_write_config")

        def failing_write(ctx):
            config_path = ctx.config_dir / "config.toml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("bad config\n")
            ctx.created_files.append(config_path)
            return StepResult(ok=False, message="Simulated config write failure")

        steps[config_idx] = failing_write
        for name in ("step_validate_proposal", "step_verify_assets", "step_readiness_check"):
            idx = next(i for i, s in enumerate(steps) if s.__name__ == name)
            steps[idx] = lambda ctx: StepResult(ok=True, message="noop")

        inp = OnboardingInput(admin_password="SecurePass1!", non_interactive=True)

        with patch("app.onboarding.steps._ALL_STEPS", steps):
            results = run_steps(inp, config_path=config_dir / "config.toml", data_path=data_dir)

        failed = [r for r in results if not r.ok]
        assert len(failed) == 1
        assert "Simulated config write failure" in failed[0].message

        config_file = config_dir / "config.toml"
        assert not config_file.exists()

    def test_metadata_records_failure_point(self, tmp_path):
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        config_dir.mkdir()
        data_dir.mkdir()

        steps = list(_ALL_STEPS)

        def fixed_resolve_paths(ctx):
            ctx.config_dir = config_dir
            ctx.data_dir = data_dir
            ctx.config_dir.mkdir(parents=True, exist_ok=True)
            ctx.data_dir.mkdir(parents=True, exist_ok=True)
            return StepResult(
                ok=True,
                message=f"Config: {ctx.config_dir}, Data: {ctx.data_dir}",
                details={"config_dir": str(ctx.config_dir), "data_dir": str(ctx.data_dir)},
            )

        path_idx = next(i for i, s in enumerate(steps) if s.__name__ == "step_resolve_paths")
        steps[path_idx] = fixed_resolve_paths

        config_idx = next(i for i, s in enumerate(steps) if s.__name__ == "step_write_config")

        def failing_write(ctx):
            config_path = ctx.config_dir / "config.toml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("bad config\n")
            ctx.created_files.append(config_path)
            return StepResult(ok=False, message="Simulated config write failure")

        steps[config_idx] = failing_write
        for name in ("step_validate_proposal", "step_verify_assets", "step_readiness_check"):
            idx = next(i for i, s in enumerate(steps) if s.__name__ == name)
            steps[idx] = lambda ctx: StepResult(ok=True, message="noop")

        inp = OnboardingInput(admin_password="SecurePass1!", non_interactive=True)

        with patch("app.onboarding.steps._ALL_STEPS", steps):
            run_steps(inp, config_path=config_dir / "config.toml", data_path=data_dir)

        meta = load_metadata(data_dir)
        assert meta is not None
        assert meta.stopped_at == "step_write_config"
        assert meta.stopped_reason == "Simulated config write failure"
        assert meta.completed_at == ""
