# Installation

Installation modes, responsibility boundaries, and path resolution for DevLog.

## Installation Modes

| Mode | Scope | Default Prefix | Description |
|------|-------|----------------|-------------|
| `native --system` | system | `/opt/devlog` | System-wide installation with root-owned paths |
| `native --user` | user | `${XDG_DATA_HOME:-~/.local/share}/devlog` | Per-user installation following XDG conventions |
| `docker` | — | `/opt/devlog` | Docker Compose bundle extraction |

The native prefix holds the versioned releases and the `current` symlink at its **root**:

```
<prefix>/releases/<version>/venv/     # Versioned release with venv
<prefix>/current -> <prefix>/releases/<version>
```

The `devlog` launcher is a symlink to `<prefix>/current/venv/bin/devlog`. It lands in
`/usr/local/bin` for a system install and in `${XDG_BIN_HOME:-~/.local}/bin` for a user
install.

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

It does **not** create a system account either. The rendered systemd units run
as the unprivileged `devlog` account, and creating that account is the
operator's responsibility:

```bash
sudo useradd --system --home-dir /var/lib/devlog --shell /usr/sbin/nologin devlog
```

`devlog doctor --check fs.service_account` reports a missing account, and the
ownership and writability checks judge the *service* account rather than
whoever runs the doctor.

### Onboarding (`devlog onboard`)

Onboarding handles all runtime configuration:

- Detects installation mode and existing state
- Collects configuration inputs (interactive or non-interactive)
- Generates `SECRET_KEY`, `HEALTH_CHECK_SECRET`, `METRICS_SECRET` (preserves existing on re-run)
- Writes `config.toml` and `.env` atomically (temp + rename, mode 0600)
- Creates runtime directories via `RuntimePaths` — the data, backup and log
  directories — and hands them to the service account when it runs as root
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
- **`DEVLOG_*` env vars** — `DEVLOG_DATA_DIR`, `DEVLOG_CONFIG_FILE`, `DEVLOG_ENV_FILE`, `DEVLOG_LOG_DIR`, `DEVLOG_RUNTIME_DIR`, `DEVLOG_RELEASE_DIR`
- **CLI overrides** — `--config <path>` and `--env-file <path>`, on the root group and on
  `devlog config check` and `devlog config migrate`. There is no `--data-dir` or
  `--config-file` option; use `DEVLOG_DATA_DIR` for the data directory.

Explicit overrides always win over env vars and mode defaults. See `devlog paths status` to inspect resolved paths and their provenance.

## Legacy Layout Migration

The filesystem subsystem supports discovering and migrating from legacy layouts:

- `app/filesystem/discovery.py` — Read-only discovery of legacy path conventions
- `app/filesystem/migration.py` — Migration planner (`plan_migration()`, dry-run by
  default) and executor (`execute_migration()`, which performs the move/copy steps and a
  SQLite WAL checkpoint on the source database). The executor is a service API; the CLI
  only ever plans.
- `app/filesystem/verification.py` — Post-migration verification checks

CLI commands: `devlog paths discover-legacy`, `devlog paths migrate`, `devlog paths check`

## Release Artifact Verification

Release artifacts are verified via SHA-256 checksums:

- `scripts/generate_checksums.py` — Generates `checksums.txt` for a directory of artifacts
- `scripts/check_release_artifacts.py` — Verifies wheel contents and checksums
- `scripts/install.sh` — Downloads and verifies checksums before installation

The checksum manifest (`checksums.txt`) is published alongside the release artifacts on
GitHub Releases. Verification is mandatory — the installer aborts if a checksum mismatches.

The manifest covers **every** published artefact, while a given install downloads only
some of them. The installer therefore skips (with a warning) the manifest entries for
artefacts it did not fetch; a mismatch on an artefact that was downloaded still aborts the
install. Verification is skipped entirely only when `checksums.txt` itself is missing from
the release.

### Published Artifacts

The release workflow (`.github/workflows/release.yml`) builds and publishes:

| Artifact | Contents |
|----------|----------|
| `devlog-<version>-py3-none-any.whl` | The Python package, with pre-built frontend assets |
| `devlog-<version>.tar.gz` | The sdist |
| `docker-bundle-<version>.tar.gz` | `docker-compose.yml`, `Dockerfile`, `.env.example` and `nginx/` |
| `checksums.txt` | SHA-256 manifest covering all of the above |

`checksums.txt` is generated in the `build` job, alongside the Docker bundle. The
installer extracts the Docker bundle with `tar --strip-components=1`, because the archive
wraps its contents in a top-level `docker-bundle/` directory.

## See Also

- [Docker](docker.md) — Container deployment details
- [Security](security.md) — Security configuration
- [CI/CD](cicd.md) — Build and release pipelines
- [app/filesystem/layout.py](../../app/filesystem/layout.py) — `RuntimePaths` implementation
