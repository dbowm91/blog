#!/usr/bin/env python3
"""Compare runtime dependencies between pyproject.toml and requirements.txt."""

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower()).rstrip("-")


def parse_version(spec: str) -> str:
    return spec.split(">=")[-1].split("<")[0] if ">=" in spec else spec


def parse_requirements(path: Path) -> dict[str, list[str]]:
    deps: dict[str, list[str]] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.split("#")[0].split(";")[0].strip()
        if not line or line.startswith("-"):
            continue
        name = re.split(r"[>=<~!]", line, maxsplit=1)[0].strip()
        name = re.split(r"[\[]", name, maxsplit=1)[0]
        norm = normalize_name(name)
        deps.setdefault(norm, []).append(line)
    return deps


def parse_pyproject_deps(path: Path) -> dict[str, list[str]]:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    deps: dict[str, list[str]] = {}
    for spec in data.get("project", {}).get("dependencies", []):
        name = re.split(r"[>=<~!\[]", spec, maxsplit=1)[0].strip()
        norm = normalize_name(name)
        deps.setdefault(norm, []).append(spec)
    return deps


def compare_versions(pyproject_specs: list[str], requirements_specs: list[str]) -> bool:
    pyproject_versions = sorted(parse_version(s) for s in pyproject_specs)
    requirements_versions = sorted(parse_version(s) for s in requirements_specs)
    return pyproject_versions == requirements_versions


def main() -> int:
    pyproject_path = ROOT / "pyproject.toml"
    requirements_path = ROOT / "requirements.txt"

    if not pyproject_path.exists():
        print(f"ERROR: {pyproject_path} not found", file=sys.stderr)
        return 2
    if not requirements_path.exists():
        print(f"ERROR: {requirements_path} not found", file=sys.stderr)
        return 2

    pyproject_deps = parse_pyproject_deps(pyproject_path)
    requirements_deps = parse_requirements(requirements_path)

    pyproject_names = set(pyproject_deps.keys())
    requirements_names = set(requirements_deps.keys())

    missing_in_requirements = sorted(pyproject_names - requirements_names)
    extra_in_requirements = sorted(requirements_names - pyproject_names)
    version_mismatches: list[tuple[str, str, str]] = []

    for name in sorted(pyproject_names & requirements_names):
        if not compare_versions(pyproject_deps[name], requirements_deps[name]):
            version_mismatches.append(
                (
                    name,
                    " ".join(sorted(pyproject_deps[name])),
                    " ".join(sorted(requirements_deps[name])),
                )
            )

    has_drift = bool(missing_in_requirements or extra_in_requirements or version_mismatches)

    if not has_drift:
        print("OK: pyproject.toml and requirements.txt are in sync")
        return 0

    print("DRIFT DETECTED between pyproject.toml and requirements.txt:\n")

    if missing_in_requirements:
        print("In pyproject.toml but NOT in requirements.txt:")
        for name in missing_in_requirements:
            print(f"  - {name}: {', '.join(pyproject_deps[name])}")
        print()

    if extra_in_requirements:
        print("In requirements.txt but NOT in pyproject.toml:")
        for name in extra_in_requirements:
            print(f"  - {name}: {', '.join(requirements_deps[name])}")
        print()

    if version_mismatches:
        print("Version bound mismatches:")
        for name, pyproject_v, req_v in version_mismatches:
            print(f"  - {name}:")
            print(f"      pyproject.toml:  {pyproject_v}")
            print(f"      requirements.txt: {req_v}")
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
