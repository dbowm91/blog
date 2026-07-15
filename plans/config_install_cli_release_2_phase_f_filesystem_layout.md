# Release 2 Phase F — Production Filesystem Layout and State Migration

## Objective

Separate DevLog application code from mutable runtime state and establish predictable, standards-aligned filesystem layouts for system-native, user-native, Docker, and development modes.

This phase must provide one path abstraction used by configuration, onboarding, installer, backups, service deployment, and runtime code. It must also define a safe migration path from the current repository-local layout without silently moving or deleting user data.

## Dependencies

- Release 1 typed path/configuration infrastructure
- Release 1 closure package boundary
- Release 2 onboarding planner and installation metadata
- Release 2 native/Docker installation modes

Phase F may be implemented in parallel with parts of Phase E, but installer activation and onboarding completion must not be finalized until the production layout contract is stable.

## Current problem

The development-oriented layout stores mutable state near source code, including combinations of:

```text
instance/
logs/
app/static/uploads/
config.toml
.env
local database files
external themes
backups
```

This is convenient for a checkout but unsuitable as the long-term production contract because:

- upgrades may replace application files
- service users may need write access to source directories
- backups and restores cannot reason about a stable state root
- native and Docker deployments diverge
- uninstall risks confusing code and data
- permissions and ownership are difficult to harden
- multiple installs can collide

## Non-goals

- Do not implement systemd or reverse-proxy installation.
- Do not implement full update/uninstall policy, though layout must support them.
- Do not automatically migrate production state on ordinary startup.
- Do not force development checkouts to use system paths.
- Do not support multi-node/shared-filesystem operation beyond documenting limitations.

## Canonical layouts

### System-native

```text
/etc/devlog/config.toml
/etc/devlog/devlog.env
/var/lib/devlog/devlog.sqlite3
/var/lib/devlog/uploads/
/var/lib/devlog/themes/
/var/lib/devlog/backups/
/var/lib/devlog/exports/
/var/log/devlog/
/run/devlog/
/opt/devlog/releases/<version>/
/opt/devlog/current
/usr/local/bin/devlog
```

Recommended ownership:

```text
/etc/devlog/config.toml    root:devlog 0640
/etc/devlog/devlog.env     root:devlog 0640 or 0600 where service access permits
/var/lib/devlog            devlog:devlog 0750
/var/log/devlog            devlog:devlog 0750
/run/devlog                devlog:devlog runtime-created
/opt/devlog/releases       root:root read-only to service
```

Exact secret-file ownership should be compatible with the service manager while remaining minimally readable.

### User-native

Use XDG paths:

```text
${XDG_CONFIG_HOME:-~/.config}/devlog/config.toml
${XDG_CONFIG_HOME:-~/.config}/devlog/devlog.env
${XDG_DATA_HOME:-~/.local/share}/devlog/devlog.sqlite3
${XDG_DATA_HOME:-~/.local/share}/devlog/uploads/
${XDG_DATA_HOME:-~/.local/share}/devlog/themes/
${XDG_STATE_HOME:-~/.local/state}/devlog/logs/
${XDG_STATE_HOME:-~/.local/state}/devlog/backups/
${XDG_RUNTIME_DIR}/devlog/ where available
```

Provide a fallback for systems without `XDG_RUNTIME_DIR`, but do not place security-sensitive runtime files in world-writable locations without safe directory creation.

### Docker

Host-side installation root:

```text
<install-root>/compose.yaml
<install-root>/config/config.toml
<install-root>/config/devlog.env
<install-root>/data/devlog.sqlite3
<install-root>/uploads/
<install-root>/themes/
<install-root>/backups/
<install-root>/logs/ or container logging backend
<install-root>/.devlog-installation.json
```

Container paths should be fixed and mapped consistently, for example:

```text
/etc/devlog/config.toml
/etc/devlog/devlog.env
/var/lib/devlog/
/var/log/devlog/
```

Do not encode host absolute paths into application configuration when Compose volume mapping can provide stable container paths.

### Development

Retain repository-local convenience:

```text
./config.toml
./.env
./instance/
./app/static/uploads/
./logs/
```

Development mode must be explicit and must not be selected merely because the current directory contains a config file when an installed system instance is being managed.

## Workstream F1 — central path model

Extend the existing path layer with a typed `RuntimePaths` or equivalent model containing:

- install mode
- config file
- environment/secret file
- data root
- database path
- uploads root
- themes root
- backups root
- exports root
- logs root
- runtime root
- installation metadata path
- release/current paths where relevant

Every field should carry provenance:

- explicit CLI/config override
- installation metadata
- system default
- XDG default
- Docker mapping
- development fallback

Runtime code must consume this model rather than constructing paths independently.

## Workstream F2 — mode detection and ambiguity prevention

Path selection order should combine explicit options and installation metadata.

Recommended rules:

1. Explicit `--config`, `--env-file`, `--data-dir`, or installation root wins where supported.
2. Existing installation metadata defines mode and managed roots.
3. Explicit `DEVLOG_*` path variables override defaults.
4. System/user defaults apply according to selected mode.
5. Repository-local paths are only fallback for explicit development mode or legacy compatibility.

If both a system install and local checkout config are visible, commands should manage the explicitly selected/system installation rather than silently switching based on current directory.

Add clear ambiguity errors and `devlog config paths --verbose` diagnostics.

## Workstream F3 — configuration fields and overrides

Add canonical path fields or derive them from a root with targeted overrides.

Avoid requiring users to configure every directory individually. A practical model is:

```toml
[paths]
data_dir = "/var/lib/devlog"
log_dir = "/var/log/devlog"
runtime_dir = "/run/devlog"
```

with derived defaults:

```text
database = data_dir/devlog.sqlite3
uploads = data_dir/uploads
themes = data_dir/themes
backups = data_dir/backups
exports = data_dir/exports
```

Permit explicit overrides only where use cases justify them.

Environment equivalents should be consistently named, such as:

```text
DEVLOG_DATA_DIR
DEVLOG_LOG_DIR
DEVLOG_RUNTIME_DIR
DEVLOG_DATABASE_PATH
DEVLOG_UPLOADS_DIR
DEVLOG_THEMES_DIR
DEVLOG_BACKUPS_DIR
```

Document precedence and avoid retaining multiple historical names indefinitely.

## Workstream F4 — runtime consumer audit

Search the entire repository for direct path construction and classify/migrate:

- SQLite database URI defaults
- upload storage
- media cleanup
- theme external directory
- backup creation/restore
- export/import
- logs
- PID/socket/runtime files
- health checks
- migrations
- tests
- Docker mounts
- scripts

Add a test or lint-like check preventing new hard-coded repository-local production paths.

Critical invariant:

```text
no production service requires write access to package/source directories
```

## Workstream F5 — directory creation and permissions

Create a reusable directory preparation service used by onboarding and deployment.

For each directory specify:

- expected owner/group
- mode
- whether created during onboarding or runtime
- whether it may contain secrets
- whether symlinks are allowed
- free-space expectations
- backup inclusion policy

Security requirements:

- reject path traversal outside managed roots where a relative path is expected
- do not follow unsafe symlinks during creation/migration
- use restrictive umask
- avoid world-writable state
- check parent ownership
- report inability to enforce ownership when running unprivileged

## Workstream F6 — legacy layout discovery

Implement a read-only discovery command:

```bash
devlog paths discover-legacy
devlog paths discover-legacy --json
```

Discover likely state from:

- current repository-local `instance/`
- local database files
- uploads directory
- logs
- external themes
- backups
- `.env`
- `config.toml`

The report must distinguish:

- confirmed managed files
- likely DevLog files
- unknown files requiring operator review
- conflicts with target paths

Do not move anything during discovery.

## Workstream F7 — migration planner

Provide an explicit migration command, potentially:

```bash
devlog paths migrate --from legacy --to system --dry-run
devlog paths migrate --from-root /opt/blog --to-mode native
```

Migration plan should include:

- source and target
- copy/move strategy
- owner/mode changes
- config rewrites
- database URI changes
- volume mapping changes where relevant
- conflicts
- required downtime
- backup action
- rollback plan

Always default to copy-and-verify rather than destructive move. Original state should remain until target startup and verification succeed.

## Workstream F8 — safe state migration

Suggested migration sequence:

1. Validate source installation and target mode.
2. Create and verify a backup.
3. Stop/quiesce application writers or require service stopped.
4. Record source database state and migration revision.
5. Create target directories.
6. Copy database, uploads, themes, and selected backups.
7. Verify file counts/hashes where practical.
8. Rewrite proposed config paths atomically.
9. Run target config validation.
10. Create target application and run database integrity/readiness checks.
11. Mark target installation active.
12. Preserve source with a migration marker.

Do not migrate logs by default unless requested; old logs may remain archival.

Do not copy transient SQLite `-wal`/`-shm` files without a deliberate consistent snapshot strategy. Ensure WAL is checkpointed or use backup APIs.

## Workstream F9 — database path handling

Make SQLite path behavior explicit.

Requirements:

- canonical absolute database path after resolution
- create parent directory before migration
- preserve WAL configuration
- use SQLite backup/checkpoint semantics during migration
- no silent fallback to a new empty database when expected database is missing or inaccessible
- health/status output reports resolved database path safely
- non-SQLite URLs remain supported only according to documented experimental scope

A missing expected production database must be an error, not an implicit fresh install, unless onboarding metadata says initialization is incomplete.

## Workstream F10 — Docker volume and ownership behavior

Define container UID/GID strategy.

Options:

- fixed non-root UID/GID documented and applied to host directories
- entrypoint ownership adjustment with bounded behavior
- Compose user mapping

Avoid recursively chowning large upload trees on every startup.

Add volume migration tests and ensure Docker onboarding creates host directories with compatible permissions.

## Workstream F11 — path diagnostics

Enhance:

```bash
devlog config paths
```

or add:

```bash
devlog paths status
```

Report:

- selected mode
- each resolved path
- provenance
- existence
- owner/group/mode
- read/write/execute access
- symlink status
- filesystem/free space
- whether path is inside a release/source directory
- migration requirement

JSON must use stable fields and avoid exposing secret-file contents.

## Workstream F12 — backup and uninstall integration contracts

Define path categories for later lifecycle work:

```text
code
configuration
secrets
persistent data
user content
backups
logs
runtime/transient
installation metadata
```

For each category specify:

- included in backup
- preserved on uninstall
- removed on purge
- safe to regenerate
- ownership expectations

This phase need not implement uninstall, but the layout contract must make default data preservation unambiguous.

## Expected files

```text
app/config/paths.py
app/config/model.py
app/filesystem/layout.py
app/filesystem/prepare.py
app/filesystem/discovery.py
app/filesystem/migration.py
app/filesystem/verification.py
devlog_cli/commands/paths.py
devlog_cli/commands/config.py
app/storage/*
app/services/operations/backup.py
app/services/operations/media.py
Dockerfile
compose templates
tests/filesystem/*
tests/cli/test_paths_commands.py
docs/filesystem-layout.md
docs/migration-from-checkout.md
```

## Testing plan

### Unit tests

- system/user/Docker/development resolution
- XDG fallbacks
- explicit overrides
- provenance
- ambiguity detection
- derived subpaths
- permission validation
- unsafe symlink rejection
- legacy discovery classification
- migration planning

### Integration tests

- fresh system-like root under temporary directory
- fresh user/XDG root
- Docker host/container path mapping
- development checkout compatibility
- application creation using each layout
- uploads/themes/backups through resolved paths

### Migration tests

- legacy SQLite database plus uploads to system layout
- WAL database migration
- target conflict
- insufficient permissions
- interrupted copy
- verification failure
- rollback to source
- re-run after successful migration

### Security tests

- symlink escape
- world-writable parent
- relative traversal
- secret file permissions
- package directory accidentally selected as writable data root

## Acceptance criteria

Phase F and Release 2 are complete when:

1. Native system, native user, Docker, and development layouts are explicit and documented.
2. All production runtime consumers use one typed path model.
3. Production service operation requires no write access to application code/release directories.
4. `devlog config paths` or `devlog paths status` explains every resolved path and provenance.
5. Onboarding and installer use the same layout definitions.
6. Legacy repository-local state can be discovered and migrated through an explicit dry-run-first workflow.
7. Migration preserves source state until target verification succeeds.
8. SQLite migration handles WAL safely and never silently creates an unintended empty database.
9. Docker volumes and ownership behavior are deterministic.
10. Backup/uninstall categories are defined for later lifecycle phases.
11. End-to-end tests prove a clean installed artifact can onboard and run outside the source checkout using production-style state paths.

## Handoff sequencing

Implement in this order:

1. canonical typed path model
2. runtime consumer audit and migration
3. directory preparation/permissions
4. diagnostics
5. Docker mapping and ownership
6. legacy discovery
7. migration planning and execution
8. end-to-end layout tests
9. documentation and Release 2 closure verification

Release 2 should not be declared complete until onboarding, installer, and filesystem work are tested together from a clean artifact on both native and Docker paths.
