# Installation

Installation modes, responsibility boundaries, and path resolution for DevLog.

## Installation Modes

| Mode | Scope | Default Prefix | Description |
|------|-------|----------------|-------------|
| `native --system` | system | `/opt/devlog` | System-wide installation with root-owned paths |
| `native --user` | user | `~/.local` | Per-user installation following XDG conventions |
| `docker` | — | `/opt/devlog` | Docker Compose bundle extraction |

## Responsibility Boundary

### Installer (`scripts/install.sh`)

The installer is responsible for **code artifacts only**:

- Downloads release wheel (or Docker bundle) from GitHub Releases
- Verifies SHA-256 checksums against `checksums.txt`
- Creates virtualenv and installs wheel (native mode)
- Extracts Docker bundle (Docker mode)
- Creates versioned release directory with atomic symlink (`current -> X.Y.Z`)
- Creates `devlog` launcher in `bin/` directory
- Optionally invokes `devlog onboard` if TTY available

The installer does **not** create configuration, database, admin users, or runtime directories. These are delegated to onboarding.

### Onboarding (`devlog onboard`)

Onboarding handles all runtime configuration:

- Detects installation mode and existing state
- Collects configuration inputs (interactive or non-interactive)
- Generates `SECRET_KEY`, `HEALTH_CHECK_SECRET`, `METRICS_SECRET` (preserves existing on re-run)
- Writes `config.toml` and `.env` atomically (temp + rename, mode 0600)
- Creates runtime directories via `RuntimePaths`
- Runs database migrations (`flask db upgrade`)
- Creates initial admin user
- Writes `onboarding-metadata.json` in the data directory
- Verifies Vite build assets

Onboarding is re-runnable, but not idempotent in the strict sense: `config.toml` and the
env file are rewritten on every run. The env file is regenerated from a fixed key set
(`SECRET_KEY`, `ADMIN_PASSWORD` and the optional secret keys), so any unrelated key that
was hand-added to `.env` is dropped by a re-run.

## Path Resolution

`RuntimePaths` in `app/filesystem/layout.py` is the **sole authority** for all runtime paths. Paths are resolved per-mode with a precedence chain:

1. Explicit override (highest priority)
2. Environment variable (`DEVLOG_*`)
3. Mode default (lowest priority)

Each resolved path carries `PathProvenance` metadata indicating its source.

### Default Paths by Mode

| Path | System | User (XDG) | Docker | Development |
|------|--------|-------------|--------|-------------|
| Config | `/etc/devlog/config.toml` | `$XDG_CONFIG_HOME/devlog/config.toml` | `/etc/devlog/config.toml` | `./config.toml` |
| Env | `/etc/devlog/.env` | `$XDG_CONFIG_HOME/devlog/.env` | `/etc/devlog/.env` | `./.env` |
| Data | `/var/lib/devlog` | `$XDG_DATA_HOME/devlog` | `/data` | `./data` |
| Database | `/var/lib/devlog/devlog.sqlite3` | `$XDG_DATA_HOME/devlog/devlog.sqlite3` | `/data/devlog.sqlite3` | `./data/devlog.sqlite3` |
| Logs | `/var/log/devlog` | `$XDG_STATE_HOME/devlog/logs` | `/var/log/devlog` | `./logs` |
| Runtime | `/run/devlog` | `$XDG_RUNTIME_DIR/devlog` (or state fallback) | `/run/devlog` | `./instance` |

### Override Mechanisms

- **config.toml** `[paths]` section — explicit path overrides per deployment
- **`DEVLOG_*` env vars** — `DEVLOG_DATA_DIR`, `DEVLOG_CONFIG_FILE`, `DEVLOG_ENV_FILE`, `DEVLOG_LOG_DIR`, `DEVLOG_RUNTIME_DIR`
- **CLI overrides** — `--data-dir`, `--config-file`, etc. on applicable commands

Explicit overrides always win over env vars and mode defaults. See `devlog paths status` to inspect resolved paths and their provenance.

## Legacy Layout Migration

The filesystem subsystem supports discovering and migrating from legacy layouts:

- `app/filesystem/discovery.py` — Read-only discovery of legacy path conventions
- `app/filesystem/migration.py` — Dry-run migration planner (no mutations in this phase)
- `app/filesystem/verification.py` — Post-migration verification checks

CLI commands: `devlog paths discover-legacy`, `devlog paths migrate`, `devlog paths check`

## Release Artifact Verification

Release artifacts are verified via SHA-256 checksums:

- `scripts/generate_checksums.py` — Generates `checksums.txt` for a directory of artifacts
- `scripts/check_release_artifacts.py` — Verifies wheel contents and checksums
- `scripts/install.sh` — Downloads and verifies checksums before installation

The checksum manifest (`checksums.txt`) is published alongside release artifacts on GitHub Releases. Verification is mandatory — the installer aborts if checksums mismatch.

## See Also

- [Docker](docker.md) — Container deployment details
- [Security](security.md) — Security configuration
- [CI/CD](cicd.md) — Build and release pipelines
- [app/filesystem/layout.py](../../app/filesystem/layout.py) — `RuntimePaths` implementation
