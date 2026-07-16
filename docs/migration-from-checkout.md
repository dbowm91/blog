# Migration from Repository-Local Layout

This document describes how to migrate from a development checkout layout to a production-style filesystem layout.

## Current Development Layout

When running from a git checkout, DevLog stores state alongside source code:

```
./config.toml
./.env
./instance/blog.db
./app/static/uploads/
./logs/
./backups/ (if configured)
```

This is convenient for development but unsuitable for production because upgrades may replace application files, service users need write access to source directories, and backup/restore cannot reason about a stable state root.

## Migration Workflow

Migration is a **dry-run-first** workflow. Nothing moves until you explicitly execute.

### Step 1: Discover Legacy State

```bash
devlog paths discover-legacy
devlog paths discover-legacy --json
```

This scans the current directory for DevLog state files and classifies them as:
- **managed** — expected DevLog files (database, uploads, config)
- **likely_devlog** — probably DevLog but requires verification
- **unknown** — requires operator review

### Step 2: Plan Migration

```bash
devlog paths migrate --from development --to system --dry-run
devlog paths migrate --from-root /path/to/checkout --to-mode native --dry-run
```

The plan includes:
- Source and target paths
- Copy/move strategy
- Owner/mode changes
- Config rewrites
- Database URI changes
- Conflicts with existing target files
- Required downtime
- Backup action
- Rollback plan

### Step 3: Create Backup

Before executing migration, create a backup of the source state:

```bash
# The migration plan will recommend this step
cp -a instance/ /backup/location/
```

### Step 4: Execute Migration

```bash
devlog paths migrate --from development --to system
```

The migration sequence:
1. Validate source installation and target mode
2. Create and verify a backup
3. Stop application writers (or require service stopped)
4. Record source database state and migration revision
5. Create target directories
6. Copy database, uploads, themes, and selected backups
7. Verify file counts/hashes where practical
8. Rewrite proposed config paths atomically
9. Run target config validation
10. Create target application and run database integrity/readiness checks
11. Mark target installation active
12. Preserve source with a migration marker

### Step 5: Verify

```bash
devlog paths check
devlog paths status
```

## Safety Guarantees

- **Copy before move**: Migration always copies files first. Original state remains until target verification succeeds.
- **WAL checkpoint**: Database WAL is checkpointed before copy to ensure consistency.
- **No silent fallback**: A missing expected production database is an error, not a fresh install.
- **Idempotent**: Re-running migration after success is safe (skips already-migrated files).
- **Rollback**: Source state is preserved with a migration marker until explicitly removed.

## Docker Migration

For Docker deployments, migration maps to volume configuration:

```yaml
volumes:
  - blog_data:/data
  - blog_config:/etc/devlog
  - blog_logs:/var/log/devlog
```

The Dockerfile creates the expected directory structure at build time. Named volumes inherit initial ownership from the container's `chown` commands (UID/GID 1000:1000).

## Limitations

- Migration planning is dry-run only in Release 2 Phase F. Actual file movement is deferred to a future phase.
- Multi-node/shared-filesystem operation is not supported.
- Logs are not migrated by default (old logs may remain archival).
- Transient SQLite `-wal`/`-shm` files are handled via WAL checkpoint, not direct copy.
