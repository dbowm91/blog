"""Failure injection tests for onboarding pipeline.

Tests compensation/rollback behavior, interrupted runs, and error scenarios.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


from app.onboarding.metadata import OnboardingMetadata, load_metadata, save_metadata
from app.onboarding.model import OnboardingInput
from app.onboarding.steps import (
    StepContext,
    StepResult,
    _ALL_STEPS,
    _compensate,
    _save_progress,
    run_steps,
)


def _make_passing_steps():
    steps = list(_ALL_STEPS)
    for name in ("step_validate_proposal", "step_verify_assets", "step_readiness_check"):
        idx = next(i for i, s in enumerate(steps) if s.__name__ == name)
        steps[idx] = lambda ctx: StepResult(ok=True, message="noop")
    return steps


def _step_that_fails_after_writing(ctx: StepContext) -> StepResult:
    config_path = ctx.config_dir / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("failed = true\n")
    ctx.created_files.append(config_path)
    return StepResult(ok=False, message="Simulated write failure")


def _step_that_fails_without_tracking(ctx: StepContext) -> StepResult:
    config_path = ctx.config_dir / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("orphaned = true\n")
    return StepResult(ok=False, message="Failure without tracking")


class TestCompensation:
    def test_compensate_removes_tracked_files(self, tmp_path):
        ctx = StepContext(input=OnboardingInput(), config_dir=tmp_path, data_dir=tmp_path / "data")
        f = tmp_path / "test.txt"
        f.write_text("hello")
        ctx.created_files.append(f)

        _compensate(ctx)

        assert not f.exists()

    def test_compensate_removes_empty_dirs(self, tmp_path):
        ctx = StepContext(input=OnboardingInput(), config_dir=tmp_path, data_dir=tmp_path / "data")
        d = tmp_path / "empty_dir"
        d.mkdir()
        ctx.created_dirs.append(d)

        _compensate(ctx)

        assert not d.exists()

    def test_compensate_preserves_nonempty_dirs(self, tmp_path):
        ctx = StepContext(input=OnboardingInput(), config_dir=tmp_path, data_dir=tmp_path / "data")
        d = tmp_path / "nonempty_dir"
        d.mkdir()
        (d / "file.txt").write_text("content")
        ctx.created_dirs.append(d)

        _compensate(ctx)

        assert d.exists()
        assert (d / "file.txt").exists()

    def test_compensate_handles_missing_files(self, tmp_path):
        ctx = StepContext(input=OnboardingInput(), config_dir=tmp_path, data_dir=tmp_path / "data")
        ctx.created_files.append(tmp_path / "nonexistent.txt")

        _compensate(ctx)

    def test_compensate_removes_in_reverse_order(self, tmp_path):
        ctx = StepContext(input=OnboardingInput(), config_dir=tmp_path, data_dir=tmp_path / "data")
        f1 = tmp_path / "first.txt"
        f2 = tmp_path / "second.txt"
        f1.write_text("first")
        f2.write_text("second")
        ctx.created_files.extend([f1, f2])

        removal_order = []
        original_unlink = Path.unlink

        def tracking_unlink(self, *args, **kwargs):
            removal_order.append(self.name)
            return original_unlink(self, *args, **kwargs)

        with patch.object(Path, "unlink", tracking_unlink):
            _compensate(ctx)

        assert removal_order == ["second.txt", "first.txt"]


class TestStepFailureTracking:
    def test_failed_step_saves_metadata_with_stopped_info(self, tmp_path):
        steps = list(_ALL_STEPS)
        fail_idx = next(i for i, s in enumerate(steps) if s.__name__ == "step_build_config")
        steps[fail_idx] = _step_that_fails_after_writing

        inp = OnboardingInput(
            admin_password="test123",
            non_interactive=True,
            dry_run=True,
        )
        ctx = StepContext(input=inp, config_dir=tmp_path, data_dir=tmp_path / "data", dry_run=True)

        results = []
        for i, step_fn in enumerate(steps):
            ctx.step_index = i
            result = step_fn(ctx)
            results.append(result)
            if not result.ok:
                _save_progress(ctx, i, stopped_at=step_fn.__name__, stopped_reason=result.message)
                break

        assert not results[-1].ok
        assert results[-1].message == "Simulated write failure"

    def test_step_failure_clears_created_files(self, tmp_path):
        steps = _make_passing_steps()
        config_idx = next(i for i, s in enumerate(steps) if s.__name__ == "step_write_config")
        steps[config_idx] = _step_that_fails_after_writing

        inp = OnboardingInput(admin_password="test123", non_interactive=True)
        results = run_steps(inp, config_path=tmp_path / "config.toml", data_path=tmp_path / "data")

        failed = [r for r in results if not r.ok]
        assert len(failed) == 1

    def test_compensation_on_config_write_failure(self, tmp_path):
        config_path = tmp_path / "config.toml"

        def failing_config_step(ctx):
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("bad = true\n")
            ctx.created_files.append(config_path)
            return StepResult(ok=False, message="Config write failed")

        steps = list(_ALL_STEPS)
        config_idx = next(i for i, s in enumerate(steps) if s.__name__ == "step_write_config")
        steps[config_idx] = failing_config_step

        inp = OnboardingInput(admin_password="test123", non_interactive=True)

        def patched_run(input, config_path=None, data_path=None, start_step=0):
            ctx = StepContext(input=input, dry_run=input.dry_run)
            if config_path:
                ctx.config_dir = config_path.parent
            if data_path:
                ctx.data_dir = data_path

            results = []
            for i, step_fn in enumerate(steps):
                if i < start_step:
                    results.append(StepResult(ok=True, message="skipped"))
                    continue
                ctx.step_index = i
                result = step_fn(ctx)
                results.append(result)
                if not result.ok:
                    _compensate(ctx)
                    break
            return results

        with patch("app.onboarding.steps.run_steps", patched_run):
            results = patched_run(inp, config_path=config_path, data_path=tmp_path / "data")

        assert not results[-1].ok
        assert not config_path.exists()


class TestResumeMetadata:
    def test_metadata_tracks_last_completed_step(self, tmp_path):
        meta = OnboardingMetadata(
            version=1,
            mode="native",
            profile="development",
            package_version="",
            completed_at="",
            config_path="config.toml",
            data_path=str(tmp_path),
            managed_paths=[],
            admin_username="admin",
            last_completed_step=5,
            stopped_at="step_write_config",
            stopped_reason="Config write failed",
        )
        save_metadata(tmp_path, meta)

        loaded = load_metadata(tmp_path)
        assert loaded is not None
        assert loaded.last_completed_step == 5
        assert loaded.stopped_at == "step_write_config"
        assert loaded.stopped_reason == "Config write failed"

    def test_metadata_defaults_for_old_format(self, tmp_path):
        meta_file = tmp_path / "onboarding-metadata.json"
        meta_file.write_text(
            '{"version": 1, "mode": "native", "profile": "development", '
            '"package_version": "", "completed_at": "2026-01-01T00:00:00", '
            '"config_path": "config.toml", "data_path": "", "managed_paths": [], '
            '"admin_username": "admin"}'
        )

        loaded = load_metadata(tmp_path)
        assert loaded is not None
        assert loaded.last_completed_step == -1
        assert loaded.stopped_at == ""
        assert loaded.stopped_reason == ""

    def test_resume_no_metadata(self, tmp_path):
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


class TestRunStepsResume:
    def test_start_step_skips_earlier_steps(self, tmp_path):
        executed = []

        def tracking_step(ctx):
            executed.append(ctx.step_index)
            return StepResult(ok=True, message="ok")

        steps = [tracking_step] * 5
        inp = OnboardingInput(admin_password="test123", non_interactive=True, dry_run=True)

        ctx = StepContext(input=inp, dry_run=True)
        results = []
        for i, step_fn in enumerate(steps):
            if i < 2:
                results.append(StepResult(ok=True, message="Skipped"))
                continue
            ctx.step_index = i
            result = step_fn(ctx)
            results.append(result)

        assert len(results) == 5
        assert all(r.ok for r in results)
        assert executed == [2, 3, 4]

    def test_resume_saves_progress_per_step(self, tmp_path):
        executed_steps = []

        def progress_tracking_step(ctx):
            executed_steps.append(ctx.step_index)
            return StepResult(ok=True, message="ok")

        steps = [progress_tracking_step] * 3
        inp = OnboardingInput(admin_password="test123", non_interactive=True, dry_run=True)
        ctx = StepContext(input=inp, dry_run=True, data_dir=tmp_path)

        results = []
        for i, step_fn in enumerate(steps):
            ctx.step_index = i
            result = step_fn(ctx)
            results.append(result)
            if result.ok:
                _save_progress(ctx, i)

        assert executed_steps == [0, 1, 2]


class TestInterruptionRecovery:
    def test_metadata_records_interruption_point(self, tmp_path):
        meta = OnboardingMetadata(
            version=1,
            mode="native",
            profile="development",
            package_version="",
            completed_at="",
            config_path="config.toml",
            data_path=str(tmp_path),
            managed_paths=[],
            admin_username="admin",
            last_completed_step=8,
            stopped_at="step_write_config",
            stopped_reason="Permission denied",
        )
        save_metadata(tmp_path, meta)

        loaded = load_metadata(tmp_path)
        assert loaded.last_completed_step == 8
        assert loaded.stopped_at == "step_write_config"
        assert loaded.stopped_reason == "Permission denied"
        assert loaded.completed_at == ""

    def test_resume_can_start_from_middle(self, tmp_path):
        from app.onboarding.steps import STEP_NAMES

        meta = OnboardingMetadata(
            version=1,
            mode="native",
            profile="development",
            package_version="",
            completed_at="",
            config_path="config.toml",
            data_path=str(tmp_path),
            managed_paths=[],
            admin_username="admin",
            last_completed_step=8,
            stopped_at="step_write_config",
            stopped_reason="Permission denied",
        )
        save_metadata(tmp_path, meta)

        loaded = load_metadata(tmp_path)
        start_step = loaded.last_completed_step + 1
        assert start_step == 9
        assert STEP_NAMES[start_step] == "step_write_env"
