# Filesystem Layout (`app/filesystem/`)

The filesystem layout subsystem is the centralized path-resolution authority for the
application: it decides where the database, uploads, themes, backups, exports, config,
logs and runtime files live, in four install modes (`system`, `user`, `docker`,
`development`). Every resolved path carries a provenance record so an operator can see
whether a value came from an explicit override, an environment variable or a mode
default. The package also owns directory preparation with permissions and ownership,
read-only discovery of pre-existing ("legacy") layouts, a migration planner/executor for
moving state between layouts, and post-migration verification.

The package is an operations authority, not a request-handling authority: it is consumed
by onboarding (`app/onboarding/`), deployment rendering (`app/deployment/`), doctor
diagnostics (`app/services/operations/doctor.py`) and the standalone `devlog` CLI. The
Flask app factory does not read `RuntimePaths` — see
[Notes and Gotchas](#notes-and-gotchas).

## Module Map

| File | Owns |
|------|------|
| `app/filesystem/__init__.py` | Public re-export surface for the package |
| `app/filesystem/layout.py` | `InstallMode`, `PathProvenance`, `ResolvedPath`, `RuntimePaths`, `InstallationMetadata`, mode detection and per-mode path resolution |
| `app/filesystem/prepare.py` | `DirectorySpec`, `get_directory_specs()`, `prepare_directories()` — creation with modes, ownership and safety checks |
| `app/filesystem/discovery.py` | `LegacyDiscovery`, `discover_legacy_layout()`, `classify_discovery()` — read-only scan of existing state |
| `app/filesystem/migration.py` | `MigrationAction`, `MigrationStep`, `MigrationPlan`, `MigrationExecutionResult`, `plan_migration()`, `execute_migration()` |
| `app/filesystem/verification.py` | `PathCheckResult`, `VerificationResult`, `check_path()`, `verify_migration()`, `verify_production_ready()` |
| `app/filesystem/lifecycle.py` | `PathCategory`, `LifecyclePolicy`, `CATEGORY_POLICIES`, `RUNTIME_PATH_CATEGORIES` — backup/uninstall/purge contract |

## Install Modes

`InstallMode` (an `Enum` in `app/filesystem/layout.py`) has four members:

| Mode | Value | Layout |
|------|-------|--------|
| `SYSTEM` | `system` | FHS-aligned: `/etc/devlog`, `/var/lib/devlog`, `/var/log/devlog`, `/run/devlog` |
| `USER` | `user` | XDG base directories under `~/.config`, `~/.local/share`, `~/.local/state` |
| `DOCKER` | `docker` | Container paths: `/data`, `/etc/devlog`, `/var/log/devlog`, `/run/devlog` |
| `DEVELOPMENT` | `development` | Repository-local: `./data`, `./config.toml`, `./logs`, `./instance` |

### Mode Detection

`detect_mode(search_root=None)` returns a `ModeDetectionResult` (`detected_mode`,
`source`, `ambiguous`, `candidates`). Candidates are collected in this order, and the
first candidate wins:

1. `detect_mode_from_metadata()` — a `.devlog-installation.json` at `<root>/`,
   `<root>/data/`, or `<root>/../`
2. `DEVLOG_DOCKER` environment variable, or the existence of `/.dockerenv`
3. `DEVLOG_MODE` environment variable
4. Existence of `/etc/devlog/config.toml` or `/var/lib/devlog`

If no candidate matches, the mode is `DEVELOPMENT` with the source string
`"no metadata or system paths found, defaulting to development"`. When more than one
candidate names a *different* mode, the result is flagged `ambiguous=True` and the full
candidate list is returned, but `detected_mode` is still the first candidate.

`InstallationMetadata.load(path)` reads the JSON metadata file and returns `None` when
the file is absent or malformed (`json.JSONDecodeError`, `KeyError`, `ValueError`). The
recognised keys are `mode` (required), `version`, `data_dir`, `config_file`, `env_file`
and `install_root`.

### Resolved Paths by Mode

| Path | system | user | docker | development |
|------|--------|------|--------|-------------|
| `config_file` | `/etc/devlog/config.toml` | `$XDG_CONFIG_HOME/devlog/config.toml` | `/etc/devlog/config.toml` | `./config.toml` |
| `env_file` | `/etc/devlog/.env` | `$XDG_CONFIG_HOME/devlog/.env` | `/etc/devlog/.env` | `./.env` |
| `data_dir` | `/var/lib/devlog` | `$XDG_DATA_HOME/devlog` | `/data` | `./data` |
| `database` | `<data_dir>/devlog.sqlite3` | `<data_dir>/devlog.sqlite3` | `/data/devlog.sqlite3` | `./data/devlog.sqlite3` |
| `uploads_dir` | `<data_dir>/uploads` | `<data_dir>/uploads` | `/data/uploads` | `./data/uploads` |
| `themes_dir` | `<data_dir>/themes` | `<data_dir>/themes` | `/data/themes` | `./data/themes` |
| `backups_dir` | `<data_dir>/backups` | `<data_dir>/backups` | `/data/backups` | `./data/backups` |
| `exports_dir` | `<data_dir>/exports` | `<data_dir>/exports` | `/data/exports` | `./data/exports` |
| `log_dir` | `/var/log/devlog` | `$XDG_STATE_HOME/devlog/logs` | `/var/log/devlog` | `./logs` |
| `runtime_dir` | `/run/devlog` | `$XDG_RUNTIME_DIR/devlog`, else `$XDG_STATE_HOME/devlog` | `/run/devlog` | `./instance` |
| `installation_metadata` | `<data_dir>/.devlog-installation.json` | `<data_dir>/.devlog-installation.json` | `/data/.devlog-installation.json` | `./data/.devlog-installation.json` |
| `release_dir` | `/opt/devlog/current` | `None` | `None` | `None` |

XDG base directories fall back to `~/.config`, `~/.local/share` and `~/.local/state` when
the corresponding environment variable is unset. In `system` mode the config/env root is
`install_root or /etc/devlog`; `release_dir` is *not* derived from that root — it is a
fixed `/opt/devlog/current`, matching the prefix `scripts/install.sh` uses for a
`--system` install, and it can be overridden with the `DEVLOG_RELEASE_DIR` environment
variable. The `data_dir`, `log_dir` and `runtime_dir` defaults in `system` mode are fixed
regardless of `install_root`.

## Provenance

`PathProvenance` is an `Enum` whose members record where a resolved value came from:

| Member | Meaning |
|--------|---------|
| `EXPLICIT` | An override passed to `RuntimePaths.resolve()` by the caller |
| `ENV_VAR` | An environment variable supplied the value |
| `SYSTEM_DEFAULT` | The `system` mode default |
| `XDG_DEFAULT` | The `user` mode XDG default |
| `DOCKER_DEFAULT` | The `docker` mode default |
| `DEVELOPMENT_FALLBACK` | The `development` mode repository-local default |
| `METADATA` | Reserved for installation-metadata values — see [Notes and Gotchas](#notes-and-gotchas) |

Resolution happens in `_resolve_path()`, which applies a three-tier precedence:

1. **Explicit override** — the keyword argument wins over everything.
2. **Environment variable** — read at resolve time via `os.environ.get(env_var, "")`;
   an empty string is treated as unset.
3. **Mode default** — the built-in path for the mode.

Every path is passed through `Path.resolve()`, so all resolved paths are absolute.

### Environment Variables Consulted by `layout.py`

| Variable | Path | Modes |
|----------|------|-------|
| `DEVLOG_DATA_DIR` | `data_dir` | all |
| `DEVLOG_CONFIG_FILE` | `config_file` | all |
| `DEVLOG_ENV_FILE` | `env_file` | all |
| `DEVLOG_LOG_DIR` | `log_dir` | all |
| `DEVLOG_RUNTIME_DIR` | `runtime_dir` | all |

The derived paths (`database`, `uploads_dir`, `themes_dir`, `backups_dir`,
`exports_dir`) have no environment-variable tier inside `app/filesystem/layout.py`; they
are derived from `data_dir` by `_resolve_database_path()`, `_resolve_uploads_dir()`,
`_resolve_themes_dir()`, `_resolve_backups_dir()` and `_resolve_exports_dir()` unless an
explicit override is passed. The typed configuration system does read
`DEVLOG_DATABASE_PATH`, `DEVLOG_UPLOADS_DIR`, `DEVLOG_THEMES_DIR`, `DEVLOG_BACKUPS_DIR`
and `DEVLOG_EXPORTS_DIR` — see [Configuration](configuration.md) — but no code path feeds
those values into `RuntimePaths`.

### `PathsConfig`

`PathsConfig` in `app/config/model.py` is the typed configuration section for the same
family of values, with eight string fields, all defaulting to `""`:

`data_dir`, `log_dir`, `runtime_dir`, `database_path`, `uploads_dir`, `themes_dir`,
`backups_dir`, `exports_dir`.

`app/config/loader.py` populates it from the `[paths]` section of `config.toml` and from
the `DEVLOG_*` environment variables listed in `_ENV_OVERRIDE_MAP`. `app/config_legacy.py`
re-exports the values as the `DEVLOG_*` module globals for backward compatibility. The
`app/config/paths.py` module is a separate concern: it resolves the *config file* and
*env file* candidates (`resolve_config_path()`, `resolve_env_file_path()`) from CLI
argument, `DEVLOG_CONFIG`/`DEVLOG_ENV_FILE`, system path, XDG path, home path and
working directory, selecting the first candidate that exists, is a file and is readable.

## `RuntimePaths`

`RuntimePaths` is a frozen dataclass. Every field except `release_dir` is a
`ResolvedPath`, itself a frozen dataclass of `path: Path`, `provenance: PathProvenance`
and `source: str` (a human-readable description of the origin).

| Field | Kind | Notes |
|-------|------|-------|
| `config_file` | `ResolvedPath` | TOML configuration |
| `env_file` | `ResolvedPath` | Environment/secrets file |
| `data_dir` | `ResolvedPath` | Root of persistent state |
| `database` | `ResolvedPath` | SQLite file; derived from `data_dir` unless overridden |
| `uploads_dir` | `ResolvedPath` | User media |
| `themes_dir` | `ResolvedPath` | Runtime themes |
| `backups_dir` | `ResolvedPath` | Backup artefacts |
| `exports_dir` | `ResolvedPath` | Data exports |
| `log_dir` | `ResolvedPath` | Application logs |
| `runtime_dir` | `ResolvedPath` | Sockets, PID files, locks |
| `installation_metadata` | `ResolvedPath` | `<data_dir>/.devlog-installation.json` |
| `release_dir` | `ResolvedPath \| None` | `None` outside `system` mode |

### Constructors

| Constructor | Behaviour |
|-------------|-----------|
| `RuntimePaths.resolve(mode, **overrides)` | Full resolution. Accepts overrides for every field, plus `xdg_config_home`, `xdg_data_home`, `xdg_state_home`, `xdg_runtime_dir` and `install_root`. |
| `RuntimePaths.for_mode(mode)` | `resolve(mode)` with no overrides. The constructor used by production code. |
| `RuntimePaths.from_metadata(metadata_path, **overrides)` | Loads `InstallationMetadata` and resolves using the recorded mode. Returns `None` if the metadata file is missing or invalid. Metadata values for `config_file`, `env_file` and `data_dir` are used only when the caller did not supply an override. |

### Helpers

| Method | Returns |
|--------|---------|
| `as_dict()` | Mapping of field name to absolute path string; `release_dir` included only when set |
| `all_paths()` | List of `(name, Path)` pairs, same inclusion rule |
| `provenance_for(name)` | `"<provenance>: <source>"` string, or `"unknown"` for a name that is not a `ResolvedPath` field |

## Directory Preparation

`prepare.py` owns the permission and ownership contract for the managed directories.

`DirectorySpec` is a frozen dataclass with `path`, `owner`, `group`, `mode`,
`created_during` (`"onboarding"` or `"runtime"`), `contains_secrets` and
`symlinks_allowed`.

`get_directory_specs(mode)` returns a mapping of seven directory names to
`DirectorySpec`: `data_dir`, `uploads_dir`, `themes_dir`, `backups_dir`, `exports_dir`,
`log_dir` and `runtime_dir`.

| Mode | `data_dir` / `uploads` / `themes` / `backups` / `exports` | `log_dir` | `runtime_dir` |
|------|----------------------------------------------------------|-----------|---------------|
| `system` | `/var/lib/devlog/…`, owner `devlog:devlog`, mode `0o750` | `/var/log/devlog`, `devlog:devlog`, `0o750` | `/run/devlog`, `devlog:devlog`, `0o755` |
| `docker` | `/data/…`, no owner, mode `0o755` | `/var/log/devlog`, `0o755` | `/run/devlog`, `0o755` |
| `user` | `~/.local/share/devlog/…`, mode `0o700` | `~/.local/state/devlog/logs`, `0o700` | `~/.local/state/devlog`, `0o700` |
| `development` | `<cwd>/data/…`, mode `0o755` | `<cwd>/logs`, `0o755` | `<cwd>/instance`, `0o755` |

`prepare_directories(paths, *, mode, dry_run=False)` returns the list of directories it
created (or, in dry-run mode, would create). For each managed path that does not yet
exist it:

1. runs `_validate_path_safety(p.parent, p)` — resolves both paths and raises
   `ValueError` if the target escapes its parent;
2. runs `_check_parent_ownership(p)`;
3. creates the directory with `mkdir(parents=True, exist_ok=True)`;
4. applies the spec's mode with `os.chmod()`, and, when running as uid 0 and the spec
   names an owner, applies `os.chown()` with the uid/gid resolved through `pwd`/`grp`
   (a `KeyError` or `OSError` there is swallowed and the directory keeps its owner);
5. falls back to mode `0o755` when no spec matches the path name.

Directories that already exist are left untouched — no mode or ownership is corrected.
The config and env file parents are not managed here; onboarding creates the config
directory separately (`app/onboarding/steps.py`, `step_resolve_paths()`).

## Legacy Discovery

`discovery.py` is read-only. `discover_legacy_layout(search_root=None)` scans the root
directory (default `Path.cwd()`) and returns a `LegacyDiscovery` with eight lists:
`database_files`, `upload_dirs`, `backup_dirs`, `theme_dirs`, `log_dirs`,
`config_files`, `env_files`, `metadata_files`.

| Category | Match rule |
|----------|------------|
| Databases | `*.sqlite3`, `*.db`, `*.sqlite` in the root and one level into each non-dot subdirectory |
| Upload dirs | Directories named `uploads`, `media`, `files` or `images` |
| Backup dirs | Directories named `backups` or `backup` |
| Theme dirs | Directories named `themes` or `theme` |
| Log dirs | Directories named `logs` or `log` |
| Config files | `config.toml`, `config.yaml`, `config.json` or `config.ini` in the root |
| Env files | `.env`, `.env.local` or `.env.production` in the root |
| Metadata files | `.devlog-installation.json` or `devlog-installation.json` in the root and one level into each non-dot subdirectory |

`classify_discovery(discovery, target)` maps each discovered path to a label relative to
the target `RuntimePaths`:

| Label | Meaning |
|-------|---------|
| `managed` | The path is the target layout's own path for that category |
| `likely_devlog` | Not the managed path, but the name or extension suggests DevLog state (database extensions, `devlog` in a directory name) |
| `unknown` | No signal either way |

Config and env files that are not the managed path are always labelled `likely_devlog`,
and every metadata file is labelled `managed`.

## Migration Planning and Execution

`migration.py` moves state from one layout to another.

`MigrationAction` has five members: `COPY`, `MOVE`, `SKIP`, `CONFLICT`, `CREATE_DIR`.
`MigrationStep` is a frozen dataclass of `action`, `source: Path | None`, `target: Path`
and `description`. `MigrationPlan` holds `steps`, `source_mode`, `target_mode`,
`warnings` and `requires_downtime`. `MigrationExecutionResult` holds `ok`,
`completed_steps`, `total_steps`, `errors` and `completed_paths`.

### `plan_migration()`

```python
def plan_migration(
    source: RuntimePaths,
    target: RuntimePaths,
    *,
    source_mode: InstallMode | None = None,
    target_mode: InstallMode | None = None,
    include_logs: bool = False,
) -> MigrationPlan
```

The plan is built in a fixed order: config file, env file, database, uploads, themes,
backups, exports, optionally logs, then installation metadata. Directory transfers are
expanded recursively; a missing source yields `SKIP`, an existing target yields
`CONFLICT`, and everything else yields `MOVE` (or `CREATE_DIR` for a missing target
directory).

`requires_downtime` is `True` when any step is `MOVE` or `COPY`. Two warnings are
raised: `"Source and target data directories are identical"` when the two `data_dir`
values match, and `"One or more target paths already exist; manual resolution required"`
when any step is a `CONFLICT`.

### `execute_migration()`

```python
def execute_migration(
    plan: MigrationPlan,
    *,
    dry_run: bool = False,
    stop_on_conflict: bool = True,
) -> MigrationExecutionResult
```

Before any transfer, the executor locates the source database by looking for the first
step whose source is named `blog.db` or `devlog.sqlite3`, and — when not a dry run —
runs `PRAGMA wal_checkpoint(TRUNCATE)` on it through `_checkpoint_sqlite()`. This
truncates the source WAL so the moved database file is self-contained.

Steps then run in order. `SKIP` counts as completed. `CONFLICT` aborts the run and
records the step description in `errors` when `stop_on_conflict` is set, otherwise it is
counted as completed. `CREATE_DIR` creates the target directory. `MOVE`/`COPY` create the
target's parent and then `shutil.move()` or `shutil.copytree()`/`shutil.copy2()`. The
first `OSError` aborts the run and is recorded in `errors`.

In dry-run mode no filesystem write happens and the checkpoint is skipped; every step is
counted as completed and the result is `ok=True`.

## Verification

`verification.py` checks a resolved layout.

`check_path(path)` returns a `PathCheckResult` with `exists`, `is_symlink`,
`symlink_target`, `writable`, `permissions` (octal `stat.S_IMODE`), `free_space_bytes`
and `is_release_dir`. A path is treated as a release directory when it is named `current`
inside a `releases` parent, or when it contains a `current` symlink.

`verify_migration(target)` returns a `VerificationResult` (`success`, `errors`,
`warnings`, `path_checks`, `path_details`) after checking every managed path. Its rules:

| Condition | Severity |
|-----------|----------|
| `data_dir` does not exist | error |
| `database` exists but is not accessible | error |
| `uploads_dir`, `themes_dir`, `backups_dir`, `exports_dir` or `log_dir` not writable | error |
| `log_dir` or `runtime_dir` do not exist | warning |
| `database` does not exist | warning |
| `runtime_dir` not writable | warning |
| Any checked path is a symlink | warning |

`verify_production_ready(target)` runs `verify_migration()` and then applies the
production-specific rules: a missing database is promoted to an error
("Production mode requires an existing database."), the target database is
WAL-checkpointed through `checkpoint_database()`, and any of `data_dir`,
`uploads_dir`, `themes_dir`, `backups_dir` or `exports_dir` with less than 100 MB free
raises a low-disk-space warning.

`verify_database_accessible(db_path)` opens the database and runs `SELECT 1`;
`checkpoint_database(db_path)` runs `PRAGMA wal_checkpoint(TRUNCATE)`;
`verify_directory_writable(path)` creates the directory if needed and writes then removes
a `.devlog-write-test` file.

## Lifecycle Policy

`lifecycle.py` is a declarative contract for how each class of path is treated during
backup, uninstall and purge. The module documents itself as a contract for later
lifecycle phases — it implements neither backup nor uninstall.

`PathCategory` has nine members: `CODE`, `CONFIGURATION`, `SECRETS`, `PERSISTENT_DATA`,
`USER_CONTENT`, `BACKUPS`, `LOGS`, `RUNTIME`, `INSTALLATION_METADATA`.
`LifecyclePolicy` is a frozen dataclass of `included_in_backup`, `preserved_on_uninstall`,
`removed_on_purge`, `safe_to_regenerate` and `ownership_note`. `CATEGORY_POLICIES` maps
each category to its policy:

| Category | Backup | Preserved on uninstall | Removed on purge | Safe to regenerate | Ownership note |
|----------|--------|-------------------------|------------------|--------------------|----------------|
| `CODE` | No | No | Yes | Yes | owned by package manager or deployment tool |
| `CONFIGURATION` | Yes | Yes | Yes | No | root:devlog 0640 (system), user-owned (user) |
| `SECRETS` | Yes | Yes | Yes | No | root:devlog 0600 (system), user-owned (user) |
| `PERSISTENT_DATA` | Yes | Yes | Yes | No | devlog:devlog 0750 (system), user-owned (user) |
| `USER_CONTENT` | Yes | Yes | Yes | No | devlog:devlog 0750 (system), user-owned (user) |
| `BACKUPS` | No | Yes | Yes | No | devlog:devlog 0750 (system), user-owned (user) |
| `LOGS` | No | No | Yes | Yes | devlog:devlog 0750 (system), user-owned (user) |
| `RUNTIME` | No | No | Yes | Yes | devlog:devlog 0700 (system), user-owned (user) |
| `INSTALLATION_METADATA` | Yes | Yes | Yes | No | devlog:devlog 0640 (system), user-owned (user) |

`RUNTIME_PATH_CATEGORIES` maps `RuntimePaths` field names onto those categories:
`config_file` → `CONFIGURATION`, `env_file` → `SECRETS`, `data_dir` and `database` →
`PERSISTENT_DATA`, `uploads_dir`, `themes_dir` and `exports_dir` → `USER_CONTENT`,
`backups_dir` → `BACKUPS`, `log_dir` → `LOGS`, `runtime_dir` → `RUNTIME`,
`installation_metadata` → `INSTALLATION_METADATA`. `release_dir` has no category.

## Operator CLI Surface

The `devlog paths` group is registered in `devlog_cli/main.py` by
`register_paths_commands()` from `devlog_cli/commands/paths.py`. All four subcommands
render through the shared `Result`/`render()` helpers and accept `--json`.

| Command | Options | Maps to |
|---------|---------|---------|
| `devlog paths status` | `--mode {system,user,docker,development}` (default `development`), `--json` | `RuntimePaths.for_mode(mode)`; reports each path with its provenance, existence, type, permissions and writability |
| `devlog paths discover-legacy` | `--search-root PATH` (default `cwd`), `--json` | `discover_legacy_layout()`; read-only, buckets results into `confirmed` / `likely` / `unknown` |
| `devlog paths migrate` | `--from-mode MODE`, `--to-mode MODE` (both required), `--json` | `plan_migration()`; always a plan, never applies |
| `devlog paths check` | `--mode MODE` (default `development`), `--json` | `verify_migration()`; reports errors, warnings and per-path existence |

Exit behaviour follows the shared `Result` conventions: `paths check` fails with
`ExitCode.GENERAL_FAILURE` when verification fails and returns a degraded result when
only warnings are present; `paths migrate` returns a degraded result when the plan
carries warnings.

`paths status` and `paths check` resolve paths through `RuntimePaths.for_mode()`, so
they honour the `DEVLOG_DATA_DIR`, `DEVLOG_CONFIG_FILE`, `DEVLOG_ENV_FILE`,
`DEVLOG_LOG_DIR` and `DEVLOG_RUNTIME_DIR` environment variables.

## Integration Points

| Consumer | Use |
|----------|-----|
| `app/onboarding/steps.py` (`step_resolve_paths()`) | Chooses an `InstallMode` from the onboarding scope and resolves `RuntimePaths` to place the config directory, data directory and env file |
| `app/onboarding/state.py` | `detect_mode()` to decide where onboarding state lives |
| `app/deployment/model.py` (`DeploymentContext.from_config()`) | Builds the `RuntimePaths` that the systemd, compose, proxy and logrotate renderers consume |
| `app/deployment/lifecycle.py` | `InstallationMetadata` and `InstallMode` to select the service backend |
| `app/services/operations/doctor.py` | Path and metadata diagnostics, including the legacy-remnants check that uses `discover_legacy_layout()` with `classify_discovery()` |
| `devlog_cli/commands/paths.py` | The operator-facing `devlog paths …` commands |

## Notes and Gotchas

### Doc and Code Mismatches

| Finding | Detail |
|---------|--------|
| `docs/filesystem-layout.md` lists five derived-path environment variables that `layout.py` never reads | `DEVLOG_DATABASE_PATH`, `DEVLOG_UPLOADS_DIR`, `DEVLOG_THEMES_DIR`, `DEVLOG_BACKUPS_DIR` and `DEVLOG_EXPORTS_DIR` are consumed by the typed config loader, not by `app/filesystem/layout.py`, so they do not change `RuntimePaths` |
| `docs/filesystem-layout.md` presents `metadata` as a live provenance | `PathProvenance.METADATA` is defined but never assigned; `RuntimePaths.from_metadata()` passes metadata values as *explicit* overrides, so they resolve with provenance `explicit` |

### Behavioural Surprises

| Finding | Detail |
|---------|--------|
| The Flask runtime does not use `RuntimePaths` | `create_app()` resolves the writable directories from the typed configuration rather than from `RuntimePaths`: the instance path follows `paths.runtime_dir`, the upload folder follows `paths.uploads_dir` (or `paths.data_dir/uploads`), and the log directory follows `paths.log_dir`. The `app.instance_path/blog.db` fallback in `create_app()` is only reached when the config carries no URI at all |
| `execute_migration()` and `MigrationExecutionResult` are not exported from the package | `app/filesystem/__init__.py` re-exports `plan_migration` but not the executor, so callers must import from `app.filesystem.migration` |
| `_check_parent_ownership()` never rejects | Every branch returns without raising, so a directory under a parent owned by another user is still created |
| `_validate_path_safety()` is called with the target's own parent as the base | It therefore only rejects a target that resolves outside its parent (an escaping symlink); it is not a containment check against the data root |
| Existing directories are never corrected | `prepare_directories()` applies the `DirectorySpec` mode and owner only to directories it creates |
| User-mode specs ignore the XDG environment variables | `get_directory_specs()` hardcodes `~/.local/share` and `~/.local/state`, while `_resolve_user()` honours `XDG_DATA_HOME` and `XDG_STATE_HOME` — a user-mode install with `XDG_DATA_HOME` set prepares directories the runtime does not use |
| The Alembic migrations directory is resolved from the package, not the working directory | Flask-Migrate resolves its `directory` against the current working directory, so a pip-installed DevLog never finds the migrations it ships and `devlog db status` fails outside a source checkout. `resolve_migrations_directory()` in `app/filesystem/layout.py` returns the directory next to the `app` package — the repository root in a source checkout, `site-packages/migrations` in a wheel install — and `create_app()` passes it to `migrate.init_app()`. The function falls back to the cwd-relative default when no `env.py` is found beside the package |
| The system runtime directory mode disagrees with the lifecycle contract | `get_directory_specs()` uses `0o755` for `/run/devlog`, while the `RUNTIME` ownership note says `devlog:devlog 0700 (system)` |
| `MigrationAction.COPY` is never planned | `plan_migration()` only emits `SKIP`, `CONFLICT`, `MOVE` and `CREATE_DIR`, although `execute_migration()` handles `COPY` |
| `verify_production_ready()` writes to the database it verifies | It calls `checkpoint_database()`, which runs `PRAGMA wal_checkpoint(TRUNCATE)` on the target database |
| `detect_mode()` raises on an invalid `DEVLOG_MODE` | `InstallMode(os.environ["DEVLOG_MODE"])` is unguarded, unlike the `ValueError` fallback in `app/services/operations/deploy.py` |
| `devlog paths discover-legacy` does not use `classify_discovery()` | The CLI applies its own type heuristics (databases, upload, backup, theme and log directories are "likely"; config, env and metadata files are "confirmed"); `classify_discovery()` is used only by the doctor's legacy-remnants check |
| `_find_spec()` is dead code | Defined in `prepare.py` and never called |
| `DirectorySpec.contains_secrets`, `.symlinks_allowed` and `.created_during` are declarative only | `prepare_directories()` reads only `mode`, `owner` and `group` |

## See Also

- [Configuration](configuration.md) - The typed config system and `PathsConfig`
- [App Factory](app-factory.md) - How the Flask app resolves its own paths
- [Models](models.md) - The SQLAlchemy models stored in the resolved database path
- [Overview](../overview.md) - High-level architecture overview
- [Services Overview](../services/overview.md) - The service layer
- [Backup Service](../services/backup.md) - Writes into the resolved `backups_dir`
- [Doctor Service](../services/doctor.md) - Diagnostics that consume the layout
- [Installation](../deployment/installation.md) - Native and Docker installation
- [Deployment Overview](../deployment/overview.md) - Renderers that consume `RuntimePaths`
- [Storage](../infrastructure/storage.md) - Media storage backends
- [Test Suite](../testing/test-suite.md) - Test layout, including `tests/filesystem/`
- [Filesystem Layout (operator guide)](../../docs/filesystem-layout.md) - The prose counterpart of this document
