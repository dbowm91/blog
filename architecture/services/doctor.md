# Doctor — Diagnostic Framework

The `devlog doctor` command provides a single-command assessment of DevLog installation health. It identifies configuration, filesystem, database, service, dependency, and deployment failures before operators resort to manual debugging.

## Architecture

### Components

- **CheckRegistry** (`app/services/operations/doctor.py`) — Central registry of typed diagnostic checks. Each check has a stable ID, category, severity, timeout, and optional safe-fix capability.
- **DoctorContext** — Pre-loads config, paths, mode, and version once per doctor run. Shared across all checks via thread-local storage.
- **Execution Engine** — Runs checks sequentially with per-check timeouts (via threading) and a total timeout. Continues after individual failures. Enforces production-required check failures as nonzero exit.
- **Safe Fix System** — Allowlisted, idempotent, reversible corrections (e.g., create missing directories, remove stale PID files, rebuild FTS index).
- **Output Contract** — Human-readable (grouped by category, failures first) and JSON (structured envelope with checks, warnings, remediation).

### CLI Command

```
devlog doctor [OPTIONS]
  --production        Enforce production-required checks as failures
  --check CHECK_ID    Run a specific check by ID
  --category CAT      Filter checks by category
  --fix-safe          Apply safe fixes after checks
  --deep              Include expensive checks (SQLite integrity, WAL checkpoint)
  --no-parallel       Disable parallel check execution
  --list-checks       List all available checks and exit
  --json              Output in JSON format
```

## Check Categories

The registry holds **76 checks across 20 categories**. The counts below are the
measured values from `app/services/operations/doctor.py`.

| Category | Checks | Description |
|----------|--------|-------------|
| installation | 5 | Package version, metadata, release symlink, config path, deprecated keys, secret permissions, stale metadata |
| configuration | 3 | Config load, validation, deprecated keys |
| secrets | 3 | SECRET_KEY, ADMIN_PASSWORD, secret-file permissions |
| filesystem | 8 | Required dirs, ownership, writability, symlinks, inodes, FS type, Docker UID, stale files, legacy remnants |
| database | 8 | Connectivity, migration, integrity, FTS5, path match, WAL, ownership, orphaned migration, backend features |
| search | 2 | FTS5 availability, FTS schema health |
| assets | 3 | Vite manifest, referenced assets, upload serving |
| themes | 5 | Bundled catalog, selected resolution, accessibility, attribution, external dir |
| redis | 3 | Connectivity, authentication, database index |
| celery | 4 | Broker config, worker accessibility, routing config, version compatibility |
| scheduler | 4 | Running state, lock staleness, job execution, owner match |
| email | 2 | SMTP config, SMTP reachability |
| storage | 3 | Backend config, writability, S3 probe |
| deployment | 8 | Mode, drift, managed files, health endpoint, proxy, bind address, PID, restart loop, systemd syntax, process version, image match |
| service | 2 | Service state, restart loop |
| backup | 6 | Directory readiness, manifest, encryption, retention, verification, path nesting |
| security | 3 | Session config, secret validation, cookie security |
| health | 1 | Health endpoint reachable |
| capacity | 2 | Disk space, inodes |
| proxy | 1 | Reverse proxy config |

## Result States

| State | Meaning |
|-------|---------|
| PASS | Check passed |
| WARN | Non-critical issue detected |
| FAIL | Required check failed |
| SKIP | Check not applicable (e.g., not SQLite) |
| ERROR | Check raised an internal error |

## Severity Levels

| Level | Exit Behavior |
|-------|---------------|
| REQUIRED | Failure causes nonzero exit |
| RECOMMENDED | Failure causes degraded exit (8) |
| OPTIONAL | Failure causes degraded exit (8) |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All required checks pass (warnings allowed) |
| 1 | Required check failed |
| 8 | Only optional/recommended checks warn/fail |

## Safe Fixes

| Fix ID | Description | Applies To |
|--------|-------------|------------|
| create_missing_dirs | Create missing runtime directories | fs.required_dirs, backup.readiness |
| cleanup_stale_pid | Remove PID files for dead processes | deploy.pid |
| rebuild_fts | Rebuild FTS search index | db.fts5 |
| correct_permissions | Set .env file to mode 600 | install.secret_permissions |

Every safe fix:
- Shows a plan before execution
- Supports dry run
- Creates an audit record
- Is idempotent
- Avoids changing user-authored configuration

## Deep Checks

Deep checks are expensive (e.g., SQLite integrity scan, WAL checkpoint) and excluded by default. Use `--deep` to include them.

## JSON Output

```json
{
  "ok": false,
  "status": "failure",
  "code": "doctor.failed",
  "summary": "3 required check(s) failed",
  "details": {
    "mode": "system",
    "version": "1.0.0",
    "duration_ms": 1234.56,
    "checks": [
      {
        "check_id": "db.connectivity",
        "category": "database",
        "status": "pass",
        "severity": "required",
        "summary": "Database connected (1.2ms)",
        "duration_ms": 1.2,
        "details": {},
        "remediation": [],
        "safe_fix_id": null,
        "paths": ["app/services/operations/doctor.py:342"]
      }
    ],
    "safe_fix_plan": [
      {
        "fix_id": "create_missing_dirs",
        "description": "Create missing runtime directories",
        "targets": ["fs.required_dirs"],
        "actions": ["mkdir -p /var/lib/devlog/cache"]
      }
    ]
  },
  "warnings": ["..."],
  "remediation": ["..."]
}
```

## Secret Redaction

All check details are redacted before output. Keys containing "secret", "password", "token", "key", or "credential" have values masked (first 2 chars + asterisks + last 2 chars).

## Engine Details

- **Topological dependency ordering**: Checks declare optional dependencies. The engine resolves execution order so that prerequisites run before dependents, preventing redundant work and ensuring consistent state.
- **Parallel execution**: Checks are grouped into batches by dependency level. Checks within a batch run concurrently via threads. Between batches, the engine waits for all checks in the current batch to complete before starting the next. Controlled by `parallel=True` parameter (default: True). Use `--no-parallel` CLI flag to disable.
- **Automatic secret redaction**: The engine redacts values in check details before output. Keys containing "secret", "password", "token", "key", or "credential" have values masked (first 2 chars + asterisks + last 2 chars).
- **Dry-run mode**: Safe fixes support dry-run execution. The engine reports what would change without applying mutations, allowing operators to review before committing.
- **Paths in output**: Check results include source file paths and line numbers for diagnostics, enabling editors and IDEs to navigate directly to relevant code.
- **Operational error handling**: Checks that raise unexpected exceptions return an ERROR result with the traceback captured. The engine continues executing remaining checks and reports the error in the output without halting the run.
- **Config loading**: Loaded once via `DoctorContext.config` (lazy, cached)
- **Path resolution**: Loaded once via `DoctorContext.paths` (lazy, cached)
- **Per-check timeout**: Each check runs in a daemon thread with `thread.join(timeout)`. If the thread is alive after timeout, an ERROR result is returned.
- **Total timeout**: Remaining checks are skipped if total elapsed time exceeds `total_timeout` (default 120s).
- **Flask app context**: Pushed into worker threads via `app.app_context()` for checks that need database access.
