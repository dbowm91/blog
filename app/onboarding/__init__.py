from __future__ import annotations

from app.onboarding.metadata import (
    OnboardingMetadata,
    is_complete,
    load_metadata,
    save_metadata,
)
from app.onboarding.model import OnboardingInput, build_config_from_input
from app.onboarding.planner import (
    PlannedAction,
    format_plan_json,
    format_plan_text,
    generate_plan,
)
from app.onboarding.rendering import CompletionInfo, render_completion_human, render_completion_json
from app.onboarding.secrets import (
    generate_health_secret,
    generate_metrics_secret,
    generate_secret_key,
    read_env_file,
    resolve_secrets,
    write_env_file,
)
from app.onboarding.state import (
    InstallState,
    InstallationInfo,
    detect_installation,
)
from app.onboarding.steps import StepContext, StepResult, run_steps, STEP_NAMES

__all__ = [
    "CompletionInfo",
    "InstallState",
    "InstallationInfo",
    "OnboardingInput",
    "OnboardingMetadata",
    "PlannedAction",
    "StepContext",
    "StepResult",
    "STEP_NAMES",
    "build_config_from_input",
    "detect_installation",
    "format_plan_json",
    "format_plan_text",
    "generate_health_secret",
    "generate_metrics_secret",
    "generate_plan",
    "generate_secret_key",
    "is_complete",
    "load_metadata",
    "read_env_file",
    "render_completion_human",
    "render_completion_json",
    "resolve_secrets",
    "run_steps",
    "save_metadata",
    "write_env_file",
]
