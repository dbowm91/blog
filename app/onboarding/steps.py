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
    env_file: Path = field(default_factory=lambda: Path(".env"))
    dry_run: bool = False
    created_files: list[Path] = field(default_factory=list)
    created_dirs: list[Path] = field(default_factory=list)
    step_index: int = 0
    runtime_paths: Any | None = None


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

    try:
        from app.filesystem.layout import InstallMode, RuntimePaths

        scope = inp.scope or ""
        if inp.mode == "docker":
            install_mode = InstallMode.DOCKER
        elif inp.mode == "native":
            if scope == "system":
                install_mode = InstallMode.SYSTEM
            elif scope == "user":
                install_mode = InstallMode.USER
            else:
                install_mode = InstallMode.DEVELOPMENT
        else:
            install_mode = InstallMode.DEVELOPMENT

        runtime_paths = RuntimePaths.for_mode(install_mode)
        ctx.runtime_paths = runtime_paths

        ctx.config_dir = runtime_paths.config_file.path.parent
        ctx.data_dir = runtime_paths.data_dir.path
        ctx.env_file = runtime_paths.env_file.path

        ctx.config_dir.mkdir(parents=True, exist_ok=True)
        ctx.data_dir.mkdir(parents=True, exist_ok=True)
    except ImportError:
        if inp.mode == "docker":
            config_dir = Path("/etc/devlog")
            data_dir = Path("/data")
            env_file = Path("/etc/devlog/.env")
        elif inp.scope == "system":
            config_dir = Path("/etc/devlog")
            data_dir = Path("/var/lib/devlog")
            env_file = Path("/etc/devlog/.env")
        elif inp.scope == "user":
            from pathlib import Path as P

            home = P.home()
            config_dir = home / ".config" / "devlog"
            data_dir = home / ".local" / "share" / "devlog"
            env_file = config_dir / ".env"
        else:
            config_dir = Path(".")
            data_dir = Path("data")
            env_file = Path(".env")

        ctx.config_dir = config_dir
        ctx.data_dir = data_dir
        ctx.env_file = env_file

        config_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)

    return StepResult(
        ok=True,
        message=f"Config: {ctx.config_dir}, Data: {ctx.data_dir}",
        details={
            "config_dir": str(ctx.config_dir),
            "data_dir": str(ctx.data_dir),
            "env_file": str(ctx.env_file),
        },
    )


def step_collect_inputs(ctx: StepContext) -> StepResult:
    inp = ctx.input

    if not inp.non_interactive and not inp.accept_defaults:
        try:
            import click

            updates: dict[str, object] = {}
            updates["site_title"] = click.prompt("Site title", default=inp.site_title)
            updates["site_description"] = click.prompt(
                "Site description", default=inp.site_description
            )
            updates["base_url"] = click.prompt("Base URL", default=inp.base_url)
            updates["admin_username"] = click.prompt("Admin username", default=inp.admin_username)

            admin_pw = click.prompt("Admin password", hide_input=True, default="")
            if admin_pw:
                updates["admin_password"] = admin_pw

            enable_newsletter = click.confirm("Enable newsletter?", default=inp.enable_newsletter)
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

            updates["enable_scheduler"] = click.confirm(
                "Enable scheduler?", default=inp.enable_scheduler
            )
            updates["enable_redis"] = click.confirm("Enable Redis?", default=inp.enable_redis)

            inp = inp.__class__(**{**inp.__dict__, **updates})
            ctx.input = inp
        except (ImportError, EOFError):
            pass

    if not inp.admin_password:
        return StepResult(
            ok=False,
            message="Admin password is required. Set via prompt, --admin-password-file, or ADMIN_PASSWORD env var.",
        )

    return StepResult(
        ok=True,
        message="Inputs collected",
        details={"admin_username": inp.admin_username},
    )


def step_build_config(ctx: StepContext) -> StepResult:
    config = build_config_from_input(ctx.input, data_dir=ctx.data_dir)
    ctx.config = config
    return StepResult(
        ok=True,
        message="Configuration built",
        details={"title": config.app.title, "base_url": config.site.base_url},
    )


def step_resolve_secrets(ctx: StepContext) -> StepResult:
    inp = ctx.input
    existing: dict[str, str] = {}

    if ctx.env_file.exists():
        existing = read_env_file(ctx.env_file)

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
    ctx.created_files.append(config_path)

    return StepResult(
        ok=True,
        message=f"Config written to {config_path}",
        details={"path": str(config_path)},
    )


def step_write_env(ctx: StepContext) -> StepResult:
    if ctx.dry_run:
        return StepResult(ok=True, message="Dry run: skipping .env write")

    env_path = ctx.env_file

    if env_path.exists():
        _backup_file(env_path)

    write_env_file(env_path, ctx.secrets)
    ctx.created_files.append(env_path)

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
            ctx.created_dirs.append(d)

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
    try:
        from importlib.resources import as_file, files

        pkg = files("app")
        checks = {
            "themes_bundled": pkg.joinpath("themes", "bundled"),
            "migrations": pkg.joinpath("migrations", "versions"),
            "base_template": pkg.joinpath("templates", "base.html"),
        }
    except Exception:
        checks = {
            "themes_bundled": Path("app/themes/bundled"),
            "migrations": Path("migrations/versions"),
            "base_template": Path("app/templates/base.html"),
        }

    try:
        from importlib.resources import as_file, files

        manifest = files("app.static").joinpath("dist", "manifest.json")
        with as_file(manifest) as p:
            checks["vite_manifest"] = Path(str(p))
    except Exception:
        checks["vite_manifest"] = Path("app/static/dist/manifest.json")

    results: dict[str, bool] = {}
    warnings: list[str] = []

    for name, path_or_ref in checks.items():
        try:
            p = Path(str(path_or_ref)) if not isinstance(path_or_ref, Path) else path_or_ref
            exists = p.exists()
        except Exception:
            exists = False
        results[name] = exists
        if not exists:
            warnings.append(f"Missing: {name}")

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

    _save_progress(ctx, ctx.step_index)

    return StepResult(
        ok=True,
        message="Metadata saved",
        details={},
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

STEP_NAMES = [s.__name__ for s in _ALL_STEPS]


def _compensate(ctx: StepContext) -> None:
    for f in reversed(ctx.created_files):
        try:
            if f.exists():
                f.unlink()
        except OSError:
            pass
    for d in reversed(ctx.created_dirs):
        try:
            if d.exists() and not any(d.iterdir()):
                d.rmdir()
        except OSError:
            pass


def _save_progress(
    ctx: StepContext, step_index: int, stopped_at: str = "", stopped_reason: str = ""
) -> None:
    if ctx.dry_run:
        return

    from datetime import datetime, timezone

    from app.onboarding.metadata import OnboardingMetadata, save_metadata

    inp = ctx.input
    now = datetime.now(timezone.utc).isoformat()

    completed_at = ""
    is_last_real_step = step_index >= len(_ALL_STEPS) - 2
    if stopped_at == "" and is_last_real_step:
        completed_at = now

    try:
        from importlib.metadata import version

        pkg_version = version("devlog")
    except Exception:
        pkg_version = ""

    metadata = OnboardingMetadata(
        version=1,
        mode=inp.mode,
        profile=inp.profile,
        package_version=pkg_version,
        completed_at=completed_at,
        config_path=str(ctx.config_dir / "config.toml"),
        data_path=str(ctx.data_dir),
        managed_paths=[
            str(ctx.config_dir / "config.toml"),
            str(ctx.env_file),
            str(ctx.data_dir),
            inp.backup_dir,
        ],
        admin_username=inp.admin_username,
        last_completed_step=step_index,
        stopped_at=stopped_at,
        stopped_reason=stopped_reason,
    )

    save_metadata(ctx.data_dir, metadata)


def run_steps(
    input: OnboardingInput,
    config_path: Path | None = None,
    data_path: Path | None = None,
    start_step: int = 0,
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

    for i, step_fn in enumerate(_ALL_STEPS):
        if i < start_step:
            results.append(StepResult(ok=True, message=f"Skipped (resume from step {start_step})"))
            continue

        ctx.step_index = i
        result = step_fn(ctx)
        results.append(result)

        if not result.ok:
            step_name = STEP_NAMES[i] if i < len(STEP_NAMES) else step_fn.__name__
            _save_progress(ctx, i, stopped_at=step_name, stopped_reason=result.message)
            _compensate(ctx)
            break

        if step_fn.__name__ != "step_render_completion":
            _save_progress(ctx, i)

    return results
