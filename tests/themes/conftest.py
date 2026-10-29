"""Shared fixtures for the theme test suite."""

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from app.themes import resources


@pytest.fixture
def case_collision(monkeypatch: pytest.MonkeyPatch) -> Callable[[Path, Sequence[str]], None]:
    """Expose two case-colliding theme names to directory discovery.

    A case-insensitive filesystem cannot hold two files whose names differ
    only by case, so the second write replaces the first and the catalogue
    never sees a collision.  The directory scan is therefore replaced with
    the colliding names; discovery, canonical-name derivation and the
    registry's collision handling all run unchanged.
    """

    def _apply(directory: Path, names: Sequence[str]) -> None:
        original = resources._candidate_files
        target = directory.resolve()

        def _candidate_files(scan_root: Path) -> list[Path]:
            if Path(scan_root).resolve() == target:
                return [directory / f"{name}.toml" for name in names]
            return original(scan_root)

        monkeypatch.setattr(resources, "_candidate_files", _candidate_files)

    return _apply
