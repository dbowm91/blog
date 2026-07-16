#!/usr/bin/env python3
"""Generate SHA-256 checksums manifest for release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_checksums(directory: Path, output: Path | None = None) -> bool:
    if not directory.is_dir():
        print(f"ERROR: directory not found: {directory}", file=sys.stderr)
        return False

    artifacts = sorted(p for p in directory.iterdir() if p.is_file())
    if not artifacts:
        print(f"ERROR: no files found in {directory}", file=sys.stderr)
        return False

    lines: list[str] = []
    for artifact in artifacts:
        sha = compute_sha256(artifact)
        lines.append(f"{sha}  {artifact.name}")

    output_path = output or directory / "checksums.txt"
    output_path.write_text("\n".join(lines) + "\n")

    print(f"Generated checksums for {len(artifacts)} files -> {output_path}")
    for line in lines:
        print(f"  {line}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate SHA-256 checksums for release artifacts."
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path("dist"),
        help="Directory containing artifacts (default: dist/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for checksums file (default: <directory>/checksums.txt)",
    )
    args = parser.parse_args(argv)

    ok = generate_checksums(args.directory, args.output)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
