# Operations Services (`app/services/operations/`)

The operational business-logic layer of DevLog. Every command an operator can
run — admin provisioning, database checks, media cleanup, export/import, theme
tooling, backup, deployment, onboarding, diagnostics — has its logic here
rather than in a command handler. The layer exists so that the same behaviour
can be reached from the standalone `devlog` CLI, from the Flask CLI
compatibility wrappers in `app/cli.py`, from admin routes, from the onboarding
step runner, and from tests, without any of those callers re-implementing the
operation or depending on a terminal.

## Module Files

| File | Owns |
|---|---|
| `app/services/operations/__init__.py` | Package facade; re-exports the public service functions under `__all__`, each import guarded by `try/except ImportError` so an optional dependency failure degrades to a missing name rather than a broken package import |
| `app/services/operations/results.py` | `OperationResult` base dataclass and 23 typed subclasses with stable operation codes |
| `app/services/operations/admin.py` | Admin user create / promote / password reset / list; password complexity policy |
| `app/services/operations/database.py` | SQLite integrity check, FTS5 index rebuild, migration status, migration apply |
| `app/services/operations/media.py` | Orphaned media scan (dry run) and apply (destructive) |
| `app/services/operations/transfer.py` | Site data export, import validation, import application |
| `app/services/operations/themes.py` | Theme list / validate / inspect / refresh / paths / accessibility facade over `app/themes/` |
| `app/services/operations/backup.py` | Backup create, verify, inspect with structured results |
| `app/services/operations/deploy.py` | Deployment render / install / drift check plus service lifecycle control |
| `app/services/operations/onboard.py` | Onboarding detect / plan / apply / resume over `app/onboarding/` |
| `app/services/operations/doctor.py` | Diagnostic check registry, execution engine, safe-fix registry, secret redaction |

Supporting pieces that are not in this package but are part of its contract:
`app/transaction.py` (`commit_with_rollback()`), `app/services/backup.py`
(encryption/compression primitives), `app/deployment/` (renderers and drift
engine), `app/onboarding/` (state, planner, steps), `app/themes/` (registry and
diagnostics), `devlog_cli/` (Click front end) and `app/cli.py` (Flask front
end).

## The Layer Contract

Service functions in this package obey four rules.

| Rule | Meaning |
|---|---|
| No terminal coupling | A service never imports Click, never prints, never writes to a stream, and never calls `sys.exit()` / raises `SystemExit`. |
| Application context required | A service reads `current_app`, the SQLAlchemy session, or app config, so the caller must have pushed an application context. |
| Typed result returned | Every entry point returns an `OperationResult` subclass carrying `ok`, a stable `code`, a human `summary`, structured `details`, `warnings` and `remediation`. |
| Explicit transaction boundary | Writes are committed through `commit_with_rollback()` from `app/transaction.py`, which rolls back and re-raises on `IntegrityError` / `SQLAlchemyError`. |

`commit_with_rollback()` lives in `app/transaction.py`:

```python
def commit_with_rollback() -> None:
    try:
        db.session.commit()
    except (IntegrityError, SQLAlchemyError):
        db.session.rollback()
        raise
```

### Stable Operation Codes

Every result carries a `code` string that callers, scripts and CI can branch
on. The codes are namespaced by domain and are part of the contract: a code
changes only with a deliberate edit.

| Domain | Code prefix | Examples |
|---|---|---|
| Admin | `admin.` | `admin.created`, `admin.promoted`, `admin.password_reset`, `admin.list` |
| Database | `db.` | `db.integrity.ok`, `db.integrity.failed`, `db.integrity.error`, `db.integrity.unsupported`, `db.search.rebuilt`, `db.search.rebuild_error`, `db.migration.status`, `db.migration.status_error`, `db.migration.applied`, `db.migration.failed` |
| Media | `media.` | `media.scan.complete`, `media.cleanup.complete` |
| Transfer | `export.` / `import.` | `export.success`, `import.valid`, `import.dry_run`, `import.success`, `import.unsupported_version` |
| Themes | `themes.` | `themes.list`, `themes.validate.ok`, `themes.validate.not_found`, `themes.validate.parse_error`, `themes.validate.translation_error`, `themes.validate.too_large`, `themes.inspect.ok`, `themes.inspect.not_found`, `themes.refresh.ok`, `themes.paths`, `themes.accessibility.ok`, `themes.accessibility.error` |
| Backup | `backup.` | `backup.create.ok`, `backup.create.failed`, `backup.create.db_not_found`, `backup.create.encryption_unavailable`, `backup.verify.ok`, `backup.verify.readable`, `backup.inspect.ok` |
| Deploy | `deploy.` / `lifecycle.` | `deploy.render.ok`, `deploy.render.context_error`, `deploy.install.ok`, `deploy.install.failed`, `deploy.install.no_files`, `deploy.check.clean`, `deploy.check.drift`, `lifecycle.status.ok`, `lifecycle.start.error`, `lifecycle.logs.ok` |
| Onboarding | `onboard.` | `onboard.detect`, `onboard.plan`, `onboard.applied`, `onboard.resumed`, `onboard.resume.complete`, `onboard.resume.failed`, `onboard.resume.no_metadata` |
| Doctor | `doctor.` | `doctor.ok`, `doctor.degraded`, `doctor.failed`, `doctor.engine_error` |

Secrets are never returned. `reset_admin_password()` returns only the
username; `create_backup_operation()` reports that the key is managed through
the `BACKUP_ENCRYPTION_KEY` environment variable and never echoes it.

## The Result Model

### `OperationResult`

`app/services/operations/results.py` defines the base class as a frozen
dataclass.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `ok` | `bool` | required | Whether the operation succeeded |
| `code` | `str` | required | Stable machine-readable operation code |
| `summary` | `str` | required | One-line human-readable outcome |
| `details` | `dict[str, Any]` | `{}` | Structured payload for the caller |
| `warnings` | `list[str]` | `[]` | Non-fatal observations |
| `remediation` | `list[str]` | `[]` | Suggested operator actions |

`OperationResult.to_dict()` emits `ok`, `code`, `summary`, `details` and
`warnings`, and adds `remediation` only when it is non-empty.

The dataclass is frozen, but `details`, `warnings` and `remediation` are
mutable containers, so a result is not deeply immutable.

### Typed Subclasses

Subclasses add domain payload fields on top of the base. There are **23**
subclasses in `results.py` and a further **4** defined locally in
`deploy.py`, for **27** `OperationResult` subclasses in the package.

| Domain | Result class | Added fields |
|---|---|---|
| Admin | `AdminCreatedResult` | `username` |
| Admin | `AdminPromotedResult` | `username` |
| Admin | `AdminPasswordResetResult` | `username` |
| Admin | `AdminListResult` | `admins` |
| Database | `DatabaseCheckResult` | `backend`, `healthy` |
| Database | `SearchRebuildResult` | `indexed_count` |
| Database | `MigrationStatusResult` | `current_head`, `pending_count` |
| Media | `MediaCleanupResult` | `orphaned_deleted`, `missing_cleared` |
| Transfer | `ExportResult` | `posts`, `subscribers`, `tags`, `pages`, `path` |
| Transfer | `ImportResult` | `posts`, `subscribers`, `tags`, `pages` |
| Theme | `ThemeListResult` | `themes`, `total` |
| Theme | `ThemeValidationResult` | `valid`, `theme_name` |
| Theme | `ThemeInspectResult` | `theme_name`, `css_vars` |
| Theme | `ThemeRefreshResult` | `old_count`, `new_count`, `added`, `removed` |
| Theme | `ThemePathsResult` | `paths` |
| Theme | `AccessibilityReportResult` | `total_themes`, `passed_exact`, `passed_with_exceptions`, `failed`, `reports` |
| Backup | `BackupCreateResult` | `path`, `verified` |
| Backup | `BackupVerifyResult` | `path`, `valid` |
| Backup | `BackupInspectResult` | `path`, `file_size`, `is_sqlite`, `is_compressed`, `is_encrypted` |
| Onboarding | `OnboardDetectResult` | `state`, `config_exists`, `database_exists`, `admin_exists` |
| Onboarding | `OnboardPlanResult` | `actions`, `action_count` |
| Onboarding | `OnboardApplyResult` | `config_path`, `data_path`, `admin_username`, `migration_head`, `steps_completed`, `steps_total`, `next_command` |
| Onboarding | `OnboardResumeResult` | `last_step`, `last_step_index`, `stopped_at`, `stopped_reason`, `completed` |
| Deploy (`deploy.py`) | `DeployRenderResult` | `files` |
| Deploy (`deploy.py`) | `DeployInstallResult` | `installed_files` |
| Deploy (`deploy.py`) | `DeployCheckResult` | `clean`, `drift_count` |
| Deploy (`deploy.py`) | `LifecycleResult` | `status`, `backend`, `details` |

`doctor.py` deliberately does **not** use `OperationResult`. It defines its own
frozen dataclasses, `CheckResult` and `DoctorResult`, because a diagnostic run
has a different shape from a single operation (a list of per-check results, a
run status, and a safe-fix plan).

## Service Modules

| Module | Responsibilities | Public functions |
|---|---|---|
| `admin.py` | Admin account lifecycle. Centralises the password policy in `_check_password_complexity()`: at least 8 characters and at least three of lowercase, uppercase, digit, special character. Raises `ValueError` for a policy violation or a missing user, and `ConflictError` for an existing user (`create_admin()`) or an already-admin user (`promote_admin()`). | `create_admin()`, `promote_admin()`, `reset_admin_password()`, `list_admins()` |
| `database.py` | Database health and schema state. `check_database_integrity()` runs `PRAGMA integrity_check` on SQLite and reports `db.integrity.unsupported` on other dialects. `rebuild_search_index()` calls `app.search.rebuild_fts()` and counts published posts. `get_migration_status()` and `run_migrations()` wrap Flask-Migrate. | `check_database_integrity()`, `rebuild_search_index()`, `get_migration_status()`, `run_migrations()` |
| `media.py` | Orphaned media handling. `scan_orphaned_media()` is the read-only dry run; `apply_orphaned_media_cleanup()` deletes unreferenced files and clears `Post.image` for rows pointing at missing files. Filenames are filtered by `_is_safe_filename()`, which rejects empty, dot-prefixed, separator-bearing and `..` names. | `scan_orphaned_media()`, `apply_orphaned_media_cleanup()` |
| `transfer.py` | Site data portability. `export_site_data()` writes atomically (temp file plus `os.replace`) and raises `FileExistsError` unless `force=True`. `validate_import()` is read-only. `import_site_data()` supports `dry_run`, skips duplicates by slug or email, and commits per entity type. `SUPPORTED_EXPORT_VERSIONS = {1}`. | `export_site_data()`, `validate_import()`, `import_site_data()` |
| `themes.py` | CLI-facing facade over `app/themes/`. Lists descriptors, validates a theme file or a registered name, inspects one theme (CSS, CSS variables, accessibility findings, dark/light classification), refreshes the registry and reports added/removed themes, reports bundled/external paths and configuration, and runs the catalog-wide WCAG contrast pass. | `list_theme_descriptors()`, `validate_theme()`, `inspect_theme()`, `refresh_theme_registry()`, `get_theme_paths()`, `run_accessibility_check()` |
| `backup.py` | Backup lifecycle with structured results. `create_backup_operation()` delegates the actual work to `app.services.backup.create_backup()` and then verifies the artifact. `verify_backup()` checks existence, size and SQLite integrity. `inspect_backup()` classifies a file as SQLite, gzip or possibly encrypted from its magic bytes. | `create_backup_operation()`, `verify_backup()`, `inspect_backup()` |
| `deploy.py` | Deployment artefact generation and service lifecycle. Renders systemd units, Compose files, Caddy and Nginx configuration and logrotate rules from a `DeploymentContext`, plans and executes installation with drift tracking, and drives the detected service backend (`systemd`, `systemd_user`, `docker`, `foreground` or `unknown`) for start/stop/restart/status/logs. | `deploy_render()`, `deploy_install()`, `deploy_check()`, `lifecycle_status()`, `lifecycle_start()`, `lifecycle_stop()`, `lifecycle_restart()`, `lifecycle_logs()` |
| `onboard.py` | First-run and reconfiguration. Wraps `app/onboarding/` state detection, planning, the step runner and the metadata record so that onboarding can be driven from a CLI, a script, or a test. | `detect_installation()`, `generate_plan()`, `apply_onboarding()`, `resume_onboarding()` |
| `doctor.py` | Diagnostics. A registry of named checks, an execution engine, an allowlisted safe-fix registry and detail redaction. Covered in detail below and in [Doctor](doctor.md). | `run_doctor()`, `register_check()`, `get_registry()`, `get_safe_fix_plan()`, `register_safe_fix()`, `register_safe_fix_runner()`, `redact_details()` |

## Consumer Flows

Two front ends call the same services.

CLI command flow:

```
CLI handler -> CliContext.ensure_app_context() -> call service function -> render Result
```

Flask compatibility flow:

```
Flask command wrapper -> call same service function -> render compatibility output
```

In the standalone CLI, `CliContext.ensure_app_context()` (`devlog_cli/context.py`)
builds the Flask app lazily — the import is deferred so `--help` and
`--version` do not pay for app creation — and the handler pushes
`app.app_context()` around the service call. The service's `OperationResult` is
then converted into a `devlog_cli.result.Result`, which carries an
`ExitCode` and is rendered by `devlog_cli/output.py:render()` in either human
or JSON mode. Exit codes come from `devlog_cli/exit_codes.py`:
`SUCCESS=0`, `GENERAL_FAILURE=1`, `INVALID_USAGE=2`, `INVALID_CONFIG=3`,
`MISSING_DEPENDENCY=4`, `DATABASE_ERROR=5`, `SERVICE_ERROR=6`,
`BACKUP_ERROR=7`, `DEGRADED=8`.

In `app/cli.py`, the Flask commands are thin compatibility wrappers. They
import the service inside the command body, call it, and echo the summary —
for example `rebuild-search` calls `rebuild_search_index()` and echoes
`result.summary`, and `cleanup-orphaned-images` calls
`apply_orphaned_media_cleanup()` and echoes the two counters. Prompts, JSON
formatting and `SystemExit` codes stay in the wrapper.

### Command Surface

| Service module | `devlog` commands | Flask CLI commands |
|---|---|---|
| `admin.py` | `devlog admin create`, `promote`, `reset-password`, `list` | `flask create-admin`, `flask promote-admin` |
| `database.py` | `devlog db check`, `rebuild-search`, `status`, `migrate` | `flask check-integrity`, `flask rebuild-search` |
| `media.py` | `devlog media scan`, `cleanup` | `flask cleanup-orphaned-images` |
| `transfer.py` | `devlog data export`, `import` | `flask export-data`, `flask import-data` |
| `themes.py` | `devlog themes list`, `validate`, `inspect`, `refresh`, `paths`, `accessibility` | `flask themes list`, `validate`, `inspect`, `refresh`, `paths`, `accessibility` |
| `backup.py` | `devlog backup create`, `verify`, `inspect` | — |
| `deploy.py` | `devlog deploy render`, `install`, `check`; `devlog lifecycle start`, `stop`, `restart`, `status`, `logs` | — |
| `onboard.py` | `devlog onboard detect`, `plan`, `run`, `resume` | — |
| `doctor.py` | `devlog doctor` (with `--production`, `--check`, `--category`, `--fix-safe`, `--deep`, `--no-parallel`, `--list-checks`) | — |

Two callers sit outside the CLI front ends and use the services directly:
`app/routes/admin/media.py:cleanup_orphaned_images()` calls
`apply_orphaned_media_cleanup()` and returns the
`(orphaned_deleted, missing_cleared)` tuple, and `app/onboarding/steps.py`
calls `run_migrations()` and `create_admin()` as onboarding steps.

## Doctor in the Operations Layer

`app/services/operations/doctor.py` is the largest module in the package
(4,078 lines). It contributes four things to the layer:

1. **A check registry.** `CheckRegistry` maps a `CheckDefinition`
   (`check_id`, `category`, `description`, `severity`, `production_required`,
   `timeout_seconds`, `safe_fix_id`, `remediation`, `prerequisites`, `deep`) to
   a runner function. `register_check()` populates it; `get_registry()` and
   `list_checks()` read it.
2. **An execution engine.** `run_doctor()` resolves the requested check set,
   topologically sorts it, runs checks in dependency-level batches on daemon
   threads with a per-check timeout and a total timeout (default 120s), pushes
   the Flask app context into each worker thread, redacts details, and
   continues after individual failures.
3. **An allowlisted safe-fix registry.** `register_safe_fix()` and
   `register_safe_fix_runner()` bind a `fix_id` to a description, a target
   `check_id` and a runner returning `(ok, detail)`. Only a fix that is
   registered in both maps can run; a check opts in by returning a
   `safe_fix_id` on its result.
4. **Detail redaction.** `redact_details()` masks values whose key contains
   `secret`, `password`, `token`, `key` or `credential`, recursing into nested
   dictionaries.

Overall status is derived from severity: any `REQUIRED` check that fails or
errors gives `doctor.failed` and a nonzero exit; otherwise any non-required
check that warns or fails gives `doctor.degraded` (exit 8); otherwise
`doctor.ok`.

### Check Categories

76 checks are registered across 20 categories.

| Category | Checks | Check IDs |
|---|---|---|
| installation | 5 | `pkg.version`, `install.metadata`, `install.release_symlink`, `install.config_path`, `install.stale_metadata` |
| configuration | 3 | `config.load`, `config.validate`, `install.deprecated_keys` |
| secrets | 3 | `secrets.secret_key`, `secrets.admin_password`, `install.secret_permissions` |
| filesystem | 8 | `fs.required_dirs`, `fs.symlink_safety`, `fs.ownership`, `fs.writable`, `fs.type`, `fs.docker_uid`, `fs.stale_files`, `fs.legacy_remnants` |
| database | 8 | `db.connectivity`, `db.migration_head`, `db.sqlite_integrity`, `db.path_match`, `db.wal_checkpoint`, `db.ownership`, `db.orphaned_migration`, `db.backend_features` |
| search | 2 | `db.fts5`, `db.fts_health` |
| assets | 3 | `assets.frontend_manifest`, `assets.referenced`, `assets.upload_serving` |
| themes | 5 | `themes.bundled`, `themes.selected`, `themes.accessibility`, `themes.attribution`, `themes.external_dir` |
| storage | 3 | `dep.storage`, `dep.storage_writable`, `dep.storage_s3_probe` |
| email | 2 | `dep.smtp`, `dep.smtp_connect` |
| redis | 3 | `dep.redis`, `dep.redis_auth`, `dep.redis_db` |
| celery | 4 | `dep.celery`, `dep.celery_workers`, `dep.celery_routing`, `dep.celery_version` |
| scheduler | 4 | `dep.scheduler`, `dep.scheduler_stale`, `dep.scheduler_runs`, `dep.scheduler_owner` |
| backup | 6 | `backup.readiness`, `backup.manifest`, `backup.encryption`, `backup.retention`, `backup.verification`, `backup.path_nesting` |
| deployment | 8 | `deploy.mode`, `deploy.drift`, `deploy.files`, `deploy.bind`, `deploy.pid`, `deploy.systemd_syntax`, `deploy.process_version`, `deploy.image_match` |
| service | 2 | `deploy.service_state`, `deploy.restart_loop` |
| proxy | 1 | `deploy.proxy` |
| health | 1 | `deploy.health_endpoint` |
| capacity | 2 | `fs.disk_space`, `fs.inodes` |
| security | 3 | `security.session`, `security.secrets`, `security.cookie` |

Severity distribution: 6 `REQUIRED`, 27 `RECOMMENDED`, 43 `OPTIONAL`. Ten
checks additionally carry `production_required=True`, and two are deep checks
(`db.sqlite_integrity`, `db.wal_checkpoint`) that are excluded unless `--deep`
is passed.

### Safe Fixes

Four safe fixes are registered.

| Fix ID | Description | Emitted by |
|---|---|---|
| `create_missing_dirs` | Create missing runtime directories | `fs.required_dirs`, `backup.readiness`, `dep.storage_writable` |
| `cleanup_stale_pid` | Remove PID files for dead processes | `deploy.pid` |
| `rebuild_fts` | Rebuild the FTS5 search index | `db.fts5` |
| `correct_permissions` | Set `.env` file to mode 600 | — |

The allowlist is enforced in two places: `get_safe_fix_plan()` only returns
fixes present in `_SAFE_FIXES`, and `_apply_safe_fixes()` only runs a fix that
has both a registered description and a registered runner. A check opts in by
returning `safe_fix_id` on its `CheckResult`; the runner receives that result
and returns `(ok, detail)`. With `--fix-safe --dry-run` the engine reports the
plan instead of applying it.

Full command reference, JSON schema and per-check documentation: [Doctor
— Diagnostic Framework](doctor.md).

## Notes and Gotchas

**Failures are not always results.** The layer's contract is "return a typed
result", but several entry points raise instead:
`create_admin()`, `promote_admin()` and `reset_admin_password()` raise
`ValueError` (password policy, or user not found) and `ConflictError` (user
already exists, or is already an admin); `export_site_data()` raises
`FileExistsError`; `apply_onboarding()` raises `ValueError` when the admin
password is missing or a step fails. Callers must catch these — both `app/cli.py`
and `devlog_cli/commands/admin.py` do. Note that `ConflictError` is defined at
the bottom of `admin.py`, after the functions that raise it.

**`pending_count` is always zero.** `get_migration_status()` and
`run_migrations()` both construct `MigrationStatusResult` with
`pending_count=0`. Nothing in the layer computes the number of pending
migrations, so the field is currently uninformative.

**Import does not populate the FTS index.** In `import_site_data()`, the
`sync_fts()` loop runs only for posts that already existed before the import
(`if existing and post_data.get("tags")`), and the whole block sits inside
`if imported_posts > 0:`. Newly imported posts are therefore never synced.
Run `devlog db rebuild-search` after an import to make the new posts
searchable.

**`media.py` bypasses `commit_with_rollback()`.** `apply_orphaned_media_cleanup()`
calls `db.session.commit()` directly, so a failure during that commit leaves
the session without the rollback the layer convention provides. This is the
only mutating service that does so.

**`verify_backup()` reports `valid=True` for an unverifiable file.** When
`_quick_verify()` cannot open the file as SQLite — the normal case for a
compressed or encrypted backup — the function returns `ok=True`, `valid=True`
and the code `backup.verify.readable` with a warning. `valid` means "readable",
not "integrity confirmed"; only `backup.verify.ok` means the integrity check
ran and passed.

**`app/services/operations/__init__.py` duplicates the `deploy` import block.**
The same `try: from app.services.operations.deploy import ...` block appears
twice, so `__all__` lists the eight deploy names twice. The package also does
not re-export `doctor` or `results`; callers import those by module path.

**`deploy.py` keeps its result classes local.** `DeployRenderResult`,
`DeployInstallResult`, `DeployCheckResult` and `LifecycleResult` are defined in
`deploy.py` rather than in `results.py`, unlike every other module.
`LifecycleResult` also re-declares the inherited `details` field.

**`doctor` does not use `OperationResult`.** `CheckResult` and `DoctorResult`
are separate frozen dataclasses. `DoctorResult.to_dict()` nests the per-check
list under `details.checks`, so a doctor payload is not shaped like the other
results.

**`run_doctor(production=True)` currently changes nothing.** The `production`
argument is accepted but never read: `run_doctor()` always calls
`list_checks(..., production_only=False)`, and the failure criterion is
`severity == REQUIRED` regardless of mode. The `production_required=True` flag
on ten check definitions is reachable only through
`list_checks(production_only=True)`, which `run_doctor()` never calls. The
`devlog doctor --production` flag therefore only echoes the per-check field
into the JSON payload.

**Doctor ordering is currently inert.** No check declares `prerequisites`, so
`_topological_sort()` preserves registry order and `_batch_by_level()` places
all 76 checks in a single level — that is, one fully parallel batch. The
dependency machinery works but has no graph to act on today.

**`correct_permissions` is registered but unreachable.** No check ever returns
`safe_fix_id="correct_permissions"`, so `get_safe_fix_plan()` and
`_apply_safe_fixes()` can never select it. `install.secret_permissions` does
not advertise it.

**Redaction is key-name based.** `redact_details()` masks a value only when
its *key* contains `secret`, `password`, `token`, `key` or `credential`. A
secret stored under an unrelated key name is not masked.

**`themes.py` imports a private symbol.** `from app.themes.resources import
_MAX_EXTERNAL_FILE_SIZE` reaches into another module's private namespace for
the size cap used by `validate_theme()` and `get_theme_paths()`.

**Destructive operations.** `apply_orphaned_media_cleanup()` deletes files and
clears `Post.image` values; `import_site_data()` writes posts, subscribers,
tags and pages; `deploy_install()` writes deployment artefacts to the
filesystem; `run_migrations()` applies schema migrations; `lifecycle_stop()`
and `lifecycle_restart()` stop a running service. Only the media cleanup and
the import have a read-only counterpart (`scan_orphaned_media()`,
`validate_import()` / `dry_run=True`). `export_site_data()` refuses to
overwrite an existing file unless `force=True`.

**Documentation drift in `architecture/services/doctor.md`.** The category
table in that document lists installation 6, secrets 4 and deployment 9
(68 checks in total) against the 5 / 3 / 8 actually registered (76). The same
document states that every safe fix "creates an audit record" — no audit
record is written by `_apply_safe_fixes()` — and its JSON example shows a
`paths` array per check and `targets`/`actions` keys in `safe_fix_plan`
entries, none of which the code emits. The root `AGENTS.md` describes the
doctor service as "76 check implementations across 14 categories"; the
registry uses 20.

**`architecture/services/overview.md` module table is incomplete.** It lists
seven modules and omits `deploy.py`, `onboard.py` and `doctor.py`. The root
`AGENTS.md` "Operations services" row lists the same seven and omits the same
three, while its separate "Doctor service" row lists the doctor module
correctly.

## See Also

- [Services Overview](overview.md) - The wider `app/services/` layer
- [Doctor](doctor.md) - The diagnostic check framework in full
- [Backup Service](backup.md) - Backup creation, encryption and retention
- [Serialization](serialization.md) - The JSON export/import format
- [Search Provider](search.md) - Full-text search abstraction
- [App Factory](../core/app-factory.md) - Application construction and context
- [Configuration](../core/configuration.md) - Typed configuration model
- [Models](../core/models.md) - The SQLAlchemy models these services mutate
- [Installation](../deployment/installation.md) - Install-time flow that onboarding drives
- [Deployment](../deployment/deployment.md) - Deployment artefacts and drift
- [Scheduler](../tasks/scheduler.md) - The scheduler the doctor checks
- [Filesystem Layout](../../docs/filesystem-layout.md) - Canonical path resolution
- [Theme Operator Guide](../../docs/themes/operator-guide.md) - Theme CLI operations
