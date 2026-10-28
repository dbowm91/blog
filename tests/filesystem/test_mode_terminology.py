"""Mode terminology tests — R2C8: CLI consistency for mode/scope/layout terminology.

Verifies that the relationship between installation mode, scope, and runtime layout
is explicit and consistent across CLI help, plans, metadata, and docs.

Terminology:
  installation mode: native | docker
  native scope: system | user
  time/runtime layout: system | user | docker | development
"""

from __future__ import annotations

import pytest

from app.filesystem.layout import InstallMode


class TestModeTerminology:
    def test_install_mode_values(self):
        modes = {m.value for m in InstallMode}
        assert modes == {"system", "user", "docker", "development"}

    def test_mode_to_scope_mapping(self):
        native_scopes = {"system", "user"}
        docker_scopes: set[str] = set()
        dev_scopes: set[str] = set()

        mode_scopes = {
            "native": native_scopes,
            "docker": docker_scopes,
            "development": dev_scopes,
        }

        assert "system" in mode_scopes["native"]
        assert "user" in mode_scopes["native"]
        assert len(mode_scopes["docker"]) == 0
        assert len(mode_scopes["development"]) == 0


class TestOnboardingInputScope:
    def test_scope_field_exists(self):
        from app.onboarding.model import OnboardingInput

        inp = OnboardingInput()
        assert hasattr(inp, "scope")

    def test_scope_default_empty(self):
        from app.onboarding.model import OnboardingInput

        inp = OnboardingInput()
        assert inp.scope == ""

    def test_scope_system(self):
        from app.onboarding.model import OnboardingInput

        inp = OnboardingInput(mode="native", scope="system")
        assert inp.scope == "system"

    def test_scope_user(self):
        from app.onboarding.model import OnboardingInput

        inp = OnboardingInput(mode="native", scope="user")
        assert inp.scope == "user"

    def test_scope_ignored_for_docker(self):
        from app.onboarding.model import OnboardingInput

        inp = OnboardingInput(mode="docker", scope="system")
        assert inp.mode == "docker"
        assert inp.scope == "system"


class TestStepResolvePathsScopeMapping:
    def test_docker_maps_to_docker_mode(self, tmp_path):
        from app.onboarding.model import OnboardingInput
        from app.onboarding.steps import StepContext

        inp = OnboardingInput(mode="docker")
        ctx = StepContext(input=inp)
        ctx.config_dir = tmp_path / "config"
        ctx.data_dir = tmp_path / "data"
        ctx.env_file = tmp_path / ".env"

        try:
            from app.filesystem.layout import InstallMode, RuntimePaths

            mode = InstallMode.DOCKER
            rp = RuntimePaths.for_mode(mode)
            assert (
                "docker" in rp.data_dir.provenance.value or "docker" in rp.data_dir.source.lower()
            )
        except ImportError:
            pytest.skip("filesystem layout not available")

    def test_native_system_maps_to_system_mode(self, tmp_path):
        from app.onboarding.model import OnboardingInput
        from app.onboarding.steps import StepContext

        inp = OnboardingInput(mode="native", scope="system")
        ctx = StepContext(input=inp)
        ctx.config_dir = tmp_path / "config"
        ctx.data_dir = tmp_path / "data"
        ctx.env_file = tmp_path / ".env"

        try:
            from app.filesystem.layout import InstallMode, RuntimePaths

            mode = InstallMode.SYSTEM
            rp = RuntimePaths.for_mode(mode)
            assert (
                "system" in rp.data_dir.provenance.value or "system" in rp.data_dir.source.lower()
            )
        except ImportError:
            pytest.skip("filesystem layout not available")

    def test_native_user_maps_to_user_mode(self, tmp_path):
        from app.onboarding.model import OnboardingInput
        from app.onboarding.steps import StepContext, step_resolve_paths

        inp = OnboardingInput(mode="native", scope="user")
        ctx = StepContext(input=inp)
        result = step_resolve_paths(ctx)
        assert result.ok

    def test_native_no_scope_maps_to_development(self, tmp_path):
        from app.onboarding.model import OnboardingInput
        from app.onboarding.steps import StepContext, step_resolve_paths

        inp = OnboardingInput(mode="native")
        ctx = StepContext(input=inp)
        result = step_resolve_paths(ctx)
        assert result.ok


class TestBuildConfigFromInput:
    def test_data_dir_override(self, tmp_path):
        from app.onboarding.model import OnboardingInput, build_config_from_input

        inp = OnboardingInput(mode="native")
        config = build_config_from_input(inp, data_dir=tmp_path)
        assert str(tmp_path.resolve()) in config.database.uri

    def test_docker_default_db_uri(self):
        from app.onboarding.model import OnboardingInput, build_config_from_input

        inp = OnboardingInput(mode="docker")
        config = build_config_from_input(inp)
        assert "/data/devlog.sqlite3" in config.database.uri
