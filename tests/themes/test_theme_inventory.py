from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.theme_inventory import (
    ThemeInventoryEntry,
    find_case_insensitive_collisions,
    inventory_themes,
    write_inventory_json,
    write_inventory_markdown,
)

THEMES_DIR = Path(__file__).resolve().parent.parent.parent / "themes"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def all_entries() -> list[ThemeInventoryEntry]:
    return inventory_themes(THEMES_DIR)


def test_discovery_count(all_entries: list[ThemeInventoryEntry]) -> None:
    assert len(all_entries) == 50


def test_no_macos_metadata(all_entries: list[ThemeInventoryEntry]) -> None:
    for e in all_entries:
        assert not e.filename.startswith("._"), f"macOS metadata leaked: {e.filename}"


def test_no_hidden_files(all_entries: list[ThemeInventoryEntry]) -> None:
    for e in all_entries:
        assert not e.filename.startswith("."), f"Hidden file leaked: {e.filename}"


def test_all_have_required_sections(all_entries: list[ThemeInventoryEntry]) -> None:
    for e in all_entries:
        assert e.has_general, f"{e.filename} missing [general]"
        assert e.has_text, f"{e.filename} missing [text]"
        assert e.has_buffer, f"{e.filename} missing [buffer]"


def test_specific_filenames_present(all_entries: list[ThemeInventoryEntry]) -> None:
    stems = {e.stem for e in all_entries}
    assert "Discord (80_ Saturation)" in stems
    assert "black but with important highlights" in stems
    assert "Catppuccin Mocha" in stems
    assert "Booberry" in stems
    assert "Dark Green" in stems
    assert "base16-atelier-forest-light" in stems


def test_no_case_insensitive_collisions(all_entries: list[ThemeInventoryEntry]) -> None:
    collisions = find_case_insensitive_collisions(all_entries)
    assert collisions == [], f"Case collisions found: {collisions}"


@pytest.mark.parametrize(
    "entry",
    inventory_themes(THEMES_DIR),
    ids=[e.stem for e in inventory_themes(THEMES_DIR)],
)
def test_each_theme_parsed(entry: ThemeInventoryEntry) -> None:
    assert not entry.has_invalid_toml, f"{entry.filename} failed to parse"
    assert len(entry.sections) > 0, f"{entry.filename} has no sections"
    assert entry.size_bytes > 0, f"{entry.filename} is empty"


def test_invalid_toml_fixture(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "themes"
    fixture_dir.mkdir()
    (fixture_dir / "invalid.toml").write_text(
        '[general]\nbackground = "#000000"\nborder = "#FFFFFF\n', encoding="utf-8"
    )
    (fixture_dir / "good.toml").write_text('[general]\nbackground = "#000000"\n', encoding="utf-8")

    entries = inventory_themes(fixture_dir)
    assert len(entries) == 2

    invalid = [e for e in entries if e.has_invalid_toml]
    assert len(invalid) == 1
    assert invalid[0].filename == "invalid.toml"
    assert invalid[0].invalid_toml_error is not None
    assert "invalid.toml" in invalid[0].invalid_toml_error

    good = [e for e in entries if not e.has_invalid_toml]
    assert len(good) == 1
    assert good[0].filename == "good.toml"


def test_alpha_color_detection(all_entries: list[ThemeInventoryEntry]) -> None:
    alpha_files = [e for e in all_entries if e.has_alpha_colors]
    assert len(alpha_files) > 0, "Expected at least one file with alpha colors"
    stems = {e.stem for e in alpha_files}
    assert "Noctis Lilac" in stems, "Noctis Lilac should have alpha colors"
    assert "Booberry" in stems, "Booberry should have alpha colors"


def test_buttons_sections(all_entries: list[ThemeInventoryEntry]) -> None:
    for e in all_entries:
        assert e.has_buttons_primary, f"{e.filename} missing [buttons.primary]"
        assert e.has_buttons_secondary, f"{e.filename} missing [buttons.secondary]"


def test_buffer_server_messages(all_entries: list[ThemeInventoryEntry]) -> None:
    for e in all_entries:
        assert e.has_buffer_server_messages, f"{e.filename} missing [buffer.server_messages]"


def test_write_inventory_json(tmp_path: Path, all_entries: list[ThemeInventoryEntry]) -> None:
    out = tmp_path / "catalog.json"
    write_inventory_json(all_entries, out)
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data) == 50
    assert data[0]["filename"]


def test_write_inventory_markdown(tmp_path: Path, all_entries: list[ThemeInventoryEntry]) -> None:
    out = tmp_path / "catalog.md"
    collisions = find_case_insensitive_collisions(all_entries)
    write_inventory_markdown(all_entries, out, collisions)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "50" in content
    assert "Halloy Theme Catalog Inventory" in content
