# Deployment Architecture

## Overview

Phase G provides backend-aware deployment artifact generation and service lifecycle management. The deployment module generates systemd units, Docker Compose configurations, reverse proxy configs (Caddy/nginx), and logrotate configurations from typed configuration.

## Module Structure

```
app/deployment/
  model.py      — DeploymentContext and RenderResult types
  systemd.py    — Systemd unit renderers (web, worker, scheduler)
  compose.py    — Docker Compose renderers
  proxy.py      — Caddy and nginx renderers
  logrotate.py  — Logrotate config renderer
  install.py    — Atomic install transaction with backup/rollback
  drift.py      — Deployment drift detection
  lifecycle.py  — Backend-aware service lifecycle commands
```

## Deployment Context

`DeploymentContext` aggregates configuration, paths, and mode into a single context object. It is built from `DevLogConfig` and `InstallMode` via `DeploymentContext.from_config()`.

## Renderers

All renderers are pure functions: `render_*(ctx: DeploymentContext) -> RenderResult`. They produce text output with structured warnings and metadata. Renderers never embed secrets.

## Systemd Units

Systemd units include:
- Dedicated non-root user/group (system mode)
- EnvironmentFile for secrets
- ExecStartPre config validation and path checks
- Hardening: NoNewPrivileges, PrivateTmp, ProtectSystem=strict, ProtectHome=true
- ReadWritePaths for data/log/runtime directories
- Restart=on-failure with bounded restart behavior

Web, worker, and scheduler responsibilities are separated into distinct units.

## Docker Compose

Generated Compose includes:
- Web service with health checks
- Optional Redis, Celery worker, and scheduler services
- Loopback-only port publication
- Named volumes for persistence
- env_file references (no inline secrets)
- Resource limits

## Lifecycle Commands

`devlog start|stop|restart|status|logs` detect the service backend from installation metadata:
- System mode → systemd
- User mode → systemd user units
- Docker mode → Docker Compose
- Development → foreground guidance

All lifecycle commands use `subprocess.run` with list arguments (never `shell=True`).

## Drift Detection

`devlog deploy check` compares installed files against expected content hashes. It detects missing files, modified files, and unmanaged files.
