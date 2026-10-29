"""Coverage tests for the onboarding step pipeline.

Every test drives one step function from ``app/onboarding/steps.py`` directly
so the branch under test is isolated from the rest of the pipeline. Nothing
here touches the network, a real database server or a real service manager.
"""

from __future__ import annotations

import importlib.metadata
import importlib.resources
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.onboarding.steps as onboarding_steps
from app.onboarding.model import OnboardingInput, build_config_from_input
from app.onboarding.state import InstallationInfo, InstallState
from app.onboarding.steps import (
    STEP_NAMES,
    StepContext,
    StepResult,
    _atomic_write,
    _backup_file,
    _chown_to_service_account,
    _compensate,
    _onboarding_environment,
    _save_progress,
    _service_account_for_paths,
    _validation_config,
    _warn_missing_service_account,
    run_steps,
    step_collect_inputs,
    step_create_administrator,
    step_create_directories,
    step_plan_changes,
    step_readiness_check,
    step_render_completion,
    step_resolve_paths,
    step_resolve_secrets,
    step_run_migrations,
    step_validate_proposal,
    step_verify_assets,
    step_write_config,
)

PASSWORD = "SecurePass1!"


def _ctx(**kwargs) -> StepContext:
    kwargs.setdefault("input", OnboardingInput(mode="native", profile="development"))
    return StepContext(**kwargs)


def _fake_runtime_paths(mode_value: str | None = "system", **extra):
    attrs = {}
    if mode_value is not None:
        attrs["mode"] = SimpleNamespace(value=mode_value)
    attrs.update(extra)
    return SimpleNamespace(**attrs)


class _FakeResource:
    """A traversable resource that is deliberately not a ``pathlib.Path``."""

    def __init__(self, present: bool = True, raises: bool = False) -> None:
        self.present = present
        self.raises = raises

    def joinpath(self, *parts):
        return self

    def is_file(self) -> bool:
        if self.raises:
            raise OSError("resource check failed")
        return self.present

    def is_dir(self) -> bool:
        if self.raises:
            raise OSError("resource check failed")
        return self.present


class TestAtomicWrite:
    def test_it_writes_the_content(self, tmp_path):
        target = tmp_path / "nested" / "file.txt"

        _atomic_write(target, "payload")

        assert target.read_text() == "payload"

    def test_it_removes_the_temporary_file_when_the_replace_fails(self, tmp_path, monkeypatch):
        target = tmp_path / "file.txt"

        def boom(src, dst):
            raise OSError("replace failed")

        monkeypatch.setattr(os, "replace", boom)

        with pytest.raises(OSError, match="replace failed"):
            _atomic_write(target, "payload")

        assert not target.exists()
        assert list(tmp_path.iterdir()) == []

    def test_it_swallows_a_failure_to_remove_the_temporary_file(self, tmp_path, monkeypatch):
        target = tmp_path / "file.txt"

        def boom_replace(src, dst):
            raise OSError("replace failed")

        def boom_unlink(path):
            raise OSError("unlink failed")

        monkeypatch.setattr(os, "replace", boom_replace)
        monkeypatch.setattr(os, "unlink", boom_unlink)

        with pytest.raises(OSError, match="replace failed"):
            _atomic_write(target, "payload")


class TestBackupFile:
    def test_it_returns_none_for_a_missing_file(self, tmp_path):
        assert _backup_file(tmp_path / "absent.toml") is None

    def test_it_copies_an_existing_file(self, tmp_path):
        source = tmp_path / "config.toml"
        source.write_text("original")

        backup = _backup_file(source)

        assert backup is not None
        assert backup.exists()
        assert backup.read_text() == "original"
        assert backup.name.startswith("config.toml.backup.")


class TestStepResolvePathsModes:
    @pytest.fixture(autouse=True)
    def _clear_path_overrides(self, monkeypatch):
        for name in (
            "DEVLOG_DATA_DIR",
            "DEVLOG_CONFIG_FILE",
            "DEVLOG_ENV_FILE",
            "DEVLOG_LOG_DIR",
            "DEVLOG_RUNTIME_DIR",
        ):
            monkeypatch.delenv(name, raising=False)

    def test_docker_mode_uses_the_docker_install_mode(self, tmp_path):
        ctx = _ctx(
            input=OnboardingInput(mode="docker", profile="docker-production"),
            config_dir=tmp_path / "cfg",
            data_dir=tmp_path / "data",
            paths_explicit=True,
        )

        result = step_resolve_paths(ctx)

        assert result.ok is True
        assert ctx.runtime_paths.config_file.path == Path("/etc/devlog/config.toml")
        assert ctx.runtime_paths.data_dir.path == Path("/data")
        assert ctx.env_file == tmp_path / "cfg" / ".env"
        assert ctx.input.backup_dir == "/data/backups"

    def test_native_system_scope_uses_the_system_install_mode(self, tmp_path):
        ctx = _ctx(
            input=OnboardingInput(mode="native", profile="native-production", scope="system"),
            config_dir=tmp_path / "cfg",
            data_dir=tmp_path / "data",
            paths_explicit=True,
        )

        result = step_resolve_paths(ctx)

        assert result.ok is True
        assert ctx.runtime_paths.config_file.path == Path("/etc/devlog/config.toml")
        assert ctx.runtime_paths.data_dir.path == Path("/var/lib/devlog")
        assert ctx.input.backup_dir == "/var/lib/devlog/backups"

    def test_native_user_scope_uses_the_user_install_mode(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data-home"))

        ctx = _ctx(
            input=OnboardingInput(mode="native", profile="development", scope="user"),
            config_dir=tmp_path / "cfg",
            data_dir=tmp_path / "data",
            paths_explicit=True,
        )

        result = step_resolve_paths(ctx)

        assert result.ok is True
        assert ctx.runtime_paths.config_file.path == tmp_path / "config" / "devlog" / "config.toml"
        assert ctx.runtime_paths.data_dir.path == tmp_path / "data-home" / "devlog"

    def test_an_unknown_mode_falls_back_to_development(self, tmp_path):
        ctx = _ctx(
            input=OnboardingInput(mode="unsupported", profile="development"),
            config_dir=tmp_path / "cfg",
            data_dir=tmp_path / "data",
            paths_explicit=True,
        )

        result = step_resolve_paths(ctx)

        assert result.ok is True
        assert ctx.runtime_paths.config_file.path == Path.cwd() / "config.toml"
        assert ctx.runtime_paths.data_dir.path == Path.cwd() / "data"

    def test_an_explicit_env_file_is_kept(self, tmp_path):
        env_file = tmp_path / "custom.env"
        ctx = _ctx(
            config_dir=tmp_path / "cfg",
            data_dir=tmp_path / "data",
            env_file=env_file,
            paths_explicit=True,
        )

        step_resolve_paths(ctx)

        assert ctx.env_file == env_file


class TestStepResolvePathsWithoutTheFilesystemPackage:
    @pytest.fixture(autouse=True)
    def _hide_layout(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "app.filesystem.layout", None)

    def test_docker_falls_back_to_the_container_paths(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "mkdir", lambda self, *a, **k: None)

        ctx = _ctx(input=OnboardingInput(mode="docker", profile="docker-production"))

        result = step_resolve_paths(ctx)

        assert result.ok is True
        assert ctx.config_dir == Path("/etc/devlog")
        assert ctx.data_dir == Path("/data")
        assert ctx.env_file == Path("/etc/devlog/.env")
        assert ctx.input.backup_dir == "/data/backups"

    def test_system_scope_falls_back_to_the_system_paths(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "mkdir", lambda self, *a, **k: None)

        ctx = _ctx(
            input=OnboardingInput(mode="native", profile="native-production", scope="system")
        )

        result = step_resolve_paths(ctx)

        assert result.ok is True
        assert ctx.config_dir == Path("/etc/devlog")
        assert ctx.data_dir == Path("/var/lib/devlog")
        assert ctx.env_file == Path("/etc/devlog/.env")
        assert ctx.input.backup_dir == "/var/lib/devlog/backups"

    def test_user_scope_falls_back_to_the_xdg_paths(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / ".local" / "share"))

        ctx = _ctx(input=OnboardingInput(mode="native", profile="development", scope="user"))

        result = step_resolve_paths(ctx)

        assert result.ok is True
        assert ctx.config_dir == tmp_path / ".config" / "devlog"
        assert ctx.data_dir == tmp_path / ".local" / "share" / "devlog"
        assert ctx.env_file == ctx.config_dir / ".env"
        assert ctx.input.backup_dir == str(ctx.data_dir / "backups")

    def test_the_default_scope_falls_back_to_the_working_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        ctx = _ctx(input=OnboardingInput(mode="native", profile="development"))

        result = step_resolve_paths(ctx)

        assert result.ok is True
        assert ctx.config_dir == Path(".")
        assert ctx.data_dir == Path("data")
        assert ctx.env_file == Path(".env")
        assert ctx.input.backup_dir == "data/backups"

    def test_an_explicit_config_dir_keeps_the_env_file_beside_it(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        ctx = _ctx(
            input=OnboardingInput(mode="native", profile="development"),
            config_dir=tmp_path / "cfg",
            paths_explicit=True,
        )

        result = step_resolve_paths(ctx)

        assert result.ok is True
        assert ctx.env_file == tmp_path / "cfg" / ".env"


class TestStepCollectInputs:
    def _install_click(self, monkeypatch, prompts, confirms):
        import click

        def fake_prompt(text, default=None, hide_input=False, **kwargs):
            if text in prompts:
                return prompts[text]
            return default

        def fake_confirm(text, default=False, **kwargs):
            return confirms.get(text, default)

        monkeypatch.setattr(click, "prompt", fake_prompt)
        monkeypatch.setattr(click, "confirm", fake_confirm)

    def test_it_collects_every_prompted_value(self, monkeypatch):
        self._install_click(
            monkeypatch,
            {
                "Site title": "Prompted Site",
                "Site description": "Prompted description",
                "Base URL": "https://prompted.example",
                "Admin username": "prompted-admin",
                "Admin password": PASSWORD,
                "SMTP host": "smtp.example.com",
                "SMTP port": 2525,
                "SMTP user": "mailer",
                "SMTP password": "smtp-secret",
                "From address": "from@example.com",
            },
            {"Enable newsletter?": True, "Enable scheduler?": True, "Enable Redis?": False},
        )

        ctx = _ctx(input=OnboardingInput(mode="native", profile="development"))
        result = step_collect_inputs(ctx)

        assert result.ok is True
        assert ctx.input.site_title == "Prompted Site"
        assert ctx.input.base_url == "https://prompted.example"
        assert ctx.input.admin_username == "prompted-admin"
        assert ctx.input.admin_password == PASSWORD
        assert ctx.input.enable_newsletter is True
        assert ctx.input.smtp_host == "smtp.example.com"
        assert ctx.input.smtp_port == 2525
        assert ctx.input.smtp_user == "mailer"
        assert ctx.input.smtp_password == "smtp-secret"
        assert ctx.input.from_address == "from@example.com"
        assert ctx.input.enable_scheduler is True
        assert ctx.input.enable_redis is False
        assert result.details["admin_username"] == "prompted-admin"

    def test_it_skips_the_smtp_prompts_when_the_newsletter_is_disabled(self, monkeypatch):
        self._install_click(
            monkeypatch,
            {
                "Site title": "Plain Site",
                "Admin password": PASSWORD,
            },
            {"Enable newsletter?": False, "Enable scheduler?": False, "Enable Redis?": True},
        )

        ctx = _ctx(input=OnboardingInput(mode="native", profile="development"))
        result = step_collect_inputs(ctx)

        assert result.ok is True
        assert ctx.input.enable_newsletter is False
        assert ctx.input.smtp_host == ""
        assert ctx.input.enable_redis is True

    def test_an_empty_admin_password_leaves_the_password_unset(self, monkeypatch):
        self._install_click(
            monkeypatch,
            {"Admin password": ""},
            {"Enable newsletter?": False, "Enable scheduler?": False, "Enable Redis?": False},
        )

        ctx = _ctx(input=OnboardingInput(mode="native", profile="development"))
        result = step_collect_inputs(ctx)

        assert result.ok is False
        assert "Admin password is required" in result.message

    def test_an_empty_smtp_password_is_not_stored(self, monkeypatch):
        self._install_click(
            monkeypatch,
            {
                "Admin password": PASSWORD,
                "SMTP host": "smtp.example.com",
                "SMTP password": "",
            },
            {"Enable newsletter?": True, "Enable scheduler?": False, "Enable Redis?": False},
        )

        ctx = _ctx(input=OnboardingInput(mode="native", profile="development"))
        result = step_collect_inputs(ctx)

        assert result.ok is True
        assert ctx.input.smtp_password == ""

    def test_a_prompt_failure_is_tolerated(self, monkeypatch):
        import click

        def boom(*args, **kwargs):
            raise EOFError("no terminal")

        monkeypatch.setattr(click, "prompt", boom)

        ctx = _ctx(input=OnboardingInput(mode="native", profile="development"))
        result = step_collect_inputs(ctx)

        assert result.ok is False
        assert "Admin password is required" in result.message

    def test_a_non_interactive_run_skips_the_prompts(self, monkeypatch):
        import click

        def boom(*args, **kwargs):
            raise AssertionError("no prompt expected")

        monkeypatch.setattr(click, "prompt", boom)
        monkeypatch.setattr(click, "confirm", boom)

        ctx = _ctx(
            input=OnboardingInput(
                mode="native", profile="development", admin_password=PASSWORD, non_interactive=True
            )
        )
        result = step_collect_inputs(ctx)

        assert result.ok is True
        assert result.details["admin_username"] == "admin"


class TestStepResolveSecrets:
    def test_it_generates_a_secret_key_when_none_is_resolved(self, monkeypatch, tmp_path):
        monkeypatch.setattr("app.onboarding.steps.resolve_secrets", lambda inp, existing: {})

        ctx = _ctx(
            input=OnboardingInput(mode="native", profile="development", admin_password=PASSWORD),
            env_file=tmp_path / ".env",
        )
        result = step_resolve_secrets(ctx)

        assert result.ok is True
        assert ctx.secrets["SECRET_KEY"]
        assert ctx.secrets["ADMIN_PASSWORD"] == PASSWORD
        assert "SECRET_KEY" in result.details["keys"]

    def test_it_keeps_an_existing_secret_key(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET_KEY=kept-value\n")

        ctx = _ctx(
            input=OnboardingInput(mode="native", profile="development", admin_password=PASSWORD),
            env_file=env_file,
        )
        step_resolve_secrets(ctx)

        assert ctx.secrets["SECRET_KEY"] == "kept-value"
        assert ctx.secrets["ADMIN_PASSWORD"] == PASSWORD


class TestValidationConfig:
    def test_it_overlays_the_pending_secrets(self):
        config = build_config_from_input(OnboardingInput(mode="native", profile="development"))

        merged = _validation_config(
            config,
            {
                "SECRET_KEY": "secret",
                "ADMIN_PASSWORD": PASSWORD,
                "HEALTH_CHECK_SECRET": "health",
                "METRICS_SECRET": "metrics",
                "SMTP_PASSWORD": "smtp",
                "BACKUP_ENCRYPTION_KEY": "backup",
            },
        )

        assert merged.secret_key == "secret"
        assert merged.admin_password == PASSWORD
        assert merged.health.check_secret == "health"
        assert merged.metrics.secret == "metrics"
        assert merged.email.smtp_password == "smtp"
        assert merged.backup.encryption_key == "backup"

    def test_it_falls_back_to_the_config_values(self):
        config = build_config_from_input(
            OnboardingInput(mode="native", profile="development", admin_password=PASSWORD)
        )

        merged = _validation_config(config, {})

        assert merged.secret_key == config.secret_key
        assert merged.admin_password == PASSWORD
        assert merged.health.check_secret == config.health.check_secret
        assert merged.metrics.secret == config.metrics.secret
        assert merged.email.smtp_password == config.email.smtp_password
        assert merged.backup.encryption_key == config.backup.encryption_key


class TestStepValidateProposal:
    def test_it_rejects_a_missing_config(self):
        ctx = _ctx()

        result = step_validate_proposal(ctx)

        assert result.ok is False
        assert result.message == "No config to validate"


class TestStepWriteConfig:
    def test_it_rejects_a_missing_config(self, tmp_path):
        ctx = _ctx(config_dir=tmp_path)

        result = step_write_config(ctx)

        assert result.ok is False
        assert result.message == "No config to write"


class TestServiceAccountOwnership:
    def test_it_returns_false_without_a_system_scope(self):
        ctx = _ctx(runtime_paths=_fake_runtime_paths(mode_value=None))

        assert _service_account_for_paths(ctx) is None

    def test_it_returns_false_for_a_non_native_mode(self):
        ctx = _ctx(runtime_paths=_fake_runtime_paths(mode_value="docker"))

        assert _service_account_for_paths(ctx) is None

    def test_a_resolved_system_install_carries_its_mode(self):
        from app.filesystem.layout import InstallMode, RuntimePaths

        runtime_paths = RuntimePaths.for_mode(InstallMode.SYSTEM)
        ctx = _ctx(runtime_paths=runtime_paths)

        assert _service_account_for_paths(ctx) == ("devlog", "devlog")

    def test_it_returns_the_system_account(self):
        ctx = _ctx(runtime_paths=_fake_runtime_paths(mode_value="system"))

        assert _service_account_for_paths(ctx) == ("devlog", "devlog")

    def test_it_reports_a_missing_account(self, monkeypatch, tmp_path):
        def boom(user, group):
            raise KeyError(user)

        monkeypatch.setattr("app.onboarding.steps._account_ids", boom)

        ctx = _ctx(runtime_paths=_fake_runtime_paths(mode_value="system"))

        assert _chown_to_service_account(tmp_path, ctx) is False
        assert any("does not exist" in warning for warning in ctx.warnings)

    def test_the_missing_account_warning_is_only_reported_once(self):
        ctx = _ctx()

        _warn_missing_service_account(ctx, "devlog", "devlog")
        _warn_missing_service_account(ctx, "devlog", "devlog")

        assert len(ctx.warnings) == 1

    def test_it_does_not_chown_when_the_process_is_not_root(self, monkeypatch, tmp_path):
        monkeypatch.setattr("app.onboarding.steps._account_ids", lambda user, group: (1, 2))
        monkeypatch.setattr(os, "geteuid", lambda: 1000)

        ctx = _ctx(runtime_paths=_fake_runtime_paths(mode_value="system"))

        assert _chown_to_service_account(tmp_path, ctx) is False

    def test_it_reports_a_failed_chown(self, monkeypatch, tmp_path):
        monkeypatch.setattr("app.onboarding.steps._account_ids", lambda user, group: (1, 2))
        monkeypatch.setattr(os, "geteuid", lambda: 0)

        def boom(path, uid, gid):
            raise OSError("not permitted")

        monkeypatch.setattr(os, "chown", boom)

        ctx = _ctx(runtime_paths=_fake_runtime_paths(mode_value="system"))

        assert _chown_to_service_account(tmp_path, ctx) is False

    def test_it_chowns_the_directory_when_root(self, monkeypatch, tmp_path):
        monkeypatch.setattr("app.onboarding.steps._account_ids", lambda user, group: (1, 2))
        monkeypatch.setattr(os, "geteuid", lambda: 0)

        owned = {}

        def record(path, uid, gid):
            owned["path"] = path
            owned["uid"] = uid
            owned["gid"] = gid

        monkeypatch.setattr(os, "chown", record)

        ctx = _ctx(runtime_paths=_fake_runtime_paths(mode_value="system"))

        assert _chown_to_service_account(tmp_path, ctx) is True
        assert owned == {"path": tmp_path, "uid": 1, "gid": 2}


class TestStepCreateDirectories:
    def test_it_creates_the_directories(self, tmp_path):
        ctx = _ctx(
            input=OnboardingInput(mode="native", profile="development", backup_dir="backups"),
            data_dir=tmp_path / "data",
        )
        ctx.input = OnboardingInput(
            mode="native", profile="development", backup_dir=str(tmp_path / "backups")
        )

        result = step_create_directories(ctx)

        assert result.ok is True
        assert (tmp_path / "data").is_dir()
        assert (tmp_path / "data" / "logs").is_dir()
        assert (tmp_path / "backups").is_dir()
        assert result.details["created"]
        assert result.details["chowned"] == []

    def test_it_records_the_directories_it_chowned(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "app.onboarding.steps._chown_to_service_account", lambda path, ctx: True
        )

        ctx = _ctx(
            input=OnboardingInput(
                mode="native", profile="development", backup_dir=str(tmp_path / "backups")
            ),
            data_dir=tmp_path / "data",
        )

        result = step_create_directories(ctx)

        assert result.ok is True
        assert result.details["chowned"]
        assert str(tmp_path / "data") in result.details["chowned"]

    def test_it_uses_the_runtime_log_and_runtime_directories(self, tmp_path):
        runtime_paths = SimpleNamespace(
            log_dir=SimpleNamespace(path=tmp_path / "logs"),
            runtime_dir=SimpleNamespace(path=tmp_path / "run"),
        )
        ctx = _ctx(
            input=OnboardingInput(
                mode="native", profile="development", backup_dir=str(tmp_path / "backups")
            ),
            data_dir=tmp_path / "data",
            runtime_paths=runtime_paths,
        )

        result = step_create_directories(ctx)

        assert result.ok is True
        assert (tmp_path / "logs").is_dir()
        assert (tmp_path / "run").is_dir()

    def test_it_skips_directories_the_runtime_paths_do_not_provide(self, tmp_path):
        ctx = _ctx(
            input=OnboardingInput(
                mode="native", profile="development", backup_dir=str(tmp_path / "backups")
            ),
            data_dir=tmp_path / "data",
            runtime_paths=SimpleNamespace(),
        )

        result = step_create_directories(ctx)

        assert result.ok is True
        assert (tmp_path / "data").is_dir()


class TestStepRunMigrations:
    def test_it_reports_a_failed_migration(self, app, monkeypatch):
        from app.services.operations.results import MigrationStatusResult

        monkeypatch.setattr("app.create_app", lambda *a, **k: app)
        monkeypatch.setattr(
            "app.services.operations.database.run_migrations",
            lambda: MigrationStatusResult(
                ok=False,
                code="db.migration.failed",
                summary="Migration failed: boom",
                current_head="",
            ),
        )

        ctx = _ctx(input=OnboardingInput(mode="native", profile="development"))
        result = step_run_migrations(ctx)

        assert result.ok is False
        assert "Migration failed: boom" in result.message
        assert result.details["error"] == "Migration failed: boom"

    def test_it_reports_a_migration_error(self, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("no app")

        monkeypatch.setattr("app.create_app", boom)

        ctx = _ctx(input=OnboardingInput(mode="native", profile="development"))
        result = step_run_migrations(ctx)

        assert result.ok is False
        assert "Migration error: no app" in result.message
        assert result.details["error"] == "no app"


class TestStepCreateAdministrator:
    def test_it_requires_a_password(self):
        ctx = _ctx(input=OnboardingInput(mode="native", profile="development"))

        result = step_create_administrator(ctx)

        assert result.ok is False
        assert result.message == "Admin password not set"

    def test_it_skips_an_existing_administrator(self):
        ctx = _ctx(
            input=OnboardingInput(mode="native", profile="development", admin_password=PASSWORD),
            state=InstallationInfo(
                state=InstallState.COMPLETE,
                config_exists=True,
                env_exists=True,
                database_exists=True,
                metadata_exists=True,
                admin_exists=True,
            ),
        )

        result = step_create_administrator(ctx)

        assert result.ok is True
        assert result.details["skipped"] is True
        assert "already exists" in result.message

    def test_it_creates_the_administrator(self, app, monkeypatch):
        from app.services.operations.results import AdminCreatedResult

        monkeypatch.setattr("app.create_app", lambda *a, **k: app)
        monkeypatch.setattr(
            "app.services.operations.admin.create_admin",
            lambda username, password, **kwargs: AdminCreatedResult(
                ok=True,
                code="admin.created",
                summary="Admin user 'admin' created.",
                username=username,
            ),
        )

        ctx = _ctx(
            input=OnboardingInput(mode="native", profile="development", admin_password=PASSWORD)
        )
        result = step_create_administrator(ctx)

        assert result.ok is True
        assert result.details["username"] == "admin"
        assert "created" in result.message

    def test_it_reports_a_creation_error(self, app, monkeypatch):
        def boom(username, password, **kwargs):
            raise ValueError("password rejected")

        monkeypatch.setattr("app.create_app", lambda *a, **k: app)
        monkeypatch.setattr("app.services.operations.admin.create_admin", boom)

        ctx = _ctx(
            input=OnboardingInput(mode="native", profile="development", admin_password=PASSWORD)
        )
        result = step_create_administrator(ctx)

        assert result.ok is False
        assert "Admin creation error: password rejected" in result.message
        assert result.details["error"] == "password rejected"


class TestStepVerifyAssets:
    def test_it_uses_the_packaged_resources(self, monkeypatch):
        monkeypatch.setattr(
            importlib.resources, "files", lambda package: _FakeResource(present=True)
        )

        ctx = _ctx()
        result = step_verify_assets(ctx)

        assert result.ok is True
        assert result.message == "Asset check complete"
        assert result.details == {
            "themes_bundled": True,
            "base_template": True,
            "vite_manifest": True,
            "migrations": True,
        }
        assert ctx.warnings == []

    def test_it_falls_back_to_the_source_tree_when_the_resources_fail(self, monkeypatch):
        def boom(package):
            raise ModuleNotFoundError(package)

        monkeypatch.setattr(importlib.resources, "files", boom)

        ctx = _ctx()
        result = step_verify_assets(ctx)

        assert set(result.details) == {
            "themes_bundled",
            "base_template",
            "vite_manifest",
            "migrations",
        }
        assert "base_template" in result.details

    def test_it_reports_a_missing_resource(self, monkeypatch):
        monkeypatch.setattr(
            importlib.resources, "files", lambda package: _FakeResource(present=False)
        )

        ctx = _ctx()
        result = step_verify_assets(ctx)

        assert result.ok is False
        assert "Missing assets: 4" == result.message
        assert len(ctx.warnings) == 4

    def test_it_reports_a_resource_check_failure(self, monkeypatch):
        monkeypatch.setattr(
            importlib.resources, "files", lambda package: _FakeResource(raises=True)
        )

        ctx = _ctx()
        result = step_verify_assets(ctx)

        assert result.ok is False
        assert all(value is False for value in result.details.values())
        assert len(ctx.warnings) == 4


class TestStepReadinessCheck:
    def test_it_passes_when_the_database_answers(self, app, monkeypatch):
        monkeypatch.setattr("app.create_app", lambda *a, **k: app)

        ctx = _ctx(input=OnboardingInput(mode="native", profile="development"))
        result = step_readiness_check(ctx)

        assert result.ok is True
        assert result.details == {"db": True, "models": True}

    def test_it_reports_a_failure(self, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("no app")

        monkeypatch.setattr("app.create_app", boom)

        ctx = _ctx(input=OnboardingInput(mode="native", profile="development"))
        result = step_readiness_check(ctx)

        assert result.ok is False
        assert "Readiness check failed: no app" in result.message
        assert result.details["error"] == "no app"


class TestStepRenderCompletion:
    def test_a_docker_install_uses_the_compose_command(self):
        ctx = _ctx(
            input=OnboardingInput(mode="docker", profile="docker-production"),
            config_dir=Path("/etc/devlog"),
            data_dir=Path("/data"),
        )

        result = step_render_completion(ctx)

        assert result.ok is True
        assert result.details["next_command"] == "docker compose --profile production up -d"

    def test_a_native_production_install_uses_the_run_command(self):
        ctx = _ctx(
            input=OnboardingInput(mode="native", profile="native-production"),
            config_dir=Path("/etc/devlog"),
            data_dir=Path("/var/lib/devlog"),
        )

        result = step_render_completion(ctx)

        assert result.ok is True
        assert result.details["next_command"] == "python run.py"

    def test_a_development_install_uses_the_run_command(self):
        ctx = _ctx(
            input=OnboardingInput(mode="native", profile="development"),
            config_dir=Path("/etc/devlog"),
            data_dir=Path("/var/lib/devlog"),
        )

        result = step_render_completion(ctx)

        assert result.ok is True
        assert result.details["next_command"] == "python run.py"


class TestOnboardingEnvironment:
    def test_it_exposes_the_config_and_the_secrets(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DEVLOG_CONFIG", raising=False)
        monkeypatch.delenv("ONBOARDING_TEST_SECRET", raising=False)

        config_path = tmp_path / "config.toml"
        config_path.write_text("[app]\n")
        ctx = _ctx(
            config_dir=tmp_path,
            secrets={"ONBOARDING_TEST_SECRET": "abc", "EMPTY_SECRET": ""},
        )

        with _onboarding_environment(ctx):
            assert os.environ["DEVLOG_CONFIG"] == str(config_path)
            assert os.environ["ONBOARDING_TEST_SECRET"] == "abc"
            assert "EMPTY_SECRET" not in os.environ

        assert "DEVLOG_CONFIG" not in os.environ
        assert "ONBOARDING_TEST_SECRET" not in os.environ

    def test_it_restores_a_previous_value(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ONBOARDING_TEST_SECRET", "previous")
        ctx = _ctx(config_dir=tmp_path, secrets={"ONBOARDING_TEST_SECRET": "new"})

        with _onboarding_environment(ctx):
            assert os.environ["ONBOARDING_TEST_SECRET"] == "new"

        assert os.environ["ONBOARDING_TEST_SECRET"] == "previous"


class TestCompensate:
    def test_it_removes_the_created_files_and_directories(self, tmp_path):
        created_file = tmp_path / "config.toml"
        created_file.write_text("content")
        created_dir = tmp_path / "data"
        created_dir.mkdir()

        ctx = _ctx(created_files=[created_file], created_dirs=[created_dir])
        _compensate(ctx)

        assert not created_file.exists()
        assert not created_dir.exists()

    def test_it_keeps_a_directory_that_is_not_empty(self, tmp_path):
        created_dir = tmp_path / "data"
        created_dir.mkdir()
        (created_dir / "keep.txt").write_text("keep")

        ctx = _ctx(created_dirs=[created_dir])
        _compensate(ctx)

        assert created_dir.exists()

    def test_it_swallows_a_failure_to_remove_a_file(self, tmp_path, monkeypatch):
        created_file = tmp_path / "config.toml"
        created_file.write_text("content")

        def boom(self):
            raise OSError("cannot unlink")

        monkeypatch.setattr(Path, "unlink", boom)

        ctx = _ctx(created_files=[created_file])
        _compensate(ctx)

        assert created_file.exists()

    def test_it_swallows_a_failure_to_remove_a_directory(self, tmp_path, monkeypatch):
        created_dir = tmp_path / "data"
        created_dir.mkdir()

        def boom(self):
            raise OSError("cannot rmdir")

        monkeypatch.setattr(Path, "rmdir", boom)

        ctx = _ctx(created_dirs=[created_dir])
        _compensate(ctx)

        assert created_dir.exists()


class TestSaveProgress:
    def test_it_writes_the_metadata(self, tmp_path):
        ctx = _ctx(
            input=OnboardingInput(mode="native", profile="development", admin_username="root"),
            config_dir=tmp_path / "cfg",
            data_dir=tmp_path / "data",
            env_file=tmp_path / "cfg" / ".env",
        )

        _save_progress(ctx, 3)

        meta = json.loads((tmp_path / "data" / "onboarding-metadata.json").read_text())
        assert meta["last_completed_step"] == 3
        assert meta["admin_username"] == "root"
        assert meta["mode"] == "native"
        assert meta["completed_at"] == ""

    def test_it_marks_the_last_step_as_complete(self, tmp_path):
        ctx = _ctx(config_dir=tmp_path / "cfg", data_dir=tmp_path / "data")

        _save_progress(ctx, len(STEP_NAMES) - 1)

        meta = json.loads((tmp_path / "data" / "onboarding-metadata.json").read_text())
        assert meta["completed_at"]

    def test_it_records_where_the_run_stopped(self, tmp_path):
        ctx = _ctx(config_dir=tmp_path / "cfg", data_dir=tmp_path / "data")

        _save_progress(ctx, 2, stopped_at="step_build_config", stopped_reason="boom")

        meta = json.loads((tmp_path / "data" / "onboarding-metadata.json").read_text())
        assert meta["stopped_at"] == "step_build_config"
        assert meta["stopped_reason"] == "boom"
        assert meta["completed_at"] == ""

    def test_it_survives_a_missing_package_version(self, tmp_path, monkeypatch):
        def boom(name):
            raise importlib.metadata.PackageNotFoundError(name)

        monkeypatch.setattr(importlib.metadata, "version", boom)

        ctx = _ctx(config_dir=tmp_path / "cfg", data_dir=tmp_path / "data")
        _save_progress(ctx, 1)

        meta = json.loads((tmp_path / "data" / "onboarding-metadata.json").read_text())
        assert meta["package_version"] == ""


class TestRunStepsResume:
    def test_it_skips_the_steps_before_the_start_index(self, tmp_path, monkeypatch):
        inp = OnboardingInput(
            mode="native",
            profile="development",
            admin_password=PASSWORD,
            dry_run=True,
            non_interactive=True,
        )
        steps = [
            lambda ctx, index=index: StepResult(ok=True, message=f"Ran step {index}")
            for index in range(5)
        ]
        monkeypatch.setattr(onboarding_steps, "_ALL_STEPS", steps)

        results = run_steps(
            inp,
            config_path=tmp_path / "config.toml",
            data_path=tmp_path / "data",
            start_step=3,
        )

        assert [result.message for result in results[:3]] == ["Skipped (resume from step 3)"] * 3
        assert [result.message for result in results[3:]] == ["Ran step 3", "Ran step 4"]

    def test_it_stops_at_the_first_failing_step(self, tmp_path):
        inp = OnboardingInput(
            mode="native",
            profile="development",
            admin_password="",
            dry_run=True,
            non_interactive=True,
        )

        results = run_steps(
            inp,
            config_path=tmp_path / "config.toml",
            data_path=tmp_path / "data",
        )

        failed = [result for result in results if not result.ok]
        assert len(failed) == 1
        assert "Admin password is required" in failed[0].message


class TestStepPlanChanges:
    def test_it_describes_the_actions(self, tmp_path):
        ctx = _ctx(
            input=OnboardingInput(
                mode="native", profile="development", backup_dir=str(tmp_path / "backups")
            ),
            state=InstallationInfo(
                state=InstallState.FRESH,
                config_exists=False,
                env_exists=False,
                database_exists=False,
                metadata_exists=False,
                admin_exists=False,
            ),
        )

        result = step_plan_changes(ctx)

        assert result.ok is True
        actions = result.details["actions"]
        assert actions
        assert all({"action", "target"} == set(action) for action in actions)


def test_step_result_is_frozen():
    result = StepResult(ok=True, message="done")

    with pytest.raises(Exception):
        result.ok = False
