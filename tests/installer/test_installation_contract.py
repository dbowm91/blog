"""Installation contract tests — verifies installer vs onboarding ownership boundary.

R2C1: The installer installs verified code artifacts and creates minimal scaffolding.
devlog onboard creates configuration, secrets, database, and administrator state.
RuntimePaths is the sole authority for runtime path resolution.

This test ensures the installer script does not generate application configuration
values beyond bootstrap metadata needed to invoke onboarding.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
INSTALLER = REPO_ROOT / "scripts" / "install.sh"

# Patterns that indicate installer generating app configuration values
_CONFIG_GENERATION_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "secret_key_generation",
        re.compile(r"SECRET_KEY\s*=\s*['\"]?\$\("),
        "Installer should not generate SECRET_KEY; onboarding handles secrets",
    ),
    (
        "admin_password_generation",
        re.compile(r"ADMIN_PASSWORD\s*=\s*['\"]?\$\("),
        "Installer should not generate ADMIN_PASSWORD; onboarding handles admin",
    ),
    (
        "database_uri_construction",
        re.compile(r"SQLALCHEMY_DATABASE_URI\s*=|DATABASE_URL\s*="),
        "Installer should not construct database URIs; onboarding handles database config",
    ),
    (
        "config_toml_generation",
        re.compile(r"cat\s*.*>\s*config\.toml|printf\s*.*config\.toml"),
        "Installer should not write config.toml; onboarding handles configuration",
    ),
    (
        "admin_user_creation",
        re.compile(r"create_admin|insert.*user.*admin|flask\s+db\s+upgrade"),
        "Installer should not create admin users or run migrations; onboarding handles these",
    ),
]

# Patterns that are legitimate installer behavior (bootstrap metadata)
_LEGITIMATE_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "version_metadata",
        re.compile(r"INSTALLED_VERSION|TARGET_VERSION"),
        "Version tracking is legitimate installer bootstrap metadata",
    ),
    (
        "install_scope",
        re.compile(r"INSTALL_SCOPE|INSTALL_MODE"),
        "Installation mode/scope tracking is legitimate",
    ),
    (
        "onboard_invocation",
        re.compile(r"devlog\s+onboard"),
        "Invoking onboarding is the correct delegation pattern",
    ),
]


class TestInstallationContract:
    """Verify installer does not encroach on onboarding responsibilities."""

    def test_installer_script_exists(self):
        assert INSTALLER.exists(), "install.sh must exist"

    def test_no_config_generation_in_installer(self):
        if not INSTALLER.exists():
            pytest.skip("install.sh not found")

        content = INSTALLER.read_text()
        violations: list[str] = []

        for tag, pattern, description in _CONFIG_GENERATION_PATTERNS:
            for line_no, line in enumerate(content.splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if pattern.search(line):
                    violations.append(f"Line {line_no} [{tag}]: {description}\n  -> {stripped}")

        if violations:
            msg = (
                "Installer is generating application configuration values.\n"
                "The installer should only install code artifacts and scaffolding.\n"
                "Configuration, secrets, database, and admin are onboarding responsibilities.\n\n"
                + "\n\n".join(violations)
            )
            pytest.fail(msg)

    def test_installer_delegates_to_onboard(self):
        if not INSTALLER.exists():
            pytest.skip("install.sh not found")

        content = INSTALLER.read_text()
        assert "devlog onboard" in content, (
            "Installer should invoke 'devlog onboard' for configuration and state setup"
        )

    def test_installer_has_scope_flag(self):
        if not INSTALLER.exists():
            pytest.skip("install.sh not found")

        content = INSTALLER.read_text()
        assert "--scope" in content or "INSTALL_SCOPE" in content, (
            "Installer should support --scope (system/user) for native installations"
        )

    def test_installer_checksum_verification(self):
        if not INSTALLER.exists():
            pytest.skip("install.sh not found")

        content = INSTALLER.read_text()
        assert "sha256sum" in content or "shasum" in content or "checksum" in content.lower(), (
            "Installer should verify artifact checksums"
        )

    def test_installer_supports_dry_run(self):
        if not INSTALLER.exists():
            pytest.skip("install.sh not found")

        content = INSTALLER.read_text()
        assert "--dry-run" in content, "Installer should support --dry-run mode"
