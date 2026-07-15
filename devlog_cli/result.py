"""Typed result contract for CLI commands."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from devlog_cli.exit_codes import ExitCode


@dataclass
class Result:
    ok: bool
    status: str
    code: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    remediation: list[str] = field(default_factory=list)
    exit_code: ExitCode = ExitCode.SUCCESS

    @classmethod
    def success(cls, code: str, summary: str, **kwargs: Any) -> Result:
        return cls(ok=True, status="success", code=code, summary=summary, **kwargs)

    @classmethod
    def failure(
        cls, code: str, summary: str, exit_code: ExitCode = ExitCode.GENERAL_FAILURE, **kwargs: Any
    ) -> Result:
        return cls(
            ok=False, status="failure", code=code, summary=summary, exit_code=exit_code, **kwargs
        )

    @classmethod
    def degraded(cls, code: str, summary: str, **kwargs: Any) -> Result:
        return cls(
            ok=False,
            status="degraded",
            code=code,
            summary=summary,
            exit_code=ExitCode.DEGRADED,
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "ok": self.ok,
            "status": self.status,
            "code": self.code,
            "summary": self.summary,
            "warnings": self.warnings,
            "details": self.details,
        }
        if self.remediation:
            d["remediation"] = self.remediation
        return d

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
