"""Centralized output rendering for human and JSON modes."""

from __future__ import annotations

import json
import sys
from typing import Any

from devlog_cli.result import Result


def render_human(result: Result, *, verbose: bool = False, file: Any = None) -> None:
    out = file or sys.stderr
    if result.ok:
        print(result.summary, file=out)
    else:
        print(f"Error: {result.summary}", file=out)
    if verbose:
        for w in result.warnings:
            print(f"  Warning: {w}", file=out)
        for r in result.remediation:
            print(f"  Hint: {r}", file=out)
        if result.details:
            print(f"  Details: {json.dumps(result.details)}", file=out)


def render_json(result: Result, *, file: Any = None) -> None:
    out = file or sys.stdout
    print(result.to_json(indent=2), file=out)


def render(
    result: Result, *, json_mode: bool = False, verbose: bool = False, file: Any = None
) -> None:
    if json_mode:
        render_json(result, file=file or sys.stdout)
    else:
        render_human(result, verbose=verbose, file=file)
