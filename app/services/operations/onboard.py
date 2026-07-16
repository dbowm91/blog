"""Onboard service functions — reusable logic for first-run and reconfiguration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.onboarding.model import OnboardingInput
from app.onboarding.planner import generate_plan as _generate_plan
from app.onboarding.state import detect_installation as _detect_installation
from app.onboarding.steps import run_steps
from app.services.operations.results import (
    OnboardApplyResult,
    OnboardDetectResult,
    OnboardPlanResult,
)


def detect_installation(
    config_path: Path | None = None,
    data_path: Path | None = None,
) -> OnboardDetectResult:
    info = _detect_installation(config_path=config_path, data_path=data_path)

    return OnboardDetectResult(
        ok=True,
        code="onboard.detect",
        summary=f"Installation state: {info.state.value}",
        state=info.state.value,
        config_exists=info.config_exists,
        database_exists=info.database_exists,
        admin_exists=info.admin_exists,
        details={
            "env_exists": info.env_exists,
            "metadata_exists": info.metadata_exists,
        },
    )


def generate_plan(
    inp: OnboardingInput,
) -> OnboardPlanResult:
    info = _detect_installation()
    actions = _generate_plan(inp, info)

    action_dicts = [{"action": a.action, "target": a.target, "details": a.details} for a in actions]

    return OnboardPlanResult(
        ok=True,
        code="onboard.plan",
        summary=f"Plan: {len(actions)} action(s)",
        actions=action_dicts,
        action_count=len(actions),
    )


def apply_onboarding(
    input_dict: dict[str, Any],
) -> OnboardApplyResult:
    inp = OnboardingInput(**input_dict)

    if not inp.admin_password:
        raise ValueError("Admin password is required.")

    step_results = run_steps(inp)

    total = len(step_results)
    completed = sum(1 for r in step_results if r.ok)

    if step_results and not step_results[-1].ok:
        failed_step = step_results[-1]
        raise ValueError(f"Onboarding failed at step: {failed_step.message}")

    config_path = ""
    data_path = ""
    admin_username = inp.admin_username
    migration_head = ""
    next_command = ""

    for result in step_results:
        if "path" in result.details:
            path_val = result.details["path"]
            if path_val.endswith("config.toml"):
                config_path = path_val
            elif path_val.endswith(".env"):
                pass
            else:
                data_path = path_val
        if "head" in result.details:
            migration_head = result.details["head"]
        if "next_command" in result.details:
            next_command = result.details["next_command"]

    return OnboardApplyResult(
        ok=True,
        code="onboard.applied",
        summary=f"Onboarding completed: {completed}/{total} steps",
        config_path=config_path,
        data_path=data_path,
        admin_username=admin_username,
        migration_head=migration_head,
        steps_completed=completed,
        steps_total=total,
        next_command=next_command,
    )
