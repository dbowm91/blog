#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import tomllib
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(frozen=True)
class ThemeInventoryEntry:
    filename: str
    stem: str
    size_bytes: int
    sections: tuple[str, ...]
    has_general: bool
    has_text: bool
    has_buffer: bool
    has_buttons_primary: bool
    has_buttons_secondary: bool
    has_buffer_server_messages: bool
    color_count_6digit: int
    color_count_8digit: int
    has_alpha_colors: bool
    has_invalid_toml: bool
    invalid_toml_error: str | None
    has_unusual_chars: bool
    unusual_chars_detail: str | None


_COLOR_6_RE = re.compile(r"#[0-9A-Fa-f]{6}(?![0-9A-Fa-f])")
_COLOR_8_RE = re.compile(r"#[0-9A-Fa-f]{8}")
_UNUSUAL_RE = re.compile(r"[\s()()\[\]{}!@#$%^&*=+|\\:;\"'<>,?/~`]")


def _extract_sections(data: dict, prefix: str = "") -> list[str]:
    sections: list[str] = []
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        sections.append(full_key)
        if isinstance(value, dict):
            sections.extend(_extract_sections(value, full_key))
    return sections


def _count_colors(text: str) -> tuple[int, int, bool]:
    six = len(_COLOR_6_RE.findall(text))
    eight = len(_COLOR_8_RE.findall(text))
    has_alpha = bool(re.search(r"#[0-9A-Fa-f]{6}00\b", text))
    return six, eight, has_alpha


def _check_unusual(filename: str) -> tuple[bool, str | None]:
    stem = Path(filename).stem
    if _UNUSUAL_RE.search(stem):
        chars = sorted({c for c in stem if _UNUSUAL_RE.search(c)})
        return True, f"contains: {' '.join(repr(c) for c in chars)}"
    return False, None


def _parse_comments(text: str) -> str | None:
    lines = text.splitlines()
    comment_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            comment_lines.append(stripped[1:].strip())
        elif stripped == "":
            continue
        else:
            break
    if comment_lines:
        return " ".join(comment_lines)
    return None


def inventory_themes(themes_dir: Path | str = "themes") -> list[ThemeInventoryEntry]:
    themes_path = Path(themes_dir)
    entries: list[ThemeInventoryEntry] = []

    for p in sorted(themes_path.iterdir()):
        if not p.is_file():
            continue
        if not p.suffix == ".toml":
            continue
        if p.name.startswith("._"):
            continue
        if p.name.startswith("."):
            continue

        text = p.read_text(encoding="utf-8")
        size = p.stat().st_size

        data: dict = {}
        error: str | None = None
        try:
            data = tomllib.loads(text)
        except Exception as exc:
            error = f"{p.name}: {exc}"

        top_sections = tuple(sorted(data.keys())) if data else ()

        has_general = "general" in data
        has_text = "text" in data
        has_buffer = "buffer" in data

        buttons = data.get("buttons", {})
        has_bp = isinstance(buttons, dict) and "primary" in buttons
        has_bs = isinstance(buttons, dict) and "secondary" in buttons

        buffer_data = data.get("buffer", {})
        has_bsm = isinstance(buffer_data, dict) and "server_messages" in buffer_data

        six, eight, has_alpha = _count_colors(text)
        unusual, unusual_detail = _check_unusual(p.name)

        entries.append(
            ThemeInventoryEntry(
                filename=p.name,
                stem=p.stem,
                size_bytes=size,
                sections=top_sections,
                has_general=has_general,
                has_text=has_text,
                has_buffer=has_buffer,
                has_buttons_primary=has_bp,
                has_buttons_secondary=has_bs,
                has_buffer_server_messages=has_bsm,
                color_count_6digit=six,
                color_count_8digit=eight,
                has_alpha_colors=has_alpha,
                has_invalid_toml=error is not None,
                invalid_toml_error=error,
                has_unusual_chars=unusual,
                unusual_chars_detail=unusual_detail,
            )
        )

    return entries


def find_case_insensitive_collisions(
    entries: list[ThemeInventoryEntry],
) -> list[tuple[str, tuple[str, ...]]]:
    groups: dict[str, list[str]] = {}
    for e in entries:
        key = e.stem.lower()
        groups.setdefault(key, []).append(e.stem)
    collisions = []
    for stems in groups.values():
        if len(stems) > 1:
            collisions.append((stems[0].lower(), tuple(sorted(stems))))
    return collisions


def write_inventory_json(entries: list[ThemeInventoryEntry], path: Path | str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(e) for e in entries]
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_inventory_markdown(
    entries: list[ThemeInventoryEntry],
    path: Path | str,
    collisions: list[tuple[str, tuple[str, ...]]],
) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Halloy Theme Catalog Inventory", ""]
    lines.append(f"**Total themes:** {len(entries)}")
    lines.append("")

    invalid = [e for e in entries if e.has_invalid_toml]
    if invalid:
        lines.append("## Invalid TOML")
        lines.append("")
        for e in invalid:
            lines.append(f"- `{e.filename}`: {e.invalid_toml_error}")
        lines.append("")

    alpha_files = [e for e in entries if e.has_alpha_colors]
    if alpha_files:
        lines.append("## Files with alpha colors")
        lines.append("")
        for e in alpha_files:
            lines.append(f"- `{e.filename}` ({e.color_count_8digit} 8-digit colors)")
        lines.append("")

    unusual_files = [e for e in entries if e.has_unusual_chars]
    if unusual_files:
        lines.append("## Files with unusual filename characters")
        lines.append("")
        for e in unusual_files:
            lines.append(f"- `{e.filename}`: {e.unusual_chars_detail}")
        lines.append("")

    if collisions:
        lines.append("## Case-insensitive collisions")
        lines.append("")
        for norm, names in collisions:
            lines.append(f"- `{norm}`: {', '.join(f'`{n}`' for n in names)}")
        lines.append("")

    lines.append("## Theme catalog")
    lines.append("")
    lines.append("| Filename | Sections | 6-digit | 8-digit | Invalid | Unusual |")
    lines.append("|----------|----------|---------|---------|---------|---------|")
    for e in entries:
        invalid_mark = "!" if e.has_invalid_toml else ""
        unusual_mark = "!" if e.has_unusual_chars else ""
        lines.append(
            f"| `{e.filename}` | {len(e.sections)} | "
            f"{e.color_count_6digit} | {e.color_count_8digit} | "
            f"{invalid_mark} | {unusual_mark} |"
        )
    lines.append("")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Halloy theme catalog inventory")
    parser.add_argument(
        "--themes-dir",
        default="themes",
        help="Path to themes directory (default: themes)",
    )
    parser.add_argument("--json", dest="json_path", help="Write JSON inventory to path")
    parser.add_argument("--markdown", dest="md_path", help="Write Markdown report to path")
    args = parser.parse_args()

    entries = inventory_themes(args.themes_dir)
    collisions = find_case_insensitive_collisions(entries)

    print("# Halloy Theme Catalog Inventory")
    print()
    print(f"**Total themes:** {len(entries)}")
    print()

    invalid = [e for e in entries if e.has_invalid_toml]
    if invalid:
        print("## Invalid TOML")
        print()
        for e in invalid:
            print(f"- `{e.filename}`: {e.invalid_toml_error}")
        print()

    alpha_files = [e for e in entries if e.has_alpha_colors]
    if alpha_files:
        print("## Files with alpha colors")
        print()
        for e in alpha_files:
            print(f"- `{e.filename}` ({e.color_count_8digit} 8-digit colors)")
        print()

    unusual_files = [e for e in entries if e.has_unusual_chars]
    if unusual_files:
        print("## Files with unusual filename characters")
        print()
        for e in unusual_files:
            print(f"- `{e.filename}`: {e.unusual_chars_detail}")
        print()

    if collisions:
        print("## Case-insensitive collisions")
        print()
        for norm, names in collisions:
            print(f"- `{norm}`: {', '.join(f'`{n}`' for n in names)}")
        print()

    print("## Theme catalog")
    print()
    print("| Filename | Sections | 6-digit | 8-digit | Invalid | Unusual |")
    print("|----------|----------|---------|---------|---------|---------|")
    for e in entries:
        invalid_mark = "!" if e.has_invalid_toml else ""
        unusual_mark = "!" if e.has_unusual_chars else ""
        print(
            f"| `{e.filename}` | {len(e.sections)} | "
            f"{e.color_count_6digit} | {e.color_count_8digit} | "
            f"{invalid_mark} | {unusual_mark} |"
        )

    if args.json_path:
        write_inventory_json(entries, args.json_path)
        print(f"\nJSON written to {args.json_path}")

    if args.md_path:
        write_inventory_markdown(entries, args.md_path, collisions)
        print(f"\nMarkdown written to {args.md_path}")


if __name__ == "__main__":
    main()
