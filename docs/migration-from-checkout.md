# Migration from Repository-Local Layout

This document describes how to migrate from a development checkout layout to a
production-style filesystem layout.

## Current Development Layout

When running from a git checkout, DevLog stores state alongside source code:

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

Legacy checkouts may also carry `./instance/blog.db`, `./app/static/uploads/` or a
root-level `./blog.db`; `devlog paths discover-legacy` finds those too.

This is convenient for development but unsuitable for production because upgrades
may replace application files, service users need write access to source
directories, and backup/restore cannot reason about a stable state root.

## Migration Workflow

Migration is a **plan-first** workflow. Nothing moves until the plan is executed.

### Step 1: Discover Legacy State

```bash
devlog paths discover-legacy
devlog paths discover-legacy --json
```

`discover_legacy_layout()` scans the current directory (and one level of
subdirectories) for:

- Database files matching `*.sqlite3`, `*.db` or `*.sqlite`
- Upload directories named `uploads`, `media`, `files` or `images`
- Backup directories named `backups` or `backup`
- Theme directories named `themes` or `theme`
- Log directories named `logs` or `log`
- Config files named `config.toml`, `config.yaml`, `config.json` or `config.ini`
- Env files named `.env`, `.env.local` or `.env.production`
- Installation metadata named `.devlog-installation.json` or
  `devlog-installation.json`

`classify_discovery()` labels each result:

- **managed** — the path is the target path for the selected mode
- **likely_devlog** — a DevLog-shaped path that is not the target
- **unknown** — requires operator review

### Step 2: Plan Migration

```bash
devlog paths migrate --from-mode development --to-mode system
devlog paths migrate --from-mode user --to-mode docker --json
```

Both `--from-mode` and `--to-mode` are required and accept `system`, `user`,
`docker` or `development`.

`plan_migration()` returns a `MigrationPlan` with a list of `MigrationStep`
entries. Each step has an action, an optional source, a target and a description:

| Action | Meaning |
|--------|---------|
| `move` | The source is transferred to the target |
| `copy` | The source is copied to the target |
| `skip` | The source does not exist |
| `conflict` | The target already exists and needs manual resolution |
| `create_dir` | A directory in the target tree must be created |

The plan covers the config file, the env file, the database, the uploads,
themes, backups and exports directories, and the installation metadata. Logs are
only included when `include_logs=True` is passed to `plan_migration()`; the CLI
does not set it.

The plan also reports:

- `warnings` — for example, identical source and target data directories, or
  existing target paths that need manual resolution
- `requires_downtime` — true when any step moves or copies a file

### Step 3: Create Backup

Before executing a migration, back up the source state:

```bash
devlog backup create
```

### Step 4: Execute Migration

`devlog paths migrate` produces a plan; it does not move files. The executor is
the service function `execute_migration(plan, dry_run=False,
stop_on_conflict=True)` in `app/filesystem/migration.py`. It:

1. Locates the source database among the plan's steps
2. Runs `PRAGMA wal_checkpoint(TRUNCATE)` on that database, so the copy is
   consistent
3. Walks the steps in order, creating directories, moving or copying files, and
   skipping sources that do not exist
4. Stops at the first error, or at the first conflict when
   `stop_on_conflict=True`

It returns a `MigrationExecutionResult` with `ok`, `completed_steps`,
`total_steps`, `errors` and `completed_paths`.

### Step 5: Verify

```bash
devlog paths check
devlog paths status
```

## Safety Guarantees

- **WAL checkpoint**: The source database is checkpointed before it is copied, so
  the migrated file is consistent.
- **Conflicts are reported, not silently overwritten**: A target path that already
  exists is planned as `conflict` and stops execution by default.
- **Idempotent**: A source that does not exist is planned as `skip`.
- **The plan is free**: `plan_migration()` only reads the filesystem.

## Docker Migration

For Docker deployments, migration maps to volume configuration:

```yaml
volumes:
  - blog_data:/data
  - blog_config:/etc/devlog
  - blog_logs:/var/log/devlog
```

The Dockerfile creates the expected directory structure at build time. Named
volumes inherit initial ownership from the container's `chown` commands
(UID/GID 1000:1000).

## Limitations

- `devlog paths migrate` is plan-only. There is no CLI command that executes a
  migration.
- Multi-node/shared-filesystem operation is not supported.
- Logs are not migrated by the CLI.
- Transient SQLite `-wal`/`-shm` files are handled via the WAL checkpoint, not by
  direct copy.

## See Also

- [Filesystem layout](filesystem-layout.md) — the four install modes and their paths
- [Filesystem architecture](../architecture/core/filesystem.md) — the module reference
  for `app/filesystem/`
- [Installation](installation.md) — installing into a production layout
