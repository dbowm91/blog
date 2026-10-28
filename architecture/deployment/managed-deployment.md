# Managed Deployment (`app/deployment/`)

The layer that renders host-level configuration for a native (non-Docker) installation, installs it atomically, detects drift between the installed files and the desired state, and drives the service lifecycle. It is reached through `devlog deploy render|install|check` and the top-level `devlog start|stop|restart|status|logs` commands. It is **not** the Docker path — the container bundle is owned by `docker-compose.yml`, `nginx/` and the `Dockerfile` (see [Docker](docker.md)).

Everything here is a pure function over a `DeploymentContext` until the install step: renderers turn a context into text, the installer writes that text to disk, and the drift checker compares what is on disk against what the renderers would produce now. The renderers never touch the host; only `app/deployment/install.py` does.

## Module Layout

| File | Purpose |
|---|---|
| `app/deployment/__init__.py` | Public re-exports of the renderers, install types and drift helpers |
| `app/deployment/model.py` | `DeploymentContext`, `RenderResult`, `validate_deployment_context()` |
| `app/deployment/systemd.py` | `render_web_unit()`, `render_worker_unit()`, `render_scheduler_unit()`, `validate_unit()` |
| `app/deployment/compose.py` | `render_compose()`, `render_compose_env()` |
| `app/deployment/proxy.py` | `render_caddyfile()`, `render_nginx_config()`, `validate_caddyfile()`, `validate_nginx_config()` |
| `app/deployment/logrotate.py` | `render_logrotate()` |
| `app/deployment/install.py` | `ManagedFile`, `InstallPlan`, `InstallResult`, `plan_installation()`, `execute_installation()`, `backup_file()`, `restore_backups()` |
| `app/deployment/drift.py` | `DriftStatus`, `DriftItem`, `DriftReport`, `compute_content_hash()`, `check_drift()`, `load_managed_manifest()`, `save_managed_manifest()` |
| `app/deployment/lifecycle.py` | `ServiceBackend`, `ServiceStatus`, `LifecycleStatus`, `detect_backend()`, `get_service_status()`, `start_service()`, `stop_service()`, `restart_service()`, `get_logs()`, `run_command()` |

The service wrapper the CLI calls is `app/services/operations/deploy.py`; it owns the `OperationResult` shaping and the `deploy_render()` / `deploy_install()` / `deploy_check()` / `lifecycle_*()` entry points. The operator surface is `devlog_cli/commands/deploy.py` and `devlog_cli/commands/lifecycle.py`.

## The Deployment Context

`DeploymentContext` is a frozen dataclass in `app/deployment/model.py`. Every renderer takes one and reads nothing else.

| Field | Type | Where it comes from |
|---|---|---|
| `mode` | `InstallMode` | `from_config()` argument; defaults to `InstallMode.DEVELOPMENT` |
| `config` | `DevLogConfig` | `current_app.config["DEVLOG_CONFIG"]`, supplied by the deploy service |
| `paths` | `RuntimePaths` | `RuntimePaths.for_mode(mode)` — see [Filesystem Layout](../core/filesystem.md) |
| `metadata` | `InstallationMetadata \| None` | `InstallationMetadata.load(paths.installation_metadata.path)` when that file exists |
| `version` | `str` | `importlib.metadata.version("devlog")`, falling back to `"0.0.0"` |

Derived properties are the renderers' only vocabulary for "what kind of install is this":

| Property | Derivation |
|---|---|
| `is_system` / `is_user` / `is_docker` / `is_development` | Comparison against `mode` |
| `service_user` / `service_group` | `"devlog"` in system mode, otherwise `getpass.getuser()` |
| `bind_address` / `bind_port` | `config.server.host` / `config.server.port` |
| `public_url` | `config.site.base_url` |
| `has_redis` / `has_celery` / `has_scheduler` / `has_smtp` | `config.redis.url`, `config.celery.broker_url`, `config.scheduler.enabled`, `config.email.smtp_host` |
| `is_production` | `config.is_production()` — `flask_env == "production"` |
| `log_to_file` | `config.logging.level != "DEBUG"` or the log directory already exists |

`validate_deployment_context(ctx)` returns a list of error strings, currently two checks:

- Scheduler enabled but `config.celery.broker_url` is empty — scheduled jobs will not execute without a broker.
- Scheduler enabled in `InstallMode.DEVELOPMENT` — the scheduler unit is not generated for a foreground deployment.

The function is exported from `app/deployment/__init__.py` and exercised by the test suite, but the deploy service never calls it (see [Notes and Gotchas](#notes-and-gotchas)).

## Renderers

Every renderer returns a `RenderResult`: `content`, `filename`, `managed`, `warnings`, `permissions` (default `0o644`) and `description`. `filename` is a bare name, not a path — the installer decides where it lands.

### systemd Units

Three entry points in `app/deployment/systemd.py`, all taking `user_unit: bool = False`:

| Entry point | Emitted filename | Returns `None` when |
|---|---|---|
| `render_web_unit(ctx, *, user_unit=False)` | `devlog-web.service` / `devlog-web@.service` | never |
| `render_worker_unit(ctx, *, user_unit=False)` | `devlog-worker.service` / `devlog-worker@.service` | `not ctx.has_celery` |
| `render_scheduler_unit(ctx, *, user_unit=False)` | `devlog-scheduler.service` / `devlog-scheduler@.service` | `not ctx.has_scheduler` |

All three share the same hardening block: `EnvironmentFile` pointing at `paths.env_file`, `ExecStartPre=/usr/bin/test -d` for each of the data / log / runtime directories, `Restart=on-failure`, `RestartSec=5`, `TimeoutStartSec=30`, `Umask=0027`, `NoNewPrivileges=true`, `PrivateTmp=true`, `ProtectSystem=strict`, `ProtectHome=true`, and `ReadWritePaths` listing the same three directories. System mode adds `User=`/`Group=` and `WantedBy=multi-user.target`; user mode omits the user and group and uses `WantedBy=default.target`.

The `ExecStart` differs by mode:

| Unit | System mode | User mode |
|---|---|---|
| web | `<release_dir>/venv/bin/python -m granian --interface asgi --workers 4 --host <bind> --port <port> app.asgi:asgi_app` | `devlog serve --host <bind> --port <port>` |
| worker | `<release_dir>/venv/bin/celery -A app.celery_app worker --loglevel=info --concurrency=1` | `devlog worker` |
| scheduler | `<release_dir>/venv/bin/flask scheduler-start` | `devlog scheduler` |

Every system-mode path comes from `ctx.paths.release_dir` via `_release_venv()`, so the
units follow the resolved release instead of a hardcoded prefix. `release_dir` is `/opt/devlog/current`
in system mode and `None` in the other three modes, in which case the renderer falls back
to the bare command names.

The worker and scheduler units carry `After=network.target devlog-web.service`. The web unit also emits `ExecStartPre=<release_dir>/venv/bin/devlog config check --config <config_file>`.

`validate_unit(content)` returns a list of errors:

- One of `[Unit]`, `[Service]`, `[Install]` is missing.
- An `ExecStart=` line inside `[Service]` contains shell interpolation (`${VAR}` or `$VAR`), matched by `_SHELL_INTERPOLATION_RE`.

### Compose File and Compose Env

`render_compose(ctx)` emits `docker-compose.yml` (mode `0o644`). The service set is conditional:

| Service | Included when |
|---|---|
| `web` | always |
| `redis` | `ctx.has_redis` — otherwise a warning is attached: *Redis is not configured; celery and scheduler services will not be included* |
| `celery` | `ctx.has_celery` |
| `scheduler` | `ctx.has_scheduler` |

`web` is built from the current directory (`build: .`), publishes `127.0.0.1:<port>:<port>`, mounts the `devlog_data`, `devlog_config` and `devlog_logs` volumes, and declares a `curl -f http://localhost:<port>/health` healthcheck with 512M/256M memory limits. The `celery` service runs `celery -A app.celery_app worker --loglevel=info --concurrency=1`; the `scheduler` service runs `flask scheduler-start`. Both depend on `redis` with `condition: service_healthy`.

`render_compose_env(ctx)` emits `docker-compose.env` (mode `0o600`). It contains no secrets — only non-secret variables, and a key whose value is empty is emitted as a commented placeholder (`# KEY=  # Set in .env`):

`FLASK_APP`, `FLASK_ENV` (`config.flask_env` or `"production"`), `SERVER_HOST`, `SERVER_PORT`, `SESSION_COOKIE_SECURE`, `PROXY_COUNT`, `REDIS_URL`, `CACHE_REDIS_URL` (`redis.cache_url` or `redis.url`), `CELERY_BROKER_URL` (`celery.broker_url` or `redis.url`), `ADMIN_USERNAME`, `ENABLE_SCHEDULER`, `ENABLE_METRICS`, plus `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`FROM_ADDRESS` when `email.smtp_host` is set and `BASE_URL` when `site.base_url` is set.

### Reverse Proxy Configuration

`app/deployment/proxy.py` renders both proxies from the same `ctx.public_url` and `ctx.bind_address` / `ctx.bind_port`.

`render_caddyfile(ctx)` emits `Caddyfile` (mode `0o644`):

| Block | Content |
|---|---|
| site address | `<hostname>:<listen>` — `:80` for plain HTTP on 80 or no explicit port, the public port otherwise, `:443` for HTTPS |
| `tls { }` | emitted only when the public URL scheme is `https` |
| `request_body` | `max_size <n>MB`, where `n` is `config.app.max_upload_size` converted to whole MiB (minimum 1) |
| `@health` | matches `/health`; the access log for that matcher is discarded |
| `header` | `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy: strict-origin-when-cross-origin`, and `-Server` |
| `encode` | `gzip zstd` |
| `proxy *` | `to http://<bind>:<port>` with `header_up` for the three forwarded headers |
| `@static` | matches `/uploads/*`; serves `paths.uploads_dir` with `file_server` |

Warnings attached: a localhost public URL with a `0.0.0.0` bind address; an HTTPS public URL with a `0.0.0.0` bind address; and an unconditional note that Caddy has no built-in rate limiting and the application does not rate limit the login routes, so a rate limiting plugin or a WAF is required.

`render_nginx_config(ctx)` emits `devlog.conf` (mode `0o644`). The file's own header states that it must be included from the **http** context, because `limit_req_zone` is only valid there.

| Directive | Value |
|---|---|
| `limit_req_zone` | `zone=login:10m rate=5r/m` and `zone=admin:10m rate=20r/m`, keyed on `$binary_remote_addr` |
| `upstream devlog_backend` | `server <bind>:<port>; keepalive 32;` |
| `server` | `listen <port>` (`443 ssl http2` for HTTPS), `server_name <hostname>`, `client_max_body_size <n>M`, proxy timeouts, the five `proxy_set_header` lines, gzip settings, and the four security headers with `always` |
| TLS | `ssl_certificate /etc/ssl/devlog/cert.pem`, `ssl_certificate_key /etc/ssl/devlog/key.pem`, `ssl_protocols TLSv1.2 TLSv1.3` — emitted only for HTTPS |
| `location /uploads/` | `alias <uploads_dir>/;` with `expires 30d` |
| `location /health` | `access_log off`, proxied to `devlog_backend` |
| `location = /login`, `location = /admin/login` | `limit_req zone=login burst=5 nodelay; limit_req_status 429;` |
| `location /` | catch-all proxy to `devlog_backend` |

Validators:

| Validator | Checks |
|---|---|
| `validate_caddyfile(content)` | Brace balance across non-comment lines; at least one block (a line ending in `{`) |
| `validate_nginx_config(content)` | Brace balance; `server` / `upstream` directives open a block; `listen` / `server_name` directives end in `;` |

### Logrotate Policy

`render_logrotate(ctx)` emits a file named `devlog` (mode `0o644`) covering `<log_dir>/*.log`: `daily`, `rotate 14`, `compress`, `delaycompress`, `missingok`, `notifempty`, `create 0640 <service_user> <service_group>`, `sharedscripts`, and a `postrotate` hook that runs `systemctl reload devlog-web`.

It returns `None` — no policy at all — when `ctx.log_to_file` is false, which happens when the logging level is `DEBUG` and the log directory does not yet exist.

## Installation

`app/deployment/install.py` owns the write path. Three types describe the work:

| Type | Fields |
|---|---|
| `ManagedFile` | `path`, `content`, `permissions`, `backup_path` |
| `InstallPlan` | `files`, `warnings`, `dry_run` |
| `InstallResult` | `ok`, `installed_files`, `backed_up_files`, `errors`, `warnings` |

`plan_installation(rendered_files, *, force=False, base_dir=None)` resolves each rendered file to a target and decides whether it should be written:

- Without an explicit `base_dir`, each file goes to the directory its consumer reads, taken from `DEFAULT_TARGET_DIRS`: `systemd` → `/etc/systemd/system`, `compose` → `/etc/devlog`, `caddy` → `/etc/caddy`, `nginx` → `/etc/nginx/conf.d`, `logrotate` → `/etc/logrotate.d`. The target is carried on `RenderResult.target`.
- An explicit `base_dir` overrides that and sends every file to one directory.
- `_resolve_install_path()` uses an absolute `filename` as-is and joins a relative one onto the chosen base.
- If the target exists and `force` is false, the file is dropped from the plan with the warning *File already exists, skipping: &lt;path&gt;* — it is never overwritten.
- If the target exists and `force` is true, the warning is *Overwriting existing file: &lt;path&gt;* and the existing file is copied to `&lt;path&gt;.bak` first.

`execute_installation(plan, *, dry_run=False)` performs the writes:

- `dry_run=True` returns `ok=True` with the planned paths and the warning *Dry run; no files were written*.
- Otherwise, for each `ManagedFile`: record the backup for rollback, write the file atomically, apply the declared permissions, append the path to `installed_files`.
- On an `OSError` the loop breaks with the error *Failed to write &lt;path&gt;: &lt;exc&gt;*, every backup taken during this run is restored, and the result carries `ok=False`.

Atomicity comes from `_atomic_write()`: it creates the parent directory, writes to `<path>.tmp`, then `os.replace()`s the temporary file over the target. Any exception unlinks the temporary file and re-raises.

Backups:

- `backup_file(path)` copies to `<path>.bak` with `shutil.copy2`, preserving metadata. It returns `None` when the source does not exist or the copy raises `OSError`.
- `restore_backups(pairs)` copies each backup back over its original and returns `False` if any backup is missing or any copy fails.

## Drift Detection

`app/deployment/drift.py` compares what is on disk against a set of expected content hashes.

`compute_content_hash(content)` is a SHA-256 hex digest of the UTF-8 encoded content.

| Type | Values / fields |
|---|---|
| `DriftStatus` | `MISSING`, `MODIFIED`, `UNMANAGED`, `STALE` |
| `DriftItem` | `path`, `status`, `expected_hash`, `actual_hash`, `description` |
| `DriftReport` | `items`, `clean`, `managed_count`, `drift_count`, `unmanaged_count` |

`check_drift(managed_files, scan_dir)` takes a mapping of expected path to expected hash:

1. An expected path that does not exist yields `MISSING` — *"Expected file missing: &lt;path&gt;"*.
2. An expected path that cannot be read (`OSError` or `UnicodeDecodeError`) yields `MODIFIED` — *"Cannot read file: &lt;path&gt;"*.
3. An expected path whose recomputed hash differs yields `MODIFIED` — *"Content mismatch: &lt;path&gt;"*.
4. Every file in `scan_dir` that is not a key of `managed_files` yields `UNMANAGED` — *"Unmanaged file found: &lt;path&gt;"*. Files whose suffix is `.bak` or `.tmp` are skipped, and subdirectories are ignored.

`DriftReport.clean` is `drift_count == 0 and unmanaged_count == 0`, so unmanaged files alone make the report unclean.

### The Managed Manifest

The manifest is a JSON object mapping absolute path to SHA-256 hash:

```json
{
  "/etc/devlog/devlog-web.service": "9f2c…",
  "/etc/devlog/docker-compose.yml": "4b71…"
}
```

`save_managed_manifest(manifest_path, files)` writes it with `json.dumps(..., indent=2, sort_keys=True)` after sorting the entries by path, using the same temp-file-plus-`os.replace()` pattern as the installer. `load_managed_manifest(manifest_path)` returns `{}` for a missing file, an unreadable file, or invalid JSON.

The deploy service looks for the manifest at `<base_dir>/.devlog-manifest.json`, where `base_dir` is the `--base-dir` value or `/etc/devlog`. When no manifest is present it falls back to re-rendering every target and hashing the fresh content, so drift is measured against current output rather than against the state recorded at install time.

## Lifecycle

`app/deployment/lifecycle.py` shells out to `systemctl`, `journalctl` or `docker compose` through a single wrapper.

`run_command(cmd, *, timeout=30)` returns `(returncode, stdout, stderr)`. A missing binary yields `-1`, a timeout yields `-2`.

`ServiceBackend` has five members, not two:

| Member | Selected when |
|---|---|
| `SYSTEMD` | `mode == InstallMode.SYSTEM` |
| `SYSTEMD_USER` | `mode == InstallMode.USER` |
| `DOCKER` | `mode == InstallMode.DOCKER` |
| `FOREGROUND` | `mode == InstallMode.DEVELOPMENT` |
| `UNKNOWN` | fallback |

`detect_backend(metadata, mode)` maps the install mode first and only then consults `InstallationMetadata`.

`ServiceStatus` has five members: `INSTALLED`, `RUNNING`, `DEGRADED`, `FAILED`, `UNMANAGED`. `LifecycleStatus` carries `backend`, `status`, `version`, `pid`, `uptime`, `health` and a free-form `details` mapping.

`get_service_status(backend, *, user_unit=False, compose_dir=None)`:

- **systemd** — `systemctl [--user] is-active devlog-web.service`. `active` → `RUNNING`, `activating`/`reloading` → `DEGRADED`, `failed` → `FAILED`, `inactive` → `INSTALLED`, anything else → `UNMANAGED`. When running, the PID comes from `systemctl show devlog-web.service --property=MainPID --value` and the uptime from `ps -o etime= -p <pid>`.
- **docker** — `docker compose [--project-directory <dir>] ps --format json`, one JSON object per line. The `web` service is preferred, falling back to `app`. `running` → `RUNNING`, `restarting`/`starting` → `DEGRADED`, `exited`/`dead` → `FAILED`, `created` → `INSTALLED`, anything else → `UNMANAGED`.
- **foreground / unknown** — `UNMANAGED` with a hint in `details`.

The mutating operations are symmetric:

| Function | systemd | docker | foreground |
|---|---|---|---|
| `start_service()` | `systemctl [--user] start devlog-web.service` | `docker compose up -d web` | `False`, *"Cannot start foreground service via service manager."* |
| `stop_service()` | `systemctl [--user] stop devlog-web.service` | `docker compose stop web` | `False`, *"Cannot stop foreground service via service manager."* |
| `restart_service()` | `systemctl [--user] restart devlog-web.service` | `docker compose restart web` | `False`, *"Cannot restart foreground service via service manager."* |

`get_logs(backend, *, follow=False, tail=50, component="web", ...)` runs `journalctl -u devlog-<component>.service --no-pager -n <tail>` (plus `-f` when following) for systemd, and `docker compose logs --tail=<n> <component>` (plus `--follow`) for docker. The timeout is 10 seconds when following and 30 seconds otherwise.

Only the web unit is managed by the lifecycle commands — the worker and scheduler units are rendered but never started, stopped or inspected by this layer.

## Operator CLI

`devlog deploy` is a group with three subcommands, registered by `register_deploy_commands()` in `devlog_cli/commands/deploy.py`. `--mode` accepts `system`, `user`, `docker` or `development` and is required; `--user` is a shorthand that forces the `user` mode; `--json` switches the output format.

| Command | Options | Service call | Backing modules |
|---|---|---|---|
| `devlog deploy render` | `--target` (repeatable; `systemd`, `compose`, `caddy`, `nginx`, `logrotate`, `all`), `--print`, `--output DIR` | `deploy_render(mode, targets=…)` | `systemd.py`, `compose.py`, `proxy.py`, `logrotate.py` |
| `devlog deploy install` | `--target` (repeatable), `--force`, `--dry-run`, `--base-dir DIR` | `deploy_install(mode, targets=…, force=…, dry_run=…, base_dir=…)` | `install.py` |
| `devlog deploy check` | `--base-dir DIR` | `deploy_check(mode, base_dir=…)` | `drift.py` |

`render` returns the file contents in the result details; `--print` adds the content to each entry. `--output DIR` writes the rendered files into `DIR`, each named `{target}-{basename}` — for example `systemd-devlog-web.service`. Writing is skipped when `--print` is given.

The lifecycle commands are registered at the top level of the CLI rather than under `deploy`:

| Command | Options | Service call |
|---|---|---|
| `devlog start` | — | `lifecycle_start()` |
| `devlog stop` | — | `lifecycle_stop()` |
| `devlog restart` | — | `lifecycle_restart()` |
| `devlog status` | `--json` | `lifecycle_status()` |
| `devlog logs` | `--follow`/`-f`, `--tail`, `--component`/`-c`, `--json` | `lifecycle_logs()` |

The deploy service resolves the install mode for the lifecycle commands from `config.server.mode` if that attribute exists, falling back to `"development"`; it then calls `RuntimePaths.for_mode()` and `detect_backend()`.

Exit codes follow the shared CLI result model: a clean result is `Result.success` (exit `0`), a result carrying warnings is `Result.degraded` (exit `8`), and a failure is `Result.failure` (exit `1` for the deploy group, `ExitCode.SERVICE_ERROR` for the lifecycle group).

## Notes and Gotchas

Findings verified against the source. Nothing here is fixed — these are recorded, not corrected.

### The rendered compose files name a command that does not exist

Both `render_compose()` and `render_compose_env()` emit the header `# Do not edit manually; regenerate with: devlog deploy compose`. The `deploy` group registers only `render`, `install` and `check`.

### The rendered compose file is not the repository's compose file

The generated `docker-compose.yml` has no Compose profiles and uses the service names `web`, `redis`, `celery` and `scheduler` with `build: .`. The repository bundle in `docker-compose.yml` uses `blog`, `celery`, `redis`, `nginx` and `backup` behind explicit `--profile` selections. The two artifacts are unrelated and the generated one does not inherit the repository's profile requirement (see [Docker](docker.md)).

### The managed manifest is never written

`save_managed_manifest()` is exported and tested, but nothing in the install path calls it, so `<base_dir>/.devlog-manifest.json` never appears. `deploy_check()` therefore always takes its fallback branch and re-renders the targets to recompute the expected hashes, so drift is measured against current output rather than against the state recorded at install time.

### `deploy check` reports unmanaged files as failures

`check_drift()` scans the entire base directory and flags every file that is not in the manifest, skipping only `.bak` and `.tmp` suffixes. In system mode the base directory is also the configuration directory, so `config.toml` and `.env` are reported as unmanaged and `DriftReport.clean` is `False` even when every managed file matches. Verified: a directory holding one matching unit plus `config.toml`, `.env` and `.devlog-manifest.json` yields `drift_count=0` and `unmanaged_count=3`.

### `DriftStatus.STALE` has no producer

`check_drift()` only ever emits `MISSING`, `MODIFIED` and `UNMANAGED`. `STALE` is defined and exported but nothing creates it.

### The metadata fallback in `detect_backend()` is unreachable

`detect_backend()` handles all four `InstallMode` members before it inspects `metadata`, so the `metadata is not None` branch can never run for a valid `InstallMode` argument.

### The lifecycle backend is always `foreground`

`_lifecycle_ctx()` reads `config.server.mode` if the attribute exists. `ServerConfig` has only `host`, `port` and `debug`, so the lookup always fails and the mode falls back to `"development"` → `InstallMode.DEVELOPMENT` → `ServiceBackend.FOREGROUND`. `devlog status` consequently always reports `unmanaged` with the *"run with `python run.py`"* hint, and `devlog start` always returns *"Cannot start foreground service via service manager."* Verified: `hasattr(config.server, "mode")` is `False`.

### The validators are never called by the service or the CLI

`validate_deployment_context()`, `validate_unit()`, `validate_caddyfile()` and `validate_nginx_config()` are exported from `app/deployment/__init__.py` and exercised by the test suite, but the render, install and check paths never invoke them. Nothing rejects a malformed artifact before it is written to disk.

### The compose renderers are not re-exported

`app/deployment/__init__.py` re-exports `render_logrotate` and the proxy renderers but not `render_compose` or `render_compose_env`; those two must be imported from `app.deployment.compose` directly.

### Permissions are applied after the atomic rename

`_atomic_write()` replaces the target first and `os.chmod()` runs afterwards, so there is a window in which the file exists with the process umask rather than its declared mode. This matters for `docker-compose.env`, which is declared `0o600`.

### `InstallPlan.dry_run` is always `False`

`plan_installation()` never sets the field. Dry-run is expressed through `execute_installation(dry_run=True)` instead.

### The nginx `admin` rate-limit zone is declared but never applied

`render_nginx_config()` defines `limit_req_zone $binary_remote_addr zone=admin:10m rate=20r/m;` but only the `login` zone is referenced, by the two exact-match login locations. No `location /admin/` block uses `zone=admin`. The container nginx configuration in `nginx/conf.d/blog.conf` does apply the admin zone (see [Security](security.md)).

### Logrotate rendering is coupled to the logging level

`render_logrotate()` returns `None` when the logging level is `DEBUG` and the log directory does not exist, so a debug-level development install produces no logrotate policy at all.

### The generated compose file references a `.env` that this module never produces

Every service in the generated compose file sets `env_file: .env`, and the compose env header states that secrets must be set in the actual `.env` file — but `render_compose_env()` writes `docker-compose.env`, which the compose file does not reference, and no renderer or installer in `app/deployment/` writes `config.toml` or `.env`. Writing those files is onboarding's responsibility (see [Installation](installation.md)).

## See Also

- [Deployment Overview](overview.md) — The deployment documentation map
- [Installation](installation.md) — Installer/onboarding boundary, install prefixes, path resolution
- [Docker](docker.md) — The container path, which this module is not
- [CI/CD](cicd.md) — Build and release pipelines
- [Security](security.md) — Proxy rate limiting, headers, TLS, encryption
- [Filesystem Layout](../core/filesystem.md) — `RuntimePaths`, `InstallMode`, `InstallationMetadata`
- [Configuration](../core/configuration.md) — The typed config model behind `DevLogConfig`
- [App Factory](../core/app-factory.md) — Where the app factory installs its configuration, including `DEVLOG_CONFIG`
- [Operations Services](../services/operations.md) — The service layer pattern this module follows
- [Services Overview](../services/overview.md) — The service inventory
- [Scheduler Tasks](../tasks/scheduler.md) — What the scheduler unit is meant to run
- [`app/deployment/`](../../app/deployment/) — The module itself
- [`app/services/operations/deploy.py`](../../app/services/operations/deploy.py) — The service wrapper the CLI calls
