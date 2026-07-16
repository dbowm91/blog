from __future__ import annotations

import hashlib
from pathlib import Path

import pytest


@pytest.fixture
def artifacts_dir(tmp_path: Path) -> Path:
    d = tmp_path / "dist"
    d.mkdir()
    return d


@pytest.fixture
def sample_wheel(artifacts_dir: Path) -> Path:
    import zipfile

    wheel_path = artifacts_dir / "devlog-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        zf.writestr("app/themes/bundled/theme.toml", '[colors]\nprimary = "#ff0000"\n')
        zf.writestr("app/templates/base.html", "<html></html>")
        zf.writestr("app/static/css/base.css", "body {}")
        zf.writestr("app/static/dist/app.js", "console.log()")
        zf.writestr("migrations/env.py", "")
        zf.writestr("app/themes/ACCESSIBILITY_EXCEPTIONS.json", "{}")
        zf.writestr("devlog/__init__.py", "__version__ = '1.0.0'")
        zf.writestr("devlog-1.0.0.dist-info/METADATA", "Metadata-Version: 2.1\nVersion: 1.0.0\n")
    return wheel_path


@pytest.fixture
def sample_checksums(artifacts_dir: Path, sample_wheel: Path) -> Path:
    sha = hashlib.sha256(sample_wheel.read_bytes()).hexdigest()
    checksums_path = artifacts_dir / "checksums.txt"
    checksums_path.write_text(f"{sha}  {sample_wheel.name}\n")
    return checksums_path


@pytest.fixture
def installer_script() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts" / "install.sh"
