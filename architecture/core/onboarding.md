# Onboarding (`app/onboarding/`)

Onboarding is the first-run configuration flow for DevLog. It detects an existing installation, resolves the install mode and the paths that belong to that mode, collects the operator's answers, generates the secrets the application needs, builds a typed `DevLogConfig`, writes `config.toml` and an env file, creates the runtime directories, applies database migrations, creates the administrator account, and verifies the result. The work is organised as one fixed, ordered pipeline of steps in `app/onboarding/steps.py` that can be inspected before it runs (`plan`), executed for real (`run`), or resumed after a failure (`resume`). Secrets never leave the pipeline in plaintext: they are written to the env file and are never echoed into step results, plan output, completion output or logs.

## Module Files

| File | Owns |
|---|---|
| `app/onboarding/__init__.py` | Public surface: re-exports the dataclasses, step helpers and renderers used outside the package |
| `app/onboarding/model.py` | `OnboardingInput` (the operator answers) and `build_config_from_input()` (answers → `DevLogConfig`) |
| `app/onboarding/state.py` | `InstallState`, `InstallationInfo`, `detect_installation()` — what already exists on disk |
| `app/onboarding/metadata.py` | `OnboardingMetadata`, `load_metadata()`, `save_metadata()`, `is_complete()` — the resume record |
| `app/onboarding/steps.py` | The step pipeline, `StepContext`, `StepResult`, `run_steps()`, atomic write, backup and compensation |
| `app/onboarding/planner.py` | `PlannedAction`, `generate_plan()`, `format_plan_text()`, `format_plan_json()` |
| `app/onboarding/secrets.py` | Secret generation, `resolve_secrets()`, `write_env_file()`, `read_env_file()` |
| `app/onboarding/rendering.py` | `CompletionInfo`, `render_completion_human()`, `render_completion_json()` |
| `app/services/operations/onboard.py` | Service layer the CLI calls: `detect_installation()`, `generate_plan()`, `apply_onboarding()`, `resume_onboarding()` |
| `devlog_cli/commands/onboard.py` | The `devlog onboard` command group and its four subcommands |

The package is imported by the service layer, never by the routes. `app/onboarding/` depends on `app/config/` (for the typed model, serialisation and validation) and on `app/filesystem/layout.py` (for `RuntimePaths`), but not the other way round.

## The Installer / Onboarding Boundary

The split is deliberate and enforced by the installation contract: **the installer delivers code, onboarding creates state.**

| Concern | Owner | Detail |
|---|---|---|
| Download release artifacts | `scripts/install.sh` | Wheel or Docker bundle fetched from GitHub Releases |
| Verify checksums | `scripts/install.sh` | SHA-256 against `checksums.txt` |
| Versioned release directory and `current` symlink | `scripts/install.sh` | e.g. `/opt/devlog/releases/X.Y.Z/` |
| `devlog` launcher | `scripts/install.sh` | `/usr/local/bin/devlog` |
| Configuration file | Onboarding | `config.toml`, written atomically by `step_write_config` |
| Secrets | Onboarding | Env file, written atomically by `step_write_env` with mode `0600` |
| Runtime directories | Onboarding | `step_resolve_paths` and `step_create_directories` |
| Database schema | Onboarding | `step_run_migrations` → `run_migrations()` (`flask db upgrade`) |
| Administrator account | Onboarding | `step_create_administrator` → `create_admin()` |
| Installation metadata | Onboarding | `<data_dir>/onboarding-metadata.json` |

The installer creates no configuration, no database, no admin user and no secrets. It only calls onboarding at the end, and only when a TTY is available:

```bash
devlog onboard run --mode native --scope "${INSTALL_SCOPE}" </dev/tty
```

Without a TTY the installer prints `devlog onboard --mode <native|docker>` and leaves configuration to the operator. `scripts/install.sh` also accepts `--onboard` and `--no-onboard` to force or suppress that step.

## The Step Pipeline

`run_steps()` walks the `_ALL_STEPS` list in `app/onboarding/steps.py`. Each step receives a shared `StepContext` and returns a `StepResult(ok, message, details)`. The first step that returns `ok=False` stops the run: the pipeline records the stop point in the metadata file, calls `_compensate()` to remove the files and empty directories it created, and returns.

| # | Step | What it does | Writes | Skipped in dry run |
|---|---|---|---|---|
| 0 | `step_detect_installation` | Calls `detect_installation()` for the resolved paths and stores the result in `ctx.state` | — | no |
| 1 | `step_resolve_mode` | Validates `mode` (`native`, `docker`) and `profile` (`development`, `native-production`, `docker-production`, `minimal`, `full`); warns on `docker` + `native-production` | — | no |
| 2 | `step_resolve_paths` | Maps mode and scope to an `InstallMode`, calls `RuntimePaths.for_mode()`, then sets `ctx.config_dir`, `ctx.data_dir`, `ctx.env_file` | config dir, data dir | no |
| 3 | `step_collect_inputs` | Prompts for site title, description, base URL, admin username and password, newsletter/SMTP, scheduler and Redis; fails if no admin password | — (mutates `ctx.input`) | no |
| 4 | `step_build_config` | `build_config_from_input(ctx.input, data_dir=ctx.data_dir)` → `ctx.config` | — | no |
| 5 | `step_resolve_secrets` | Reads the existing env file, merges with the input, resolves or generates the secrets into `ctx.secrets` | — | no |
| 6 | `step_plan_changes` | `generate_plan(ctx.input, ctx.state)` — reports the intended actions | — | no |
| 7 | `step_validate_proposal` | `validate_all(ctx.config, config_path=...)` from `app/config/validation.py`; errors fail the run, warnings are collected into `ctx.warnings` | — | no |
| 8 | `step_write_config` | Backs up any existing file, then serialises the config with `config_to_toml()` and writes it atomically | `<config_dir>/config.toml` (+ `config.toml.backup.<UTC timestamp>`) | yes |
| 9 | `step_write_env` | Backs up any existing file, then writes the secret map with `write_env_file()` (temp file, `chmod 0600`, rename) | `<env_file>` (+ `.env.backup.<UTC timestamp>`) | yes |
| 10 | `step_create_directories` | Creates the data directory, `logs/` under it, and the backup directory | directories | yes |
| 11 | `step_run_migrations` | `create_app()` then `run_migrations()` (`flask db upgrade`) | database schema | yes |
| 12 | `step_create_administrator` | Skips when an admin already exists, otherwise `create_admin(username, password)` | admin row in `users` | yes |
| 13 | `step_verify_assets` | Checks the bundled themes, the migration versions, `templates/base.html` and the Vite manifest; missing assets become warnings and a failed result | — | no |
| 14 | `step_readiness_check` | `create_app()` then `SELECT 1` against the database | — | yes |
| 15 | `step_write_metadata` | `_save_progress()` → `onboarding-metadata.json` | `<data_dir>/onboarding-metadata.json` | yes |
| 16 | `step_render_completion` | Builds a `CompletionInfo` and renders the human-readable summary and the next command | — | no |

`STEP_NAMES` is the ordered list of these function names and is what the resume machinery indexes into.

### Mode and Scope

`step_resolve_paths` maps the input to an `InstallMode`:

| Input | `InstallMode` | Config file | Env file | Data directory |
|---|---|---|---|---|
| `--mode docker` | `DOCKER` | `/etc/devlog/config.toml` | `/etc/devlog/.env` | `/data` |
| `--mode native --scope system` | `SYSTEM` | `/etc/devlog/config.toml` | `/etc/devlog/.env` | `/var/lib/devlog` |
| `--mode native --scope user` | `USER` | `~/.config/devlog/config.toml` | `~/.config/devlog/.env` | `~/.local/share/devlog` |
| `--mode native`, no scope | `DEVELOPMENT` | `<cwd>/config.toml` | `<cwd>/.env` | `<cwd>/data` |

The paths come from `RuntimePaths.for_mode()` in `app/filesystem/layout.py`, which also honours the `DEVLOG_CONFIG_FILE`, `DEVLOG_ENV_FILE` and `DEVLOG_DATA_DIR` overrides. When the caller supplies explicit paths (`run_steps(config_path=..., data_path=...)`), `ctx.paths_explicit` is set and the resolved paths are kept instead of the mode defaults.

### Repeat Behaviour

| Step class | Re-running the pipeline |
|---|---|
| Observation steps (0, 1, 6, 7, 13, 16) | Safe; they observe state and produce the same result |
| `step_readiness_check` | Safe; it builds the app and runs `SELECT 1` against the database |
| `step_create_directories` | Safe; existing directories are left alone |
| `step_run_migrations` | Safe; `flask db upgrade` only applies pending revisions |
| `step_create_administrator` | Skipped when `ctx.state.admin_exists` is true, so an existing admin's password is not changed |
| `step_write_config` | Overwrites `config.toml` from the current answers, after taking a timestamped backup |
| `step_write_env` | Rewrites the env file from the current secrets, after taking a timestamped backup |
| `step_write_metadata` | Overwrites `onboarding-metadata.json` |

`step_create_administrator` can still fail on a re-run: `create_admin()` raises `ConflictError` when a non-admin user already holds the chosen username, and rejects passwords that do not satisfy its complexity rule (at least 8 characters, at least three of four character classes). Both exceptions are caught and reported as a failed step, which triggers compensation.

## `OnboardingInput` and `build_config_from_input()`

`OnboardingInput` is a frozen dataclass in `app/onboarding/model.py` holding the operator's answers. It is the only input the pipeline takes; the CLI fills it and `run_steps()` passes it through unchanged.

| Field | Default | Set by |
|---|---|---|
| `mode` | `"native"` | `--mode` |
| `profile` | `"development"` | `--profile` |
| `scope` | `""` | `--scope` |
| `site_title` | `"DevLog"` | prompt |
| `site_description` | `"A place for thoughts on code"` | prompt |
| `base_url` | `"http://localhost:5000"` | `--site-url` |
| `bind_host` | `"127.0.0.1"` | — |
| `bind_port` | `5000` | — |
| `behind_reverse_proxy` | `False` | — |
| `admin_username` | `"admin"` | `--admin-username` |
| `admin_password` | `""` | `--admin-password-file`, or an interactive prompt |
| `enable_newsletter` | `False` | prompt |
| `smtp_host` / `smtp_port` / `smtp_user` / `smtp_password` | `""` / `587` / `""` / `""` | prompt (only when newsletter is enabled) |
| `from_address` | `"blog@example.com"` | prompt |
| `enable_scheduler` | `False` | prompt |
| `enable_redis` | `False` | prompt |
| `storage_backend` | `"local"` | — |
| `backup_dir` | `"backups"` | — |
| `enable_backup_encryption` | `False` | — |
| `s3_access_key` / `s3_secret_key` | `""` | — |
| `theme_dark` | `"Catppuccin Mocha"` | — |
| `theme_light` | `"Catppuccin Latte"` | — |
| `theme_scheme` | `"system"` | — |
| `dry_run` | `False` | `--dry-run` |
| `non_interactive` | `False` | `--non-interactive` |
| `accept_defaults` | `False` | `--accept-defaults` |

`build_config_from_input(inp, data_dir=...)` maps those answers onto the typed model in `app/config/model.py` and returns a `DevLogConfig`:

| Derived value | Rule |
|---|---|
| `server.host` | `0.0.0.0` in docker mode, otherwise `bind_host` |
| `server.debug` | `not is_production`, where `is_production` is `profile in ("native-production", "docker-production")` |
| `database.uri` | docker: `sqlite:///data/blog.db`; otherwise `sqlite:///<data_dir resolved>/blog.db`, falling back to `data/blog.db` when `data_dir` is `None` |
| `redis.url` | always `redis://localhost:6379/0` |
| `redis.cache_url`, `redis.rate_limit_url`, `celery.broker_url` | the Redis URL only when `enable_redis` is true, otherwise empty |
| `scheduler.enabled` | `enable_scheduler` |
| `storage.backend` | `storage_backend` |
| `themes.default_dark` / `default_light` / `default_scheme` | `theme_dark` / `theme_light` / `theme_scheme` |
| `backup.data_backup_dir` | `backup_dir` |
| `session_cookie_secure` | true when `base_url` starts with `https://` or the profile is a production profile |
| `proxy_count` | `2` when `behind_reverse_proxy`, otherwise `1` |
| `flask_env` | `"production"` for a production profile, otherwise `""` |
| `secret_key` | empty — the real value is written to the env file, never to `config.toml` |
| `admin_password` | `input.admin_password` |

Sections with no corresponding question — `newsletter`, `comments`, `health`, `metrics`, `security`, `webhook`, `logging`, `search` — are left at their model defaults. `enable_newsletter` has no representation in the config model; it only controls the prompt flow and whether an SMTP password is generated.

The result is consumed in two places: `step_validate_proposal` validates it with `validate_all()` from `app/config/validation.py`, and `step_write_config` serialises it with `config_to_toml()` from `app/config/serialization.py`. `config_to_toml()` redacts every field listed in `SECRET_FIELDS`, so the SMTP password in the written file is a placeholder (`se**et`), not the value.

## Secrets

`app/onboarding/secrets.py` owns generation and persistence. The generators are:

| Function | Value |
|---|---|
| `generate_secret_key()` | `secrets.token_hex(32)` — 64 hex characters |
| `generate_health_secret()` | `secrets.token_urlsafe(32)` |
| `generate_metrics_secret()` | `secrets.token_urlsafe(32)` |

`resolve_secrets(inp, existing)` produces the secret map. Every key prefers a value from `existing` — the env file already on disk — and only generates a new one when none is present:

| Key | Generated when | Reuse source |
|---|---|---|
| `SECRET_KEY` | always | existing `SECRET_KEY`, else `generate_secret_key()` |
| `ADMIN_PASSWORD` | always | existing `ADMIN_PASSWORD`, else the input password |
| `HEALTH_CHECK_SECRET` | always | existing value, else `generate_health_secret()` |
| `METRICS_SECRET` | always | existing value, else `generate_metrics_secret()` |
| `SMTP_PASSWORD` | `enable_newsletter` or `smtp_host` is set | existing value, else the input password |
| `BACKUP_ENCRYPTION_KEY` | `enable_backup_encryption` | existing value, else `secrets.token_hex(32)` |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | `storage_backend == "s3"` | existing value, else the input value |

`step_resolve_secrets` reads the env file with `read_env_file()`, merges the input password, calls `resolve_secrets()`, and then re-asserts the operator's password over the result — so an explicitly supplied admin password wins over the value already in the file. The step returns only the *names* of the resolved keys in `StepResult.details`; no value is ever placed in a step result, the plan, the completion output or a log line.

`write_env_file(path, secrets)` writes the file in a fixed order — `SECRET_KEY`, `ADMIN_PASSWORD`, then the optional `HEALTH_CHECK_SECRET`, `METRICS_SECRET`, `SMTP_PASSWORD`, `BACKUP_ENCRYPTION_KEY`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`. It writes to a temp file in the same directory, applies `chmod 0600` to it and renames it over the target, so the file is never briefly world-readable and is never left half-written.

`read_env_file(path)` is the inverse: it skips blank lines and `#` comments, ignores lines without `=`, and strips matching single or double quotes from the value.

## State and Metadata

### Installation state

`detect_installation(config_path, data_path, env_path)` in `app/onboarding/state.py` returns an `InstallationInfo`:

| Field | Meaning |
|---|---|
| `state` | `InstallState.UNKNOWN`, `FRESH`, `PARTIAL` or `COMPLETE` |
| `config_exists` | a config file was found |
| `env_exists` | an env file was found |
| `database_exists` | a SQLite database was found |
| `metadata_exists` | `onboarding-metadata.json` was found in the data directory |
| `admin_exists` | the database contains at least one admin user |
| `config_path` | the resolved config file |
| `data_path` | the resolved database file |

The state is derived as: `COMPLETE` when config, database and admin all exist; `PARTIAL` when a config or a database exists; `FRESH` otherwise. `UNKNOWN` is declared but never produced.

Discovery order:

| Artefact | Explicit argument | Environment variable | Fallback candidates |
|---|---|---|---|
| Config | `config_path` | `DEVLOG_CONFIG` | `config.toml`, `~/.config/devlog/config.toml` |
| Env file | `env_path` | `DEVLOG_ENV_FILE` | `.env`, `~/.config/devlog/devlog.env` |
| Database | `data_path` (directory) | — | `<data_dir>/blog.db`, `<data_dir>/devlog.sqlite3`, or `data/blog.db`, `data/devlog.sqlite3`, `blog.db`, `devlog.sqlite3` |

The admin check opens the SQLite file directly and runs `SELECT COUNT(*) FROM users WHERE is_admin = 1`. Any exception — a missing table, a locked file, a non-SQLite file — is swallowed and the admin is reported as absent. When no explicit paths are given, `detect_installation()` first asks `app/filesystem/layout.py` for the mode via `detect_mode()` and `RuntimePaths.for_mode()`.

### Progress metadata

`app/onboarding/metadata.py` defines the persisted record:

| Field | Meaning |
|---|---|
| `version` | `METADATA_VERSION` (1); a different value makes `load_metadata()` return `None` |
| `mode` / `profile` | the inputs the run used |
| `package_version` | `importlib.metadata.version("devlog")`, or `""` when the package is not installed |
| `completed_at` | UTC ISO timestamp, set only when the run reaches the end |
| `config_path` / `data_path` | where the run wrote |
| `managed_paths` | the config file, the env file, the data directory and the backup directory |
| `admin_username` | the administrator that was requested |
| `last_completed_step` | index of the last successful step (`-1` when none) |
| `stopped_at` / `stopped_reason` | the failing step name and its message |

`save_metadata()` writes the file through a temp file and `os.replace()`. `is_complete(metadata)` is true when the version matches and `completed_at` is non-empty.

### Resume

`_save_progress()` is called after every successful step, so the metadata file always reflects the furthest point reached. When a step fails, the pipeline calls `_save_progress(ctx, i, stopped_at=..., stopped_reason=...)` before compensating.

`resume_onboarding(data_path)` in `app/services/operations/onboard.py`:

1. Reads the metadata from `data_path or Path("data")`. If there is none, it returns `onboard.resume.no_metadata`.
2. If `is_complete(metadata)` is true, it returns `onboard.resume.complete` and does nothing.
3. Otherwise it sets `start_step = metadata.last_completed_step + 1` and calls `run_steps(inp, start_step=start_step)`. Steps before `start_step` return `StepResult(ok=True, message="Skipped (resume from step N)")`.

The result codes are `onboard.resume.no_metadata`, `onboard.resume.complete`, `onboard.resume.failed` and `onboard.resumed`.

## The Planner

`generate_plan(inp, state)` in `app/onboarding/planner.py` returns a list of `PlannedAction(action, target, details)`. The action vocabulary is fixed:

| Action | Icon in text output | Meaning |
|---|---|---|
| `create` | `+` | the target does not exist and will be created |
| `update` | `~` | the target exists and will be overwritten, with a backup |
| `preserve` | `=` | the target exists and will be kept |
| `skip` | `-` | reserved; never emitted today |
| `conflict` | `!` | reserved; never emitted today |

The plan covers the config file, the env file, the data directory, the backup directory, the admin user, the database migrations and the completion metadata, in that order. The config action depends on the installation state: `preserve` for `COMPLETE`, `update` when a config exists, `create` otherwise. The admin action is `create` when no admin exists and `preserve` when one does.

`format_plan_text(plan)` renders the plan as an indented list with a one-line detail under each action and a total count. `format_plan_json(plan)` renders the same data as a JSON array of objects with `action`, `target` and `details`. The CLI's `plan` command uses the text rendering by default and the JSON rendering with `--json`; the service layer returns the structured list and the CLI formats it.

## The CLI Surface

`devlog onboard` is registered in `devlog_cli/main.py`; the subcommands live in `devlog_cli/commands/onboard.py` and call the service layer in `app/services/operations/onboard.py`.

| Command | Service call | Steps executed |
|---|---|---|
| `devlog onboard detect` | `detect_installation()` | none — `state.detect_installation()` only |
| `devlog onboard plan` | `generate_plan(inp)` | none — `planner.generate_plan()` only |
| `devlog onboard run` | `apply_onboarding(input_dict)` | the full pipeline via `run_steps()` |
| `devlog onboard resume` | `resume_onboarding(data_path)` | from `metadata.last_completed_step + 1` |

Options:

| Command | Options |
|---|---|
| `detect` | none |
| `plan` | `--mode {native,docker}`, `--scope {system,user}`, `--profile {development,native-production,docker-production,minimal,full}`, `--json` |
| `run` | `--mode`, `--scope`, `--profile`, `--non-interactive`, `--dry-run`, `--accept-defaults`, `--site-url`, `--admin-username`, `--admin-password-file`, `--json` |
| `resume` | `--data-path`, `--json` |

Behaviour worth knowing at the CLI boundary:

- `--non-interactive` refuses to prompt. The admin password must then come from `--admin-password-file`; the CLI exits with `onboard.run.missing_password` otherwise.
- Without `--non-interactive`, the CLI prompts for the admin password itself (with confirmation) when stdin is a TTY, and refuses with the same code when it is not.
- `--accept-defaults` suppresses the in-step prompts entirely; `step_collect_inputs` only prompts when both `non_interactive` and `accept_defaults` are false.
- `--dry-run` runs the whole pipeline with the seven mutating steps skipped. The remaining steps still run, including the prompts and the path resolution.
- `run` has no `--config-path` or `--data-path`; only `resume` exposes `--data-path`.
- Every command renders through `devlog_cli/output.render()` and exits with the result's exit code, so `--json` output is stable for scripting.

The service layer returns typed results from `app/services/operations/results.py`: `OnboardDetectResult`, `OnboardPlanResult`, `OnboardApplyResult` and `OnboardResumeResult`. `apply_onboarding()` raises `ValueError` when the admin password is missing or when the last step failed; the CLI turns that into `onboard.run.failed`.

## Notes and Gotchas

Findings below were verified against the source. They are recorded, not fixed.

### The written `config.toml` holds fewer sections than the config that was built

`build_config_from_input()` populates the `database`, `redis`, `celery`, `scheduler`, `storage`, `health`, `metrics`, `logging` and `paths` sections, but `config_to_toml()` serialises only thirteen: `app`, `admin`, `server`, `author`, `site`, `email`, `newsletter`, `comments`, `themes`, `backup`, `security`, `webhook`, `search`. The database URI, the storage backend, the scheduler flag and the Redis URLs therefore exist only in the in-memory config that `step_validate_proposal` validates; they are not written to `config.toml` and are not restored by the loader. The same applies to the top-level fields `secret_key`, `admin_password`, `session_cookie_secure`, `proxy_count` and `flask_env`.

### The plan's `preserve` action is not honoured by the run

`generate_plan()` emits `preserve` for the config file when the installation state is `COMPLETE`, but `step_write_config()` rewrites `config.toml` unconditionally from the current answers. A re-run with default answers replaces an existing configuration with the defaults; the timestamped backup is the only recovery path.

### A re-run rewrites the env file from scratch

`write_env_file()` emits only the eight keys it knows about. Any other key already in the file — `DATABASE_URL`, `REDIS_URL`, `FLASK_ENV`, `DEVLOG_DATA_DIR` — is dropped by the rewrite, even though the existing values of the keys it does write are preserved.

### Dry run is not side-effect free

`step_resolve_paths()` calls `mkdir(parents=True, exist_ok=True)` on the config directory and the data directory without consulting `ctx.dry_run`, and `step_collect_inputs()` still prompts. Only the seven mutating steps check the flag. A dry run therefore leaves two empty directories behind.

### Resume does not restore the failed run's context

`resume_onboarding()` rebuilds the input as `OnboardingInput(mode=metadata.mode, profile=metadata.profile, non_interactive=True)` — no admin password, no scope, no paths — and calls `run_steps(inp, start_step=...)` without `config_path` or `data_path`. `run_steps()` starts from a fresh `StepContext` whose defaults are `config_dir=Path(".")`, `data_dir=Path("data")` and `env_file=Path(".env")`. Because the skipped steps do not run again, `ctx.config`, `ctx.secrets` and `ctx.state` are empty, and the resumed run targets the working directory rather than the paths the original run used. `resume_onboarding()` also looks for the metadata in `data_path or Path("data")` rather than in the recorded `metadata.data_path`.

### The pipeline's paths and the application's paths are resolved independently

`step_run_migrations()` and `step_create_administrator()` call `create_app()`, which loads configuration through `load_effective_config()` → `resolve_config_path()` / `resolve_env_file_path()` in `app/config/paths.py`. Those candidates are `DEVLOG_CONFIG`, `DEVLOG_ENV_FILE`, the XDG and home `devlog.env` locations, and the working-directory `config.toml` / `.env`. The `StepContext` paths are never consulted, and the pipeline does not export `DEVLOG_*` variables for them. In a development-scope install the working-directory candidates happen to coincide with the resolved paths; in a system- or user-scope install they do not.

### Env file naming differs between the two path authorities

`RuntimePaths` names the env file `<config_dir>/.env` in every mode (`/etc/devlog/.env`, `~/.config/devlog/.env`, `<cwd>/.env`). `resolve_env_file_path()` looks for `devlog.env` in the XDG, home and system locations and `.env` only in the working directory. `app/onboarding/state.py::_find_env_file()` uses the `devlog.env` spelling. A system- or user-scope install therefore finds its env file only when `DEVLOG_ENV_FILE` is exported.

### Three of the generated secrets do not reach the typed configuration

`SECRET_KEY` and `ADMIN_PASSWORD` from the env file are picked up by `load_effective_config()`. `HEALTH_CHECK_SECRET`, `METRICS_SECRET` and `SMTP_PASSWORD` are not: the environment override map writes them to the prefixed keys `health_check_secret`, `metrics_secret` and `email_smtp_password`, while `_build_section()` reads the unprefixed TOML keys `check_secret`, `secret` and `smtp_password`. The result is `HealthConfig.check_secret`, `MetricsConfig.secret` and `EmailConfig.smtp_password` stay empty, and the consumers in `app/routes/public/meta.py` and `app/email.py` read those empty values. This is in the configuration loader rather than in the onboarding package, but it breaks the onboarding → application handoff for three of the keys onboarding writes.

### Two metadata APIs for the same file

`app/onboarding/state.py` and `app/onboarding/metadata.py` both define `load_metadata()` and `save_metadata()` for `onboarding-metadata.json`. The package `__init__.py` exports the typed pair from `metadata.py`; the dict-based pair in `state.py` is reachable only by importing `app.onboarding.state` directly, and the pipeline never uses it.

### `InstallationInfo.data_path` holds the database file

`detect_installation()` returns `data_path=resolved_data`, the first existing candidate among `blog.db` and `devlog.sqlite3` — a file, not a directory. `generate_plan()` uses that value as its "data directory" target, so the plan names a file where a directory is meant.

### The plan's env target is hard-coded

`generate_plan()` uses `Path(".env")` regardless of the resolved env file, so a system-scope plan reports `.env` rather than `/etc/devlog/.env`.

### `step_verify_assets` can fail the whole pipeline

The step returns `ok=False` when the Vite manifest is missing, and `run_steps()` then compensates — deleting the `config.toml` and the env file it has just written — and stops. `app/static/` has no `__init__.py`, so `files("app.static")` raises and the check falls back to the relative path `app/static/dist/manifest.json`, resolved against the working directory. The Docker build runs the Vite build, so a native install from a release wheel is unaffected; a source checkout without `npm run build` is not.

### Permissions are applied to the env file only

`write_env_file()` chmods the temp file to `0600` before the rename. `_atomic_write()` in `app/onboarding/steps.py` sets no mode on the config file, so `config.toml` takes the process umask.

### Temp file naming replaces the suffix

`write_env_file()` and `save_metadata()` derive their temp file with `Path.with_suffix(".tmp")`, which replaces the existing suffix: `devlog.env` → `devlog.tmp`, `onboarding-metadata.json` → `onboarding-metadata.tmp`. Two env files in one directory with different names can therefore target the same temp file.

### The metadata file is rewritten after every step

`_save_progress()` is called after each successful step, and `step_write_metadata()` calls it again, so the metadata file is written repeatedly. `completed_at` is only set once `step_index >= len(_ALL_STEPS) - 2`, that is, at `step_write_metadata`.

### Discrepancies with existing documentation

These are recorded here rather than corrected, since the onboarding package and the other documents are owned elsewhere.

| Document | Claim | Observed |
|---|---|---|
| `architecture/deployment/installation.md` | Onboarding "Writes `.devlog-installation.json` metadata" | The pipeline writes `onboarding-metadata.json` in the data directory. `.devlog-installation.json` belongs to the filesystem layer in `app/filesystem/layout.py`. |
| `architecture/deployment/installation.md` | "Onboarding is idempotent — safe to re-run for reconfiguration" | The config and env files are rewritten on every run, and the env rewrite drops unrelated keys. See the notes above. |
| `AGENTS.md` | "When `--scope` is omitted, the onboarding step detects the appropriate scope from the current installation" | `step_resolve_paths()` maps an empty scope to `InstallMode.DEVELOPMENT`. It performs no scope detection. |
| `architecture/overview.md` | "`RuntimePaths` is the sole path-resolution authority — neither the installer nor onboarding derives paths independently" | `app/onboarding/state.py` keeps its own candidate lists for the config, the env file and the database, and `step_resolve_paths()` carries an `ImportError` fallback that derives `/etc/devlog`, `/var/lib/devlog` and `~/.local/share/devlog` directly. The filesystem test suite explicitly allows these two files. |
| `AGENTS.md` | "Dry-run mode skips all mutations" | `step_resolve_paths()` creates the config and data directories during a dry run. |

## See Also
- [App Factory](app-factory.md) - `create_app()`, which the migration, admin and readiness steps call
- [Configuration](configuration.md) - The typed config model, loader and validation that `build_config_from_input()` targets
- [Models](models.md) - The schema the migration and admin steps operate on
- [Filesystem Layout](filesystem.md) - `RuntimePaths`, the source of the resolved onboarding paths
- [Deployment Installation](../deployment/installation.md) - The installer half of the installation contract
- [Deployment Overview](../deployment/overview.md) - Container and service topology
- [Services Overview](../services/overview.md) - The service layer that `app/services/operations/onboard.py` belongs to
- [Backup Service](../services/backup.md) - The backup directory the onboarding pipeline creates
- [Architecture Overview](../overview.md) - Where onboarding sits in the system
