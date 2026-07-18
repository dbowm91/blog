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
  --list-checks       List all available checks and exit
  --json              Output in JSON format
```

## Check Categories

| Category | Checks | Description |
|----------|--------|-------------|
| installation | 6 | Package version, metadata, release symlink, config path, deprecated keys, secret permissions, stale metadata |
| configuration | 3 | Config load, validation, deprecated keys |
| secrets | 4 | SECRET_KEY, ADMIN_PASSWORD, secret-file permissions |
| filesystem | 8 | Required dirs, ownership, writability, symlinks, inodes, FS type, Docker UID, stale files, legacy remnants |
| database | 8 | Connectivity, migration, integrity, FTS5, path match, WAL, ownership, orphaned migration, backend features |
| search | 2 | FTS5 availability, FTS schema health |
| assets | 2 | Vite manifest, referenced assets |
| themes | 4 | Bundled catalog, selected resolution, accessibility, attribution |
| redis | 2 | Connectivity, authentication |
| celery | 2 | Broker config, worker accessibility |
| scheduler | 2 | Running state, lock staleness |
| email | 2 | SMTP config, SMTP reachability |
| storage | 2 | Backend config, writability |
| deployment | 6 | Mode, drift, managed files, health endpoint, proxy, bind address, PID, restart loop |
| service | 2 | Service state, restart loop |
| backup | 4 | Directory readiness, manifest, encryption, retention |
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
        "safe_fix_id": null
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

- **Config loading**: Loaded once via `DoctorContext.config` (lazy, cached)
- **Path resolution**: Loaded once via `DoctorContext.paths` (lazy, cached)
- **Per-check timeout**: Each check runs in a daemon thread with `thread.join(timeout)`. If the thread is alive after timeout, an ERROR result is returned.
- **Total timeout**: Remaining checks are skipped if total elapsed time exceeds `total_timeout` (default 120s).
- **Flask app context**: Pushed into worker threads via `app.app_context()` for checks that need database access.
