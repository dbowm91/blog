#!/usr/bin/env python3
"""Verify that the wheel package includes all bundled theme resources.

Run manually after building a wheel:
    python -m build --wheel
    python scripts/verify_theme_package.py dist/devlog-*.whl
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def verify_wheel(wheel_path: str | Path) -> bool:
    wheel_path = Path(wheel_path)
    if not wheel_path.exists():
        print(f"ERROR: wheel not found at {wheel_path}")
        return False

    print(f"Verifying wheel: {wheel_path.name}")

    with tempfile.TemporaryDirectory(prefix="verify_theme_") as tmpdir:
        venv_dir = Path(tmpdir) / "venv"
        venv.create(venv_dir, with_pip=True)

        pip = venv_dir / "bin" / "pip"
        python = venv_dir / "bin" / "python"

        print("  Installing wheel in isolated venv...")
        result = subprocess.run(
            [str(pip), "install", str(wheel_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"  ERROR: pip install failed:\n{result.stderr}")
            return False

        checks = [
            (
                "import app.themes",
                "from app.themes import ThemeRegistry, LoadedTheme, ThemeDescriptor",
            ),
            (
                "from app.themes.resources import discover_bundled_package",
                "themes = discover_bundled_package()\n"
                "assert len(themes) == 50, f'Expected 50 bundled themes, got {len(themes)}'\n"
                "print(f'  Bundled themes: {len(themes)}')",
            ),
            (
                "ThemeRegistry default init",
                "from app.themes.registry import ThemeRegistry\n"
                "reg = ThemeRegistry()\n"
                "themes = reg.list_themes()\n"
                "assert len(themes) == 50, f'Expected 50 themes from registry, got {len(themes)}'\n"
                "print(f'  Registry lists: {len(themes)} themes')",
            ),
            (
                "Load dark theme",
                "from app.themes.registry import ThemeRegistry\n"
                "reg = ThemeRegistry()\n"
                "loaded = reg.load('Dracula')\n"
                "assert loaded.is_dark is True\n"
                "assert '--blog-bg-page' in loaded.css\n"
                "print(f'  Dracula loaded: is_dark={loaded.is_dark}')",
            ),
            (
                "Load light theme",
                "from app.themes.registry import ThemeRegistry\n"
                "reg = ThemeRegistry()\n"
                "loaded = reg.load('Catppuccin Latte')\n"
                "assert loaded.is_dark is False\n"
                "print(f'  Catppuccin Latte loaded: is_dark={loaded.is_dark}')",
            ),
            (
                "Manifest accessible",
                "from importlib.resources import files\n"
                "manifest = files('app.themes').joinpath('bundled/catalog_manifest.json').read_text()\n"
                "import json\n"
                "data = json.loads(manifest)\n"
                "assert data['theme_count'] == 50\n"
                'print(f\'  Manifest: version={data["version"]}, themes={data["theme_count"]}\')',
            ),
            (
                "Attribution accessible",
                "from importlib.resources import files\n"
                "attr = files('app.themes').joinpath('bundled/ATTRIBUTION.md').read_text()\n"
                "assert len(attr) > 0\n"
                "print(f'  Attribution: {len(attr)} bytes')",
            ),
        ]

        passed = 0
        failed = 0
        for label, script in checks:
            print(f"  Checking: {label}...")
            result = subprocess.run(
                [str(python), "-c", script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    for line in output.splitlines():
                        print(f"    {line}")
                passed += 1
            else:
                print(f"    FAILED: {result.stderr.strip()}")
                failed += 1

        print(f"\nResults: {passed} passed, {failed} failed")
        return failed == 0


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_theme_package.py <wheel-path>")
        print("\nBuild a wheel first:")
        print("  python -m build --wheel")
        print("  python scripts/verify_theme_package.py dist/devlog-*.whl")
        return 1

    success = verify_wheel(sys.argv[1])
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
