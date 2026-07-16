"""Onboard service functions — reusable logic for first-run and reconfiguration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.onboarding.model import OnboardingInput
from app.onboarding.planner import generate_plan as _generate_plan
from app.onboarding.state import detect_installation as _detect_installation
from app.onboarding.steps import run_steps, STEP_NAMES
from app.services.operations.results import (
    OnboardApplyResult,
    OnboardDetectResult,
    OnboardPlanResult,
    OnboardResumeResult,
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


def resume_onboarding(
    data_path: Path | None = None,
) -> OnboardResumeResult:
    from app.onboarding.metadata import load_metadata, is_complete

    target = data_path or Path("data")
    metadata = load_metadata(target)

    if metadata is None:
        return OnboardResumeResult(
            ok=False,
            code="onboard.resume.no_metadata",
            summary="No onboarding metadata found. Run 'devlog onboard run' first.",
            last_step="",
            last_step_index=-1,
            stopped_at="",
            stopped_reason="",
            completed=False,
        )

    if is_complete(metadata):
        return OnboardResumeResult(
            ok=True,
            code="onboard.resume.complete",
            summary="Onboarding already completed. Nothing to resume.",
            last_step=STEP_NAMES[metadata.last_completed_step]
            if 0 <= metadata.last_completed_step < len(STEP_NAMES)
            else "",
            last_step_index=metadata.last_completed_step,
            stopped_at="",
            stopped_reason="",
            completed=True,
        )

    start_step = metadata.last_completed_step + 1
    if start_step >= len(STEP_NAMES):
        start_step = len(STEP_NAMES) - 1

    inp = OnboardingInput(
        mode=metadata.mode,
        profile=metadata.profile,
        non_interactive=True,
    )

    step_results = run_steps(inp, start_step=start_step)

    total = len(step_results)
    completed = sum(1 for r in step_results if r.ok)

    if step_results and not step_results[-1].ok:
        failed_step = step_results[-1]
        return OnboardResumeResult(
            ok=False,
            code="onboard.resume.failed",
            summary=f"Resume failed at step: {failed_step.message}",
            last_step=failed_step.message,
            last_step_index=metadata.last_completed_step + 1,
            stopped_at=STEP_NAMES[metadata.last_completed_step + 1]
            if metadata.last_completed_step + 1 < len(STEP_NAMES)
            else "",
            stopped_reason=failed_step.message,
            completed=False,
        )

    return OnboardResumeResult(
        ok=True,
        code="onboard.resumed",
        summary=f"Onboarding resumed and completed: {completed}/{total} steps",
        last_step=STEP_NAMES[-1],
        last_step_index=len(STEP_NAMES) - 1,
        stopped_at="",
        stopped_reason="",
        completed=True,
    )
