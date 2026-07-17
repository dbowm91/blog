# Release 3 Phase H — Diagnostics, Health, and Operational Readiness

## Objective

Create a single diagnostic framework and `devlog doctor` command that can identify configuration, filesystem, database, service, dependency, and deployment failures before operators resort to manual debugging.

This phase should reuse the typed configuration validator, RuntimePaths verification, service lifecycle adapters, health endpoints, and operational services established in Releases 1–3. It must not duplicate those checks with inconsistent logic.

## Scope

Implement:

```text
devlog doctor
devlog doctor --production
devlog doctor --json
devlog doctor --check CHECK_ID
devlog doctor --category CATEGORY
devlog doctor --fix-safe
```

`--fix-safe` is limited to explicitly reversible, non-destructive corrections such as creating missing empty runtime directories or correcting known managed-file permissions. It must never modify configuration values, regenerate secrets, migrate databases, restore backups, or overwrite unmanaged deployment files.

## Non-goals

- Do not build a general remote monitoring platform.
- Do not send telemetry externally.
- Do not perform destructive automatic repair.
- Do not replace health/readiness endpoints.
- Do not add update or restore behavior.

## Workstream H1 — diagnostic framework

Create a registry of typed checks.

Each check defines:

- stable check ID
- category
- description
- prerequisites
- severity policy
- production-required flag
- timeout
- safe-fix capability
- human remediation
- structured details schema

Result states:

```text
PASS
WARN
FAIL
SKIP
ERROR
```

Distinguish a failed check from a check that could not execute due to an internal diagnostic error.

Suggested categories:

- installation
- configuration
- secrets
- filesystem
- database
- search
- assets
- themes
- storage
- email
- Redis
- Celery
- scheduler
- backup
- deployment
- service
- proxy
- health
- capacity
- security

## Workstream H2 — execution engine

The engine should:

- resolve installation metadata and mode
- load typed effective configuration once
- resolve RuntimePaths once
- order checks by dependencies
- enforce per-check and total timeouts
- support parallel execution only for independent, side-effect-free checks
- redact secrets centrally
- collect timing information
- continue after individual check failures
- map required production failures to nonzero exit status

Avoid checks that instantiate multiple competing Flask applications or database pools unnecessarily.

## Workstream H3 — installation and configuration checks

Checks should include:

- package/CLI version consistency
- installation metadata version and completeness
- current release symlink correctness
- supported config schema version
- config path and environment-file selection
- unknown/deprecated keys
- production validation
- secret presence and placeholder detection
- secret-file ownership and permissions
- deployment mode/scope consistency
- stale or ambiguous installation metadata

## Workstream H4 — filesystem and capacity checks

Reuse `RuntimePaths` verification for:

- required directories
- ownership and permissions
- writable data/upload/theme/backup/export/log/runtime paths
- release directory and symlink
- symlink safety
- free disk space
- inode availability where practical
- filesystem type warnings relevant to SQLite
- Docker bind-mount UID/GID mismatch
- stale runtime files
- legacy checkout remnants after migration

Capacity thresholds must be configurable or clearly documented.

## Workstream H5 — database and migration checks

Checks:

- connectivity
- migration revision/current head
- SQLite integrity
- WAL checkpoint status
- database path matches RuntimePaths
- database file ownership/permissions
- FTS5 availability
- FTS schema/index health
- orphaned or failed migration state
- unsupported backend features
- basic latency

Do not run expensive full integrity checks by default if they can block a large production database. Offer a deep mode where necessary.

## Workstream H6 — application assets and themes

Checks:

- frontend manifest presence and parseability
- referenced static assets exist
- bundled theme catalog integrity
- selected dark/light themes resolve
- external theme directory validity
- accessibility policy result for selected themes
- package metadata and attribution presence
- uploads/static serving assumptions match deployment configuration

Preserve Halloy warm-path behavior; diagnostics may explicitly request refresh but should not force registry I/O for every status invocation.

## Workstream H7 — dependency and integration checks

Redis:

- configured URL parse
- connectivity
- selected database
- authentication failure classification
- required versus optional state

Celery:

- broker connectivity
- worker availability where enabled
- queue routing consistency
- version compatibility where available

Scheduler:

- exactly one owner
- active process/container
- next run and last run status
- stale lock/state detection

SMTP:

- configuration completeness
- DNS/connect/TLS/auth stages
- no message sent by default
- explicit opt-in send-test command may be separate

Storage:

- local writable roots
- S3 dependency/configuration/connectivity where selected
- non-destructive list/head probe

## Workstream H8 — deployment and service checks

Using Phase G adapters, check:

- managed deployment file presence
- deployment drift
- systemd/Compose syntax validity
- service enabled/running state
- process/container version
- executable/image matches installed metadata
- health and readiness endpoint response
- reverse-proxy reachability and forwarded-header behavior where safely testable
- localhost versus public bind assumptions
- stale PID/container metadata
- recent restart loop or failure status

## Workstream H9 — backup readiness checks

Before Release 4 full backup lifecycle, diagnostics should inspect current backup primitives:

- backup directory writable
- latest backup timestamp
- manifest parseability
- latest backup verification state
- encryption dependency/key presence when enabled
- retention policy sanity
- backup path not nested inside a source path that would recurse

Do not create a backup automatically unless explicitly requested through a separate command.

## Workstream H10 — output contract

Human output should group failures first and provide concise remediation.

JSON envelope should include:

```json
{
  "ok": false,
  "status": "failure",
  "code": "doctor.failed",
  "summary": "3 required checks failed",
  "details": {
    "mode": "system",
    "version": "1.0.0",
    "checks": []
  },
  "warnings": []
}
```

Each check entry includes stable ID, category, status, severity, duration, summary, safe details, and remediation.

Exit behavior:

- 0: all required checks pass; warnings allowed
- degraded code: only optional checks warn/fail
- nonzero failure: required check fails
- operational error code: diagnostic engine cannot complete

## Workstream H11 — safe fixes

Define a strict allowlist of safe fixes, such as:

- create missing empty runtime/log directory
- correct mode on a managed secret/config file
- remove stale owned PID file after confirming no process exists
- refresh a managed deployment hash after explicit confirmation only if content matches generated output

Every fix must:

- show a plan
- support dry run
- create an audit/result record
- be idempotent
- avoid changing user-authored configuration or content

## Workstream H12 — testing

Unit tests:

- registry and dependency ordering
- timeout behavior
- redaction
- severity/exit mapping
- JSON schema
- safe-fix allowlist

Integration tests:

- broken config
- missing secret
- wrong permissions
- missing assets
- stale migration
- corrupt SQLite fixture
- Redis unavailable
- duplicate scheduler ownership
- service stopped/failed
- deployment drift
- low disk mock

End-to-end tests:

- healthy native system installation
- healthy Docker installation
- intentionally broken installations with expected remediation
- `--production` required-check behavior
- `--fix-safe` dry run and application

## Explicit acceptance criteria

1. `devlog doctor` uses one shared diagnostic registry with stable check IDs.
2. Checks reuse existing configuration, filesystem, service, and operational primitives rather than duplicating logic.
3. Human and JSON outputs are deterministic, redacted, and test-covered.
4. Production-required failures return nonzero.
5. Optional unavailable services are SKIP or WARN, not false failures.
6. Database, migration, FTS, asset, theme, storage, Redis, Celery, scheduler, SMTP, backup readiness, deployment, and service checks are represented.
7. Per-check timeouts prevent indefinite hangs.
8. One failed check does not prevent unrelated checks from running.
9. No check mutates state unless invoked through the explicit safe-fix path.
10. Safe fixes are allowlisted, dry-run capable, idempotent, and reversible where applicable.
11. Secrets never appear in output, logs, exceptions, or JSON details.
12. Healthy native system and Docker installations pass production doctor runs.
13. Broken fixture installations produce the expected check IDs and remediation.
14. Doctor output includes installation mode, version, selected paths, and total duration.
15. Documentation explains check categories, exit codes, deep checks, and safe fixes.

## Definition of done

Phase H is complete when an operator can run one command and receive a trustworthy, machine-readable assessment of whether DevLog is correctly installed, configured, deployable, running, and recoverable enough to proceed with normal operations.
