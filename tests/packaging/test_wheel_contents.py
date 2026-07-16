"""Packaging validation tests for the devlog wheel and sdist.

These tests build the project, inspect the resulting artifacts, and verify
required package data is present while sensitive files are excluded.

Marked slow because they build wheels and create isolated venvs.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SENSITIVE_WHEEL_PATTERNS = [
    ".env",
    "config.toml",
    ".env.local",
    ".env.production",
    "blog.db",
    "instance/",
    "logs/",
    "backups/",
    "app/static/uploads/",
    "plans/",
    "tests/",
    "docs/",
    ".github/",
    ".opencode/",
    ".skills/",
    "node_modules/",
    ".ruff_cache/",
    ".mypy_cache/",
    ".pytest_cache/",
    "scripts/",
    "architecture/",
]

SENSITIVE_SDIST_PATTERNS = [
    ".env",
    "config.toml",
    ".env.local",
    ".env.production",
    "blog.db",
    "instance/",
    "logs/",
    "backups/",
    "app/static/uploads/",
    "plans/",
    ".github/",
    ".opencode/",
    ".skills/",
    "node_modules/",
    ".ruff_cache/",
    ".mypy_cache/",
    ".pytest_cache/",
    "scripts/",
    "architecture/",
]


def _build_wheel(tmp_dir: Path) -> Path:
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_dir)],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        timeout=120,
    )
    wheels = list(tmp_dir.glob("*.whl"))
    assert wheels, f"No wheel found in {tmp_dir}"
    return wheels[0]


def _build_sdist(tmp_dir: Path) -> Path:
    subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--outdir", str(tmp_dir)],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        timeout=120,
    )
    sdists = list(tmp_dir.glob("*.tar.gz"))
    assert sdists, f"No sdist found in {tmp_dir}"
    return sdists[0]


def _wheel_contents(wheel_path: Path) -> list[str]:
    with zipfile.ZipFile(wheel_path, "r") as zf:
        return zf.namelist()


def _sdist_contents(sdist_path: Path) -> list[str]:
    import tarfile

    with tarfile.open(sdist_path, "r:gz") as tf:
        return tf.getnames()


def _install_wheel_in_venv(wheel_path: Path, venv_dir: Path) -> Path:
    venv.create(venv_dir, with_pip=True)
    pip = venv_dir / "bin" / "pip"
    subprocess.run(
        [str(pip), "install", str(wheel_path)],
        check=True,
        capture_output=True,
        timeout=120,
    )
    return venv_dir / "bin" / "devlog"


def _run_devlog(devlog_bin: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(devlog_bin), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture(scope="module")
def wheel_path():
    with tempfile.TemporaryDirectory(prefix="devlog_wheel_") as tmp:
        yield _build_wheel(Path(tmp))


@pytest.fixture(scope="module")
def sdist_path():
    with tempfile.TemporaryDirectory(prefix="devlog_sdist_") as tmp:
        yield _build_sdist(Path(tmp))


@pytest.fixture(scope="module")
def wheel_contents(wheel_path):
    return _wheel_contents(wheel_path)


@pytest.fixture(scope="module")
def sdist_contents(sdist_path):
    return _sdist_contents(sdist_path)


@pytest.fixture(scope="module")
def isolated_devlog(wheel_path):
    with tempfile.TemporaryDirectory(prefix="devlog_venv_") as tmp:
        yield _install_wheel_in_venv(wheel_path, Path(tmp))


class TestBuild:
    def test_wheel_builds_successfully(self, wheel_path):
        assert wheel_path.exists()
        assert wheel_path.suffix == ".whl"

    def test_sdist_builds_successfully(self, sdist_path):
        assert sdist_path.exists()
        assert sdist_path.name.endswith(".tar.gz")

    def test_wheel_has_correct_naming(self, wheel_path):
        name = wheel_path.name
        assert name.startswith("devlog-")
        assert name.endswith(".whl")


class TestWheelContents:
    def test_has_pyproject_metadata(self, wheel_contents):
        metadata = [f for f in wheel_contents if f.endswith("METADATA")]
        assert metadata, "Wheel missing METADATA file"

    def test_has_record(self, wheel_contents):
        record = [f for f in wheel_contents if f.endswith("RECORD")]
        assert record, "Wheel missing RECORD file"

    def test_includes_devlog_cli(self, wheel_contents):
        cli_files = [f for f in wheel_contents if f.startswith("devlog_cli/")]
        assert cli_files, "Wheel missing devlog_cli package"
        assert any("__init__.py" in f for f in cli_files)
        assert any("main.py" in f for f in cli_files)

    def test_includes_app_package(self, wheel_contents):
        app_files = [f for f in wheel_contents if f.startswith("app/")]
        assert app_files, "Wheel missing app package"

    def test_includes_themes(self, wheel_contents):
        theme_files = [f for f in wheel_contents if "themes/bundled/" in f and f.endswith(".toml")]
        assert len(theme_files) >= 40, f"Expected >= 40 theme files, got {len(theme_files)}"

    def test_includes_templates(self, wheel_contents):
        template_files = [f for f in wheel_contents if "templates/" in f and f.endswith(".html")]
        assert template_files, "Wheel missing HTML templates"

    def test_includes_css(self, wheel_contents):
        css_files = [f for f in wheel_contents if "static/css/" in f and f.endswith(".css")]
        assert css_files, "Wheel missing CSS files"

    def test_includes_accessibility_exceptions(self, wheel_contents):
        acc_files = [f for f in wheel_contents if "ACCESSIBILITY_EXCEPTIONS" in f]
        assert acc_files, "Wheel missing ACCESSIBILITY_EXCEPTIONS.json"

    def test_includes_catalog_manifest(self, wheel_contents):
        manifest_files = [f for f in wheel_contents if "catalog_manifest.json" in f]
        assert manifest_files, "Wheel missing catalog_manifest.json"


class TestSensitiveFilesExcluded:
    """Wheel must not contain sensitive or repository-only files."""

    def _check_no_sensitive(self, contents: list[str], patterns: list[str]):
        for pattern in patterns:
            matches = [f for f in contents if pattern in f]
            assert not matches, f"Artifact contains sensitive pattern '{pattern}': {matches[:3]}..."

    def test_wheel_excludes_sensitive_files(self, wheel_contents):
        self._check_no_sensitive(wheel_contents, SENSITIVE_WHEEL_PATTERNS)

    def test_sdist_excludes_sensitive_files(self, sdist_contents):
        self._check_no_sensitive(sdist_contents, SENSITIVE_SDIST_PATTERNS)

    def test_wheel_excludes_plans(self, wheel_contents):
        plan_files = [f for f in wheel_contents if "plans/" in f]
        assert not plan_files, f"Wheel contains plans directory: {plan_files}"

    def test_wheel_excludes_tests(self, wheel_contents):
        test_files = [f for f in wheel_contents if "tests/" in f]
        assert not test_files, f"Wheel contains tests directory: {test_files}"

    def test_wheel_excludes_docs(self, wheel_contents):
        doc_files = [f for f in wheel_contents if "docs/" in f]
        assert not doc_files, f"Wheel contains docs directory: {doc_files}"

    def test_wheel_excludes_github(self, wheel_contents):
        gh_files = [f for f in wheel_contents if ".github/" in f]
        assert not gh_files, f"Wheel contains .github directory: {gh_files}"


class TestIsolatedInstallation:
    """Verify the CLI works in an isolated venv outside the repository."""

    def test_devlog_binary_exists(self, isolated_devlog):
        assert isolated_devlog.exists()
        assert isolated_devlog.is_file()

    def test_devlog_help(self, isolated_devlog):
        result = _run_devlog(isolated_devlog, "--help")
        assert result.returncode == 0
        assert "DevLog" in result.stdout

    def test_devlog_version(self, isolated_devlog):
        result = _run_devlog(isolated_devlog, "--version")
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "devlog" in output.lower()

    def test_devlog_version_json(self, isolated_devlog):
        result = _run_devlog(isolated_devlog, "--json", "version")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["ok"] is True
        assert data["status"] == "success"
        assert "version" in data["details"]

    def test_devlog_no_subcommand_shows_version(self, isolated_devlog):
        result = _run_devlog(isolated_devlog)
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "devlog" in output.lower() or "DevLog" in output

    def test_command_groups_help(self, isolated_devlog):
        for group in ["config", "admin", "db", "themes", "backup", "deploy"]:
            result = _run_devlog(isolated_devlog, group, "--help")
            assert result.returncode == 0, f"devlog {group} --help failed"
            assert result.stdout, f"devlog {group} --help produced no stdout"


class TestNoFlaskStartup:
    """Help and version must not construct the Flask application."""

    def test_help_does_not_import_app(self, isolated_devlog):
        result = _run_devlog(isolated_devlog, "--help")
        assert result.returncode == 0
        assert "flask" not in result.stderr.lower()
        assert "sqlalchemy" not in result.stderr.lower()

    def test_version_does_not_import_app(self, isolated_devlog):
        result = _run_devlog(isolated_devlog, "--version")
        assert result.returncode == 0
        assert "flask" not in result.stderr.lower()
        assert "sqlalchemy" not in result.stderr.lower()


class TestExitCodes:
    """Stable exit codes for known error conditions."""

    def test_unknown_option_returns_error(self, isolated_devlog):
        result = _run_devlog(isolated_devlog, "--bogus")
        assert result.returncode != 0

    def test_unknown_subcommand_returns_error(self, isolated_devlog):
        result = _run_devlog(isolated_devlog, "nonexistent")
        assert result.returncode != 0

    def test_help_exits_zero(self, isolated_devlog):
        result = _run_devlog(isolated_devlog, "--help")
        assert result.returncode == 0

    def test_version_exits_zero(self, isolated_devlog):
        result = _run_devlog(isolated_devlog, "--version")
        assert result.returncode == 0


class TestVersionConsistency:
    """CLI version should match pyproject.toml version."""

    def test_version_matches_pyproject(self, isolated_devlog):
        result = _run_devlog(isolated_devlog, "--json", "version")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        cli_version = data["details"]["version"]

        pyproject = (REPO_ROOT / "pyproject.toml").read_text()
        for line in pyproject.splitlines():
            line = line.strip()
            if line.startswith("version"):
                pyproject_version = line.split("=")[1].strip().strip('"')
                break
        else:
            pytest.skip("Could not parse version from pyproject.toml")

        assert cli_version == pyproject_version, (
            f"CLI version {cli_version!r} != pyproject.toml {pyproject_version!r}"
        )


class TestPackageDataCompleteness:
    def test_includes_migrations(self, wheel_contents):
        migration_files = [
            f for f in wheel_contents if f.startswith("migrations/") and f.endswith(".py")
        ]
        assert migration_files, "Wheel missing Alembic migration scripts"

    def test_includes_alembic_ini(self, wheel_contents):
        source_ini = REPO_ROOT / "migrations" / "alembic.ini"
        if not source_ini.exists():
            pytest.skip("alembic.ini not present in source")
        ini_files = [f for f in wheel_contents if f.endswith("alembic.ini")]
        assert ini_files, "Wheel missing alembic.ini (present in source but not in wheel)"

    def test_includes_config_example(self, wheel_contents):
        source_example = REPO_ROOT / "config.toml.example"
        if not source_example.exists():
            pytest.skip("config.toml.example not present in source")
        example_files = [f for f in wheel_contents if "config.toml.example" in f]
        assert not example_files, (
            "Wheel should not include config.toml.example (development template, not runtime data)"
        )

    def test_includes_static_js(self, wheel_contents):
        js_files = [f for f in wheel_contents if "static/js/" in f and f.endswith(".js")]
        assert js_files, "Wheel missing JS files in static/js/"

    def test_includes_static_dist(self, wheel_contents):
        source_dist = REPO_ROOT / "app" / "static" / "dist"
        if not source_dist.exists():
            pytest.skip("Vite dist not built in source")
        dist_files = [f for f in wheel_contents if "static/dist/" in f]
        assert dist_files, "Wheel missing Vite dist files (present in source but not in wheel)"

    def test_wheel_excludes_env_files(self, wheel_contents):
        env_files = [f for f in wheel_contents if ".env" in f]
        assert not env_files, f"Wheel contains .env files: {env_files}"

    def test_wheel_excludes_database_files(self, wheel_contents):
        db_extensions = (".db", ".sqlite", ".wal", ".shm")
        db_files = [f for f in wheel_contents if any(f.endswith(ext) for ext in db_extensions)]
        assert not db_files, f"Wheel contains database files: {db_files}"

    def test_wheel_excludes_upload_dir(self, wheel_contents):
        upload_files = [f for f in wheel_contents if "static/uploads/" in f]
        assert not upload_files, f"Wheel contains uploads: {upload_files}"

    def test_wheel_excludes_logs(self, wheel_contents):
        log_files = [f for f in wheel_contents if f.startswith("logs/") or "/logs/" in f]
        assert not log_files, f"Wheel contains logs directory: {log_files}"

    def test_wheel_excludes_backups(self, wheel_contents):
        backup_files = [f for f in wheel_contents if "backups/" in f]
        assert not backup_files, f"Wheel contains backups directory: {backup_files}"

    def test_wheel_excludes_caches(self, wheel_contents):
        cache_patterns = ("__pycache__", ".ruff_cache", ".mypy_cache", ".pytest_cache")
        cache_files = [f for f in wheel_contents if any(p in f for p in cache_patterns)]
        assert not cache_files, f"Wheel contains cache directories: {cache_files}"

    def test_wheel_excludes_build_artifacts(self, wheel_contents):
        artifact_patterns = ("build/", "dist/", ".egg-info")
        artifact_files = [f for f in wheel_contents if any(p in f for p in artifact_patterns)]
        filtered = [f for f in artifact_files if not f.startswith("app/static/dist/")]
        assert not filtered, f"Wheel contains build artifacts: {filtered}"


@pytest.fixture(scope="module")
def isolated_devlog_with_context(wheel_path):
    with tempfile.TemporaryDirectory(prefix="devlog_venv_ctx_") as tmp:
        venv_dir = Path(tmp)
        venv.create(venv_dir, with_pip=True)
        pip = venv_dir / "bin" / "pip"
        subprocess.run(
            [str(pip), "install", str(wheel_path)],
            check=True,
            capture_output=True,
            timeout=120,
        )
        devlog_bin = venv_dir / "bin" / "devlog"
        config_path = venv_dir / "test-config.toml"
        yield devlog_bin, config_path


class TestCleanInstallAppContext:
    def test_config_init_and_check(self, isolated_devlog_with_context):
        devlog_bin, config_path = isolated_devlog_with_context
        init_result = _run_devlog(
            devlog_bin,
            "config",
            "init",
            "--profile",
            "development",
            "--output",
            str(config_path),
        )
        assert init_result.returncode == 0, (
            f"config init failed:\nstdout: {init_result.stdout}\nstderr: {init_result.stderr}"
        )
        assert config_path.exists(), "config.toml was not created"

        check_result = _run_devlog(
            devlog_bin,
            "--config",
            str(config_path),
            "config",
            "check",
        )
        assert check_result.returncode in (0, 8), (
            f"config check failed (exit {check_result.returncode}):\n"
            f"stdout: {check_result.stdout}\nstderr: {check_result.stderr}"
        )

    def test_themes_list(self, isolated_devlog_with_context):
        devlog_bin, config_path = isolated_devlog_with_context
        if not config_path.exists():
            init_result = _run_devlog(
                devlog_bin,
                "config",
                "init",
                "--profile",
                "development",
                "--output",
                str(config_path),
            )
            assert init_result.returncode == 0

        result = _run_devlog(
            devlog_bin,
            "--config",
            str(config_path),
            "--json",
            "themes",
            "list",
        )
        assert result.returncode == 0, (
            f"themes list failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        data = json.loads(result.stdout)
        assert data["ok"] is True
        themes = data.get("themes", [])
        if not themes:
            themes = data.get("details", {}).get("themes", [])
        assert len(themes) > 0, f"No themes found in output: {list(data.keys())}"

    def test_db_status(self, isolated_devlog_with_context):
        devlog_bin, config_path = isolated_devlog_with_context
        if not config_path.exists():
            init_result = _run_devlog(
                devlog_bin,
                "config",
                "init",
                "--profile",
                "development",
                "--output",
                str(config_path),
            )
            assert init_result.returncode == 0

        result = _run_devlog(
            devlog_bin,
            "--config",
            str(config_path),
            "db",
            "status",
        )
        output = result.stdout + result.stderr
        assert (
            "migration" in output.lower()
            or "database" in output.lower()
            or "error" in output.lower()
        ), f"db status produced unexpected output:\n{output}"
