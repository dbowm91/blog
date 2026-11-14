# Plan a Migration from a Checkout

This guide helps you find existing state and preview a path migration. The `devlog paths migrate` command is plan-only. It does not move or copy files, and there is no supported CLI command to execute the plan. Do not treat the plan as a completed migration procedure.

## What the planner finds

A development checkout may store application state beside the source code:

```text
./config.toml
./.env
./data/devlog.sqlite3
./data/uploads/
./data/themes/
./data/backups/
./data/exports/
./logs/
```

Older checkouts may also have `./instance/blog.db`, `./app/static/uploads/`, or a root-level `./blog.db`.

## 1. Discover existing state

Run discovery from the checkout or provide a search root:

```bash
devlog paths discover-legacy
devlog paths discover-legacy --search-root /path/to/checkout
```

Discovery scans the current directory and one level of subdirectories. It reports likely configuration, environment, database, upload, theme, backup, export, log, and installation-metadata paths. Review every result before using it.

## 2. Preview a plan

Specify both the current and target install modes:

```bash
devlog paths migrate --from-mode development --to-mode system
devlog paths migrate --from-mode user --to-mode docker --json
```

The modes are `system`, `user`, `docker`, and `development`. The plan lists actions for each path:

| Action | Meaning |
|---|---|
| `move` | The source is planned to move to the target |
| `copy` | The source is planned to copy to the target |
| `skip` | The source does not exist |
| `conflict` | The target already exists and needs review |
| `create_dir` | The target directory would need to be created |

The plan reports warnings and whether its proposed moves or copies would require downtime. It does not stop the service, create target paths, or apply any action.

## 3. Back up the current installation

Before any separately arranged migration, create and verify a backup:

```bash
devlog backup create
devlog backup verify /path/to/backup
```

Keep the original checkout and its data until the new installation has been independently migrated and checked.

## Important limitation

There is no operator-facing command that executes a filesystem migration. The executor exists only as an internal service and is not available through `devlog paths migrate`. This guide does not provide a manual copy procedure. For production data, do not move files based only on the planner output. Use a separately tested migration process that includes downtime and a verified backup.

The internal executor attempts a SQLite WAL checkpoint but does not check whether it succeeded. Because that executor is not an operator command, do not rely on it to safely copy a live SQLite database.

## Further reading

- [Filesystem layout](filesystem-layout.md)
- [Installation](installation.md)
- [Deployment](../DEPLOY.md)
- [Filesystem architecture](../architecture/core/filesystem.md)
