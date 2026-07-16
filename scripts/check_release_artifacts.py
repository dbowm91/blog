#!/usr/bin/env python3
"""Verify release artifacts against a SHA-256 checksums manifest and validate wheel contents."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import zipfile
from pathlib import Path

WHEEL_NAME_RE = re.compile(r"^devlog-(\d+\.\d+\.\d+)-py3-none-any\.whl$")

EXPECTED_WHEEL_PREFIXES = [
    "app/themes/bundled/",
    "app/themes/ACCESSIBILITY_EXCEPTIONS.json",
    "migrations/",
    "app/templates/",
    "app/static/css/",
    "app/static/dist/",
]


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_checksums(path: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("  ", maxsplit=1)
        if len(parts) != 2:
            print(f"WARNING: skipping malformed line: {line}", file=sys.stderr)
            continue
        sha, name = parts
        checksums[name] = sha
    return checksums


def verify_checksums(checksums: dict[str, str], directory: Path) -> tuple[int, int, list[str]]:
    passed = 0
    failed = 0
    errors: list[str] = []

    for filename, expected_sha in sorted(checksums.items()):
        filepath = directory / filename
        if not filepath.exists():
            msg = f"MISSING: {filename}"
            print(f"  FAIL  {msg}")
            errors.append(msg)
            failed += 1
            continue

        actual_sha = compute_sha256(filepath)
        if actual_sha == expected_sha:
            print(f"  OK    {filename}")
            passed += 1
        else:
            msg = f"CHECKSUM MISMATCH: {filename} (expected {expected_sha}, got {actual_sha})"
            print(f"  FAIL  {msg}")
            errors.append(msg)
            failed += 1

    return passed, failed, errors


def verify_wheel_filename(directory: Path) -> tuple[bool, str]:
    wheels = sorted(directory.glob("*.whl"))
    if not wheels:
        return False, "no .whl files found in directory"

    for wheel in wheels:
        m = WHEEL_NAME_RE.match(wheel.name)
        if m:
            version = m.group(1)
            return True, f"{wheel.name} (version {version})"

    names = ", ".join(w.name for w in wheels)
    return False, f"no wheel matches devlog-X.Y.Z-py3-none-any.whl pattern (found: {names})"


def verify_wheel_contents(wheel_path: Path) -> tuple[int, int, list[str]]:
    passed = 0
    failed = 0
    errors: list[str] = []

    try:
        with zipfile.ZipFile(wheel_path) as zf:
            names = zf.namelist()
    except zipfile.BadZipFile as e:
        return 0, 1, [f"bad wheel file: {e}"]

    for prefix in EXPECTED_WHEEL_PREFIXES:
        matching = [n for n in names if n.startswith(prefix)]
        if matching:
            print(f"  OK    {prefix}* ({len(matching)} files)")
            passed += 1
        else:
            msg = f"MISSING in wheel: {prefix}"
            print(f"  FAIL  {msg}")
            errors.append(msg)
            failed += 1

    return passed, failed, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify release artifacts against a checksums manifest."
    )
    parser.add_argument(
        "--checksums",
        type=Path,
        default=Path("dist/checksums.txt"),
        help="Path to checksums manifest (default: dist/checksums.txt)",
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path("dist"),
        help="Directory containing artifacts (default: dist/)",
    )
    args = parser.parse_args(argv)

    all_errors: list[str] = []

    if not args.directory.is_dir():
        print(f"ERROR: directory not found: {args.directory}", file=sys.stderr)
        return 1

    if not args.checksums.exists():
        print(f"ERROR: checksums file not found: {args.checksums}", file=sys.stderr)
        return 1

    print(f"=== Verifying checksums ({args.checksums}) ===\n")
    checksums = parse_checksums(args.checksums)
    if not checksums:
        print("ERROR: no valid checksums found in manifest", file=sys.stderr)
        return 1

    cs_passed, cs_failed, cs_errors = verify_checksums(checksums, args.directory)
    all_errors.extend(cs_errors)

    print("\n=== Verifying wheel filename ===\n")
    fn_ok, fn_msg = verify_wheel_filename(args.directory)
    if fn_ok:
        print(f"  OK    {fn_msg}")
    else:
        print(f"  FAIL  {fn_msg}")
        all_errors.append(fn_msg)

    wheels = sorted(args.directory.glob("*.whl"))
    whl_path = next((w for w in wheels if WHEEL_NAME_RE.match(w.name)), None)
    if whl_path:
        print(f"\n=== Verifying wheel contents ({whl_path.name}) ===\n")
        wh_passed, wh_failed, wh_errors = verify_wheel_contents(whl_path)
        cs_passed += wh_passed
        cs_failed += wh_failed
        all_errors.extend(wh_errors)
    else:
        print("\n=== Skipping wheel contents check (no matching wheel found) ===")

    total = cs_passed + cs_failed
    print(f"\n=== Results: {cs_passed}/{total} passed, {cs_failed} failed ===")
    if all_errors:
        print("\nFailures:")
        for err in all_errors:
            print(f"  - {err}")

    return 0 if cs_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
