from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CompletionInfo:
    mode: str
    config_path: str
    data_path: str
    base_url: str
    admin_username: str
    validation_ok: bool
    next_command: str
    warnings: list[str]


def render_completion_human(info: CompletionInfo) -> str:
    lines: list[str] = []
    lines.append("")
    lines.append("Onboarding Complete")
    lines.append("=" * 40)
    lines.append("")
    lines.append(f"  Mode:       {info.mode}")
    lines.append(f"  Config:     {info.config_path}")
    lines.append(f"  Data:       {info.data_path}")
    lines.append(f"  URL:        {info.base_url}")
    lines.append(f"  Admin:      {info.admin_username}")
    lines.append(f"  Valid:      {'yes' if info.validation_ok else 'no'}")
    lines.append("")

    if info.warnings:
        lines.append("Warnings:")
        for w in info.warnings:
            lines.append(f"  - {w}")
        lines.append("")

    lines.append("Next steps:")
    lines.append(f"  {info.next_command}")
    lines.append("")

    return "\n".join(lines)


def render_completion_json(info: CompletionInfo) -> str:
    return json.dumps(asdict(info), indent=2)
