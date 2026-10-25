# Filesystem Layout

DevLog supports four deployment modes with distinct filesystem layouts. The layout system is defined in `app/filesystem/layout.py` and provides a typed `RuntimePaths` model used by all runtime consumers.

## Modes

| Mode | Description | Typical Use |
|------|-------------|-------------|
| `system` | FHS-aligned paths under `/etc`, `/var`, `/opt` | Native package install |
| `user` | XDG-compliant paths under `~/.config`, `~/.local` | Single-user install |
| `docker` | Container paths under `/data`, `/etc/devlog` | Docker deployment |
| `development` | Repository-local paths under `$PWD` | Development checkout |

## Canonical Layouts

### System-native

```
/etc/devlog/config.toml        root:devlog 0640
/etc/devlog/.env               root:devlog 0600
/var/lib/devlog/               devlog:devlog 0750
/var/lib/devlog/devlog.sqlite3 devlog:devlog 0640
/var/lib/devlog/uploads/       devlog:devlog 0750
/var/lib/devlog/themes/        devlog:devlog 0750
/var/lib/devlog/backups/       devlog:devlog 0750
/var/lib/devlog/exports/       devlog:devlog 0750
/var/log/devlog/               devlog:devlog 0750
/run/devlog/                   devlog:devlog 0700
/opt/devlog/releases/current   symlink to versioned release
```

### User-native (XDG)

```
${XDG_CONFIG_HOME:-~/.config}/devlog/config.toml
${XDG_CONFIG_HOME:-~/.config}/devlog/.env
${XDG_DATA_HOME:-~/.local/share}/devlog/devlog.sqlite3
${XDG_DATA_HOME:-~/.local/share}/devlog/uploads/
${XDG_DATA_HOME:-~/.local/share}/devlog/themes/
${XDG_DATA_HOME:-~/.local/share}/devlog/backups/
${XDG_DATA_HOME:-~/.local/share}/devlog/exports/
${XDG_STATE_HOME:-~/.local/state}/devlog/logs/
```

### Docker

Container paths (mapped via Compose volumes):

```
/etc/devlog/config.toml
/etc/devlog/.env
/data/devlog.sqlite3
/data/uploads/
/data/themes/
/data/backups/
/data/exports/
/var/log/devlog/
/run/devlog/
```

UID/GID is fixed at 1000:1000 (`blog:blog`).

### Development

```
./config.toml
./.env
./data/devlog.sqlite3
./data/uploads/
./data/themes/
./data/backups/
./data/exports/
./logs/
```

## Path Resolution

Paths are resolved via `RuntimePaths.for_mode(mode)` or `RuntimePaths.resolve(mode, ...)` with explicit overrides. Each path carries a `PathProvenance` indicating its source:

- `explicit` — CLI/config override
- `metadata` — installation metadata
- `env_var` — `DEVLOG_*` environment variable
- `system_default` — FHS system path
- `xdg_default` — XDG base directory
- `docker_default` — Docker container path
- `development_fallback` — repository-local default

## Environment Variable Overrides

`app/filesystem/layout.py` consults these variables directly when it resolves a path:

| Variable | Maps To | Example |
|----------|---------|---------|
| `DEVLOG_DATA_DIR` | `data_dir` | `/srv/data` |
| `DEVLOG_CONFIG_FILE` | `config_file` | `/etc/devlog/config.toml` |
| `DEVLOG_ENV_FILE` | `env_file` | `/etc/devlog/.env` |
| `DEVLOG_LOG_DIR` | `log_dir` | `/var/log/devlog` |
| `DEVLOG_RUNTIME_DIR` | `runtime_dir` | `/run/devlog` |

The database, uploads, themes, backups and exports directories are derived from
`data_dir` and are not individually settable through an environment variable in
`layout.py`. The typed configuration package exposes separate variables for them
(`DEVLOG_DATABASE_PATH`, `DEVLOG_UPLOADS_DIR`, `DEVLOG_THEMES_DIR`,
`DEVLOG_BACKUPS_DIR`, `DEVLOG_EXPORTS_DIR`); they populate the `[paths]` section of
the typed config, not `RuntimePaths`.

Precedence for a resolved path: explicit override > environment variable > mode
default. Installation metadata is read as an explicit override by
`RuntimePaths.from_metadata()`, so a recorded installation wins over the
environment.

## Configuration Override

Paths can also be overridden in `config.toml` under the `[paths]` section, which
accepts `data_dir`, `log_dir`, `runtime_dir`, `database_path`, `uploads_dir`,
`themes_dir`, `backups_dir` and `exports_dir`:

```toml
[paths]
data_dir = "/var/lib/devlog"
log_dir = "/var/log/devlog"
runtime_dir = "/run/devlog"
```

## CLI Commands

```bash
devlog paths status               # Show resolved paths and provenance
devlog paths status --json        # JSON output
devlog paths discover-legacy      # Find legacy repository-local state
devlog paths migrate --from-mode development --to-mode system  # Plan a migration
devlog paths check                # Verify layout integrity
```

`devlog paths migrate` only produces a plan. It accepts `--from-mode` and
`--to-mode` (each `system`, `user`, `docker` or `development`) and never moves
files; the executor in `app/filesystem/migration.py` is a service API, not a CLI
command.

## Lifecycle Categories

Paths are categorized for backup/uninstall policy (see `app/filesystem/lifecycle.py`):

| Category | Backup | Uninstall | Purge | Regenerate |
|----------|--------|-----------|-------|------------|
| Code | No | No | Yes | Yes |
| Configuration | Yes | Yes | Yes | No |
| Secrets | Yes | Yes | Yes | No |
| Persistent data | Yes | Yes | Yes | No |
| User content | Yes | Yes | Yes | No |
| Backups | No | Yes | Yes | No |
| Logs | No | No | Yes | Yes |
| Runtime | No | No | Yes | Yes |
| Installation metadata | Yes | Yes | Yes | No |

## See Also

- [Filesystem architecture](../architecture/core/filesystem.md) — the module-by-module
  reference for `app/filesystem/`
- [Migration from a repository-local layout](migration-from-checkout.md) — the
  operator workflow for moving an existing checkout
- [Typed configuration](../architecture/core/configuration.md) — how `[paths]`
  interacts with the rest of the config system

