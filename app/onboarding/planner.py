from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.onboarding.model import OnboardingInput
from app.onboarding.state import InstallState, InstallationInfo


@dataclass(frozen=True)
class PlannedAction:
    action: str
    target: str
    details: str = ""


def generate_plan(inp: OnboardingInput, state: InstallationInfo) -> list[PlannedAction]:
    actions: list[PlannedAction] = []

    config_path = state.config_path or Path("config.toml")
    env_path = Path(".env")

    if state.state == InstallState.COMPLETE:
        actions.append(
            PlannedAction(
                action="preserve",
                target=str(config_path),
                details="Existing config will be preserved",
            )
        )
    elif state.config_exists:
        actions.append(
            PlannedAction(
                action="update",
                target=str(config_path),
                details="Existing config will be overwritten (backup created)",
            )
        )
    else:
        actions.append(
            PlannedAction(
                action="create",
                target=str(config_path),
                details="New config file",
            )
        )

    if state.env_exists:
        actions.append(
            PlannedAction(
                action="update",
                target=str(env_path),
                details="Existing .env will be updated (backup created)",
            )
        )
    else:
        actions.append(
            PlannedAction(
                action="create",
                target=str(env_path),
                details="New .env file with secrets (mode 0600)",
            )
        )

    data_dir_target = state.data_path or Path("data")
    if data_dir_target.exists():
        actions.append(
            PlannedAction(
                action="preserve",
                target=str(data_dir_target),
                details="Existing data directory",
            )
        )
    else:
        actions.append(
            PlannedAction(
                action="create",
                target=str(data_dir_target),
                details="Data directory for database and backups",
            )
        )

    backup_dir = Path(inp.backup_dir)
    if not backup_dir.exists():
        actions.append(
            PlannedAction(
                action="create",
                target=str(backup_dir),
                details="Backup directory",
            )
        )

    if not state.admin_exists:
        actions.append(
            PlannedAction(
                action="create",
                target="admin user",
                details=f"Create admin user '{inp.admin_username}'",
            )
        )
    else:
        actions.append(
            PlannedAction(
                action="preserve",
                target="admin user",
                details=f"Admin user '{inp.admin_username}' already exists",
            )
        )

    actions.append(
        PlannedAction(
            action="create",
            target="database migrations",
            details="Run flask db upgrade",
        )
    )

    actions.append(
        PlannedAction(
            action="create",
            target="completion metadata",
            details="Write onboarding-metadata.json",
        )
    )

    return actions


def format_plan_text(plan: list[PlannedAction]) -> str:
    lines: list[str] = []
    lines.append("Onboarding Plan")
    lines.append("=" * 40)

    action_icons = {
        "create": "+",
        "update": "~",
        "preserve": "=",
        "skip": "-",
        "conflict": "!",
    }

    for item in plan:
        icon = action_icons.get(item.action, "?")
        lines.append(f"  [{icon}] {item.action.upper():>8}  {item.target}")
        if item.details:
            lines.append(f"           {item.details}")

    lines.append("")
    lines.append(f"Total: {len(plan)} action(s)")
    return "\n".join(lines)


def format_plan_json(plan: list[PlannedAction]) -> str:
    return json.dumps(
        [asdict(item) for item in plan],
        indent=2,
    )
