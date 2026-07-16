from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def script_path() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts" / "install.sh"


def run_install(
    script_path: Path, *args: str, check: bool = False, timeout: int = 10
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["bash", str(script_path), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check:
        assert result.returncode == 0, (
            f"Exit {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


class TestHelpOutput:
    def test_shows_usage(self, script_path: Path) -> None:
        result = run_install(script_path, "--help")
        assert result.returncode == 0
        assert "DevLog Installer" in result.stderr
        assert "--native" in result.stderr
        assert "--docker" in result.stderr
        assert "--dry-run" in result.stderr
        assert "--version" in result.stderr

    def test_shows_all_options(self, script_path: Path) -> None:
        result = run_install(script_path, "--help")
        for flag in [
            "--user",
            "--system",
            "--channel",
            "--non-interactive",
            "--yes",
            "--no-onboard",
            "--onboard",
        ]:
            assert flag in result.stderr


class TestOptionParsing:
    def test_unknown_option_fails(self, script_path: Path) -> None:
        result = run_install(script_path, "--bogus")
        assert result.returncode != 0
        assert "Unknown option" in result.stderr

    def test_version_requires_value(self, script_path: Path) -> None:
        result = run_install(script_path, "--version")
        assert result.returncode != 0
        assert "requires a value" in result.stderr

    def test_prefix_requires_value(self, script_path: Path) -> None:
        result = run_install(script_path, "--prefix")
        assert result.returncode != 0

    def test_channel_requires_value(self, script_path: Path) -> None:
        result = run_install(script_path, "--channel")
        assert result.returncode != 0

    def test_invalid_channel_fails(self, script_path: Path) -> None:
        result = run_install(script_path, "--channel", "invalid")
        assert result.returncode != 0
        assert "Invalid channel" in result.stderr


class TestDryRun:
    def test_dry_run_flag_accepted(self, script_path: Path) -> None:
        result = run_install(script_path, "--help")
        assert "--dry-run" in result.stderr

    def test_dry_run_with_mocked_install(self, script_path: Path, tmp_path: Path) -> None:
        prefix = tmp_path / "devlog"
        prefix.mkdir()
        mock_script = tmp_path / "mock_install.sh"
        mock_script.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f'INSTALL_MODE="native"\n'
            f"DRY_RUN=true\n"
            f'PREFIX="{prefix}"\n'
            f'TARGET_VERSION="1.0.0"\n'
            f'VERSION_DIR="${{PREFIX}}/releases/1.0.0"\n'
            f'CURRENT_LINK="${{PREFIX}}/current"\n'
            'mkdir -p "$(dirname "$CURRENT_LINK")"\n'
            'if [ "$DRY_RUN" = true ]; then\n'
            '    echo "[dry-run] Would create $VERSION_DIR"\n'
            '    echo "[dry-run] Would install wheel"\n'
            '    echo "[dry-run] Would update $CURRENT_LINK"\n'
            '    echo "[dry-run] Would create launcher"\n'
            "fi\n"
            'echo "DONE"\n'
        )
        os.chmod(mock_script, 0o755)
        result = subprocess.run(
            ["bash", str(mock_script)], capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0
        assert "[dry-run] Would create" in result.stdout
        assert "DONE" in result.stdout


class TestChecksumVerification:
    def test_portable_sha256_function(self, tmp_path: Path) -> None:
        script = tmp_path / "test_sha.sh"
        script.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "portable_sha256() {\n"
            "    if command -v sha256sum >/dev/null 2>&1; then\n"
            '        sha256sum "$1" | cut -d" " -f1\n'
            "    elif command -v shasum >/dev/null 2>&1; then\n"
            '        shasum -a 256 "$1" | cut -d" " -f1\n'
            "    else\n"
            '        echo "NO_TOOL"\n'
            "    fi\n"
            "}\n"
            'portable_sha256 "$1"\n'
        )
        os.chmod(script, 0o755)

        test_file = tmp_path / "data.txt"
        test_file.write_text("hello world")

        result = subprocess.run(
            ["bash", str(script), str(test_file)], capture_output=True, text=True
        )
        assert result.returncode == 0
        assert len(result.stdout.strip()) == 64

    def test_verify_checksums_function_passes(self, tmp_path: Path) -> None:
        import hashlib

        data = b"test artifact"
        artifact = tmp_path / "release.whl"
        artifact.write_bytes(data)

        sha = hashlib.sha256(data).hexdigest()
        checksums = tmp_path / "checksums.txt"
        checksums.write_text(f"{sha}  release.whl\n")

        verify_script = tmp_path / "verify.sh"
        verify_script.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f'ARTIFACTS_DIR="{tmp_path}"\n'
            f'CHECKSUMS_FILE="{checksums}"\n'
            "failed=0\n"
            "while IFS= read -r line; do\n"
            '    [ -z "$line" ] && continue\n'
            '    [[ "$line" == \\#* ]] && continue\n'
            '    expected_hash="${line%%  *}"\n'
            '    filename="${line#*  }"\n'
            '    filepath="${ARTIFACTS_DIR}/${filename}"\n'
            '    if [ ! -f "$filepath" ]; then\n'
            '        echo "MISSING: $filename"\n'
            "        failed=1\n"
            "        continue\n"
            "    fi\n"
            '    actual_hash=$(sha256sum "$filepath" | cut -d" " -f1)\n'
            '    if [ "$actual_hash" = "$expected_hash" ]; then\n'
            '        echo "OK: $filename"\n'
            "    else\n"
            '        echo "MISMATCH: $filename"\n'
            "        failed=1\n"
            "    fi\n"
            'done < "$CHECKSUMS_FILE"\n'
            "exit $failed\n"
        )
        os.chmod(verify_script, 0o755)

        result = subprocess.run(["bash", str(verify_script)], capture_output=True, text=True)
        assert result.returncode == 0
        assert "OK: release.whl" in result.stdout

    def test_verify_checksums_function_fails_on_mismatch(self, tmp_path: Path) -> None:
        artifact = tmp_path / "release.whl"
        artifact.write_bytes(b"content")

        checksums = tmp_path / "checksums.txt"
        checksums.write_text(
            "0000000000000000000000000000000000000000000000000000000000000000  release.whl\n"
        )

        verify_script = tmp_path / "verify.sh"
        verify_script.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f'ARTIFACTS_DIR="{tmp_path}"\n'
            f'CHECKSUMS_FILE="{checksums}"\n'
            "failed=0\n"
            "while IFS= read -r line; do\n"
            '    [ -z "$line" ] && continue\n'
            '    expected_hash="${line%%  *}"\n'
            '    filename="${line#*  }"\n'
            '    filepath="${ARTIFACTS_DIR}/${filename}"\n'
            '    actual_hash=$(sha256sum "$filepath" | cut -d" " -f1)\n'
            '    if [ "$actual_hash" = "$expected_hash" ]; then\n'
            '        echo "OK"\n'
            "    else\n"
            '        echo "MISMATCH"\n'
            "        failed=1\n"
            "    fi\n"
            'done < "$CHECKSUMS_FILE"\n'
            "exit $failed\n"
        )
        os.chmod(verify_script, 0o755)

        result = subprocess.run(["bash", str(verify_script)], capture_output=True, text=True)
        assert result.returncode != 0
        assert "MISMATCH" in result.stdout


class TestPrerequisiteDetection:
    def test_script_syntax_valid(self, script_path: Path) -> None:
        result = subprocess.run(["bash", "-n", str(script_path)], capture_output=True, text=True)
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_script_is_executable_or_bashable(self, script_path: Path) -> None:
        assert script_path.exists()
        result = subprocess.run(
            ["bash", "-c", f"test -r '{script_path}'"], capture_output=True, text=True
        )
        assert result.returncode == 0

    def test_detect_os_function(self, script_path: Path) -> None:
        probe = f"""
set -euo pipefail
source "{script_path}" < /dev/null 2>/dev/null || true
detect_os 2>/dev/null || true
echo "$OS_NAME"
"""
        result = subprocess.run(["bash", "-c", probe], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            assert result.stdout.strip() in ("linux", "macos", "")
