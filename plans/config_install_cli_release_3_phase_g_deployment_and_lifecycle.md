# Release 3 Phase G — Deployment Generation and Service Lifecycle

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/deployment/managed-deployment.md](../architecture/deployment/managed-deployment.md); this file is the historical record.

## Objective

Provide supported, backend-aware deployment artifacts and lifecycle commands for systemd and Docker installations, with secure defaults, dry-run/print/install modes, and no dependence on repository-local commands.

This phase begins only after Release 2 closure proves installation metadata, RuntimePaths, and onboarding behavior in clean environments.

## Scope

Implement:

```text
devlog deploy systemd
devlog deploy compose
devlog deploy caddy
devlog deploy nginx
devlog deploy logrotate
devlog deploy all

devlog start
devlog stop
devlog restart
devlog status
devlog logs
```

Deployment commands should consume typed effective configuration, RuntimePaths, and installation metadata. They must not parse TOML independently or duplicate installer/onboarding path decisions.

## Non-goals

- Do not add application serving modes outside the existing WSGI/Granian deployment model.
- Do not implement Kubernetes, Nomad, or cloud-provider-specific deployment.
- Do not implement update/rollback; Release 4 owns lifecycle mutation.
- Do not make reverse-proxy installation mandatory.
- Do not silently invoke privileged changes without `--install` and clear confirmation.

## Workstream G1 — deployment model and renderer architecture

Create a typed deployment model representing:

- installation mode and native scope
- executable/release location
- config and secret paths
- data/log/runtime paths
- service user/group
- bind address and port
- public base URL
- proxy topology
- worker/process settings
- Redis/Celery/scheduler enablement
- health/readiness endpoints
- log strategy

Renderers should be pure functions returning text plus structured warnings. Installation adapters write files, set permissions, reload managers, and report results.

Suggested modules:

```text
app/deployment/model.py
app/deployment/systemd.py
app/deployment/compose.py
app/deployment/proxy.py
app/deployment/logrotate.py
app/deployment/install.py
app/services/operations/deploy.py
devlog_cli/commands/deploy.py
```

## Workstream G2 — systemd unit generation

Generate a hardened service unit using RuntimePaths and installation metadata.

Required properties:

- dedicated non-root user/group
- explicit `EnvironmentFile`
- explicit executable path through current release symlink
- `ExecStartPre` configuration validation
- `ExecStartPre` path/permission readiness check
- graceful stop and restart policy
- restrictive umask
- `NoNewPrivileges=true`
- `PrivateTmp=true`
- appropriate `ProtectSystem`
- appropriate `ProtectHome`
- writable-path allowlist
- explicit working directory independent of source checkout
- bounded restart behavior
- readiness-compatible startup timeout
- no shell interpolation for secrets

Support:

```text
--print
--output PATH
--install
--force
--dry-run
--user
```

System-wide units and user units must be separate templates with correct paths and manager commands.

## Workstream G3 — worker and scheduler units

When Celery or scheduler functionality is enabled, generate separate units rather than embedding multiple responsibilities in one process.

Define:

- web service
- optional Celery worker
- optional scheduler/beat service

Enforce exactly one scheduler owner. Configuration validation must reject ambiguous scheduler ownership.

Units must share the same release, config, environment, and runtime path contract.

## Workstream G4 — Docker Compose generation

Generate a Compose bundle from effective configuration and installation metadata.

Support:

- web service
- optional Redis
- optional Celery worker
- optional scheduler
- health checks
- persistent volumes
- loopback host publication by default
- explicit image version/digest
- non-root UID/GID contract
- configuration and secret mounts
- restart policy
- optional profiles

Generated Compose must not contain secret values. Use environment files or Docker secrets-compatible references.

Provide `--print`, `--output`, and `--install` behavior without overwriting user-modified bundles unless `--force` is explicit.

## Workstream G5 — Caddy and nginx generation

Generate reverse-proxy configuration from effective settings.

Include:

- public hostname
- upstream address
- trusted forwarded headers
- upload limits
- request and response timeouts
- static/upload serving ownership decision
- TLS assumptions
- compression ownership
- security-header ownership
- websocket support if needed
- health endpoint exclusions where appropriate

The renderer should warn if public URL, bind address, proxy count, and TLS assumptions conflict.

Do not install Caddy or nginx packages. `--install` may place configuration only when the target software is detected and the destination is explicit.

## Workstream G6 — logrotate generation

Generate logrotate only for file-based logs. If journald is the documented default, report that logrotate is unnecessary unless application file logging is enabled.

Include ownership, rotation count, compression, retention, and post-rotate behavior consistent with the application's logging implementation.

## Workstream G7 — deployment installation transaction

`devlog deploy ... --install` must:

1. validate effective configuration
2. validate RuntimePaths
3. render proposed files
4. show a plan in dry-run mode
5. back up existing managed files
6. write atomically with correct permissions
7. validate syntax where supported
8. reload the relevant manager
9. enable/start only when explicitly requested
10. restore previous files if validation/reload fails

Record managed deployment files in installation metadata.

## Workstream G8 — backend-aware lifecycle commands

Implement a backend detector using installation metadata, not process heuristics alone.

Lifecycle behavior:

- system installation -> systemd
- user installation -> systemd user unit or documented foreground backend
- Docker installation -> Compose
- development -> foreground/manual guidance

Commands:

```text
devlog start
devlog stop
devlog restart
devlog status
devlog logs
```

Requirements:

- no shell=True subprocesses
- structured command execution and timeout handling
- JSON status output
- distinguish installed, running, degraded, failed, and unmanaged
- status includes version, backend, PID/container, uptime, health, and config/path validation summary
- logs support follow, tail count, and component selection
- do not expose environment contents or secrets

## Workstream G9 — deployment drift detection

Store a renderer version and content hash for managed deployment files.

`devlog deploy ... --check` should identify:

- missing managed files
- user modifications
- stale executable/release paths
- stale image version
- changed config assumptions
- unmanaged files

Never overwrite drift automatically without explicit force or merge policy.

## Workstream G10 — testing

Unit tests:

- renderer output for every mode/profile
- quoting and path escaping
- secret exclusion
- systemd hardening directives
- Compose profile combinations
- proxy consistency warnings
- logrotate policy

Integration tests:

- systemd-analyze verify where available
- nginx `-t` and Caddy validation where available
- Docker Compose config validation
- atomic install and rollback
- lifecycle subprocess adapters
- drift detection

End-to-end tests:

- clean native system installation -> deploy systemd -> start -> health -> logs -> stop
- user installation lifecycle
- Docker deploy/start/replacement
- optional Redis/worker/scheduler combinations

## Explicit acceptance criteria

1. Deployment renderers consume typed configuration, RuntimePaths, and installation metadata only.
2. Generated systemd units pass static verification.
3. System units run as non-root and include the required hardening directives.
4. `ExecStartPre` rejects invalid configuration and invalid runtime paths.
5. Web, worker, and scheduler responsibilities are separated when enabled.
6. Exactly one scheduler owner is enforced.
7. Generated Compose passes `docker compose config` and contains no secret values.
8. Default host publication is loopback-only unless public exposure is explicit.
9. Caddy and nginx output reflects public URL, proxy, upload, timeout, and TLS configuration accurately.
10. Deployment installation is atomic and restores prior managed files on validation failure.
11. Existing unmanaged or modified files are not overwritten without explicit force.
12. Lifecycle commands select the backend from installation metadata.
13. Status and logs work for systemd and Docker and support stable JSON output.
14. Start/restart failure returns nonzero with actionable diagnostics.
15. Managed deployment drift is detectable.
16. Native system and Docker end-to-end lifecycle tests pass from installed artifacts.
17. No command depends on a source checkout or Node.js.
18. Documentation provides tested deployment flows for systemd, Docker, Caddy, and nginx.

## Definition of done

Phase G is complete when an installed DevLog instance can generate, validate, install, start, stop, inspect, and troubleshoot its supported service backend through `devlog`, with secure defaults and reversible deployment-file changes.
