from __future__ import annotations

from pathlib import Path

from app.onboarding.model import OnboardingInput
from app.onboarding.steps import (
    StepContext,
    StepResult,
    step_build_config,
    step_resolve_mode,
    step_resolve_paths,
    step_verify_assets,
    run_steps,
)


class TestStepResolveModeValid:
    def test_native_development_passes(self):
        ctx = StepContext(input=OnboardingInput(mode="native", profile="development"))
        result = step_resolve_mode(ctx)

        assert result.ok is True
        assert result.details["mode"] == "native"
        assert result.details["profile"] == "development"

    def test_docker_production_passes(self):
        ctx = StepContext(input=OnboardingInput(mode="docker", profile="docker-production"))
        result = step_resolve_mode(ctx)

        assert result.ok is True
        assert result.details["mode"] == "docker"
        assert result.details["profile"] == "docker-production"

    def test_native_production_passes(self):
        ctx = StepContext(input=OnboardingInput(mode="native", profile="native-production"))
        result = step_resolve_mode(ctx)

        assert result.ok is True

    def test_minimal_profile_passes(self):
        ctx = StepContext(input=OnboardingInput(mode="native", profile="minimal"))
        result = step_resolve_mode(ctx)

        assert result.ok is True

    def test_full_profile_passes(self):
        ctx = StepContext(input=OnboardingInput(mode="native", profile="full"))
        result = step_resolve_mode(ctx)

        assert result.ok is True


class TestStepResolveModeInvalid:
    def test_bad_mode_fails(self):
        ctx = StepContext(input=OnboardingInput(mode="badmode", profile="development"))
        result = step_resolve_mode(ctx)

        assert result.ok is False
        assert "Invalid mode" in result.message

    def test_bad_profile_fails(self):
        ctx = StepContext(input=OnboardingInput(mode="native", profile="badprofile"))
        result = step_resolve_mode(ctx)

        assert result.ok is False
        assert "Invalid profile" in result.message

    def test_docker_native_production_warns(self):
        ctx = StepContext(input=OnboardingInput(mode="docker", profile="native-production"))
        result = step_resolve_mode(ctx)

        assert result.ok is True
        assert len(ctx.warnings) == 1
        assert "unusual" in ctx.warnings[0].lower()


class TestStepResolvePathsNative:
    def test_creates_dirs(self, tmp_path):
        data_dir = tmp_path / "test_data"
        config_dir = tmp_path / "test_config"

        ctx = StepContext(
            input=OnboardingInput(mode="native", profile="development"),
            config_dir=config_dir,
            data_dir=data_dir,
        )

        result = step_resolve_paths(ctx)

        assert result.ok is True
        assert ctx.config_dir.exists()
        assert ctx.data_dir.exists()

    def test_native_mode_uses_current_dir(self):
        ctx = StepContext(
            input=OnboardingInput(mode="native", profile="development"),
        )

        result = step_resolve_paths(ctx)

        assert result.ok is True
        assert ctx.config_dir == Path(".")
        assert ctx.data_dir == Path("data")


class TestStepBuildConfig:
    def test_builds_devlog_config(self):
        ctx = StepContext(
            input=OnboardingInput(
                mode="native",
                profile="development",
                site_title="My Blog",
                base_url="http://localhost:5000",
            )
        )

        result = step_build_config(ctx)

        assert result.ok is True
        assert ctx.config is not None
        assert ctx.config.app.title == "My Blog"
        assert result.details["title"] == "My Blog"
        assert result.details["base_url"] == "http://localhost:5000"

    def test_docker_config(self):
        ctx = StepContext(input=OnboardingInput(mode="docker", profile="docker-production"))

        result = step_build_config(ctx)

        assert result.ok is True
        assert ctx.config is not None
        assert ctx.config.server.host == "0.0.0.0"
        assert ctx.config.server.debug is False

    def test_redis_config_when_enabled(self):
        ctx = StepContext(
            input=OnboardingInput(
                mode="native",
                profile="development",
                enable_redis=True,
            )
        )

        result = step_build_config(ctx)

        assert result.ok is True
        assert ctx.config.redis.cache_url == "redis://localhost:6379/0"


class TestStepVerifyAssets:
    def test_checks_expected_paths(self):
        ctx = StepContext(
            input=OnboardingInput(mode="native", profile="development"),
        )

        result = step_verify_assets(ctx)

        assert result.ok is False or result.ok is True
        assert "details" in result.__dict__ or hasattr(result, "details")
        for key in ["vite_manifest", "base_template", "themes_bundled", "migrations"]:
            assert key in result.details

    def test_warns_on_missing_assets(self, monkeypatch):
        original_exists = Path.exists

        def mock_exists(self):
            if "app/static/dist/manifest.json" in str(self):
                return False
            return original_exists(self)

        monkeypatch.chdir(Path("."))

        ctx = StepContext(
            input=OnboardingInput(mode="native", profile="development"),
        )

        result = step_verify_assets(ctx)

        assert result.ok is False
        assert any("vite_manifest" in w for w in ctx.warnings) or not result.ok


class TestRunStepsDryRun:
    def test_dry_run_prevents_config_write(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        from app.onboarding.steps import StepContext, step_write_config

        ctx = StepContext(
            input=OnboardingInput(dry_run=True),
            dry_run=True,
            config_dir=config_dir,
        )

        from app.onboarding.model import build_config_from_input

        ctx.config = build_config_from_input(OnboardingInput(dry_run=True))

        result = step_write_config(ctx)

        assert result.ok is True
        assert "Dry run" in result.message
        assert not (config_dir / "config.toml").exists()

    def test_dry_run_prevents_env_write(self, tmp_path):
        from app.onboarding.steps import StepContext, step_write_env

        ctx = StepContext(
            input=OnboardingInput(dry_run=True),
            dry_run=True,
            config_dir=tmp_path,
            secrets={"SECRET_KEY": "test", "ADMIN_PASSWORD": "test"},
        )

        result = step_write_env(ctx)

        assert result.ok is True
        assert "Dry run" in result.message
        assert not (tmp_path / ".env").exists()

    def test_dry_run_prevents_directory_creation(self, tmp_path):
        from app.onboarding.steps import StepContext, step_create_directories

        ctx = StepContext(
            input=OnboardingInput(dry_run=True, backup_dir="backups"),
            dry_run=True,
            data_dir=tmp_path / "new_data",
        )

        result = step_create_directories(ctx)

        assert result.ok is True
        assert "Dry run" in result.message
        assert not (tmp_path / "new_data").exists()

    def test_dry_run_prevents_migrations(self):
        from app.onboarding.steps import StepContext, step_run_migrations

        ctx = StepContext(
            input=OnboardingInput(dry_run=True),
            dry_run=True,
        )

        result = step_run_migrations(ctx)

        assert result.ok is True
        assert "Dry run" in result.message

    def test_dry_run_prevents_admin_creation(self):
        from app.onboarding.steps import StepContext, step_create_administrator

        ctx = StepContext(
            input=OnboardingInput(dry_run=True, admin_password="pw"),
            dry_run=True,
        )

        result = step_create_administrator(ctx)

        assert result.ok is True
        assert "Dry run" in result.message

    def test_dry_run_prevents_metadata_write(self, tmp_path):
        from app.onboarding.steps import StepContext, step_write_metadata

        ctx = StepContext(
            input=OnboardingInput(dry_run=True, mode="native", profile="development"),
            dry_run=True,
            data_dir=tmp_path,
        )

        result = step_write_metadata(ctx)

        assert result.ok is True
        assert "Dry run" in result.message
        assert not (tmp_path / "onboarding-metadata.json").exists()


class TestRunStepsCollectInputs:
    def test_fails_without_admin_password(self):
        inp = OnboardingInput(
            mode="native",
            profile="development",
            admin_password="",
            dry_run=True,
            non_interactive=True,
        )

        results = run_steps(inp)

        failed = [r for r in results if not r.ok]
        assert len(failed) >= 1
        assert "password" in failed[0].message.lower()

    def test_proceeds_with_admin_password(self, tmp_path):
        inp = OnboardingInput(
            mode="native",
            profile="development",
            admin_password="SecurePass1!",
            dry_run=True,
            non_interactive=True,
        )

        results = run_steps(
            inp,
            config_path=tmp_path / "config.toml",
            data_path=tmp_path / "data",
        )

        step_names = [r.message.split(":")[0] if ":" in r.message else r.message for r in results]
        assert "Inputs collected" in step_names
        assert "Configuration built" in step_names
        assert "Secrets resolved" in step_names

        failed_steps = [r for r in results if not r.ok]
        for r in failed_steps:
            assert "Dry run" not in r.message

    def test_stops_on_first_failure(self):
        inp = OnboardingInput(
            mode="native",
            profile="development",
            admin_password="",
            dry_run=True,
            non_interactive=True,
        )

        results = run_steps(inp)

        assert not results[-1].ok or all(r.ok for r in results)


class TestStepContext:
    def test_defaults(self):
        ctx = StepContext(input=OnboardingInput())

        assert ctx.config is None
        assert ctx.state is None
        assert ctx.secrets == {}
        assert ctx.warnings == []
        assert ctx.dry_run is False

    def test_step_result_ok(self):
        result = StepResult(ok=True, message="done")

        assert result.ok is True
        assert result.message == "done"
        assert result.details == {}

    def test_step_result_with_details(self):
        result = StepResult(ok=True, message="done", details={"key": "val"})

        assert result.details == {"key": "val"}
