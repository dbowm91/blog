"""CLI context object passed through Click commands."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CliContext:
    config_path: Path | None = None
    env_file: Path | None = None
    json_mode: bool = False
    quiet: bool = False
    verbose: bool = False
    no_color: bool = False

    @classmethod
    def from_env(cls) -> CliContext:
        is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        return cls(no_color=not is_tty)

    def ensure_app_context(self) -> Any:
        """Construct Flask app and return it. Deferred import to avoid app creation for --help/--version."""
        from app import create_app

        return create_app()
