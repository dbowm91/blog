"""Branch coverage for the diagnostic checks in app.services.operations.doctor.

Every check reads its input from the effective configuration and the resolved
runtime paths, so these tests install a temporary installation, stub the
outbound integrations and assert on the returned status and summary.
"""

from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import types
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import loader as config_loader
from app.config.model import DevLogConfig
from app.filesystem import layout
from app.filesystem.layout import InstallMode, PathProvenance, ResolvedPath, RuntimePaths
from app.services.operations import doctor as doctor_mod
from app.services.operations.doctor import (
    CheckResult,
    CheckStatus,
    DoctorContext,
    _apply_safe_fixes,
    _fix_cleanup_stale_pid,
    _service_account_ids,
    _set_ctx,
    _writable_by,
    run_doctor,
)


class _FakeNoCredentialsError(Exception):
    pass


class _FakeClientError(Exception):
    def __init__(self, response):
        super().__init__(str(response))
        self.response = response


@pytest.fixture(autouse=True)
def _reset_doctor_context():
    """The doctor context is thread-local; never leak it into another test."""
    yield
    doctor_mod._ctx.doctor_context = None


def _boom(*args, **kwargs):
    raise RuntimeError("boom")


def _detect_mode(mode: InstallMode):
    def _detect():
        return SimpleNamespace(detected_mode=mode, source="test")

    return _detect


def _make_config(**sections) -> DevLogConfig:
    """Return the effective configuration with the named sections replaced."""
    base = config_loader.load_effective_config()
    updates = {}
    for name, value in sections.items():
        current = getattr(base, name)
        updates[name] = replace(current, **value) if isinstance(value, dict) else value
    return replace(base, **updates)


def _section(name: str):
    return getattr(_make_config(), name)


def _redis_section():
    return _section("redis")


def _celery_section():
    return _section("celery")


def _scheduler_section():
    return _section("scheduler")


def _email_section():
    return _section("email")


def _storage_section():
    return _section("storage")


def _backup_section():
    return _section("backup")


def _themes_section():
    return _section("themes")


def _s3_config() -> DevLogConfig:
    return _make_config(
        storage=replace(
            _storage_section(),
            backend="s3",
            s3_bucket="assets",
            s3_access_key="x" * 8,
            s3_secret_key="x" * 8,
            s3_region="eu-west-1",
            s3_endpoint="https://s3.test",
        )
    )


def _result(
    *,
    status: CheckStatus = CheckStatus.WARN,
    safe_fix_id: str | None = None,
    check_id: str = "check.one",
) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        category="filesystem",
        status=status,
        severity="optional",
        summary="summary",
        safe_fix_id=safe_fix_id,
    )


def _install_paths(root: Path, *, release: Path | None = None) -> RuntimePaths:
    paths = RuntimePaths.resolve(
        InstallMode.DEVELOPMENT,
        config_file=root / "config.toml",
        env_file=root / ".env",
        data_dir=root / "data",
        log_dir=root / "logs",
        runtime_dir=root / "runtime",
        uploads_dir=root / "uploads",
        themes_dir=root / "themes",
        backups_dir=root / "backups",
        exports_dir=root / "exports",
        database_path=root / "data" / "devlog.sqlite3",
    )
    if release is not None:
        paths = replace(
            paths,
            release_dir=ResolvedPath(
                path=release,
                provenance=PathProvenance.EXPLICIT,
                source="test release directory",
            ),
        )
    return paths


class _Install:
    """A temporary installation wired into the doctor engine."""

    def __init__(self, root: Path, monkeypatch):
        self.root = root
        self._monkeypatch = monkeypatch
        self.paths = _install_paths(root)
        self.config: DevLogConfig | None = None
        self.mode = InstallMode.DEVELOPMENT
        self._apply()

    def _apply(self) -> None:
        self._monkeypatch.setattr(RuntimePaths, "for_mode", lambda mode: self.paths)
        self._monkeypatch.setattr(layout, "detect_mode", _detect_mode(self.mode))
        if self.config is not None:
            self._monkeypatch.setattr(
                config_loader, "load_effective_config", lambda *a, **k: self.config
            )

    def use_paths(self, paths: RuntimePaths) -> None:
        self.paths = paths
        self._apply()

    def use_mode(self, mode: InstallMode) -> None:
        self.mode = mode
        self._apply()

    def use_config(self, config: DevLogConfig) -> None:
        self.config = config
        self._apply()

    def break_paths(self) -> None:
        self._monkeypatch.setattr(RuntimePaths, "for_mode", _boom)

    def break_config(self) -> None:
        self._monkeypatch.setattr(config_loader, "load_effective_config", _boom)


@pytest.fixture
def install(tmp_path, monkeypatch):
    root = tmp_path / "install"
    for name in ("data", "logs", "runtime", "uploads", "themes", "backups", "exports"):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / "data" / "devlog.sqlite3").write_bytes(b"")
    return _Install(root, monkeypatch)


def _write_metadata(paths: RuntimePaths, mode: InstallMode, version: str = "1.0.0") -> None:
    paths.installation_metadata.path.parent.mkdir(parents=True, exist_ok=True)
    paths.installation_metadata.path.write_text(
        json.dumps({"mode": mode.value, "version": version}),
        encoding="utf-8",
    )


def _kill_stub(monkeypatch, alive: set[int]) -> None:
    def _kill(pid, sig):
        if pid not in alive:
            raise ProcessLookupError(pid)

    monkeypatch.setattr(os, "kill", _kill)


class _FakeRedis:
    def __init__(self, *, db: int = 3, value: str | None = "1", version: str = "7.2.4"):
        self._db = db
        self._value = value
        self._version = version
        self.connection_pool = SimpleNamespace(connection_kwargs={"db": db})

    def ping(self):
        return True

    def info(self, section=None):
        return {"redis_version": self._version}

    def keys(self, pattern):
        return ["celery-task-1"]

    def select(self, db):
        return True

    def set(self, key, value, ex=None):
        return True

    def get(self, key):
        return self._value

    def delete(self, key):
        return 1


def _patch_redis(monkeypatch, client=None, error: Exception | None = None) -> None:
    import redis as redis_lib

    def _from_url(url, **kwargs):
        if error is not None:
            raise error
        return client

    monkeypatch.setattr(redis_lib.Redis, "from_url", staticmethod(_from_url))


def _patch_boto3(monkeypatch, head_error: Exception | None = None) -> None:
    exceptions = types.ModuleType("botocore.exceptions")
    exceptions.NoCredentialsError = _FakeNoCredentialsError
    exceptions.ClientError = _FakeClientError

    botocore = types.ModuleType("botocore")
    botocore.exceptions = exceptions

    boto3 = types.ModuleType("boto3")

    class _Client:
        def head_bucket(self, Bucket):
            if head_error is not None:
                raise head_error
            return {}

    boto3.client = lambda service, **kwargs: _Client()

    monkeypatch.setitem(sys.modules, "boto3", boto3)
    monkeypatch.setitem(sys.modules, "botocore", botocore)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", exceptions)


def _patch_proc(
    monkeypatch,
    *,
    cgroup: str | None = None,
    uid_map: str | None = None,
    cgroup_error: bool = False,
    uid_map_error: bool = False,
) -> None:
    real_exists = Path.exists
    real_read_text = Path.read_text

    def fake_exists(self):
        if str(self) == "/proc/self/cgroup":
            return cgroup is not None
        if str(self) == "/proc/1/uid_map":
            return uid_map is not None
        return real_exists(self)

    def fake_read_text(self, *args, **kwargs):
        if str(self) == "/proc/self/cgroup":
            if cgroup_error:
                raise OSError("unreadable")
            return cgroup
        if str(self) == "/proc/1/uid_map":
            if uid_map_error:
                raise OSError("unreadable")
            return uid_map
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "read_text", fake_read_text)


# ---------------------------------------------------------------------------
# Release symlink
# ---------------------------------------------------------------------------


class TestReleaseSymlink:
    def test_skipped_outside_system_and_user_modes(self, app, db, install):
        install.use_mode(InstallMode.DEVELOPMENT)
        with app.app_context():
            result = run_doctor(check_ids=["install.release_symlink"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert "mode=development" in result.checks[0].summary

    def test_skipped_when_paths_are_unavailable(self, app, db, install):
        install.use_mode(InstallMode.SYSTEM)
        install.break_paths()
        with app.app_context():
            result = run_doctor(check_ids=["install.release_symlink"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Paths unavailable"

    def test_warns_when_release_directory_is_not_configured(self, app, db, install):
        install.use_mode(InstallMode.SYSTEM)
        with app.app_context():
            result = run_doctor(check_ids=["install.release_symlink"])
        assert result.checks[0].status == CheckStatus.WARN
        assert result.checks[0].summary == "Release directory not configured"
        assert result.checks[0].remediation

    def test_warns_when_release_directory_is_missing(self, app, db, install):
        install.use_mode(InstallMode.SYSTEM)
        install.use_paths(
            _install_paths(install.root, release=install.root / "releases" / "current")
        )
        with app.app_context():
            result = run_doctor(check_ids=["install.release_symlink"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "does not exist" in result.checks[0].summary

    def test_fails_when_symlink_target_is_missing(self, app, db, install, monkeypatch):
        release = install.root / "releases" / "current"
        release.parent.mkdir(parents=True, exist_ok=True)
        release.symlink_to(install.root / "releases" / "gone")
        install.use_mode(InstallMode.SYSTEM)
        install.use_paths(_install_paths(install.root, release=release))

        real_exists = Path.exists

        def fake_exists(self):
            if self == release:
                return True
            return real_exists(self)

        monkeypatch.setattr(Path, "exists", fake_exists)
        with app.app_context():
            result = run_doctor(check_ids=["install.release_symlink"])
        assert result.checks[0].status == CheckStatus.FAIL
        assert "missing target" in result.checks[0].summary

    def test_passes_for_a_valid_symlink(self, app, db, install):
        target = install.root / "releases" / "v1"
        target.mkdir(parents=True)
        release = install.root / "releases" / "current"
        release.parent.mkdir(parents=True, exist_ok=True)
        release.symlink_to(target)
        install.use_mode(InstallMode.SYSTEM)
        install.use_paths(_install_paths(install.root, release=release))
        with app.app_context():
            result = run_doctor(check_ids=["install.release_symlink"])
        assert result.checks[0].status == CheckStatus.PASS
        assert "Release symlink valid" in result.checks[0].summary

    def test_passes_for_a_plain_release_directory(self, app, db, install):
        release = install.root / "releases" / "current"
        release.mkdir(parents=True)
        install.use_mode(InstallMode.SYSTEM)
        install.use_paths(_install_paths(install.root, release=release))
        with app.app_context():
            result = run_doctor(check_ids=["install.release_symlink"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "Release directory exists (not a symlink)"


# ---------------------------------------------------------------------------
# Deprecated configuration keys
# ---------------------------------------------------------------------------


class TestDeprecatedKeys:
    def test_skipped_when_config_is_unavailable(self, app, db, install):
        install.break_config()
        with app.app_context():
            result = run_doctor(check_ids=["install.deprecated_keys"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Config unavailable"

    def test_skipped_when_config_file_is_absent(self, app, db, install, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with app.app_context():
            result = run_doctor(check_ids=["install.deprecated_keys"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "config.toml not found on disk"

    def test_skipped_when_config_file_is_unparseable(self, app, db, install, tmp_path, monkeypatch):
        install.use_config(_make_config())
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.toml").write_text("this is [not valid toml", encoding="utf-8")
        with app.app_context():
            result = run_doctor(check_ids=["install.deprecated_keys"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "config.toml not parseable"

    def test_warns_about_unknown_keys(self, app, db, install, tmp_path, monkeypatch):
        install.use_config(_make_config())
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.toml").write_text('[legacy]\nfoo = "bar"\n', encoding="utf-8")
        with app.app_context():
            result = run_doctor(check_ids=["install.deprecated_keys"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "unknown config key" in result.checks[0].summary
        assert "legacy" in result.checks[0].summary

    def test_passes_for_known_keys(self, app, db, install, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.toml").write_text('[app]\ntitle = "DevLog"\n', encoding="utf-8")
        with app.app_context():
            result = run_doctor(check_ids=["install.deprecated_keys"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "No unknown config keys detected"


# ---------------------------------------------------------------------------
# Stale installation metadata
# ---------------------------------------------------------------------------


class TestStaleMetadata:
    def test_skipped_when_paths_are_unavailable(self, app, db, install):
        install.break_paths()
        with app.app_context():
            result = run_doctor(check_ids=["install.stale_metadata"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Paths unavailable"

    def test_skipped_when_no_metadata_exists(self, app, db, install):
        with app.app_context():
            result = run_doctor(check_ids=["install.stale_metadata"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "No metadata to check for staleness"

    def test_warns_when_metadata_mode_differs_from_detection(self, app, db, install):
        _write_metadata(install.paths, InstallMode.USER)
        install.use_mode(InstallMode.SYSTEM)
        with app.app_context():
            result = run_doctor(check_ids=["install.stale_metadata"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "differs from detected" in result.checks[0].summary

    def test_passes_when_metadata_mode_matches(self, app, db, install):
        _write_metadata(install.paths, InstallMode.DEVELOPMENT)
        with app.app_context():
            result = run_doctor(check_ids=["install.stale_metadata"])
        assert result.checks[0].status == CheckStatus.PASS
        assert "Metadata mode consistent" in result.checks[0].summary


# ---------------------------------------------------------------------------
# Filesystem checks
# ---------------------------------------------------------------------------


class TestSymlinkSafety:
    def test_errors_when_paths_are_unavailable(self, app, db, install):
        install.break_paths()
        with app.app_context():
            result = run_doctor(check_ids=["fs.symlink_safety"])
        assert result.checks[0].status == CheckStatus.ERROR
        assert result.checks[0].summary == "Cannot resolve paths"

    def test_warns_about_symlinks_outside_the_project_root(
        self, app, db, install, monkeypatch, tmp_path_factory
    ):
        monkeypatch.chdir(install.root)
        outside = tmp_path_factory.mktemp("outside")
        shutil.rmtree(install.root / "data")
        (install.root / "data").symlink_to(outside, target_is_directory=True)
        with app.app_context():
            result = run_doctor(check_ids=["fs.symlink_safety"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "symlinks outside project root" in result.checks[0].summary
        assert result.checks[0].details["unsafe_symlinks"][0]["name"] == "data_dir"

    def test_passes_when_symlinks_stay_inside_the_project_root(self, app, db, install, monkeypatch):
        monkeypatch.chdir(install.root)
        target = install.root / "uploads" / "store"
        target.mkdir(parents=True)
        shutil.rmtree(install.root / "themes")
        (install.root / "themes").symlink_to(target, target_is_directory=True)
        with app.app_context():
            result = run_doctor(check_ids=["fs.symlink_safety"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "No unsafe symlinks detected"


class TestDirOwnership:
    def test_skipped_when_paths_are_unavailable(self, app, db, install):
        install.break_paths()
        with app.app_context():
            result = run_doctor(check_ids=["fs.ownership"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Paths unavailable"

    def test_warns_when_a_directory_is_owned_by_another_user(self, app, db, install, monkeypatch):
        monkeypatch.setattr(os, "getuid", lambda: 424242)
        with app.app_context():
            result = run_doctor(check_ids=["fs.ownership"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "owned by different user" in result.checks[0].summary
        assert result.checks[0].details["ownership_issues"]

    def test_ignores_directories_that_cannot_be_statted(self, app, db, install, monkeypatch):
        real_exists = Path.exists
        real_stat = Path.stat
        data_dir = install.paths.data_dir.path

        def fake_exists(self):
            if self == data_dir:
                return True
            return real_exists(self)

        def fake_stat(self, *args, **kwargs):
            if self == data_dir:
                raise OSError("boom")
            return real_stat(self, *args, **kwargs)

        monkeypatch.setattr(Path, "exists", fake_exists)
        monkeypatch.setattr(Path, "stat", fake_stat)
        with app.app_context():
            result = run_doctor(check_ids=["fs.ownership"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "Directory ownership OK"

    def test_passes_when_every_directory_matches_the_service_account(self, app, db, install):
        with app.app_context():
            result = run_doctor(check_ids=["fs.ownership"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "Directory ownership OK"

    def test_ignores_directories_that_do_not_exist(self, app, db, install):
        install.paths.runtime_dir.path.rmdir()
        with app.app_context():
            result = run_doctor(check_ids=["fs.ownership"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "Directory ownership OK"


class TestDirWritable:
    def test_skipped_when_paths_are_unavailable(self, app, db, install):
        install.break_paths()
        with app.app_context():
            result = run_doctor(check_ids=["fs.writable"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Paths unavailable"

    def test_passes_when_every_directory_is_writable(self, app, db, install):
        with app.app_context():
            result = run_doctor(check_ids=["fs.writable"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "All runtime directories are writable"

    def test_ignores_directories_that_do_not_exist(self, app, db, install):
        install.paths.exports_dir.path.rmdir()
        with app.app_context():
            result = run_doctor(check_ids=["fs.writable"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "All runtime directories are writable"

    def test_fails_when_a_directory_is_not_writable(self, app, db, install, monkeypatch):
        real_access = os.access

        def fake_access(path, mode, **kwargs):
            if Path(path) == install.paths.backups_dir.path:
                return False
            return real_access(path, mode, **kwargs)

        monkeypatch.setattr(os, "access", fake_access)
        with app.app_context():
            result = run_doctor(check_ids=["fs.writable"])
        assert result.checks[0].status == CheckStatus.FAIL
        assert result.checks[0].details["not_writable"] == ["backups_dir"]

    def test_uses_the_service_account_when_one_is_known(self, app, db, install, monkeypatch):
        monkeypatch.setattr(doctor_mod, "_service_account_ids", lambda: (os.getuid(), os.getgid()))
        backups = install.paths.backups_dir.path
        backups.chmod(0o500)
        try:
            with app.app_context():
                result = run_doctor(check_ids=["fs.writable"])
        finally:
            backups.chmod(0o755)
        assert result.checks[0].status == CheckStatus.FAIL
        assert result.checks[0].details["not_writable"] == ["backups_dir"]


class TestWritableBy:
    def test_missing_path_is_not_writable(self, tmp_path):
        assert _writable_by(tmp_path / "absent", os.getuid(), os.getgid()) is False

    def test_owner_write_bit_is_honoured(self, tmp_path):
        target = tmp_path / "owner"
        target.mkdir()
        target.chmod(0o700)
        assert _writable_by(target, os.getuid(), os.getgid()) is True

    def test_group_write_bit_is_honoured(self, tmp_path):
        target = tmp_path / "group"
        target.mkdir()
        target.chmod(0o070)
        assert _writable_by(target, os.getuid() + 1, os.getgid()) is True

    def test_other_write_bit_is_honoured(self, tmp_path):
        target = tmp_path / "other"
        target.mkdir()
        target.chmod(0o007)
        assert _writable_by(target, os.getuid() + 1, os.getgid() + 1) is True

    def test_a_read_only_directory_is_not_writable(self, tmp_path):
        target = tmp_path / "readonly"
        target.mkdir()
        target.chmod(0o500)
        assert _writable_by(target, os.getuid(), os.getgid()) is False


class TestFsType:
    def test_skipped_when_paths_are_unavailable(self, app, db, install):
        install.break_paths()
        with app.app_context():
            result = run_doctor(check_ids=["fs.type"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Paths unavailable"

    def test_skipped_for_non_sqlite_backends(self, app, db, install, monkeypatch):
        monkeypatch.setattr(doctor_mod, "_is_sqlite", lambda: False)
        with app.app_context():
            result = run_doctor(check_ids=["fs.type"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert "not SQLite" in result.checks[0].summary

    def test_skipped_when_the_database_file_is_missing(self, app, db, install, monkeypatch):
        database_path = install.paths.database.path
        real_exists = Path.exists
        monkeypatch.setattr(
            Path,
            "exists",
            lambda path: False if path == database_path else real_exists(path),
        )
        with app.app_context():
            result = run_doctor(check_ids=["fs.type"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert "Database file not found" in result.checks[0].summary

    def test_warns_about_filesystems_with_weak_locking(self, app, db, install, monkeypatch):
        monkeypatch.setattr(os, "statvfs", lambda path: SimpleNamespace(f_type=0x65735546))
        with app.app_context():
            result = run_doctor(check_ids=["fs.type"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "FUSE" in result.checks[0].summary
        assert result.checks[0].remediation

    def test_passes_for_a_known_filesystem(self, app, db, install, monkeypatch):
        monkeypatch.setattr(os, "statvfs", lambda path: SimpleNamespace(f_type=0xEF53))
        with app.app_context():
            result = run_doctor(check_ids=["fs.type"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].details["fs_type"] == "ext4"

    def test_skipped_when_the_filesystem_type_cannot_be_read(self, app, db, install, monkeypatch):
        def _boom_statvfs(path):
            raise OSError("boom")

        monkeypatch.setattr(os, "statvfs", _boom_statvfs)
        with app.app_context():
            result = run_doctor(check_ids=["fs.type"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Could not determine filesystem type"


class TestDockerUid:
    def test_skipped_without_a_cgroup(self, app, db, install, monkeypatch):
        _patch_proc(monkeypatch)
        with app.app_context():
            result = run_doctor(check_ids=["fs.docker_uid"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Not in Docker (no cgroup)"

    def test_skipped_outside_a_container(self, app, db, install, monkeypatch):
        _patch_proc(monkeypatch, cgroup="12:devices:/user.slice\n")
        with app.app_context():
            result = run_doctor(check_ids=["fs.docker_uid"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Not in Docker container"

    def test_skipped_when_the_cgroup_cannot_be_read(self, app, db, install, monkeypatch):
        _patch_proc(monkeypatch, cgroup="docker", cgroup_error=True)
        with app.app_context():
            result = run_doctor(check_ids=["fs.docker_uid"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Could not read cgroup"

    def test_skipped_when_the_uid_mapping_is_unknown(self, app, db, install, monkeypatch):
        _patch_proc(monkeypatch, cgroup="12:devices:/docker/abc\n")
        with app.app_context():
            result = run_doctor(check_ids=["fs.docker_uid"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Cannot determine host UID mapping"

    def test_skipped_when_the_uid_mapping_cannot_be_read(self, app, db, install, monkeypatch):
        _patch_proc(
            monkeypatch,
            cgroup="12:devices:/docker/abc\n",
            uid_map="0 0 4294967295\n",
            uid_map_error=True,
        )
        with app.app_context():
            result = run_doctor(check_ids=["fs.docker_uid"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Could not read UID mapping"

    def test_passes_inside_a_container(self, app, db, install, monkeypatch):
        _patch_proc(
            monkeypatch,
            cgroup="12:devices:/docker/abc\n",
            uid_map="0 0 4294967295\n",
        )
        with app.app_context():
            result = run_doctor(check_ids=["fs.docker_uid"])
        assert result.checks[0].status == CheckStatus.PASS
        assert "Docker UID mapping" in result.checks[0].summary


# ---------------------------------------------------------------------------
# Stale PID files
# ---------------------------------------------------------------------------


class TestStalePid:
    def test_skipped_when_paths_are_unavailable(self, app, db, install):
        install.break_paths()
        with app.app_context():
            result = run_doctor(check_ids=["deploy.pid"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Paths unavailable"

    def test_skipped_when_the_runtime_directory_is_missing(self, app, db, install):
        install.paths.runtime_dir.path.rmdir()
        with app.app_context():
            result = run_doctor(check_ids=["deploy.pid"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Runtime directory does not exist"

    def test_passes_without_pid_files(self, app, db, install):
        with app.app_context():
            result = run_doctor(check_ids=["deploy.pid"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "No PID files in runtime directory"

    def test_passes_when_every_pid_is_alive(self, app, db, install, monkeypatch):
        (install.paths.runtime_dir.path / "devlog.pid").write_text(
            str(os.getpid()), encoding="utf-8"
        )
        _kill_stub(monkeypatch, {os.getpid()})
        with app.app_context():
            result = run_doctor(check_ids=["deploy.pid"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "All PID files reference running processes"

    def test_ignores_pid_files_that_are_not_numbers(self, app, db, install):
        (install.paths.runtime_dir.path / "devlog.pid").write_text("not-a-pid", encoding="utf-8")
        with app.app_context():
            result = run_doctor(check_ids=["deploy.pid"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "All PID files reference running processes"

    def test_warns_about_stale_pid_files(self, app, db, install, monkeypatch):
        (install.paths.runtime_dir.path / "devlog.pid").write_text("4242", encoding="utf-8")
        _kill_stub(monkeypatch, set())
        with app.app_context():
            result = run_doctor(check_ids=["deploy.pid"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "1 stale PID file(s) found" in result.checks[0].summary
        assert result.checks[0].details["stale_pids"][0]["pid"] == 4242
        assert result.checks[0].safe_fix_id == "cleanup_stale_pid"


class TestCleanupStalePidFix:
    def test_reports_when_paths_are_unavailable(self, app, db, install):
        install.break_paths()
        _set_ctx(DoctorContext("development", "1.0.0"))
        ok, detail = _fix_cleanup_stale_pid(_result())
        assert ok is False
        assert detail == "Cannot resolve paths"

    def test_reports_a_missing_runtime_directory(self, app, db, install):
        install.paths.runtime_dir.path.rmdir()
        _set_ctx(DoctorContext("development", "1.0.0"))
        ok, detail = _fix_cleanup_stale_pid(_result())
        assert ok is False
        assert detail == "Runtime directory does not exist"

    def test_removes_stale_pid_files(self, app, db, install, monkeypatch):
        stale = install.paths.runtime_dir.path / "stale.pid"
        stale.write_text("4242", encoding="utf-8")
        live = install.paths.runtime_dir.path / "live.pid"
        live.write_text(str(os.getpid()), encoding="utf-8")
        _kill_stub(monkeypatch, {os.getpid()})
        _set_ctx(DoctorContext("development", "1.0.0"))
        ok, detail = _fix_cleanup_stale_pid(_result())
        assert ok is True
        assert detail == "Removed 1 stale PID file(s)"
        assert not stale.exists()
        assert live.exists()

    def test_reports_when_nothing_is_stale(self, app, db, install):
        (install.paths.runtime_dir.path / "bad.pid").write_text("nope", encoding="utf-8")
        _set_ctx(DoctorContext("development", "1.0.0"))
        ok, detail = _fix_cleanup_stale_pid(_result())
        assert ok is True
        assert detail == "No stale PID files found"

    def test_reports_a_failure(self, app, db, install, monkeypatch):
        def _boom_glob(self, pattern):
            raise OSError("boom")

        monkeypatch.setattr(Path, "glob", _boom_glob)
        _set_ctx(DoctorContext("development", "1.0.0"))
        ok, detail = _fix_cleanup_stale_pid(_result())
        assert ok is False
        assert "Failed to clean up PID files" in detail


# ---------------------------------------------------------------------------
# Safe fixes
# ---------------------------------------------------------------------------


class TestApplySafeFixes:
    def test_skips_passing_and_unfixable_results(self, app, db):
        results = [
            _result(status=CheckStatus.PASS, safe_fix_id="create_missing_dirs"),
            _result(status=CheckStatus.WARN, safe_fix_id=None),
            _result(status=CheckStatus.WARN, safe_fix_id="unknown_fix"),
        ]
        assert _apply_safe_fixes(results) == []

    def test_skips_a_fix_without_a_runner(self, app, db):
        results = [_result(status=CheckStatus.WARN, safe_fix_id="rebuild_fts")]
        runner = doctor_mod._SAFE_FIX_RUNNERS.pop("rebuild_fts")
        try:
            assert _apply_safe_fixes(results) == []
        finally:
            doctor_mod._SAFE_FIX_RUNNERS["rebuild_fts"] = runner

    def test_applies_a_registered_fix(self, app, db):
        results = [_result(status=CheckStatus.WARN, safe_fix_id="cleanup_stale_pid")]
        applied = _apply_safe_fixes(results)
        assert len(applied) == 1
        assert applied[0]["fix_id"] == "cleanup_stale_pid"
        assert applied[0]["check_id"] == "check.one"
        assert "ok" in applied[0]

    def test_records_a_failing_fix(self, app, db, monkeypatch):
        def _explode(cr):
            raise RuntimeError("boom")

        monkeypatch.setitem(doctor_mod._SAFE_FIX_RUNNERS, "cleanup_stale_pid", _explode)
        results = [_result(status=CheckStatus.WARN, safe_fix_id="cleanup_stale_pid")]
        applied = _apply_safe_fixes(results)
        assert applied[0]["ok"] is False
        assert "RuntimeError" in applied[0]["detail"]

    def test_run_doctor_applies_fixes_when_not_a_dry_run(self, app, db, install, monkeypatch):
        applied: list[str] = []

        def _record(cr):
            applied.append(cr.check_id)
            return True, "done"

        monkeypatch.setitem(doctor_mod._SAFE_FIX_RUNNERS, "cleanup_stale_pid", _record)
        (install.paths.runtime_dir.path / "stale.pid").write_text("4242", encoding="utf-8")
        _kill_stub(monkeypatch, set())
        with app.app_context():
            result = run_doctor(check_ids=["deploy.pid"], fix_safe=True, dry_run=False)
        assert applied == ["deploy.pid"]
        assert result.safe_fix_plan == []


# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------


class TestRedisAuth:
    def test_skipped_when_config_is_unavailable(self, app, db, install):
        install.break_config()
        with app.app_context():
            result = run_doctor(check_ids=["dep.redis_auth"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Config unavailable"

    def test_skipped_when_redis_is_not_configured(self, app, db, install):
        install.use_config(_make_config(redis=replace(_redis_section(), url="")))
        with app.app_context():
            result = run_doctor(check_ids=["dep.redis_auth"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Redis not configured"

    def test_skipped_when_the_redis_client_is_missing(self, app, db, install, monkeypatch):
        monkeypatch.setitem(sys.modules, "redis", None)
        with app.app_context():
            result = run_doctor(check_ids=["dep.redis_auth"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Redis client not installed"

    def test_passes_when_redis_accepts_the_credentials(self, app, db, install, monkeypatch):
        _patch_redis(monkeypatch, client=_FakeRedis(version="7.4.1"))
        with app.app_context():
            result = run_doctor(check_ids=["dep.redis_auth"])
        assert result.checks[0].status == CheckStatus.PASS
        assert "7.4.1" in result.checks[0].summary
        assert result.checks[0].details["redis_version"] == "7.4.1"

    def test_fails_when_redis_rejects_the_credentials(self, app, db, install, monkeypatch):
        import redis as redis_lib

        _patch_redis(monkeypatch, error=redis_lib.AuthenticationError("bad password"))
        with app.app_context():
            result = run_doctor(check_ids=["dep.redis_auth"])
        assert result.checks[0].status == CheckStatus.FAIL
        assert result.checks[0].summary == "Redis authentication failed"

    def test_fails_when_the_error_mentions_authentication(self, app, db, install, monkeypatch):
        _patch_redis(monkeypatch, error=RuntimeError("Authentication required"))
        with app.app_context():
            result = run_doctor(check_ids=["dep.redis_auth"])
        assert result.checks[0].status == CheckStatus.FAIL
        assert result.checks[0].summary == "Redis authentication failed"

    def test_warns_on_an_unrelated_error(self, app, db, install, monkeypatch):
        _patch_redis(monkeypatch, error=RuntimeError("connection reset"))
        with app.app_context():
            result = run_doctor(check_ids=["dep.redis_auth"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "Redis auth check failed" in result.checks[0].summary


class TestRedisDb:
    def test_skipped_when_config_is_unavailable(self, app, db, install):
        install.break_config()
        with app.app_context():
            result = run_doctor(check_ids=["dep.redis_db"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Config unavailable"

    def test_skipped_when_redis_is_not_configured(self, app, db, install):
        install.use_config(_make_config(redis=replace(_redis_section(), url="")))
        with app.app_context():
            result = run_doctor(check_ids=["dep.redis_db"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Redis not configured"

    def test_skipped_when_the_redis_client_is_missing(self, app, db, install, monkeypatch):
        monkeypatch.setitem(sys.modules, "redis", None)
        with app.app_context():
            result = run_doctor(check_ids=["dep.redis_db"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Redis client not installed"

    def test_passes_when_the_write_read_round_trip_succeeds(self, app, db, install, monkeypatch):
        _patch_redis(monkeypatch, client=_FakeRedis(db=4, value="1", version="7.4.1"))
        with app.app_context():
            result = run_doctor(check_ids=["dep.redis_db"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].details["db"] == 4
        assert result.checks[0].details["redis_version"] == "7.4.1"

    def test_warns_when_the_round_trip_returns_nothing(self, app, db, install, monkeypatch):
        _patch_redis(monkeypatch, client=_FakeRedis(db=2, value=None))
        with app.app_context():
            result = run_doctor(check_ids=["dep.redis_db"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "write/read test failed" in result.checks[0].summary

    def test_warns_on_an_unrelated_error(self, app, db, install, monkeypatch):
        _patch_redis(monkeypatch, error=RuntimeError("boom"))
        with app.app_context():
            result = run_doctor(check_ids=["dep.redis_db"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "Redis DB check failed" in result.checks[0].summary


class TestCeleryWorkers:
    def test_skipped_when_config_is_unavailable(self, app, db, install):
        install.break_config()
        with app.app_context():
            result = run_doctor(check_ids=["dep.celery_workers"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Config unavailable"

    def test_skipped_when_the_broker_is_not_configured(self, app, db, install):
        install.use_config(_make_config(celery=replace(_celery_section(), broker_url="")))
        with app.app_context():
            result = run_doctor(check_ids=["dep.celery_workers"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Celery broker not configured"

    def test_skipped_when_the_redis_client_is_missing(self, app, db, install, monkeypatch):
        monkeypatch.setitem(sys.modules, "redis", None)
        with app.app_context():
            result = run_doctor(check_ids=["dep.celery_workers"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Redis client not installed"

    def test_skipped_for_a_non_redis_broker(self, app, db, install):
        install.use_config(
            _make_config(celery=replace(_celery_section(), broker_url="amqp://guest@localhost//"))
        )
        with app.app_context():
            result = run_doctor(check_ids=["dep.celery_workers"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert "only supports Redis broker" in result.checks[0].summary

    def test_passes_when_the_broker_is_reachable(self, app, db, install, monkeypatch):
        _patch_redis(monkeypatch, client=_FakeRedis())
        with app.app_context():
            result = run_doctor(check_ids=["dep.celery_workers"])
        assert result.checks[0].status == CheckStatus.PASS
        assert "1 celery key(s)" in result.checks[0].summary

    def test_warns_when_the_broker_keys_cannot_be_listed(self, app, db, install, monkeypatch):
        class _BrokenKeys(_FakeRedis):
            def keys(self, pattern):
                raise RuntimeError("boom")

        _patch_redis(monkeypatch, client=_BrokenKeys())
        with app.app_context():
            result = run_doctor(check_ids=["dep.celery_workers"])
        assert result.checks[0].status == CheckStatus.WARN
        assert result.checks[0].summary == "Cannot inspect Celery broker keys"

    def test_errors_when_the_client_cannot_be_built(self, app, db, install, monkeypatch):
        _patch_redis(monkeypatch, error=RuntimeError("boom"))
        with app.app_context():
            result = run_doctor(check_ids=["dep.celery_workers"])
        assert result.checks[0].status == CheckStatus.ERROR
        assert result.checks[0].summary.startswith("Check raised")


class TestSchedulerStale:
    def test_skipped_when_config_is_unavailable(self, app, db, install):
        install.break_config()
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_stale"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Config unavailable"

    def test_skipped_when_the_scheduler_is_disabled(self, app, db, install):
        install.use_config(_make_config(scheduler=replace(_scheduler_section(), enabled=False)))
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_stale"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Scheduler disabled in config"

    def test_skipped_when_paths_are_unavailable(self, app, db, install):
        install.use_config(_make_config(scheduler=replace(_scheduler_section(), enabled=True)))
        install.break_paths()
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_stale"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Paths unavailable"

    def test_warns_about_an_old_lock_file(self, app, db, install):
        install.use_config(_make_config(scheduler=replace(_scheduler_section(), enabled=True)))
        lock = install.paths.runtime_dir.path / "scheduler.lock"
        lock.write_text("{}", encoding="utf-8")
        old = time.time() - 48 * 3600
        os.utime(lock, (old, old))
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_stale"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "may be stale" in result.checks[0].summary
        assert result.checks[0].details["lock_age_hours"] > 24

    def test_passes_for_a_fresh_lock_file(self, app, db, install):
        install.use_config(_make_config(scheduler=replace(_scheduler_section(), enabled=True)))
        (install.paths.runtime_dir.path / "scheduler.lock").write_text("{}", encoding="utf-8")
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_stale"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "Scheduler lock file OK or absent"

    def test_passes_without_a_lock_file(self, app, db, install):
        install.use_config(_make_config(scheduler=replace(_scheduler_section(), enabled=True)))
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_stale"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "Scheduler lock file OK or absent"


class TestSchedulerOwner:
    def test_skipped_when_paths_are_unavailable(self, app, db, install):
        install.break_paths()
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_owner"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Paths unavailable"

    def test_passes_without_a_lock_file(self, app, db, install):
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_owner"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "No scheduler lock file (single owner assumed)"

    def test_passes_when_the_lock_owner_is_alive(self, app, db, install, monkeypatch):
        lock = install.paths.runtime_dir.path / "scheduler.lock"
        lock.write_text(json.dumps({"pid": os.getpid(), "hostname": "host-a"}), encoding="utf-8")
        _kill_stub(monkeypatch, {os.getpid()})
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_owner"])
        assert result.checks[0].status == CheckStatus.PASS
        assert "Scheduler owned by PID" in result.checks[0].summary
        assert result.checks[0].details["hostname"] == "host-a"

    def test_warns_when_the_lock_owner_is_dead(self, app, db, install, monkeypatch):
        lock = install.paths.runtime_dir.path / "scheduler.lock"
        lock.write_text(json.dumps({"pid": 4242, "hostname": "host-a"}), encoding="utf-8")
        _kill_stub(monkeypatch, set())
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_owner"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "dead PID 4242" in result.checks[0].summary

    def test_passes_for_an_unreadable_lock_file(self, app, db, install):
        lock = install.paths.runtime_dir.path / "scheduler.lock"
        lock.write_text("not json", encoding="utf-8")
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_owner"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "Scheduler lock file present"

    def test_passes_for_a_lock_file_without_a_pid(self, app, db, install):
        lock = install.paths.runtime_dir.path / "scheduler.lock"
        lock.write_text(json.dumps({"hostname": "host-a"}), encoding="utf-8")
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_owner"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "Scheduler lock file present"


class TestSchedulerRuns:
    def test_warns_when_the_scheduler_is_not_running(self, app, db, install, monkeypatch):
        import app.scheduler as sched_mod

        monkeypatch.setattr(sched_mod, "get_scheduler_status", lambda: False)
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_runs"])
        assert result.checks[0].status == CheckStatus.WARN
        assert result.checks[0].summary == "Scheduler is not running"

    def test_passes_without_a_scheduler_instance(self, app, db, install, monkeypatch):
        import app.scheduler as sched_mod

        monkeypatch.setattr(sched_mod, "get_scheduler_status", lambda: True)
        monkeypatch.setattr(sched_mod, "_scheduler", None)
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_runs"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "Scheduler is running"

    def test_reports_the_scheduled_jobs(self, app, db, install, monkeypatch):
        import app.scheduler as sched_mod

        job = SimpleNamespace(id="daily-backup", next_run_time=None)
        scheduler = SimpleNamespace(get_jobs=lambda: [job])
        monkeypatch.setattr(sched_mod, "get_scheduler_status", lambda: True)
        monkeypatch.setattr(sched_mod, "_scheduler", scheduler)
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_runs"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].details["job_count"] == 1
        assert result.checks[0].details["jobs"][0]["id"] == "daily-backup"

    def test_passes_when_the_job_list_cannot_be_read(self, app, db, install, monkeypatch):
        import app.scheduler as sched_mod

        def _boom():
            raise RuntimeError("boom")

        scheduler = SimpleNamespace(get_jobs=_boom)
        monkeypatch.setattr(sched_mod, "get_scheduler_status", lambda: True)
        monkeypatch.setattr(sched_mod, "_scheduler", scheduler)
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_runs"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "Scheduler is running"

    def test_skipped_when_the_status_is_not_determinable(self, app, db, install, monkeypatch):
        import app.scheduler as sched_mod

        def _boom():
            raise RuntimeError("boom")

        monkeypatch.setattr(sched_mod, "get_scheduler_status", _boom)
        with app.app_context():
            result = run_doctor(check_ids=["dep.scheduler_runs"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Scheduler status not determinable"


class TestSmtpConnect:
    def test_skipped_when_config_is_unavailable(self, app, db, install):
        install.break_config()
        with app.app_context():
            result = run_doctor(check_ids=["dep.smtp_connect"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Config unavailable"

    def test_skipped_when_smtp_is_not_configured(self, app, db, install):
        install.use_config(_make_config(email=replace(_email_section(), smtp_host="")))
        with app.app_context():
            result = run_doctor(check_ids=["dep.smtp_connect"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "SMTP not configured"

    def test_passes_when_the_host_accepts_a_connection(self, app, db, install, monkeypatch):
        install.use_config(_make_config(email=replace(_email_section(), smtp_host="smtp.test")))
        monkeypatch.setattr(
            socket,
            "create_connection",
            lambda *a, **k: SimpleNamespace(close=lambda: None),
        )
        with app.app_context():
            result = run_doctor(check_ids=["dep.smtp_connect"])
        assert result.checks[0].status == CheckStatus.PASS
        assert "succeeded" in result.checks[0].summary

    def test_warns_when_the_connection_times_out(self, app, db, install, monkeypatch):
        install.use_config(_make_config(email=replace(_email_section(), smtp_host="smtp.test")))

        def _timeout(*args, **kwargs):
            raise socket.timeout("timed out")

        monkeypatch.setattr(socket, "create_connection", _timeout)
        with app.app_context():
            result = run_doctor(check_ids=["dep.smtp_connect"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "timed out" in result.checks[0].summary

    def test_warns_when_the_connection_is_refused(self, app, db, install, monkeypatch):
        install.use_config(_make_config(email=replace(_email_section(), smtp_host="smtp.test")))

        def _refused(*args, **kwargs):
            raise ConnectionRefusedError("connection refused")

        monkeypatch.setattr(socket, "create_connection", _refused)
        with app.app_context():
            result = run_doctor(check_ids=["dep.smtp_connect"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "connection failed" in result.checks[0].summary.lower()


class TestStorageBackend:
    def test_skipped_when_config_is_unavailable(self, app, db, install):
        install.break_config()
        with app.app_context():
            result = run_doctor(check_ids=["dep.storage"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Config unavailable"

    def test_passes_for_the_local_backend(self, app, db, install):
        install.use_config(_make_config(storage=replace(_storage_section(), backend="local")))
        with app.app_context():
            result = run_doctor(check_ids=["dep.storage"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].details["backend"] == "local"

    def test_fails_when_the_s3_backend_is_incomplete(self, app, db, install):
        install.use_config(
            _make_config(
                storage=replace(
                    _storage_section(),
                    backend="s3",
                    s3_bucket="",
                    s3_access_key="",
                    s3_secret_key="",
                )
            )
        )
        with app.app_context():
            result = run_doctor(check_ids=["dep.storage"])
        assert result.checks[0].status == CheckStatus.FAIL
        assert result.checks[0].details["missing_vars"] == [
            "S3_BUCKET",
            "S3_ACCESS_KEY",
            "S3_SECRET_KEY",
        ]
        assert result.checks[0].remediation

    def test_passes_when_the_s3_backend_is_complete(self, app, db, install):
        install.use_config(
            _make_config(
                storage=replace(
                    _storage_section(),
                    backend="s3",
                    s3_bucket="assets",
                    s3_access_key="x" * 8,
                    s3_secret_key="x" * 8,
                )
            )
        )
        with app.app_context():
            result = run_doctor(check_ids=["dep.storage"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].details["backend"] == "s3"


class TestStorageS3Probe:
    def test_skipped_when_config_is_unavailable(self, app, db, install):
        install.break_config()
        with app.app_context():
            result = run_doctor(check_ids=["dep.storage_s3_probe"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Config unavailable"

    def test_skipped_for_a_non_s3_backend(self, app, db, install):
        install.use_config(_make_config(storage=replace(_storage_section(), backend="local")))
        with app.app_context():
            result = run_doctor(check_ids=["dep.storage_s3_probe"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "S3 backend not configured"

    def test_skipped_when_boto3_is_missing(self, app, db, install, monkeypatch):
        install.use_config(_s3_config())
        monkeypatch.setitem(sys.modules, "boto3", None)
        with app.app_context():
            result = run_doctor(check_ids=["dep.storage_s3_probe"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "boto3 not installed"

    def test_passes_when_the_bucket_is_reachable(self, app, db, install, monkeypatch):
        install.use_config(_s3_config())
        _patch_boto3(monkeypatch)
        with app.app_context():
            result = run_doctor(check_ids=["dep.storage_s3_probe"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].details["bucket"] == "assets"

    def test_passes_without_a_region_or_endpoint(self, app, db, install, monkeypatch):
        install.use_config(
            _make_config(
                storage=replace(
                    _storage_section(),
                    backend="s3",
                    s3_bucket="assets",
                    s3_access_key="x" * 8,
                    s3_secret_key="x" * 8,
                    s3_region="",
                    s3_endpoint="",
                )
            )
        )
        _patch_boto3(monkeypatch)
        with app.app_context():
            result = run_doctor(check_ids=["dep.storage_s3_probe"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].details["bucket"] == "assets"

    def test_fails_without_credentials(self, app, db, install, monkeypatch):
        install.use_config(_s3_config())
        _patch_boto3(monkeypatch, head_error=_FakeNoCredentialsError())
        with app.app_context():
            result = run_doctor(check_ids=["dep.storage_s3_probe"])
        assert result.checks[0].status == CheckStatus.FAIL
        assert result.checks[0].summary == "S3 credentials not configured"

    def test_warns_when_the_bucket_rejects_the_request(self, app, db, install, monkeypatch):
        install.use_config(_s3_config())
        _patch_boto3(monkeypatch, head_error=_FakeClientError({"Error": {"Code": "404"}}))
        with app.app_context():
            result = run_doctor(check_ids=["dep.storage_s3_probe"])
        assert result.checks[0].status == CheckStatus.WARN
        assert result.checks[0].details["error_code"] == "404"

    def test_warns_on_an_unexpected_error(self, app, db, install, monkeypatch):
        install.use_config(_s3_config())
        _patch_boto3(monkeypatch, head_error=RuntimeError("boom"))
        with app.app_context():
            result = run_doctor(check_ids=["dep.storage_s3_probe"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "S3 probe failed: RuntimeError" in result.checks[0].summary


# ---------------------------------------------------------------------------
# Backup checks
# ---------------------------------------------------------------------------


class TestBackupDirectory:
    def test_errors_when_paths_are_unavailable(self, app, db, install):
        install.break_paths()
        with app.app_context():
            result = run_doctor(check_ids=["backup.readiness"])
        assert result.checks[0].status == CheckStatus.ERROR
        assert result.checks[0].summary == "Cannot resolve paths"

    def test_warns_when_the_backup_directory_is_missing(self, app, db, install):
        install.paths.backups_dir.path.rmdir()
        with app.app_context():
            result = run_doctor(check_ids=["backup.readiness"])
        assert result.checks[0].status == CheckStatus.WARN
        assert result.checks[0].summary == "Backup directory does not exist"
        assert result.checks[0].safe_fix_id == "create_missing_dirs"

    def test_fails_when_the_backup_directory_is_not_writable(self, app, db, install, monkeypatch):
        real_access = os.access

        def fake_access(path, mode, **kwargs):
            if Path(path) == install.paths.backups_dir.path:
                return False
            return real_access(path, mode, **kwargs)

        monkeypatch.setattr(os, "access", fake_access)
        with app.app_context():
            result = run_doctor(check_ids=["backup.readiness"])
        assert result.checks[0].status == CheckStatus.FAIL
        assert result.checks[0].summary == "Backup directory is not writable"

    def test_passes_when_a_backup_is_present(self, app, db, install):
        (install.paths.backups_dir.path / "backup-1.tar.gz").write_text("x", encoding="utf-8")
        with app.app_context():
            result = run_doctor(check_ids=["backup.readiness"])
        assert result.checks[0].status == CheckStatus.PASS
        assert "latest backup" in result.checks[0].summary
        assert result.checks[0].details["backup_count"] == 1

    def test_warns_when_the_backup_directory_is_empty(self, app, db, install):
        with app.app_context():
            result = run_doctor(check_ids=["backup.readiness"])
        assert result.checks[0].status == CheckStatus.WARN
        assert result.checks[0].summary == "Backup directory exists but is empty"


class TestBackupManifest:
    def test_skipped_when_paths_are_unavailable(self, app, db, install):
        install.break_paths()
        with app.app_context():
            result = run_doctor(check_ids=["backup.manifest"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Paths unavailable"

    def test_skipped_when_the_backup_directory_is_missing(self, app, db, install):
        install.paths.backups_dir.path.rmdir()
        with app.app_context():
            result = run_doctor(check_ids=["backup.manifest"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Backup directory does not exist"

    def test_skipped_without_a_manifest(self, app, db, install):
        with app.app_context():
            result = run_doctor(check_ids=["backup.manifest"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "No backup manifest files found"

    def test_warns_when_the_manifest_cannot_be_parsed(self, app, db, install):
        (install.paths.backups_dir.path / "b.manifest.json").write_text(
            "not json", encoding="utf-8"
        )
        with app.app_context():
            result = run_doctor(check_ids=["backup.manifest"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "not parseable" in result.checks[0].summary

    def test_passes_for_a_parseable_manifest(self, app, db, install):
        (install.paths.backups_dir.path / "b.manifest.json").write_text(
            json.dumps({"created_at": "2026-01-01", "files": []}), encoding="utf-8"
        )
        with app.app_context():
            result = run_doctor(check_ids=["backup.manifest"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].details["manifest_file"] == "b.manifest.json"


class TestBackupEncryption:
    def test_skipped_when_config_is_unavailable(self, app, db, install):
        install.break_config()
        with app.app_context():
            result = run_doctor(check_ids=["backup.encryption"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Config unavailable"

    def test_passes_when_no_key_is_configured(self, app, db, install):
        install.use_config(_make_config(backup=replace(_backup_section(), encryption_key="")))
        with app.app_context():
            result = run_doctor(check_ids=["backup.encryption"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].summary == "Backup encryption not configured (no key)"

    def test_passes_when_the_key_is_set_and_cryptography_is_available(self, app, db, install):
        install.use_config(_make_config(backup=replace(_backup_section(), encryption_key="k" * 32)))
        with app.app_context():
            result = run_doctor(check_ids=["backup.encryption"])
        assert result.checks[0].status == CheckStatus.PASS
        assert "cryptography available" in result.checks[0].summary

    def test_warns_when_cryptography_is_missing(self, app, db, install, monkeypatch):
        install.use_config(_make_config(backup=replace(_backup_section(), encryption_key="k" * 32)))
        monkeypatch.setitem(sys.modules, "cryptography", None)
        with app.app_context():
            result = run_doctor(check_ids=["backup.encryption"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "cryptography library not available" in result.checks[0].summary


class TestBackupRetention:
    def test_warns_when_the_value_is_not_an_integer(self, app, db, install, monkeypatch):
        monkeypatch.setenv("BACKUP_KEEP", "many")
        with app.app_context():
            result = run_doctor(check_ids=["backup.retention"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "not a valid integer" in result.checks[0].summary

    def test_warns_when_no_backup_is_kept(self, app, db, install, monkeypatch):
        monkeypatch.setenv("BACKUP_KEEP", "0")
        with app.app_context():
            result = run_doctor(check_ids=["backup.retention"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "no backups will be kept" in result.checks[0].summary

    def test_warns_when_the_retention_is_very_high(self, app, db, install, monkeypatch):
        monkeypatch.setenv("BACKUP_KEEP", "500")
        with app.app_context():
            result = run_doctor(check_ids=["backup.retention"])
        assert result.checks[0].status == CheckStatus.WARN
        assert "very high" in result.checks[0].summary

    def test_passes_for_a_sane_retention(self, app, db, install, monkeypatch):
        monkeypatch.setenv("BACKUP_KEEP", "14")
        with app.app_context():
            result = run_doctor(check_ids=["backup.retention"])
        assert result.checks[0].status == CheckStatus.PASS
        assert "keep 14 backups" in result.checks[0].summary


# ---------------------------------------------------------------------------
# Theme, deployment and engine checks
# ---------------------------------------------------------------------------


class TestExternalThemeDir:
    def test_skipped_when_config_is_unavailable(self, app, db, install):
        install.break_config()
        with app.app_context():
            result = run_doctor(check_ids=["themes.external_dir"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Config unavailable"

    def test_skipped_when_no_directory_is_configured(self, app, db, install):
        install.use_config(_make_config(themes=replace(_themes_section(), external_dir="")))
        with app.app_context():
            result = run_doctor(check_ids=["themes.external_dir"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "No external theme directory configured"

    def test_fails_when_the_directory_is_missing(self, app, db, install):
        install.use_config(
            _make_config(
                themes=replace(_themes_section(), external_dir=str(install.root / "absent"))
            )
        )
        with app.app_context():
            result = run_doctor(check_ids=["themes.external_dir"])
        assert result.checks[0].status == CheckStatus.FAIL
        assert "does not exist" in result.checks[0].summary

    def test_fails_when_the_directory_is_not_readable(self, app, db, install, monkeypatch):
        external = install.root / "external-themes"
        external.mkdir()
        install.use_config(
            _make_config(themes=replace(_themes_section(), external_dir=str(external)))
        )
        real_access = os.access

        def fake_access(path, mode, **kwargs):
            if Path(path) == external:
                return False
            return real_access(path, mode, **kwargs)

        monkeypatch.setattr(os, "access", fake_access)
        with app.app_context():
            result = run_doctor(check_ids=["themes.external_dir"])
        assert result.checks[0].status == CheckStatus.FAIL
        assert "not readable" in result.checks[0].summary

    def test_passes_for_a_readable_directory(self, app, db, install):
        external = install.root / "external-themes"
        external.mkdir()
        (external / "custom.toml").write_text("[theme]\n", encoding="utf-8")
        install.use_config(
            _make_config(themes=replace(_themes_section(), external_dir=str(external)))
        )
        with app.app_context():
            result = run_doctor(check_ids=["themes.external_dir"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].details["theme_count"] == 1


class TestSystemdSyntax:
    def test_skipped_without_unit_files(self, app, db, install, tmp_path, monkeypatch):
        import app.deployment.systemd as systemd_mod

        units = tmp_path / "units"
        units.mkdir()
        monkeypatch.setattr(systemd_mod, "__file__", str(units / "systemd.py"))
        with app.app_context():
            result = run_doctor(check_ids=["deploy.systemd_syntax"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "No systemd unit files found"

    def test_skipped_when_the_deployment_module_is_unavailable(self, app, db, install, monkeypatch):
        import app.deployment as deployment_mod

        monkeypatch.setattr(deployment_mod, "systemd", object())
        with app.app_context():
            result = run_doctor(check_ids=["deploy.systemd_syntax"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Deployment module not available"

    def test_passes_for_a_valid_unit(self, app, db, install, tmp_path, monkeypatch):
        import app.deployment.systemd as systemd_mod

        units = tmp_path / "units"
        units.mkdir()
        (units / "devlog.service").write_text("[Service]\n", encoding="utf-8")
        monkeypatch.setattr(systemd_mod, "__file__", str(units / "systemd.py"))
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **k: SimpleNamespace(returncode=0, stdout="", stderr=""),
        )
        with app.app_context():
            result = run_doctor(check_ids=["deploy.systemd_syntax"])
        assert result.checks[0].status == CheckStatus.PASS
        assert "systemd unit syntax OK" in result.checks[0].summary

    def test_warns_for_a_broken_unit(self, app, db, install, tmp_path, monkeypatch):
        import app.deployment.systemd as systemd_mod

        units = tmp_path / "units"
        units.mkdir()
        (units / "devlog.service").write_text("[Service]\n", encoding="utf-8")
        monkeypatch.setattr(systemd_mod, "__file__", str(units / "systemd.py"))
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="bad unit"),
        )
        with app.app_context():
            result = run_doctor(check_ids=["deploy.systemd_syntax"])
        assert result.checks[0].status == CheckStatus.WARN
        assert result.checks[0].details["stderr"] == "bad unit"

    def test_skipped_when_systemd_analyze_is_missing(self, app, db, install, tmp_path, monkeypatch):
        import app.deployment.systemd as systemd_mod

        units = tmp_path / "units"
        units.mkdir()
        (units / "devlog.service").write_text("[Service]\n", encoding="utf-8")
        monkeypatch.setattr(systemd_mod, "__file__", str(units / "systemd.py"))

        def _missing(*args, **kwargs):
            raise FileNotFoundError("systemd-analyze")

        monkeypatch.setattr(subprocess, "run", _missing)
        with app.app_context():
            result = run_doctor(check_ids=["deploy.systemd_syntax"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "systemd-analyze not available"

    def test_warns_when_systemd_analyze_times_out(self, app, db, install, tmp_path, monkeypatch):
        import app.deployment.systemd as systemd_mod

        units = tmp_path / "units"
        units.mkdir()
        (units / "devlog.service").write_text("[Service]\n", encoding="utf-8")
        monkeypatch.setattr(systemd_mod, "__file__", str(units / "systemd.py"))

        def _timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="systemd-analyze", timeout=8)

        monkeypatch.setattr(subprocess, "run", _timeout)
        with app.app_context():
            result = run_doctor(check_ids=["deploy.systemd_syntax"])
        assert result.checks[0].status == CheckStatus.WARN
        assert result.checks[0].summary == "systemd-analyze timed out"


class TestImageMatch:
    def test_skipped_when_the_package_version_is_unknown(self, app, db, install, monkeypatch):
        monkeypatch.setattr(importlib.metadata, "version", lambda name: "")
        with app.app_context():
            result = run_doctor(check_ids=["deploy.image_match"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Cannot determine package version"

    def test_skipped_when_paths_are_unavailable(self, app, db, install, monkeypatch):
        monkeypatch.setattr(importlib.metadata, "version", lambda name: "9.9.9")
        install.break_paths()
        with app.app_context():
            result = run_doctor(check_ids=["deploy.image_match"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Paths unavailable"

    def test_skipped_without_installation_metadata(self, app, db, install, monkeypatch):
        monkeypatch.setattr(importlib.metadata, "version", lambda name: "9.9.9")
        with app.app_context():
            result = run_doctor(check_ids=["deploy.image_match"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "No installation metadata"

    def test_warns_when_the_versions_differ(self, app, db, install, monkeypatch):
        monkeypatch.setattr(importlib.metadata, "version", lambda name: "9.9.9")
        _write_metadata(install.paths, InstallMode.DEVELOPMENT, version="0.0.1")
        with app.app_context():
            result = run_doctor(check_ids=["deploy.image_match"])
        assert result.checks[0].status == CheckStatus.WARN
        assert result.checks[0].details["installed"] == "9.9.9"
        assert result.checks[0].details["metadata_version"] == "0.0.1"

    def test_passes_when_the_versions_match(self, app, db, install, monkeypatch):
        monkeypatch.setattr(importlib.metadata, "version", lambda name: "9.9.9")
        _write_metadata(install.paths, InstallMode.DEVELOPMENT, version="9.9.9")
        with app.app_context():
            result = run_doctor(check_ids=["deploy.image_match"])
        assert result.checks[0].status == CheckStatus.PASS
        assert result.checks[0].details["version"] == "9.9.9"

    def test_skipped_when_the_metadata_cannot_be_read(self, app, db, install, monkeypatch):
        monkeypatch.setattr(importlib.metadata, "version", lambda name: "9.9.9")

        def _broken(path):
            raise OSError("boom")

        monkeypatch.setattr(layout.InstallationMetadata, "load", staticmethod(_broken))
        with app.app_context():
            result = run_doctor(check_ids=["deploy.image_match"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Cannot compare with deployment metadata"


class TestServiceAccountIds:
    def test_none_outside_a_system_installation(self, app, db):
        _set_ctx(DoctorContext("development", "1.0.0"))
        assert _service_account_ids() is None

    def test_none_when_the_account_is_missing(self, app, db, monkeypatch):
        def _missing(name):
            raise KeyError(name)

        monkeypatch.setattr("pwd.getpwnam", _missing)
        _set_ctx(DoctorContext("system", "1.0.0"))
        assert _service_account_ids() is None

    def test_returns_the_ids_of_the_service_account(self, app, db, monkeypatch):
        monkeypatch.setattr("pwd.getpwnam", lambda name: SimpleNamespace(pw_uid=123))
        monkeypatch.setattr("grp.getgrnam", lambda name: SimpleNamespace(gr_gid=456))
        _set_ctx(DoctorContext("system", "1.0.0"))
        assert _service_account_ids() == (123, 456)


class TestRunDoctorEngine:
    def test_reports_an_unknown_package_version(self, app, db, monkeypatch):
        def _missing(name):
            raise importlib.metadata.PackageNotFoundError(name)

        monkeypatch.setattr(importlib.metadata, "version", _missing)
        with app.app_context():
            result = run_doctor(check_ids=["pkg.version"])
        assert result.version == "unknown"

    def test_runs_without_a_flask_application_context(self, app):
        result = run_doctor(check_ids=["pkg.version"])
        assert result.checks[0].check_id == "pkg.version"

    def test_skips_a_check_that_is_no_longer_registered(self, app, db, install, monkeypatch):
        registry = doctor_mod._registry
        real_get = registry.get
        calls = {"count": 0}

        def fake_get(check_id):
            calls["count"] += 1
            if calls["count"] == 2:
                return None
            return real_get(check_id)

        monkeypatch.setattr(registry, "get", fake_get)
        with app.app_context():
            result = run_doctor(check_ids=["pkg.version"])
        assert result.checks[0].status == CheckStatus.SKIP
        assert result.checks[0].summary == "Skipped: not registered"

    def test_skips_every_check_when_the_total_timeout_is_reached(self, app, db, install):
        with app.app_context():
            result = run_doctor(
                check_ids=["pkg.version", "config.load"],
                parallel=True,
                total_timeout=0.0,
            )
        assert len(result.checks) == 2
        assert all(c.status == CheckStatus.SKIP for c in result.checks)
        assert all(c.summary == "Skipped: total timeout reached" for c in result.checks)

    def test_skips_every_check_when_the_sequential_timeout_is_reached(self, app, db, install):
        with app.app_context():
            result = run_doctor(
                check_ids=["pkg.version", "config.load"],
                parallel=False,
                total_timeout=0.0,
            )
        assert len(result.checks) == 2
        assert all(c.status == CheckStatus.SKIP for c in result.checks)

    def test_reports_a_check_that_did_not_finish(self, app, db, install, monkeypatch):
        def _slow(runner, timeout, app=None, doctor_ctx=None, **kwargs):
            time.sleep(1.0)
            return CheckResult(
                check_id=kwargs.get("check_id", "unknown"),
                category=kwargs.get("category", "unknown"),
                status=CheckStatus.PASS,
                severity=kwargs.get("severity", "optional"),
                summary="slow",
            )

        monkeypatch.setattr(doctor_mod, "_run_check_with_timeout", _slow)
        with app.app_context():
            result = run_doctor(
                check_ids=["pkg.version", "config.load"],
                parallel=True,
                total_timeout=0.05,
            )
        assert any(c.summary == "Check timed out or failed to complete" for c in result.checks)

    def test_reports_no_paths_when_they_cannot_be_resolved(self, app, db, install):
        install.break_paths()
        with app.app_context():
            result = run_doctor(check_ids=["pkg.version"])
        assert result.paths == {}

    def test_reports_the_resolved_paths(self, app, db, install):
        with app.app_context():
            result = run_doctor(check_ids=["pkg.version"])
        assert result.paths["data_dir"] == str(install.paths.data_dir.path)
        assert result.paths["database"] == str(install.paths.database.path)
        assert result.paths["config_file"] == str(install.paths.config_file.path)
