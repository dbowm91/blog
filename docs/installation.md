# Installation

Complete installation guide for DevLog blog CMS.

## Quick Install (Recommended)

Install DevLog from a release with one command:

```bash
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --native
```

This downloads the latest verified release, installs it to `/opt/devlog/`, and creates a `devlog` launcher at `/usr/local/bin/devlog`. Then run onboarding:

```bash
sudo devlog onboard run --mode native --scope system --profile native-production
```

A system install needs root — onboarding writes `/etc/devlog/config.toml` and
`/var/lib/devlog`. A `--user` install writes into your own home directory and
needs neither root nor `--scope system`.

`--scope` matters: without it, onboarding falls back to the development layout
and writes `config.toml` and `data/` into the current working directory instead
of the install prefix. Use `--scope user` for a user-scope install.

### Service account (system installs only)

The systemd units run as an unprivileged `devlog` account. Nothing creates
that account for you, so create it **before** onboarding — onboarding then
hands the data and log directories to it:

```bash
sudo useradd --system --home-dir /var/lib/devlog --shell /usr/sbin/nologin devlog
```

Onboarding creates `/var/lib/devlog`, `/var/lib/devlog/backups` and
`/var/log/devlog` and gives them to the service account when it runs as root.
`/run/devlog` is created by systemd itself at every start
(`RuntimeDirectory=devlog`). If the account is missing, onboarding warns and
the service cannot start — `devlog doctor --check fs.service_account` reports
it.

### Install Options

```bash
# Install to user paths (~/.local/share/devlog)
curl -fsSL ... | bash -s -- --native --user

# Install a specific version
curl -fsSL ... | bash -s -- --native --version 1.2.0

# Install and run onboarding immediately (requires TTY)
curl -fsSL ... | bash -s -- --native --onboard

# Docker mode (no host Python required)
curl -fsSL ... | bash -s -- --docker
```

See `scripts/install.sh --help` for all options.

### Installation Layout

Native system install:

```
/opt/devlog/releases/X.Y.Z/venv/    # Versioned release with venv
/opt/devlog/current -> /opt/devlog/releases/X.Y.Z  # Symlink to active release
/usr/local/bin/devlog -> /opt/devlog/current/venv/bin/devlog  # Launcher
```

User install (`--user`):

```
~/.local/share/devlog/releases/X.Y.Z/venv/
~/.local/share/devlog/current -> ~/.local/share/devlog/releases/X.Y.Z
~/.local/bin/devlog -> ~/.local/share/devlog/current/venv/bin/devlog
```

The user-scope prefix is `${XDG_DATA_HOME:-~/.local/share}/devlog` and the launcher is
`${XDG_BIN_HOME:-~/.local}/bin/devlog`. In both scopes the `current` symlink sits at the
**prefix root**, not inside `releases/`.

### Supply Chain Safety

The installer verifies SHA-256 checksums before installation. Artifacts are downloaded over HTTPS from GitHub Releases. See `scripts/check_release_artifacts.py` for artifact verification.

The release publishes a wheel, an sdist and a Docker bundle (`docker-bundle-<version>.tar.gz`,
containing `docker-compose.yml`, `Dockerfile`, `.env.example` and `nginx/`). `checksums.txt`
covers every published artefact, so the installer skips the manifest entries it did not
download for this run — a mismatch on an artefact that *was* fetched still aborts the
install. Verification is skipped entirely only when `checksums.txt` itself is absent from
the release.

## Prerequisites

- Python 3.12+
- Node.js 20 (for local development; Docker builds handle this automatically)
- SQLite (bundled with Python)
- Git

## Docker Production

### Via Installer

```bash
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --docker
cd /opt/devlog
devlog onboard run --mode docker
docker compose --profile production up -d
```

### Via Git Clone

```bash
git clone https://github.com/dbowm91/blog.git /opt/blog
cd /opt/blog
cp .env.example .env
# Edit .env: set SECRET_KEY and ADMIN_PASSWORD
docker compose --profile production up -d --build
```

Docker builds frontend assets (Vite) automatically inside the container. No local Node.js installation required.

The app binds to `127.0.0.1:5000` (localhost only). For public access, terminate TLS with a host-level reverse proxy (Caddy, nginx, Traefik) and proxy to `http://127.0.0.1:5000`.

> **Local HTTP testing:** Set `SESSION_COOKIE_SECURE=false` in your `.env` when testing at `http://localhost:5000`, otherwise admin login cookies will not persist. The app refuses to start with that setting unless debug mode is on, so run the local server with `DEBUG=true` as well — it enables the Werkzeug debugger, so keep it bound to `127.0.0.1`. Never use `SESSION_COOKIE_SECURE=false` in production behind HTTPS.

### Docker Compose Profiles

All services require explicit profiles:

| Profile | Services | Port |
|---------|----------|------|
| `production` | blog, celery, redis | `127.0.0.1:5000` |
| `reverse-proxy` | nginx | 80/443 |
| `backup` | backup service | — |

```bash
docker compose --profile production up -d
docker compose --profile production --profile reverse-proxy up -d
```

## Local Development

```bash
git clone https://github.com/dbowm91/blog.git /opt/blog
cd /opt/blog
./scripts/setup-dev.sh
venv/bin/python run.py
```

This creates a virtual environment, generates secure credentials, and loads the `.env` file.

## CLI Installation

DevLog provides a standalone `devlog` CLI for operator tasks. The installer creates a launcher automatically. For manual installation:

```bash
pip install .
devlog --help
devlog --version
```

For development (editable install with dev dependencies):

```bash
pip install -e '.[dev]'
```

Global options:

```bash
devlog --json version       # JSON output
devlog --verbose config --help  # Verbose help
devlog --quiet db status    # Minimal output
```

Command groups: `config`, `admin`, `db`, `data`, `media`, `themes`, `backup`,
`onboard`, `paths`, `deploy`.

Top-level commands: `version`, `doctor`, `start`, `stop`, `restart`, `status`,
`logs`.

See [the CLI reference](../architecture/deployment/cli.md) for every command and
option.

## Onboarding System

The `devlog onboard` command provides first-run and reconfiguration onboarding:

### Interactive Onboarding

```bash
devlog onboard run
```

This guides you through:
1. Mode selection (native or Docker)
2. Deployment profile (development, native-production, docker-production, minimal, full)
3. Site configuration (title, description, base URL)
4. Admin user creation
5. Newsletter and scheduler settings
6. Redis and storage configuration
7. Theme selection

### Non-Interactive Onboarding

For automated deployments (CI, Docker, scripts):

```bash
devlog onboard run \
  --non-interactive \
  --mode native \
  --profile native-production \
  --admin-password-file /path/to/password.txt \
  --site-url https://blog.example.com \
  --admin-username admin
```

Password must be provided via `--admin-password-file` in non-interactive mode. Never pass passwords as CLI arguments.

### Dry Run

Preview what onboarding would do without making changes:

```bash
devlog onboard run --dry-run
devlog onboard run --dry-run --json
```

### Plan

Show the onboarding plan without applying:

```bash
devlog onboard plan --mode native --profile development
devlog onboard plan --mode docker --profile docker-production --json
```

### Detect Installation State

Check if an installation already exists:

```bash
devlog onboard detect
devlog --json onboard detect
```

### Resume Interrupted Onboarding

If onboarding was interrupted (e.g., power failure, Ctrl+C), resume from where it left off:

```bash
devlog onboard resume
devlog onboard resume --data-path /path/to/data
```

The resume command reads metadata from the data directory to determine the last completed step and continues from there.

### What Onboarding Writes

Onboarding is not additive. Two behaviours matter when re-running it against an
existing installation:

- **The `.env` file is rewritten from a fixed key set.** `write_env_file()` emits
  `SECRET_KEY`, `ADMIN_PASSWORD`, `HEALTH_CHECK_SECRET`, `METRICS_SECRET` and,
  when applicable, `SMTP_PASSWORD`, `BACKUP_ENCRYPTION_KEY`, `S3_ACCESS_KEY` and
  `S3_SECRET_KEY`. A key you added by hand is not in that set and is dropped on the
  next run. Keep extra settings in `config.toml`, or re-add them afterwards.
- **Progress is recorded in `onboarding-metadata.json`** in the data directory. This
  is a different file from the `.devlog-installation.json` that the filesystem
  layout uses to describe an installed instance.

## Configuration

### Typed Configuration System

DevLog uses a typed configuration system at `app/config/` with 24 frozen dataclasses
(`DevLogConfig` plus 23 section classes):

```bash
devlog config check                    # Validate configuration
devlog config show --effective         # Show resolved values with sources
devlog config explain email.smtp_host  # Explain one field (section.field)
devlog config paths                    # Show config file locations
devlog config init                     # Generate config.toml from defaults
devlog config migrate                  # Migrate config to latest version
```

### Configuration Precedence

1. Environment variables (highest priority)
2. `config.toml`
3. Defaults (lowest priority)

Secret fields never carry their value in `config.toml`. Section-level secrets
(`smtp_password`, `smtp_user`, the check secrets, the encryption keys, the S3 keys) are
written as empty strings, and the top-level `secret_key` and `admin_password` are left out
of the file entirely. They must be supplied by the environment or the env file.

### Environment Variables

Key environment variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `SECRET_KEY` | Flask session signing | — (required) |
| `ADMIN_PASSWORD` | Admin user password | — (required) |
| `DATABASE_URL` | Database URI | `sqlite:///<cwd>/data/devlog.sqlite3` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `SERVER_PORT` | HTTP listen port | `5000` |
| `SESSION_COOKIE_SECURE` | Secure cookies | `true` |
| `ENABLE_SCHEDULER` | APScheduler jobs | `false` |
| `ENABLE_METRICS` | Metrics endpoint | `false` |

`DATABASE_URL` is only the fallback: `SQLALCHEMY_DATABASE_URI` takes precedence over
it, and `DEVLOG_DATABASE_PATH` selects a SQLite file directly. `DEVLOG_DATABASE_PATH`
outranks `DEVLOG_DATA_DIR`, but not `SQLALCHEMY_DATABASE_URI` or `DATABASE_URL`.

### config.toml

The `config.toml` file provides typed configuration:

```toml
version = 1

[app]
title = "My Blog"
description = "A place for thoughts on code"

[site]
base_url = "https://blog.example.com"

[server]
host = "127.0.0.1"
port = 5000

[email]
smtp_host = "smtp.example.com"
smtp_port = 587
```

See `config.toml.example` for all available options.

## Database

### Migrations

```bash
flask db upgrade          # Apply pending migrations
flask db downgrade       # Rollback last migration
flask db history         # Show migration history
flask db current         # Show current revision
```

Or via CLI:

```bash
devlog db status         # Migration status
devlog db check          # Database integrity check
devlog db migrate        # Run pending migrations
devlog db rebuild-search # Rebuild FTS5 search index
```

### Backup and Restore

```bash
devlog backup create           # Create backup
devlog backup verify BACKUP   # Verify backup integrity
devlog backup inspect BACKUP  # Show backup details
```

Encrypted backups require `BACKUP_ENCRYPTION_KEY` in `.env`.

## Frontend Build

Production releases include pre-built frontend assets in the wheel. Native production installation does not require Node.js.

For local development, build frontend assets:

```bash
npm install
npm run dev        # Development with hot reload
npm run build      # Production build
```

Docker builds handle this automatically via the multi-stage `Dockerfile`.

## Themes

DevLog ships with 50 Halloy-compatible themes:

```bash
devlog themes list                          # List available themes
devlog themes validate "Catppuccin Mocha"   # Validate a theme file or name
devlog themes inspect "Catppuccin Mocha"    # Show theme details
```

Themes are selected in the admin dashboard at `/admin/settings`.

## Troubleshooting

### Admin Login Cookies Not Persisting

Set `SESSION_COOKIE_SECURE=false` in `.env` when testing at `http://localhost:5000`. The server also needs `DEBUG=true` to start with that setting — without it, startup fails with `RuntimeError: SESSION_COOKIE_SECURE must be True in production`.

### Search Not Working

FTS5 initialization fails silently. Check database integrity:

```bash
devlog db check
```

### Scheduler Not Running

Set `ENABLE_SCHEDULER=true` in `.env`. Only one container should run the scheduler:

```bash
docker compose --profile production up -d  # Set ENABLE_SCHEDULER=true on one container only
```

### Port Already in Use

Change the port in `config.toml` under `[server]`, or via the `SERVER_PORT`
environment variable:

```bash
SERVER_PORT=8080 python run.py
```

## See Also

- [Filesystem layout](filesystem-layout.md) — where each mode keeps its state
- [Migration from a repository-local layout](migration-from-checkout.md) — moving a
  checkout to a production layout
- [Operator CLI reference](../architecture/deployment/cli.md) — every `devlog` command
- [Installation architecture](../architecture/deployment/installation.md) — how the
  installer and onboarding fit together

