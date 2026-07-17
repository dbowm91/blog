from __future__ import annotations

from app.deployment.model import DeploymentContext, RenderResult


def render_logrotate(ctx: DeploymentContext) -> RenderResult | None:
    if not ctx.log_to_file:
        return None

    log_dir = ctx.paths.log_dir.path
    log_pattern = f"{log_dir}/*.log"
    user = ctx.service_user
    group = ctx.service_group

    lines: list[str] = []

    lines.append(f"{log_pattern} {{")
    lines.append("    daily")
    lines.append("    rotate 14")
    lines.append("    compress")
    lines.append("    delaycompress")
    lines.append("    missingok")
    lines.append("    notifempty")
    lines.append(f"    create 0640 {user} {group}")
    lines.append("    sharedscripts")
    lines.append("    postrotate")
    lines.append("        invoke-rc.d devlog restart > /dev/null 2>&1 || true")
    lines.append("    endscript")
    lines.append("}")

    content = "\n".join(lines) + "\n"

    return RenderResult(
        content=content,
        filename="devlog",
        managed=True,
        warnings=[],
        permissions=0o644,
        description="Logrotate configuration for DevLog log files",
    )
