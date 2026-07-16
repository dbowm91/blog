from __future__ import annotations

import json

from app.onboarding.model import OnboardingInput
from app.onboarding.planner import (
    PlannedAction,
    format_plan_json,
    format_plan_text,
    generate_plan,
)
from app.onboarding.state import InstallState, InstallationInfo


class TestGeneratePlanFresh:
    def test_all_create_actions(self, tmp_path):
        inp = OnboardingInput(mode="native", profile="development", admin_password="pw")
        state = InstallationInfo(
            state=InstallState.FRESH,
            config_exists=False,
            env_exists=False,
            database_exists=False,
            metadata_exists=False,
            admin_exists=False,
        )

        plan = generate_plan(inp, state)

        actions = [a.action for a in plan]
        assert "create" in actions

        targets = {a.target for a in plan}
        assert "admin user" in targets

    def test_includes_config_creation(self, tmp_path):
        inp = OnboardingInput(mode="native", profile="development", admin_password="pw")
        state = InstallationInfo(
            state=InstallState.FRESH,
            config_exists=False,
            env_exists=False,
            database_exists=False,
            metadata_exists=False,
            admin_exists=False,
        )

        plan = generate_plan(inp, state)

        config_actions = [a for a in plan if "config.toml" in a.target]
        assert len(config_actions) == 1
        assert config_actions[0].action == "create"

    def test_includes_env_creation(self, tmp_path):
        inp = OnboardingInput(mode="native", profile="development", admin_password="pw")
        state = InstallationInfo(
            state=InstallState.FRESH,
            config_exists=False,
            env_exists=False,
            database_exists=False,
            metadata_exists=False,
            admin_exists=False,
        )

        plan = generate_plan(inp, state)

        env_actions = [a for a in plan if ".env" in a.target]
        assert len(env_actions) == 1
        assert env_actions[0].action == "create"

    def test_includes_database_migration(self, tmp_path):
        inp = OnboardingInput(mode="native", profile="development", admin_password="pw")
        state = InstallationInfo(
            state=InstallState.FRESH,
            config_exists=False,
            env_exists=False,
            database_exists=False,
            metadata_exists=False,
            admin_exists=False,
        )

        plan = generate_plan(inp, state)

        migration_actions = [a for a in plan if "migration" in a.target]
        assert len(migration_actions) == 1

    def test_includes_metadata_creation(self, tmp_path):
        inp = OnboardingInput(mode="native", profile="development", admin_password="pw")
        state = InstallationInfo(
            state=InstallState.FRESH,
            config_exists=False,
            env_exists=False,
            database_exists=False,
            metadata_exists=False,
            admin_exists=False,
        )

        plan = generate_plan(inp, state)

        metadata_actions = [a for a in plan if "metadata" in a.target]
        assert len(metadata_actions) == 1

    def test_includes_admin_creation(self, tmp_path):
        inp = OnboardingInput(mode="native", profile="development", admin_password="pw")
        state = InstallationInfo(
            state=InstallState.FRESH,
            config_exists=False,
            env_exists=False,
            database_exists=False,
            metadata_exists=False,
            admin_exists=False,
        )

        plan = generate_plan(inp, state)

        admin_actions = [a for a in plan if a.target == "admin user"]
        assert len(admin_actions) == 1
        assert admin_actions[0].action == "create"


class TestGeneratePlanComplete:
    def test_preserve_config_when_complete(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[app]\ntitle='T'")

        inp = OnboardingInput(mode="native", profile="development", admin_password="pw")
        state = InstallationInfo(
            state=InstallState.COMPLETE,
            config_exists=True,
            env_exists=True,
            database_exists=True,
            metadata_exists=True,
            admin_exists=True,
            config_path=config_file,
        )

        plan = generate_plan(inp, state)

        config_actions = [a for a in plan if "config.toml" in a.target]
        assert config_actions[0].action == "preserve"

    def test_preserve_admin_when_exists(self, tmp_path):
        inp = OnboardingInput(mode="native", profile="development", admin_password="pw")
        state = InstallationInfo(
            state=InstallState.COMPLETE,
            config_exists=True,
            env_exists=True,
            database_exists=True,
            metadata_exists=True,
            admin_exists=True,
        )

        plan = generate_plan(inp, state)

        admin_actions = [a for a in plan if a.target == "admin user"]
        assert admin_actions[0].action == "preserve"

    def test_update_env_when_exists(self, tmp_path):
        inp = OnboardingInput(mode="native", profile="development", admin_password="pw")
        state = InstallationInfo(
            state=InstallState.FRESH,
            config_exists=False,
            env_exists=True,
            database_exists=False,
            metadata_exists=False,
            admin_exists=False,
        )

        plan = generate_plan(inp, state)

        env_actions = [a for a in plan if ".env" in a.target]
        assert env_actions[0].action == "update"

    def test_update_config_when_partial(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[app]\ntitle='T'")

        inp = OnboardingInput(mode="native", profile="development", admin_password="pw")
        state = InstallationInfo(
            state=InstallState.PARTIAL,
            config_exists=True,
            env_exists=False,
            database_exists=False,
            metadata_exists=False,
            admin_exists=False,
            config_path=config_file,
        )

        plan = generate_plan(inp, state)

        config_actions = [a for a in plan if "config.toml" in a.target]
        assert config_actions[0].action == "update"


class TestFormatPlanText:
    def test_contains_header(self):
        plan = [PlannedAction(action="create", target="config.toml", details="New file")]

        text = format_plan_text(plan)

        assert "Onboarding Plan" in text
        assert "=" * 40 in text

    def test_contains_action_icons(self):
        plan = [
            PlannedAction(action="create", target="a", details="d1"),
            PlannedAction(action="update", target="b", details="d2"),
            PlannedAction(action="preserve", target="c", details="d3"),
        ]

        text = format_plan_text(plan)

        assert "[+]" in text
        assert "[~]" in text
        assert "[=]" in text

    def test_contains_total_count(self):
        plan = [
            PlannedAction(action="create", target="a"),
            PlannedAction(action="create", target="b"),
        ]

        text = format_plan_text(plan)

        assert "Total: 2 action(s)" in text

    def test_contains_details(self):
        plan = [PlannedAction(action="create", target="x", details="some detail")]

        text = format_plan_text(plan)

        assert "some detail" in text


class TestFormatPlanJson:
    def test_valid_json(self):
        plan = [PlannedAction(action="create", target="config.toml", details="New file")]

        output = format_plan_json(plan)
        parsed = json.loads(output)

        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["action"] == "create"
        assert parsed[0]["target"] == "config.toml"

    def test_multiple_actions(self):
        plan = [
            PlannedAction(action="create", target="a"),
            PlannedAction(action="update", target="b"),
        ]

        output = format_plan_json(plan)
        parsed = json.loads(output)

        assert len(parsed) == 2

    def test_empty_plan(self):
        output = format_plan_json([])
        parsed = json.loads(output)

        assert parsed == []
