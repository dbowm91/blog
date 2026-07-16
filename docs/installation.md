# Installation

Complete installation guide for DevLog blog CMS.

## Quick Install (Recommended)

Install DevLog from a release with one command:

```bash
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --native
```

This downloads the latest verified release, installs it to `/opt/devlog/`, and creates a `devlog` launcher at `/usr/local/bin/devlog`. Then run onboarding:

```bash
devlog onboard --mode native
```

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
~/.local/share/devlog/current -> ...
~/.local/bin/devlog -> ...
```

### Supply Chain Safety

The installer verifies SHA-256 checksums before installation. Artifacts are downloaded over HTTPS from GitHub Releases. See `scripts/check_release_artifacts.py` for artifact verification.

## Prerequisites

- Python 3.12+
- Node.js 18+ (for local development; Docker builds handle this automatically)
- SQLite (bundled with Python)
- Git

## Docker Production

### Via Installer

```bash
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --docker
cd /opt/devlog
devlog onboard --mode docker
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

> **Local HTTP testing:** Set `SESSION_COOKIE_SECURE=false` in your `.env` when testing at `http://localhost:5000`, otherwise admin login cookies will not persist. Never use `SESSION_COOKIE_SECURE=false` in production behind HTTPS.

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
devlog --verbose config     # Verbose help
devlog --quiet db           # Minimal output
```

Command groups: `config`, `admin`, `db`, `data`, `themes`, `backup`, `onboard`.

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
devlog onboard detect --json
```

### Resume Interrupted Onboarding

If onboarding was interrupted (e.g., power failure, Ctrl+C), resume from where it left off:

```bash
devlog onboard resume
devlog onboard resume --data-path /path/to/data
```

The resume command reads metadata from the data directory to determine the last completed step and continues from there.

## Configuration

### Typed Configuration System

DevLog uses a typed configuration system at `app/config/` with 20 frozen dataclasses:

```bash
devlog config check              # Validate configuration
devlog config show --effective   # Show resolved values with sources
devlog config explain            # Explain all config fields
devlog config paths              # Show config file locations
devlog config init               # Generate config.toml from defaults
devlog config migrate            # Migrate config to latest version
```

### Configuration Precedence

1. Environment variables (highest priority)
2. `config.toml`
3. Defaults (lowest priority)

### Environment Variables

Key environment variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `SECRET_KEY` | Flask session signing | — (required) |
| `ADMIN_PASSWORD` | Admin user password | — (required) |
| `DATABASE_URL` | Database URI | `sqlite:///data/blog.db` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `SESSION_COOKIE_SECURE` | Secure cookies | `true` |
| `ENABLE_SCHEDULER` | APScheduler jobs | `false` |
| `ENABLE_METRICS` | Metrics endpoint | `false` |

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
devlog backup create                  # Create backup
devlog backup verify --path backup.db # Verify backup integrity
devlog backup inspect --path backup.db # Show backup details
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
devlog themes list                        # List available themes
devlog themes validate --name "Catppuccin Mocha"  # Validate theme
devlog themes inspect --name "Catppuccin Mocha"   # Show theme details
```

Themes are selected in the admin dashboard at `/admin/settings`.

## Troubleshooting

### Admin Login Cookies Not Persisting

Set `SESSION_COOKIE_SECURE=false` in `.env` when testing at `http://localhost:5000`.

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

Change the port in `config.toml` or via environment variable:

```bash
PORT=8080 python run.py
```
