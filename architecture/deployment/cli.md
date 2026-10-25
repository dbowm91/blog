# Operator CLI (`devlog_cli/`)

The `devlog` command is the standalone operator interface to a DevLog deployment. It is a
Click application that shares no code path with the Flask app: it builds a `CliContext`, calls a
service function, renders a `Result`, and exits with a stable exit code. The console script is
registered in `pyproject.toml` under `[project.scripts]` as `devlog = "devlog_cli.main:main"`, and
the package ships as `devlog_cli*` in the wheel. It is the primary surface for installing,
configuring, diagnosing and operating a running instance — the Flask CLI in `app/cli.py` is a
compatibility wrapper over the same services, not the primary interface.

## Module Files

| File | Owns |
|------|------|
| `devlog_cli/__init__.py` | Package version, read from installed distribution metadata via `importlib.metadata.version("devlog")`, falling back to `"0.0.0-dev"` when the distribution is not installed |
| `devlog_cli/main.py` | Root Click group `main`, global flags, and registration of every sub-group and top-level command |
| `devlog_cli/context.py` | `CliContext` dataclass and `ensure_app_context()` — the bridge to the Flask app |
| `devlog_cli/result.py` | `Result` dataclass, its `success` / `failure` / `degraded` factories, and JSON serialization |
| `devlog_cli/output.py` | `render_human()`, `render_json()` and the `render()` dispatcher |
| `devlog_cli/errors.py` | Domain exception hierarchy with per-class exit codes and stable error codes |
| `devlog_cli/exit_codes.py` | `ExitCode` IntEnum — the stable process exit status set |
| `devlog_cli/commands/__init__.py` | Empty package marker |
| `devlog_cli/commands/config.py` | `config` group — reads and writes configuration through `app/config/` |
| `devlog_cli/commands/admin.py` | `admin` group — admin user management |
| `devlog_cli/commands/db.py` | `db` group — integrity check, FTS rebuild, migrations |
| `devlog_cli/commands/themes.py` | `themes` group — catalog inspection and validation |
| `devlog_cli/commands/backup.py` | `backup` group — backup create / verify / inspect |
| `devlog_cli/commands/data.py` | `data` group — site data export / import |
| `devlog_cli/commands/media.py` | `media` group — orphaned media scan / cleanup |
| `devlog_cli/commands/onboard.py` | `onboard` group — first-run detection, planning and execution |
| `devlog_cli/commands/paths.py` | `paths` group — filesystem layout reporting and migration planning |
| `devlog_cli/commands/deploy.py` | `deploy` group — rendering and installing host-level configuration |
| `devlog_cli/commands/doctor.py` | `doctor` command — diagnostic check runner |
| `devlog_cli/commands/lifecycle.py` | `start`, `stop`, `restart`, `status`, `logs` — service lifecycle control |

## Invocation Contract

### Root group

`devlog_cli.main:main` is a Click group declared with `invoke_without_command=True`. Invoking
`devlog` with no subcommand renders the same result as `devlog version`. `--version` is Click's
`version_option` and prints `devlog, version <x>` before the group callback runs, so no
application is constructed for `--help` or `--version`.

### Global flags

| Flag | Context field | Effect |
|------|---------------|--------|
| `--version` | — | Print the version and exit |
| `--config PATH` | `config_path` | Path to the config file (must exist) |
| `--env-file PATH` | `env_file` | Path to the `.env` file (must exist) |
| `--json` | `json_mode` | Emit the JSON result envelope instead of human output |
| `-q`, `--quiet` | `quiet` | Intended to suppress non-error output |
| `-v`, `--verbose` | `verbose` | Include warnings, remediation hints and details in human output |
| `--no-color` | `no_color` | Intended to disable coloured output |

Because these are options of the root group, they must appear **before** the subcommand:
`devlog --json admin list`, not `devlog admin list --json`. Most groups additionally define their
own `--json` option, which is OR-ed with the global one — see [Notes and Gotchas](#notes-and-gotchas).

### Top-level surface

| Command | Kind | Purpose |
|---------|------|---------|
| `admin` | group | Manage admin users |
| `backup` | group | Backup and restore |
| `config` | group | Manage DevLog configuration |
| `data` | group | Import and export site data |
| `db` | group | Database operations |
| `deploy` | group | Deployment operations |
| `doctor` | command | Run diagnostic checks to assess installation health |
| `logs` | command | Show DevLog service logs |
| `media` | group | Media management |
| `onboard` | group | First-run and reconfiguration onboarding |
| `paths` | group | Manage filesystem paths and layout |
| `restart` | command | Restart the DevLog service |
| `start` | command | Start the DevLog service |
| `status` | command | Show DevLog service status |
| `stop` | command | Stop the DevLog service |
| `themes` | group | Theme management |
| `version` | command | Show DevLog version information |

The `lifecycle` commands are registered directly on the root group, so they are
`devlog start` rather than `devlog lifecycle start`.

## `CliContext`

`CliContext` is the object stored in `ctx.obj` by the root group callback and read by every
command via `ctx.obj`.

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `config_path` | `Optional[Path]` | `None` | Config file path from `--config` |
| `env_file` | `Optional[Path]` | `None` | Env file path from `--env-file` |
| `json_mode` | `bool` | `False` | JSON output requested |
| `quiet` | `bool` | `False` | Quiet mode requested |
| `verbose` | `bool` | `False` | Verbose output requested |
| `no_color` | `bool` | `False` | Colour suppression requested |

`CliContext.from_env()` is a classmethod that returns a context with `no_color` set to
`not sys.stdout.isatty()`. It is never called anywhere in the codebase.

`ensure_app_context()` imports `create_app` from `app` lazily — the deferred import keeps
`--help` and `--version` from building an application — and returns the app object. Callers push
the context themselves:

```python
app = cli_ctx.ensure_app_context()
with app.app_context():
    result = some_service_function()
```

`create_app()` takes no arguments, so `ensure_app_context()` does **not** propagate `config_path`
or `env_file` into the application; the app resolves its own configuration through
`load_effective_config()`.

## The `Result` Model

### Fields

| Field | Type | Meaning |
|-------|------|---------|
| `ok` | `bool` | Whether the operation succeeded |
| `status` | `str` | `"success"`, `"failure"` or `"degraded"` |
| `code` | `str` | Stable dotted operation code |
| `summary` | `str` | One-line human summary |
| `details` | `dict[str, Any]` | Structured payload |
| `warnings` | `list[str]` | Non-fatal warnings |
| `remediation` | `list[str]` | Suggested operator actions |
| `exit_code` | `ExitCode` | Process exit status to use |

### Factories

| Factory | `ok` | `status` | `exit_code` |
|---------|-----|----------|-------------|
| `Result.success(code, summary, **kwargs)` | `True` | `"success"` | `ExitCode.SUCCESS` |
| `Result.failure(code, summary, exit_code=ExitCode.GENERAL_FAILURE, **kwargs)` | `False` | `"failure"` | Caller-supplied |
| `Result.degraded(code, summary, **kwargs)` | `False` | `"degraded"` | `ExitCode.DEGRADED` |

`degraded` deliberately sets `ok=False`, so a degraded run is not reported as a success even
though the operation completed.

### Serialization

`to_dict()` produces `{"ok", "status", "code", "summary", "warnings", "details"}`, adding
`"remediation"` only when the list is non-empty. `to_json(indent=None)` serializes it with
`ensure_ascii=False`.

This envelope is the CLI's own contract. It is not the same shape as the service-layer
`OperationResult` in `app/services/operations/results.py`, which has no `status` field — see
[Operations Services](../services/operations.md).

### Rendering

`devlog_cli/output.py` provides three functions.

| Function | Default stream | Output |
|----------|----------------|--------|
| `render_human(result, *, verbose=False, file=None)` | `sys.stderr` | `result.summary`, prefixed with `Error: ` when `ok` is `False`. With `verbose=True` it also prints each warning as `  Warning: ...`, each remediation entry as `  Hint: ...`, and details as `  Details: {json}` |
| `render_json(result, *, file=None)` | `sys.stdout` | `result.to_json(indent=2)` |
| `render(result, *, json_mode=False, verbose=False, file=None)` | — | Dispatches to `render_json` when `json_mode` is set, otherwise to `render_human` |

Human output goes to stderr and JSON output to stdout, so the two modes are not
interchangeable in a pipeline.

## Exit Codes

`devlog_cli/exit_codes.py` defines `ExitCode`, an `IntEnum` with stable numeric values.

| Member | Value | Meaning |
|--------|-------|---------|
| `SUCCESS` | 0 | Operation completed successfully |
| `GENERAL_FAILURE` | 1 | Unclassified failure |
| `INVALID_USAGE` | 2 | Invalid arguments, or input rejected by the operator |
| `INVALID_CONFIG` | 3 | Configuration failed validation |
| `MISSING_DEPENDENCY` | 4 | An optional dependency required by the operation is unavailable |
| `DATABASE_ERROR` | 5 | Database unreachable, corrupt, or missing a required table |
| `SERVICE_ERROR` | 6 | A managed service (systemd unit, container) failed to start, stop or act |
| `BACKUP_ERROR` | 7 | Backup creation, verification or inspection failed |
| `DEGRADED` | 8 | Operation completed but with a degraded status |

### Mapping a service result onto an exit code

A command renders its `Result` and then raises `SystemExit(result.exit_code)`. The mapping is
per-command, not centralised:

| Command | Condition | Exit code |
|---------|-----------|-----------|
| `config check` | Validation produced errors | `INVALID_CONFIG` (3) |
| `config check` | Validation produced warnings or infos only | `DEGRADED` (8) |
| `backup create` | `backup.create.db_not_found` | `DATABASE_ERROR` (5) |
| `backup create` | `backup.create.encryption_unavailable` | `MISSING_DEPENDENCY` (4) |
| `backup create` | Any other failure | `BACKUP_ERROR` (7) |
| `admin create` | `ValueError` from the password policy | `INVALID_USAGE` (2) |
| `admin create` | `ConflictError` | `GENERAL_FAILURE` (1) |
| `admin promote` | `ValueError` or `ConflictError` | `GENERAL_FAILURE` (1) |
| `admin reset-password` | `ValueError` | `INVALID_USAGE` (2) |
| `data import` | Neither `--dry-run` nor `--apply` supplied | `INVALID_USAGE` (2) |
| `media scan`, `media cleanup` | Service failure | `SERVICE_ERROR` (6) |
| `doctor` | Service status `"failure"` | `GENERAL_FAILURE` (1) |
| `doctor` | Service status `"degraded"` | `DEGRADED` (8) |
| `doctor` | Any other status | `SUCCESS` (0) |

`doctor` is the one command that maps a service status directly onto an exit code without
building a `Result`.

Click's own usage errors — unknown command, unknown option, or a `click.Path(exists=True)`
argument that does not exist — exit with Click's code `2`, which coincides with
`ExitCode.INVALID_USAGE`.

## Error Model

`devlog_cli/errors.py` defines a domain exception hierarchy. Each class carries the exit code
and the stable error code it maps onto.

| Exception | Base | `exit_code` | `code` |
|-----------|------|-------------|--------|
| `DevlogError` | `Exception` | `ExitCode.GENERAL_FAILURE` (1) | `error.general` |
| `ConfigError` | `DevlogError` | `ExitCode.INVALID_CONFIG` (3) | `error.config` |
| `DatabaseError` | `DevlogError` | `ExitCode.DATABASE_ERROR` (5) | `error.database` |
| `ServiceError` | `DevlogError` | `ExitCode.SERVICE_ERROR` (6) | `error.service` |
| `BackupError` | `DevlogError` | `ExitCode.BACKUP_ERROR` (7) | `error.backup` |
| `MissingDependencyError` | `DevlogError` | `ExitCode.MISSING_DEPENDENCY` (4) | `error.missing_dependency` |

`DevlogError.__init__(message, *, remediation=None)` stores the optional remediation hint on the
exception.

The hierarchy is **not** wired into the command layer. No command module imports
`devlog_cli.errors`; commands catch raw `Exception`, `ValueError`, `ConflictError` and
`FileExistsError` and hand-build a `Result.failure(...)` with an explicit exit code. The classes
are exercised only by `tests/cli/test_result.py`.

## Command Reference

### `devlog config`

This group does not use the operations service layer — it calls `app/config/` directly.

| Command | Purpose | Calls |
|---------|---------|-------|
| `check` | Validate the effective configuration; report schema, security, filesystem, dependency and compatibility findings | `app.config.loader.load_effective_config()`, `app.config.paths.resolve_config_path()`, `app.config.validation.validate_all()` |
| `show` | Print the effective configuration, optionally with source provenance per field | `load_effective_config()`, `app.config.serialization.config_to_dict()` |
| `explain` | Explain one field: type, default, effective value, env var, secret flag, production note | `load_effective_config()`, `config_to_dict()` |
| `paths` | Show where the config file and env file are resolved from | `app.config.paths.resolve_config_path()`, `app.config.paths.resolve_env_file_path()` |
| `init` | Write a `config.toml` from a named profile (`--profile`), with `--output` and `--force` | `app.config.profiles.get_profile()` |
| `migrate` | Migrate a config file to the current version; `--dry-run` previews | `app.config.migration.needs_migration()`, `dry_run_migration()`, `apply_migration()`, `backup_config()` |

### `devlog admin`

| Command | Purpose | Calls |
|---------|---------|-------|
| `create` | Create an admin user; enforces the password complexity policy; `--password-file` reads the password from a file, `--update-existing` promotes on conflict | `app.services.operations.admin.create_admin()` |
| `promote` | Grant admin rights to an existing user | `app.services.operations.admin.promote_admin()` |
| `reset-password` | Reset an admin user's password | `app.services.operations.admin.reset_admin_password()` |
| `list` | List admin users | `app.services.operations.admin.list_admins()` |

### `devlog db`

| Command | Purpose | Calls |
|---------|---------|-------|
| `check` | Run the SQLite integrity check | `app.services.operations.database.check_database_integrity()` |
| `rebuild-search` | Rebuild the FTS5 search index | `app.services.operations.database.rebuild_search_index()` |
| `status` | Report Alembic migration status | `app.services.operations.database.get_migration_status()` |
| `migrate` | Apply pending Alembic migrations | `app.services.operations.database.run_migrations()` |

### `devlog themes`

| Command | Purpose | Calls |
|---------|---------|-------|
| `list` | List available themes; `--source` filters by `all`/`bundled`/`external`, `--warnings` includes diagnostics, `--verbose` adds absolute paths | `app.services.operations.themes.list_theme_descriptors()` |
| `validate` | Validate a Halloy TOML theme file or a registered theme name | `app.services.operations.themes.validate_theme()` |
| `inspect` | Inspect a theme's full details; `--css` emits the generated CSS variables instead of the envelope | `app.services.operations.themes.inspect_theme()` |
| `refresh` | Rebuild the theme registry | `app.services.operations.themes.refresh_theme_registry()` |
| `paths` | Show theme resource paths and configuration | `app.services.operations.themes.get_theme_paths()` |
| `accessibility` | Run WCAG contrast checks across the catalog; `--strict` rejects external themes with mandatory failures | `app.services.operations.themes.run_accessibility_check()` |

### `devlog backup`

| Command | Purpose | Calls |
|---------|---------|-------|
| `create` | Create a backup; `--compress`, `--encrypt` and `--keep` control the archive form and retention | `app.services.operations.backup.create_backup_operation()` |
| `verify` | Verify a backup archive | `app.services.operations.backup.verify_backup()` |
| `inspect` | Inspect a backup archive's contents | `app.services.operations.backup.inspect_backup()` |

### `devlog data`

| Command | Purpose | Calls |
|---------|---------|-------|
| `export` | Export site data to a JSON archive; `--force` overwrites an existing destination | `app.services.operations.transfer.export_site_data()` |
| `import` | Validate and apply an import archive; `--dry-run` validates only, `--apply` executes, `--skip-confirmed`/`--include-confirmed` controls subscriber handling | `app.services.operations.transfer.validate_import()`, `import_site_data()` |

### `devlog media`

| Command | Purpose | Calls |
|---------|---------|-------|
| `scan` | Scan for orphaned media files; read-only | `app.services.operations.media.scan_orphaned_media()` |
| `cleanup` | Delete orphaned media; destructive, requires `--apply` | `app.services.operations.media.apply_orphaned_media_cleanup()` |

### `devlog onboard`

| Command | Purpose | Calls |
|---------|---------|-------|
| `detect` | Detect an existing installation | `app.services.operations.onboard.detect_installation()` |
| `plan` | Produce a first-run plan; `--scope` selects `system` or `user`, `--mode` and `--profile` narrow the plan | `app.services.operations.onboard.generate_plan()` |
| `run` | Execute the plan; `--dry-run` previews, `--non-interactive` refuses prompts, `--accept-defaults` takes every default, `--admin-username` / `--admin-password-file` / `--site-url` supply answers | `app.services.operations.onboard.apply_onboarding()` |
| `resume` | Resume an interrupted onboarding from `--data-path` | `app.services.operations.onboard.resume_onboarding()` |

### `devlog paths`

This group calls `app/filesystem/` directly rather than the operations service layer.

| Command | Purpose | Calls |
|---------|---------|-------|
| `status` | Report all resolved paths with provenance, existence and permissions | `app.filesystem.layout.InstallMode`, `app.filesystem.layout.RuntimePaths.for_mode()` |
| `discover-legacy` | Search for a legacy layout; read-only, `--search-root` bounds the search | `app.filesystem.discovery.discover_legacy_layout()` |
| `migrate` | Plan a layout migration from `--from-mode` to `--to-mode` | `app.filesystem.migration.plan_migration()` |
| `check` | Health-check the resolved filesystem paths | `app.filesystem.verification.verify_migration()` |

### `devlog deploy`

| Command | Purpose | Calls |
|---------|---------|-------|
| `render` | Render systemd units, compose and proxy files; `--target` selects components, `--output` writes them to a directory, `--print` embeds them in the result | `app.services.operations.deploy.deploy_render()` |
| `install` | Install rendered files into the host; `--dry-run` previews, `--force` overwrites, `--base-dir` overrides the target root | `app.services.operations.deploy.deploy_install()` |
| `check` | Check the installed state for drift against the expected configuration | `app.services.operations.deploy.deploy_check()` |

### `devlog doctor`

| Command | Purpose | Calls |
|---------|---------|-------|
| `doctor` | Run the diagnostic check registry; `--production` applies production-mode checks, `--check` runs one check, `--category` filters by category, `--fix-safe` applies registered safe fixes, `--list-checks` enumerates the registry, `--deep` enables slow checks, `--no-parallel` runs serially | `app.services.operations.doctor.run_doctor()`, `get_registry()`, `get_safe_fix_plan()` |

See [Doctor Service](../services/doctor.md) for the check registry and severity model.

### Lifecycle commands

These are registered directly on the root group.

| Command | Purpose | Calls |
|---------|---------|-------|
| `devlog start` | Start the DevLog service | `app.services.operations.deploy.lifecycle_start()` |
| `devlog stop` | Stop the DevLog service | `app.services.operations.deploy.lifecycle_stop()` |
| `devlog restart` | Restart the DevLog service | `app.services.operations.deploy.lifecycle_restart()` |
| `devlog status` | Show the DevLog service status | `app.services.operations.deploy.lifecycle_status()` |
| `devlog logs` | Show service logs; `--follow` streams, `--tail` bounds the output, `--component` filters | `app.services.operations.deploy.lifecycle_logs()` |

### `devlog version`

| Command | Purpose | Calls |
|---------|---------|-------|
| `version` | Show version information | None — reads `devlog_cli.__version__` |

## Relationship to `app/cli.py`

`app/cli.py` registers Flask CLI commands that call the same operations services. It exists for
compatibility with `flask ...` invocations inside an activated application environment.

| Flask command | Equivalent `devlog` command |
|---------------|----------------------------|
| `flask rebuild-search` | `devlog db rebuild-search` |
| `flask cleanup-orphaned-images` | `devlog media cleanup --apply` |
| `flask create-admin` | `devlog admin create` |
| `flask promote-admin` | `devlog admin promote` |
| `flask check-integrity` | `devlog db check` |
| `flask export-data` | `devlog data export` |
| `flask import-data` | `devlog data import` |
| `flask themes list` | `devlog themes list` |
| `flask themes validate` | `devlog themes validate` |
| `flask themes inspect` | `devlog themes inspect` |
| `flask themes accessibility` | `devlog themes accessibility` |
| `flask seed` | No equivalent |

Which to use:

| Concern | `devlog ...` | `flask ...` |
|---------|--------------|-------------|
| Environment | Standalone; builds the app itself via `ensure_app_context()` | Requires `FLASK_APP=run:app` and an importable app environment |
| Output contract | `Result` envelope with stable operation codes | Ad-hoc `click.echo` text, no envelope |
| Exit status | Stable `ExitCode` values | `SystemExit(1)` on failure, `0` otherwise |
| JSON support | `--json` on most commands | `--json` only on the `themes` subcommands |

`flask seed` is the one command with no operations-service backing: it writes tags, users, posts,
subscribers and pages inline in `app/cli.py`, and it has no `devlog` equivalent.

## Notes and Gotchas

1. **`--quiet` and `--no-color` are inert.** Both are parsed into `CliContext`, but no command
   reads `cli_ctx.quiet` or `cli_ctx.no_color`, and `output.py` never emits ANSI colour.
   `CliContext.from_env()` — the only code that would auto-disable colour for non-TTY output — is
   never called.

2. **`devlog_cli/errors.py` is dead code.** No command raises or catches `DevlogError` or a
   subclass; commands catch raw exception types instead. Adding a new error class will not change
   any behaviour.

3. **`devlog config explain` raises `TypeError` for five fields.** The reported source is
   computed as `"env" if os.environ.get(meta["env_var"]) else "config_file"`, and `meta["env_var"]`
   is `None` for fields with no environment-variable mapping. In the CLI's own section table those
   are `admin.username`, `database.pool_size`, `database.max_overflow`, `database.pool_recycle` and
   `logging.level`. `os.environ.get(None)` raises `TypeError`, which is uncaught, so the command
   exits with a traceback instead of a `Result`.

4. **`config explain` reports a misleading source.** A field still at its default is reported as
   `config_file`; `default` and `env_file` are never reported as sources.

5. **`devlog_cli/commands/config.py` duplicates the configuration defaults.** It keeps its own
   `_SECTION_DEFAULTS` snapshot instead of reading `app/config/model.py`, which AGENTS.md names as
   the canonical source of truth. The snapshot is currently in sync with the model for the 22
   sections it covers, but it omits the model's `paths` section and the top-level scalars
   (`secret_key`, `admin_password`, `session_cookie_secure`, `proxy_count`, `flask_env`,
   `testing`) — so `devlog config explain paths.data_dir` reports "Unknown config field".

6. **`config show --effective` ignores the global `--env-file`.** Its provenance helper calls
   `resolve_env_file_path()` with no argument rather than passing the requested path.

7. **The global `--config` and `--env-file` never reach the Flask app.**
   `CliContext.ensure_app_context()` calls `create_app()`, which takes no arguments and resolves
   configuration through `load_effective_config()` on its own. Only the `config` group reads
   `cli_ctx.config_path` and `cli_ctx.env_file`.

8. **Two groups bypass the operations service layer.** `config` calls `app/config/` directly and
   `paths` calls `app/filesystem/` directly. Everything else goes through
   `app/services/operations/`.

9. **`devlog paths migrate` only plans.** It calls `plan_migration()`; `execute_migration()` in
   `app/filesystem/migration.py` is not reachable from the CLI, so the CLI never moves files.

10. **Human output goes to stderr, JSON output to stdout.** `render_human()` defaults to
    `sys.stderr` and `render_json()` to `sys.stdout`, so `devlog admin list > out.txt` captures
    nothing in human mode.

11. **Several commands bypass the `Result` envelope.**
    - `themes list` in human mode prints a table with `click.echo` and never renders a `Result`.
    - `themes inspect --css` echoes raw CSS and returns.
    - `devlog doctor --json` prints `doctor_result.to_dict()` — the **service-level**
      `OperationResult` dict — rather than the CLI envelope, so its key set differs: it has no
      `status` key and always carries `remediation`.
    - `devlog doctor --list-checks --json` prints a bare JSON array of check descriptors.
    `tests/cli/test_command_parity.py` asserts the envelope shape only for the commands that use
    it.

12. **`--json` placement is inconsistent between groups.** The global flag must precede the
    subcommand. Per-command `--json` options exist on `config check`, `config show`,
    `config paths`; all `db` commands; `themes list`, `themes validate`, `themes inspect`,
    `themes accessibility`; `backup inspect`; `media scan`, `media cleanup`; `onboard plan`,
    `onboard run`, `onboard resume`; all `paths` commands; all `deploy` commands; `doctor`;
    `status`; `logs`. The remaining commands honour only the global flag: `admin *`,
    `data export`, `data import`, `backup create`, `backup verify`, `onboard detect`,
    `config explain`, `config init`, `config migrate`, `themes refresh`, `themes paths`, `start`,
    `stop`, `restart`.

13. **`devlog data import` resolves `--dry-run` and `--apply` by precedence, not validation.**
    Passing both runs the dry run, because the dry-run branch is tested first. Passing neither
    fails with exit code 2.

14. **`devlog media cleanup` without `--apply` is a dry run** that still exits 0 and prefixes its
    summary with `"Dry run: "`.

15. **`deploy render --print` and `--output` are mutually exclusive in effect.** `--output`
    writes files named `{target}-{basename}` into the directory only when `--print` is absent;
    `--print` embeds the file contents in the result's `details` instead of writing to stdout.
    `deploy install` with no `--target` installs all components.

16. **`--user` overrides `--mode` on the deploy and lifecycle commands.** Supplying `--user`
    forces the effective mode to `user` regardless of the `--mode` value.

17. **Five groups are defined twice.** `devlog_cli/commands/config.py`, `db.py`, `backup.py`,
    `data.py` and `media.py` each declare a module-level `click.group()` with the same name as the
    group in `devlog_cli/main.py`. The commands are attached to the `main.py` group by
    `register_*_commands(group)`; the module-level group objects are unreachable but retain the
    same `Command` instances.

18. **`--config` path validation is inconsistent.** The root group's `--config` and
    `config migrate --config` use `click.Path(exists=True)` and fail with a Click usage error on
    a missing file, while `config check --config` uses a plain `click.Path` and passes the
    nonexistent path on to `load_effective_config()` and `resolve_config_path()` instead of
    rejecting it.

19. **The version falls back to `0.0.0-dev`.** `devlog_cli/__init__.py` reads the version from
    installed distribution metadata, so running from a source checkout that was never installed
    reports `0.0.0-dev`.

## See Also

- [Managed Deployment](managed-deployment.md) — systemd units, compose and proxy rendering, drift and lifecycle
- [Installation](installation.md) — installation modes, responsibility boundaries and path resolution
- [Deployment & Operations](deployment.md) — deployment context, renderers and drift detection
- [Docker](docker.md) — container orchestration
- [Security](security.md) — authentication, CSRF and security headers
- [Operations Services](../services/operations.md) — the service layer the CLI calls into
- [Doctor Service](../services/doctor.md) — diagnostic check registry and severity model
- [Filesystem Layout](../core/filesystem.md) — `RuntimePaths`, install modes and legacy migration
- [Configuration](../core/configuration.md) — the typed configuration system and its precedence chain
- [Onboarding](../core/onboarding.md) — the onboarding package behind `devlog onboard`
- [Themes](../core/themes.md) — the theme system behind `devlog themes`
