from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.onboarding.model import OnboardingInput, build_config_from_input
from app.onboarding.planner import generate_plan
from app.onboarding.secrets import (
    generate_secret_key,
    read_env_file,
    resolve_secrets,
    write_env_file,
)
from app.onboarding.state import InstallationInfo, detect_installation


@dataclass
class StepContext:
    input: OnboardingInput
    config: Any | None = None
    state: InstallationInfo | None = None
    secrets: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    config_dir: Path = field(default_factory=lambda: Path("."))
    data_dir: Path = field(default_factory=lambda: Path("data"))
    dry_run: bool = False


@dataclass(frozen=True)
class StepResult:
    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp", prefix=f".{path.name}-")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.parent / f"{path.name}.backup.{ts}"
    import shutil

    shutil.copy2(path, backup)
    return backup


def step_detect_installation(ctx: StepContext) -> StepResult:
    state = detect_installation(
        config_path=ctx.config_dir / "config.toml" if ctx.config_dir else None,
        data_path=ctx.data_dir,
    )
    ctx.state = state
    return StepResult(
        ok=True,
        message=f"Installation state: {state.state.value}",
        details={
            "state": state.state.value,
            "config_exists": state.config_exists,
            "env_exists": state.env_exists,
            "database_exists": state.database_exists,
            "admin_exists": state.admin_exists,
        },
    )


def step_resolve_mode(ctx: StepContext) -> StepResult:
    inp = ctx.input
    valid_modes = {"native", "docker"}
    if inp.mode not in valid_modes:
        return StepResult(
            ok=False,
            message=f"Invalid mode: {inp.mode!r}. Expected one of: {', '.join(sorted(valid_modes))}",
        )

    valid_profiles = {
        "development",
        "native-production",
        "docker-production",
        "minimal",
        "full",
    }
    if inp.profile not in valid_profiles:
        return StepResult(
            ok=False,
            message=f"Invalid profile: {inp.profile!r}. Expected one of: {', '.join(sorted(valid_profiles))}",
        )

    if inp.mode == "docker" and inp.profile == "native-production":
        ctx.warnings.append(
            "Mode 'docker' with profile 'native-production' is unusual; consider 'docker-production'."
        )

    return StepResult(
        ok=True,
        message=f"Mode: {inp.mode}, Profile: {inp.profile}",
        details={"mode": inp.mode, "profile": inp.profile},
    )


def step_resolve_paths(ctx: StepContext) -> StepResult:
    inp = ctx.input

    if inp.mode == "docker":
        config_dir = Path("/etc/devlog")
        data_dir = Path("/data")
    else:
        config_dir = Path(".")
        data_dir = Path("data")

    ctx.config_dir = config_dir
    ctx.data_dir = data_dir

    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    return StepResult(
        ok=True,
        message=f"Config: {config_dir}, Data: {data_dir}",
        details={"config_dir": str(config_dir), "data_dir": str(data_dir)},
    )


def step_collect_inputs(ctx: StepContext) -> StepResult:
    inp = ctx.input

    if not inp.non_interactive and not inp.accept_defaults:
        try:
            import click

            updates: dict[str, object] = {}
            updates["site_title"] = click.prompt("Site title", default=inp.site_title)
            updates["site_description"] = click.prompt("Site description", default=inp.site_description)
            updates["base_url"] = click.prompt("Base URL", default=inp.base_url)
            updates["admin_username"] = click.prompt("Admin username", default=inp.admin_username)

            admin_pw = click.prompt("Admin password", hide_input=True, default="")
            if admin_pw:
                updates["admin_password"] = admin_pw

            enable_newsletter = click.confirm(
                "Enable newsletter?", default=inp.enable_newsletter
            )
            updates["enable_newsletter"] = enable_newsletter
            if enable_newsletter:
                updates["smtp_host"] = click.prompt("SMTP host", default=inp.smtp_host)
                if updates["smtp_host"]:
                    updates["smtp_port"] = int(click.prompt("SMTP port", default=inp.smtp_port))
                    updates["smtp_user"] = click.prompt("SMTP user", default=inp.smtp_user)
                    smtp_pw = click.prompt("SMTP password", hide_input=True, default="")
                    if smtp_pw:
                        updates["smtp_password"] = smtp_pw
                    updates["from_address"] = click.prompt("From address", default=inp.from_address)

            updates["enable_scheduler"] = click.confirm("Enable scheduler?", default=inp.enable_scheduler)
            updates["enable_redis"] = click.confirm("Enable Redis?", default=inp.enable_redis)

            inp = inp.__class__(**{**inp.__dict__, **updates})
            ctx.input = inp
        except (ImportError, EOFError):
            pass

    if not inp.admin_password:
        return StepResult(
            ok=False,
            message="Admin password is required. Set via prompt, --admin-password, or ADMIN_PASSWORD env var.",
        )

    if inp.non_interactive and not inp.admin_password:
        return StepResult(
            ok=False,
            message="Admin password is required in non-interactive mode.",
        )

    return StepResult(
        ok=True,
        message="Inputs collected",
        details={"admin_username": inp.admin_username},
    )


def step_build_config(ctx: StepContext) -> StepResult:
    config = build_config_from_input(ctx.input)
    ctx.config = config
    return StepResult(
        ok=True,
        message="Configuration built",
        details={"title": config.app.title, "base_url": config.site.base_url},
    )


def step_resolve_secrets(ctx: StepContext) -> StepResult:
    inp = ctx.input
    existing: dict[str, str] = {}

    env_path = Path(".env")
    if env_path.exists():
        existing = read_env_file(env_path)

    if inp.admin_password:
        existing.setdefault("ADMIN_PASSWORD", inp.admin_password)

    secrets_dict = resolve_secrets(inp, existing)
    ctx.secrets = secrets_dict

    if not secrets_dict.get("SECRET_KEY"):
        secrets_dict["SECRET_KEY"] = generate_secret_key()

    if inp.admin_password:
        secrets_dict["ADMIN_PASSWORD"] = inp.admin_password

    return StepResult(
        ok=True,
        message="Secrets resolved",
        details={"keys": list(secrets_dict.keys())},
    )


def step_plan_changes(ctx: StepContext) -> StepResult:
    state = ctx.state or detect_installation()
    plan = generate_plan(ctx.input, state)
    return StepResult(
        ok=True,
        message=f"Plan: {len(plan)} action(s)",
        details={"actions": [{"action": a.action, "target": a.target} for a in plan]},
    )


def step_validate_proposal(ctx: StepContext) -> StepResult:
    if ctx.config is None:
        return StepResult(ok=False, message="No config to validate")

    from app.config.validation import validate_all

    config_path = ctx.config_dir / "config.toml"
    result = validate_all(ctx.config, config_path=config_path)

    if not result.ok:
        error_msgs = [f.message for f in result.errors]
        return StepResult(
            ok=False,
            message=f"Validation failed: {'; '.join(error_msgs)}",
            details={"errors": [f.message for f in result.errors]},
        )

    warning_msgs = [f.message for f in result.warnings]
    ctx.warnings.extend(warning_msgs)

    return StepResult(
        ok=True,
        message="Validation passed",
        details={"warnings": warning_msgs},
    )


def step_write_config(ctx: StepContext) -> StepResult:
    if ctx.dry_run:
        return StepResult(ok=True, message="Dry run: skipping config write")

    if ctx.config is None:
        return StepResult(ok=False, message="No config to write")

    from app.config.serialization import config_to_toml

    config_path = ctx.config_dir / "config.toml"

    if config_path.exists():
        _backup_file(config_path)

    toml_content = config_to_toml(ctx.config)
    _atomic_write(config_path, toml_content)

    return StepResult(
        ok=True,
        message=f"Config written to {config_path}",
        details={"path": str(config_path)},
    )


def step_write_env(ctx: StepContext) -> StepResult:
    if ctx.dry_run:
        return StepResult(ok=True, message="Dry run: skipping .env write")

    env_path = Path(".env")

    if env_path.exists():
        _backup_file(env_path)

    write_env_file(env_path, ctx.secrets)

    return StepResult(
        ok=True,
        message=f"Secrets written to {env_path}",
        details={"path": str(env_path)},
    )


def step_create_directories(ctx: StepContext) -> StepResult:
    if ctx.dry_run:
        return StepResult(ok=True, message="Dry run: skipping directory creation")

    dirs = [
        ctx.data_dir,
        ctx.data_dir / "logs",
        Path(ctx.input.backup_dir),
    ]

    created: list[str] = []
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(str(d))

    return StepResult(
        ok=True,
        message=f"Directories ready ({len(created)} created)",
        details={"created": created},
    )


def step_run_migrations(ctx: StepContext) -> StepResult:
    if ctx.dry_run:
        return StepResult(ok=True, message="Dry run: skipping migrations")

    try:
        from app import create_app

        app = create_app()
        with app.app_context():
            from app.services.operations.database import run_migrations

            result = run_migrations()
            if not result.ok:
                return StepResult(
                    ok=False,
                    message=f"Migration failed: {result.summary}",
                    details={"error": result.summary},
                )
            return StepResult(
                ok=True,
                message=result.summary,
                details={"head": result.current_head},
            )
    except Exception as e:
        return StepResult(
            ok=False,
            message=f"Migration error: {e}",
            details={"error": str(e)},
        )


def step_create_administrator(ctx: StepContext) -> StepResult:
    if ctx.dry_run:
        return StepResult(ok=True, message="Dry run: skipping admin creation")

    inp = ctx.input
    if not inp.admin_password:
        return StepResult(ok=False, message="Admin password not set")

    if ctx.state and ctx.state.admin_exists:
        return StepResult(
            ok=True,
            message=f"Admin user '{inp.admin_username}' already exists",
            details={"skipped": True},
        )

    try:
        from app import create_app

        app = create_app()
        with app.app_context():
            from app.services.operations.admin import create_admin

            result = create_admin(inp.admin_username, inp.admin_password)
            return StepResult(
                ok=True,
                message=result.summary,
                details={"username": result.username},
            )
    except Exception as e:
        return StepResult(
            ok=False,
            message=f"Admin creation error: {e}",
            details={"error": str(e)},
        )


def step_verify_assets(ctx: StepContext) -> StepResult:
    checks = {
        "vite_manifest": Path("app/static/dist/manifest.json"),
        "base_template": Path("app/templates/base.html"),
        "themes_bundled": Path("app/themes/bundled"),
        "migrations": Path("migrations/versions"),
    }

    results: dict[str, bool] = {}
    warnings: list[str] = []

    for name, path in checks.items():
        exists = path.exists()
        results[name] = exists
        if not exists:
            warnings.append(f"Missing: {name} at {path}")

    ctx.warnings.extend(warnings)

    all_ok = all(results.values())
    return StepResult(
        ok=all_ok,
        message="Asset check complete" if all_ok else f"Missing assets: {len(warnings)}",
        details=results,
    )


def step_readiness_check(ctx: StepContext) -> StepResult:
    if ctx.dry_run:
        return StepResult(ok=True, message="Dry run: skipping readiness check")

    try:
        from app import create_app

        app = create_app()
        with app.app_context():
            from app.extensions import db

            db.session.execute(db.text("SELECT 1"))

            return StepResult(
                ok=True,
                message="Readiness check passed",
                details={"db": True, "models": True},
            )
    except Exception as e:
        return StepResult(
            ok=False,
            message=f"Readiness check failed: {e}",
            details={"error": str(e)},
        )


def step_write_metadata(ctx: StepContext) -> StepResult:
    if ctx.dry_run:
        return StepResult(ok=True, message="Dry run: skipping metadata write")

    from datetime import datetime, timezone

    from app.onboarding.metadata import OnboardingMetadata, save_metadata

    inp = ctx.input
    now = datetime.now(timezone.utc).isoformat()

    metadata = OnboardingMetadata(
        version=1,
        mode=inp.mode,
        profile=inp.profile,
        package_version="",
        completed_at=now,
        config_path=str(ctx.config_dir / "config.toml"),
        data_path=str(ctx.data_dir),
        managed_paths=[
            str(ctx.config_dir / "config.toml"),
            ".env",
            str(ctx.data_dir),
            inp.backup_dir,
        ],
        admin_username=inp.admin_username,
    )

    save_metadata(ctx.data_dir, metadata)

    return StepResult(
        ok=True,
        message="Metadata saved",
        details={"completed_at": now},
    )


def step_render_completion(ctx: StepContext) -> StepResult:
    inp = ctx.input
    is_production = inp.profile in ("native-production", "docker-production")

    if inp.mode == "docker":
        next_cmd = "docker compose --profile production up -d"
    elif is_production:
        next_cmd = "python run.py"
    else:
        next_cmd = "python run.py"

    from app.onboarding.rendering import CompletionInfo, render_completion_human

    info = CompletionInfo(
        mode=inp.mode,
        config_path=str(ctx.config_dir / "config.toml"),
        data_path=str(ctx.data_dir),
        base_url=inp.base_url,
        admin_username=inp.admin_username,
        validation_ok=True,
        next_command=next_cmd,
        warnings=list(ctx.warnings),
    )

    output = render_completion_human(info)
    return StepResult(
        ok=True,
        message="Onboarding complete",
        details={"next_command": next_cmd, "output": output},
    )


_ALL_STEPS = [
    step_detect_installation,
    step_resolve_mode,
    step_resolve_paths,
    step_collect_inputs,
    step_build_config,
    step_resolve_secrets,
    step_plan_changes,
    step_validate_proposal,
    step_write_config,
    step_write_env,
    step_create_directories,
    step_run_migrations,
    step_create_administrator,
    step_verify_assets,
    step_readiness_check,
    step_write_metadata,
    step_render_completion,
]


def run_steps(
    input: OnboardingInput,
    config_path: Path | None = None,
    data_path: Path | None = None,
) -> list[StepResult]:
    ctx = StepContext(
        input=input,
        dry_run=input.dry_run,
    )

    if config_path:
        ctx.config_dir = config_path.parent
    if data_path:
        ctx.data_dir = data_path

    results: list[StepResult] = []

    for step_fn in _ALL_STEPS:
        result = step_fn(ctx)
        results.append(result)

        if not result.ok:
            break

    return results
